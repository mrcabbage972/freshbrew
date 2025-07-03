# type: ignore

import contextlib
import io
import os
import random
import shutil
import traceback
from pathlib import Path

import yaml
from dotenv import load_dotenv

from java_migration.eval.data_model import MigrationDatasetItem
from java_migration.eval.env_checker import EnvironmentValidator
from java_migration.eval.maven_build_verifier import MavenBuildVerifier
from java_migration.eval.utils import safe_repo_name
from java_migration.job_runner import JobCfg, JobResult, JobRunner, JobStatus, Worker

# from java_migration.randoop import run_randoop_on_repo
from java_migration.randoop.randoop import RandoopRunner
from java_migration.repo_workspace import RepoWorkspace
from java_migration.test_cov import get_test_cov
from java_migration.utils import REPO_ROOT


class TestCovExpander:
    def __init__(self, randoop_jar_path: Path, target_jdk_version: str = "8", clear_cache: str = True):
        self.randoop_jar_path = randoop_jar_path
        self.target_jdk_version = target_jdk_version
        self.clear_cache = clear_cache

        validator = EnvironmentValidator()
        if not validator.validate(int(target_jdk_version)):
            raise RuntimeError("Failed validating environment")

        if not self.randoop_jar_path.exists():
            raise RuntimeError(f"Randoop jar not found at {self.randoop_jar_path}")

        self.build_verifier = MavenBuildVerifier()

        self.randoop_runner = RandoopRunner(
            target_java_version=target_jdk_version, randoop_jar_path=self.randoop_jar_path
        )

    def run(
        self, dataset_item: MigrationDatasetItem, output_root: Path, workspace_root: Path, clean_workspace: bool = True
    ):
        workspace = None
        try:
            output_dir = output_root / safe_repo_name(dataset_item.repo_name)
            if (
                not self.clear_cache
                and output_dir.exists()
                and (
                    (output_dir / "randoop.patch").exists()
                    or (output_dir / "stdout.txt").exists()
                    or (output_dir / "cov_before.yaml").exists()
                )
            ):
                print(f"Skipping existing output for {dataset_item.repo_name}")
                return

            print(f"Processing repo {dataset_item.repo_name}")

            if output_dir.exists():
                shutil.rmtree(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            repo_workspace = RepoWorkspace.from_git(
                repo_name=dataset_item.repo_name,
                commit_sha=dataset_item.commit,
                workspace_dir=workspace_root / safe_repo_name(dataset_item.repo_name),
            )
            build_result = self.build_verifier.verify(
                repo_workspace.workspace_dir, target_java_version=self.target_jdk_version, build_only=True
            )
            if not build_result.build_success:
                raise RuntimeError(f"Build failed for repo {dataset_item.repo_name}")

            with open(output_dir / "build.yaml", "w") as fout:
                fout.write(build_result.build_log)

            self._get_cov(repo_workspace.workspace_dir, output_dir / "cov_before.yaml")
            repo_workspace.reset()
            patch_path = self.randoop_runner.run(repo_workspace.workspace_dir)
            self._get_cov(repo_workspace.workspace_dir, output_dir / "cov_after.yaml")

            shutil.copyfile(patch_path, output_dir / "randoop.patch")

        except Exception:
            print(f"Failed processing repo {dataset_item.repo_name} with error {traceback.format_exc()}")
        finally:
            if workspace is not None and clean_workspace:
                workspace.clean()

    def _get_cov(self, workspace_dir: Path, output_path: Path):
        test_cov = get_test_cov(str(workspace_dir), use_wrapper=False, target_java_version=self.target_jdk_version)

        if test_cov:
            with open(output_path, "w") as fout:
                yaml.dump(test_cov.model_dump(), fout)
        else:
            raise RuntimeError("No test coverage found for repo")


class TestCovExpandWorker(Worker):
    def __init__(self, randoop_jar_path: Path, target_jdk_version: str, clear_cache: str):
        self.test_cov_expander = TestCovExpander(randoop_jar_path, target_jdk_version, clear_cache)

    def __call__(self, job: JobCfg) -> JobResult:
        try:
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                self.test_cov_expander.run(job.dataset_item, job.output_root, job.workspace_root, job.cleanup_workspace)
            with open(job.output_root / safe_repo_name(job.dataset_item.repo_name) / "stdout.txt", "w") as f:
                f.write(buffer.getvalue())
            return JobResult(status=JobStatus.SUCCESS)
        except Exception:
            return JobResult(status=JobStatus.FAIL, error=traceback.format_exc())


def main():
    output_dir = REPO_ROOT / "output" / "cov_expand_30k"

    # dataset = MigrationDatasetItem.from_yaml(Dataset.get_path(Dataset.MEDIUM))
    dataset = MigrationDatasetItem.from_yaml("data/30k_dataset/30k_processed.yaml")

    print(len(dataset))

    # dataset = [x for x in dataset if "hera" in x.repo_name]

    # TestCovExpander(Path(os.environ["RANDOOP_JAR_PATH"])).run(dataset[0], output_dir)

    job_cfgs = [
        JobCfg(dataset_item=item, output_root=output_dir, workspace_root=REPO_ROOT / "data" / "workspace")
        for item in dataset
    ]

    job_runner = JobRunner(
        TestCovExpandWorker(Path(os.environ["RANDOOP_JAR_PATH"]), target_jdk_version="8", clear_cache=False),
        concurrency=os.cpu_count() - 4,
    )
    random.shuffle(job_cfgs)
    job_results = job_runner.run(job_cfgs)

    print(job_runner.get_result_stats(job_results))


if __name__ == "__main__":
    load_dotenv()
    main()
