import subprocess
from dataclasses import dataclass
from typing import Any, Dict
from pathlib import Path
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


def get_test_cov(repo_path: str, use_wrapper: bool, target_java_version: str) -> TestCoverage:
    """
    Run Maven commands to generate a JaCoCo coverage report and return a TestCoverage dataclass.
    """
    build_command = "./mvnw" if use_wrapper else "mvn"
    jacoco_plugin = "org.jacoco:jacoco-maven-plugin:0.8.8"
    extra_args = f"-Dmaven.compiler.source={target_java_version} -Dmaven.compiler.target={target_java_version}"

    commands = {
        "test": f"{build_command} {jacoco_plugin}:prepare-agent clean test -ntp --batch-mode {extra_args}",
        "coverage": f"{build_command} {jacoco_plugin}:report",
        "coverage_file": "cat target/site/jacoco/jacoco.xml",
    }

    # Run the coverage report command to generate the XML file.
    try:
        subprocess.run(commands["test"].split(), capture_output=True, cwd=repo_path, check=True)
        subprocess.run(commands["coverage"].split(), capture_output=True, cwd=repo_path, check=True)
        cov_file_result = subprocess.run(
            commands["coverage_file"].split(), capture_output=True, cwd=repo_path, check=True
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Error running coverage command: {e}") from e

    try:
        report = cov_file_result.stdout.decode("utf-8")
        report_dict = xmltodict.parse(report)
    except Exception as e:
        raise ValueError(f"Failed to parse JaCoCo XML report: {e}") from e

    return _parse_coverage_summary(report_dict)


if __name__ == "__main__":
    print(
        get_test_cov(repo_path="/Users/mayvic/Documents/git/springboot-jwt", use_wrapper=False, target_java_version="8")
    )
