import multiprocessing
from java_migration.eval.utils import safe_repo_name, generate_experiment_dir
from java_migration.eval.worker import Worker
from java_migration.eval.data_model import JobCfg, AgentConfig, JobResult, EvalMetrics
from java_migration.utils import REPO_ROOT
from pathlib import Path
import yaml
import logging


logger = logging.getLogger(__name__)

class EvalRunner:
    def __init__(self, concurrency=4) -> None:
        self.concurrency = concurrency

    def run(
        self, repo_names: list[str], agent_config_path: Path, experiment_root_dir: Path = REPO_ROOT / "data/experiments"
    ):
        agent_config = self._load_agent_config(agent_config_path)

        experiment_dir = generate_experiment_dir(experiment_root_dir)
        job_cfgs = self._get_job_configs(agent_config, experiment_dir / "repo", repo_names)

        logger.info("Submitting jobs")
        worker = Worker()
        with multiprocessing.Pool(processes=self.concurrency) as pool:
            job_results = pool.map(worker, job_cfgs)
        logging.info("Computing metrics")
        metrics = self._compute_metrics(job_results)
        self._save_metrics(metrics, experiment_dir)
        self._save_job_results(job_cfgs, job_results, experiment_dir / "job_results")

    def _save_metrics(self, metrics: EvalMetrics, output_path: Path):
        output_path.mkdir(parents=True, exist_ok=True)
        with open(output_path / "metrics.yaml", "w") as fout:
            yaml.dump(metrics.model_dump(), fout)

    def _compute_metrics(self, job_results: list[JobResult]) -> EvalMetrics:
        num_build_success = 0
        num_failed_to_run = 0

        for job_result in job_results:
            if job_result.run_success:
                if job_result.migration_result.build_success:
                    num_build_success += 1
            else:
                num_failed_to_run += 1

        return EvalMetrics(
            num_build_success=num_build_success,
            num_failed_to_run=num_failed_to_run,
            num_total=len(job_results),
            build_success_rate=1.0 * num_build_success / len(job_results),
        )

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
        for job_cfg, job_result in zip(job_configs, job_results):
            job_result_dir = output_path / safe_repo_name(job_cfg.repo_name)
            job_result_dir.mkdir(parents=True, exist_ok=True)

            with open(job_result_dir / "result.yaml", "w") as fout:
                summary_dict = {"run_success": job_result.run_success, "error": job_result.error}
                if job_result.migration_result:
                    summary_dict.update({"build_success": job_result.migration_result.build_success})
                    yaml.dump(summary_dict, fout)

                    with open(job_result_dir / "stdout.log", "w") as fout:
                        fout.write(job_result.migration_result.stdout)

                    with open(job_result_dir / "diff.patch", "w") as fout:
                        fout.write(job_result.migration_result.diff)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
    repo_names = ["nydiarra/springboot-jwt"]
    agent_cfg_path = REPO_ROOT / "config" / "smol_default.yaml"
    EvalRunner().run(repo_names, agent_cfg_path)
