import os
from typing import Dict, List, Optional

from java_migration.maven.maven_pom_editor import MavenPomEditor


class MavenProject:
    def __init__(self, root_pom_path: str) -> None:
        """
        Initialize the MavenProject with the path to the top-level pom.xml.

        :param root_pom_path: Path to the project's root pom.xml.
        :raises RuntimeError: If the pom.xml is not found.
        """
        if not os.path.exists(root_pom_path):
            raise RuntimeError("No pom.xml found at the given path.")
        self.root_pom_path: str = os.path.abspath(root_pom_path)
        self.root_editor: MavenPomEditor = MavenPomEditor(self.root_pom_path)

    def is_multi_module(self) -> bool:
        """
        Determine whether the project is multi-module.

        :return: True if a <modules> section exists; False otherwise.
        """
        return self.root_editor.element_exists("m:modules")

    def get_modules(self) -> List[str]:
        """
        Retrieve the list of modules defined in the project.

        :return: List of module names.
        """
        modules_elem = self.root_editor.root.find("m:modules", namespaces=self.root_editor.namespaces)
        if modules_elem is None:
            return []
        return [
            mod.text.strip()
            for mod in modules_elem.findall("m:module", namespaces=self.root_editor.namespaces)
            if mod.text
        ]

    def get_all_pom_paths(self, root_dir: Optional[str] = None) -> Dict[str, Optional[str]]:
        """
        Get a mapping of module names to their pom.xml paths, including the root.

        :param root_dir: Base directory for pom files; defaults to the directory of the root pom.
        :return: Dictionary with keys "root" and each module.
        """
        base_dir = root_dir if root_dir is not None else os.path.dirname(self.root_pom_path)
        poms: Dict[str, Optional[str]] = {"root": self.root_pom_path}
        if self.is_multi_module():
            for mod in self.get_modules():
                mod_pom = os.path.join(base_dir, mod, "pom.xml")
                poms[mod] = os.path.abspath(mod_pom) if os.path.exists(mod_pom) else None
        return poms

    def get_pom_editor(self, module: Optional[str] = None) -> MavenPomEditor:
        """
        Return a MavenPomEditor for the specified module's pom.

        :param module: Module name. If None, return the root pom editor.
        :return: A MavenPomEditor instance.
        :raises FileNotFoundError: If the module pom.xml is not found.
        """
        if module is None:
            return self.root_editor
        else:
            mod_pom = os.path.join(os.path.dirname(self.root_pom_path), module, "pom.xml")
            if not os.path.exists(mod_pom):
                raise FileNotFoundError(f"No pom.xml found for module {module} at {mod_pom}.")
            return MavenPomEditor(mod_pom)


# Example usage:
if __name__ == "__main__":
    # Update the path as needed.
    project_path: str = "/home/user/java-migration-paper/data/workspace/alibaba_fastjson2/pom.xml"

    project = MavenProject(project_path)
    print("Multi-module project:", project.is_multi_module())
    print("Modules found:", project.get_modules())

    # Get the root pom editor and update an element (for example, the version).
    root_editor = project.get_pom_editor()
    root_editor.update_element_text(".//m:version", "1.2.3")

    # If the project has modules, get an editor for the first module and add a dependency.
    if project.is_multi_module() and project.get_modules():
        module_name = project.get_modules()[0]
        module_editor = project.get_pom_editor(module_name)
        if not module_editor.dependency_exists("junit", "junit"):
            module_editor.add_dependency("junit", "junit", "4.13.2", scope="test")
