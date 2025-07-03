#!/usr/bin/env python3
"""
get_commit_dates_yaml.py

Read a YAML list of objects with keys:
  repo_name: owner/repo
  commit:    <sha>
Fetch the committer date for each commit via GitHub's REST API
and write a new YAML file that includes commit_date for every item.

Usage:
  python get_commit_dates_yaml.py commits.yaml
  python get_commit_dates_yaml.py commits.yaml -o dated.yaml
"""

from __future__ import annotations

import os
import pathlib
import sys
import time
from typing import Dict, List

import requests
import yaml
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()


API_ROOT = "https://api.github.com/repos"
TOKEN = os.getenv("GITHUB_TOKEN")  # set this to raise your limit to 5 000 req/h


def fetch_commit_date(repo: str, sha: str) -> str:
    """Return ISO-8601 committer date for repo@sha."""
    url = f"{API_ROOT}/{repo}/commits/{sha}"
    headers = {"Accept": "application/vnd.github+json"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    r = requests.get(url, headers=headers, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"{repo}@{sha}: HTTP {r.status_code} – {r.text[:200]}")
    return r.json()["commit"]["committer"]["date"]  # e.g. '2025-01-04T14:22:37Z'


def enrich(data: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Return a new list with commit_date added (empty on failure)."""
    enriched = []
    for item in tqdm(data):
        repo = item["repo_name"]
        sha = item["commit"]
        try:
            date = fetch_commit_date(repo, sha)
        except Exception as exc:
            print(f"Warning: {exc}", file=sys.stderr)
            date = ""  # leave blank if fetch fails
        enriched.append({**item, "commit_date": date})
        time.sleep(1)
    return enriched


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] in {"-h", "--help"}:
        print(__doc__)
        return

    in_path = pathlib.Path(sys.argv[1])
    out_path = (
        pathlib.Path(sys.argv[sys.argv.index("-o") + 1])
        if "-o" in sys.argv
        else in_path.with_stem(in_path.stem + "_with_dates")
    )

    # --- read YAML ---
    try:
        data = yaml.safe_load(in_path.read_text(encoding="utf-8"))
        assert isinstance(data, list), "Top-level YAML value must be a list"
    except Exception as exc:
        sys.exit(f"❌ Failed to parse YAML: {exc}")

    # --- enrich with commit dates ---
    enriched = enrich(data)

    # --- write output YAML ---
    with out_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(enriched, f, sort_keys=False)

    print(f"✔ Wrote {out_path} ({len(enriched)} entries)")


if __name__ == "__main__":
    main()
