from collections import defaultdict

from java_migration.figure_plotting.figure_utils import plot_counts
from java_migration.utils import REPO_ROOT

dataset_path = REPO_ROOT / "data/migration_datasets/full_dataset.yaml"

counts_per_lib = defaultdict(int)
counts_per_lib = {"a": 1, "b": 2, "c": 3, "d": 4, "e": 5}

output_path = REPO_ROOT / "java_migration/figures/samples_per_library.pdf"

plot_counts(counts_per_lib, "x", "y", output_path)
