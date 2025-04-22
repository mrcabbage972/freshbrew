import subprocess
from pathlib import Path
from typing import Optional, List

import xmltodict

from java_migration.eval.data_model import TestCoverage, CoverageSummary
from java_migration.maven.maven_pom_editor import MavenPomEditor
from java_migration.maven.maven_project import MavenProject




# JaCoCo plugin version to use
JACOCO_VERSION = "0.8.8"

def ensure_jacoco_argline(editor: MavenPomEditor) -> bool:
    """
    Ensures the JaCoCo agent property ${argLine} is included in the <argLine>
    configuration of maven-surefire-plugin and maven-failsafe-plugin if they exist.

    It checks the <configuration> section of each plugin. If <argLine> exists,
    it ensures ${argLine} is present (appends if missing). If <argLine> does not
    exist, it creates it with ${argLine}.

    :param editor: An initialized MavenPomEditor instance for the target pom.xml.
    :return: True if the POM was modified, False otherwise.
    """
    plugins_to_configure = [
        ("org.apache.maven.plugins", "maven-surefire-plugin"),
        ("org.apache.maven.plugins", "maven-failsafe-plugin"),
    ]
    modified = False
    argline_prop = "${argLine}"

    for group_id, artifact_id in plugins_to_configure:
        plugin_element = editor.get_plugin(group_id, artifact_id)

        if plugin_element is not None:
            print(f"Checking plugin: {group_id}:{artifact_id} in {editor.pom_file}")
            # 1. Ensure the <configuration> element exists within the plugin
            #    ensure_element returns the element, creating it if necessary.
            #    Note: ensure_element calls _save() internally if it *creates* the element.
            config_element = editor.ensure_element(plugin_element, "m:configuration")

            # 2. Find the <argLine> element within the configuration
            #    We use xpath directly here to handle existence checks gracefully.
            argline_elements = config_element.xpath("m:argLine", namespaces=editor.namespaces)

            if not argline_elements:
                # 3a. <argLine> does not exist - create it with ${argLine}
                print(f"  Adding <argLine>{argline_prop}</argLine>")
                # Use create_sub_element as ensure_element might overwrite text if called with text=
                editor.create_sub_element(config_element, "m:argLine", text=argline_prop)
                modified = True
            else:
                # 3b. <argLine> exists - check and potentially update its content
                argline_element = argline_elements[0]
                current_text = argline_element.text if argline_element.text else ""

                if argline_prop not in current_text:
                    # Append ${argLine}, preserving existing args
                    # Add a space only if current_text is not empty/whitespace
                    separator = " " if current_text.strip() else ""
                    new_text = current_text.strip() + separator + argline_prop
                    print(f"  Updating <argLine> to: {new_text}")
                    argline_element.text = new_text
                    modified = True
                else:
                    print(f"  <argLine> already contains {argline_prop}")

    # Save the file *if* any modifications were made by create_sub_element
    # or by directly setting .text
    if modified:
        print(f"Saving changes to {editor.pom_file}")
        editor._save() # Ensure all changes are written

    return modified


def _install_all_modules(repo: Path, use_wrapper: bool, target_java_version: str) -> None:
    """
    Pre‑install every module in the reactor so that snapshot
    dependencies (e.g. base, logic, comet, web) are available
    before running randoop-tests or coverage.
    """
    mvn_cmd = str(repo / "mvnw") if use_wrapper and (repo / "mvnw").exists() else "mvn"
    cmd = [
        mvn_cmd,
        "install",
        "-DskipTests=true",
        "-DskipITs=true",
        "-DskipDocs=true",
        "-B",
        "-ntp",
        f"-Dmaven.compiler.source={target_java_version}",
        f"-Dmaven.compiler.target={target_java_version}",
        "-Dmaven.test.failure.ignore=true",
    ]
    print(f"Installing modules: {' '.join(cmd)}")
    subprocess.run(cmd, cwd=repo, check=True, capture_output=True)


def _run_maven_with_jacoco(repo: Path, use_wrapper: bool, target_java_version) -> None:
    mvn_cmd = str(repo / "mvnw") if use_wrapper and (repo / "mvnw").exists() else "mvn"
    goals = [        
        f"org.jacoco:jacoco-maven-plugin:{JACOCO_VERSION}:prepare-agent",
        "test",
        f"org.jacoco:jacoco-maven-plugin:{JACOCO_VERSION}:report",
        f"org.jacoco:jacoco-maven-plugin:{JACOCO_VERSION}:report-aggregate",
    ]
    cmd = [mvn_cmd] + goals + [
        "-B",
        "-ntp",
        "-Dmaven.test.failure.ignore=true",
        f"-Dmaven.compiler.source={target_java_version}",
        f"-Dmaven.compiler.target={target_java_version}",
    ]
    print(f"Running JaCoCo goals: {' '.join(cmd)}")
    subprocess.run(cmd, cwd=repo, check=True, capture_output=True)


def _find_jacoco_reports(repo: Path) -> List[Path]:
    """
    Find all jacoco.xml files under any target/site/jacoco* directory.
    """
    return list(repo.glob("**/target/site/jacoco*/jacoco.xml"))


def _parse_one_report(xml_path: Path) -> dict:
    """
    Parse a single jacoco.xml and return a dict:
      { "LINE": {"missed": int, "covered": int},
        "METHOD": {"missed": int, "covered": int} }
    """
    data = xmltodict.parse(xml_path.read_text(encoding="utf-8"))
    report = data.get("report", {})
    counters = {t: {"missed": 0, "covered": 0} for t in ("LINE", "METHOD")}

    def recurse(node):
        if isinstance(node, dict):
            typ = node.get("@type")
            if typ in counters:
                counters[typ]["missed"]  += int(node.get("@missed",  0))
                counters[typ]["covered"] += int(node.get("@covered", 0))
            for v in node.values():
                recurse(v)
        elif isinstance(node, list):
            for item in node:
                recurse(item)

    recurse(report)
    return counters


def _aggregate_counters(all_counters: List[dict]) -> TestCoverage:
    """
    Sum up multiple counter dicts into a single TestCoverage.
    """
    agg = {t: {"missed": 0, "covered": 0} for t in ("LINE", "METHOD")}
    for c in all_counters:
        for t in agg:
            agg[t]["missed"]  += c[t]["missed"]
            agg[t]["covered"] += c[t]["covered"]

    def make_summary(d):
        total = d["missed"] + d["covered"]
        pct   = (d["covered"] / total * 100) if total > 0 else 0.0
        return CoverageSummary(
            missed=d["missed"],
            covered=d["covered"],
            total=total,
            percent=pct
        )

    return TestCoverage(
        LINE=make_summary(agg["LINE"]),
        METHOD=make_summary(agg["METHOD"])
    )


def get_test_cov(repo_path: str, use_wrapper: bool = False, target_java_version: str = "8") -> Optional[TestCoverage]:
    """
    1. Pre‑install all modules so snapshot dependencies for randoop-tests resolve.
    2. Instrument & run tests with JaCoCo, generating per-module and aggregate reports.
    3. Globs for every jacoco.xml under target/site/jacoco*.
    4. Parses & sums all LINE/METHOD counters.
    Returns None if no reports were found.
    """
    repo = Path(repo_path)
    if not repo.is_dir():
        raise FileNotFoundError(f"Repo path not found: {repo_path}")

    project = MavenProject(repo / "pom.xml")
    root_editor = project.get_pom_editor()
    ensure_jacoco_argline(root_editor)    

    # 1) Ensure all modules are installed locally
    _install_all_modules(repo, use_wrapper, target_java_version)

    # 2) Run Maven + JaCoCo goals
    _run_maven_with_jacoco(repo, use_wrapper, target_java_version)

    # 3) Find generated jacoco.xml files
    reports = _find_jacoco_reports(repo)
    if not reports:
        print("❗ No jacoco.xml files found under target/site/jacoco*")
        return None

    # 4) Parse each, collect counters
    all_counts = []
    for rpt in reports:
        try:
            all_counts.append(_parse_one_report(rpt))
        except Exception as e:
            print(f"Warning: failed to parse {rpt}: {e}")

    if not all_counts:
        print("❗ No valid coverage data could be parsed.")
        return None

    # 5) Aggregate and return
    coverage = _aggregate_counters(all_counts)
    print(f"Aggregated Coverage → LINE: {coverage.LINE.percent:.2f}%, "
          f"METHOD: {coverage.METHOD.percent:.2f}%")
    return coverage


if __name__ == "__main__":
    # Example invocation; replace with CLI parsing as needed
    path    = "/home/user/java-migration-paper/data/workspace/scxwhite_hera"
    wrapper = False

    coverage = get_test_cov(path, wrapper)
    if coverage:
        print(f"Final: {coverage.LINE.covered}/{coverage.LINE.total} lines "
              f"({coverage.LINE.percent:.2f}%)")
    else:
        print("Coverage could not be determined.")
