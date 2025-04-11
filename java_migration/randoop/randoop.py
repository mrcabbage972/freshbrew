import os
import re
import subprocess
from pathlib import Path

from java_migration.maven import Maven
from java_migration.randoop.deps import RandoopDependencyManager, remove_class_from_list
from java_migration.utils import create_git_diff

RANDOOP_TESTS_DIR = "randoop-tests"


def extract_failing_class(error_output: str) -> str | None:
    """
    Extract the failing class name from Randoop's error output.
    Expects a line like: "Could not load class com.sojson.core.statics.Constant: ..."
    """
    m = re.search(r"Could not load class\s+([\w\.\$]+)", error_output)
    if m:
        failing_class = m.group(1)
        print(f"Extracted failing class: {failing_class}")
        return failing_class
    return None


class RandoopRunner:
    def __init__(
        self, randoop_jar_path: Path, target_java_version: str = "8", time_limit: int = 60, output_limit: int = 200, num_retries: int = 20
    ):
        self.randoop_jar_path = randoop_jar_path
        self.target_java_version = target_java_version
        self.time_limit = time_limit
        self.output_limit = output_limit
        self.num_retries = num_retries
        self.randoop_opts = self._get_randoop_options()

    def _get_randoop_options(self) -> list[str]:
        return [
            "gentests",
            "--no-error-revealing-tests=true",
            "--junit-output-dir=randoop-tests",
            f"--time-limit={self.time_limit}",
            f"--output-limit={self.output_limit}",
        ]

    def _ensure_repo_sanity(self, repo_path: Path):
        if not Maven(target_java_version=self.target_java_version).install(repo_path, skip_tests=True).status == 0:
            raise RuntimeError("Maven install failed. Skipping.")

        if not os.path.exists(os.path.join(repo_path, ".git")):
            raise RuntimeError("Error: Not a valid Git repository. Skipping.")

    def execute_randoop(self, classpath: str, class_list_file: str) -> tuple[str, str]:
        """
        Execute Randoop with the given classpath and class list.
        Returns stdout and stderr if an error occurs.
        """
        cmd = (
            ["java", "-classpath", classpath, "randoop.main.Main"]
            + self.randoop_opts
            + [f"--classlist={class_list_file}"]
        )
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            raise subprocess.CalledProcessError(result.returncode, cmd, output=result.stdout, stderr=result.stderr)
        return result.stdout, result.stderr

    def run(self, repo_path: Path) -> Path:
        original_cwd = os.getcwd()
        try:
            os.chdir(repo_path)
            print(f"\nProcessing repository: {repo_path}")

            self._ensure_repo_sanity(repo_path)

            deps_man = RandoopDependencyManager(repo_path, self.randoop_jar_path, self.target_java_version)

            # Ensure output directory for Randoop tests exists.
            output_dir = repo_path / RANDOOP_TESTS_DIR
            if not output_dir.exists():
                output_dir.mkdir()

            success = False
            for attempt in range(1, self.num_retries + 1):
                print(f"Randoop run attempt {attempt} of {self.num_retries}...")
                try:
                    stdout, stderr = self.execute_randoop(deps_man.get_class_path(), deps_man.get_class_list_file())
                    print("Randoop completed successfully.")
                    success = True
                    break
                except subprocess.CalledProcessError as e:
                    print("Randoop failed")
                    failing_class = extract_failing_class(e.stdout)
                    if not failing_class:
                        print("Could not extract failing class; aborting retries.")
                        break
                    remove_class_from_list(deps_man.get_class_list_file(), failing_class)
            if not success:
                raise RuntimeError("Randoop did not complete successfully after retries.")

            deps_man.cleanup()

            # Create the dedicated test module and update the parent's modules.
            # create_dedicated_test_module(repo_path)
            # update_parent_modules_for_test_module(repo_path)

            # Update all pom files for regression test configuration.
            # update_pom_for_regression_tests(str(repo_path))
            # dedicated_test_pom = output_dir / "pom.xml"
            # update_pom_for_regression_tests(str(dedicated_test_pom.parent))

            # Stage changes and generate a Git diff.
            diff_file = create_git_diff(repo_path)
            return Path(diff_file)

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Error processing repo {repo_path}: {e}")
        finally:
            os.chdir(original_cwd)
