import yaml

from java_migration.eval.utils import recover_safe_repo_name

build_result_path = "/Users/mayvic/Documents/git/java-migration-paper/data/jdk8_build_results.yaml"
dataset_path = "/Users/mayvic/Documents/git/java-migration-paper/data/migration_datasets/full_dataset.yaml"

filtered_build_result_path = "/Users/mayvic/Documents/git/java-migration-paper/data/jdk8_build_results_filtered.yaml"
with open(build_result_path, "r") as fin:
    build_result = yaml.safe_load(fin.read())

with open(dataset_path, "r") as fin:
    dataset = yaml.safe_load(fin.read())

valid_repo_names = set([x["repo_name"] for x in dataset])

valid_build_results = []
for repo in build_result:
    repo["repo_name"] = recover_safe_repo_name(repo["repo_name"])
    if repo["repo_name"] in valid_repo_names:
        valid_build_results.append(repo)


with open(filtered_build_result_path, "w") as fout:
    fout.write(yaml.dump(valid_build_results))
