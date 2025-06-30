import json
import tempfile
from pathlib import Path

import yaml
from tqdm import tqdm

from java_migration.repo_workspace import RepoWorkspace
from java_migration.utils import REPO_ROOT

dataset_path = REPO_ROOT / "data/migration_datasets/full_dataset.yaml"

failed_path = REPO_ROOT / "data" / "failed_checkout.jsonl"

with open(dataset_path, "r") as fin:
    dataset = yaml.safe_load(fin.read())

errors = []

for item in tqdm(dataset):
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            RepoWorkspace.from_git(item["repo_name"], workspace_dir=Path(tmpdir), commit_sha=item["commit"])
    except Exception as e:
        errors.append({"repo_name": item["repo_name"], "error": e.args[0]._exception})

with open(failed_path, "w") as fout:
    for error in errors:
        fout.write(json.dumps(error) + "\n")
