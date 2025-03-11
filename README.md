# java-migration-paper

## Dataset Construction
### Process
- Get top 10k repos from Github with the script `java_migration/- scripts/get_repos_from_github.py`
- Build them with Maven on JDK8. 
- Filter succesful.
- Build these with JDK17. 
- Filter on either compilation or tests failing.
- Deduplicate
### Where Is The Data
The raw 10k dataset: `data/10k_repo_features.csv`

The filtered dataset: `data/10k_filtered.yaml`

## Processed Dataset
The datasets are in `data/migration_datasets`:
- `full_dataset.yaml`: the full dataset.
- `tiniy_dataset.yaml`: a small dataset for testing functionality during development.

## Development Environment Setup
Install poetry: `curl -sSL https://install.python-poetry.org | python3 -`
Run `poetry install`

Get Gemini API Key (Or any other model...) and put it in a `.env` file at the repo root.

Install JDK 17

Install Maven:
```sudo apt-get update
 sudo apt-get install maven```

Register SSH Key on Github:
Create key with ssh-keygen

Follow
https://docs.github.com/en/authentication/connecting-to-github-with-ssh/adding-a-new-ssh-key-to-your-github-account

## Running the eval script
The eval script is at `java_migration/scripts/run_eval.py`. Currently the input dataset path is hardcoded.
The script prints the path where the results are written.
The results dir contains:
- `metrics.yaml`: the aggregate metrics.
- `job_results`: a folder for each repo in the dataset with run details.