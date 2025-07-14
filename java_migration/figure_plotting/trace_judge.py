import asyncio
import json
from pathlib import Path
import numpy as np
import litellm
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator, PercentFormatter
import pandas as pd
import textwrap
import yaml
from tqdm.asyncio import tqdm
from dotenv import load_dotenv
import os

load_dotenv()


# --- Local Project Imports ---
# Make sure this script can import from your project structure
# You may need to adjust the path or run as a module.
from java_migration.eval.smol_log_parser import parse_log
from java_migration.utils import REPO_ROOT

plt.rcParams.update(
    {
        "font.size": 20, "axes.titlesize": 22, "axes.labelsize": 20,
        "xtick.labelsize": 18, "ytick.labelsize": 18, "legend.fontsize": 20,
    }
)

PURPLE = "#8e44ad"

# --- 🚨 IMPORTANT: Configuration ---
CONFIG = {
    # Recommended to use a powerful model for judging
    "JUDGE_MODEL": "vertex_ai/gemini-2.5-flash",
    "MODELS": ["Gemini 2.5 Flash", "GPT 4.1", "DeepSeek-V3"],
    "EXPERIMENT_PATHS": [
        "data/experiments/2025-07-13/12-31-56-exciting-dubinsky", # gemini 2.5 flash 21
        "data/experiments/2025-07-09/smol-openai-gpt-4.1-target-jdk-17",
        "data/experiments/deepseek/home/user/java-migration-paper/data/experiments/2025-07-13/14-37-28-crazy-tharp", # deepseek 17
    ],
    "COLORS": ["#8e44ad", "#3498db", "#2ecc71"],
    "MAX_CONCURRENT_REQUESTS": 8,  # Adjust based on your API rate limits
    "OUTPUT_DIR": REPO_ROOT / "java_migration/failure_analysis",
    "STEPS_TO_ANALYZE": 10,
    "MAX_EXAMPLES": 20
}

# The failure categories the LLM judge must choose from.
FAILURE_CATEGORIES = [
    "Dependency Management Failure",
    "Build Configuration Error",
    "Java API Incompatibility",
    "Agent Behavioral Failure",
    "Root Cause Not in Final Steps",
    "Unknown",
]

# The prompt template for the LLM judge.
JUDGE_PROMPT_TEMPLATE = f"""
You are an expert Java software engineer and researcher specializing in code migration and developer tool evaluation. Your task is to analyze the final {{n_steps}} 'thought-action' steps from a failed attempt by an AI agent to migrate a Java 8 project to Java 17.

Based on the provided trace, identify the primary technical reason for the failure. Do not simply state that the agent failed or ran out of steps. Pinpoint the specific build, dependency, or code-level issue that the agent was unable to resolve.

Choose ONLY ONE of the following categories that best describes the failure:
{json.dumps(FAILURE_CATEGORIES, indent=2)}

The agent's final {{n_steps}} steps are as follows:
--- BEGIN TRACE ---
{{final_steps_trace}}
--- END TRACE ---

Provide your output in JSON format with two keys: "failure_category" and "reasoning". The reasoning should be a brief, one-sentence explanation supporting your choice.
"""


def get_failed_runs(exp_paths: list[Path]) -> list[Path]:
    """Scans experiment directories to find all failed migration runs."""
    failed_run_paths = []
    print("🔍 Searching for failed migration runs...")
    for exp_path in exp_paths:
        job_results_path = exp_path / "job_results"
        if not job_results_path.exists():
            continue
        for run_dir in job_results_path.iterdir():
            if not run_dir.is_dir():
                continue
            result_path = run_dir / "result.yaml"
            if not result_path.exists():
                continue
            try:
                result = yaml.safe_load(result_path.read_text())
                if result is None:
                    print(f"Missing result for {result_path}")
                    continue
                if not result.get("build_result", {}).get("test_success", True):
                    failed_run_paths.append(run_dir)
            except (yaml.YAMLError, IOError):
                continue
    print(f"✅ Found {len(failed_run_paths)} failed runs to analyze.")
    return failed_run_paths


def format_last_n_steps(log_path: Path, n: int) -> str | None:
    """Parses a log file and formats the last n steps into a string."""
    try:
        log = parse_log(log_path.read_text())
        if not log.steps:
            return None
        last_steps = log.steps[-n:]
        return "\n\n".join(["\n\n".join([f"{k}: {v}" for k,v in step.model_dump().items()]) for step in last_steps])
        
    except Exception:
        return None


async def get_failure_verdict(semaphore: asyncio.Semaphore, run_path: Path) -> dict:
    """Async worker to get a failure verdict from the LLM judge for a single run."""
    async with semaphore:
        log_path = run_path / "stdout.log"
        formatted_steps = format_last_n_steps(log_path, CONFIG["STEPS_TO_ANALYZE"])

        if not formatted_steps:
            return {"status": "error", "reason": "Log parsing failed", "path": str(run_path)}

        prompt = JUDGE_PROMPT_TEMPLATE.format(
            n_steps=CONFIG["STEPS_TO_ANALYZE"], final_steps_trace=formatted_steps
        )
        messages = [{"role": "user", "content": prompt}]

        try:
            response = await litellm.acompletion(
                model=CONFIG["JUDGE_MODEL"],
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.1,
            )
            verdict_json = json.loads(response.choices[0].message.content)

            # Validate the response
            if "failure_category" not in verdict_json or "reasoning" not in verdict_json:
                 return {"status": "error", "reason": "Invalid JSON schema", "path": str(run_path)}
            if verdict_json["failure_category"] not in FAILURE_CATEGORIES:
                 return {"status": "error", "reason": "Invalid failure category", "path": str(run_path)}


            return {
                "status": "success",
                "path": str(run_path),
                "category": verdict_json["failure_category"],
                "reasoning": verdict_json["reasoning"],
            }
        except Exception as e:
            return {"status": "error", "reason": str(e), "path": str(run_path)}


def plot_failure_modes(df: pd.DataFrame, output_path: Path):
    """
    Generates a horizontal bar chart showing the percentage of each failure category.
    """
    if df.empty:
        print("DataFrame is empty, skipping plot generation.")
        return

    # --- THE FIX: Calculate percentages using normalize=True ---
    category_counts = df["category"].value_counts(normalize=True).sort_values(ascending=True)

    wrapped_labels = [textwrap.fill(label, width=20) for label in category_counts.index]

    plt.figure(figsize=(10, 8))
    ax = plt.gca()

    bars = ax.barh(wrapped_labels, category_counts.values, color=PURPLE, alpha=0.9)

    # --- THE FIX: Update axis label and formatter ---
    ax.set_xlabel("Percentage of Failures")
    ax.set_title("Common Failure Modes in Java Migration")
    ax.xaxis.set_major_formatter(PercentFormatter(1.0)) # Format axis as percentage

    ax.grid(True, which="major", axis="x", linestyle="--", linewidth=1, alpha=0.5)
    ax.set_ylabel(None)

    # --- THE FIX: Format bar labels as percentages ---
    #ax.bar_label(bars, fmt='{:.1%}', padding=5, fontsize=16)
    
    # Set x-axis limit to be slightly larger than the max percentage
    if len(category_counts) > 0:
        plt.xlim(0, category_counts.max() * 1.15)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"📊 Saving percentage-based failure analysis plot to {output_path}")


def plot_grouped_failure_modes(all_results: dict[str, pd.Series], output_path: Path):
    """
    Generates a grouped horizontal bar chart comparing failure modes across experiments.
    """
    model_names = list(all_results.keys())
    
    # Find all unique categories across all models
    all_categories = set()
    for series in all_results.values():
        all_categories.update(series.index)
    sorted_categories = sorted(list(all_categories))

    # Wrap labels for readability
    wrapped_labels = [textwrap.fill(label, width=20) for label in sorted_categories]
    y = np.arange(len(sorted_categories))
    
    # --- Logic for Grouped Bars ---
    num_models = len(model_names)
    total_bar_height = 0.8
    bar_height = total_bar_height / num_models

    fig, ax = plt.subplots(figsize=(12, 10))

    for i, model_name in enumerate(model_names):
        # Get percentages for this model, filling missing categories with 0
        percentages = all_results.get(model_name, pd.Series()).reindex(sorted_categories, fill_value=0)
        
        # Calculate vertical offset for each model's bar
        offset = (i - (num_models - 1) / 2) * bar_height
        
        ax.barh(y + offset, percentages, height=bar_height, label=model_name, color=CONFIG["COLORS"][i], alpha=0.9)

    ax.set_xlabel("Percentage of Failures")
    ax.set_title("Comparison of Failure Modes Across Models")
    
    # Set y-ticks to be in the center of the groups
    ax.set_yticks(y)
    ax.set_yticklabels(wrapped_labels)
    
    ax.xaxis.set_major_formatter(PercentFormatter(1.0))
    ax.grid(True, which="major", axis="x", linestyle="--", linewidth=1, alpha=0.5)
    ax.legend(title="Model")

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"📊 Saving grouped failure analysis plot to {output_path}")



async def main():
    """Main function with caching logic."""
    print("--- Starting Failure Analysis Workflow ---")
    litellm.set_verbose = False
    output_dir = CONFIG["OUTPUT_DIR"]
    output_dir.mkdir(exist_ok=True)
    
    output_csv_path = output_dir / "failure_verdicts_all_models.csv"

    # --- THE FIX: Caching Logic ---
    if output_csv_path.exists():
        print(f"✅ Found existing results file. Loading from cache: {output_csv_path}")
        df_all = pd.read_csv(output_csv_path)
    else:
        print(f"📄 No cached results found. Running full analysis...")
        print("\n⚠️  WARNING: This will make LLM API calls which may incur costs.")
        
        all_results_for_csv = []
        for model_name, exp_path_str in zip(CONFIG["MODELS"], CONFIG["EXPERIMENT_PATHS"]):
            print(f"\n--- Analyzing Experiment: {model_name} ---")
            exp_path = REPO_ROOT / exp_path_str
            failed_runs = get_failed_runs([exp_path])
            
            if not failed_runs:
                print("No failed runs found for this experiment.")
                continue

            semaphore = asyncio.Semaphore(CONFIG["MAX_CONCURRENT_REQUESTS"])
            tasks = [get_failure_verdict(semaphore, run_path) for run_path in failed_runs]
            # if "MAX_EXAMPLES" in CONFIG:
            #     tasks = tasks[:CONFIG["MAX_EXAMPLES"]]
            
            results = await tqdm.gather(*tasks)
            
            for r in results:
                r['model'] = model_name
            all_results_for_csv.extend(results)

        if not all_results_for_csv:
            print("\nNo results were generated. Exiting.")
            return

        df_all = pd.DataFrame(all_results_for_csv)
        df_all.to_csv(output_csv_path, index=False)
        print(f"\n💾 Full analysis complete. Results saved to: {output_csv_path}")

    # --- Plotting (runs every time, using data from cache or fresh run) ---
    if df_all.empty:
        print("No data available to plot.")
        return
        
    # Filter for successful verdicts to plot
    # The .dropna subset ensures we only consider rows where a category was successfully assigned.
    df_success = df_all.dropna(subset=['category']).copy()
    df_success = df_success[df_success['status'] == 'success']

    if df_success.empty:
        print("No successful verdicts found in the data. Cannot create plot.")
        return
        
    # Prepare data for the grouped bar chart
    all_verdicts_by_model = {}
    # Use the model order from config for consistency
    for model_name in CONFIG["MODELS"]:
        model_df = df_success[df_success['model'] == model_name]
        if not model_df.empty:
            all_verdicts_by_model[model_name] = model_df['category'].value_counts(normalize=True)
            
    if not all_verdicts_by_model:
        print("No data to plot after processing. Exiting.")
        return

    plot_grouped_failure_modes(
        all_verdicts_by_model,
        output_dir / "failure_modes_comparison.pdf"
    )



if __name__ == "__main__":
    litellm.vertex_project = os.getenv("DEFAULT_VERTEXAI_PROJECT", None)
    litellm.vertex_location = os.getenv("DEFAULT_VERTEXAI_LOCATION", None)
    litellm.num_retries = 5
    asyncio.run(main())