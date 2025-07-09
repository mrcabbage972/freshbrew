# type: ignore

import pandas as pd
import yaml

from java_migration.eval.utils import recover_safe_repo_name
from java_migration.figure_plotting.figure_utils import (
    plot_boxplot_grid,
    plot_counts,
    plot_histogram,
    plot_histogram_grid,
)
from java_migration.utils import REPO_ROOT


def plot_deps_per_repo(df, output_path):
    plot_histogram(df["number_of_external_dependencies"], "External Dependencies", "Repositories", output_path, bins=5)


def plot_num_files(df, output_path):
    plot_histogram(df["number_of_java_files"], "External Dependencies", "Repositories", output_path, bins=5)


dataset_path = REPO_ROOT / "data/migration_datasets/full_dataset.yaml"
cov_data_path = REPO_ROOT / "data/migration_datasets/cov_data.csv"

with open(dataset_path) as fin:
    ds = yaml.safe_load(fin)

all_repo_features = [
    x["repo_features"] | {"repo": x["repo_name"]} | {"license": x["license"]} | {"commit_date": x["commit_date"]}
    for x in ds
]
df = pd.DataFrame(all_repo_features)

df_cov = pd.read_csv(cov_data_path)
df_cov["repo"] = df_cov.repo.apply(recover_safe_repo_name)
df = df.merge(df_cov, on="repo")

date_years = df["commit_date"].apply(lambda x: x.split("-")[0])
date_year_counts = date_years.value_counts(sort=False)
date_year_counts = date_year_counts.sort_index(axis=0)

plot_counts(
    bins=date_year_counts.index.tolist(),
    counts=date_year_counts.tolist(),
    xlabel="Commit Date",
    ylabel="Repositories",
    output_path=REPO_ROOT / "java_migration/figures" / "commit_date_hist.pdf",
)

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


tick_definitions = {
    0: [1, 5, 10, 50, 100],  # External Dependencies
    1: [1, 10, 100, 1000],  # Java Files
    2: [1, 10, 100, 1000, 10000, 100000],  # Lines of Code
    3: [1, 10, 20, 30, 40],  # Modules (Linear)
    4: [1, 10, 100, 1000, 10000],  # Unit Tests
    5: [50, 60, 70, 80, 90, 100],  # Test Coverage (Linear)
}

# Define which subplots should use a log scale
log_scale_indices = [0, 1, 2, 4]


# --- Call the generic function with your configurations ---
plot_boxplot_grid(
    data_list=data_list,
    subplot_titles=titles,
    figure_ylabel="Value Distribution",
    output_path=REPO_ROOT / "java_migration/figures" / "dataset_boxplots.pdf",
    tick_definitions=tick_definitions,
    log_scale_indices=log_scale_indices,
    figs_x=1,
    figs_y=6,
    figsize=(20, 6),
)
