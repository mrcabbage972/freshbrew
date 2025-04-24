import os
import re
import subprocess
from pathlib import Path

from java_migration.maven.maven_runner import Maven
from java_migration.randoop.deps import RandoopDependencyManager, remove_class_from_list
from java_migration.randoop.pom_updater import PomUpdater
from java_migration.utils import create_git_diff

RANDOOP_TESTS_DIR = "randoop-tests"
RANDOOP_SRC_TEST_JAVA = os.path.join(RANDOOP_TESTS_DIR, "src", "test", "java")


class RandoopRunner:
    def __init__(
        self,
        randoop_jar_path: Path,
        target_java_version: str = "8",
        time_limit: int = 300,
        output_limit: int = 500,
        num_retries: int = 20,
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
            f"--junit-output-dir={RANDOOP_SRC_TEST_JAVA}",
            f"--time-limit={self.time_limit}",
            f"--output-limit={self.output_limit}",
        ]

    def _to_wildcard_classpath(self, classpath: str) -> str:
        """
        Collapse any jars in the same folder into folder/* wildcards.
        """
        parts = classpath.split(os.pathsep)
        jar_dirs = {}
        others = []
        for p in parts:
            if p.endswith(".jar"):
                d = os.path.dirname(p)
                jar_dirs.setdefault(d, []).append(p)
            else:
                others.append(p)

        # build wildcard entries for each jar directory
        wildcard_parts = [os.path.join(d, "*") for d in jar_dirs]
        return os.pathsep.join(others + wildcard_parts)

    def _ensure_repo_sanity(self, repo_path: Path):
        if Maven(target_java_version=self.target_java_version) \
               .test(repo_path, skip_tests=True).status != 0:
            raise RuntimeError("Maven install failed. Skipping.")

        if not (repo_path / ".git").exists():
            raise RuntimeError("Error: Not a valid Git repository. Skipping.")

    def execute_randoop(self, classpath: str, class_list_file: str) -> tuple[str, str]:
        """
        Execute Randoop, but first convert any long jar lists into wildcard dirs.
        """
        wildcard_cp = self._to_wildcard_classpath(classpath)
        cmd = (
            ["java", "-classpath", wildcard_cp, "randoop.main.Main"]
            + self.randoop_opts
            + [f"--classlist={class_list_file}"]
        )
        result = subprocess.run(cmd,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True)
        if result.returncode != 0:
            raise subprocess.CalledProcessError(
                result.returncode, cmd,
                output=result.stdout,
                stderr=result.stderr
            )
        return result.stdout, result.stderr

    def run(self, repo_path: Path) -> Path:
        original_cwd = os.getcwd()
        try:
            os.chdir(repo_path)
            print(f"\nProcessing repository: {repo_path}")

            self._ensure_repo_sanity(repo_path)

            deps_man = RandoopDependencyManager(
                repo_path, self.randoop_jar_path, self.target_java_version
            )

            # Prepare output dirs
            output_dir = repo_path / RANDOOP_SRC_TEST_JAVA
            output_dir.mkdir(parents=True, exist_ok=True)

            PomUpdater(repo_path).update()

            for attempt in range(1, self.num_retries + 1):
                print(f"Randoop run attempt {attempt} of {self.num_retries}…")
                try:
                    stdout, stderr = self.execute_randoop(
                        deps_man.get_class_path(),
                        deps_man.get_class_list_file()
                    )
                    print("✅ Randoop completed successfully.")
                    break
                except subprocess.CalledProcessError as e:
                    error_str = e.stderr or e.output
                    print(f"❌ Randoop failed: {error_str[:500]}")
                    cls = extract_failing_class(e.stdout or e.stderr)
                    if not cls:
                        raise RuntimeError("Could not extract failing class.")
                    remove_class_from_list(deps_man.get_class_list_file(), cls)
            else:
                raise RuntimeError("Randoop did not succeed after retries.")

            deps_man.cleanup()
            diff_file = create_git_diff(repo_path)
            return Path(diff_file)

        finally:
            os.chdir(original_cwd)


def extract_failing_class(error_output: str) -> str | None:
    m = re.search(r"Could not load class\s+([\w\.\$]+)", error_output)
    if m:
        cls = m.group(1)
        print(f"Extracted failing class: {cls}")
        return cls
    return None


def main():
    # if len(sys.argv) < 2:
    #     print("Usage: python script.py <repo_path1> [<repo_path2> ...]")
    #     sys.exit(1)

    # v5tech_oltu-oauth2-example
    # grpc-swagger_grpc-swagger
    # yeecode_EasyRPC
    # baichengzhou_SpringMVC-Mybatis-shiro
    # scxwhite_hera
    # ESAPI_esapi-java
    # /home/user/java-migration-paper/data/workspace/yangxiufeng666_Micro-Service-Skeleton
    # "/home/user/java-migration-paper/data/workspace/zykzhangyukang_Xinguan"
    repos = [Path("/home/user/java-migration-paper/data/workspace_tmp/forum-java")]  # sys.argv[1:]
    for repo in repos:
        if os.path.isdir(repo):

            randoop_runner = RandoopRunner(
            target_java_version="8", randoop_jar_path=Path("/home/user/java-migration-paper/randoop-4.3.3/randoop-all-4.3.3.jar")
        )

            randoop_runner.run(repo)
            #run_randoop_on_repo(repo, Path("/home/user/java-migration-paper/randoop-4.3.3/randoop-all-4.3.3.jar"))
        else:
            print(f"Path does not exist or is not a directory: {repo}")


if __name__ == "__main__":
    main()