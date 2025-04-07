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


def find_compiled_classes_dirs(repo_path):
    """
    Recursively search for directories that contain .class files and look for
    common compiled directories (like those ending with "target/classes", "bin", or "build/classes").
    Then, filter out any directories that are subdirectories of another candidate.
    """
    candidate_dirs = set()
    for root, dirs, files in os.walk(repo_path):
        if any(file.endswith(".class") for file in files):
            if root.endswith("target/classes") or root.endswith("bin") or root.endswith("build/classes"):
                candidate_dirs.add(os.path.abspath(root))
    if not candidate_dirs:
        # Fallback: return any directory that contains .class files.
        for root, dirs, files in os.walk(repo_path):
            if any(file.endswith(".class") for file in files):
                candidate_dirs.add(os.path.abspath(root))
    candidate_dirs = list(candidate_dirs)

    # Filter out candidate directories that are subdirectories of another candidate.
    filtered = []
    for d in candidate_dirs:
        if not any(d != other and d.startswith(other + os.sep) for other in candidate_dirs):
            filtered.append(d)
    return sorted(filtered)

def infer_class_name(rel_path):
    """
    Convert a relative path to a .class file into a fully qualified class name.
    For example, "com/sohu/index/tv/mq/common/PullResponse.class" becomes
    "com.sohu.index.tv.mq.common.PullResponse".
    """
    if rel_path.endswith(".class"):
        rel_path = rel_path[:-6]
    return rel_path.replace(os.path.sep, ".")

def generate_class_list(repo_path, compiled_dirs, output_filename="classlist.txt"):
    """
    For each compiled classes directory, walk through its files and write fully qualified
    class names (based on the relative path from that directory) into a file.
    """
    class_list_path = os.path.join(repo_path, output_filename)
    with open(class_list_path, "w") as f:
        for base_dir in compiled_dirs:
            for root, dirs, files in os.walk(base_dir):
                for file in files:
                    if file.endswith(".class"):
                        # Compute the relative path from the base compiled directory.
                        rel_path = os.path.relpath(os.path.join(root, file), base_dir)
                        class_name = infer_class_name(rel_path)
                        f.write(class_name + "\n")
    print(f"Generated class list at {class_list_path}")
    return class_list_path

def run_randoop_on_repo(repo_path):
    """Run Randoop on the given Java repo and output changes as a Git diff file."""
    original_cwd = os.getcwd()
    try:
        os.chdir(repo_path)
        print(f"\nProcessing repository: {repo_path}")

        if not os.path.exists(os.path.join(repo_path, ".git")):
            print("Error: Not a valid Git repository. Skipping.")
            return

        # Get all candidate directories that contain compiled classes.
        compiled_dirs = find_compiled_classes_dirs(repo_path)
        if not compiled_dirs:
            print("No compiled .class files found. Please build your project first.")
            return
        else:
            print("Found compiled classes in the following directories:")
            for d in compiled_dirs:
                print("  ", d)

        # Generate the class list file from all candidate directories.
        class_list_file = generate_class_list(repo_path, compiled_dirs)
        if not class_list_file:
            print("Failed to generate class list. Skipping Randoop execution.")
            return

        # Ensure output directory for Randoop tests exists.
        output_dir = "randoop-tests"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Build the classpath by including all candidate directories plus the Randoop jar.
        separator = ":" if os.name != "nt" else ";"
        classpath_elements = compiled_dirs + [RANDOOP_JAR]
        classpath = separator.join(classpath_elements)

        # Build the Randoop command with the --classlist option.
        randoop_cmd = [
            "java",
            "-classpath", classpath,
            "randoop.main.Main"
        ] + RANDOOP_OPTIONS + [f"--classlist={class_list_file}"]

        print("Running Randoop command:")
        print(" ".join(randoop_cmd))
        subprocess.run(randoop_cmd, check=True)

        # Stage changes and generate a Git diff.
        subprocess.run(["git", "add", "."], check=True)
        diff = subprocess.check_output(["git", "diff", "--cached"])
        diff_file = os.path.join(repo_path, "randoop_diff.patch")
        with open(diff_file, "wb") as f:
            f.write(diff)
        print(f"Git diff saved to: {diff_file}")

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
