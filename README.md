# java-migration-paper

## Data
### Process
- Get top 10k repos from Github with the script `java_migration/- scripts/get_repos_from_github.py`
- Build them with Maven on JDK8. 
- Filter succesful.
- Build these with JDK17. 
- Filter on either compilation or tests failing.
### Data
The raw 10k dataset: `data/10k_repo_features.csv`

The filtered dataset: `data/10k_filtered.yaml`
