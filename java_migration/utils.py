import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent


def maven_test(repo_path: Path, skip_tests: bool = False, target_java_version: str = "17") -> str:
    cmd = [
        "mvn",
        "-B",  # Batch mode
        "test",
        "-Dorg.slf4j.simpleLogger.log.org.apache.maven.cli.transfer.Slf4jMavenTransferListener=warn",
        f"-Dmaven.compiler.source={target_java_version}",
        f"-Dmaven.compiler.target={target_java_version}",
    ]
    if skip_tests:
        cmd.append("-DskipTests")
    result = subprocess.run(cmd, capture_output=True, cwd=repo_path)
    return result.stdout.decode("utf-8")


def maven_verify(
    repo_path: Path, skip_tests: bool = False, target_java_version: str = "17", clean: bool = False
) -> str:
    cmd = [
        "mvn",
        "-B",  # Batch mode
        "verify",
        "-Dorg.slf4j.simpleLogger.log.org.apache.maven.cli.transfer.Slf4jMavenTransferListener=warn",
        f"-Dmaven.compiler.source={target_java_version}",
        f"-Dmaven.compiler.target={target_java_version}",
    ]
    if skip_tests:
        cmd.append("-DskipTests")
        cmd.append("-DskipITs")
    if clean:
        cmd.insert(1, "clean")
    result = subprocess.run(cmd, capture_output=True, cwd=repo_path)
    return result.stdout.decode("utf-8")


def validate_xml(xml_content: str):
    try:
        import xml.etree.ElementTree as ET
    except ImportError as e:
        raise ImportError("Python's built-in xml.etree.ElementTree module is required but not available.") from e
    try:
        # Try parsing the XML content
        ET.fromstring(xml_content)
    except ET.ParseError as pe:
        raise ValueError(f"XML is not well-formed: {str(pe)}")
    except Exception as e:
        raise ValueError(f"An unexpected error occurred: {str(e)}")


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
