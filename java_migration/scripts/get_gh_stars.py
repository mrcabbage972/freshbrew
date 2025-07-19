import os
import argparse
import requests
import yaml

from dotenv import load_dotenv

load_dotenv()

def get_github_stars(repo_name, token=None):
    """
    Fetches the star count for a given GitHub repository using the GitHub API.

    Args:
        repo_name (str): The name of the repository in 'owner/repo' format.
        token (str, optional): A GitHub Personal Access Token for authentication.
                               Using a token increases the API rate limit.

    Returns:
        int: The number of stars for the repository.
        None: If the repository is not found or an API error occurs.
    """
    api_url = f"https://api.github.com/repos/{repo_name}"
    headers = {
        "Accept": "application/vnd.github.v3+json",
    }
    if token:
        headers["Authorization"] = f"token {token}"

    try:
        response = requests.get(api_url, headers=headers)
        # Raise an exception for bad status codes (4xx or 5xx)
        response.raise_for_status()

        data = response.json()
        return data.get("stargazers_count")

    except requests.exceptions.HTTPError as http_err:
        if response.status_code == 404:
            print(f"Error: Repository '{repo_name}' not found.")
        else:
            print(f"HTTP error occurred for repo '{repo_name}': {http_err}")
    except requests.exceptions.RequestException as req_err:
        print(f"An unexpected error occurred: {req_err}")
    
    return None

def parse_yaml_file(file_path):
    """
    Parses a YAML file and returns its content.

    Args:
        file_path (str): The path to the YAML file.

    Returns:
        list: The parsed content of the YAML file.
        None: If the file cannot be opened or parsed.
    """
    try:
        with open(file_path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
    except yaml.YAMLError as e:
        print(f"Error parsing YAML file '{file_path}': {e}")
    
    return None

def main():
    """
    Main function to execute the script.
    """
  
    file_path = "data/migration_datasets/full_dataset.yaml"

    # It's recommended to set your GitHub token as an environment variable
    # for better security and to avoid lower API rate limits.
    # e.g., export GITHUB_TOKEN='your_personal_access_token'
    github_token = os.environ.get("GITHUB_TOKEN")

    if not github_token:
        print("Warning: GITHUB_TOKEN environment variable not set.")
        print("You may encounter lower API rate limits.\n")

    repo_data = parse_yaml_file(file_path)

    if repo_data:
        print("--- Fetching Star Counts ---")
        for item in repo_data:
            # Ensure the item is a dictionary and contains the 'repo_name' key
            if isinstance(item, dict) and 'repo_name' in item:
                repo_name = item['repo_name']
                if repo_name:
                    stars = get_github_stars(repo_name, github_token)
                    if stars is not None:
                        print(f"{repo_name}: {stars} stars")
                else:
                    print("Warning: Found an entry with an empty 'repo_name'.")
            else:
                print("Warning: Skipping an invalid item in the YAML file.")
        print("----------------------------")

if __name__ == "__main__":
    # To run this script, you need to install the required libraries:
    # pip install requests pyyaml
    main()
