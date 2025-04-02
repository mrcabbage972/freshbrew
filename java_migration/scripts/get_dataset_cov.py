from java_migration.test_cov import get_test_cov
from java_migration.eval.data_model import MigrationDatasetItem
from java_migration.utils import REPO_ROOT
from java_migration.repo_workspace import RepoWorkspace
import yaml
from tqdm import tqdm
from java_migration.eval.utils import safe_repo_name

def main():
    dataset_path = REPO_ROOT / "data" / "migration_datasets" / "tiny_dataset.yaml"
    output_path = REPO_ROOT / "data" / "cov_output"
    workspace_dir = REPO_ROOT / "data" / "workspace"
    
    output_path.mkdir(parents=True, exist_ok=True)
    workspace_dir.mkdir(parents=True, exist_ok=True)
    
    dataset = MigrationDatasetItem.from_yaml(dataset_path)
    dataset = dataset[1:]

    for repo in tqdm(dataset):
        workspace = RepoWorkspace.from_git(repo_name=repo.repo_name, workspace_dir=workspace_dir, commit_sha=repo.commit)
        test_cov = get_test_cov(workspace.workspace_dir, use_wrapper=False, target_java_version="8")
        with open(output_path / f"{safe_repo_name(repo.repo_name)}.yaml", "w") as fout:
            yaml.dump(test_cov.model_dump(), fout)
        workspace.clean()        
    pass        


if __name__ == "__main__":
    main()
