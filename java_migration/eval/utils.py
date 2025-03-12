import logging
import os
import re
from datetime import datetime
from pathlib import Path

import git
from names_generator import generate_name

logger = logging.getLogger(__name__)


def safe_repo_name(repo_name: str) -> str:
    return repo_name.replace("/", "_")


def recover_safe_repo_name(repo_name: str) -> str:
    split_idx = repo_name.index("_")
    return repo_name[:split_idx] + "/" + repo_name[split_idx + 1 :]


def generate_experiment_dir(prefix: Path) -> Path:
    """Generates a unique experiment directory name based on the date and time."""
    timestamp = datetime.now()
    date_str = timestamp.strftime("%Y-%m-%d")
    time_str = timestamp.strftime("%H-%M-%S")
    experiment_name = generate_name(style="hyphen")
    exp_path = prefix / date_str / f"{time_str}-{experiment_name}"
    exp_path.mkdir(parents=True, exist_ok=True)
    return exp_path


def create_git_patch(repo_path: Path) -> str:
    repo = git.Repo(str(repo_path))

    # Get a list of modified (unstaged) files
    changed_files = repo.git.diff("--name-only").splitlines()

    # Define exclusion criteria:
    # - Any file that is in a directory named 'target'
    # - Files with excluded extensions (compiled binaries, temporary files, etc.)
    exclude_dirs = {"target"}
    exclude_exts = {".class", ".jar", ".war", ".ear", ".tmp"}  # add more extensions if needed

    def is_excluded(file_path: str) -> bool:
        # Exclude if any directory in the file's path is in the exclude list.
        path_parts = file_path.split(os.sep)
        if any(part in exclude_dirs for part in path_parts):
            return True
        # Exclude if the file extension is in the exclusion list.
        _, ext = os.path.splitext(file_path)
        if ext.lower() in exclude_exts:
            return True
        return False

    # Filter out the excluded files
    allowed_files = [f for f in changed_files if not is_excluded(f)]

    if not allowed_files:
        return ""

    # Generate the patch for the allowed files
    patch = repo.git.diff("--patch", *allowed_files)
    return patch


def collapse_middle(s: str | None, max_len: int = 100) -> str:
    if s is None:
        return "None"
    if len(s) <= max_len:
        return s

    # Calculate how many characters to keep on each side
    keep_start = (max_len - 3) // 2  # Subtract 3 for "..."
    keep_end = max_len - 3 - keep_start

    return s[:keep_start] + "..." + s[-keep_end:]


def escape_newlines(s: str) -> str:
    """Replaces newline characters with their escaped representation."""
    return s.replace("\n", "\\n").replace("\r", "\\r")


def clean_log_string(log_string: str) -> str:
    try:
        ansi_escape = re.compile(r"(?:\x1B[@-_][0-?]*[ -/]*[@-~])")
        return ansi_escape.sub("", log_string)
    except Exception as e:
        logger.warning(f"Error cleaning log string: {e}")
        return log_string
