# type: ignore
#!/usr/bin/env python3
import glob
import logging
import os
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

from lxml import etree

from java_migration.maven import Maven

logger = logging.getLogger(__name__)

NUM_RETRIES = 20

RANDOOP_OPTIONS = [
    "gentests",
    "--no-error-revealing-tests=true",
    "--junit-output-dir=randoop-tests",
    "--time-limit=60",
    "--output-limit=200",
]


def find_compiled_classes_dirs(repo_path: Path):
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


def infer_class_name(rel_path):
    """
    Convert a relative path to a .class file into a fully qualified class name.
    E.g., "com/sohu/index/tv/mq/common/PullResponse$1.class" becomes
    "com.sohu.index.tv.mq.common.PullResponse$1".
    """
    if rel_path.endswith(".class"):
        rel_path = rel_path[:-6]
    return rel_path.replace(os.path.sep, ".")


def generate_class_list(repo_path, compiled_dirs, output_filename="classlist.txt"):
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


def run_maven_dependency_cp(repo_path, target_java_version="8") -> list[str]:
    """
    Run Maven to copy dependencies and return all dependency jar paths.
    """
    print("Running Maven command to copy dependencies")
    result = Maven(target_java_version=target_java_version).copy_deps(repo_path)
    if result.status != 0:
        raise RuntimeError(f"Maven command failed with status {result.status}: {result.stderr}")
    return get_all_dependency_jars(repo_path)


def update_pom_for_regression_tests(repo_path: str):
    """
    Parse the pom.xml file and add the needed plugin tags for executing regression tests.
    Specifically, add the build-helper-maven-plugin (to add randoop-tests as a test source)
    and the maven-surefire-plugin (to include RegressionTest* classes), and add a JUnit dependency if missing.
    In a multi-module child pom, uses "${project.parent.basedir}/randoop-tests",
    otherwise "${project.basedir}/randoop-tests".
    """
    pom_path = os.path.join(repo_path, "pom.xml")
    if not os.path.exists(pom_path):
        raise RuntimeError("No pom.xml found; skipping pom update.")

    ET.register_namespace("", "http://maven.apache.org/POM/4.0.0")
    tree = ET.parse(pom_path)
    root = tree.getroot()
    ns = {"m": "http://maven.apache.org/POM/4.0.0"}

    parent_elem = root.find("m:parent", ns)
    if parent_elem is not None:
        randoop_source = "${project.parent.basedir}/randoop-tests"
    else:
        randoop_source = "${project.basedir}/randoop-tests"

    build = root.find("m:build", ns)
    if build is None:
        build = ET.SubElement(root, "build")

    plugins = build.find("m:plugins", ns)
    if plugins is None:
        plugins = ET.SubElement(build, "plugins")

    def plugin_exists(group_id, artifact_id):
        for plugin in plugins.findall("m:plugin", ns):
            g = plugin.find("m:groupId", ns)
            a = plugin.find("m:artifactId", ns)
            if g is not None and a is not None and g.text.strip() == group_id and a.text.strip() == artifact_id:
                return plugin
        return None

    if plugin_exists("org.codehaus.mojo", "build-helper-maven-plugin") is None:
        helper_plugin = ET.Element("plugin")
        ET.SubElement(helper_plugin, "groupId").text = "org.codehaus.mojo"
        ET.SubElement(helper_plugin, "artifactId").text = "build-helper-maven-plugin"
        ET.SubElement(helper_plugin, "version").text = "3.2.0"
        executions = ET.SubElement(helper_plugin, "executions")
        execution = ET.SubElement(executions, "execution")
        ET.SubElement(execution, "id").text = "add-test-source"
        ET.SubElement(execution, "phase").text = "generate-test-sources"
        goals = ET.SubElement(execution, "goals")
        ET.SubElement(goals, "goal").text = "add-test-source"
        configuration = ET.SubElement(execution, "configuration")
        sources = ET.SubElement(configuration, "sources")
        ET.SubElement(sources, "source").text = randoop_source
        plugins.append(helper_plugin)

    if plugin_exists("org.apache.maven.plugins", "maven-surefire-plugin") is None:
        surefire_plugin = ET.Element("plugin")
        ET.SubElement(surefire_plugin, "groupId").text = "org.apache.maven.plugins"
        ET.SubElement(surefire_plugin, "artifactId").text = "maven-surefire-plugin"
        ET.SubElement(surefire_plugin, "version").text = "2.22.2"
        configuration = ET.SubElement(surefire_plugin, "configuration")
        includes = ET.SubElement(configuration, "includes")
        ET.SubElement(includes, "include").text = "**/*Test.class"
        ET.SubElement(includes, "include").text = "**/RegressionTest*.class"
        plugins.append(surefire_plugin)

    # Add JUnit dependency if not present.
    dependencies = root.find("m:dependencies", ns)
    if dependencies is None:
        dependencies = ET.SubElement(root, "dependencies")
    junit_found = False
    for dep in dependencies.findall("m:dependency", ns):
        group = dep.find("m:groupId", ns)
        if group is not None and group.text is not None and group.text.strip() == "junit":
            junit_found = True
            break
    if not junit_found:
        junit_dep = ET.Element("dependency")
        ET.SubElement(junit_dep, "groupId").text = "junit"
        ET.SubElement(junit_dep, "artifactId").text = "junit"
        ET.SubElement(junit_dep, "version").text = "4.13.2"
        ET.SubElement(junit_dep, "scope").text = "test"
        dependencies.append(junit_dep)
        print("Added JUnit dependency to pom.")

    tree.write(pom_path, encoding="utf-8", xml_declaration=True)
    print(f"POM file at {pom_path} updated for regression tests.")


def create_dedicated_test_module(repo_path: Path):
    """
    Create a dedicated test module named 'randoop-tests' in the repository root if it doesn't exist.
    Generates a minimal pom.xml for it that depends on all modules from the aggregator pom.
    """
    test_module_dir = repo_path / "randoop-tests"
    if not test_module_dir.exists():
        print(f"Creating dedicated test module folder at {test_module_dir}")
        test_module_dir.mkdir()
    test_module_pom = test_module_dir / "pom.xml"
    if test_module_pom.exists():
        print("Dedicated test module pom.xml already exists.")
        return

    # Read the parent (aggregator) pom for info.
    parent_pom_path = repo_path / "pom.xml"
    if not parent_pom_path.exists():
        raise RuntimeError("No aggregator pom.xml found in repository root.")
    tree = ET.parse(str(parent_pom_path))
    root = tree.getroot()
    ns = {"m": "http://maven.apache.org/POM/4.0.0"}
    parent_group = root.find("m:groupId", ns)
    if parent_group is None:
        parent_group = root.find("m:parent/m:groupId", ns)
    parent_artifact = root.find("m:artifactId", ns)
    parent_version = root.find("m:version", ns)
    if parent_version is None:
        parent_version = root.find("m:parent/m:version", ns)
    parent_group = parent_group.text.strip() if parent_group is not None else "unknown.group"
    parent_artifact = (
        parent_artifact.text.strip()
        if parent_artifact is not None and parent_artifact.text is not None
        else "unknown-artifact"
    )
    parent_version = (
        parent_version.text.strip()
        if parent_version is not None and parent_version.text is not None
        else "0.0.1-SNAPSHOT"
    )

    # Get modules from the parent's <modules>
    modules_elem = root.find("m:modules", ns)
    deps_xml = ""
    if modules_elem is not None:
        for mod in modules_elem.findall("m:module", ns):
            mod_text = mod.text.strip()
            if mod_text != "randoop-tests":
                deps_xml += "    <dependency>\n"
                deps_xml += f"      <groupId>{parent_group}</groupId>\n"
                deps_xml += f"      <artifactId>{mod_text}</artifactId>\n"
                deps_xml += f"      <version>{parent_version}</version>\n"
                deps_xml += "    </dependency>\n"
    pom_template = f"""<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0" 
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 
         http://maven.apache.org/xsd/maven-4.0.0.xsd">
  <modelVersion>4.0.0</modelVersion>
  <parent>
    <groupId>{parent_group}</groupId>
    <artifactId>{parent_artifact}</artifactId>
    <version>{parent_version}</version>
    <relativePath>../pom.xml</relativePath>
  </parent>
  <artifactId>randoop-tests</artifactId>
  <packaging>jar</packaging>
  <name>Randoop Generated Tests</name>
  <dependencies>
{deps_xml}    <dependency>
      <groupId>junit</groupId>
      <artifactId>junit</artifactId>
      <version>4.13.2</version>
      <scope>test</scope>
    </dependency>
  </dependencies>
  <build>
    <plugins>
      <plugin>
        <groupId>org.codehaus.mojo</groupId>
        <artifactId>build-helper-maven-plugin</artifactId>
        <version>3.2.0</version>
        <executions>
          <execution>
            <id>add-test-source</id>
            <phase>generate-test-sources</phase>
            <goals>
              <goal>add-test-source</goal>
            </goals>
            <configuration>
              <sources>
                <source>${{project.parent.basedir}}/randoop-tests</source>
              </sources>
            </configuration>
          </execution>
        </executions>
      </plugin>
      <plugin>
        <groupId>org.apache.maven.plugins</groupId>
        <artifactId>maven-surefire-plugin</artifactId>
        <version>2.22.2</version>
        <configuration>
          <includes>
            <include>**/*Test.class</include>
            <include>**/RegressionTest*.class</include>
          </includes>
        </configuration>
      </plugin>
    </plugins>
  </build>
</project>
"""
    test_module_pom.write_text(pom_template, encoding="utf-8")
    print(f"Created pom.xml for dedicated test module at {test_module_pom}")


def update_parent_modules_for_test_module(repo_path: Path) -> None:
    """
    Update the aggregator pom.xml (in repo_path) to include the "randoop-tests" module
    if it is not already present. This implementation uses lxml to produce clean output,
    avoiding unwanted namespace prefixes.
    """
    parent_pom_path = repo_path / "pom.xml"
    if not parent_pom_path.exists():
        print("No parent pom.xml found.")
        return

    # Parse the pom.xml using lxml with an XMLParser that preserves formatting.
    parser = etree.XMLParser(remove_blank_text=True)
    tree = etree.parse(str(parent_pom_path), parser)
    root = tree.getroot()
    ns = "http://maven.apache.org/POM/4.0.0"

    # Find or create the <modules> element.
    modules = root.find("{%s}modules" % ns)
    if modules is None:
        modules = etree.SubElement(root, "{%s}modules" % ns)

    # Check if a <module> element with text "randoop-tests" exists.
    found = False
    for module in modules.findall("{%s}module" % ns):
        if module.text and module.text.strip() == "randoop-tests":
            found = True
            break

    if not found:
        new_module = etree.Element("{%s}module" % ns)
        new_module.text = "randoop-tests"
        modules.append(new_module)
        # Write out with pretty printing. lxml will use the default namespace (without extra prefixes).
        tree.write(str(parent_pom_path), pretty_print=True, xml_declaration=True, encoding="utf-8")
        print("Updated parent pom.xml to include randoop-tests module.")
    else:
        print("Parent pom.xml already includes the randoop-tests module.")


def execute_randoop(classpath: str, class_list_file: str) -> tuple[str, str]:
    """
    Execute Randoop with the given classpath and class list.
    Returns stdout and stderr if an error occurs.
    """
    cmd = ["java", "-classpath", classpath, "randoop.main.Main"] + RANDOOP_OPTIONS + [f"--classlist={class_list_file}"]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, cmd, output=result.stdout, stderr=result.stderr)
    return result.stdout, result.stderr


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


def create_git_diff(repo_path) -> str:
    """
    Stage changes and create a Git diff patch file.
    """
    subprocess.run(["git", "add", "."], cwd=str(repo_path), check=True)
    diff = subprocess.check_output(["git", "diff", "--cached"], cwd=str(repo_path))
    diff_file = os.path.join(repo_path, "randoop_diff.patch")
    with open(diff_file, "wb") as f:
        f.write(diff)
    print(f"Git diff saved to: {diff_file}")
    return diff_file


def run_randoop_on_repo(repo_path: Path, randoop_jar_path: Path) -> Path:
    """
    Run Randoop on the given repository:
      - Installs the project.
      - Creates/updates a dedicated test module for Randoop tests.
      - Updates all pom files for regression test configuration.
      - Finds compiled class directories.
      - Gets dependency jars.
      - Generates the class list file.
      - Combines these into a full classpath and runs Randoop,
        retrying up to NUM_RETRIES times and removing any failing classes.
      - Creates a Git diff with the changes.
    """
    original_cwd = os.getcwd()
    try:
        os.chdir(repo_path)
        print(f"\nProcessing repository: {repo_path}")

        if not Maven(target_java_version="8").install(repo_path, skip_tests=True).status == 0:
            raise RuntimeError("Maven install failed. Skipping.")

        if not os.path.exists(os.path.join(repo_path, ".git")):
            raise RuntimeError("Error: Not a valid Git repository. Skipping.")

        # Find candidate compiled classes directories.
        compiled_dirs = find_compiled_classes_dirs(repo_path)
        if not compiled_dirs:
            raise RuntimeError("No compiled classes directories found. Please build your project first.")

        # Generate the class list file.
        class_list_file = generate_class_list(repo_path, compiled_dirs)
        if not class_list_file:
            raise RuntimeError("Failed to generate class list. Skipping Randoop execution.")

        # Get dependencies.
        dependency_cp = ""
        if os.path.exists(os.path.join(repo_path, "pom.xml")):
            dependency_cp = run_maven_dependency_cp(repo_path)
        additional_jars = get_all_dependency_jars(str(repo_path))
        separator = ":" if os.name != "nt" else ";"
        classpath_elements = compiled_dirs + [str(randoop_jar_path)] + additional_jars
        if dependency_cp:
            classpath = separator.join(classpath_elements) + separator + separator.join(dependency_cp)
        else:
            classpath = separator.join(classpath_elements)

        # Ensure output directory for Randoop tests exists.
        output_dir = repo_path / "randoop-tests"
        if not output_dir.exists():
            output_dir.mkdir()

        success = False
        for attempt in range(1, NUM_RETRIES + 1):
            print(f"Randoop run attempt {attempt} of {NUM_RETRIES}...")
            try:
                stdout, stderr = execute_randoop(classpath, class_list_file)
                print("Randoop completed successfully.")
                success = True
                break
            except subprocess.CalledProcessError as e:
                print("Randoop failed")
                failing_class = extract_failing_class(e.stdout)
                if not failing_class:
                    print("Could not extract failing class; aborting retries.")
                    break
                remove_class_from_list(class_list_file, failing_class)
        if not success:
            raise RuntimeError("Randoop did not complete successfully after retries.")

        # Clean up temporary classlist and cp files.
        if os.path.exists(Path(repo_path) / "classlist.txt"):
            os.remove(Path(repo_path) / "classlist.txt")
        if os.path.exists(Path(repo_path) / "cp.txt"):
            os.remove(Path(repo_path) / "cp.txt")

        # Create the dedicated test module and update the parent's modules.
        create_dedicated_test_module(repo_path)
        update_parent_modules_for_test_module(repo_path)

        # Update all pom files for regression test configuration.
        # update_pom_for_regression_tests(str(repo_path))
        dedicated_test_pom = repo_path / "randoop-tests" / "pom.xml"
        update_pom_for_regression_tests(str(dedicated_test_pom.parent))

        # Stage changes and generate a Git diff.
        diff_file = create_git_diff(repo_path)
        return Path(diff_file)

    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Error processing repo {repo_path}: {e}")
    finally:
        os.chdir(original_cwd)


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
    repos = [Path("/home/user/java-migration-paper/data/workspace/nydiarra_springboot-jwt")]  # sys.argv[1:]
    for repo in repos:
        if os.path.isdir(repo):
            run_randoop_on_repo(repo, Path("/home/user/java-migration-paper/randoop-4.3.3/randoop-all-4.3.3.jar"))
        else:
            print(f"Path does not exist or is not a directory: {repo}")


if __name__ == "__main__":
    main()
