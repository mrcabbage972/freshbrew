import pandas as pd
import yaml

from java_migration.utils import REPO_ROOT

experiment_paths = [
    "data/experiments/2025-07-07/20-22-09-quirky-pasteur",
    "data/experiments/2025-07-08/14-01-20-objective-northcutt",
]

exp_results = []
for experiment_path in experiment_paths:
    full_experiment_path = REPO_ROOT / experiment_path
    exp_info = yaml.safe_load((full_experiment_path / "experiment.yaml").read_text())
    metrics = yaml.safe_load((full_experiment_path / "metrics.yaml").read_text())
    cov = yaml.safe_load((full_experiment_path / "cov_results.yaml").read_text())
    compile_success_rate = 1.0 * metrics["compile"]["succeeded"] / metrics["compile"]["started"]
    test_success_rate = 1.0 * metrics["test"]["succeeded"] / metrics["compile"]["started"]

    num_success = len([x["status"] for x in cov["repo_results"].values() if x["status"] == "JobStatus.SUCCESS" and x["coverage"]["cov_guard_pass"] is True])
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


# --- LaTeX Generation ---
latex_string = r"""
\begin{table*}[htbp]
\centering
\caption{Performance on Migration}
\begin{tabular}{
    l    
    c c     
    > {\columncolor{HighlightGray}}c    
    c c 
    > {\columncolor{HighlightGray}}c}
\toprule
\textbf{Model} & \multicolumn{3}{c}{\textbf{JDK 17 Success Rate}} & \multicolumn{3}{c}{\textbf{JDK 21 Success Rate}} \\
\cmidrule(lr){2-4} \cmidrule(lr){5-7}
& \textbf{Compilation} & \textbf{Tests} & \textbf{Cov Guard} & \textbf{Compilation} & \textbf{Tests} & \textbf{Cov Guard}\\
\midrule
"""

# Dynamically create a row for each model in the DataFrame
for index, row in pivoted_df.iterrows():
    # Format model name (e.g., 'gemini-2.0-flash' -> 'Gemini 2.0 Flash')
    model_name = index.replace("-", " ").title()  # type: ignore

    # Format rates as percentages with one decimal place
    rates_percent = [f"{val * 100:.1f}\\%" for val in row]

    # Join all parts into a single table row line
    latex_string += f"{model_name} & " + " & ".join(rates_percent) + r" \\" + "\n"

# Add the final part of the table
latex_string += r"""\bottomrule
\end{tabular}
\label{tab:model_performance}
\end{table*}"""

print(latex_string)
