#!/usr/bin/env python3
import glob
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
    Use glob to find candidate directories for compiled classes.
    Looks for directories matching:
      - **/target/classes
      - **/build/classes
      - **/bin
    Only returns those that contain at least one .class file.
    """
    patterns = [
        os.path.join(repo_path, "**", "target", "classes"),
        os.path.join(repo_path, "**", "build", "classes"),
        os.path.join(repo_path, "**", "bin"),
    ]
    candidate_dirs = set()
    for pattern in patterns:
        for d in glob.glob(pattern, recursive=True):
            if os.path.isdir(d):
                # Check that the directory contains .class files.
                class_files = glob.glob(os.path.join(d, "**", "*.class"), recursive=True)
                if class_files:
                    candidate_dirs.add(os.path.abspath(d))
    return sorted(candidate_dirs)


def infer_class_name(rel_path):
    """
    Convert a relative path to a .class file into a fully qualified class name.
    For example, "com/sohu/tv/mq/rocketmq/RocketMQConsumer.class" becomes
    "com.sohu.tv.mq.rocketmq.RocketMQConsumer".
    """
    if rel_path.endswith(".class"):
        rel_path = rel_path[:-6]
    return rel_path.replace(os.path.sep, ".")


def generate_class_list(repo_path, compiled_dirs, output_filename="classlist.txt"):
    """
    For each candidate compiled classes directory, walk through its files and write fully
    qualified class names (based on the relative path from that directory) into a file.
    """
    class_list_path = os.path.join(repo_path, output_filename)
    with open(class_list_path, "w") as f:
        for base_dir in compiled_dirs:
            for root, dirs, files in os.walk(base_dir):
                for file in files:
                    if file.endswith(".class"):
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

        # Verify that the repo is a Git repository.
        if not os.path.exists(os.path.join(repo_path, ".git")):
            print("Error: Not a valid Git repository. Skipping.")
            return

        # Find all candidate directories for compiled classes.
        compiled_dirs = find_compiled_classes_dirs(repo_path)
        if not compiled_dirs:
            print("No compiled classes directories found. Please build your project first.")
            return
        else:
            print("Found compiled classes directories:")
            for d in compiled_dirs:
                print("  ", d)

        # Generate the class list file using these directories.
        class_list_file = generate_class_list(repo_path, compiled_dirs)
        if not class_list_file:
            print("Failed to generate class list. Skipping Randoop execution.")
            return

        # Ensure the output directory for Randoop tests exists.
        output_dir = "randoop-tests"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Build the classpath by including all candidate directories plus the Randoop jar.
        separator = ":" if os.name != "nt" else ";"
        classpath_elements = compiled_dirs + [RANDOOP_JAR]
        classpath = separator.join(classpath_elements)

        # Build and run the Randoop command.
        randoop_cmd = (
            ["java", "-classpath", classpath, "randoop.main.Main"]
            + RANDOOP_OPTIONS
            + [f"--classlist={class_list_file}"]
        )

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
