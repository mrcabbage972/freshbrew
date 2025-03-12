import json
import os
import time
from datetime import datetime, timedelta

import requests
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()


class GitHubGraphQLClient:
    def __init__(self, token):
        self.token = token
        self.url = "https://api.github.com/graphql"
        self.headers = {"Authorization": f"Bearer {token}"}
        self.save_dir = "github_data"
        os.makedirs(self.save_dir, exist_ok=True)

    def execute_query(self, query, variables=None):
        response = requests.post(self.url, headers=self.headers, json={"query": query, "variables": variables})

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Query failed with status code: {response.status_code}\n{response.text}")

    def get_repos_by_date_range(self, start_date, end_date, cursor=None):
        query = """
        query ($query: String!, $cursor: String) {
          search(query: $query, type: REPOSITORY, first: 100, after: $cursor) {
            pageInfo {
              hasNextPage
              endCursor
            }
            nodes {
              ... on Repository {
                nameWithOwner
                url
                description
                stargazerCount
                createdAt
                primaryLanguage {
                  name
                }
              }
            }
          }
        }
        """

        variables = {"query": f"language:java created:{start_date}..{end_date} sort:stars-desc", "cursor": cursor}

        return self.execute_query(query, variables)

    def save_chunk(self, repos, start_date, end_date):
        filename = f"{self.save_dir}/repos_{start_date}_{end_date}.json"
        with open(filename, "w") as f:
            json.dump(repos, f)

    def load_existing_chunks(self):
        repos = []
        for filename in os.listdir(self.save_dir):
            if filename.startswith("repos_") and filename.endswith(".json"):
                with open(os.path.join(self.save_dir, filename)) as f:
                    repos.extend(json.load(f))
        return repos

    def get_top_repos(self):
        start_date = "2008-01-01"
        end_date = datetime.now().strftime("%Y-%m-%d")

        # Calculate date ranges (3-month chunks)
        dates = []
        current = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")

        while current < end:
            next_date = min(current + timedelta(days=90), end)
            dates.append((current.strftime("%Y-%m-%d"), next_date.strftime("%Y-%m-%d")))
            current = next_date

        all_repos = []

        # Load any existing progress
        print("Loading existing progress...")
        all_repos = self.load_existing_chunks()
        completed_ranges = {f"repos_{start}_{end}.json" for start, end in dates}
        completed_ranges &= set(os.listdir(self.save_dir))

        with tqdm(total=len(dates), desc="Fetching repos") as pbar:
            # Skip already completed date ranges
            pbar.update(len(completed_ranges))

            for start_date, end_date in dates:
                filename = f"repos_{start_date}_{end_date}.json"
                if filename in completed_ranges:
                    continue

                chunk_repos = []
                cursor = None

                while True:
                    try:
                        result = self.get_repos_by_date_range(start_date, end_date, cursor)

                        if "errors" in result:
                            print(f"Error in response: {result['errors']}")
                            time.sleep(60)  # Wait if we hit rate limit
                            continue

                        page_info = result["data"]["search"]["pageInfo"]
                        nodes = result["data"]["search"]["nodes"]

                        # Filter out None values and repositories without primary language
                        valid_repos = [repo for repo in nodes if repo and repo.get("primaryLanguage")]
                        chunk_repos.extend(valid_repos)

                        if not page_info["hasNextPage"]:
                            break

                        cursor = page_info["endCursor"]
                        time.sleep(2)  # Respect rate limits

                    except Exception as e:
                        print(f"\nError fetching chunk: {e}")
                        time.sleep(60)  # Wait longer on errors
                        continue

                # Save this chunk
                self.save_chunk(chunk_repos, start_date, end_date)
                all_repos.extend(chunk_repos)

                pbar.set_description(f"Fetched {len(chunk_repos)} repos ({start_date} to {end_date})")
                pbar.update(1)

        print("\nSorting repositories...")
        all_repos.sort(key=lambda x: x["stargazerCount"], reverse=True)

        # Save final sorted result
        with open(f"{self.save_dir}/top_java_repos.json", "w") as f:
            json.dump(all_repos[:10000], f, indent=2)

        return all_repos[:10000]


if __name__ == "__main__":
    client = GitHubGraphQLClient(os.getenv("GITHUB_TOKEN"))
    top_repos = client.get_top_repos()
    print(f"\nFetched {len(top_repos)} repositories")
    print(f"Top repo: {top_repos[0]['nameWithOwner']} with {top_repos[0]['stargazerCount']} stars")
