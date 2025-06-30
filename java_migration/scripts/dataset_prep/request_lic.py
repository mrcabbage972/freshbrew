import os
import time

import dotenv
import pandas as pd
import requests

dotenv.load_dotenv()

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")  # Set your token via environment variable
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}

ISSUE_TITLE = "Clarification Request: License Missing"
ISSUE_BODY = """\
Hello,

We are conducting research in the space of automated software engineering and would like to include your repository in a public benchmark dataset. However, we noticed that your repository does not currently specify a license.

Could you please clarify the license under which this code is distributed by adding a LICENSE file or setting the license in the repository metadata?

This will help us and others use the code appropriately and legally. Thank you!

Best regards.
"""


def get_license_info(repo_full_name):
    url = f"https://api.github.com/repos/{repo_full_name}"
    resp = requests.get(url, headers=HEADERS)
    if resp.status_code == 200:
        return resp.json().get("license")
    else:
        print(f"Failed to fetch {repo_full_name}: {resp.status_code}")
        return None


def create_issue(repo_full_name):
    url = f"https://api.github.com/repos/{repo_full_name}/issues"
    data = {"title": ISSUE_TITLE, "body": ISSUE_BODY}
    resp = requests.post(url, headers=HEADERS, json=data)
    if resp.status_code == 201:
        print(f"Issue created in {repo_full_name}")
    else:
        print(f"Failed to create issue in {repo_full_name}: {resp.status_code} - {resp.text}")


def main(csv_path):
    df = pd.read_csv(csv_path)
    for _, row in df.iterrows():
        repo = row[1].strip()  # assumes first column has repo names
        license_info = get_license_info(repo)
        if not license_info:
            print(f"No license detected for {repo}, creating issue...")
            create_issue(repo)
            time.sleep(2)  # to avoid hitting rate limits
        else:
            print(f"License found for {repo}: {license_info.get('spdx_id', 'unknown')}")


if __name__ == "__main__":
    p = "/home/user/java-migration-paper/java_migration/notebooks/unknown_lic.csv"
    main(p)
