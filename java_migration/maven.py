import subprocess
from pathlib import Path
import os
from pydantic import BaseModel


class CliResult(BaseModel):
    status: int
    stdout: str
    stderr: str


class Maven:
    def __init__(self, target_java_version: str):
        self.target_java_version = target_java_version

    def _ensure_mvnw_executable(self, repo_path: Path):
        mvnw_path = repo_path / "mvnw"
        if mvnw_path.exists():
            current_permissions = os.stat(mvnw_path).st_mode
            # Add execute permissions for owner, group, and others
            new_permissions = current_permissions | 0o111
            os.chmod(mvnw_path, new_permissions)

    def _use_wrapper(self, repo_path: Path) -> bool:
        return (repo_path / "mvnw").exists()

    def _get_base_cmd(self, repo_path: Path) -> str:
        if self._use_wrapper(repo_path):
            self._ensure_mvnw_executable(repo_path)  # Call this before getting the command
            return "./mvnw"
        else:
            return "mvn"

    def test(self, repo_path: Path, skip_tests: bool = False) -> CliResult:
        cmd = [
            self._get_base_cmd(repo_path),
            "test",
            "--batch-mode",
            "-Dorg.slf4j.simpleLogger.log.org.apache.maven.cli.transfer.Slf4jMavenTransferListener=warn",
            f"-Dmaven.compiler.source={self.target_java_version}",
            f"-Dmaven.compiler.target={self.target_java_version}",
        ]
        if skip_tests:
            cmd.append("-DskipTests")
        result = subprocess.run(cmd, capture_output=True, cwd=str(repo_path))
        return CliResult(
            status=result.returncode, stdout=result.stdout.decode("utf-8"), stderr=result.stderr.decode("utf-8")
        )

    def install(self, repo_path: Path, skip_tests: bool = False) -> CliResult:
        cmd = [
            self._get_base_cmd(repo_path),
            "install",
            "--batch-mode",
            "-Dorg.slf4j.simpleLogger.log.org.apache.maven.cli.transfer.Slf4jMavenTransferListener=warn",
            f"-Dmaven.compiler.source={self.target_java_version}",
            f"-Dmaven.compiler.target={self.target_java_version}",
        ]
        if skip_tests:
            cmd.append("-DskipTests")
        result = subprocess.run(cmd, capture_output=True, cwd=str(repo_path))
        return CliResult(
            status=result.returncode, stdout=result.stdout.decode("utf-8"), stderr=result.stderr.decode("utf-8")
        )

    def deps(self, repo_path: Path, output_path: Path) -> CliResult:
        cmd = [
            self._get_base_cmd(repo_path),
            "--batch-mode",
            "-Dorg.slf4j.simpleLogger.log.org.apache.maven.cli.transfer.Slf4jMavenTransferListener=warn",
            "dependency:build-classpath",
            "-Dmdep.includeScope=compile,runtime,provided",
            f"-Dmdep.outputFile={str(output_path)}",
            f"-Dmaven.compiler.source={self.target_java_version}",
            f"-Dmaven.compiler.target={self.target_java_version}",
        ]

        print(f"Running command: {' '.join(cmd)}")

        result = subprocess.run(cmd, capture_output=True, cwd=str(repo_path))
        return CliResult(
            status=result.returncode, stdout=result.stdout.decode("utf-8"), stderr=result.stderr.decode("utf-8")
        )

    def copy_deps(self, repo_path: Path) -> CliResult:
        cmd = [
            self._get_base_cmd(repo_path),
            "dependency:copy-dependencies",
            "-DincludeScope=runtime",
            "-DoutputDirectory=target/dependencies",
            "--batch-mode",
            "-Dorg.slf4j.simpleLogger.log.org.apache.maven.cli.transfer.Slf4jMavenTransferListener=warn",
        ]

        # mvn dependency:copy-dependencies -DincludeScope=runtime -DoutputDirectory=target/dependencies
        result = subprocess.run(cmd, capture_output=True, cwd=repo_path)
        return CliResult(
            status=result.returncode, stdout=result.stdout.decode("utf-8"), stderr=result.stderr.decode("utf-8")
        )
