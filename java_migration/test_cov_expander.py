import os
import shutil
import traceback
from pathlib import Path

from dotenv import load_dotenv

from java_migration.eval.data_model import MigrationDatasetItem
from java_migration.eval.env_checker import EnvironmentValidator
from java_migration.eval.maven_build_verifier import MavenBuildVerifier
from java_migration.eval.utils import Dataset, safe_repo_name
from java_migration.randoop import run_randoop_on_repo
from java_migration.repo_workspace import RepoWorkspace
from java_migration.utils import REPO_ROOT
from java_migration.job_runner import JobRunner, Worker, JobCfg, JobResult, JobStatus





class TestCovExpander:
    def __init__(self, randoop_jar_path: Path, target_jdk_version=8):
        self.randoop_jar_path = randoop_jar_path

        validator = EnvironmentValidator()
        if not validator.validate(target_jdk_version):
            raise RuntimeError("Failed validating environment")

        if not self.randoop_jar_path.exists():
            raise RuntimeError(f"Randoop jar not found at {self.randoop_jar_path}")
        
        self.build_verifier = MavenBuildVerifier()

    def run(self, dataset_item: MigrationDatasetItem, output_root: Path, workspace_root: Path, clean_workspace: bool = True):
        workspace = None
        try:
            repo_workspace = RepoWorkspace.from_git(
                repo_name=dataset_item.repo_name,
                commit_sha=dataset_item.commit,
                workspace_dir=workspace_root / safe_repo_name(dataset_item.repo_name),
            )
            build_result = self.build_verifier.verify(repo_workspace.workspace_dir)
            if not build_result.build_success:
                raise RuntimeError(f"Build failed for repo {dataset_item.repo_name}")

            patch_path = run_randoop_on_repo(repo_workspace.workspace_dir, self.randoop_jar_path)

            output_dir.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(patch_path, output_root / f"{safe_repo_name(dataset_item.repo_name)}.patch")

        except Exception:
            print(f"Failed processing repo {dataset_item.repo_name} with error {traceback.format_exc()}")
        finally:
            if workspace is not None and clean_workspace:
                workspace.clean()


class TestCovExpandWorker(Worker):
    def __init__(self, randoop_jar_path: Path, target_jdk_version=8):
        self.test_cov_expander = TestCovExpander(randoop_jar_path, target_jdk_version)
        

    def __call__(self, job: JobCfg) -> JobResult:
        try:
            self.test_cov_expander.run(job.dataset_item, job.output_root, job.workspace_root, job.cleanup_workspace)
            return JobResult(status=JobStatus.SUCCESS)
        except Exception:
            return JobResult(status=JobStatus.FAIL, error=traceback.format_exc())


if __name__ == "__main__":
    load_dotenv()

    output_dir = REPO_ROOT / "data" / "cov_expand"

    dataset = MigrationDatasetItem.from_yaml(Dataset.get_path(Dataset.TINY))

    #TestCovExpander(Path(os.environ["RANDOOP_JAR_PATH"])).run(dataset[0], output_dir)

    job_cfgs = [JobCfg(dataset_item=item, output_root=output_dir, workspace_root=REPO_ROOT / "data" / "workspace") for item in dataset]

    job_runner = JobRunner(TestCovExpandWorker(Path(os.environ["RANDOOP_JAR_PATH"])), concurrency=4)
    job_results = job_runner.run(job_cfgs)

    print(job_runner.get_result_stats(job_results))
