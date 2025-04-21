import os
from typing import Optional

from java_migration.maven.maven_pom_editor import MavenPomEditor
from java_migration.maven.maven_project import MavenProject



class PomUpdater:
    RANDOOP_MODULE_NAME = "randoop-tests"

    JUNIT_VERSION = "4.13.2"
    RANDOOP_VERSION = "4.3.2"
    SUREFIRE_VERSION = "2.22.2" 
    INSTALL_PLUGIN_VERSION = "2.5.2"
    DEPLOY_PLUGIN_VERSION = "2.8.2"


    def __init__(self, repo_path: str) -> None:
        """
        Initialize the updater with a repository path (containing pom.xml) and optionally a module name.
        """
        pom_path = os.path.join(repo_path, "pom.xml")
        self.project_root = repo_path
        if not os.path.exists(pom_path):
            raise RuntimeError("No pom.xml found in repository; cannot update.")
        self.project = MavenProject(pom_path)
        # Root editor is always initialized
        self.editor: MavenPomEditor = self.project.get_pom_editor(None)

    def _randoop_module_exists(self) -> bool:
        """
        Check if the randoop-tests module already exists in the project.
        """
        return self.RANDOOP_MODULE_NAME in self.project.get_modules()

    def ensure_managed_dependencies_in_root(self) -> None:
        """
        Ensure JUnit and Randoop are managed in the root POM's <dependencyManagement>.
        Also ensures corresponding version properties exist.
        """
        print("Ensuring JUnit is managed in root pom...")
        # Ensure properties exist in root pom
        self.editor.ensure_property("junit.version", self.JUNIT_VERSION)

        # Ensure dependencies are managed in root pom
        self.editor.ensure_managed_dependency("junit", "junit", "${junit.version}", scope="test")

    def _create_randoop_module_pom(self, module_path: str) -> MavenPomEditor:
        """
        Create a new pom.xml for the randoop-tests module.
        """
        pom_path = os.path.join(module_path, "pom.xml")
        with open(pom_path, "w") as f:
            f.write("<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n")
            f.write("<project xmlns=\"http://maven.apache.org/POM/4.0.0\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\"\n")
            f.write("         xsi:schemaLocation=\"http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd\">\n")
            f.write("    <modelVersion>4.0.0</modelVersion>\n")
            # Basic parent info needed for dependency resolution during creation
            f.write("    <parent>\n")
            f.write(f"        <groupId>{self.editor.root.findtext('m:groupId', namespaces=self.editor.namespaces)}</groupId>\n") # Get from root editor
            f.write(f"        <artifactId>{self.editor.root.findtext('m:artifactId', namespaces=self.editor.namespaces)}</artifactId>\n") # Get from root editor
            f.write(f"        <version>{self.editor.root.findtext('m:version', namespaces=self.editor.namespaces)}</version>\n") # Get from root editor
            f.write("    </parent>\n")
            f.write(f"    <artifactId>{self.RANDOOP_MODULE_NAME}</artifactId>\n")
            f.write(f"    <name>{self.RANDOOP_MODULE_NAME}</name>\n")
            f.write("    <packaging>jar</packaging>\n")
            f.write("</project>\n")

        randoop_editor = MavenPomEditor(pom_path) # Create editor for the new pom

        # Add JUnit and Randoop dependencies (WITHOUT version - managed by parent)
        dependencies_elem = randoop_editor.ensure_element(".", "m:dependencies")
        # JUnit
        dependency_junit = randoop_editor.create_sub_element(dependencies_elem, "m:dependency")
        randoop_editor.create_sub_element(dependency_junit, "m:groupId", text="junit")
        randoop_editor.create_sub_element(dependency_junit, "m:artifactId", text="junit")
        # randoop_editor.create_sub_element(dependency_junit, "m:version", text="...") # NO VERSION
        randoop_editor.create_sub_element(dependency_junit, "m:scope", text="test")
        # Randoop
        # dependency_randoop = randoop_editor.create_sub_element(dependencies_elem, "m:dependency")
        # randoop_editor.create_sub_element(dependency_randoop, "m:groupId", text="org.randoop")
        # randoop_editor.create_sub_element(dependency_randoop, "m:artifactId", text="randoop")
        # # randoop_editor.create_sub_element(dependency_randoop, "m:version", text="...") # NO VERSION
        # randoop_editor.create_sub_element(dependency_randoop, "m:scope", text="test")

        # --- Add dependencies to other project modules ---
        root_group_id = self.editor.root.findtext("m:groupId", namespaces=self.editor.namespaces)
        root_version = self.editor.root.findtext("m:version", namespaces=self.editor.namespaces) # Use root version
        all_modules = self.project.get_modules()
        print(f"Adding dependencies in {self.RANDOOP_MODULE_NAME} to modules: {[m for m in all_modules if m != self.RANDOOP_MODULE_NAME]}")

        for module_name in all_modules:
            if module_name == self.RANDOOP_MODULE_NAME:
                continue # Don't add self

            module_dep = randoop_editor.create_sub_element(dependencies_elem, "m:dependency")
            randoop_editor.create_sub_element(module_dep, "m:groupId", text=root_group_id)
            randoop_editor.create_sub_element(module_dep, "m:artifactId", text=module_name)
            # Use parent version (effectively ${project.version})
            randoop_editor.create_sub_element(module_dep, "m:version", text=root_version)
            randoop_editor.create_sub_element(module_dep, "m:scope", text="test") # Crucial

        # Add Surefire plugin for running tests
        build_elem = randoop_editor.ensure_element(".", "m:build")
        plugins_elem = randoop_editor.ensure_element(build_elem, "m:plugins")

        # Surefire Plugin
        plugin_elem = randoop_editor.create_sub_element(plugins_elem, "m:plugin") # Use create_sub_element
        randoop_editor.create_sub_element(plugin_elem, "m:groupId", text="org.apache.maven.plugins")
        randoop_editor.create_sub_element(plugin_elem, "m:artifactId", text="maven-surefire-plugin")
        # Version could be managed in root <pluginManagement> but adding here is simpler for now
        # randoop_editor.create_sub_element(plugin_elem, "m:version", text=self.SUREFIRE_VERSION)
        config_elem = randoop_editor.ensure_element(plugin_elem, "m:configuration")
        includes_elem = randoop_editor.ensure_element(config_elem, "m:includes")
        randoop_editor.create_sub_element(includes_elem, "m:include", text="**/RegressionTest*.java")
        randoop_editor.create_sub_element(includes_elem, "m:include", text="**/ErrorTest*.java") # Also include error tests

        # --- Add install/deploy skip plugins ---
        # Install Plugin skip
        install_plugin = randoop_editor.create_sub_element(plugins_elem, "m:plugin")
        randoop_editor.create_sub_element(install_plugin, "m:groupId", text="org.apache.maven.plugins")
        randoop_editor.create_sub_element(install_plugin, "m:artifactId", text="maven-install-plugin")
        # Optionally add version
        # randoop_editor.create_sub_element(install_plugin, "m:version", text=self.INSTALL_PLUGIN_VERSION)
        randoop_editor.add_skip_plugin_config(install_plugin) # Use helper

        # Deploy Plugin skip
        deploy_plugin = randoop_editor.create_sub_element(plugins_elem, "m:plugin")
        randoop_editor.create_sub_element(deploy_plugin, "m:groupId", text="org.apache.maven.plugins")
        randoop_editor.create_sub_element(deploy_plugin, "m:artifactId", text="maven-deploy-plugin")
        # Optionally add version
        # randoop_editor.create_sub_element(deploy_plugin, "m:version", text=self.DEPLOY_PLUGIN_VERSION)
        randoop_editor.add_skip_plugin_config(deploy_plugin) # Use helper
        # --- End Add install/deploy skip plugins ---

        randoop_editor._save()
        return randoop_editor

    def create_randoop_module(self) -> Optional[MavenPomEditor]:
        """
        Create a new module for running Randoop tests if it doesn't exist.
        """
        if not self.project.is_multi_module():
            print("Project is not multi-module. Skipping Randoop module creation.")
            return None # Indicate no editor created/found

        if not self._randoop_module_exists():
            print(f"Creating Randoop test module: {self.RANDOOP_MODULE_NAME}...")
            module_path = os.path.join(self.project_root, self.RANDOOP_MODULE_NAME)
            os.makedirs(module_path, exist_ok=True)
            randoop_module_editor = self._create_randoop_module_pom(module_path)

            # Add the new module to the root pom.xml
            modules_elem = self.editor.ensure_element(".", "m:modules")
            # Check if module is already listed before adding
            module_exists_in_list = modules_elem.xpath(f"m:module[text()='{self.RANDOOP_MODULE_NAME}']", namespaces=self.editor.namespaces)
            if not module_exists_in_list:
                 self.editor.create_sub_element(modules_elem, "m:module", text=self.RANDOOP_MODULE_NAME)
                 self.editor._save() # Save root pom after adding module
            print(f"Created and configured Randoop test module: {self.RANDOOP_MODULE_NAME}")
            return randoop_module_editor
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
            print("Processing multi-module project for Randoop setup...")
            # 1. Ensure JUnit/Randoop dependencies are managed in root POM
            self.ensure_managed_dependencies_in_root()

            # 2. Create/update the randoop-tests module and add it to root modules list
            self.create_randoop_module()

            print(f"Root POM at {self.editor.pom_file} updated for Randoop test module management.")
            print(f"Randoop module '{self.RANDOOP_MODULE_NAME}' created/updated.")

        else:
            # Keep original single-module logic (may need separate review)
            print("Processing single-module project (using potentially different logic)...")
            self.editor.ensure_element(".", "m:build")
            self.editor.ensure_element("m:build", "m:plugins")
            self.update_build_helper_plugin()
            self.update_surefire_plugin()
            # Original logic (Now likely redundant due to ensure_managed_dependencies_in_root if called)
            # self.update_junit_dependency()
            print(f"POM file at {self.editor.pom_file} updated (single-module logic).")


if __name__ == "__main__":    
    repository_path: str = "/home/user/java-migration-paper/data/workspace/zykzhangyukang_Xinguan"
    try:
        updater = PomUpdater(repository_path)
        updater.update()
        print("PomUpdater finished successfully.")
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()