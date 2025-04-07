#!/usr/bin/env python3
import glob
import os
import subprocess
import sys
import logging
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

RANDOOP_OPTIONS = [
    "gentests",
    "--no-error-revealing-tests=true",
    "--junit-output-dir=randoop-tests",
    "--time-limit=20",
    "--output-limit=100",
]


def find_compiled_classes_dirs(repo_path):
    """
    Use glob to find candidate directories for compiled classes.
    Looks for directories matching common patterns such as:
      - **/target/classes
      - **/build/classes
      - **/bin
    Only returns those that contain at least one .class file.
    """
    patterns = [
        os.path.join(repo_path, "**", "target", "classes"),
        os.path.join(repo_path, "**", "build", "classes"),
        os.path.join(repo_path, "**", "bin"),
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
    For each candidate compiled classes directory, walk through its files and write
    fully qualified class names (based on the relative path from that directory) into a file.
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
    logger.info(f"Generated class list at {class_list_path}")
    return class_list_path


def run_maven_dependency_cp(repo_path):
    """
    Run the Maven command to build the dependency classpath.
    The command writes the classpath to cp.txt in the repo's root.
    """
    cp_file = os.path.join(repo_path, "cp.txt")
    mvn_cmd = ["mvn", "dependency:build-classpath", f"-Dmdep.outputFile={cp_file}", "-DskipTests"]
    logger.info("Running Maven command to generate dependency classpath:")
    logger.info(" ".join(mvn_cmd))
    subprocess.run(mvn_cmd, cwd=repo_path, check=True)
    if os.path.exists(cp_file):
        with open(cp_file, "r") as f:
            cp = f.read().strip()
            logger.info(f"Dependency classpath from Maven: {cp}")
            return cp
    else:
        logger.info("Maven did not generate cp.txt. No dependency classpath found.")
        return ""


def update_pom_for_regression_tests(repo_path):
    """
    Parse the pom.xml file and add the needed plugin tags for executing regression tests.
    Specifically, add the build-helper-maven-plugin (to add randoop-tests as a test source)
    and the maven-surefire-plugin (to include RegressionTest* classes), if they are missing.
    """
    pom_path = os.path.join(repo_path, "pom.xml")
    if not os.path.exists(pom_path):
        logger.info("No pom.xml found; skipping pom update.")
        return

    # Register the Maven POM namespace.
    ET.register_namespace("", "http://maven.apache.org/POM/4.0.0")
    tree = ET.parse(pom_path)
    root = tree.getroot()
    ns = {"m": "http://maven.apache.org/POM/4.0.0"}

    # Find or create the <build> element.
    build = root.find("m:build", ns)
    if build is None:
        build = ET.SubElement(root, "build")

    # Find or create the <plugins> element.
    plugins = build.find("m:plugins", ns)
    if plugins is None:
        plugins = ET.SubElement(build, "plugins")

    def plugin_exists(group_id, artifact_id):
        for plugin in plugins.findall("m:plugin", ns):
            g = plugin.find("m:groupId", ns)
            a = plugin.find("m:artifactId", ns)
            if g is not None and a is not None and g.text == group_id and a.text == artifact_id:
                return plugin
        return None

    # Add build-helper-maven-plugin if missing.
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
        ET.SubElement(sources, "source").text = "${project.basedir}/randoop-tests"
        plugins.append(helper_plugin)

    # Add maven-surefire-plugin if missing.
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

    tree.write(pom_path, encoding="utf-8", xml_declaration=True)
    logger.info("POM file updated for regression tests.")


def run_randoop_on_repo(repo_path, randoop_jar_path):
    """
    Run Randoop on the given repository:
      - Updates the pom file so that the regression tests are executed.
      - Finds compiled class directories.
      - Runs Maven to generate the dependency classpath.
      - Generates a class list file.
      - Combines these into a full classpath and runs Randoop.
      - Captures a Git diff with the changes.
    """
    original_cwd = os.getcwd()
    try:
        os.chdir(repo_path)
        logger.info(f"\nProcessing repository: {repo_path}")

        if not os.path.exists(os.path.join(repo_path, ".git")):
            logger.info("Error: Not a valid Git repository. Skipping.")
            return

        # Update the pom file so that regression tests are executed.
        update_pom_for_regression_tests(repo_path)

        # Find candidate compiled classes directories.
        compiled_dirs = find_compiled_classes_dirs(repo_path)
        if not compiled_dirs:
            logger.info("No compiled classes directories found. Please build your project first.")
            return
        else:
            logger.info("Found compiled classes directories:")
            for d in compiled_dirs:
                logger.info("  ", d)

        # Generate the class list file.
        class_list_file = generate_class_list(repo_path, compiled_dirs)
        if not class_list_file:
            logger.info("Failed to generate class list. Skipping Randoop execution.")
            return

        # Run Maven to generate dependency classpath, if a pom.xml exists.
        dependency_cp = ""
        if os.path.exists(os.path.join(repo_path, "pom.xml")):
            dependency_cp = run_maven_dependency_cp(repo_path)

        # Build the full classpath: compiled classes, Maven dependency classpath, and Randoop jar.
        separator = ":" if os.name != "nt" else ";"
        classpath_elements = compiled_dirs + [randoop_jar_path]
        if dependency_cp:
            # Maven's cp is already a separator-delimited string; simply append.
            classpath = separator.join(classpath_elements) + separator + dependency_cp
        else:
            classpath = separator.join(classpath_elements)
        logger.info("Full classpath for Randoop:")
        logger.info(classpath)

        # Ensure output directory for Randoop tests exists.
        output_dir = "randoop-tests"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Build and run the Randoop command.
        randoop_cmd = (
            ["java", "-classpath", classpath, "randoop.main.Main"]
            + RANDOOP_OPTIONS
            + [f"--classlist={class_list_file}"]
        )

        logger.info("Running Randoop command:")
        logger.info(" ".join(randoop_cmd))
        subprocess.run(randoop_cmd, check=True)

        # Stage changes and generate a Git diff.
        subprocess.run(["git", "add", "."], check=True)
        diff = subprocess.check_output(["git", "diff", "--cached"])
        diff_file = os.path.join(repo_path, "randoop_diff.patch")
        with open(diff_file, "wb") as f:
            f.write(diff)
        logger.info(f"Git diff saved to: {diff_file}")

    except subprocess.CalledProcessError as e:
        logger.info(f"Error processing repo {repo_path}: {e}")
    finally:
        os.chdir(original_cwd)


def main():
    # if len(sys.argv) < 2:
    #     logger.info("Usage: python script.py <repo_path1> [<repo_path2> ...]")
    #     sys.exit(1)

    repos = ["/home/user/java-migration-paper/data/workspace/springboot-jwt"]  # sys.argv[1:]
    for repo in repos:
        if os.path.isdir(repo):
            run_randoop_on_repo(repo, "/home/user/java-migration-paper/randoop-4.3.3/randoop-all-4.3.3.jar")
        else:
            logger.info(f"Path does not exist or is not a directory: {repo}")


if __name__ == "__main__":
    main()
