"""Management tools for system administration tasks."""

from typing import Any
from typing import Dict
from typing import List

from mcp.types import EmbeddedResource
from mcp.types import ImageContent
from mcp.types import TextContent
from mcp.types import Tool

from .base import BaseTool


class ManagementTools(BaseTool):
    """Tools for system management operations."""

    def get_tools(self) -> List[Tool]:
        """Return list of available management tools.

        Returns:
            List of Tool objects for management operations.
        """
        return [
            Tool(
                name="manage_services",
                description="Manage systemd services (start, stop, restart, enable, disable, status)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": [
                                "start",
                                "stop",
                                "restart",
                                "enable",
                                "disable",
                                "status",
                            ],
                            "description": "Service management action",
                        },
                        "service": {
                            "type": "string",
                            "description": "Name of the service to manage",
                        },
                    },
                    "required": ["action", "service"],
                },
            ),
        ]

    def _execute_command(self, command: str) -> tuple[int, str, str]:
        """Execute command via container and return tuple for compatibility.

        Args:
            command: Command to execute

        Returns:
            Tuple of (exit_code, stdout, stderr) for backward compatibility
        """
        result = self.container.retropie_client.execute_command(command)
        return result.exit_code, result.stdout, result.stderr

    async def handle_tool_call(
        self, name: str, arguments: Dict[str, Any]
    ) -> List[TextContent | ImageContent | EmbeddedResource]:
        """Handle tool calls for management operations.

        Args:
            name: Name of the tool to call.
            arguments: Arguments for the tool.

        Returns:
            List of content objects with the tool's response.
        """
        try:
            if name == "manage_services":
                return await self._manage_services(arguments)
            else:
                return self.format_error(f"Unknown tool: {name}")
        except Exception as e:
            return self.format_error(f"Error in {name}: {e!s}")

    async def _manage_services(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Manage systemd services."""
        action = arguments.get("action")
        service = arguments.get("service")

        # Validate inputs
        if not service:
            return self.format_error("Service name required")

        valid_actions = ["start", "stop", "restart", "enable", "disable", "status"]
        if action not in valid_actions:
            return self.format_error(
                f"Invalid action: {action}. Must be one of: {', '.join(valid_actions)}"
            )

        # Execute the appropriate systemctl command
        if action == "status":
            # Status doesn't require sudo
            exit_code, stdout, stderr = self._execute_command(
                f"systemctl status {service} --no-pager"
            )

            # Parse status output
            if "Active: active (running)" in stdout:
                status = "✅ Active (running)"
            elif "Active: inactive (dead)" in stdout:
                status = "⚠️ Inactive (dead)"
            elif "Active: failed" in stdout:
                status = "❌ Failed"
            else:
                status = "❓ Unknown"

            # Check if enabled
            enabled = "enabled;" in stdout or "enabled; vendor" in stdout
            enabled_status = "enabled" if enabled else "disabled"

            # Format output
            output = f"**Service Status: {service}**\n\n"
            output += f"Status: {status}\n"
            output += f"Startup: {enabled_status}\n\n"

            # Include relevant parts of systemctl output
            if stdout:
                lines = stdout.strip().split("\n")
                # Get first few lines with service info
                for line in lines[:10]:
                    if line.strip():
                        output += f"{line}\n"

            return [TextContent(type="text", text=output)]

        else:
            # All other actions require sudo
            command = f"sudo systemctl {action} {service}"
            exit_code, stdout, stderr = self._execute_command(command)

            if exit_code == 0:
                # Success messages
                action_past = {
                    "start": "started",
                    "stop": "stopped",
                    "restart": "restarted",
                    "enable": "enabled",
                    "disable": "disabled",
                }

                message = f"Service '{service}' {action_past.get(action, action)} successfully"
                if stdout:
                    message += f"\n\n{stdout}"

                return self.format_success(message)
            else:
                # Error handling
                error_msg = stderr or stdout or f"Failed to {action} service"
                return self.format_error(f"Failed to {action} '{service}': {error_msg}")
