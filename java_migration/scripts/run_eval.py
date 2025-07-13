import os

import litellm
from dotenv import load_dotenv

from java_migration.eval.env_checker import EnvironmentValidator
from java_migration.eval.eval_runner import EvalRunner
from java_migration.utils import REPO_ROOT

if __name__ == "__main__":
    load_dotenv()
    target_jdk_version = os.environ["TARGET_JAVA_VERSION"]

    validator = EnvironmentValidator()
    if not validator.validate(int(target_jdk_version)):
        raise RuntimeError("Failed validating environment")

    litellm.vertex_project = os.getenv("DEFAULT_VERTEXAI_PROJECT", None)
    litellm.vertex_location = os.getenv("DEFAULT_VERTEXAI_LOCATION", None)
    litellm.num_retries = 5

    dataset_path = REPO_ROOT / "data" / "migration_datasets" / "full_dataset.yaml"
    agent_cfg_path = REPO_ROOT / "java_migration" / "config" / f"smol_default_{target_jdk_version}.yaml"

    EvalRunner().run(dataset_path, agent_cfg_path)
