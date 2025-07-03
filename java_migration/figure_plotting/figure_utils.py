from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import MaxNLocator, MultipleLocator

plt.rcParams.update(
    {
        "font.size": 24,  # base font size
        "axes.titlesize": 24,
        "axes.labelsize": 24,
        "xtick.labelsize": 24,
        "ytick.labelsize": 24,
        "legend.fontsize": 24,
    }
)

PURPLE = "#8e44ad"


def plot_counts(count_dict: dict[str, int | float], xlabel: str, ylabel: str, output_path: Path, sort: bool = True):
    lib_sample_counts = []
    for lib, count in count_dict.items():
        lib_sample_counts.append((lib, count))
    if sort:
        lib_sample_counts_sorted = sorted(lib_sample_counts, key=lambda x: x[1], reverse=True)
    else:
        lib_sample_counts_sorted = lib_sample_counts
    libs = [item[0] for item in lib_sample_counts_sorted]
    samples = [item[1] for item in lib_sample_counts_sorted]

    plt.figure(figsize=(16, 10))
    x = np.arange(len(libs))
    plt.bar(x, samples, width=0.7, color=PURPLE, alpha=0.9)
    plt.xticks(x, libs, rotation=45, ha="right")
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.gca().yaxis.set_major_locator(MaxNLocator(integer=True))
    plt.gca().yaxis.set_minor_locator(MultipleLocator(1))
    plt.grid(True, which="major", axis="y", linestyle="--", linewidth=1, alpha=0.5)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.clf()
