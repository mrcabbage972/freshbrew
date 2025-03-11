import pandas as pd
from java_migration.eval.smol_log_parser import parse_log
from pathlib import Path
import numpy as np
from java_migration.eval.utils import recover_safe_repo_name
import yaml
import pandas as pd
import seaborn as sns
from java_migration.utils import REPO_ROOT
import os
from collections.abc import MutableMapping
from java_migration.eval.maven_build_verifier import MavenBuildVerifier
import matplotlib.pyplot as plt
import matplotlib.cm as cm


def flatten(dictionary, parent_key="", separator="_"):
    items = []
    for key, value in dictionary.items():
        new_key = parent_key + separator + key if parent_key else key
        if isinstance(value, MutableMapping):
            items.extend(flatten(value, new_key, separator=separator).items())
        else:
            items.append((new_key, value))
    return dict(items)


def visualize_agent_trace(trace, cmap_name="viridis"):
    """
    Visualizes an agent trace using a scatter plot.

    Parameters:
        trace (list of dict): Each dict should have keys 'step' and 'status'.
                              'status' is expected to be an enum with attributes `name` and `value`.
        cmap_name (str): The name of the matplotlib colormap to use for assigning colors.
    """
    # Extract unique statuses and sort them by their enum numeric value.
    statuses = sorted({item["status"] for item in trace}, key=lambda s: s.value)
    # Map each status to a numeric y-value based on its sorted order.
    status_to_y = {status: i for i, status in enumerate(statuses)}

    # Create a colormap instance from the specified colormap.
    cmap = plt.get_cmap(cmap_name)
    n_statuses = len(statuses)
    # Generate a color for each unique status based on the colormap.
    status_colors = {status: cmap(i / n_statuses) for i, status in enumerate(statuses)}

    # Prepare data for plotting.
    steps = [item["step"] for item in trace]
    y_values = [status_to_y[item["status"]] for item in trace]
    color_list = [status_colors[item["status"]] for item in trace]

    # Create a scatter plot with larger markers for prominence.
    plt.figure(figsize=(8, 4))
    plt.scatter(steps, y_values, s=200, c=color_list, edgecolors="black")

    # Set the y-axis ticks with the status names and enum values for clarity.
    plt.yticks(list(status_to_y.values()), [f"{status.name} ({status.value})" for status in statuses])
    plt.xlabel("Step")
    plt.ylabel("Status")
    plt.title("Agent Trace Visualization")
    plt.grid(True)
    plt.show()


def get_experiment_data(experiment_path):
    exp_dirs = [Path(f.path) for f in os.scandir(experiment_path / "job_results") if f.is_dir()]
    repo_names = [recover_safe_repo_name(f.name) for f in exp_dirs]

    repo_dict = {repo_name: {} for repo_name in repo_names}

    repo_feats_path = REPO_ROOT / "data" / "repo_feats.yaml"
    with open(repo_feats_path) as fin:
        repo_feats = yaml.safe_load(fin.read())

    for exp_dir, repo_name in zip(exp_dirs, repo_names):
        if (exp_dir / "stdout.log").exists():
            repo_dict[repo_name]["agent_log"] = parse_log(open(exp_dir / "stdout.log").read())
        if (exp_dir / "result.yaml").exists():
            with open(exp_dir / "result.yaml") as fin:
                repo_dict[repo_name]["build_result"] = yaml.safe_load(fin.read())
        if repo_name in repo_feats:
            repo_dict[repo_name]["repo_feats"] = repo_feats[repo_name]

    return repo_dict


from enum import Enum


class MavenStatus(Enum):
    NO_MAVEN = 0
    COMPILE_ERROR = 1
    TESTS_STARTED = 2
    SUCCESS = 3
    DEPENDENCY_ERROR = 4
    UNKNOWN_ERROR = 5
    UNKNOWN = 6
    GOAL_ERROR = 7
    PLUGIN_RESOLVE_ERROR = 8
    INVALID_POM = 9
    SKIPPED_TESTS = 10


def step_log_maven_status(log: str):
    if "Scanning for projects" not in log:
        return MavenStatus.NO_MAVEN
    if "Non-parseable POM" in log or "Malformed POM" in log:
        return MavenStatus.INVALID_POM
    if "COMPILATION ERROR" in log:
        return MavenStatus.COMPILE_ERROR
    if "Could not resolve dependencies for project" in log:
        return MavenStatus.DEPENDENCY_ERROR
    if "Tests are skipped." in log:
        return MavenStatus.SKIPPED_TESTS
    if "BUILD SUCCESS" in log:
        return MavenStatus.SUCCESS
    if "Tests run" in log:
        return MavenStatus.TESTS_STARTED
    if "one of its dependencies could not be resolved" in log:
        return MavenStatus.PLUGIN_RESOLVE_ERROR
    if "Failed to execute goal" in log:
        return MavenStatus.GOAL_ERROR
    if "BUILD FAILURE" in log:
        return MavenStatus.UNKNOWN_ERROR
    return MavenStatus.UNKNOWN


def get_maven_logs(repo_data):
    try:
        maven_statuses = [
            {"step": idx, "status": step_log_maven_status(x.execution_logs)}
            for idx, x in enumerate(repo_data["agent_log"].steps)
            if x.execution_logs
        ]
        return [x for x in maven_statuses if x["status"] != MavenStatus.NO_MAVEN]
    except:
        return []
