import collections
from pathlib import Path
import yaml
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import PercentFormatter
from java_migration.eval.smol_log_parser import parse_log
from java_migration.eval.utils import recover_safe_repo_name


# Assuming figure_utils.py is in a reachable path
# and REPO_ROOT is defined, similar to the example script.
# from your_project.figure_utils import PURPLE
# from your_project.utils import REPO_ROOT

# --- Configuration ---

# Define a placeholder for the project's root directory.
# In your project, you'd likely have a shared constant for this.
REPO_ROOT = Path(".")
PURPLE = "#8e44ad"

# Path to the YAML file containing repository features.
# Please update this path to match your file's location.
REPO_STATS_PATH = REPO_ROOT / "data/migration_datasets/full_dataset.yaml"

# Path to the experiment results for a single model.
# We'll use this model's success data for the y-axis.
# Please update this to a valid experiment path.
EXP_RESULT_PATH = REPO_ROOT / "data/experiments/2025-07-13/22-05-18-sleepy-rosalind"

# --- Matplotlib Global Style (from your example) ---
plt.rcParams.update(
    {
        "font.size": 24,
        "axes.titlesize": 22,
        "axes.labelsize": 22,
        "xtick.labelsize": 18,
        "ytick.labelsize": 18,
        "legend.fontsize": 20,
    }
)


def load_repo_stats(yaml_path: Path) -> dict[str, dict]:
    """Loads repository features from the YAML file into a dictionary keyed by repo_name."""
    if not yaml_path.exists():
        raise FileNotFoundError(f"Repository stats file not found at: {yaml_path}")
    data = yaml.safe_load(yaml_path.read_text())
    return {repo['repo_name']: repo['repo_features'] for repo in data}


def load_success_data(exp_path: Path) -> dict[str, bool]:
    """Loads success/failure status for each repository in an experiment run."""
    success_map = {}
    job_results_path = exp_path / "job_results"
    if not job_results_path.exists():
        print(f"Warning: Job results path not found: {job_results_path}")
        return {}

    for entry in job_results_path.iterdir():
        if not entry.is_dir():
            continue
        result_path = entry / "result.yaml"
        if not result_path.exists():
            continue
        
        # The directory name is the repo name, but with '/' replaced by '-'.
        repo_name = recover_safe_repo_name(entry.name)
        result_data = yaml.safe_load(result_path.read_text())
        if not result_data:
            print(f"result missing")
            continue
        is_success = result_data.get("build_result", {}).get("test_success", False)
        success_map[repo_name] = is_success
        
    return success_map


def plot_feature_success_grid(
    df: pd.DataFrame,
    feature_cols: list[str],
    subplot_titles: list[str],
    output_path: Path,
    bins: int = 4, # Use 4 bins for quartiles
):
    """
    Plots a grid showing success rate against binned dataset statistics.

    Args:
        df: DataFrame containing boolean 'is_success' and numerical feature columns.
        feature_cols: List of column names to plot.
        subplot_titles: List of titles for each subplot.
        output_path: Path to save the figure.
        bins: Number of quantile-based bins to create.
    """
    if len(feature_cols) > 6:
        raise ValueError("This function supports a maximum of 6 plots.")

    figs_y = 3
    figs_x = int(np.ceil(len(feature_cols) / figs_y))
    figsize = (22, 6 * figs_x)

    fig, axes = plt.subplots(figs_x, figs_y, figsize=figsize, constrained_layout=True)
    axes = axes.flatten()

    for i, feature in enumerate(feature_cols):
        ax = axes[i]

        try:
            # Create quantile-based bins directly. This returns a Series of Intervals.
            binned_series = pd.qcut(df[feature], q=bins, duplicates='drop')

            # Group the DataFrame by these interval bins and calculate the success rate.
            binned_success = df.groupby(binned_series)['is_success'].mean()

            # Create clean labels for the x-axis directly from the result's index.
            bin_labels = [f"({int(interval.left)}, {int(interval.right)}]" for interval in binned_success.index]

            # Plotting
            ax.bar(bin_labels, binned_success.values, width=0.7, color=PURPLE, alpha=0.9)
            ax.set_title(subplot_titles[i])
            ax.yaxis.set_major_formatter(PercentFormatter(1.0))
            ax.set_ylim(0, 1.0)
            ax.tick_params(axis='x', rotation=30)#, ha='right')
            ax.grid(True, which="major", axis="y", linestyle="--", linewidth=1, alpha=0.5)

        except Exception as e:
            print(f"Could not plot for feature '{feature}': {e}")
            ax.set_title(f"{subplot_titles[i]}\n(Not Plotted)")
            ax.set_visible(False)

    # Hide any unused subplots
    for j in range(i + 1, len(axes)):
        axes[j].set_visible(False)

    fig.supylabel("Migration Success Rate", fontsize=28)

    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.clf()
    plt.close(fig)
    print(f"✅ Successfully generated grid plot at: {output_path}")


if __name__ == "__main__":
    # --- 1. Load Data ---
    print("Loading repository statistics and experiment success data...")
    repo_features = load_repo_stats(REPO_STATS_PATH)
    success_data = load_success_data(EXP_RESULT_PATH)

    # --- 2. Merge Data ---
    merged_data = []
    for repo_name, features in repo_features.items():
        if repo_name in success_data:
            record = {
                'repo_name': repo_name,
                'is_success': success_data[repo_name],
                **features  # Unpack all features into the record
            }
            merged_data.append(record)

    if not merged_data:
        print("Error: No overlapping data found between repo stats and success logs. Please check your paths.")
    else:
        # Create a pandas DataFrame for easy manipulation
        df = pd.DataFrame(merged_data)

        # --- 3. Plotting ---
        features_to_plot = [
            "number_of_external_dependencies",
            "number_of_java_files",
            "number_of_lines_of_code",
            "number_of_modules",
            "number_of_unit_tests",
        ]
        
        subplot_titles = [
            "vs. External Dependencies",
            "vs. Java Files",
            "vs. Lines of Code",
            "vs. Modules",
            "vs. Unit Tests",
        ]

        output_dir = REPO_ROOT / "java_migration/figures"
        output_dir.mkdir(exist_ok=True)
        
        plot_feature_success_grid(
            df=df,
            feature_cols=features_to_plot,
            subplot_titles=subplot_titles,
            output_path=output_dir / "feature_success_grid.pdf"
        )