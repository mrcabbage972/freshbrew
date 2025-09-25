# ☕ FreshBrew: A Benchmark for Evaluating AI Agents on Java Code Migration


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

# Running Java Migration
The script `run_migration.py` is the main entry point for the Java migration evaluation framework. It orchestrates the entire evaluation process by validating the local environment, configuring an LLM agent, and running the migration tasks on a specified dataset of Java repositories.

For each repository, the script creates a dedicated output directory containing the generated patch file (`diff.patch`), a build log (`build.log`), the agent trajectory log (`stdout.log`) and a `result.yaml` summarizing the outcome. The main result folder also contains a `metrics.yaml` file with the aggregate success metrics.

To run the migration, use the following command structure:

```bash
python java_migration/scripts/run_migration.py [OPTIONS]
```

**Options**:

--jdk, -j INTEGER (Required)

    The target JDK version. Can also be set with the TARGET_JAVA_VERSION environment variable.

--dataset, -d PATH

    Path to the evaluation dataset YAML file.
[default: ./data/migration_datasets/full_dataset.yaml]

--agent-config, -a PATH

    Path to the agent configuration YAML file. If not provided, a default is used based on the JDK version.

--retries, -r INTEGER

    Number of retries for API calls. [default: 5]

--concurrency INTEGER

    Number of parallel workers to run. [default: 1]

# Test Coverage Guard
The script `migration_cov_guard.py` is a command-line tool designed to evaluate the results of Java migration experiments by measuring the impact of generated patches on test coverage. It acts as a "coverage guard," ensuring that code modifications do not significantly degrade the existing test coverage.

The script outputs a `cov_results.yaml` file in the experiment directory, summarizing the overall pass rate, the number of job failures, and detailed coverage results for each repository.

To run the evaluator, use the following command structure:

```bash
python java_migration/eval/migration_cov_guard <EXPERIMENT_PATH> <COV_DATA_PATH> [OPTIONS]
```

**Arguments**:

*  EXPERIMENT_PATH       (Required) 
    
        The root directory for the experiment results and summaries.
*  COV_DATA_PATH       (Required) 
        
        Path to the input coverage data CSV file.
*  WORKSPACE_DIR       
        
        Path to the directory for temporary job workspaces.  

**Options**:
*  --dataset, -d TEXT            

        Path to the migration dataset YAML file.
                                 
 * --jdk, -j TEXT                
 
        The target Java version for the migration jobs. [default: 17]
  --concurrency, -c INTEGER     
  
        Number of concurrent jobs to run. [default: 1]
 * --timeout, -t INTEGER         
 
        Timeout in seconds for each individual job. [default: 120]
 * --cleanup / --no-cleanup      
 
        Enable or disable cleanup of the workspace after jobs complete. [default: cleanup]