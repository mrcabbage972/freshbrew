import contextlib
import io
import shutil
import traceback

import yaml
from dotenv import load_dotenv

from java_migration.eval.data_model import MigrationDatasetItem
from java_migration.eval.env_checker import EnvironmentValidator
from java_migration.eval.maven_build_verifier import MavenBuildVerifier
from java_migration.eval.utils import Dataset, safe_repo_name
from java_migration.job_runner import JobCfg, JobResult, JobRunner, JobStatus, Worker
from java_migration.repo_workspace import RepoWorkspace
from java_migration.utils import REPO_ROOT


class BuildCheckWorker(Worker):
    def __init__(self, target_jdk_version: str):
        self.build_verifier = MavenBuildVerifier()
        self.target_jdk_version = target_jdk_version

        validator = EnvironmentValidator()
        if not validator.validate(int(target_jdk_version)):
            raise RuntimeError("Failed validating environment")

    def __call__(self, job: JobCfg) -> JobResult:
        try:
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                self._run_build_check(job)
            with open(job.output_root / safe_repo_name(job.dataset_item.repo_name) / "stdout.txt", "w") as f:
                f.write(buffer.getvalue())
            return JobResult(status=JobStatus.SUCCESS)
        except Exception:
            return JobResult(status=JobStatus.FAIL, error=traceback.format_exc())

    def _run_build_check(self, job: JobCfg):
        workspace = None
        try:
            output_dir = job.output_root / safe_repo_name(job.dataset_item.repo_name)
            if output_dir.exists():
                shutil.rmtree(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            repo_workspace = RepoWorkspace.from_git(
                repo_name=job.dataset_item.repo_name,
                commit_sha=job.dataset_item.commit,
                workspace_dir=job.workspace_root / safe_repo_name(job.dataset_item.repo_name),
            )
            build_result = self.build_verifier.verify(
                repo_workspace.workspace_dir, target_java_version=self.target_jdk_version, clean=True
            )

            with open(output_dir / "build.yaml", "w") as fout:
                yaml.dump(build_result.model_dump(), fout)

            if not build_result.build_success:
                raise RuntimeError(f"Build failed for repo {job.dataset_item.repo_name}")
        except Exception:
            print(f"Failed processing repo {job.dataset_item.repo_name} with error {traceback.format_exc()}")
        finally:
            if workspace is not None:
                workspace.clean()


def main():
    output_dir = REPO_ROOT / "output" / "build_check_medium"

    dataset = MigrationDatasetItem.from_yaml(Dataset.get_path(Dataset.MEDIUM))

    job_cfgs = [
        JobCfg(dataset_item=item, output_root=output_dir, workspace_root=REPO_ROOT / "data" / "workspace")
        for item in dataset
    ]

    job_runner = JobRunner(BuildCheckWorker(target_jdk_version="17"), concurrency=8)
    # BuildCheckWorker(target_jdk_version="17")(job_cfgs[0])

    job_results = job_runner.run(job_cfgs)

    print(job_runner.get_result_stats(job_results))


if __name__ == "__main__":
    load_dotenv()
    main()
