# type: ignore

import logging
import multiprocessing
import multiprocessing.context
import subprocess
from enum import Enum
from pathlib import Path
from typing import Union

import pandas as pd
import yaml
from dotenv import load_dotenv
from pydantic import BaseModel
from tqdm import tqdm

from java_migration.eval.data_model import MigrationDatasetItem
from java_migration.eval.utils import recover_safe_repo_name, safe_repo_name
from java_migration.repo_workspace import RepoWorkspace
from java_migration.test_cov import get_test_cov
from java_migration.utils import REPO_ROOT

workspace_dir = REPO_ROOT / "data" / "workspace"
cov_data_path = REPO_ROOT / "data/migration_datasets/cov_data.csv"

COV_DECREASE_FLOOR = -0.05

logger = logging.getLogger(__name__)


class PatchApplyError(Exception):
    """Base exception for patch application failures."""

    pass


class PatchConflictError(PatchApplyError):
    """Raised when the patch cannot be applied due to conflicts."""

    pass


class CorruptPatchError(PatchApplyError):
    """Raised when the patch file is corrupt or malformed."""

    pass


class InvalidGitRepositoryError(PatchApplyError):
    """Raised when the target directory is not a valid Git repository."""

    pass


def apply_patch_to_repo(repo_path: Union[str, Path], patch_file_path: Union[str, Path]):
    """
    Applies a patch file to a Git repository, with a fallback to a 3-way merge
    for patches that don't apply cleanly due to context issues (e.g., line endings).

    Args:
        repo_path: The file system path to the root of the Git repository.
        patch_file_path: The file system path to the .patch file.

    Raises:
        FileNotFoundError: If the repo_path or patch_file_path does not exist.
        InvalidGitRepositoryError: If the repo_path is not a valid Git repository.
        PatchApplyError: If the patch fails to apply even with the fallback.
    """
    repo_path = Path(repo_path).resolve()
    patch_file_path = Path(patch_file_path).resolve()

    # --- 1. Validate paths and repository ---
    if not repo_path.exists() or not repo_path.is_dir():
        raise FileNotFoundError(f"Repository path does not exist or is not a directory: {repo_path}")
    if not patch_file_path.exists() or not patch_file_path.is_file():
        raise FileNotFoundError(f"Patch file not found: {patch_file_path}")
    if not (repo_path / ".git").exists():
        raise InvalidGitRepositoryError(f"Not a valid Git repository: {repo_path}")

    # --- 2. Read patch and ensure it has a final newline ---
    patch_content = patch_file_path.read_text(encoding="utf-8")
    if not patch_content.endswith("\n"):
        patch_content += "\n"

    # --- 3. Attempt a strict check first ---
    apply_command = ["git", "apply"]
    try:
        subprocess.run(
            ["git", "apply", "--check"],
            cwd=str(repo_path),
            check=True,
            capture_output=True,
            text=True,
            input=patch_content,
            encoding="utf-8",
        )
        logger.info("Patch passed strict check. Applying normally.")
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.lower()
        # If strict check fails for common reasons, fall back to a 3-way merge.
        if "patch does not apply" in stderr or "malformed patch" in stderr:
            logger.warning("Strict patch check failed. Attempting a 3-way merge application...")
            apply_command.append("--3way")
        else:
            # For other, unexpected check errors, fail fast.
            raise PatchApplyError(f"Failed to check patch with an unexpected error.\nDetails: {e.stderr}")

    # --- 4. Apply the patch using the selected strategy ---
    try:
        subprocess.run(
            apply_command,
            cwd=str(repo_path),
            check=True,
            capture_output=True,
            text=True,
            input=patch_content,
            encoding="utf-8",
        )
        logger.info("Patch applied successfully.")
    except subprocess.CalledProcessError as e:
        # This error is raised if the standard apply fails OR the 3-way merge fails.
        raise PatchApplyError(f"The patch could not be applied, even with fallback attempts.\nDetails: {e.stderr}")


class JobCfg(BaseModel):
    dataset_item: MigrationDatasetItem
    output_root: Path
    workspace_root: Path
    cleanup_workspace: bool = False
    target_java_version: str


class JobStatus(Enum):
    FAIL = 0
    SKIP = 1
    SUCCESS = 2


class CovResult(BaseModel):
    cov_before: float
    cov_after: float
    cov_percent_change: float
    cov_guard_pass: bool


class JobResult(BaseModel):
    status: JobStatus
    error: str | None = None
    cov_result: CovResult | None = None


class Worker:
    def __init__(self, pre_cov: dict[str, float]):
        self.pre_cov = pre_cov

    def __call__(self, job: JobCfg) -> JobResult:
        workspace = None
        try:
            repo_dir = job.output_root / safe_repo_name(job.dataset_item.repo_name)
            post_cov_file_path = repo_dir / "cov.yaml"
            if post_cov_file_path.exists():
                print(f"Repo {job.dataset_item.repo_name} already processed, skipping")
                with open(post_cov_file_path) as fin:
                    cov_result = CovResult.model_validate(yaml.safe_load(fin.read()))
                return JobResult(status=JobStatus.SKIP, cov_result=cov_result)

            results_file_path = repo_dir / "result.yaml"
            result_dict = yaml.safe_load(results_file_path.read_text())
            if result_dict["build_result"]["test_success"] is not True:
                print(f"Repo {job.dataset_item.repo_name} did not pass tests, skipping")
                return JobResult(status=JobStatus.SKIP)

            patch_path = repo_dir / "diff.patch"
            if not patch_path.exists():
                print(f"Repo {job.dataset_item.repo_name} has no patch")
                return JobResult(status=JobStatus.FAIL)

            workspace = RepoWorkspace.from_git(
                repo_name=job.dataset_item.repo_name,
                workspace_dir=job.workspace_root / safe_repo_name(job.dataset_item.repo_name),
                commit_sha=job.dataset_item.commit,
            )

            try:
                apply_patch_to_repo(workspace.workspace_dir, patch_path)
            except PatchApplyError as e:
                return JobResult(status=JobStatus.FAIL, error=f"Failed applying patch: {str(e)}")
     
            test_cov = get_test_cov(
                str(workspace.workspace_dir), use_wrapper=False, target_java_version=job.target_java_version
            )
            if test_cov is None:
                return JobResult(status=JobStatus.FAIL, error="Failed calculating coverage")

            cur_pre_cov = self.pre_cov[job.dataset_item.repo_name]

            cov_percent_change = test_cov.LINE.percent / cur_pre_cov - 1
            
            cov_result = CovResult(
                cov_before=cur_pre_cov,
                cov_after=test_cov.LINE.percent,
                cov_percent_change=cov_percent_change,
                cov_guard_pass=cov_percent_change > COV_DECREASE_FLOOR,
            )

            with open(post_cov_file_path, "w") as fout:
                yaml.dump(cov_result.model_dump(), fout)

            return JobResult(status=JobStatus.SUCCESS, cov_result=cov_result)

        except Exception as e:
            print(f"Failed processing repo {job.dataset_item.repo_name} with error {str(e)}")
            return JobResult(status=JobStatus.FAIL, error=str(e))
        finally:
            if job.cleanup_workspace and workspace is not None:
                workspace.clean()


def listener(progress_queue: multiprocessing.Queue, total: int):
    pbar = tqdm(total=total)
    for _ in range(total):
        progress_queue.get()
        pbar.update(1)
    pbar.close()


def worker_wrapper(worker: Worker, job_cfg: JobCfg, progress_queue: multiprocessing.Queue) -> JobResult:
    result = worker(job_cfg)
    progress_queue.put(1)
    return result


def _run_jobs(
    job_cfgs: list[JobCfg], pre_cov: dict[str, float], concurrency: int, timeout_seconds: int
) -> list[JobResult]:
    worker = Worker(pre_cov)
    manager = multiprocessing.Manager()
    progress_queue = manager.Queue()
    progress_process = multiprocessing.Process(target=listener, args=(progress_queue, len(job_cfgs)))
    progress_process.start()

    with multiprocessing.Pool(processes=concurrency) as pool:
        task_futures = [pool.apply_async(worker_wrapper, (worker, job_cfg, progress_queue)) for job_cfg in job_cfgs]
        job_results = []
        for task_futures in task_futures:
            try:
                result = task_futures.get(timeout=timeout_seconds)
                job_results.append(result)
            except multiprocessing.context.TimeoutError:
                progress_queue.put(1)
                job_results.append(
                    JobResult(status=JobStatus.FAIL, error=f"Job timed out after {timeout_seconds} seconds")
                )
    progress_process.join()
    return job_results


def main():
    load_dotenv()
    experiment_path = REPO_ROOT / "data" / "experiments/2025-07-03/13-42-13-interesting-lederberg"
    target_java_version = "17"

    df_cov = pd.read_csv(cov_data_path)
    df_cov["repo"] = df_cov.repo.apply(recover_safe_repo_name)
    pre_cov = df_cov.set_index("repo")["percent_before"].to_dict()

    workspace_dir.mkdir(parents=True, exist_ok=True)

    dataset = MigrationDatasetItem.from_yaml(REPO_ROOT / "data/migration_datasets/full_dataset.yaml")
    # dataset = [x for x in dataset if x.repo_name == "abahgat/suffixtree"]

    job_cfgs = [
        JobCfg(
            dataset_item=item,
            output_root=experiment_path / "job_results",
            workspace_root=workspace_dir,
            cleanup_workspace=True,
            target_java_version=target_java_version,
        )
        for item in dataset
    ]

    results = _run_jobs(job_cfgs, pre_cov, concurrency=16, timeout_seconds=60)

    summary = {"repo_results": {}}
    passed = 0
    total = 0
    job_fails = 0
    for job_cfg, result in zip(job_cfgs, results):
        summary["repo_results"][job_cfg.dataset_item.repo_name] = {"status": str(result.status)}
        if result.status == JobStatus.FAIL:
            summary["repo_results"][job_cfg.dataset_item.repo_name]["error"] = result.error
            job_fails += 1
        if result.cov_result is not None:
            summary["repo_results"][job_cfg.dataset_item.repo_name]["coverage"] = result.cov_result.model_dump()
            if result.cov_result.cov_guard_pass:
                passed += 1
            total += 1
    summary["cov_guard_pass_rate"] = 1.0 * passed / total
    summary["job_fails"] = job_fails

    summary_path = experiment_path / "cov_results.yaml"
    with open(summary_path, "w") as fout:
        yaml.dump(summary, fout)


if __name__ == "__main__":
    main()
