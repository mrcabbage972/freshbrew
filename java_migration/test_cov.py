import subprocess
from pathlib import Path
from typing import Optional, List

import xmltodict

from java_migration.eval.data_model import TestCoverage, CoverageSummary

# JaCoCo plugin version to use
JACOCO_VERSION = "0.8.8"


def _run_maven_with_jacoco(repo: Path, use_wrapper: bool) -> None:
    """
    Runs:
      mvn clean \
          org.jacoco:jacoco-maven-plugin:{JACOCO_VERSION}:prepare-agent \
          test \
          org.jacoco:jacoco-maven-plugin:{JACOCO_VERSION}:report \
          org.jacoco:jacoco-maven-plugin:{JACOCO_VERSION}:report-aggregate \
        -B -ntp -Dmaven.test.failure.ignore=true
    """
    mvn_cmd = str(repo / "mvnw") if use_wrapper and (repo / "mvnw").exists() else "mvn"
    goals = [
        "clean",
        f"org.jacoco:jacoco-maven-plugin:{JACOCO_VERSION}:prepare-agent",
        "test",
        f"org.jacoco:jacoco-maven-plugin:{JACOCO_VERSION}:report",
        f"org.jacoco:jacoco-maven-plugin:{JACOCO_VERSION}:report-aggregate",
    ]
    cmd = [mvn_cmd] + goals + [
        "-B",
        "-ntp",
        "-Dmaven.test.failure.ignore=true"
    ]
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


def get_test_cov(repo_path: str, use_wrapper: bool = False) -> Optional[TestCoverage]:
    """
    1. Instruments & runs all tests + generates both per-module and aggregate
       jacoco.xml reports.
    2. Globs for every jacoco.xml under target/site/jacoco*.
    3. Parses & sums all LINE/METHOD counters.
    Returns None if no reports were found.
    """
    repo = Path(repo_path)
    if not repo.is_dir():
        raise FileNotFoundError(f"Repo path not found: {repo_path}")

    # 1) Run Maven with JaCoCo plugin directly
    _run_maven_with_jacoco(repo, use_wrapper)

    # 2) Find all generated jacoco.xml files
    reports = _find_jacoco_reports(repo)
    if not reports:
        print("❗ No jacoco.xml files found under target/site/jacoco*")
        return None

    # 3) Parse each, collect counters
    all_counts = []
    for rpt in reports:
        try:
            all_counts.append(_parse_one_report(rpt))
        except Exception as e:
            print(f"Warning: failed to parse {rpt}: {e}")

    if not all_counts:
        print("❗ No valid coverage data could be parsed.")
        return None

    # 4) Aggregate and return
    coverage = _aggregate_counters(all_counts)
    print(f"Aggregated Coverage → LINE: {coverage.LINE.percent:.2f}%, "
          f"METHOD: {coverage.METHOD.percent:.2f}%")
    return coverage



if __name__ == "__main__":
    import sys

    # if len(sys.argv) < 2:
    #     print("Usage: python coverage_runner.py <repo_path> [--wrapper]")
    #     sys.exit(1)

    #path = sys.argv[1]
    path = "/home/user/java-migration-paper/data/workspace/wenweihu86_raft-java"
    wrapper = False
    #wrapper = "--wrapper" in sys.argv[2:]
    coverage = get_test_cov(path, wrapper)
    if coverage:
        print(f"Final: {coverage.LINE.covered}/{coverage.LINE.total} lines ({coverage.LINE.percent:.2f}%)")
    else:
        print("Coverage could not be determined.")
