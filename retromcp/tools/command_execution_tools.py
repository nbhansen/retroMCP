"""Command execution tools for running system commands."""

import shlex
from typing import Any
from typing import Dict
from typing import List

from mcp.types import EmbeddedResource
from mcp.types import ImageContent
from mcp.types import TextContent
from mcp.types import Tool

from ..domain.models import ExecuteCommandRequest
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
            timeout = arguments.get("timeout", 60)
            escape_args = arguments.get("escape_args", True)

            if not command:
                return self.format_error("Command is required")

            # Create command request
            request = ExecuteCommandRequest(
                command=command,
                use_sudo=use_sudo,
                timeout=timeout,
                escape_args=escape_args,
            )

            # Get the use case from container
            use_case = self.container.get_execute_command_use_case()
            result = use_case.execute(request)

            if result.success:
                output = f"Command executed successfully (exit code: {result.exit_code})"
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