import json

from java_migration.utils import REPO_ROOT

result_path = REPO_ROOT / "or_results.json"


result_dict = json.loads(result_path.read_text())

build_success_count = 0
test_success_count = 0

for repo, repo_result in result_dict.items():
    if repo_result["build_success"]:
        build_success_count += 1
    if repo_result["test_success"]:
        test_success_count += 1

print(f"build: {build_success_count}")
print(f"test: {test_success_count}")
