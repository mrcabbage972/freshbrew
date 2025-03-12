from pathlib import Path

import yaml

from java_migration.eval.utils import recover_safe_repo_name, safe_repo_name

repo_feats_root = Path("/Users/mayvic/Documents/git/java-migration-paper/data/repo_feats/repo_features_10k")
dataset_path = Path("/Users/mayvic/Documents/git/java-migration-paper/data/migration_datasets/full_dataset.yaml")
output_path = Path("/Users/mayvic/Documents/git/java-migration-paper/data/repo_feats.yaml")

with open(dataset_path, "r") as fin:
    dataset = yaml.safe_load(fin)

repo_feats = {}

for item in dataset:
    safe_name = item["repo_name"].replace("/", "-")
    repo_feats_path = repo_feats_root / f"{safe_name}.yaml"
    if not repo_feats_path.exists():
        print(f"Warning: missing repo features for {item['repo_name']}")
        continue
    with open(repo_feats_path, "r") as fin:
        cur_repo_feats = yaml.safe_load(fin)
        repo_feats[item["repo_name"]] = cur_repo_feats

with open(output_path, "w") as fout:
    yaml.safe_dump(repo_feats, fout)
