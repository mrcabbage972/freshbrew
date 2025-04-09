import abc
import multiprocessing
import multiprocessing.context
from enum import Enum
from pathlib import Path

from pydantic import BaseModel
from tqdm import tqdm

from java_migration.eval.data_model import MigrationDatasetItem


class JobCfg(BaseModel):
    dataset_item: MigrationDatasetItem
    output_root: Path
    workspace_root: Path
    cleanup_workspace: bool = False


class JobStatus(Enum):
    FAIL = 0
    SKIP = 1
    SUCCESS = 2


class JobResult(BaseModel):
    status: JobStatus
    error: str | None = None


class Worker(abc.ABC):
    def __call__(self, job: JobCfg) -> JobResult:
        raise NotImplementedError()


def listener(progress_queue: multiprocessing.Queue, total: int):
    pbar = tqdm(total=total)
    for _ in range(total):
        progress_queue.get()
        pbar.update(1)
    pbar.close()


def worker_wrapper(worker: Worker, job_cfg: JobCfg, progress_queue: multiprocessing.Queue) -> JobResult:
    result = worker(job_cfg)
    progress_queue.put(1)
    return result


class JobRunner:
    def __init__(self, worker: Worker, concurrency: int = 1, timeout_seconds: int = 300):
        self.concurrency = concurrency
        self.timeout_seconds = timeout_seconds
        self.worker = worker

    def run(self, job_cfgs: list[JobCfg]) -> list[JobResult]:
        manager = multiprocessing.Manager()
        progress_queue = manager.Queue()
        progress_process = multiprocessing.Process(target=listener, args=(progress_queue, len(job_cfgs)))
        progress_process.start()

        with multiprocessing.Pool(processes=self.concurrency) as pool:
            task_futures = [
                pool.apply_async(worker_wrapper, (self.worker, job_cfg, progress_queue)) for job_cfg in job_cfgs
            ]
            job_results = []
            for task_futures in task_futures:
                try:
                    result = task_futures.get(timeout=self.timeout_seconds)
                    job_results.append(result)
                except multiprocessing.context.TimeoutError:
                    progress_queue.put(1)
                    job_results.append(
                        JobResult(status=JobStatus.FAIL, error=f"Job timed out after {self.timeout_seconds} seconds")
                    )
        progress_process.join()
        return job_results

    def get_result_stats(self, job_results: list[JobResult]) -> dict:
        stats = {
            "success": len(list(filter(lambda x: x.status == JobStatus.SUCCESS, job_results))),
            "fail": len(list(filter(lambda x: x.status == JobStatus.FAIL, job_results))),
            "skip": len(list(filter(lambda x: x.status == JobStatus.SKIP, job_results))),
        }
        return stats
