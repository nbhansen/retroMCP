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

            # Get the client from container
            client = self.container.retropie_client

            if action == "read":
                if lines:
                    cmd = f"head -n {lines} {path}" if lines > 0 else f"tail -n {abs(lines)} {path}"
                else:
                    cmd = f"cat {path}"
                result = client.execute_command(cmd)
                if result.success:
                    return self.format_success(f"File content:\n{result.stdout}")
                else:
                    return self.format_error(f"Failed to read file: {result.stderr}")
            elif action == "write":
                if not content:
                    return self.format_error("Content is required for write action")
                # Write content to file, creating parent directories if needed
                if create_parents:
                    parent_cmd = f"mkdir -p $(dirname {path})"
                    client.execute_command(parent_cmd)
                write_cmd = f"echo '{content}' > {path}"
                result = client.execute_command(write_cmd)
                if result.success:
                    return self.format_success(f"File written successfully to {path}")
                else:
                    return self.format_error(f"Failed to write file: {result.stderr}")
            elif action == "append":
                if not content:
                    return self.format_error("Content is required for append action")
                append_cmd = f"echo '{content}' >> {path}"
                result = client.execute_command(append_cmd)
                if result.success:
                    return self.format_success(f"Content appended to {path}")
                else:
                    return self.format_error(f"Failed to append to file: {result.stderr}")
            elif action == "copy":
                if not destination:
                    return self.format_error("Destination is required for copy action")
                result = client.execute_command(f"cp {path} {destination}")
                if result.success:
                    return self.format_success(f"File copied to {destination}")
                else:
                    return self.format_error(f"Failed to copy file: {result.stderr}")
            elif action == "move":
                if not destination:
                    return self.format_error("Destination is required for move action")
                result = client.execute_command(f"mv {path} {destination}")
                if result.success:
                    return self.format_success(f"File moved to {destination}")
                else:
                    return self.format_error(f"Failed to move file: {result.stderr}")
            elif action == "delete":
                result = client.execute_command(f"rm -f {path}")
                if result.success:
                    return self.format_success(f"File deleted: {path}")
                else:
                    return self.format_error(f"Failed to delete file: {result.stderr}")
            elif action == "create":
                if file_type == "directory":
                    mkdir_cmd = "mkdir -p" if create_parents else "mkdir"
                    result = client.execute_command(f"{mkdir_cmd} {path}")
                    if result.success:
                        return self.format_success(f"Directory created: {path}")
                    else:
                        return self.format_error(f"Failed to create directory: {result.stderr}")
                else:
                    # Create file with optional parent directories
                    if create_parents:
                        parent_cmd = f"mkdir -p $(dirname {path})"
                        client.execute_command(parent_cmd)
                    touch_cmd = f"touch {path}"
                    if content:
                        touch_cmd = f"echo '{content}' > {path}"
                    result = client.execute_command(touch_cmd)
                    if result.success:
                        return self.format_success(f"File created: {path}")
                    else:
                        return self.format_error(f"Failed to create file: {result.stderr}")
            elif action == "permissions":
                commands = []
                if mode:
                    commands.append(f"chmod {mode} {path}")
                if owner:
                    commands.append(f"chown {owner} {path}")
                if not commands:
                    return self.format_error("Either mode or owner must be specified")

                for cmd in commands:
                    result = client.execute_command(cmd)
                    if not result.success:
                        return self.format_error(f"Failed to set permissions: {result.stderr}")
                return self.format_success(f"Permissions updated for {path}")
            elif action == "download":
                if not url:
                    return self.format_error("URL is required for download action")
                result = client.execute_command(f"wget -O {path} {url}")
                if result.success:
                    return self.format_success(f"File downloaded to {path}")
                else:
                    return self.format_error(f"Failed to download file: {result.stderr}")
            else:
                return self.format_error(f"Unknown action: {action}")

        except Exception as e:
            return self.format_error(f"File management error: {e!s}")
