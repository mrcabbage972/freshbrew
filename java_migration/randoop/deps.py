import glob
import os
from pathlib import Path

from java_migration.maven import Maven


def infer_class_name(rel_path: str) -> str:
    """
    Convert a relative path to a .class file into a fully qualified class name.
    E.g., "com/sohu/index/tv/mq/common/PullResponse$1.class" becomes
    "com.sohu.index.tv.mq.common.PullResponse$1".
    """
    if rel_path.endswith(".class"):
        rel_path = rel_path[:-6]
    return rel_path.replace(os.path.sep, ".")


def find_compiled_classes_dirs(repo_path: Path) -> list[str]:
    """
    Use glob to find candidate directories for compiled classes.
    Looks for directories matching patterns such as:
      - **/target/classes
      - **/build/classes
      - **/bin
    Only returns those that contain at least one .class file.
    """
    patterns = [
        os.path.join(str(repo_path), "**", "target", "classes"),
        os.path.join(str(repo_path), "**", "build", "classes"),
        os.path.join(str(repo_path), "**", "bin"),
    ]
    candidate_dirs = set()
    for pattern in patterns:
        for d in glob.glob(pattern, recursive=True):
            if os.path.isdir(d):
                class_files = glob.glob(os.path.join(d, "**", "*.class"), recursive=True)
                if class_files:
                    candidate_dirs.add(os.path.abspath(d))
    return sorted(candidate_dirs)


def generate_class_list(repo_path: Path, compiled_dirs: list[str], output_filename="classlist.txt") -> str:
    """
    Walk through each candidate compiled classes directory and write fully qualified
    class names (based on the relative path) into a file.
    """
    class_list_path = os.path.join(repo_path, output_filename)
    with open(class_list_path, "w") as f:
        for base_dir in compiled_dirs:
            for root, dirs, files in os.walk(base_dir):
                for file in files:
                    if file.endswith(".class"):
                        rel_path = os.path.relpath(os.path.join(root, file), base_dir)
                        class_name = infer_class_name(rel_path)
                        f.write(class_name + "\n")
    print(f"Generated class list at {class_list_path}")
    return class_list_path


def get_all_dependency_jars(repo_path: str) -> list[str]:
    jars = []
    pattern = os.path.join(repo_path, "**", "target", "dependencies")
    for dep_dir in glob.glob(pattern, recursive=True):
        if os.path.isdir(dep_dir):
            for root, dirs, files in os.walk(dep_dir):
                for file in files:
                    if file.endswith(".jar"):
                        jars.append(os.path.abspath(os.path.join(root, file)))
    return jars


def run_maven_dependency_cp(repo_path: Path, target_java_version="8") -> list[str]:
    """
    Run Maven to copy dependencies and return all dependency jar paths.
    """
    print("Running Maven command to copy dependencies")
    result = Maven(target_java_version=target_java_version).copy_deps(repo_path)
    if result.status != 0:
        raise RuntimeError(f"Maven command failed with status {result.status}: {result.stderr}")
    return get_all_dependency_jars(str(repo_path))


def remove_class_from_list(class_list_file: str, failing_class: str):
    """
    Remove all occurrences of failing_class from the class list file.
    """
    with open(class_list_file, "r") as f:
        lines = f.readlines()
    new_lines = [line for line in lines if line.strip() != failing_class]
    with open(class_list_file, "w") as f:
        f.writelines(new_lines)
    print(f"Removed {failing_class} from class list.")


class RandoopDependencyManager:
    def __init__(self, repo_path: Path, randoop_jar_path: Path, target_java_version: str = "8"):
        self.repo_path = repo_path
        self.randoop_jar_path = randoop_jar_path
        self.target_java_version = target_java_version

        self._process()

    def _process(self):
        # Find candidate compiled classes directories.
        compiled_dirs = find_compiled_classes_dirs(self.repo_path)
        if not compiled_dirs:
            raise RuntimeError("No compiled classes directories found. Please build your project first.")

        # Generate the class list file.
        self.class_list_file = generate_class_list(self.repo_path, compiled_dirs)
        if not self.class_list_file:
            raise RuntimeError("Failed to generate class list. Skipping Randoop execution.")

        # Get dependencies.
        dependency_cp = ""
        if os.path.exists(os.path.join(self.repo_path, "pom.xml")):
            dependency_cp = run_maven_dependency_cp(self.repo_path)
        additional_jars = get_all_dependency_jars(str(self.repo_path))
        separator = ":" if os.name != "nt" else ";"
        classpath_elements = compiled_dirs + [str(self.randoop_jar_path)] + additional_jars
        if dependency_cp:
            self.classpath = separator.join(classpath_elements) + separator + separator.join(dependency_cp)
        else:
            self.classpath = separator.join(classpath_elements)

    def get_class_path(self) -> str:
        return self.classpath

    def get_class_list_file(self) -> str:
        return self.class_list_file

    def cleanup(self):
        # Clean up temporary classlist and cp files.
        if os.path.exists(Path(self.repo_path) / "classlist.txt"):
            os.remove(Path(self.repo_path) / "classlist.txt")
