from java_migration.eval.data_model import JobCfg, JobResult
from java_migration.smol_tools import get_tools

class Worker:
    def __call__(self, job: JobCfg) -> JobResult:
        tools = get_tools(job.tools, job.workspace_dir)
        return JobResult(status=True, output="hello")