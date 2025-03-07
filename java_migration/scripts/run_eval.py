import logging
from java_migration.eval.eval_runner import EvalRunner
from java_migration.utils import REPO_ROOT

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

    dataset_path = REPO_ROOT / "data" / "migration_datasets" / "tiny_dataset.yaml"
    agent_cfg_path = REPO_ROOT / "java_migration" / "config" / "smol_default.yaml"

    EvalRunner().run(dataset_path, agent_cfg_path)
