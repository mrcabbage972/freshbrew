import multiprocessing
from java_migration.eval.utils import safe_repo_name, generate_experiment_dir
from java_migration.eval.worker import Worker
from java_migration.eval.data_model import JobCfg

if __name__ == "__main__":
    repo_names = ["springboot-jwt"]
    root_dir = "/Users/mayvic/Documents/git/java-migration-paper/data/experiments"
    tools = []
    max_num_steps = 100

    experiment_dir = generate_experiment_dir(root_dir)

    job_cfgs = [
        JobCfg(
            max_num_steps=max_num_steps,
            tools=tools,
            repo_name=repo_name,
            workspace_dir=experiment_dir / safe_repo_name(repo_name),
        )
        for repo_name in repo_names
    ]

    worker = Worker()

    with multiprocessing.Pool(processes=len(job_cfgs)) as pool:
        results = pool.map(worker, job_cfgs)
    print(results)
