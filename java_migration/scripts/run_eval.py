import logging
import os

import litellm
from dotenv import load_dotenv

from java_migration.eval.env_checker import EnvironmentValidator
from java_migration.eval.eval_runner import EvalRunner
from java_migration.utils import REPO_ROOT

if __name__ == "__main__":
    load_dotenv()

    validator = EnvironmentValidator()
    if not validator.validate():
        raise RuntimeError("Failed validating environment")

    litellm.vertex_project = os.getenv("DEFAULT_VERTEXAI_PROJECT", None)
    litellm.vertex_location = os.getenv("DEFAULT_VERTEXAI_LOCATION", None)

    dataset_path = REPO_ROOT / "data" / "migration_datasets" / "tiny_dataset.yaml"
    agent_cfg_path = REPO_ROOT / "java_migration" / "config" / "smol_default.yaml"

    EvalRunner().run(dataset_path, agent_cfg_path)
