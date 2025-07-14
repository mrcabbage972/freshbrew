from pathlib import Path

import pandas as pd
import yaml

from java_migration.utils import REPO_ROOT

# --- Configuration ---
# The total number of samples you want in your final audit.
TOTAL_SAMPLE_SIZE = 30
# The output file where the sampled data will be saved.
SAMPLE_FILE = "auditing_sample.csv"
# Seed for reproducibility of the random sampling.
RANDOM_STATE = 42


def parse_yaml_file(filepath):
    """Safely parses a YAML file and returns its content."""
    try:
        with open(filepath, "r") as f:
            return yaml.safe_load(f)
    except (FileNotFoundError, yaml.YAMLError):
        # print(f"Warning: Could not read or parse {filepath}. Reason: {e}")
        return None


def process_experiment_data(exp_dirs):
    """
    Walks through experiment directories, parses result files,
    and returns a list of all migration attempt records.
    """
    all_records = []
    print("🔍 Starting to process experiment directories...")

    for exp_dir in exp_dirs:
        base_path = Path(exp_dir)
        if not base_path.is_dir():
            print(f"Warning: Directory not found, skipping: {base_path}")
            continue

        job_results_path = base_path / "job_results"
        if not job_results_path.is_dir():
            continue

        cov = parse_yaml_file(exp_dir / "cov_results.yaml")

        # Get model info from experiment.yaml at the run level
        experiment_yaml = parse_yaml_file(exp_dir / "experiment.yaml")
        model_name = experiment_yaml.get("model", "unknown") if experiment_yaml else "unknown"

        # Iterate through each repository migrated in this run
        for repo_path in job_results_path.iterdir():
            if not repo_path.is_dir():
                continue

            repo_name = repo_path.name

            # --- Parse result files ---
            result_yaml = parse_yaml_file(repo_path / "result.yaml")

            if not result_yaml:
                continue  # Skip if essential files are missing

            # --- Extract key data ---
            outcome = "success" if result_yaml.get("run_success") else "failure"

            # Find coverage for the specific repo. Note the repo name in cov.yaml has slashes.
            repo_key = repo_name.replace("_", "/", 1)  # Assumes format is owner_repo
            if cov is None:
                continue
            coverage_info = cov.get("repo_results", {}).get(repo_key, {})
            if "cov_percent_change" not in coverage_info.get("coverage", {}):
                continue

            # The 'cov_percent_change' is negative for a drop, so we invert it
            coverage_drop = coverage_info.get("coverage", {}).get("cov_percent_change", 0.0) * -100

            # Get the path to the diff file
            diff_filepath = repo_path / "diff.patch"

            all_records.append(
                {
                    "run_id": f"{exp_dir.name}/{repo_name}",
                    "model": model_name,
                    "outcome": outcome,
                    "coverage_drop_percent": round(coverage_drop, 2),
                    "diff_filepath": str(diff_filepath),
                }
            )

    print(f"Processed {len(all_records)} total migration records.")
    return all_records


def perform_stratified_sampling(df, strata_cols, n_samples):
    """
    Performs stratified sampling on a DataFrame.
    """
    # Calculate the number of samples to draw from each stratum
    strata_counts = df.groupby(strata_cols).size()
    n_strata = len(strata_counts)

    if n_strata == 0:
        print("Error: No data available to sample from after filtering.")
        return pd.DataFrame()

    print(f"\nFound {n_strata} unique strata in the filtered dataset:\n{strata_counts.unstack(fill_value=0)}")

    # Proportional allocation
    sample_proportions = strata_counts / len(df)
    n_samples_per_stratum = (sample_proportions * n_samples).round().astype(int)

    # Adjust to ensure total sample size is correct due to rounding
    diff = n_samples - n_samples_per_stratum.sum()
    if diff != 0:
        # Add or subtract the difference from the largest stratum
        if not n_samples_per_stratum.empty:
            largest_stratum = n_samples_per_stratum.idxmax()
            n_samples_per_stratum[largest_stratum] += diff

    print(
        f"\nCalculated samples per stratum for a total of {n_samples}:\n{n_samples_per_stratum.unstack(fill_value=0)}"
    )

    # Perform sampling
    sample_df = df.groupby(strata_cols, group_keys=False).apply(
        lambda x: x.sample(
            n=n_samples_per_stratum[x.name],
            random_state=RANDOM_STATE,
            replace=False,  # Cannot sample more than available
        )
        if len(x) >= n_samples_per_stratum.get(x.name, 0) and n_samples_per_stratum.get(x.name, 0) > 0
        else x.sample(len(x), random_state=RANDOM_STATE)
    )

    return sample_df


def main():
    """
    Main function to execute the sampling script.
    """
    exp_dirs = [
        "data/experiments/2025-07-09/smol-openai-gpt-4.1-target-jdk-17",
        "data/experiments/deepseek/home/user/java-migration-paper/data/experiments/2025-07-13/14-37-28-crazy-tharp",  # deepseek 17
        "data/experiments/2025-07-13/22-05-18-sleepy-rosalind",  # gemini 2.5 flash 17
    ]
    max_coverage_drop = 20

    # --- 1. Gather and Parse Data ---
    exp_dirs = [REPO_ROOT / x for x in exp_dirs]
    records = process_experiment_data(exp_dirs)
    if not records:
        print("No valid records found. Exiting.")
        return

    all_results_df = pd.DataFrame(records)

    # --- 2. Filter Data (Optional) ---
    if max_coverage_drop is not None:
        print(f"\nFiltering records to include only those with a coverage drop <= {max_coverage_drop}%...")
        initial_count = len(all_results_df)
        # We only consider drops, so filter for values >= 0 and <= max_coverage_drop
        all_results_df = all_results_df[
            (all_results_df["coverage_drop_percent"] >= 0)
            & (all_results_df["coverage_drop_percent"] <= max_coverage_drop)
        ]
        filtered_count = len(all_results_df)
        print(f"Filtered from {initial_count} to {filtered_count} records.")

    # --- 3. Perform Sampling ---
    print("\nPerforming stratified sampling...")
    strata = ["model", "outcome"]
    final_sample = perform_stratified_sampling(all_results_df, strata, TOTAL_SAMPLE_SIZE)

    # --- 4. Save the Sample ---
    if final_sample.empty:
        print("\nCould not generate a sample from the available data.")
        return

    final_sample.to_csv(SAMPLE_FILE, index=False)
    print("\n✅ Sampling complete!")
    print(f"A sample of {len(final_sample)} migration attempts has been saved to '{SAMPLE_FILE}'.")
    print("\nFinal sampled data distribution:")
    print(final_sample.groupby(["model", "outcome"]).size().unstack(fill_value=0))


if __name__ == "__main__":
    main()
