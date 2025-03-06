from datetime import datetime
from pathlib import Path


def safe_repo_name(repo_name: str) -> str:
    return repo_name.replace("/", "_")


def generate_experiment_dir(prefix: str) -> Path:
    """Generates a unique experiment directory name based on the date and time."""
    timestamp = datetime.now()
    date_str = timestamp.strftime("%Y-%m-%d")
    time_str = timestamp.strftime("%H-%M-%S")
    exp_path = Path(prefix) / date_str / time_str
    exp_path.mkdir(parents=True, exist_ok=True)
    return exp_path
