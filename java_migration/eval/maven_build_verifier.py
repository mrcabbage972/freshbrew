from pathlib import Path
from java_migration.utils import maven_install


class MavenBuildVerifier:
    BUILD_SUCCESS = "BUILD SUCCESS"
    BUILD_FAILURE = "BUILD FAILURE"
    FATAL_TAG = "[FATAL]"

    def verify(self, repo_path: Path) -> bool | None:
        build_log = maven_install(repo_path)
        if self.BUILD_SUCCESS in build_log:
            return True
        if self.BUILD_FAILURE in build_log:
            return False
        if self.FATAL_TAG in build_log:
            return False

        return None
