import multiprocessing
import multiprocessing.context
from enum import Enum
from pathlib import Path

import yaml
from pydantic import BaseModel
from tqdm import tqdm

from java_migration.eval.data_model import MigrationDatasetItem
from java_migration.eval.maven_build_verifier import MavenBuildVerifier
from java_migration.eval.utils import safe_repo_name
from java_migration.repo_workspace import RepoWorkspace
from java_migration.test_cov import get_test_cov
from java_migration.utils import REPO_ROOT


class JobCfg(BaseModel):
    dataset_item: MigrationDatasetItem
    output_root: Path
    workspace_root: Path
    cleanup_workspace: bool = False


class JobStatus(Enum):
    FAIL = 0
    SKIP = 1
    SUCCESS = 2


class JobResult(BaseModel):
    status: JobStatus
    error: str | None = None


class Worker:
    def __call__(self, job: JobCfg) -> JobResult:
        workspace = None
        try:
            repo_dir = job.output_root / safe_repo_name(job.dataset_item.repo_name)
            if repo_dir.exists():
                print(f"Repo {job.dataset_item.repo_name} already processed, skipping")
                return JobResult(status=JobStatus.SKIP)

            workspace = RepoWorkspace.from_git(
                repo_name=job.dataset_item.repo_name,
                workspace_dir=job.workspace_root / safe_repo_name(job.dataset_item.repo_name),
                commit_sha=job.dataset_item.commit,
            )

            build_result = MavenBuildVerifier().verify(workspace.workspace_dir)
            if not build_result.build_success:
                print(f"Repo {job.dataset_item.repo_name} build failed, skipping")
                return JobResult(status=JobStatus.SKIP)
            if not build_result.test_success:
                print(f"Repo {job.dataset_item.repo_name} tests failed, skipping")
                return JobResult(status=JobStatus.SKIP)
            if not build_result.test_results:
                print(f"Repo {job.dataset_item.repo_name} tests result missing, skipping")
                return JobResult(status=JobStatus.SKIP)
            if build_result.test_results.tests_run == 0:
                print(f"Repo {job.dataset_item.repo_name} no tests run, skipping")
                return JobResult(status=JobStatus.SKIP)
            test_cov, test_stdout, test_stderr, coverage_stdout, coverage_stderr = get_test_cov(
                str(workspace.workspace_dir), use_wrapper=False, target_java_version="8"
            )

            repo_dir.mkdir(parents=True, exist_ok=True)
            if test_cov:
                with open(repo_dir / "cov.yaml", "w") as fout:
                    yaml.dump(test_cov.model_dump(), fout)
            with open(repo_dir / "test_stdout.txt", "w") as fout:
                fout.write(test_stdout)
            with open(repo_dir / "test_stderr.txt", "w") as fout:
                fout.write(test_stderr)
            with open(repo_dir / "coverage_stdout.txt", "w") as fout:
                fout.write(coverage_stdout)
            with open(repo_dir / "coverage_stderr.txt", "w") as fout:
                fout.write(coverage_stderr)

            return JobResult(status=JobStatus.SUCCESS)

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


def _run_jobs(job_cfgs: list[JobCfg], concurrency: int, timeout_seconds: int) -> list[JobResult]:
    worker = Worker()
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
    dataset_path = REPO_ROOT / "data" / "migration_datasets" / "mini_dataset.yaml"
    output_path = REPO_ROOT / "data" / "cov_output"
    workspace_dir = REPO_ROOT / "data" / "workspace"

    output_path.mkdir(parents=True, exist_ok=True)
    workspace_dir.mkdir(parents=True, exist_ok=True)

    dataset = MigrationDatasetItem.from_yaml(dataset_path)
    
    job_cfgs = [JobCfg(dataset_item=item, output_root=output_path, workspace_root=workspace_dir) for item in dataset]

    # worker = Worker()
    # results = [worker(job_cfg) for job_cfg in tqdm(job_cfgs)]
    results = _run_jobs(job_cfgs, concurrency=4, timeout_seconds=300)
    print(results)
    pass


if __name__ == "__main__":
    main()
