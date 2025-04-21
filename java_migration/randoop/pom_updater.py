import os
from typing import Optional

from java_migration.maven.maven_pom_editor import MavenPomEditor
from java_migration.maven.maven_project import MavenProject


class PomUpdater:
    RANDOOP_MODULE_NAME = "randoop-tests"

    def __init__(self, repo_path: str) -> None:
        """
        Initialize the updater with a repository path (containing pom.xml) and optionally a module name.
        """
        pom_path = os.path.join(repo_path, "pom.xml")
        self.project_root = repo_path
        if not os.path.exists(pom_path):
            raise RuntimeError("No pom.xml found in repository; cannot update.")
        self.project = MavenProject(pom_path)
        self.editor: MavenPomEditor = self.project.get_pom_editor(None)

    def _randoop_module_exists(self) -> bool:
        """
        Check if the randoop-tests module already exists in the project.
        """
        return self.RANDOOP_MODULE_NAME in self.project.get_modules()

    def _create_randoop_module_pom(self, module_path: str) -> MavenPomEditor:
        """
        Create a new pom.xml for the randoop-tests module.
        """
        pom_path = os.path.join(module_path, "pom.xml")
        with open(pom_path, "w") as f:
            f.write("<project xmlns=\"http://maven.apache.org/POM/4.0.0\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\"\n")
            f.write("         xsi:schemaLocation=\"http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd\">\n")
            f.write("    <modelVersion>4.0.0</modelVersion>\n")
            f.write("</project>\n")
        editor = MavenPomEditor(pom_path)
        editor.ensure_element(".", "m:modelVersion", text="4.0.0")
        editor.ensure_element(".", "m:parent")
        editor.ensure_element("m:parent", "m:groupId", text=self.editor.root.findtext("m:groupId", namespaces=self.editor.namespaces))
        editor.ensure_element("m:parent", "m:artifactId", text=self.editor.root.findtext("m:artifactId", namespaces=self.editor.namespaces))
        editor.ensure_element("m:parent", "m:version", text=self.editor.root.findtext("m:version", namespaces=self.editor.namespaces))
        editor.ensure_element(".", "m:artifactId", text=self.RANDOOP_MODULE_NAME)
        editor.ensure_element(".", "m:name", text=self.RANDOOP_MODULE_NAME)

        # Add JUnit and Randoop dependencies
        dependencies_elem = editor.ensure_element(".", "m:dependencies")
        if dependencies_elem is not None: # Minimal change: Check if dependencies_elem was created
            editor.create_sub_element(dependencies_elem, "m:dependency")
            dependency_junit = dependencies_elem.xpath("m:dependency[last()]", namespaces=editor.namespaces)[0]
            editor.create_sub_element(dependency_junit, "m:groupId", text="junit")
            editor.create_sub_element(dependency_junit, "m:artifactId", text="junit")
            editor.create_sub_element(dependency_junit, "m:version", text="4.13.2")
            editor.create_sub_element(dependency_junit, "m:scope", text="test")

            editor.create_sub_element(dependencies_elem, "m:dependency")
            dependency_randoop = dependencies_elem.xpath("m:dependency[last()]", namespaces=editor.namespaces)[0]
            editor.create_sub_element(dependency_randoop, "m:groupId", text="org.randoop")
            editor.create_sub_element(dependency_randoop, "m:artifactId", text="randoop")
            editor.create_sub_element(dependency_randoop, "m:version", text="4.3.2")
            editor.create_sub_element(dependency_randoop, "m:scope", text="test")

        # Add Surefire plugin for running tests
        build_elem = editor.ensure_element(".", "m:build")
        plugins_elem = editor.ensure_element(build_elem, "m:plugins")
        plugin_elem = editor.ensure_element(plugins_elem, "m:plugin")
        editor.create_sub_element(plugin_elem, "m:groupId", text="org.apache.maven.plugins")
        editor.create_sub_element(plugin_elem, "m:artifactId", text="maven-surefire-plugin")
        config_elem = editor.ensure_element(plugin_elem, "m:configuration")
        includes_elem = editor.ensure_element(config_elem, "m:includes")
        editor.create_sub_element(includes_elem, "m:include", text="**/RegressionTest*.java")

        editor._save()
        return editor

    def create_randoop_module(self) -> None:
        """
        Create a new module for running Randoop tests if it doesn't exist.
        """
        if not self.project.is_multi_module():
            print("Project is not multi-module. Skipping Randoop module creation.")
            return

        if not self._randoop_module_exists():
            module_path = os.path.join(self.project_root, self.RANDOOP_MODULE_NAME)
            os.makedirs(module_path, exist_ok=True)
            randoop_module_editor = self._create_randoop_module_pom(module_path)

            # Add the new module to the root pom.xml
            modules_elem = self.editor.ensure_element(".", "m:modules")
            self.editor.create_sub_element(modules_elem, "m:module", text=self.RANDOOP_MODULE_NAME)
            self.editor._save()
            print(f"Created Randoop test module: {self.RANDOOP_MODULE_NAME}")
        else:
            print(f"Randoop test module already exists: {self.RANDOOP_MODULE_NAME}")

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
        if self.project.is_multi_module():
            self.create_randoop_module()
            self.update_build_helper_plugin()
            print(f"Root POM at {self.editor.pom_file} updated for Randoop test module.")
        else:
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
