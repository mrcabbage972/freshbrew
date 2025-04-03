import yaml
from tqdm import tqdm

from java_migration.eval.data_model import MigrationDatasetItem
from java_migration.eval.utils import safe_repo_name
from java_migration.repo_workspace import RepoWorkspace
from java_migration.test_cov import get_test_cov
from java_migration.utils import REPO_ROOT


def main():
    dataset_path = REPO_ROOT / "data" / "migration_datasets" / "mini_dataset.yaml"
    output_path = REPO_ROOT / "data" / "cov_output"
    workspace_dir = REPO_ROOT / "data" / "workspace"

    output_path.mkdir(parents=True, exist_ok=True)
    workspace_dir.mkdir(parents=True, exist_ok=True)

    dataset = MigrationDatasetItem.from_yaml(dataset_path)

    for repo in tqdm(dataset):
        workspace = None
        try:
            repo_dir = output_path / safe_repo_name(repo.repo_name)
            if repo_dir.exists():
                print(f"Repo {repo.repo_name} already processed, skipping")
                continue

            workspace = RepoWorkspace.from_git(
                repo_name=repo.repo_name, workspace_dir=workspace_dir, commit_sha=repo.commit
            )
            test_cov, test_stdout, test_stderr, coverage_stdout, coverage_stderr = get_test_cov(
                workspace.workspace_dir, use_wrapper=False, target_java_version="8"
            )

            repo_dir.mkdir(parents=True, exist_ok=True)
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

        except Exception as e:
            print(f"Failed processing repo {repo.repo_name} with error {str(e)}")
        finally:
            pass
            # if workspace is not None:
            #     workspace.clean()

    pass


if __name__ == "__main__":
    main()
