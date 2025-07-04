import contextlib
import io
import logging
import os

from smolagents import CodeAgent
from smolagents.models import LiteLLMModel

from java_migration.dummy_agent import DummyAgent
from java_migration.eval.data_model import JobCfg, JobResult, MigrationResult
from java_migration.eval.maven_build_verifier import MavenBuildVerifier
from java_migration.eval.utils import create_git_patch
from java_migration.repo_workspace import RepoWorkspace
from java_migration.smol_tools import get_tools

logger = logging.getLogger(__name__)


class Worker:
    """
    A worker class that processes Java migration jobs.

    This class handles the execution of migration tasks by:
    1. Setting up a repository workspace from a git repository
    2. Creating and running an appropriate agent (smol or dummy)
    3. Verifying the build after migration
    4. Capturing the migration results including output, stdout, and git diff

    The worker supports different agent types:
    - "smol": Uses CodeAgent with LiteLLM model and custom tools
    - "dummy": Uses DummyAgent for testing purposes

    Attributes:
        None (stateless class)

    Methods:
        __call__(job: JobCfg) -> JobResult: Main entry point to process a migration job
        _get_agent(job: JobCfg): Creates and returns the appropriate agent instance
    """

    def __call__(self, job: JobCfg) -> JobResult:
        repo_workspace = None
        try:
            logger.info(f"Processing job {job}")
            repo_workspace = RepoWorkspace.from_git(job.repo_name, job.workspace_dir, job.commit)
            agent = self._get_agent(job)

            logger.info("Running agent")
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                result = agent.run(job.agent_config.prompt)

            logger.info("Verifying build")
            build_result = MavenBuildVerifier().verify(
                repo_path=job.workspace_dir, target_java_version=str(job.agent_config.target_jdk_version), clean=True
            )

            repo_diff = create_git_patch(job.workspace_dir)
            logger.info("Successfully finished job")
            migration_result = MigrationResult(
                build_result=build_result, output=str(result), stdout=buffer.getvalue(), diff=repo_diff
            )
            return JobResult(run_success=True, migration_result=migration_result)
        except Exception as e:
            logger.exception(e)
            return JobResult(run_success=False, error=str(e))
        finally:
            if repo_workspace:
                repo_workspace.clean()

    def _get_agent(self, job: JobCfg):
        if job.agent_config.agent_type == "smol":
            tools = get_tools(job.agent_config.tools, job.workspace_dir)
            api_key = None
            if job.agent_config.model_name.startswith("openai"):
                api_key = os.getenv("OPENAI_API_KEY")
            model = LiteLLMModel(model_id=job.agent_config.model_name, api_key=api_key)
            agent = CodeAgent(tools=tools, model=model, max_steps=job.agent_config.max_num_steps)
        elif job.agent_config.agent_type == "dummy":
            agent = DummyAgent()
        else:
            raise ValueError(f"Unknown agent type: {job.agent_config.agent_type}")
        return agent


if __name__ == "__main__":
    pass
    # from dotenv import load_dotenv

    # load_dotenv()
    # logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
    # worker = Worker()
    # with tempfile.TemporaryDirectory() as tmpdirname:
    #     agent_cfg = AgentConfig(tools=[], model_name="gemini/gemini-1.5-flash", max_num_steps=1)
    #     job = JobCfg(
    #         repo_name="nydiarra/springboot-jwt",
    #         workspace_dir=Path(tmpdirname),
    #         agent_config=agent_cfg,
    #     )
    #     print(worker(job))
