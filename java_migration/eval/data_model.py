from pydantic import BaseModel
from pathlib import Path


class TestResults(BaseModel):
    tests_run: int
    failures: int
    errors: int
    skipped: int


class BuildResults(BaseModel):
    build_log: str
    overall_success: bool | None
    build_success: bool | None
    test_success: bool | None
    test_results: TestResults | None


class AgentConfig(BaseModel):
    max_num_steps: int
    tools: list[str]
    model_name: str
    prompt: str = "Upgrade the project to use JDK 17. Ensure that the build and the tests pass."
    agent_type: str


class JobCfg(BaseModel):
    agent_config: AgentConfig
    repo_name: str
    workspace_dir: Path


class MigrationResult(BaseModel):
    build_result: BuildResults
    output: str
    stdout: str
    diff: str

    # def __repr__(self) -> str:
    #     status_str = "Success" if self.build_success else "Failure"
    #     output_str = f"output='{escape_newlines(collapse_middle(self.output))}'"
    #     stdout_str = f", stdout='{escape_newlines(collapse_middle(self.stdout))}'" if self.stdout is not None else ""
    #     diff_str = f", diff='{escape_newlines(collapse_middle(self.diff))}'" if self.diff is not None else ""

    #     parts = [status_str, output_str, stdout_str, diff_str]
    #     non_empty_parts = [part for part in parts if part]
    #     combined_str = ", ".join(non_empty_parts)

    #     return f"JobResult({combined_str})"


class JobResult(BaseModel):
    run_success: bool
    error: str | None = None
    migration_result: MigrationResult | None = None

    def __repr__(self) -> str:
        return f"JobResult(run_success={self.run_success}, error='{self.error}')"

    def __str__(self) -> str:
        return self.__repr__()


class EvalMetrics(BaseModel):
    num_overall_success: int
    num_build_success: int
    num_test_success: int
    num_failed_to_run: int
    num_total: int
