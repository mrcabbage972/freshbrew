import yaml
from tqdm import tqdm

from java_migration.eval.utils import safe_repo_name

dataset_path = "data/migration_datasets/full_dataset.yaml"
filtered_build_result_path = "data/migration_datasets/jdk8_build_results_30k.yaml"
result_path = "data/migration_datasets/full_dataset_.yaml"

with open(filtered_build_result_path, "r") as fin:
    build_result = yaml.safe_load(fin.read())

with open(dataset_path, "r") as fin:
    dataset = yaml.safe_load(fin.read())

safe_repo_names = {safe_repo_name(x["repo_name"]): idx for idx, x in enumerate(dataset)}

filtered_built_result = [x for x in build_result if x["repo_name"] in safe_repo_names]


for repo in tqdm(filtered_built_result):
    if "test" in repo and "tests" in repo["test"]:
        tests = repo["test"]["tests"]
        dataset_idx = safe_repo_names[repo["repo_name"]]
        dataset[dataset_idx]["test_count"] = tests

with open(result_path, "w") as fout:
    fout.write(yaml.dump(dataset))
