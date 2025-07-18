"""System update tools for managing system updates."""

from typing import Any
from typing import Dict
from typing import List

from mcp.types import EmbeddedResource
from mcp.types import ImageContent
from mcp.types import TextContent
from mcp.types import Tool

from .base import BaseTool


class SystemUpdateTools(BaseTool):
    """Tools for managing system updates."""

    def get_tools(self) -> List[Tool]:
        """Return list of available system update tools."""
        return [
            Tool(
                name="update_system",
                description="Perform system updates and maintenance",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["update", "upgrade", "check", "cleanup"],
                            "description": "Update action to perform",
                        },
                        "force": {
                            "type": "boolean",
                            "description": "Force the update operation",
                            "default": False,
                        },
                    },
                    "required": ["action"],
                },
            )
        ]

    async def handle_tool_call(
        self, name: str, arguments: Dict[str, Any]
    ) -> List[TextContent | ImageContent | EmbeddedResource]:
        """Handle system update tool calls."""
        if name == "update_system":
            return await self._handle_system_update(arguments)
        else:
            return self.format_error(f"Unknown tool: {name}")

    async def _handle_system_update(
        self, arguments: Dict[str, Any]
    ) -> List[TextContent | ImageContent | EmbeddedResource]:
        """Handle system update operations."""
        try:
            action = arguments.get("action")
            force = arguments.get("force", False)

            if not action:
                return self.format_error("Action is required")

            # Get the client from container
            client = self.container.retropie_client

            if action == "update":
                result = client.execute_command("sudo apt update", use_sudo=False)
                if result.success:
                    return self.format_success(f"System update completed:\n{result.stdout}")
                else:
                    return self.format_error(f"System update failed:\n{result.stderr}")
            elif action == "upgrade":
                # For upgrade, run apt upgrade with force flag if specified
                upgrade_cmd = "sudo apt upgrade"
                if force:
                    upgrade_cmd += " -y"
                result = client.execute_command(upgrade_cmd, use_sudo=False)
                if result.success:
                    return self.format_success(f"System upgrade completed:\n{result.stdout}")
                else:
                    return self.format_error(f"System upgrade failed:\n{result.stderr}")
            elif action == "check":
                # Check for available updates
                result = client.execute_command("sudo apt list --upgradable", use_sudo=False)
                if result.success:
                    return self.format_info(f"Update check completed:\n{result.stdout}")
                else:
                    return self.format_error(f"Update check failed:\n{result.stderr}")
            elif action == "cleanup":
                # Clean up after updates
                result = client.execute_command("sudo apt autoremove -y", use_sudo=False)
                if result.success:
                    return self.format_success(f"System cleanup completed:\n{result.stdout}")
                else:
                    return self.format_error(f"System cleanup failed:\n{result.stderr}")
            else:
                return self.format_error(f"Unknown action: {action}")

        except Exception as e:
            return self.format_error(f"System update error: {e!s}")
