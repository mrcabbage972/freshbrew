from java_migration.utils import REPO_ROOT
from java_migration.figure_plotting.figure_utils import plot_counts
from pathlib import Path
import json
import pandas as pd

INPUT_PATH = REPO_ROOT / "dependencies.json"

deps = json.loads(INPUT_PATH.read_text())
dep_names = []
for repo_deps in deps.values():
    dep_names.extend([x["artifactId"] for x in repo_deps])



value_counts = pd.Series(dep_names).value_counts(ascending=True).tail(10)

#print(value_counts.head(10))
plot_counts(
    bins=value_counts.index.tolist(),
    counts=value_counts.tolist(),
    ylabel="Number of Repositories",
    xlabel="Dependency",
    output_path=REPO_ROOT / "java_migration/figures" / "dep_counts.pdf",
    is_barh=False
)