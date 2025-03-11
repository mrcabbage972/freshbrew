from pathlib import Path
import subprocess


REPO_ROOT = Path(__file__).parent.parent


def maven_install(repo_path: Path) -> str:
    cmd = [
        "mvn",
        "-B",
        "-U",
        "install",
        "-Dorg.slf4j.simpleLogger.log.org.apache.maven.cli.transfer.Slf4jMavenTransferListener=warn",
    ]
    result = subprocess.run(cmd, capture_output=True, cwd=repo_path)
    return result.stdout.decode("utf-8")


def maven_test(repo_path: Path, skip_tests=False) -> str:
    cmd = [
        "mvn",
        "-B",
        "-U",
        "test",
        "-Dorg.slf4j.simpleLogger.log.org.apache.maven.cli.transfer.Slf4jMavenTransferListener=warn",
    ]
    if skip_tests:
        cmd.append("-DskipTests")
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
