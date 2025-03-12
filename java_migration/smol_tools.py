import os
from pathlib import Path

from smolagents import DuckDuckGoSearchTool, Tool

from java_migration.utils import maven_install, validate_xml


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


class StatefulFileTool(Tool):
    name = "stateful_file_tool"
    description = (
        "A stateful file editing tool that supports commands: view, create, str_replace, insert, and undo_edit. "
        "It maintains a history per file to enable undo operations."
    )
    inputs = {
        "command": {
            "type": "string",
            "enum": ["view", "create", "str_replace", "insert", "undo_edit"],
            "description": "The commands to run. Allowed options are: `view`, `create`, `str_replace`, `insert`, `undo_edit`.",
        },
        "file_text": {
            "description": "Required parameter of `create` command, with the content of the file to be created.",
            "type": "string",
            "nullable": True,
        },
        "insert_line": {
            "description": "Required parameter of `insert` command. The `new_str` will be inserted AFTER the line `insert_line` of `path`.",
            "type": "integer",
            "nullable": True,
        },
        "new_str": {
            "description": "Required parameter of `str_replace` command containing the new string. Also used in `insert` command as the string to insert.",
            "type": "string",
            "nullable": True,
        },
        "old_str": {
            "description": "Required parameter of `str_replace` command containing the string in `path` to replace.",
            "type": "string",
            "nullable": True,
        },
        "path": {
            "description": "Relative path to file or directory.",
            "type": "string",
        },
        "view_range": {
            "description": "Optional parameter of `view` command when `path` points to a file. If none is given, the full file is shown. "
            "If provided, the file will be shown in the indicated line number range, e.g. [11, 12] will show lines 11 and 12. "
            "Indexing starts at 1. Setting `[start_line, -1]` shows all lines from `start_line` to the end of the file.",
            "type": "array",
            "items": {"type": "integer"},
            "nullable": True,
        },
    }  # type: ignore
    output_type = "string"

    # Class-level dictionary to maintain history for each file.
    history = {}

    def __init__(self, root_path):
        super().__init__()
        self.root_path = root_path

    # Helper methods
    def _read_file(self, path: str) -> str | None:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return None

    def _write_file(self, path: str, content: str):
        _, file_extension = os.path.splitext(path)
        if file_extension == ".xml":
            validate_xml(content)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    def _push_history(self, path: str, content: str) -> None:
        if path not in self.history:
            self.history[path] = []
        self.history[path].append(content)

    # Command submethods
    def _command_create(self, path: str, file_text: str) -> str:
        if file_text is None:
            return "Error: 'file_text' is required for create command."
        try:
            self._write_file(path, file_text)
        except Exception as e:
            return f"Error writing to file {path}: {str(e)}"
        # Initialize history with the created version.
        self.history[path] = [file_text]
        return f"File {path} created successfully."

    def _command_view(self, path: str, view_range: list[int] | None = None) -> str:
        content = self._read_file(path)
        if content is None:
            return f"Error reading file {path}."
        if view_range and isinstance(view_range, list) and len(view_range) == 2:
            lines = content.splitlines()
            start, end = view_range
            start_index = max(start - 1, 0)
            if end == -1:
                selected_lines = lines[start_index:]
            else:
                selected_lines = lines[start_index:end]
            return "\n".join(selected_lines)
        return content

    def _command_str_replace(self, path: str, old_str: str, new_str: str) -> str:
        if old_str is None or new_str is None:
            return "Error: 'old_str' and 'new_str' are required for str_replace command."
        content = self._read_file(path)
        if content is None:
            return f"Error reading file {path}."
        self._push_history(path, content)
        updated_content = content.replace(old_str, new_str)
        try:
            self._write_file(path, updated_content)
        except Exception as e:
            return f"Error writing to file {path}: {str(e)}"

        return f"String replacement completed in file {path}."

    def _command_insert(self, path: str, insert_line: int, new_str: str) -> str:
        if insert_line is None or new_str is None:
            return "Error: 'insert_line' and 'new_str' are required for insert command."
        content = self._read_file(path)
        if content is None:
            return f"Error reading file {path}."
        self._push_history(path, content)
        lines = content.splitlines()
        # insert after the given line (1-indexed)
        index = insert_line  # insert after the given line means new line goes at this index (0-indexed position after insert_line-1)
        if index > len(lines):
            lines.append(new_str)
        else:
            lines.insert(index, new_str)
        updated_content = "\n".join(lines) + "\n"
        try:
            self._write_file(path, updated_content)
        except Exception as e:
            return f"Error writing to file {path}: {str(e)}"
        return f"String inserted into file {path} after line {insert_line}."

    def _command_undo_edit(self, path: str) -> str:
        if path not in self.history or len(self.history[path]) < 2:
            return f"No previous version available to undo for file {path}."
        # Remove current version and revert to the previous version.
        self.history[path].pop()  # Remove current state.
        prev_content = self.history[path][-1]
        try:
            self._write_file(path, prev_content)
        except Exception as e:
            return f"Error writing to file {path}: {str(e)}"
        return f"Undo successful for file {path}."

    # Main forward method
    def forward(  # type: ignore
        self,
        command: str,
        path: str,
        file_text: str | None = None,
        insert_line: int | None = None,
        new_str: str | None = None,
        old_str: str | None = None,
        view_range: list | None = None,
    ) -> str:
        import os

        resolved_path = str(resolve_path(self.root_path, path))
        # For commands other than 'create', the file must exist.
        if command != "create":
            if not os.path.exists(resolved_path):
                return f"Error: The file {path} does not exist."

        if command == "create":
            if file_text is None:
                return "Error: 'file_text' is required for create command."
            return self._command_create(resolved_path, file_text)
        elif command == "view":
            return self._command_view(resolved_path, view_range)
        elif command == "str_replace":
            if old_str is None:
                return "Error: 'old_str' is required for str_replace command."
            if new_str is None:
                return "Error: 'new_str' is required for str_replace command."
            return self._command_str_replace(resolved_path, old_str, new_str)
        elif command == "insert":
            if insert_line is None:
                return "Error: 'insert_line' is required for insert command."
            if new_str is None:
                return "Error: 'new_str' is required for insert command."
            return self._command_insert(resolved_path, insert_line, new_str)
        elif command == "undo_edit":
            return self._command_undo_edit(resolved_path)
        else:
            return f"Unknown command: {command}"


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
        elif tool_name == "stateful_file_tool":
            tools.append(StatefulFileTool(root_path))
        # elif tool_name == "replace_xml_subtree_file":
        #     tools.append(ReplaceXMLSubtreeFileTool(root_path))
        else:
            raise ValueError(f"Unknown tool name: {tool_name}")
    return tools
