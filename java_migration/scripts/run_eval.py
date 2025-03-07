import logging
from java_migration.eval.eval_runner import EvalRunner
from java_migration.utils import REPO_ROOT

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
    repo_names = [
        "mrcabbage972/springboot-jwt",
        "mrcabbage972/QLExpress",
        "mrcabbage972/hunt-admin",
        "mrcabbage972/zkui",
        "mrcabbage972/spring-microservice-ddd",
        "mrcabbage972/Bridge",
        "mrcabbage972/disunity",
        "mrcabbage972/Surus",
        "mrcabbage972/unidbg-boot-server",
        "mrcabbage972/springboot-jwt",
        "mrcabbage972/FizzBuzzEnterpriseEdition",
    ]

    agent_cfg_path = REPO_ROOT / "java_migration" / "config" / "smol_default.yaml"
    EvalRunner().run(repo_names, agent_cfg_path)
