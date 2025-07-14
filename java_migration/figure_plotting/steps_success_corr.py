import collections
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import yaml
from matplotlib.ticker import PercentFormatter

from java_migration.eval.smol_log_parser import parse_log
from java_migration.utils import REPO_ROOT

# --- Configuration ---
exp_result_paths = [
    "data/experiments/2025-07-07/18-20-39-stoic-feistel-2",
    "data/experiments/2025-07-09/smol-openai-gpt-4.1-target-jdk-17",
    "data/experiments/2025-07-09/smol-openai-o3-mini-target-jdk-17",
]
models = ["Gemini 2.0 Flash", "GPT 4.1", "O3-mini"]
PURPLE = "#8e44ad"

# --- Matplotlib Global Style ---
plt.rcParams.update(
    {
        "font.size": 20,
        "axes.titlesize": 22,
        "axes.labelsize": 20,
        "xtick.labelsize": 18,
        "ytick.labelsize": 18,
        "legend.fontsize": 20,
    }
)


def get_all_run_data(exp_path: Path) -> list[tuple[int, bool]]:
    """
    Parses all job results, extracting steps and success status.
    Includes a detailed report on excluded runs.
    """
    # (This function remains unchanged from the previous version)
    run_data = []
    job_results_path = exp_path / "job_results"
    if not job_results_path.exists():
        print(f"Warning: Directory not found: {job_results_path}")
        return []

    total_found = 0
    missing_files = 0
    parse_errors = 0
    zero_step_runs = 0
    all_entries = list(job_results_path.iterdir())
    total_found = len([entry for entry in all_entries if entry.is_dir()])

    for entry in all_entries:
        if not entry.is_dir():
            continue
        result_path = entry / "result.yaml"
        log_path = entry / "stdout.log"
        if not result_path.exists() or not log_path.exists():
            missing_files += 1
            continue
        is_success = yaml.safe_load(result_path.read_text()).get("build_result", {}).get("test_success", False)
        try:
            log = parse_log(log_path.read_text())
            num_steps = len(log.steps)
            if num_steps == 0:
                zero_step_runs += 1
                continue
            run_data.append((num_steps, is_success))
        except Exception:
            parse_errors += 1
            continue

    print(f"--- Data Loading Report for: {exp_path.name} ---")
    print(f"Found {total_found} total repository runs.")
    print(f"  - Excluded {missing_files:<4} due to missing result/log files.")
    print(f"  - Excluded {parse_errors:<4} due to log parsing errors.")
    print(f"  - Excluded {zero_step_runs:<4} because they had zero steps.")
    print(f"-> Returning {len(run_data)} valid data points for plotting.")
    print("-" * 50)
    return run_data


def plot_binned_success_rate_grid(
    all_models_data: list[list[tuple[int, bool]]],
    subplot_titles: list[str],
    output_path: Path,
    max_steps: int = 100,
    smoothing_alpha: float = 1.0,
    bin_strategy: str = "custom",
):
    """
    Plots success rate vs. agent steps, with multiple binning strategies.

    Args:
        bin_strategy: 'linear', 'log', or 'custom'.
    """
    figs_y = len(all_models_data)
    fig, axes = plt.subplots(1, figs_y, figsize=(8 * figs_y, 7), constrained_layout=True)
    if figs_y == 1:
        axes = [axes]

    # --- REFACTORED: Select binning strategy ---
    if bin_strategy == "custom":
        bins = [1, 6, 11, 21, 41, max_steps + 1]
        bin_labels = ["1-5", "6-10", "11-20", "21-40", f"41-{max_steps}"]
    elif bin_strategy == "log":
        bins = [1, 2, 4, 8, 16, 32, 64, max_steps + 1]
        bin_labels = [f"{bins[i]}-{bins[i + 1] - 1}" for i in range(len(bins) - 2)]
        bin_labels.insert(0, "1")
        bin_labels.append(f"{bins[-2]}-{max_steps}")
    else:  # Default to linear
        bin_size = 10
        bins = range(1, max_steps + bin_size, bin_size)
        bin_labels = [f"{i}-{i + bin_size - 1}" for i in bins[:-1]]

    for i, ax in enumerate(axes):
        if i >= len(all_models_data):
            ax.set_visible(False)
            continue

        model_data = all_models_data[i]
        total_counts = collections.defaultdict(int)
        success_counts = collections.defaultdict(int)

        steps_array = np.array([d[0] for d in model_data if d[0] <= max_steps])
        is_success_array = np.array([d[1] for d in model_data if d[0] <= max_steps])

        # Use numpy.digitize for efficient, generalized binning
        bin_indices = np.digitize(steps_array, bins=bins, right=False) - 1

        for j, bin_idx in enumerate(bin_indices):
            if bin_idx < 0 or bin_idx >= len(bin_labels):
                continue
            total_counts[bin_idx] += 1
            if is_success_array[j]:
                success_counts[bin_idx] += 1

        rates = [
            (success_counts[j] + smoothing_alpha) / (total_counts[j] + 2 * smoothing_alpha)
            for j in range(len(bin_labels))
        ]

        x = np.arange(len(bin_labels))
        ax.bar(x, rates, width=0.8, color=PURPLE, alpha=0.9)

        ax.set_title(subplot_titles[i])
        ax.set_xticks(x)
        ax.set_xticklabels(bin_labels, rotation=45, ha="right")
        ax.set_ylim(0, 1.05)
        ax.yaxis.set_major_formatter(PercentFormatter(1.0))
        ax.grid(True, which="major", axis="y", linestyle="--", linewidth=1, alpha=0.5)

        for idx, rect in enumerate(ax.patches):
            N = total_counts[idx]
            if N > 0:
                ax.text(
                    rect.get_x() + rect.get_width() / 2.0,
                    rect.get_height() + 0.02,
                    f"N={N}",
                    ha="center",
                    va="bottom",
                    fontsize=12,
                )

    fig.supxlabel("Number of Agent Steps (Binned)", fontsize=22)
    fig.supylabel("Smoothed Success Rate", fontsize=22)
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.clf()
    plt.close(fig)
    print(f"Generated plot: {output_path}")


if __name__ == "__main__":
    all_data = []
    for p in exp_result_paths:
        all_data.append(get_all_run_data(REPO_ROOT / p))

    output_dir = REPO_ROOT / "java_migration/figures"
    output_dir.mkdir(exist_ok=True)

    # Generate the plot with the new custom bins
    plot_binned_success_rate_grid(
        all_models_data=all_data,
        subplot_titles=models,
        output_path=output_dir / "step_success_correlation_custom_bins.pdf",
        smoothing_alpha=1.0,
        bin_strategy="custom",
    )
