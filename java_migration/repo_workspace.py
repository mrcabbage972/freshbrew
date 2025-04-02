import shutil
from logging import getLogger
from pathlib import Path

from git import Repo
from tenacity import retry, stop_after_attempt

logger = getLogger(__name__)


class RepoWorkspace:
    def __init__(self, repo_name: str, workspace_dir: Path, commit_sha: str):
        self.repo_name = repo_name
        self.workspace_dir = workspace_dir
        self.commit_sha = commit_sha

    @retry(stop=stop_after_attempt(3))
    @staticmethod
    def from_git(repo_name: str, workspace_dir: Path, commit_sha: str) -> "RepoWorkspace":
        if workspace_dir.exists():
            shutil.rmtree(workspace_dir)
        repo_url = f"git@github.com:{repo_name}.git"
        repo = Repo.clone_from(repo_url, workspace_dir, depth=1)
        repo.git.checkout(commit_sha)
        logger.info(f"Cloned repository {repo_name} to {workspace_dir} and checked out commit {commit_sha}")
        return RepoWorkspace(repo_name, workspace_dir, commit_sha)

    def clean(self):
        if self.workspace_dir.exists():
            shutil.rmtree(self.workspace_dir)
            logger.info(f"Cleaned workspace {self.workspace_dir}")
