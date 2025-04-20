import os
from typing import Optional

from java_migration.maven.maven_pom_editor import MavenPomEditor
from java_migration.maven.maven_project import MavenProject


class PomUpdater:
    def __init__(self, repo_path: str, module: Optional[str] = None) -> None:
        """
        Initialize the updater with a repository path (containing pom.xml) and optionally a module name.
        """
        pom_path = os.path.join(repo_path, "pom.xml")
        if not os.path.exists(pom_path):
            raise RuntimeError("No pom.xml found in repository; cannot update.")
        self.project = MavenProject(pom_path)
        self.editor: MavenPomEditor = self.project.get_pom_editor(module)

    def get_randoop_source(self) -> str:
        """
        Determine the randoop-tests source directory.
        """
        return (
            "${project.parent.basedir}/randoop-tests"
            if self.project.is_multi_module()
            else "${project.basedir}/randoop-tests"
        )

    def update_build_helper_plugin(self) -> None:
        """
        Ensure the build-helper-maven-plugin is present with the correct execution to add test sources.
        """
        if not self.editor.plugin_exists("org.codehaus.mojo", "build-helper-maven-plugin"):
            plugin = self.editor.add_plugin("org.codehaus.mojo", "build-helper-maven-plugin", version="3.2.0")
            executions_elem = self.editor.ensure_element(plugin, "m:executions")
            execution_elem = self.editor.create_sub_element(executions_elem, "m:execution")
            self.editor.create_sub_element(execution_elem, "m:id", text="add-test-source")
            self.editor.create_sub_element(execution_elem, "m:phase", text="generate-test-sources")
            goals_elem = self.editor.create_sub_element(execution_elem, "m:goals")
            self.editor.create_sub_element(goals_elem, "m:goal", text="add-test-source")
            configuration_elem = self.editor.create_sub_element(execution_elem, "m:configuration")
            sources_elem = self.editor.create_sub_element(configuration_elem, "m:sources")
            self.editor.create_sub_element(sources_elem, "m:source", text=self.get_randoop_source())
            self.editor._save()

    def update_surefire_plugin(self) -> None:
        """
        Ensure the maven-surefire-plugin is present with configuration to include regression tests.
        """
        if not self.editor.plugin_exists("org.apache.maven.plugins", "maven-surefire-plugin"):
            plugin = self.editor.add_plugin("org.apache.maven.plugins", "maven-surefire-plugin", version="2.22.2")
            config_elem = self.editor.ensure_element(plugin, "m:configuration")
            includes_elem = self.editor.ensure_element(config_elem, "m:includes")
            self.editor.create_sub_element(includes_elem, "m:include", text="**/*Test.class")
            self.editor.create_sub_element(includes_elem, "m:include", text="**/*Tests.class")
            self.editor.create_sub_element(includes_elem, "m:include", text="**/RegressionTest*.class")
            self.editor._save()

    def update_junit_dependency(self) -> None:
        """
        Ensure that the JUnit dependency exists; add it if missing.
        """
        if not self.editor.dependency_exists("junit", "junit"):
            self.editor.add_dependency("junit", "junit", "4.13.2", scope="test")
            print("Added JUnit dependency to pom.")

    def update(self) -> None:
        """
        Run all update operations: ensure <build>/<plugins> exist, then update
        the build-helper plugin, surefire plugin, and JUnit dependency.
        """
        self.editor.ensure_element(".", "m:build")
        self.editor.ensure_element("m:build", "m:plugins")
        self.update_build_helper_plugin()
        self.update_surefire_plugin()
        self.update_junit_dependency()
        print(f"POM file at {self.editor.pom_file} updated for regression tests.")


if __name__ == "__main__":
    # Change this path to point to a repository containing a pom.xml
    repository_path: str = "path/to/your/repo"
    try:
        updater = PomUpdater(repository_path)
        updater.update()
    except Exception as e:
        print("An error occurred:", e)
