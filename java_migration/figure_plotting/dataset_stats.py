import pandas as pd
import yaml

from java_migration.figure_plotting.figure_utils import plot_counts
from java_migration.utils import REPO_ROOT

dataset_path = REPO_ROOT / "data/migration_datasets/full_dataset.yaml"

with open(dataset_path) as fin:
    ds = yaml.safe_load(fin)

all_repo_features = [x["repo_features"] for x in ds]
df = pd.DataFrame(all_repo_features)
counts_df = df.number_of_external_dependencies.value_counts(bins=10)

count_dict = {f"{0.5 * (bin.left + bin.right):.2f}": count for bin, count in counts_df.to_dict().items()}

# counts_per_lib = defaultdict(int)
# counts_per_lib = {"a": 1, "b": 2, "c": 3, "d": 4, "e": 5}

output_path = REPO_ROOT / "java_migration/figures/samples_per_library.pdf"

plot_counts(count_dict, "x", "y", output_path)
