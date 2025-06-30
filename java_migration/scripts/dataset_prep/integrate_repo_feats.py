import csv

import yaml
from tqdm import tqdm

from java_migration.eval.utils import safe_repo_name

dataset_path = "data/migration_datasets/full_dataset.yaml"
repo_feats_path = "data/migration_datasets/repo_features.csv"
result_path = "data/migration_datasets/full_dataset_.yaml"

repo_feats = {}
with open(repo_feats_path, "r") as fin:
    for row in csv.DictReader(fin):
        repo_feats[row["repo_name"][:-5]] = row


with open(dataset_path, "r") as fin:
    dataset = yaml.safe_load(fin.read())

safe_repo_names = {safe_repo_name(x["repo_name"]).lower().replace("-", "_"): idx for idx, x in enumerate(dataset)}

filtered_repo_feats_result = {
    k.lower().replace("-", "_"): v for k, v in repo_feats.items() if k.lower().replace("-", "_") in safe_repo_names
}

for repo in tqdm(filtered_repo_feats_result):
    dataset_idx = safe_repo_names[repo]
    del filtered_repo_feats_result[repo]["repo_name"]
    dataset[dataset_idx]["repo_features"] = {
        k: int(v) for k, v in filtered_repo_feats_result[repo].items() if v != "maven"
    }

with open(result_path, "w") as fout:
    fout.write(yaml.dump(dataset))
