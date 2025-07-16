import collections
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import yaml
from matplotlib.ticker import PercentFormatter

from java_migration.eval.smol_log_parser import parse_log
from java_migration.utils import REPO_ROOT
from java_migration.figure_plotting.model_name_map import get_model_name
# --- Configuration ---
exp_result_paths = [
    "data/experiments/2025-07-13/22-05-18-sleepy-rosalind",  # gemini 2.5 flash 17
    "data/experiments/2025-07-09/smol-openai-gpt-4.1-target-jdk-17",
    "data/experiments/deepseek/home/user/java-migration-paper/data/experiments/2025-07-13/14-37-28-crazy-tharp",  # deepseek 17
 
]
models = ["Gemini 2.5 Flash", "GPT-4.1", "DeepSeek-V3"]
# --- NEW: Color palette for the models ---
COLORS = ["#8e44ad", "#3498db", "#2ecc71"]  # Purple, Blue, Green

# --- Matplotlib Global Style ---
plt.rcParams.update(
    {
        "font.size": 18,
        "axes.titlesize": 20,
        "axes.labelsize": 18,
        "xtick.labelsize": 16,
        "ytick.labelsize": 16,
        "legend.fontsize": 16,
    }
)


def get_all_run_data(exp_path: Path) -> list[tuple[int, bool]]:
    """
    Parses all job results, extracting steps and success status.
    (This function remains unchanged from the previous version)
    """
    run_data = []
    job_results_path = exp_path / "job_results"
    if not job_results_path.exists():
        return []
    all_entries = list(job_results_path.iterdir())
    for entry in all_entries:
        if not entry.is_dir():
            continue
        result_path = entry / "result.yaml"
        log_path = entry / "stdout.log"
        if not result_path.exists() or not log_path.exists():
            continue
        is_success = yaml.safe_load(result_path.read_text()).get("build_result", {}).get("test_success", False)
        try:
            log = parse_log(log_path.read_text())
            num_steps = len(log.steps)
            if num_steps > 0:
                run_data.append((num_steps, is_success))
        except Exception:
            continue
    return run_data


def plot_grouped_success_rate_chart(
    all_models_data: list[list[tuple[int, bool]]],
    model_names: list[str],
    output_path: Path,
    max_steps: int = 100,
    smoothing_alpha: float = 1.0,
    bin_strategy: str = "custom",
):
    """
    Plots a single grouped bar chart comparing success rates for multiple models.
    """
    plt.figure(figsize=(8, 8))
    ax = plt.gca()

    # --- Define bins ---
    if bin_strategy == "custom":
        bins = [1, 6, 11, 21, 41, max_steps + 1]
        bin_labels = ["1-5", "6-10", "11-20", "21-40", f"41-{max_steps}"]
    else:  # Fallback to linear
        bin_size = 10
        bins = range(1, max_steps + bin_size, bin_size)
        bin_labels = [f"{i}-{i + bin_size - 1}" for i in bins[:-1]]

    # --- Calculate rates for all models ---
    all_rates = []
    for model_data in all_models_data:
        total_counts = collections.defaultdict(int)
        success_counts = collections.defaultdict(int)

        steps_array = np.array([d[0] for d in model_data if d[0] <= max_steps])
        is_success_array = np.array([d[1] for d in model_data if d[0] <= max_steps])

        bin_indices = np.digitize(steps_array, bins=bins, right=False) - 1

        for j, bin_idx in enumerate(bin_indices):
            if 0 <= bin_idx < len(bin_labels):
                total_counts[bin_idx] += 1
                if is_success_array[j]:
                    success_counts[bin_idx] += 1

        rates = [
            (success_counts[j] + smoothing_alpha) / (total_counts[j] + 2 * smoothing_alpha)
            for j in range(len(bin_labels))
        ]
        all_rates.append(rates)

    # --- Plotting logic for grouped bars ---
    num_models = len(model_names)
    num_bins = len(bin_labels)
    x = np.arange(num_bins)
    total_bar_width = 0.8
    bar_width = total_bar_width / num_models

    for i, model_rates in enumerate(all_rates):
        # Calculate the offset for each model's bar from the center of the group
        offset = (i - (num_models - 1) / 2) * bar_width
        ax.bar(x + offset, model_rates, width=bar_width, label=model_names[i], color=COLORS[i])

    ax.set_xlabel("Number of Agent Steps", fontsize=18)
    ax.set_ylabel("Success Rate", fontsize=18)
    ax.set_xticks(x)
    ax.set_xticklabels(bin_labels, rotation=45, ha="right")
    ax.yaxis.set_major_formatter(PercentFormatter(1.0))
    ax.grid(True, which="major", axis="y", linestyle="--", linewidth=1, alpha=0.5)
    ax.legend(title="Model")

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.clf()
    plt.close()
    print(f"Generated grouped bar chart: {output_path}")


if __name__ == "__main__":
    # Suppress the detailed data loading reports for cleaner output
    print("Loading data for all models...")
    all_data = [get_all_run_data(REPO_ROOT / p) for p in exp_result_paths]
    print("Data loading complete.")

    output_dir = REPO_ROOT / "java_migration/figures"
    output_dir.mkdir(exist_ok=True)

    plot_grouped_success_rate_chart(
        all_models_data=all_data,
        model_names=models,
        output_path=output_dir / "step_success_correlation_grouped.pdf",
        smoothing_alpha=1.0,
        bin_strategy="custom",
    )
