from pydantic import BaseModel
from pathlib import Path


class JobCfg(BaseModel):
    max_num_steps: int
    tools: list[str]
    repo_name: str
    workspace_dir: Path


class JobResult(BaseModel):
    status: bool
    output: str
