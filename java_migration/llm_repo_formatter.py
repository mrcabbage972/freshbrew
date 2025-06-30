import asyncio
import os

DEFAULT_EXT = {
    ".py",
    ".js",
    ".java",
    ".c",
    ".cpp",
    ".cs",
    ".go",
    ".rb",
    ".php",
    ".html",
    ".css",
    ".sql",
}


async def read_file(file_path: str) -> str:
    """
    Reads the content of a file asynchronously.

    Args:
        file_path (str): Path to the file.

    Returns:
        str: Content of the file with a header indicating the file path.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            return f"\n--- File: {file_path} ---\n{content}"
    except (UnicodeDecodeError, OSError) as e:
        print(f"Warning: Could not read file {file_path}. Skipping. Error: {e}")
        return ""


async def gather_files(file_paths: list[str]) -> list[str]:
    """
    Reads multiple files asynchronously.

    Args:
        file_paths (list[str]): List of file paths to read.

    Returns:
        list[str]: List of file contents.
    """
    tasks = [read_file(file_path) for file_path in file_paths]
    return await asyncio.gather(*tasks)


def get_code_files(source_dir: str, file_extensions: set[str]) -> list[str]:
    """
    Collects paths to code files in a directory recursively, filtering by extensions.

    Args:
        source_dir (str): Path to the source directory.
        file_extensions (list[str]): List of allowed file extensions.

    Returns:
        list[str]: List of file paths matching the criteria.
    """
    code_files = []

    for root, dirs, files in os.walk(source_dir):
        # Exclude hidden directories
        dirs[:] = [d for d in dirs if not d.startswith(".")]

        for file in files:
            # Exclude hidden files and filter by allowed extensions
            if not file.startswith(".") and any(file.endswith(ext) for ext in file_extensions):
                code_files.append(os.path.join(root, file))

    return code_files


async def create_llm_friendly_repo_content(source_dir: str, file_extensions: set[str] = DEFAULT_EXT) -> str:
    """
    Creates a text string from a given repository source directory, including only code files
    and excluding hidden folders and files.

    Args:
        source_dir (str): Path to the repository's source directory.
        file_extensions (list[str]): List of allowed file extensions (e.g., ['.py', '.java']).

    Returns:
        str: Concatenated string of file contents.
    """
    if not os.path.isdir(source_dir):
        raise ValueError(f"Provided source directory '{source_dir}' does not exist or is not a directory.")

    code_files = get_code_files(source_dir, file_extensions)
    file_contents = await gather_files(code_files)

    return "\n".join(filter(None, file_contents))


# Example usage
if __name__ == "__main__":
    repo_path = "/home/user/java-migration-paper/java_migration"

    output_string = asyncio.run(create_llm_friendly_repo_content(repo_path))
    with open("repo_context.txt", "w") as fout:
        fout.write(output_string)
