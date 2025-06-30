#!/usr/bin/env python3
"""
fetch_licenses.py

Read a CSV with a column of GitHub repositories (owner/repo) and output a
CSV listing each repo’s license SPDX identifier (or 'NO_LICENSE').

Usage:
    python fetch_licenses.py --input repos.csv --output repos_with_license.csv \
        --token $GITHUB_TOKEN
"""

import argparse
import csv
import os
import sys
from typing import Iterable, Tuple
import yaml
import dotenv
import requests
import time


dotenv.load_dotenv()

API_URL_TEMPLATE = "https://api.github.com/repos/{owner}/{repo}"


def read_repos(csv_path: str) -> Iterable[str]:
    """Yield repo strings from the first column of the CSV."""
    with open(csv_path, newline="", encoding="utf-8") as f:
        ds = yaml.safe_load(f)
        return [x["repo_name"] for x in ds]


def fetch_license(repo: str, token: str | None = None) -> Tuple[str, str]:
    """
    Return (repo, license_spdx_id) for the given repository.

    If no license is found or the repo is inaccessible, returns 'NO_LICENSE'.
    """
    owner, _, name = repo.partition("/")
    if not owner or not name:
        return repo, "INVALID_REPO_NAME"

    url = API_URL_TEMPLATE.format(owner=owner, repo=name)
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    resp = requests.get(url, headers=headers, timeout=15)
    if resp.status_code == 403 and resp.headers.get("X-RateLimit-Remaining") == "0":
        reset = int(resp.headers.get("X-RateLimit-Reset", "0"))
        print(
            "Rate limit exceeded. Try again after {:.0f} minutes.".format((reset - time.time()) / 60),
            file=sys.stderr,
        )
        sys.exit(1)

    if resp.status_code != 200:
        return repo, f"ERROR_{resp.status_code}"

    data = resp.json()
    license_info = data.get("license") or {}
    spdx_id = license_info.get("spdx_id") or license_info.get("key") or "NO_LICENSE"
    return repo, spdx_id


def write_output(rows: Iterable[Tuple[str, str]], csv_path: str) -> None:
    """Write (repo, license) rows to a CSV file."""
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["repo", "license"])
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch license types for GitHub repositories listed in a CSV.")
    parser.add_argument(
        "--input",
        "-i",
        default="/home/user/java-migration-paper/data/migration_datasets/full_dataset.yaml",
        help="Path to input CSV (owner/repo per row)",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="/home/user/java-migration-paper/data/migration_datasets/licenses.csv",
        help="Path to output CSV with license info",
    )
    parser.add_argument(
        "--token",
        "-t",
        default=os.getenv("GITHUB_TOKEN"),
        help="GitHub personal access token (or set GITHUB_TOKEN env var)",
    )
    args = parser.parse_args()

    if not args.token:
        print(
            "Warning: No GitHub token provided – unauthenticated requests are limited to 60 per hour.",
            file=sys.stderr,
        )

    repos = list(read_repos(args.input))
    results: list[Tuple[str, str]] = []

    for repo in repos:
        repo_name, license_id = fetch_license(repo, args.token)
        results.append((repo_name, license_id))
        print(f"{repo_name}: {license_id}")

    write_output(results, args.output)
    print(f"\nWrote results to {args.output}")


if __name__ == "__main__":
    main()
