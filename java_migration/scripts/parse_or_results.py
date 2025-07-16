import json
from java_migration.utils import REPO_ROOT

exp_paths = {"21": "or_results_17.json", "17": "or_results_21.json"}


num_parsable = 159

for jd, exp_path in exp_paths.items():
    build_success_count = 0
    test_success_count = 0
    exp_data = json.loads((REPO_ROOT / exp_path).read_text())
    for repo_name, repo_data in exp_data.items():
        build_success = repo_data.get("build_success", False)
        test_success = repo_data.get("test_success", False)
        if test_success:
            test_success_count += 1
        if build_success:
            build_success_count += 1
    print(f"jd = {jd}")
    print(f"build success = {100.0* build_success_count / len(exp_data):.1f}")
    print(f"test success = {100.0*test_success_count / len(exp_data):.1f}")
    print(f"build success (parsable) = {100.0* build_success_count / num_parsable:.1f}")
    print(f"test success (parsable) = {100.0*test_success_count / num_parsable:.1f}")
    print(f"num repos {len(exp_data)}")
