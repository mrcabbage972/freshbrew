
def maven_commands(use_wrapper: bool) -> dict[str, str]:
    build_command = "./mvnw" if use_wrapper else "mvn"
    jacoco_plugin = "org.jacoco:jacoco-maven-plugin:0.8.8"
    # Explanation of the Maven install flags.
    # -DskipTests: don't run tests.
    # -ntp: suppress download progress logs.
    # -T 1C: 1 process per CPU core.
    # --batch-mode: no log coloring and not ever expecting user input.

    extra_args = ""
    if target_java_version:
        extra_args = f"-Dmaven.compiler.source={target_java_version} -Dmaven.compiler.target={target_java_version}"

    if run_coverage:
        commands["test"] = f"{build_command} {jacoco_plugin}:prepare-agent test -ntp --batch-mode {extra_args}"
        commands["coverage"] = f"{build_command} {jacoco_plugin}:report"
        commands["coverage_file"] = "cat target/site/jacoco/jacoco.xml"
    else:
        commands["test"] = f"{build_command} test -ntp --batch-mode"
    return commands

def gradle_commands() -> dict[str, str]:
    extra_args = ""
    if target_java_version:
        extra_args = f"-PsourceCompatibility={target_java_version} -PtargetCompatibility={target_java_version}"

    commands = {"build": f"./gradlew clean build -x test {extra_args}", "test": f"./gradlew test {extra_args}"}
    if run_coverage:
        commands["coverage"] = "./gradlew jacocoTestReport"
        commands["coverage_file"] = "cat build/reports/jacoco/test/jacocoTestReport.xml"
    return commands
