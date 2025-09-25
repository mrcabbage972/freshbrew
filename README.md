# FreshBrew


## Development Environment Setup
## Install Prerequisites
Poetry: `curl -sSL https://install.python-poetry.org | python3 -`.
Update apt-get: `sudo apt-get update`

Install JDK's
```
sudo apt-get install temurin-8-jdk
sudo apt-get install temurin-17-jdk
sudo apt-get install temurin-21-jdk
```

Install Maven:
```
sudo apt-get update
sudo apt-get install maven
```
## Environment Setup
Run `poetry install` to setup the local development environment.

To be able to smoothly clone any of the dataset repos from Github programatically, register your local SSH Key on Github. First, create key with ssh-keygen. Then follow [this](
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
### OpenAI
Set the following environment variables in your `.env` file:
```
OPENAI_API_KEY=
```
Change the model_name to be openai model in the smol_default_{java_version}.yaml file

### Target Java Version (Required)
Need to add the target Java version, such as 17 or 21 in your `.env` file: 
```
TARGET_JAVA_VERSION=
```

## Setting The Target Java Version
In order to run migration to a specified Java version, follow the steps below.

1. List all java versions:
`update-java-alternatives --list`
1. Set the desired Java version as default (requires root permissions):
`sudo update-java-alternatives --set /path/to/java/version`
1. Set the target Java version in the environment variable `TARGET_JAVA_VERSION`.

## Running Java Migration
The migration script is at `java_migration/scripts/run_migration.py`. 
The results dir contains:
- `metrics.yaml`: the aggregate metrics.
- `job_results`: a folder for each repo in the dataset with run details.


# Test Coverage Checking

To check the coverage, run the following script: `get_dataset_cov.py`.