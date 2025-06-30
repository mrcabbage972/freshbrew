import csv
from pathlib import Path

import yaml

full_dataset_path = Path("data/migration_datasets/full_dataset.yaml")

license_file_path = Path("data/migration_datasets/permissive.csv")


license_map = {}
with open(license_file_path, "r") as csvfile:
    reader = csv.DictReader(csvfile, fieldnames=["id", "repo", "license"])
    for row in reader:
        license_map[row["repo"]] = row["license"]


with open(full_dataset_path, "r") as f:
    dataset = yaml.safe_load(f)

out_dataset = []
for item in dataset:
    if item["repo_name"] in license_map:
        item["license"] = license_map[item["repo_name"]]
        out_dataset.append(item)

with open("data/migration_datasets/full_dataset_with_license.yaml", "w") as f:
    yaml.dump(out_dataset, f)
