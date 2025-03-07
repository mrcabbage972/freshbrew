from pathlib import Path
import subprocess


REPO_ROOT = Path(__file__).parent.parent


def maven_install(repo_path: Path) -> str:
    cmd = [
        "mvn",
        "-B",
        "-U",
        "install",
        "-Dorg.slf4j.simpleLogger.log.org.apache.maven.cli.transfer.Slf4jMavenTransferListener=warn",
    ]
    result = subprocess.run(cmd, capture_output=True, cwd=repo_path)
    return result.stdout.decode("utf-8")


def maven_test(repo_path: Path) -> str:
    cmd = [
        "mvn",
        "-B",
        "-U",
        "test",
        "-Dorg.slf4j.simpleLogger.log.org.apache.maven.cli.transfer.Slf4jMavenTransferListener=warn",
    ]
    result = subprocess.run(cmd, capture_output=True, cwd=repo_path)
    return result.stdout.decode("utf-8")
