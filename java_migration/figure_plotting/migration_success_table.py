import pandas as pd
import yaml

from java_migration.utils import REPO_ROOT
from java_migration.figure_plotting.plot_target_ver_scatter import plot_data
from java_migration.figure_plotting.model_name_map import get_model_name


experiment_paths = [
    # "data/experiments/2025-07-07/20-22-09-quirky-pasteur", # gemini 2.0 flash
    # "data/experiments/2025-07-08/14-01-20-objective-northcutt", # gemini 2.0 flash
    # "data/experiments/2025-07-09/02-45-46-intelligent-benz", # gemini-2.5-flash - high temp
    # "data/experiments/2025-07-08/21-40-26-laughing-cerf", # gemini-2.5-flash - high temp
    #"data/experiments/2025-07-09/smol-openai-gpt-4.1-target-jdk-21",
    #"data/experiments/2025-07-09/smol-openai-gpt-4.1-target-jdk-17",
    "data/experiments/2025-07-09/smol-openai-o3-mini-target-jdk-21",
    "data/experiments/2025-07-09/smol-openai-o3-mini-target-jdk-17",
    # "data/experiments/2025-07-09/smol-openai-gpt-4o-target-jdk-17",
    "data/experiments/check_yanqi/smol-openai-gpt-4.1-target-jdk-17_Temperature0.2",
    "data/experiments/check_yanqi/smol-openai-gpt-4.1-target-jdk-21_Temperature0.2",
    "data/experiments/check_yanqi/smol-openai-gpt-4o-target-jdk-17-Temperature0.2",
    "data/experiments/check_yanqi/smol-openai-gpt-4o-target-jdk-21-Temperature0.2",
    "data/experiments/deepseek/home/user/java-migration-paper/data/experiments/2025-07-13/14-37-28-crazy-tharp",  # deepseek 17
    "data/experiments/deepseek/home/user/java-migration-paper/data/experiments/2025-07-13/16-48-59-nifty-bhaskara",  # 21
    "data/experiments/2025-07-13/12-31-56-exciting-dubinsky",  # gemini 2.5 flash 21
    "data/experiments/2025-07-13/22-05-18-sleepy-rosalind",  # gemini 2.5 flash 17
    "data/experiments/2025-07-15/00-27-00-nifty-wozniak",  # qwen 21"
    "data/experiments/2025-07-14/19-32-21-stoic-diffie",  # qwen 17
    "data/experiments/2025-07-15/11-41-38-optimistic-hertz",  # arcee 17
    "data/experiments/2025-07-15/16-38-59-frosty-shaw",  # arcee 21
]


exp_results = []
for experiment_path in experiment_paths:
    full_experiment_path = REPO_ROOT / experiment_path
    exp_info = yaml.safe_load((full_experiment_path / "experiment.yaml").read_text())
    metrics = yaml.safe_load((full_experiment_path / "metrics.yaml").read_text())
    cov = yaml.safe_load((full_experiment_path / "cov_results.yaml").read_text())
    compile_success_rate = 1.0 * metrics["compile"]["succeeded"] / metrics["compile"]["started"]
    test_success_rate = 1.0 * metrics["test"]["succeeded"] / metrics["compile"]["started"]

    num_success = len(
        [
            x["status"]
            for x in cov["repo_results"].values()
            if x.get("coverage", {}).get("cov_guard_pass", "False") is True
        ]
    )
    cov_guard_pass_rate = 1.0 * num_success / (metrics["compile"]["started"] - cov["job_fails"])

    exp_results.append(
        {
            "java_version": exp_info["target_jdk_version"],
            "model": exp_info["model"],
            "cov_guard_pass_rate": cov_guard_pass_rate,
            "compile_success_rate": compile_success_rate,
            "test_success_rate": test_success_rate,
        }
    )

df = pd.DataFrame(exp_results)

pivoted_df = df.pivot(
    index="model", columns="java_version", values=["cov_guard_pass_rate", "compile_success_rate", "test_success_rate"]
)


pivoted_df = pivoted_df[
    [
        ("compile_success_rate", 17),
        ("test_success_rate", 17),
        ("cov_guard_pass_rate", 17),
        ("compile_success_rate", 21),
        ("test_success_rate", 21),
        ("cov_guard_pass_rate", 21),
    ]
]

plot_data(pivoted_df)


# --- LaTeX Generation ---
latex_string = r"""
\begin{table*}[htbp]
\centering
\begin{tabular}{
    l    
    c c     
    > {\columncolor{HighlightGray}}c    
    c c 
    > {\columncolor{HighlightGray}}c}
\toprule
\textbf{Model} & \multicolumn{3}{c}{\textbf{JDK 17 Success Rate}} & \multicolumn{3}{c}{\textbf{JDK 21 Success Rate}} \\
\cmidrule(lr){2-4} \cmidrule(lr){5-7}
& \textbf{Compilation} & \textbf{Tests} & \textbf{Overall Success Rate} & \textbf{Compilation} & \textbf{Tests} & \textbf{Overall Success Rate}\\
\midrule
"""

# Dynamically create a row for each model in the DataFrame
for index, row in pivoted_df.iterrows():
    # Format model name (e.g., 'gemini-2.0-flash' -> 'Gemini 2.0 Flash')
    model_name = get_model_name(index.replace("-", " ").title())  # type: ignore

    # Format rates as percentages with one decimal place
    rates_percent = [f"{val * 100:.1f}\\%" for val in row]

    # Join all parts into a single table row line
    latex_string += f"{model_name} & " + " & ".join(rates_percent) + r" \\" + "\n"

# Add the final part of the table
latex_string += r"""\bottomrule
\end{tabular}
\caption{Performance on Migration}
\label{tab:model_performance}
\end{table*}"""

print(latex_string)
