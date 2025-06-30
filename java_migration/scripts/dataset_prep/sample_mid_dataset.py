import random

import yaml

from java_migration.utils import REPO_ROOT


def main():
    dataset_path = REPO_ROOT / "data" / "migration_datasets" / "full_dataset.yaml"
    output_path = REPO_ROOT / "data" / "migration_datasets" / "tiny_dataset.yaml"

    with open(dataset_path, "r") as fin:
        dataset = yaml.safe_load(fin)

    random.shuffle(dataset)
    dataset = dataset[:3]

    with open(output_path, "w") as fout:
        yaml.dump(dataset, fout)


if __name__ == "__main__":
    main()
