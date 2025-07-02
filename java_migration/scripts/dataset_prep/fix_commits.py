
import yaml
from tqdm import tqdm

from java_migration.eval.utils import recover_safe_repo_name
from java_migration.utils import REPO_ROOT

dataset_path = REPO_ROOT / "data/migration_datasets/full_dataset.yaml"

failed_path = REPO_ROOT / "data/missing_commits.txt"
result_path = REPO_ROOT / "data/migration_datasets/full_dataset_.yaml"

with open(dataset_path, "r") as fin:
    dataset = yaml.safe_load(fin.read())

with open(failed_path) as fin:
    failed = [x.split(",") for x in fin.readlines()]
    failed_dict = {}
    for x in failed:
        try:
            failed_dict[recover_safe_repo_name(x[0])] = x[1].strip()
        except Exception as e:
            print(f"Error in {x[0]}: {e}")


for item in tqdm(dataset):
    if item["repo_name"] in failed_dict:
        item["commit"] = failed_dict[item["repo_name"]]
        print(f"Using commit {item['commit']} for {item['repo_name']}")

with open(result_path, "w") as fout:
    fout.write(yaml.dump(dataset))
