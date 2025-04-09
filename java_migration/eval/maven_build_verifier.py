import re
from pathlib import Path

from java_migration.eval.data_model import BuildResults, TestResults
from java_migration.utils import maven_test


class MavenBuildVerifier:
    BUILD_SUCCESS = "BUILD SUCCESS"
    BUILD_FAILURE = "BUILD FAILURE"
    FATAL_TAG = "[FATAL]"
    ERROR_TAG = "[ERROR]"

    def verify(self, repo_path: Path, build_only=False, target_java_version="17") -> BuildResults:
        compile_only_log = maven_test(repo_path, skip_tests=True, target_java_version=target_java_version)
        if (
            self._detect_compilation_failure(compile_only_log)
            or self.ERROR_TAG in compile_only_log
            or self.FATAL_TAG in compile_only_log
            or self.BUILD_FAILURE in compile_only_log
        ):
            return BuildResults(
                build_log=compile_only_log,
                build_success=False,
                test_success=None,
                test_results=None,
            )

        if build_only:
            return BuildResults(
                build_log=compile_only_log,
                build_success=True,
                test_success=None,
                test_results=None,
            )

        build_log = maven_test(repo_path)

        assert self._detect_compilation_failure(build_log) is False
        build_success = True
        test_success = self._extract_overall_success(build_log)
        test_run_status = self._extract_test_run_status(build_log)

        return BuildResults(
            build_log=build_log,
            build_success=build_success,
            test_success=test_success,
            test_results=test_run_status,
        )

    def _detect_compilation_failure(self, log_text: str) -> bool:
        pattern = r"Failed to execute goal org\.apache\.maven\.plugins:maven-compiler-plugin:[^:]+:compile"

        return bool(re.search(pattern, log_text))

    def _extract_overall_success(self, log_text: str) -> bool | None:
        if self.BUILD_SUCCESS in log_text:
            return True
        if self.BUILD_FAILURE in log_text:
            return False
        if self.FATAL_TAG in log_text:
            return False

        return None

    def _extract_test_run_status(self, log_text: str) -> TestResults | None:
        pattern = r"Tests run:\s*(\d+),\s*Failures:\s*(\d+),\s*Errors:\s*(\d+),\s*Skipped:\s*(\d+)"

        matches = re.findall(pattern, log_text)
        if not matches:
            return None

        counters = {"tests_run": 0, "failures": 0, "errors": 0, "skipped": 0}

        for match in matches:
            tests_run, failures, errors, skipped = map(int, match)
            counters["tests_run"] += tests_run
            counters["failures"] += failures
            counters["errors"] += errors
            counters["skipped"] += skipped

        return TestResults(
            tests_run=counters["tests_run"],
            failures=counters["failures"],
            errors=counters["errors"],
            skipped=counters["skipped"],
        )


if __name__ == "__main__":
    repo_path = Path("/Users/mayvic/Documents/git/springboot-jwt")
    verifier = MavenBuildVerifier()
    results = verifier.verify(repo_path)
    print(results)
