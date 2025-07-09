import pandas as pd
import yaml

from java_migration.utils import REPO_ROOT
from java_migration.figure_plotting.figure_utils import (
    plot_boxplot_grid,
    plot_counts,
    plot_histogram,
    plot_histogram_grid,
)

experiment_paths = [
    "data/experiments/2025-07-07/20-22-09-quirky-pasteur",
    "data/experiments/2025-07-08/14-01-20-objective-northcutt",
]
from typing import Tuple

def diff_stats(diff_file_path: str) -> Tuple[int, int]:
    """
    Parses a git diff file and returns the number of edited files
    and total lines of code added or removed.

    :param diff_file_path: Path to the git diff file.
    :return: A tuple (num_files, num_lines_edited)
    """
    files = set()
    additions = 0
    deletions = 0

    with open(diff_file_path, 'r', encoding='utf-8') as f:
        for line in f:
            # Detect new diff section and record file path
            if line.startswith('diff --git '):
                parts = line.strip().split()
                # format: diff --git a/path b/path
                if len(parts) >= 4:
                    a_path = parts[2]
                    # remove prefix a/
                    file_path = a_path[2:] if a_path.startswith('a/') else a_path
                    files.add(file_path)
            # Skip diff metadata lines
            elif line.startswith('+++ ') or line.startswith('--- '):
                continue
            # Count added and removed lines
            elif line.startswith('+'):
                additions += 1
            elif line.startswith('-'):
                deletions += 1

    num_files = len(files)
    num_lines_edited = additions + deletions
    return num_files, num_lines_edited

stats = []

for exp_path in experiment_paths:
    for entry in (REPO_ROOT / exp_path / "job_results").iterdir():
        result = yaml.safe_load((entry / "result.yaml").read_text())
        if result is None:
            continue
        if not result.get("build_result", {}).get("test_success"):
            continue
        patch_path = entry / "diff.patch"
        if not patch_path.exists():
            continue
        num_files, num_lines = diff_stats(patch_path)
        stats.append({"num_files": num_files, "num_lines": num_lines})
        #print(f"Edited files: {num_files}, Lines changed: {num_lines}")


df = pd.DataFrame(stats)


plot_histogram(
    data=df.num_lines,
    xlabel="Lines Edited",
    ylabel="Repositories",
    output_path=REPO_ROOT / "java_migration/figures" / "patch_stats.pdf",
    bins = 10,
    figsize = (10, 10),)