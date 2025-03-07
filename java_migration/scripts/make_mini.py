import yaml

full_ds_path = "/Users/mayvic/Documents/git/java-migration-paper/data/migration_datasets/full_dataset.yaml"
mini_ds_path = "/Users/mayvic/Documents/git/java-migration-paper/data/migration_datasets/mini_dataset1.yaml"

repo_names = [
    "nydiarra/springboot-jwt",
    "alibaba/QLExpress",
    "Ouyangan/hunt-admin",
]

with open(full_ds_path, "r") as fin:
    full_ds = yaml.safe_load(fin.read())

mini_ds = []
for repo in repo_names:
    # Find the repo in full_ds
    for idx in range(len(full_ds)):
        if full_ds[idx]["repo_name"] == repo:
            mini_ds.append(full_ds[idx])

with open(mini_ds_path, "w") as fout:
    fout.write(yaml.dump(mini_ds))
