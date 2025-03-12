from github import Github
from tqdm import tqdm


def get_head_commits(repo_names: list[str], token=None):
    # Create a Github instance with or without authentication.
    gh = Github(token) if token else Github()

    results = []

    for repo_name in tqdm(repo_names):
        try:
            split_idx = repo_name.index("_")
            repo_name = repo_name[:split_idx] + "/" + repo_name[split_idx + 1 :]
            # Get the repository object
            repo = gh.get_repo(repo_name)
            default_branch = repo.default_branch
            # Get the branch object for the default branch
            branch = repo.get_branch(default_branch)
            commit_sha = branch.commit.sha
            results.append({repo_name: commit_sha})
        except Exception as e:
            print(f"Error processing repo {repo_name}: {e}")

    return results


# Example usage:
if __name__ == "__main__":
    import yaml

    repo_file_path = "/Users/mayvic/Documents/git/java-migration-paper/data/10k_filtered.yaml"

    with open(repo_file_path, "r") as fin:
        repos = yaml.safe_load(fin)

    repo_names = [repo["repo_name"] for repo in repos]

    import os

    from dotenv import load_dotenv

    load_dotenv()
    github_token = os.getenv("GITHUB_TOKEN")
    head_commits = get_head_commits(repo_names, token=github_token)

    with open("/Users/mayvic/Documents/git/java-migration-paper/data/head_commits.yaml", "w") as fout:
        yaml.dump(head_commits, fout)
