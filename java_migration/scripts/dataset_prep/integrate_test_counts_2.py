import yaml

from java_migration.eval.utils import recover_safe_repo_name

dataset_path = "/Users/mayvic/Documents/git/java-migration-paper/data/migration_datasets/mini_dataset.yaml"
filtered_build_result_path = "/Users/mayvic/Documents/git/java-migration-paper/data/jdk8_build_results_filtered.yaml"
# result_path =  "/Users/mayvic/Documents/git/java-migration-paper/data/migration_datasets/full_dataset.yaml"

with open(filtered_build_result_path, "r") as fin:
    build_result = yaml.safe_load(fin.read())

with open(dataset_path, "r") as fin:
    dataset = yaml.safe_load(fin.read())

test_counts = {}

for repo in build_result:
    if "test" in repo and "tests" in repo["test"]:
        tests = repo["test"]["tests"]
        test_counts[repo["repo_name"]] = tests

dataset_idx_lookup = {x["repo_name"]: idx for idx, x in enumerate(dataset)}

for repo_name, test_counts in test_counts.items():
    if repo_name in dataset_idx_lookup:
        dataset[dataset_idx_lookup[repo_name]]["test_count"] = test_counts

with open(dataset_path, "w") as fout:
    fout.write(yaml.dump(dataset))
