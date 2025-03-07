import yaml


input_path = "/Users/mayvic/Documents/git/java-migration-paper/data/migration_datasets/full_dataset.yaml"
output_path = "/Users/mayvic/Documents/git/java-migration-paper/data/migration_datasets/full_dataset_deduped.yaml"

with open(input_path, "r") as f:
    data = yaml.safe_load(f)

known_repos = set()
output = []
for repo in data:
    cur_repo_name = repo["repo_name"].split("/")[1]
    if cur_repo_name in known_repos:
        print(f"Skipping {repo["repo_name"]}")
        continue
    known_repos.add(cur_repo_name)
    output.append(repo)

with open(output_path, "w") as f:
    yaml.dump(output, f)