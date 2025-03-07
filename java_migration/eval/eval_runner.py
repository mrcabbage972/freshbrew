import multiprocessing
from java_migration.eval.utils import safe_repo_name, generate_experiment_dir, clean_log_string
from java_migration.eval.worker import Worker
from java_migration.eval.data_model import (
    JobCfg,
    AgentConfig,
    JobResult,
    EvalMetrics,
    StageMetrics,
    MigrationDatasetItem,
)
from java_migration.utils import REPO_ROOT
from pathlib import Path
import yaml
import logging
from tqdm import tqdm

logger = logging.getLogger(__name__)


def listener(progress_queue: multiprocessing.Queue, total: int):
    pbar = tqdm(total=total)
    for _ in range(total):
        progress_queue.get()
        pbar.update(1)
    pbar.close()


def save_job_results(job_cfg: JobCfg, job_result: JobResult, output_path: Path):
    job_result_dir = output_path / safe_repo_name(job_cfg.repo_name)
    job_result_dir.mkdir(parents=True, exist_ok=True)

    with open(job_result_dir / "result.yaml", "w") as fout:
        summary_dict = {"run_success": job_result.run_success, "error": job_result.error}
        if job_result.migration_result:
            build_result_dict = job_result.migration_result.build_result.model_dump()
            build_log = build_result_dict.pop("build_log")
            summary_dict.update({"build_result": build_result_dict})
            yaml.dump(summary_dict, fout)

            with open(job_result_dir / "build.log", "w") as fout:
                fout.write(build_log)

            with open(job_result_dir / "stdout.log", "w") as fout:
                fout.write(clean_log_string(job_result.migration_result.stdout))

            with open(job_result_dir / "diff.patch", "w") as fout:
                fout.write(job_result.migration_result.diff)


def worker_wrapper(worker: Worker, job_cfg: JobCfg, results_dir: Path, progress_queue: multiprocessing.Queue):
    result = worker(job_cfg)
    progress_queue.put(1)
    save_job_results(job_cfg, result, results_dir)
    return result


class EvalRunner:
    def __init__(self, concurrency=4) -> None:
        self.concurrency = concurrency

    def run(
        self, dataset_path: Path, agent_config_path: Path, experiment_root_dir: Path = REPO_ROOT / "data/experiments"
    ):
        dataset = self._load_dataset(dataset_path)
        agent_config = self._load_agent_config(agent_config_path)

        experiment_dir = generate_experiment_dir(experiment_root_dir)
        logger.info(f"Experiment dir: {experiment_dir}")
        job_cfgs = self._get_job_configs(agent_config, experiment_dir / "repo", dataset)

        logger.info("Submitting jobs")
        job_results = self._run_jobs(job_cfgs, experiment_dir / "job_results")

        logging.info("Computing metrics")
        metrics = self._compute_metrics(job_results)
        self._save_metrics(metrics, experiment_dir)

    def _load_dataset(self, dataset_path: Path) -> list[MigrationDatasetItem]:
        with open(dataset_path, "r") as fin:
            dataset_dict = yaml.safe_load(fin)
        return [MigrationDatasetItem.model_validate(x) for x in dataset_dict]

    def _run_jobs(self, job_cfgs: list[JobCfg], results_dir: Path) -> list[JobResult]:
        worker = Worker()
        manager = multiprocessing.Manager()
        progress_queue = manager.Queue()
        progress_process = multiprocessing.Process(target=listener, args=(progress_queue, len(job_cfgs)))
        progress_process.start()
        with multiprocessing.Pool(processes=self.concurrency) as pool:
            job_results = pool.starmap(
                worker_wrapper, [(worker, job_cfg, results_dir, progress_queue) for job_cfg in job_cfgs]
            )
        progress_process.join()
        return job_results

    def _save_metrics(self, metrics: EvalMetrics, output_path: Path):
        output_path.mkdir(parents=True, exist_ok=True)
        with open(output_path / "metrics.yaml", "w") as fout:
            yaml.dump(metrics.model_dump(), fout, sort_keys=False)

    def _compute_metrics(self, job_results: list[JobResult]) -> EvalMetrics:
        num_failed_to_run = 0
        num_build_success = 0
        num_test_success = 0

        for job_result in job_results:
            if job_result.migration_result:
                if job_result.migration_result.build_result.test_success:
                    num_test_success += 1
                if job_result.migration_result.build_result.build_success:
                    num_build_success += 1
            else:
                num_failed_to_run += 1

        num_started_build = len(job_results) - num_failed_to_run

        return EvalMetrics(
            run_job=StageMetrics(started=len(job_results), succeeded=num_started_build),
            compile=StageMetrics(started=num_started_build, succeeded=num_build_success),
            test=StageMetrics(started=num_build_success, succeeded=num_test_success),
            overall=StageMetrics(started=len(job_results), succeeded=num_test_success),
        )

    def _load_agent_config(self, agent_config_path: Path) -> AgentConfig:
        with open(agent_config_path, "r") as file:
            config_dict = yaml.safe_load(file)
            return AgentConfig(**config_dict)

    def _get_job_configs(
        self, agent_config: AgentConfig, experiment_dir: Path, dataset: list[MigrationDatasetItem]
    ) -> list[JobCfg]:
        job_cfgs = [
            JobCfg(
                agent_config=agent_config,
                workspace_dir=experiment_dir / safe_repo_name(item.repo_name),
                repo_name=item.repo_name,
                commit=item.commit,
            )
            for item in dataset
        ]
        return job_cfgs
