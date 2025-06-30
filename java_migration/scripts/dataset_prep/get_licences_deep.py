#!/usr/bin/env python3
"""
fetch_licenses_deep.py

Detects licence IDs for GitHub repositories.

Hierarchy:
 1. GitHub's built-in detector
 2. Keyword scan of root-level files
 3. Keyword scan of any "licence-ish" file in the repo tree

Unauthenticated quota ≈ 60 req/h ; authenticated ≈ 5 000 req/h.
"""

from __future__ import annotations
import yaml
import dotenv
import argparse
import base64
import csv
import os
import re
import sys
import time
from typing import Iterable, Tuple

import requests

dotenv.load_dotenv()

# --------------------------------------------------------------------------- #
#   Constants
# --------------------------------------------------------------------------- #
API_REPO = "https://api.github.com/repos/{owner}/{repo}"
API_CONTENT = "https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={ref}"
API_TREE = "https://api.github.com/repos/{owner}/{repo}/git/trees/{ref}?recursive=1"

ROOT_CANDIDATE_RGX = re.compile(r"^(LICENSE|LICENCE|COPYING|COPYRIGHT|NOTICE|LEGAL|README)(\.[a-z0-9]+)?$", re.I)
# anything with "license/licence"/"copying"/"notice"/"copyright"
DEEP_CANDIDATE_RGX = re.compile(r"(?:^|/)(LICENSE|LICENCE|COPYING|NOTICE|COPYRIGHT)[^/]*$", re.I)
# extensions worth inspecting
TEXT_EXT_RGX = re.compile(r"\.(?:txt|md|rst|html?)$", re.I)

# SPDX keyword map  (add more rows easily)
LICENSE_PATTERNS: dict[re.Pattern[str], str] = {
    re.compile(r"apache license[^0-9]*2\.0", re.I): "Apache-2.0",
    re.compile(r"\bmit license\b", re.I): "MIT",
    re.compile(r"\bgnu general public license\b.*(?:version|v)?\s*3", re.I): "GPL-3.0-or-later",
    re.compile(r"\bgnu general public license\b.*(?:version|v)?\s*2", re.I): "GPL-2.0-or-later",
    re.compile(r"\bbsd.*2[- ]clause\b", re.I): "BSD-2-Clause",
    re.compile(r"\bbsd.*3[- ]clause\b", re.I): "BSD-3-Clause",
    re.compile(r"mozilla public license[^0-9]*2\.0", re.I): "MPL-2.0",
    re.compile(r"eclipse public license", re.I): "EPL-2.0",
    re.compile(r"\bunlicense\b", re.I): "Unlicense",
    re.compile(r"\bcc0[^a-z0-9]*1\.0", re.I): "CC0-1.0",
    re.compile(r"\bgnu lesser general public license\b.*3", re.I): "LGPL-3.0-or-later",
    re.compile(r"\bgnu lesser general public license\b.*2\.1", re.I): "LGPL-2.1-or-later",
    re.compile(r"\baffero general public license\b.*3", re.I): "AGPL-3.0-or-later",
}

MAX_FILE_BYTES = 64_000
MAX_DEEP_CANDIDATES = 10  # keep API usage sane


# --------------------------------------------------------------------------- #
#   Helpers
# --------------------------------------------------------------------------- #
def api_get(url: str, token: str | None = None, *, stream=False):
    hdrs = {"Accept": "application/vnd.github+json"}
    if token:
        hdrs["Authorization"] = f"Bearer {token}"
    resp = requests.get(url, headers=hdrs, timeout=30, stream=stream)
    if resp.status_code == 403 and resp.headers.get("X-RateLimit-Remaining") == "0":
        wait = max(int(resp.headers.get("X-RateLimit-Reset", "0")) - time.time(), 0)
        print(f"Rate-limit hit; retry in {wait / 60:.1f} min", file=sys.stderr)
        sys.exit(1)
    resp.raise_for_status()
    return resp


def read_repos(csv_path: str) -> Iterable[str]:
    """Yield repo strings from the first column of the CSV."""
    with open(csv_path, newline="", encoding="utf-8") as f:
        ds = yaml.safe_load(f)
        return [x["repo_name"] for x in ds]


def decode_base64_to_text(json_blob: dict) -> str | None:
    if json_blob.get("encoding") != "base64":
        return None
    try:
        data = base64.b64decode(json_blob["content"])
        return data.decode("utf-8", errors="ignore")
    except Exception:
        return None


def match_license(text: str) -> str | None:
    for patt, spdx in LICENSE_PATTERNS.items():
        if patt.search(text):
            return spdx
    return None


# --------------------------------------------------------------------------- #
#   Licence discovery pipeline
# --------------------------------------------------------------------------- #
def discover_license(owner: str, repo: str, token: str | None) -> str | None:
    # 1. GH built-in
    meta = api_get(API_REPO.format(owner=owner, repo=repo), token).json()
    spdx = (meta.get("license") or {}).get("spdx_id")
    if spdx and spdx != "NOASSERTION":
        return spdx

    default_branch = meta.get("default_branch") or "main"

    # 2. Root-level scan
    root_listing = api_get(
        API_CONTENT.format(owner=owner, repo=repo, path="", ref=default_branch),
        token,
    ).json()
    if isinstance(root_listing, list):
        for itm in root_listing:
            if itm.get("type") == "file" and ROOT_CANDIDATE_RGX.match(itm["name"]):
                blob = api_get(itm["url"], token).json()
                text = decode_base64_to_text(blob)
                if text:
                    found = match_license(text)
                    if found:
                        return found

    # 3. Deep scan – find candidate paths, then inspect first N
    tree = api_get(API_TREE.format(owner=owner, repo=repo, ref=default_branch), token).json()
    if not tree.get("tree"):
        return None

    # Filter to interesting paths
    paths = [
        node["path"]
        for node in tree["tree"]
        if node.get("type") == "blob" and (DEEP_CANDIDATE_RGX.search(node["path"]) or TEXT_EXT_RGX.search(node["path"]))
    ][:MAX_DEEP_CANDIDATES]

    for path in paths:
        # skip giant blobs (> 64 kB)
        # (need a separate API call to get size because tree nodes include it only for small blobs)
        itm = api_get(
            API_CONTENT.format(owner=owner, repo=repo, path=path, ref=default_branch),
            token,
        ).json()
        if itm.get("size", 0) > MAX_FILE_BYTES:
            continue
        text = decode_base64_to_text(itm)
        if not text:
            continue
        found = match_license(text)
        if found:
            return found

    return None


def fetch_license(repo_full: str, token: str | None = None) -> Tuple[str, str]:
    owner, _, name = repo_full.partition("/")
    if not owner or not name:
        return repo_full, "INVALID_REPO_NAME"
    spdx = discover_license(owner, name, token)
    return repo_full, spdx or "NO_LICENSE"


def write_output(rows: Iterable[Tuple[str, str]], csv_path: str) -> None:
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["repo", "license"])
        writer.writerows(rows)


# --------------------------------------------------------------------------- #
#   CLI
# --------------------------------------------------------------------------- #
def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch SPDX licences for GitHub repos (deep scan fallback).")
    parser.add_argument(
        "--input",
        "-i",
        default="/home/user/java-migration-paper/data/migration_datasets/full_dataset.yaml",
        help="Path to input CSV (owner/repo per row)",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="/home/user/java-migration-paper/data/migration_datasets/licenses_deep_2.csv",
        help="Path to output CSV with license info",
    )
    parser.add_argument(
        "-t",
        "--token",
        default=os.getenv("GITHUB_TOKEN"),
        help="GitHub PAT for higher rate limits",
    )
    args = parser.parse_args()

    if not args.token:
        print(
            "⚠️  No token set – limited to ~60 requests/hour.",
            file=sys.stderr,
        )

    repos = list(read_repos(args.input))
    out_rows: list[Tuple[str, str]] = []
    for repo in repos:
        repo, lic = fetch_license(repo, args.token)
        out_rows.append((repo, lic))
        print(f"{repo:45} → {lic}")

    write_output(out_rows, args.output)
    print(f"\nSaved results to {args.output}")


if __name__ == "__main__":
    main()
