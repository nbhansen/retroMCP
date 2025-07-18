"""Command execution tools for running system commands."""

from typing import Any
from typing import Dict
from typing import List

from mcp.types import EmbeddedResource
from mcp.types import ImageContent
from mcp.types import TextContent
from mcp.types import Tool

from .base import BaseTool


class CommandExecutionTools(BaseTool):
    """Tools for executing system commands."""

    def get_tools(self) -> List[Tool]:
        """Return list of available command execution tools."""
        return [
            Tool(
                name="execute_command",
                description="Execute system commands with proper security controls",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "Command to execute",
                        },
                        "use_sudo": {
                            "type": "boolean",
                            "description": "Execute with sudo privileges",
                            "default": False,
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Command timeout in seconds",
                            "default": 60,
                        },
                        "escape_args": {
                            "type": "boolean",
                            "description": "Escape command arguments for security",
                            "default": True,
                        },
                    },
                    "required": ["command"],
                },
            )
        ]

    async def handle_tool_call(
        self, name: str, arguments: Dict[str, Any]
    ) -> List[TextContent | ImageContent | EmbeddedResource]:
        """Handle command execution tool calls."""
        if name == "execute_command":
            return await self._handle_command_execution(arguments)
        else:
            return self.format_error(f"Unknown tool: {name}")

    async def _handle_command_execution(
        self, arguments: Dict[str, Any]
    ) -> List[TextContent | ImageContent | EmbeddedResource]:
        """Handle command execution operations."""
        try:
            command = arguments.get("command")
            use_sudo = arguments.get("use_sudo", False)
            working_directory = arguments.get("working_directory")

            if not command:
                return self.format_error("Command is required")

            # Basic security validation
            dangerous_patterns = [
                "rm -rf /",
                "dd if=/dev/zero",
                "mkfs",
                "> /dev/sda",
                "chmod 777 /",
            ]

            for pattern in dangerous_patterns:
                if pattern in command:
                    return self.format_error("Security validation failed: Command contains dangerous pattern")

            # Get the client from container
            client = self.container.retropie_client

            # Execute command with options
            if working_directory:
                command = f"cd {working_directory} && {command}"

            result = client.execute_command(command, use_sudo=use_sudo)

            if result.success:
                output = "Command Executed Successfully"
                if result.stdout:
                    output += f"\n\nSTDOUT:\n{result.stdout}"
                if result.stderr:
                    output += f"\n\nSTDERR:\n{result.stderr}"
                return self.format_success(output)
            else:
                error_msg = f"Command failed (exit code: {result.exit_code})"
                if result.stderr:
                    error_msg += f"\n\nSTDERR:\n{result.stderr}"
                if result.stdout:
                    error_msg += f"\n\nSTDOUT:\n{result.stdout}"
                return self.format_error(error_msg)

        except Exception as e:
            return self.format_error(f"Command execution error: {e!s}")
