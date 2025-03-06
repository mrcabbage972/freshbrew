# java-migration-paper

## Data
### Process
- Get top 10k repos from Github with the script `java_migration/- scripts/get_repos_from_github.py`
- Build them with Maven on JDK8. 
- Filter succesful.
- Build these with JDK17. 
- Filter on either compilation or tests failing.
### Where Is The Data
The raw 10k dataset: `data/10k_repo_features.csv`

The filtered dataset: `data/10k_filtered.yaml`


## Development Environment Setup
Run `poetry install`

Get Gemini API Key (Or any other model...) and put it in a `.env` file at the repo root.

Register SSH Key on Github:
Create key with ssh-keygen

Follow
https://docs.github.com/en/authentication/connecting-to-github-with-ssh/adding-a-new-ssh-key-to-your-github-account