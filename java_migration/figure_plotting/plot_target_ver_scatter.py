import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches # Needed for custom legend handles
import random
from matplotlib.lines import Line2D # For custom legend elements
import matplotlib.cm as cm
from java_migration.utils import REPO_ROOT

from java_migration.figure_plotting.model_name_map import get_model_name
# --- CONFIGURATION ----------------------------------------------------------

# Define styles for the two groups (mainly for color and group label)
STYLE_WITH_DEBUG    = {'color': '#ff7f0e', 'label': 'With Self-Debug'}    # Orange

# Define a list of markers for individual models
# Ensuring enough unique markers for the number of models (e.g., 25)
MARKERS = [
    '.', ',', 'o', 'v', '^', '<', '>', 's', 'p', '*', 'h', 'H', '+', 'D', 'd',
    '|', '_', '1', '2', '3', '4', '8', 'P', 'X', 'Y'
] # List of 25 distinct markers

# --- PLOTTING -------------------------------------------------------------

def plot_data(pivoted_df):
    cmap = cm.get_cmap('viridis')
    n_models_to_plot = 25
    #data = generate_synthetic_data(n_models=n_models_to_plot)

    # Ensure we have enough markers, cycle if not (though MARKERS list is sized for 25)
    if n_models_to_plot > len(MARKERS):
        print(f"Warning: Number of models ({n_models_to_plot}) exceeds number of unique markers ({len(MARKERS)}). Markers will be recycled.")

    fig, ax = plt.subplots(1, 1, figsize=(10, 7)) # Single scatter plot, slightly wider for legend

    # Plot data points
    for i, (index, row) in enumerate(pivoted_df.iterrows()):
        model_name = index.replace("-", " ").title()

        point_color = STYLE_WITH_DEBUG['color']
        point_marker = MARKERS[i % len(MARKERS)] # Use unique marker for each model

        ax.scatter(
            100*row[("cov_guard_pass_rate", 17)],
            100*row[("cov_guard_pass_rate", 21)],
            marker=point_marker,
            color=cmap(random.uniform(0, 1)),
            s=100, # Marker size
            label=get_model_name(model_name) # Label each point with its model name for the legend
        )

    # Add the y=x line (zero gap)
    limits = [0, 100] # Assuming rates are percentages
    # Plot the line and ensure it gets a label for the legend
    ax.plot(limits, limits, '--', alpha=0.7)

    # Set labels and title (Corrected axis labels for clarity)
    ax.set_xlabel("Success Rate on Java 17 (%)", fontsize=15)
    ax.set_ylabel("Success Rate on Java 21 (%)", fontsize=15)
    #ax.set_title("Success Rate Gap by Self-Debug Capability", fontsize=25, fontweight='bold')

    # Set axis limits to be equal and cover the rate range
    #ax.set_xlim(limits)
    #ax.set_ylim(limits)
    ax.set_aspect('equal', adjustable='box') # Ensure axes are scaled equally

    # Add grid lines
    ax.grid(True, linestyle='--', alpha=0.6)

    handles, labels = ax.get_legend_handles_labels()

    model_legend = ax.legend(handles, labels, title="Models",
                             loc='center left', bbox_to_anchor=(1.02, 0.5),
                             fontsize=15, ncol=1,
                             title_fontsize=15) # Adjust ncol
    #ax.add_artist(model_legend) # Required when adding multiple legends to the same axes

    ax.tick_params(axis='x', labelsize=20, direction='out')
    ax.tick_params(axis='y', labelsize=20, direction='out')

    fig.subplots_adjust(right=0.70 if n_models_to_plot <=10 else 0.60) # Reduce right boundary to make space for legends

    plt.savefig(REPO_ROOT / "java_migration/figures" / "target_ver_scatter.pdf", dpi=300, bbox_inches="tight")
    plt.show()

