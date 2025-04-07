#!/usr/bin/env python3
import os
import subprocess
import sys

# Configure your Randoop settings here:
# Path to the randoop jar. Adjust this to your local installation.
RANDOOP_JAR = "/home/user/java-migration-paper/randoop-4.3.3/randoop-all-4.3.3.jar"
# Additional Randoop options.
RANDOOP_OPTIONS = [
    "gentests",
    "--no-error-revealing-tests=true",
    "--junit-output-dir=randoop-tests",  # Output directory for generated tests.
]


def find_compiled_classes_dir(repo_path):
    """
    Recursively search the repo for directories containing .class files.
    Returns the candidate directory with the shortest relative path from repo root.
    """
    candidates = []
    for root, dirs, files in os.walk(repo_path):
        if any(file.endswith(".class") for file in files):
            rel_root = os.path.relpath(root, repo_path)
            candidates.append((rel_root, root))
    if not candidates:
        return None
    # Pick the candidate with the shortest relative path (likely the base directory).
    candidates.sort(key=lambda tup: len(tup[0].split(os.sep)))
    return candidates[0][1]


def generate_class_list(repo_path, base_dir, output_filename="classlist.txt"):
    """
    Walk through the base directory (of compiled classes) and generate a file containing
    fully qualified class names based on the directory structure.
    """
    class_list_path = os.path.join(repo_path, output_filename)

    with open(class_list_path, "w") as f:
        for root, dirs, files in os.walk(base_dir):
            for file in files:
                if file.endswith(".class"):
                    # Compute the relative path from the base directory.
                    rel_path = os.path.relpath(os.path.join(root, file), base_dir)
                    # Convert the file path to a fully qualified class name (replace separators with dots and remove .class)
                    class_name = rel_path.replace(os.path.sep, ".")[:-6]
                    f.write(class_name + "\n")
    print(f"Generated class list at {class_list_path}")
    return class_list_path


def run_randoop_on_repo(repo_path):
    """Run Randoop on the given Java repo and output changes as a Git diff file."""
    original_cwd = os.getcwd()
    try:
        os.chdir(repo_path)
        print(f"\nProcessing repository: {repo_path}")

        # Check if the directory is a Git repository.
        if not os.path.exists(os.path.join(repo_path, ".git")):
            print("Error: Not a valid Git repository. Skipping.")
            return

        # Automatically locate the compiled classes directory.
        compiled_dir = find_compiled_classes_dir(repo_path)
        if not compiled_dir:
            print("No compiled .class files found. Ensure your project is built before running Randoop.")
            return
        else:
            print(f"Found compiled classes in: {compiled_dir}")

        # Generate the class list file.
        class_list_file = generate_class_list(repo_path, compiled_dir)
        if not class_list_file:
            print("Class list generation failed. Skipping Randoop execution.")
            return

        # Ensure output directory for Randoop tests exists.
        output_dir = "randoop-tests"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Append the --classlist option to Randoop options.
        randoop_cmd = (
            ["java", "-classpath", RANDOOP_JAR, "randoop.main.Main"]
            + RANDOOP_OPTIONS
            + [f"--classlist={class_list_file}"]
        )
        print("Running Randoop command:", " ".join(randoop_cmd))
        subprocess.run(randoop_cmd, check=True)

        # Stage all changes to generate a diff.
        subprocess.run(["git", "add", "."], check=True)
        diff = subprocess.check_output(["git", "diff", "--cached"])
        diff_file = os.path.join(repo_path, "randoop_diff.patch")
        with open(diff_file, "wb") as f:
            f.write(diff)
        print(f"Git diff saved to: {diff_file}")

        # Optionally, reset staged changes:
        # subprocess.run(["git", "reset"], check=True)

    except subprocess.CalledProcessError as e:
        print(f"Error processing repo {repo_path}: {e}")
    finally:
        os.chdir(original_cwd)


def main():
    # if len(sys.argv) < 2:
    #     print("Usage: python script.py <repo_path1> [<repo_path2> ...]")
    #     sys.exit(1)

    repos = ["/home/user/java-migration-paper/data/workspace/sohutv_mqcloud"]  # sys.argv[1:]
    for repo in repos:
        if os.path.isdir(repo):
            run_randoop_on_repo(repo)
        else:
            print(f"Path does not exist or is not a directory: {repo}")


if __name__ == "__main__":
    main()
