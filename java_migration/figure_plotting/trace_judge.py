import asyncio
import json
from pathlib import Path

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
        "font.size": 24,  # base font size
        "axes.titlesize": 24,
        "axes.labelsize": 24,
        "xtick.labelsize": 24,
        "ytick.labelsize": 24,
        "legend.fontsize": 24,
    }
)

PURPLE = "#8e44ad"

# --- 🚨 IMPORTANT: Configuration ---
CONFIG = {
    # Recommended to use a powerful model for judging
    "JUDGE_MODEL": "vertex_ai/gemini-2.5-pro",
    "EXPERIMENT_PATHS": [
        "data/experiments/2025-07-09/smol-openai-gpt-4.1-target-jdk-17",
    ],
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
    Generates a publication-quality horizontal bar chart with wrapped labels.
    """
    if df.empty:
        print("DataFrame is empty, skipping plot generation.")
        return

    category_counts = df["category"].value_counts().sort_values(ascending=True)

    # --- THE FIX: Wrap long labels before plotting ---
    # Create a new list of wrapped labels. Adjust width as needed.
    wrapped_labels = [textwrap.fill(label, width=20) for label in category_counts.index]

    # Adjust figure size for better vertical spacing with wrapped labels
    plt.figure(figsize=(10, 8))
    ax = plt.gca()

    # Use the wrapped labels for the y-axis
    bars = ax.barh(wrapped_labels, category_counts.values, color=PURPLE, alpha=0.9)

    ax.set_xlabel("Number of Failures")
    ax.set_title("Common Failure Modes in Java Migration")
    
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.grid(True, which="major", axis="x", linestyle="--", linewidth=1, alpha=0.5)
    ax.set_ylabel(None)
    #ax.bar_label(bars, padding=5, fontsize=16)
    
    # Use tight_layout and bbox_inches to ensure everything fits
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    
    plt.close()
    print(f"📊 Saving final failure analysis plot to {output_path}")


async def main():
    """Main async function to orchestrate the analysis."""
    print("--- Starting Failure Analysis Workflow ---")
    
    # Ensure a non-verbose mode for cleaner output
    litellm.set_verbose=False
    
    CONFIG["OUTPUT_DIR"].mkdir(exist_ok=True)
    output_csv_path = CONFIG["OUTPUT_DIR"] / "failure_verdicts.csv"
   
    if not output_csv_path.exists():
        print("Running judge")

        # --- 🚨 Cost Warning ---
        print("\n⚠️  WARNING: This script will make LLM API calls which may incur costs.")
        
        exp_paths = [REPO_ROOT / p for p in CONFIG["EXPERIMENT_PATHS"]]
        failed_runs = get_failed_runs(exp_paths)
        
        if not failed_runs:
            print("No failed runs found. Exiting.")
            return

        semaphore = asyncio.Semaphore(CONFIG["MAX_CONCURRENT_REQUESTS"])
        tasks = [get_failure_verdict(semaphore, run_path) for run_path in failed_runs]
        if "MAX_EXAMPLES" in CONFIG:
            tasks = tasks[:CONFIG["MAX_EXAMPLES"]]
        
        print(f"\n🤖 Sending {len(tasks)} failed traces to LLM judge ('{CONFIG['JUDGE_MODEL']}')...")
        results = await tqdm.gather(*tasks)

        # --- Process and save results ---
        successes = [r for r in results if r["status"] == "success"]
        errors = [r for r in results if r["status"] == "error"]

        print(f"\n--- Analysis Complete ---")
        print(f"✅ Successfully analyzed: {len(successes)} traces")
        print(f"❌ Failed to analyze:    {len(errors)} traces")
        if errors:
            print("A summary of errors can be found in the output CSV.")

        if not successes:
            print("No successful verdicts to analyze. Exiting.")
            return

        df = pd.DataFrame(successes)
        
        # Add errors to the CSV for later inspection
        if errors:
            error_df = pd.DataFrame(errors)
            df = pd.concat([df, error_df], ignore_index=True)
            
        df.to_csv(output_csv_path, index=False)
        print(f"\n💾 Full results saved to: {output_csv_path}")
    else:
        df = pd.read_csv(output_csv_path)
        print("Reusing results")

    plot_failure_modes(df[df['status'] == 'success'], CONFIG["OUTPUT_DIR"] / "failure_modes.pdf")


if __name__ == "__main__":
    litellm.vertex_project = os.getenv("DEFAULT_VERTEXAI_PROJECT", None)
    litellm.vertex_location = os.getenv("DEFAULT_VERTEXAI_LOCATION", None)
    litellm.num_retries = 5
    asyncio.run(main())