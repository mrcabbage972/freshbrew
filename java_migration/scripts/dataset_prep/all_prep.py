import yaml

def get_normal_repo_name(repo_name: str) -> str:
    split_idx = repo_name.index("_")
    normal_repo_name = repo_name[:split_idx] + "/" + repo_name[split_idx + 1 :]
    return normal_repo_name


input_dataset_path = "/home/user/java-migration-paper/data/30k.yaml"
output_dataset_path = "/home/user/java-migration-paper/data/30k_dataset/30k_processed.yaml"


with open(input_dataset_path) as fin:
    input_ds = yaml.safe_load(fin)

for item in input_ds:
    item["repo_name"] = get_normal_repo_name(item["repo_name"])

with open(output_dataset_path, 'w') as fout:
    yaml.dump(input_ds, fout)