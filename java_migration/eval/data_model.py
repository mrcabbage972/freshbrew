from pydantic import BaseModel
from pathlib import Path
from java_migration.eval.utils import collapse_middle, escape_newlines


class AgentConfig(BaseModel):
    max_num_steps: int
    tools: list[str]
    model_name: str
    prompt: str = "Upgrade the project to use JDK 17. Ensure that the build and the tests pass."


class JobCfg(BaseModel):
    agent_config: AgentConfig
    repo_name: str
    workspace_dir: Path


class JobResult(BaseModel):
    status: bool
    output: str
    stdout: str | None = None
    diff: str | None = None

    def __repr__(self) -> str:
        status_str = "Success" if self.status else "Failure"
        output_str = f"output='{escape_newlines(collapse_middle(self.output))}'"
        stdout_str = f", stdout='{escape_newlines(collapse_middle(self.stdout))}'" if self.stdout is not None else ""
        diff_str = f", diff='{escape_newlines(collapse_middle(self.diff))}'" if self.diff is not None else ""

        parts = [status_str, output_str, stdout_str, diff_str]
        non_empty_parts = [part for part in parts if part]
        combined_str = ", ".join(non_empty_parts)

        return f"JobResult({combined_str})"

    def __str__(self) -> str:
        return self.__repr__()
