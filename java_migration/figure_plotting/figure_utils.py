from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import MaxNLocator, MultipleLocator


from matplotlib.ticker import ScalarFormatter, MaxNLocator, LogLocator

from matplotlib.ticker import ScalarFormatter

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


def plot_counts(
    bins: list[str],
    counts: list[float | int],
    xlabel: str,
    ylabel: str,
    output_path: Path,
    figsize: tuple[int, int] = (10, 10),
):
    libs = bins
    samples = counts

    plt.figure(figsize=figsize)
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


def plot_histogram(
    data: list[float | int],
    xlabel: str,
    ylabel: str,
    output_path: Path,
    bins: int = 10,
    figsize: tuple[int, int] = (10, 10),
):
    """
    Plots a histogram for continuous numerical data in the same style.

    Args:
        data: A list of numbers (integers or floats).
        xlabel: Label for the x-axis.
        ylabel: Label for the y-axis.
        output_path: Path to save the figure.
        bins: The number of bins to use for the histogram.
        figsize: The size of the figure.
    """
    plt.figure(figsize=figsize)

    # The hist function automatically calculates frequencies and draws the bars
    plt.hist(data, bins=bins, color=PURPLE, alpha=0.9, rwidth=0.9)

    plt.xlabel(xlabel)
    plt.ylabel(ylabel)

    # Ensure y-axis has integer ticks
    plt.gca().yaxis.set_major_locator(MaxNLocator(integer=True))

    # Apply the same grid style
    plt.grid(True, which="major", axis="y", linestyle="--", linewidth=1, alpha=0.5)

    # Rotate x-axis labels if they overlap (optional, but good practice)
    plt.xticks(rotation=45, ha="right")

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.clf()
    plt.close()  # Ensure figure memory is released


def plot_histogram_grid(
    data_list: list[list[float | int]],
    subplot_titles: list[str],
    figure_xlabel: str | None,
    figure_ylabel: str | None,
    output_path: Path,
    bins: int = 15,
    figsize: tuple[int, int] = (20, 15),
    figs_x: int = 3,
    figs_y: int = 2,
):
    """
    Plots a 3x2 grid of histograms and saves it as a single file.

    Args:
        data_list: A list containing up to 6 lists of numerical data.
        subplot_titles: A list of titles corresponding to each data list.
        figure_xlabel: The shared label for the x-axis of the entire figure.
        figure_ylabel: The shared label for the y-axis of the entire figure.
        output_path: Path to save the single figure file (e.g., as a PDF or PNG).
        bins: The number of bins to use for each histogram.
        figsize: The overall size of the 3x2 grid.
    """
    # Create a 3x2 grid of subplots. constrained_layout helps prevent labels from overlapping.
    fig, axes = plt.subplots(figs_x, figs_y, figsize=figsize, constrained_layout=True)

    # Flatten the 3x2 array of axes to make it easy to iterate over
    axes = axes.flatten()

    if len(data_list) > 6:
        raise ValueError("This function supports a maximum of 6 plots for a 3x2 grid.")

    # Iterate over the axes and plot the data
    for i, ax in enumerate(axes):
        if i < len(data_list):
            # Plot histogram on the current axis `ax`
            ax.hist(data_list[i], bins=bins, color=PURPLE, alpha=0.9, rwidth=0.9)

            # Set individual subplot titles
            ax.set_title(subplot_titles[i])

            # Apply consistent styling to each subplot
            ax.yaxis.set_major_locator(MaxNLocator(integer=True))
            ax.grid(True, which="major", axis="y", linestyle="--", linewidth=1, alpha=0.5)
            ax.tick_params(axis="x", rotation=30)
        else:
            # Hide any unused subplots
            ax.set_visible(False)

    # Set shared labels for the entire figure
    if figure_xlabel:
        fig.supxlabel(figure_xlabel)
    if figure_ylabel:
        fig.supylabel(figure_ylabel)

    # Save the entire figure to a single file
    plt.savefig(output_path, dpi=300)
    plt.clf()
    plt.close(fig)

def plot_boxplot_grid(
    data_list: list[list[float | int]],
    subplot_titles: list[str],
    figure_ylabel: str | None,
    output_path: Path,
    tick_definitions: dict[int, list] | None = None,
    log_scale_indices: list[int] | None = None,
    figsize: tuple[int, int] = (20, 12),
    figs_x: int = 2,
    figs_y: int = 3,
):
    """Plots a generic, publication-quality grid of box plots."""
    fig, axes = plt.subplots(figs_x, figs_y, figsize=figsize, constrained_layout=True)
    axes = axes.flatten()

    # --- Style Dictionaries for ACM Paper Quality ---
    boxprops = dict(facecolor=PURPLE, color=PURPLE, alpha=0.9, linewidth=1.5)
    medianprops = dict(color="#ffc107", linewidth=2.5, zorder=10)
    # Outliers are now solid, small circles for clear visibility
    flierprops = dict(marker='o', markerfacecolor='k', markersize=5.5, alpha=0.35, markeredgewidth=1)
    whiskerprops = dict(linewidth=1.5)
    capprops = dict(linewidth=1.5)

    for i, ax in enumerate(axes):
        if i < len(data_list):
            # --- BUG FIX: Plot one dataset at a time ---
            # Pass the single dataset for the current subplot, wrapped in a list
            ax.boxplot(
                [data_list[i]],
                vert=True, patch_artist=True, boxprops=boxprops,
                medianprops=medianprops, flierprops=flierprops,
                whiskerprops=whiskerprops, capprops=capprops, showfliers=True,
            )

            # --- BUG FIX: Set one title at a time ---
            ax.set_title(subplot_titles[i], fontsize=22, pad=10)
            ax.set_xticks([])
            ax.grid(True, which="major", axis="y", linestyle="--", linewidth=1, alpha=0.5)
            ax.tick_params(axis='y', labelsize=20)

            if log_scale_indices and i in log_scale_indices:
                ax.set_yscale('log')
                ax.yaxis.set_major_formatter(ScalarFormatter())
                ax.tick_params(axis='y', which='minor', bottom=False, top=False)

            if tick_definitions and i in tick_definitions:
                ax.set_yticks(tick_definitions[i])
        else:
            ax.set_visible(False)

    if figure_ylabel:
        fig.supylabel(figure_ylabel, fontsize=28)

    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.clf()
    plt.close(fig)