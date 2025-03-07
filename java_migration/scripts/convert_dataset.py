import yaml

input_path = "/Users/mayvic/Documents/git/java-migration-paper/data/head_commits.yaml"
output_path = "/Users/mayvic/Documents/git/java-migration-paper/data/full_dataset.yaml"
with open(input_path) as fin:
    input_data = yaml.safe_load(fin.read())

output_data = []
for commit in input_data:
    repo_name, commit = list(commit.items())[0]
    output_data.append({"repo_name": repo_name, "commit": commit})

with open(output_path, "w") as fout:
    fout.write(yaml.dump(output_data))
