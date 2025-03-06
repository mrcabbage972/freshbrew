import multiprocessing
from java_migration.eval.utils import safe_repo_name, generate_experiment_dir
from java_migration.eval.worker import Worker
from java_migration.eval.data_model import JobCfg, AgentConfig, JobResult
from java_migration.utils import REPO_ROOT
from pathlib import Path
import yaml


class EvalRunner:
    def __init__(self, concurrency=4) -> None:
        self.concurrency = concurrency

    def run(
        self, repo_names: list[str], agent_config_path: Path, experiment_root_dir: Path = REPO_ROOT / "data/experiments"
    ):
        agent_config = self._load_agent_config(agent_config_path)

        experiment_dir = generate_experiment_dir(experiment_root_dir)
        job_cfgs = self._get_job_configs(agent_config, experiment_dir / "repo", repo_names)

        worker = Worker()
        with multiprocessing.Pool(processes=self.concurrency) as pool:
            job_results = pool.map(worker, job_cfgs)
        self._save_job_results(job_cfgs, job_results, experiment_dir / "results")

    def _load_agent_config(self, agent_config_path: Path) -> AgentConfig:
        with open(agent_config_path, "r") as file:
            config_dict = yaml.safe_load(file)
            return AgentConfig(**config_dict)

    def _get_job_configs(self, agent_config: AgentConfig, experiment_dir: Path, repo_names: list[str]) -> list[JobCfg]:
        job_cfgs = [
            JobCfg(
                agent_config=agent_config, workspace_dir=experiment_dir / safe_repo_name(repo_name), repo_name=repo_name
            )
            for repo_name in repo_names
        ]
        return job_cfgs

    def _save_job_results(self, job_configs: list[JobCfg], job_results: list[JobResult], output_path: Path):
        output_path.mkdir(parents=True, exist_ok=True)
        for job_cfg, job_result in zip(job_configs, job_results):
            job_dict = job_result.model_dump()
            if job_result.migration_result is not None:
                job_dict["migration_result"]["output"] = [
                    x.strip() for x in job_dict["migration_result"]["output"].split("\n")
                ]
            output_file_path = output_path / f"{safe_repo_name(job_cfg.repo_name)}.yaml"
            with open(output_file_path, "w") as file:
                yaml.dump(job_dict, file)


if __name__ == "__main__":
    repo_names = ["nydiarra/springboot-jwt"]
    agent_cfg_path = "/Users/mayvic/Documents/git/java-migration-paper/java_migration/config/smol_default.yaml"
    EvalRunner().run(repo_names, agent_cfg_path)
