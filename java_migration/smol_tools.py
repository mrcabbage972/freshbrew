from smolagents import Tool, DuckDuckGoSearchTool
import os
from pathlib import Path
import subprocess


def resolve_path(root: str, path: str) -> Path:
    rel_path = Path(path)
    abs_path = (root / rel_path).resolve()
    if not abs_path.is_relative_to(root):
        raise ValueError("Invalid path. Must be a relative path that does not go outside the root.")

    return abs_path


class ReadFile(Tool):
    name = "read_file"
    description = "Reads the content of a file"
    inputs = {
        "path": {
            "type": "string",
            "description": "The relative path of the file to the current working directory. Don't use .",
        }
    }
    output_type = "string"

    def __init__(self, root_path):
        super().__init__()
        self.root_path = root_path

    def forward(self, path):
        resolved_path = resolve_path(self.root_path, path)
        with open(resolved_path, "r") as fin:
            return fin.read()


class ListDir(Tool):
    name = "list_dir"
    description = "List the files in the given directory"
    inputs = {
        "path": {"type": "string", "description": "The relative path to the current working directory. Don't use .."}
    }
    output_type = "string"

    def __init__(self, root_path):
        super().__init__()
        self.root_path = root_path

    def forward(self, path):
        resolved_path = resolve_path(self.root_path, path)
        return os.listdir(resolved_path)


class MavenInstall(Tool):
    name = "maven_install"
    description = "Executes `mvn install` in the current directory and return the stdout."
    inputs = {}
    output_type = "string"

    def __init__(self, root_path):
        super().__init__()
        self.root_path = root_path

    def forward(self):
        cmd = [
            "mvn",
            "-B",
            "-U",
            "install",
            "-Dorg.slf4j.simpleLogger.log.org.apache.maven.cli.transfer.Slf4jMavenTransferListener=warn",
        ]
        result = subprocess.run(cmd, capture_output=True, cwd=self.root_path)
        return result.stdout.decode("utf-8")


class WriteFile(Tool):
    name = "write_file"
    description = "Write text content to a file. This replaces the file if it already exists."
    inputs = {
        "path": {"type": "string", "description": "The relative path of the file to write. Don't use .."},
        "content": {"type": "string", "description": "The content to write to the file."},
    }
    output_type = "boolean"

    def __init__(self, root_path):
        super().__init__()
        self.root_path = root_path

    def forward(self, path, content):
        resolved_path = resolve_path(self.root_path, path)
        if os.path.exists(resolved_path):
            os.remove(resolved_path)
        with open(resolved_path, "w") as fout:
            fout.write(content)
        return True


def get_tools(tool_names: list[str], root_path: Path):
    tools = []
    for tool_name in tool_names:
        if tool_name == "read_file":
            tools.append(ReadFile(root_path))
        elif tool_name == "list_dir":
            tools.append(ListDir(root_path))
        elif tool_name == "maven_install":
            tools.append(MavenInstall(root_path))
        elif tool_name == "write_file":
            tools.append(WriteFile(root_path))
        elif tool_name == "duckduckgo":
            tools.append(DuckDuckGoSearchTool())
        else:
            raise ValueError(f"Unknown tool name: {tool_name}")
    return tools
