import os
from pathlib import Path

import litellm
import typer
from dotenv import load_dotenv
from typing_extensions import Annotated

from java_migration.eval.env_checker import EnvironmentValidator
from java_migration.eval.eval_runner import EvalRunner
from java_migration.utils import REPO_ROOT

# Create a Typer application
app = typer.Typer()


@app.command()
def main(
    target_jdk_version: Annotated[
        int,
        typer.Option(
            "--jdk",
            "-j",
            help="The target JDK version. Can also be set with the TARGET_JAVA_VERSION env var.",
            # This tells typer to look for the environment variable if the --jdk flag is not provided
            envvar="TARGET_JAVA_VERSION",
        ),
    ],
    dataset_path: Annotated[
        Path,
        typer.Option(
            "--dataset",
            "-d",
            help="Path to the evaluation dataset YAML file.",
        ),
    ] = REPO_ROOT / "data" / "migration_datasets" / "tiny_dataset.yaml",
    agent_cfg_path: Annotated[
        Path | None,
        typer.Option(
            "--agent-config",
            "-a",
            help="Path to the agent configuration YAML file. If not provided, a default is used based on the JDK version.",
        ),
    ] = None,
    run_single: Annotated[
        bool,
        typer.Option(
            "--run_sungle",
            "-r",
            help="Use this to run migration on a single dataset example.",
        ),
    ] = False,
    retries: Annotated[int, typer.Option("--retries", "-r", help="Number of retries for API calls.")] = 5,
    concurrency: Annotated[int, typer.Option("--retries", "-r", help="Number of parallel workers to run.")] = 1,
):
    """
    Runs the Java migration evaluation framework.
    """
    print(f"🔬 Validating environment for JDK {target_jdk_version}...")
    validator = EnvironmentValidator()
    if not validator.validate(target_jdk_version):
        raise RuntimeError("Failed validating environment")
    print("✅ Environment validation successful.")

    # Configure litellm
    litellm.vertex_project = os.getenv("DEFAULT_VERTEXAI_PROJECT")
    litellm.vertex_location = os.getenv("DEFAULT_VERTEXAI_LOCATION")
    litellm.num_retries = retries

    # If agent config path is not provided, generate the default path
    if agent_cfg_path is None:
        agent_cfg_path = REPO_ROOT / "java_migration" / "config" / f"smol_default_{target_jdk_version}.yaml"

    print(f"📊 Using dataset: {dataset_path}")
    print(f"🤖 Using agent config: {agent_cfg_path}")

    # Run the evaluation
    max_examples = 1 if run_single else -1
    EvalRunner(concurrency=concurrency).run(dataset_path, agent_cfg_path, max_examples=max_examples)
    print("🎉 Evaluation run complete.")


if __name__ == "__main__":
    load_dotenv()
    app()
