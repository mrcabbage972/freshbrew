
import yaml
import random

from java_migration.eval.data_model import MigrationDatasetItem
from java_migration.utils import REPO_ROOT


def main():
    dataset_path = REPO_ROOT / "data" / "migration_datasets" / "full_dataset.yaml"
    output_path = REPO_ROOT / "data" / "migration_datasets" / "medium_dataset.yaml"
    
    dataset = MigrationDatasetItem.from_yaml(dataset_path)

    random.shuffle(dataset)
    dataset = dataset[:50]

    with open(output_path, "w") as fout:
        yaml.dump([x.model_dump() for x in dataset], fout)


if __name__ == "__main__":
    main()
