import csv
from pathlib import Path

full_dataset_path = Path("data/migration_datasets/full_dataset.yaml")

license_file_path = Path("data/migration_datasets/permissive.csv")


with open(license_file_path, "r") as csvfile:
    reader = csv.DictReader(csvfile, fieldnames=None)
    for row in reader:
        print(row)
