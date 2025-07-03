import pandas as pd
import yaml

from java_migration.figure_plotting.figure_utils import plot_histogram, plot_histogram_grid
from java_migration.utils import REPO_ROOT

def plot_deps_per_repo(df, output_path):
    plot_histogram(df["number_of_external_dependencies"], "External Dependencies", "Repositories", output_path, bins=5)
   

def plot_num_files(df, output_path):
     plot_histogram(df["number_of_java_files"], "External Dependencies", "Repositories", output_path, bins=5)

dataset_path = REPO_ROOT / "data/migration_datasets/full_dataset.yaml"

with open(dataset_path) as fin:
    ds = yaml.safe_load(fin)

all_repo_features = [x["repo_features"] for x in ds]
df = pd.DataFrame(all_repo_features)

#plot_deps_per_repo(df, REPO_ROOT / "java_migration/figures/deps_per_repo.pdf")
#plot_num_files(df, REPO_ROOT / "java_migration/figures/files_per_repo.pdf")

columns_to_plot = {
    "number_of_external_dependencies": "External_dependencies",
    "number_of_java_files": "Java Files",
    "number_of_lines_of_code": "Lines of Code",
    "number_of_modules": "Modules",
    "number_of_unit_tests": "Unit Tests"}

data_list = [df[col].tolist() for col in columns_to_plot.keys()]
titles = list(columns_to_plot.values())

plot_histogram_grid(
    data_list,
    titles,
    figure_xlabel=None,
    figure_ylabel="Repositories",
    output_path=REPO_ROOT / "java_migration/figures" / "dataset_stats.pdf",
    bins=5,
    figsize= (20, 15))
