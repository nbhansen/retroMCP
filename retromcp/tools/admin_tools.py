"""Administrative tools for direct system control with elevated privileges."""

from typing import Any
from typing import Dict
from typing import List

from mcp.types import EmbeddedResource
from mcp.types import ImageContent
from mcp.types import TextContent
from mcp.types import Tool

from ..domain.models import ExecuteCommandRequest
from ..domain.models import WriteFileRequest
from .base import BaseTool


class AdminTools(BaseTool):
    """Administrative tools for direct command execution and file writing."""

    def get_tools(self) -> List[Tool]:
        """Return list of available administrative tools.

        Returns:
            List of Tool objects for administrative operations.
        """
        return [
            Tool(
                name="execute_command",
                description="Execute shell commands directly on the RetroPie system with security validation",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "Shell command to execute (will be validated for security)",
                        },
                        "use_sudo": {
                            "type": "boolean",
                            "default": False,
                            "description": "Execute command with sudo privileges",
                        },
                        "working_directory": {
                            "type": "string",
                            "description": "Working directory for command execution",
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Command timeout in seconds (optional)",
                        },
                    },
                    "required": ["command"],
                },
            ),
            Tool(
                name="write_file",
                description="Write content directly to files with proper permissions and security validation",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Full file path where content should be written (will be validated for security)",
                        },
                        "content": {
                            "type": "string",
                            "description": "File content (supports multi-line text)",
                        },
                        "mode": {
                            "type": "string",
                            "description": "File permissions (e.g., '644', '755', '600')",
                        },
                        "backup": {
                            "type": "boolean",
                            "default": False,
                            "description": "Create backup of existing file before overwriting",
                        },
                        "create_directories": {
                            "type": "boolean",
                            "default": False,
                            "description": "Create parent directories if they don't exist",
                        },
                    },
                    "required": ["path", "content"],
                },
            ),
        ]

    async def handle_tool_call(
        self, name: str, arguments: Dict[str, Any]
    ) -> List[TextContent | ImageContent | EmbeddedResource]:
        """Handle tool calls for administrative operations.

        Args:
            name: Name of the tool to call.
            arguments: Arguments for the tool.

        Returns:
            List of content objects with the tool's response.
        """
        try:
            if name == "execute_command":
                return await self._execute_command(arguments)
            elif name == "write_file":
                return await self._write_file(arguments)
            else:
                return self.format_error(f"Unknown tool: {name}")
        except Exception as e:
            return self.format_error(f"Error in {name}: {e!s}")

    async def _execute_command(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Execute command with security validation."""
        command = arguments.get("command")
        use_sudo = arguments.get("use_sudo", False)
        working_directory = arguments.get("working_directory")
        timeout = arguments.get("timeout")

        # Validate required arguments
        if not command:
            return self.format_error("Command is required")

        # Create request object
        request = ExecuteCommandRequest(
            command=command,
            use_sudo=use_sudo,
            working_directory=working_directory,
            timeout=timeout,
        )

        try:
            # Execute via use case
            result = self.container.execute_command_use_case.execute(request)

            if result.success:
                # Format successful output
                output = "**Command Executed Successfully**\n\n"
                output += f"Command: `{result.command}`\n"
                output += f"Exit Code: {result.exit_code}\n"
                output += f"Execution Time: {result.execution_time:.2f}s\n\n"

                if result.stdout:
                    output += "**Output:**\n```\n"
                    output += result.stdout
                    output += "\n```\n"

                if result.stderr:
                    output += "\n**Warnings/Errors:**\n```\n"
                    output += result.stderr
                    output += "\n```"

                return self.format_success(output)
            else:
                # Format error output
                error_msg = f"Command failed with exit code {result.exit_code}"
                if result.stderr:
                    error_msg += f": {result.stderr}"
                elif result.stdout:
                    error_msg += f". Output: {result.stdout}"

                return self.format_error(error_msg)

        except ValueError as e:
            # Security validation failed
            return self.format_error(f"Security validation failed: {e!s}")
        except Exception as e:
            # Other execution errors
            return self.format_error(f"Command execution failed: {e!s}")

    async def _write_file(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Write file with security validation."""
        path = arguments.get("path")
        content = arguments.get("content")
        mode = arguments.get("mode")
        backup = arguments.get("backup", False)
        create_directories = arguments.get("create_directories", False)

        # Validate required arguments
        if not path:
            return self.format_error("File path is required")
        if content is None:  # Allow empty content
            return self.format_error("File content is required")

        # Create request object
        request = WriteFileRequest(
            path=path,
            content=content,
            mode=mode,
            backup=backup,
            create_directories=create_directories,
        )

        try:
            # Execute via use case
            result = self.container.write_file_use_case.execute(request)

            if result.success:
                # Format successful output
                output = "**File Written Successfully**\n\n"
                output += f"Path: `{path}`\n"
                output += f"Content Length: {len(content)} characters\n"

                if mode:
                    output += f"Permissions: {mode}\n"
                if backup:
                    output += "Backup: Created\n"
                if create_directories:
                    output += "Directories: Created as needed\n"

                output += f"Execution Time: {result.execution_time:.2f}s\n"

                if result.stdout:
                    output += f"\n**Details:**\n{result.stdout}"

                return self.format_success(output)
            else:
                # Format error output
                error_msg = f"File write failed with exit code {result.exit_code}"
                if result.stderr:
                    error_msg += f": {result.stderr}"
                elif result.stdout:
                    error_msg += f". Output: {result.stdout}"

                return self.format_error(error_msg)

        except ValueError as e:
            # Security validation failed
            return self.format_error(f"Security validation failed: {e!s}")
        except Exception as e:
            # Other execution errors
            return self.format_error(f"File write failed: {e!s}")
