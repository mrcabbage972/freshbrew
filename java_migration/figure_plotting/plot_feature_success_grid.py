import collections
from pathlib import Path
import yaml
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import PercentFormatter
from java_migration.eval.utils import recover_safe_repo_name
from java_migration.figure_plotting.figure_utils import get_repo_success_df

# --- Configuration ---
REPO_ROOT = Path(".")
PURPLE = "#8e44ad"

# --- NEW: Define paths and names for all models you want to compare ---
EXP_CONFIG = {
    "Gemini 2.5 Flash": "data/experiments/2025-07-13/22-05-18-sleepy-rosalind",
    "GPT-4.1": "data/experiments/2025-07-09/smol-openai-gpt-4.1-target-jdk-17",
    "DeepSeek-V3": "data/experiments/deepseek/home/user/java-migration-paper/data/experiments/2025-07-13/14-37-28-crazy-tharp",
}
# Colors for the models in the chart
COLORS = ["#8e44ad", "#3498db", "#2ecc71"]

REPO_STATS_PATH = REPO_ROOT / "data/migration_datasets/full_dataset.yaml"

# --- Matplotlib Global Style ---
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
    return {repo["repo_name"]: repo["repo_features"] for repo in data}


def load_success_data(exp_path: Path) -> dict[str, bool]:
    """Loads success/failure status for each repository in an experiment run."""
    success_map = {}
    job_results_path = exp_path / "job_results"
    if not job_results_path.exists():
        print(f"Warning: Job results path not found: {job_results_path}")
        return {}

    for entry in job_results_path.iterdir():
        if not entry.is_dir(): continue
        result_path = entry / "result.yaml"
        if not result_path.exists(): continue

        repo_name = recover_safe_repo_name(entry.name)
        result_data = yaml.safe_load(result_path.read_text())
        if not result_data:
            print("missing results data")
            continue
        is_success = result_data.get("build_result", {}).get("test_success", False)
        success_map[repo_name] = is_success

    return success_map


def plot_grouped_feature_success_grid(
    df: pd.DataFrame,
    feature_cols: list[str],
    subplot_titles: list[str],
    model_names: list[str],
    colors: list[str],
    output_path: Path,
    bins: int = 4,
):
    """
    Plots a grid of grouped bar charts, comparing model success rates against binned statistics.
    """
    if len(feature_cols) > 6:
        raise ValueError("This function supports a maximum of 6 plots.")

    figs_y = 3
    figs_x = 1
    figsize = (22, 8) # Made figure wider to accommodate legend

    # Removed constrained_layout=True to use tight_layout with rect
    fig, axes = plt.subplots(figs_x, figs_y, figsize=figsize)
    axes = axes.flatten()

    for i, feature in enumerate(feature_cols):
        ax = axes[i]

        try:
            binned_col_name = f"{feature}_bin"
            df[binned_col_name] = pd.qcut(df[feature], q=bins, duplicates="drop")
            
            grouped = df.groupby([binned_col_name, "model"])["is_success"].mean()
            rates_df = grouped.unstack(level="model")
            
            bin_labels = [f"({int(interval.left)}, {int(interval.right)}]" for interval in rates_df.index]
            num_models = len(model_names)
            num_bins = len(bin_labels)
            x = np.arange(num_bins)
            bar_width = 0.8 / num_models

            for j, model_name in enumerate(model_names):
                if model_name in rates_df.columns:
                    offset = (j - (num_models - 1) / 2) * bar_width
                    ax.bar(x + offset, rates_df[model_name].fillna(0), width=bar_width, label=model_name, color=colors[j])

            ax.set_title(subplot_titles[i])
            ax.set_xticks(x)
            ax.set_xticklabels(bin_labels, rotation=30, ha='right')
            ax.yaxis.set_major_formatter(PercentFormatter(1.0))
            ax.set_ylim(0, 1.0)
            ax.grid(True, which="major", axis="y", linestyle="--", linewidth=1, alpha=0.5)

            if i == 0:
                ax.set_ylabel("Success Rate")
            if i == 1:
                ax.set_xlabel("Binned Values")

            

        except Exception as e:
            print(f"Could not plot for feature '{feature}': {e}")
            ax.set_title(f"{subplot_titles[i]}\n(Not Plotted)")
            ax.set_visible(False)

    for j in range(i + 1, len(axes)):
        axes[j].set_visible(False)

    # --- LEGEND AND LAYOUT CHANGES ---
    # 1. Get handles and labels from one of the subplots
    handles, labels = axes[0].get_legend_handles_labels()

    
    
    # 2. Place legend to the right of the figure, vertically centered, in a single column
    wrapped_labels = [label.replace(" 2.5 Flash", "\n2.5 Flash") for label in labels]
    fig.legend(handles, wrapped_labels, loc='center left', bbox_to_anchor=(0.88, 0.5), ncol=1, title="Model")
    
    # 3. Adjust the layout to make space for the legend on the right
    # The `right` parameter is reduced from 1.0 to e.g., 0.88 to create space.
    plt.tight_layout(rect=[0, 0, 0.88, 1])

    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.clf()
    plt.close(fig)
    print(f"✅ Successfully generated grouped grid plot at: {output_path}")


if __name__ == "__main__":
    print("Loading repository statistics...")
    repo_features = load_repo_stats(REPO_STATS_PATH)

    merged_data = []
    model_names = list(EXP_CONFIG.keys())

    for model_name, exp_path_str in EXP_CONFIG.items():
        print(f"Loading success data for model: {model_name}")
        exp_path = REPO_ROOT / exp_path_str
        success_data = load_success_data(exp_path)

        for repo_name, features in repo_features.items():
            if repo_name in success_data:
                record = {
                    "model": model_name,
                    "repo_name": repo_name,
                    "is_success": success_data[repo_name],
                    **features,
                }
                merged_data.append(record)

    if not merged_data:
        print("Error: No overlapping data found. Please check your paths.")
    else:
        df = pd.DataFrame(merged_data)

        features_to_plot = [
            "number_of_external_dependencies",
            "number_of_lines_of_code",
            "number_of_unit_tests",
        ]

        subplot_titles = [
            "vs. External Dependencies",
            "vs. Lines of Code",
            "vs. Unit Tests",
        ]

        output_dir = REPO_ROOT / "java_migration" / "figures"
        output_dir.mkdir(exist_ok=True, parents=True)

        plot_grouped_feature_success_grid(
            df=df,
            feature_cols=features_to_plot,
            subplot_titles=subplot_titles,
            model_names=model_names,
            colors=COLORS,
            output_path=output_dir / "feature_success_grid.pdf"
        )