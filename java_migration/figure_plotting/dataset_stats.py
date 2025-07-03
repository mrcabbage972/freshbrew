# type: ignore

import pandas as pd
import yaml

from java_migration.eval.utils import recover_safe_repo_name
from java_migration.figure_plotting.figure_utils import plot_counts, plot_histogram, plot_histogram_grid
from java_migration.utils import REPO_ROOT


def plot_deps_per_repo(df, output_path):
    plot_histogram(df["number_of_external_dependencies"], "External Dependencies", "Repositories", output_path, bins=5)


def plot_num_files(df, output_path):
    plot_histogram(df["number_of_java_files"], "External Dependencies", "Repositories", output_path, bins=5)


dataset_path = REPO_ROOT / "data/migration_datasets/full_dataset.yaml"
cov_data_path = REPO_ROOT / "data/migration_datasets/cov_data.csv"

with open(dataset_path) as fin:
    ds = yaml.safe_load(fin)

all_repo_features = [x["repo_features"] | {"repo": x["repo_name"]} | {"license": x["license"]} for x in ds]
df = pd.DataFrame(all_repo_features)

df_cov = pd.read_csv(cov_data_path)
df_cov["repo"] = df_cov.repo.apply(recover_safe_repo_name)
df = df.merge(df_cov, on="repo")
# plot_deps_per_repo(df, REPO_ROOT / "java_migration/figures/deps_per_repo.pdf")
# plot_num_files(df, REPO_ROOT / "java_migration/figures/files_per_repo.pdf")

columns_to_plot = {
    "number_of_external_dependencies": "External Dependencies",
    "number_of_java_files": "Java Files",
    "number_of_lines_of_code": "Lines of Code",
    "number_of_modules": "Modules",
    "number_of_unit_tests": "Unit Tests",
    "percent_before": "Test Coverage",
}

data_list = [df[col].tolist() for col in columns_to_plot.keys()]
titles = list(columns_to_plot.values())

plot_histogram_grid(
    data_list,
    titles,
    figure_xlabel=None,
    figure_ylabel="Repositories",
    output_path=REPO_ROOT / "java_migration/figures" / "dataset_stats.pdf",
    bins=10,
    figsize=(20, 12),
)

licenses = df.license.value_counts()

plot_counts(
    licenses.index.tolist(),
    counts=licenses.to_list(),
    xlabel="License Type",
    ylabel="Repositories",
    output_path=REPO_ROOT / "java_migration/figures" / "license_stats.pdf",
    figsize=(8, 8),
)
