import yaml

from java_migration.eval.smol_log_parser import parse_log
from java_migration.figure_plotting.figure_utils import plot_histogram_grid
from java_migration.utils import REPO_ROOT

exp_result_path = REPO_ROOT / "data/experiments/2025-07-07/18-20-39-stoic-feistel-2"

logs = []
for entry in (exp_result_path / "job_results").iterdir():
    result_path = entry / "result.yaml"
    result_dict = yaml.safe_load(result_path.read_text())
    if not result_dict.get("build_result", {}).get("test_success"):
        continue

    log_path = entry / "stdout.log"
    logs.append(parse_log(log_path.read_text()))

plot_histogram_grid(
    [[len(log.steps) for log in logs]],
    ["Gemini 2.0 Flash"],
    figure_xlabel="Steps",
    figure_ylabel="Repositories",
    output_path=REPO_ROOT / "java_migration/figures" / "trace_steps_hist.pdf",
    bins=10,
    figsize=(20, 12),
    figs_x=2,
    figs_y=1,
)
