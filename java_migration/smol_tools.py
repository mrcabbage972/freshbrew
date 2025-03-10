from smolagents import Tool, DuckDuckGoSearchTool
import os
from pathlib import Path
from java_migration.utils import maven_install


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

    def forward(self, path):  # type: ignore
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

    def forward(self, path):  # type: ignore
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

    def forward(self):  # type: ignore
        return maven_install(self.root_path)


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

    def forward(self, path, content):  # type: ignore
        resolved_path = resolve_path(self.root_path, path)
        if os.path.exists(resolved_path):
            os.remove(resolved_path)
        with open(resolved_path, "w") as fout:
            fout.write(content)
        return True


class ValidateXMLTool(Tool):
    name = "validate_xml"
    description = (
        "Validates a given XML string to ensure it is well-formed. "
        "Returns a success message if the XML is valid, or error details if not."
    )
    inputs = {
        "xml_content": {
            "type": "string",
            "description": "The XML content to validate.",
        }
    }
    output_type = "string"

    def forward(self, xml_content: str):  # type: ignore
        try:
            import xml.etree.ElementTree as ET
        except ImportError as e:
            raise ImportError("Python's built-in xml.etree.ElementTree module is required but not available.") from e
        try:
            # Try parsing the XML content
            ET.fromstring(xml_content)
            return "XML is well-formed."
        except ET.ParseError as pe:
            return f"XML is not well-formed: {str(pe)}"
        except Exception as e:
            return f"An unexpected error occurred: {str(e)}"


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
        elif tool_name == "validate_xml":
            tools.append(ValidateXMLTool())
        else:
            raise ValueError(f"Unknown tool name: {tool_name}")
    return tools
