from java_migration.eval.data_model import JobCfg, JobResult
from java_migration.smol_tools import get_tools
from git import Repo
import logging
import tempfile
import shutil
from pathlib import Path
import io
import contextlib
from smolagents import CodeAgent
from smolagents.models import LiteLLMModel
from java_migration.eval.utils import create_git_patch

logger = logging.getLogger(__name__)


class Worker:
    def __call__(self, job: JobCfg) -> JobResult:
        try:
            logger.info(f"Processing job {job}")
            tools = get_tools(job.tools, job.workspace_dir)
            self._clone_repo(job.repo_name, job.workspace_dir)

            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                model = LiteLLMModel(model_id=job.model_name)
                agent = CodeAgent(tools=tools, model=model, max_steps=job.max_num_steps)
                result = agent.run(job.prompt)

            repo_diff = create_git_patch(job.workspace_dir)
            logger.info("Successfully finished job")
            return JobResult(status=True, output=result, stdout=buffer.getvalue(), diff=repo_diff)
        except Exception as e:
            logger.exception(e)
            return JobResult(status=False, output=str(e))
        finally:
            self._clean_workspace(job.workspace_dir)

    def _clone_repo(self, repo_name: str, workspace_dir: Path):
        repo_url = f"git@github.com:{job.repo_name}.git"
        Repo.clone_from(repo_url, job.workspace_dir)
        logger.info(f"Cloned repository {job.repo_name} to {job.workspace_dir}")

    def _clean_workspace(self, workspace_dir: Path):
        if workspace_dir.exists():
            shutil.rmtree(workspace_dir)
            logger.info(f"Cleaned workspace {job.workspace_dir}")


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
    worker = Worker()
    with tempfile.TemporaryDirectory() as tmpdirname:
        job = JobCfg(
            repo_name="nydiarra/springboot-jwt",
            model_name="gemini/gemini-1.5-flash",
            tools=[],
            workspace_dir=tmpdirname,
            max_num_steps=1,
        )
        print(worker(job))
