import re
import subprocess


class EnvironmentValidator:
    def validate(self, jdk_version: int = 17):
        """
        Validates the environment by ensuring that:
        1. Maven (mvn) is installed.
        2. Java 17 is installed.

        Returns:
            bool: True if both validations pass; otherwise, False.
        """
        if not self.__check_maven():
            return False
        if not self.__check_java(jdk_version):
            return False

        print(f"Environment validation successful: Maven and Java {jdk_version} are installed.")
        return True

    def __check_maven(self):
        """
        Private method to check if Maven is installed.
        Returns:
            bool: True if Maven is installed, otherwise False.
        """
        try:
            mvn_result = subprocess.run(["mvn", "--version"], capture_output=True, text=True, check=True)
            print("Maven is installed:")
            print(mvn_result.stdout)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("Error: Maven (mvn) is not installed or not found in PATH.")
            return False

    def __check_java(self, jdk_version: int):
        """
        Private method to check if Java is installed.
        Returns:
            bool: True if Java is installed, otherwise False.
        """
        try:
            java_result = subprocess.run(["java", "-version"], capture_output=True, text=True, check=True)
            # Java typically outputs its version info to stderr
            java_output = java_result.stderr or java_result.stdout
            match = re.search(r"\"(\d+)\.(\d+)\.(\d+)", java_output)
            if match:
                major_version = int(match.group(1))
                if major_version == 1:
                    minor_version = int(match.group(2))
                    if minor_version == 8 and jdk_version == 8:
                        return True

                if major_version != jdk_version:
                    print(f"Error: Java version {major_version} found. Java {jdk_version} is required.")
                    return False
                else:
                    print(f"Java {jdk_version} is installed.")
                    return True
            else:
                print("Error: Unable to parse Java version from the output:")
                print(java_output)
                return False
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("Error: Java is not installed or not found in PATH.")
            return False


# Example usage:
if __name__ == "__main__":
    validator = EnvironmentValidator()
    if validator.validate(17):
        print("All checks passed. Environment is correctly set up.")
    else:
        print("Environment validation failed. Please install the required tools.")
