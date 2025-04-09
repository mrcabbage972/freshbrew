import os
import re
import subprocess
import xml.etree.ElementTree as ET
from typing import Any, Dict

import xmltodict

from java_migration.eval.data_model import CoverageSummary, TestCoverage


def _aggregate_summary(node: Any, counters: Dict[str, Dict[str, int]]) -> Dict[str, Dict[str, int]]:
    """
    Recursively aggregate missed and covered counts from XML nodes.
    """
    if isinstance(node, dict):
        node_type = node.get("@type")
        if node_type in counters:
            try:
                missed = int(node.get("@missed", 0))
                covered = int(node.get("@covered", 0))
            except (ValueError, TypeError):
                missed, covered = 0, 0
            counters[node_type]["missed"] += missed
            counters[node_type]["covered"] += covered
        # Recurse for all dictionary values
        for value in node.values():
            _aggregate_summary(value, counters)
    elif isinstance(node, list):
        for item in node:
            _aggregate_summary(item, counters)
    return counters


def _parse_coverage_summary(xml_dict: Dict[str, Any]) -> TestCoverage:
    """
    Parse the XML dictionary to compute coverage summaries.
    """
    # Initialize counters for each type we care about.
    counters = {key: {"missed": 0, "covered": 0} for key in ["LINE", "METHOD"]}
    aggregated = _aggregate_summary(xml_dict, counters)

    def make_summary(data: Dict[str, int]) -> CoverageSummary:
        total = data["missed"] + data["covered"]
        percent = (data["covered"] / total) if total > 0 else 0.0
        return CoverageSummary(
            missed=data["missed"],
            covered=data["covered"],
            total=total,
            percent=percent,
        )

    return TestCoverage(LINE=make_summary(aggregated["LINE"]), METHOD=make_summary(aggregated["METHOD"]))


def get_namespace(element):
    """
    Extract the namespace URI from an XML element's tag.
    For example, if element.tag is '{http://maven.apache.org/POM/4.0.0}project',
    this returns 'http://maven.apache.org/POM/4.0.0'.
    """
    m = re.match(r"\{(.*)\}", element.tag)
    return m.group(1) if m else ""


def aggregate_test_coverages(repo_path: str) -> TestCoverage:
    """
    Recursively find all jacoco.xml files under repo_path, parse them into TestCoverage
    objects (using _parse_coverage_summary), and aggregate the results.
    """
    # Initialize aggregated values for each type.
    agg_line = {"missed": 0, "covered": 0}
    agg_method = {"missed": 0, "covered": 0}

    # Walk through the repository looking for jacoco.xml files.
    for root_dir, dirs, files in os.walk(repo_path):
        for file in files:
            if file == "jacoco.xml":
                file_path = os.path.join(root_dir, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        report_dict = xmltodict.parse(f.read())
                    # Parse the XML into a TestCoverage object.
                    tc = _parse_coverage_summary(report_dict)
                    agg_line["missed"] += tc.LINE.missed
                    agg_line["covered"] += tc.LINE.covered
                    agg_method["missed"] += tc.METHOD.missed
                    agg_method["covered"] += tc.METHOD.covered
                except Exception as e:
                    print(f"Error parsing {file_path}: {e}")

    def make_summary(data):
        missed = data["missed"]
        covered = data["covered"]
        total = missed + covered
        percent = (covered / total * 100) if total > 0 else 0.0
        return CoverageSummary(missed=missed, covered=covered, total=total, percent=percent)

    return TestCoverage(LINE=make_summary(agg_line), METHOD=make_summary(agg_method))


def modify_pom_to_enable_jacoco(pom_path: str) -> None:
    """
    Modify the pom.xml file to disable JaCoCo skipping.
    This sets both <jacoco.skip> and <skip.jacoco.plugin> to "false".
    """
    tree = ET.parse(pom_path)
    root = tree.getroot()
    ns_uri = get_namespace(root)
    ns = {"m": ns_uri} if ns_uri else {}

    # Register the namespace as default to avoid outputting prefixes like ns0.
    if ns_uri:
        ET.register_namespace("", ns_uri)

    # Locate or create the <properties> element.
    properties = root.find("m:properties", ns)
    if properties is None:
        properties = ET.Element("properties")
        root.insert(0, properties)

    # Set <jacoco.skip> to false.
    jacoco_skip = properties.find("m:jacoco.skip", ns)
    if jacoco_skip is None:
        jacoco_skip = ET.SubElement(properties, "jacoco.skip")
    jacoco_skip.text = "false"

    # Set <skip.jacoco.plugin> to false.
    skip_jacoco_plugin = properties.find("m:skip.jacoco.plugin", ns)
    if skip_jacoco_plugin is None:
        skip_jacoco_plugin = ET.SubElement(properties, "skip.jacoco.plugin")
    skip_jacoco_plugin.text = "false"

    # Write the modified pom.xml back to disk.
    tree.write(pom_path, encoding="utf-8", xml_declaration=True)


def get_test_cov(repo_path: str, use_wrapper: bool, target_java_version: str) -> tuple:
    """
    Run Maven commands to generate a JaCoCo coverage report and return a tuple:
      (TestCoverage, test_stdout, test_stderr, coverage_stdout, coverage_stderr)
    This version attaches the JaCoCo agent via the -DargLine JVM parameter, ensuring inner classes are instrumented.
    It also modifies the pom.xml file in repo_path to disable jacoco.skip.
    After running the tests and generating reports, it aggregates the TestCoverage objects from each jacoco.xml.
    """
    # --- Modify pom.xml to disable jacoco.skip ---
    pom_path = os.path.join(repo_path, "pom.xml")
    modify_pom_to_enable_jacoco(pom_path)

    # --- Prepare Maven command ---
    build_command = "./mvnw" if use_wrapper else "mvn"
    # Path to the JaCoCo agent JAR in your local Maven repository.
    jacoco_agent_path = (
        f"{os.getenv('HOME')}/.m2/repository/org/jacoco/org.jacoco.agent/0.8.8/org.jacoco.agent-0.8.8-runtime.jar"
    )

    extra_args = f"-Dmaven.compiler.source={target_java_version} -Dmaven.compiler.target={target_java_version}"
    # Attach the JaCoCo agent using the -DargLine JVM property.
    javaagent_arg = f"-DargLine=-javaagent:{jacoco_agent_path}=destfile=target/jacoco.exec,includes=*"

    commands = {
        # Using direct agent attachment instead of the prepare-agent goal.
        "test": f"{build_command} test {javaagent_arg} -ntp --batch-mode {extra_args}",
        "coverage": f"{build_command} org.jacoco:jacoco-maven-plugin:report",
    }

    # --- Run Maven commands and capture outputs ---
    try:
        # Run the test stage.
        test_proc = subprocess.run(commands["test"].split(), capture_output=True, cwd=repo_path, check=False)
        # Run the coverage report stage.
        coverage_proc = subprocess.run(commands["coverage"].split(), capture_output=True, cwd=repo_path, check=False)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Error running coverage command: {e}") from e

    # Decode outputs.
    test_stdout = test_proc.stdout.decode("utf-8", errors="replace")
    test_stderr = test_proc.stderr.decode("utf-8", errors="replace")
    coverage_stdout = coverage_proc.stdout.decode("utf-8", errors="replace")
    coverage_stderr = coverage_proc.stderr.decode("utf-8", errors="replace")

    # --- Aggregate TestCoverage objects from all jacoco.xml files ---
    test_coverage = None
    try:
        test_coverage = aggregate_test_coverages(repo_path)
    except Exception as e:
        print(f"Failed to aggregate TestCoverage objects: {e}")

    return test_coverage, test_stdout, test_stderr, coverage_stdout, coverage_stderr


if __name__ == "__main__":
    path_new = "/home/user/java-migration-paper/data/workspace/springboot-jwt"
    path_old = "/home/user/java-migration-paper/data/tmp/springboot-jwt"
    cov, _, _, _, _ = get_test_cov(repo_path=path_new, use_wrapper=False, target_java_version="8")
    print(cov)
