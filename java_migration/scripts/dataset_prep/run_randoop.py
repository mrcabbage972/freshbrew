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
    "--junit-output-dir=randoop-tests",
    "--time-limit=20",
    "--output-limit=100",
]


def find_compiled_classes_dirs(repo_path):
    """
    Use glob to find candidate directories for compiled classes.
    Looks for directories matching common patterns such as:
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
                class_files = glob.glob(os.path.join(d, "**", "*.class"), recursive=True)
                if class_files:
                    candidate_dirs.add(os.path.abspath(d))
    return sorted(candidate_dirs)


def infer_class_name(rel_path):
    """
    Convert a relative path to a .class file into a fully qualified class name.
    E.g., "com/sohu/index/tv/mq/common/PullResponse$1.class" becomes
    "com.sohu.index.tv.mq.common.PullResponse$1".
    """
    if rel_path.endswith(".class"):
        rel_path = rel_path[:-6]
    return rel_path.replace(os.path.sep, ".")


def generate_class_list(repo_path, compiled_dirs, output_filename="classlist.txt"):
    """
    For each candidate compiled classes directory, walk through its files and write
    fully qualified class names (based on the relative path from that directory) into a file.
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


def run_maven_dependency_cp(repo_path):
    """
    Run the Maven command to build the dependency classpath.
    The command writes the classpath to cp.txt in the repo's root.
    """
    cp_file = os.path.join(repo_path, "cp.txt")
    mvn_cmd = ["mvn", "dependency:build-classpath", f"-Dmdep.outputFile={cp_file}", "-DskipTests"]
    print("Running Maven command to generate dependency classpath:")
    print(" ".join(mvn_cmd))
    subprocess.run(mvn_cmd, cwd=repo_path, check=True)
    if os.path.exists(cp_file):
        with open(cp_file, "r") as f:
            cp = f.read().strip()
            print(f"Dependency classpath from Maven: {cp}")
            return cp
    else:
        print("Maven did not generate cp.txt. No dependency classpath found.")
        return ""


def update_pom_for_regression_tests(repo_path):
    """
    Modify the pom.xml in the repository to add configuration so that
    the regression tests (Randoop-generated tests) are executed.
    Inserts build-helper-maven-plugin and maven-surefire-plugin configurations
    into the <build> section if they are not already present.
    """
    pom_path = os.path.join(repo_path, "pom.xml")
    if not os.path.exists(pom_path):
        print("No pom.xml found; skipping pom update.")
        return

    with open(pom_path, "r") as f:
        pom_content = f.read()

    # If both plugins are already present, do nothing.
    if "build-helper-maven-plugin" in pom_content and "maven-surefire-plugin" in pom_content:
        print("POM file already configured for regression tests.")
        return

    snippet = """
    <!-- Build Helper Plugin: Add randoop-tests as an additional test source -->
    <plugin>
        <groupId>org.codehaus.mojo</groupId>
        <artifactId>build-helper-maven-plugin</artifactId>
        <version>3.2.0</version>
        <executions>
            <execution>
                <id>add-test-source</id>
                <phase>generate-test-sources</phase>
                <goals>
                    <goal>add-test-source</goal>
                </goals>
                <configuration>
                    <sources>
                        <source>${project.basedir}/randoop-tests</source>
                    </sources>
                </configuration>
            </execution>
        </executions>
    </plugin>
    <!-- Maven Surefire Plugin: Configure test inclusion patterns -->
    <plugin>
        <groupId>org.apache.maven.plugins</groupId>
        <artifactId>maven-surefire-plugin</artifactId>
        <version>2.22.2</version>
        <configuration>
            <includes>
                <include>**/*Test.class</include>
                <include>**/RegressionTest*.class</include>
            </includes>
        </configuration>
    </plugin>
    """

    # Insert snippet before the closing </plugins> if found.
    if "</plugins>" in pom_content:
        new_pom_content = pom_content.replace("</plugins>", snippet + "\n</plugins>")
    elif "</build>" in pom_content:
        new_pom_content = pom_content.replace("</build>", "<plugins>" + snippet + "</plugins>\n</build>")
    else:
        # If there is no build section, append one.
        new_pom_content = pom_content + "\n<build><plugins>" + snippet + "</plugins></build>\n"

    with open(pom_path, "w") as f:
        f.write(new_pom_content)
    print("POM file updated for regression tests.")


def run_randoop_on_repo(repo_path):
    """
    Run Randoop on the given repository:
      - Updates the pom file so that the regression tests are executed.
      - Finds compiled class directories.
      - Runs Maven to generate the dependency classpath.
      - Generates a class list file.
      - Combines these into a full classpath and runs Randoop.
      - Captures a Git diff with the changes.
    """
    original_cwd = os.getcwd()
    try:
        os.chdir(repo_path)
        print(f"\nProcessing repository: {repo_path}")

        if not os.path.exists(os.path.join(repo_path, ".git")):
            print("Error: Not a valid Git repository. Skipping.")
            return

        # Update the pom file so that regression tests are executed.
        update_pom_for_regression_tests(repo_path)

        # Find candidate compiled classes directories.
        compiled_dirs = find_compiled_classes_dirs(repo_path)
        if not compiled_dirs:
            print("No compiled classes directories found. Please build your project first.")
            return
        else:
            print("Found compiled classes directories:")
            for d in compiled_dirs:
                print("  ", d)

        # Generate the class list file.
        class_list_file = generate_class_list(repo_path, compiled_dirs)
        if not class_list_file:
            print("Failed to generate class list. Skipping Randoop execution.")
            return

        # Run Maven to generate dependency classpath, if a pom.xml exists.
        dependency_cp = ""
        if os.path.exists(os.path.join(repo_path, "pom.xml")):
            dependency_cp = run_maven_dependency_cp(repo_path)

        # Build the full classpath: compiled classes, Maven dependency classpath, and Randoop jar.
        separator = ":" if os.name != "nt" else ";"
        classpath_elements = compiled_dirs + [RANDOOP_JAR]
        if dependency_cp:
            # Maven's cp is already a separator-delimited string; simply append.
            classpath = separator.join(classpath_elements) + separator + dependency_cp
        else:
            classpath = separator.join(classpath_elements)
        print("Full classpath for Randoop:")
        print(classpath)

        # Ensure output directory for Randoop tests exists.
        output_dir = "randoop-tests"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

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

    repos = ["/home/user/java-migration-paper/data/workspace/springboot-jwt"]  # sys.argv[1:]
    for repo in repos:
        if os.path.isdir(repo):
            run_randoop_on_repo(repo)
        else:
            print(f"Path does not exist or is not a directory: {repo}")


if __name__ == "__main__":
    main()
