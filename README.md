# java-migration-paper

## Datasets
### Construction Process
- Get top 10k repos from Github with the script `java_migration/- scripts/get_repos_from_github.py`
- Build them with Maven on JDK8. 
- Filter succesful.
- Build these with JDK17. 
- Filter on either compilation or tests failing.
- Deduplicate
- Add JDK8 test counts
- Calculate repo features
## Processed Datasets
- `data/migration_datasets/full_dataset.yaml`: 450-ish samples
- `data/migration_datasets/mini_dataset.yaml`: 15 samples
- `data/migration_datasets/tiny_dataset.yaml`: 3 samples
### Raw Data
- The raw 10k dataset: `data/10k_repo_features.csv`
- The filtered dataset: `data/10k_filtered.yaml`

## Development Environment Setup
### Install Prerequisites
Poetry: `curl -sSL https://install.python-poetry.org | python3 -`.

Install JDK 17

Install Maven:
```
sudo apt-get update
sudo apt-get install maven
```
## Environment Setup
Run `poetry install` to setup the local development environment.

Register your local SSH Key on Github. First, create key with ssh-keygen. Then follow [this](
https://docs.github.com/en/authentication/connecting-to-github-with-ssh/adding-a-new-ssh-key-to-your-github-account) guide to register it on your Github account.

Set up model credentials as follows.

### Gemini - AI Studio
Get Gemini API Key (Or any other model...) and put it in a `.env` file at the repo root. The key name for Gemini is GEMINI_API_KEY.

### Gemini - Vertex
Set the following environment variables in your `.env` file:
```
DEFAULT_VERTEXAI_PROJECT=
DEFAULT_VERTEXAI_LOCATION=
DEFAULT_GOOGLE_APPLICATION_CREDENTIALS={path to service acount key file}
```


## Running the Eval Script
The eval script is at `java_migration/scripts/run_eval.py`. Currently the input dataset path is hardcoded.
The script prints the path where the results are written.
The results dir contains:
- `metrics.yaml`: the aggregate metrics.
- `job_results`: a folder for each repo in the dataset with run details.