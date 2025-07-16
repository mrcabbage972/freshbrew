import yaml

from java_migration.eval.smol_log_parser import parse_log
from java_migration.figure_plotting.figure_utils import plot_boxplot_grid
from java_migration.utils import REPO_ROOT

exp_result_paths = [
        "data/experiments/2025-07-13/22-05-18-sleepy-rosalind",  # gemini 2.5 flash 17
        "data/experiments/2025-07-09/smol-openai-gpt-4.1-target-jdk-17",
        "data/experiments/deepseek/home/user/java-migration-paper/data/experiments/2025-07-13/14-37-28-crazy-tharp",  # deepseek 17
   
]

models = ["Gemini 2.5 Flash", "GPT-4.1", "DeepSeek-V3"]


def get_logs(exp_result_path):
    logs = []
    for entry in (exp_result_path / "job_results").iterdir():
        result_path = entry / "result.yaml"
        result_dict = yaml.safe_load(result_path.read_text())
        if result_dict is None:
            print(f"Missing result for {result_path}")
            continue
        if not result_dict.get("build_result", {}).get("test_success"):
            continue

        log_path = entry / "stdout.log"
        logs.append(parse_log(log_path.read_text()))
    return logs


all_logs = []
for p in exp_result_paths:
    all_logs.append(get_logs(REPO_ROOT / p))

# plot_histogram_grid(
#     [[len(log.steps) for log in logs] for logs in all_logs],
#     models,
#     figure_xlabel="Steps",
#     figure_ylabel="Repositories",
#     output_path=REPO_ROOT / "java_migration/figures" / "trace_steps_hist.pdf",
#     bins=10,
#     figsize=(20, 12),
#     figs_x=2,
#     figs_y=1,
# )

num_toks = [[log.steps[-1].meta.input_tokens // 1000 for log in logs] for logs in all_logs]
num_steps = [[len(log.steps) for log in logs] for logs in all_logs]


# plot_histogram_grid(
#     num_toks,
#     models,
#     figure_xlabel="Tokens (thousands)",
#     figure_ylabel="Repositories",
#     output_path=REPO_ROOT / "java_migration/figures" / "trace_tokens_hist.pdf",
#     bins=10,
#     figsize=(20, 12),
#     figs_x=2,
#     figs_y=1,
# )


plot_boxplot_grid(
    data_list=num_steps,  # type: ignore
    subplot_titles=models,
    figure_ylabel="Steps",
    output_path=REPO_ROOT / "java_migration/figures" / "step_boxplots.pdf",
    figs_x=1,
    figs_y=3,
    figsize=(8, 6),
)

plot_boxplot_grid(
    data_list=num_toks,
    subplot_titles=models,
    figure_ylabel="Tokens (thousands)",
    output_path=REPO_ROOT / "java_migration/figures" / "token_boxplots.pdf",
    figs_x=1,
    figs_y=3,
    figsize=(8, 6),
)
