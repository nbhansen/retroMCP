"""File management tools for file operations."""

from typing import Any
from typing import Dict
from typing import List

from mcp.types import EmbeddedResource
from mcp.types import ImageContent
from mcp.types import TextContent
from mcp.types import Tool

from .base import BaseTool


class FileManagementTools(BaseTool):
    """Tools for managing files and directories."""

    def get_tools(self) -> List[Tool]:
        """Return list of available file management tools."""
        return [
            Tool(
                name="manage_file",
                description="Manage files and directories (read, write, append, copy, move, delete, create, permissions)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["read", "write", "append", "copy", "move", "delete", "create", "permissions", "download"],
                            "description": "Action to perform on the file/directory",
                        },
                        "path": {
                            "type": "string",
                            "description": "File or directory path",
                        },
                        "content": {
                            "type": "string",
                            "description": "Content to write/append to file",
                        },
                        "destination": {
                            "type": "string",
                            "description": "Destination path for copy/move operations",
                        },
                        "mode": {
                            "type": "string",
                            "description": "Permission mode (e.g., '755')",
                        },
                        "owner": {
                            "type": "string",
                            "description": "Owner (user:group format)",
                        },
                        "lines": {
                            "type": "integer",
                            "description": "Number of lines to read (for read action)",
                        },
                        "create_parents": {
                            "type": "boolean",
                            "description": "Create parent directories if they don't exist",
                        },
                        "type": {
                            "type": "string",
                            "enum": ["file", "directory"],
                            "description": "Type of item to create",
                        },
                        "url": {
                            "type": "string",
                            "description": "URL to download from",
                        },
                    },
                    "required": ["action", "path"],
                },
            )
        ]

    async def handle_tool_call(
        self, name: str, arguments: Dict[str, Any]
    ) -> List[TextContent | ImageContent | EmbeddedResource]:
        """Handle file management tool calls."""
        if name == "manage_file":
            return await self._handle_file_management(arguments)
        else:
            return self.format_error(f"Unknown tool: {name}")

    async def _handle_file_management(
        self, arguments: Dict[str, Any]
    ) -> List[TextContent | ImageContent | EmbeddedResource]:
        """Handle file management operations."""
        try:
            action = arguments.get("action")
            path = arguments.get("path")
            content = arguments.get("content", "")
            destination = arguments.get("destination", "")
            mode = arguments.get("mode", "")
            owner = arguments.get("owner", "")
            lines = arguments.get("lines")
            create_parents = arguments.get("create_parents", False)
            file_type = arguments.get("type", "file")
            url = arguments.get("url", "")

            if not action or not path:
                return self.format_error("Both 'action' and 'path' are required")

            # Get the use case from container
            use_case = self.container.get_file_management_use_case()
            
            if action == "read":
                if lines:
                    result = use_case.read_file_lines(path, lines)
                else:
                    result = use_case.read_file(path)
            elif action == "write":
                if not content:
                    return self.format_error("Content is required for write action")
                result = use_case.write_file(path, content)
            elif action == "append":
                if not content:
                    return self.format_error("Content is required for append action")
                result = use_case.append_file(path, content)
            elif action == "copy":
                if not destination:
                    return self.format_error("Destination is required for copy action")
                result = use_case.copy_file(path, destination)
            elif action == "move":
                if not destination:
                    return self.format_error("Destination is required for move action")
                result = use_case.move_file(path, destination)
            elif action == "delete":
                result = use_case.delete_file(path)
            elif action == "create":
                if file_type == "directory":
                    result = use_case.create_directory(path, create_parents)
                else:
                    result = use_case.create_file(path, content, create_parents)
            elif action == "permissions":
                result = use_case.set_permissions(path, mode, owner)
            elif action == "download":
                if not url:
                    return self.format_error("URL is required for download action")
                result = use_case.download_file(url, path)
            else:
                return self.format_error(f"Unknown action: {action}")

            if result.success:
                return self.format_success(f"File {action}: {result.stdout}")
            else:
                return self.format_error(f"Failed to {action} file: {result.stderr}")

        except Exception as e:
            return self.format_error(f"File management error: {e!s}")