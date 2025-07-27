"""Connection management tools for testing and managing connections."""

from typing import Any
from typing import Dict
from typing import List

from mcp.types import EmbeddedResource
from mcp.types import ImageContent
from mcp.types import TextContent
from mcp.types import Tool

from .base import BaseTool


class ConnectionManagementTools(BaseTool):
    """Tools for managing system connections."""

    def get_tools(self) -> List[Tool]:
        """Return list of available connection management tools."""
        return [
            Tool(
                name="manage_connection",
                description="Test and manage system connections",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["test", "status", "reconnect"],
                            "description": "Connection action to perform",
                        },
                    },
                    "required": ["action"],
                },
            )
        ]

    async def handle_tool_call(
        self, name: str, arguments: Dict[str, Any]
    ) -> List[TextContent | ImageContent | EmbeddedResource]:
        """Handle connection management tool calls."""
        if name == "manage_connection":
            return await self._handle_connection_management(arguments)
        else:
            return self.format_error(f"Unknown tool: {name}")

    async def _handle_connection_management(
        self, arguments: Dict[str, Any]
    ) -> List[TextContent | ImageContent | EmbeddedResource]:
        """Handle connection management operations."""
        try:
            action = arguments.get("action")

            if not action:
                return self.format_error("Action is required")

            # Get the use case from container
            use_case = self.container.test_connection_use_case

            if action == "test":
                result = use_case.execute()
                if result.is_error():
                    error = result.error_or_none
                    return self.format_error(f"Connection test failed: {error.message}")

                connection_info = result.value
                if connection_info.connected:
                    return self.format_success(
                        f"Connection test successful!\n"
                        f"Host: {connection_info.host}\n"
                        f"Port: {connection_info.port}\n"
                        f"Username: {connection_info.username}"
                    )
                else:
                    return self.format_error("Connection test failed")
            elif action == "status":
                result = use_case.execute()
                if result.is_error():
                    error = result.error_or_none
                    return self.format_error(
                        f"Failed to get connection status: {error.message}"
                    )

                connection_info = result.value
                status = "Connected" if connection_info.connected else "Disconnected"
                return self.format_info(
                    f"Connection Status: {status}\n"
                    f"Host: {connection_info.host}\n"
                    f"Port: {connection_info.port}\n"
                    f"Username: {connection_info.username}"
                )
            elif action == "reconnect":
                # Force reconnection by testing connection
                result = use_case.execute()
                if result.is_error():
                    error = result.error_or_none
                    return self.format_error(f"Reconnection failed: {error.message}")

                connection_info = result.value
                if connection_info.connected:
                    return self.format_success("Reconnection successful")
                else:
                    return self.format_error("Reconnection failed")
            else:
                return self.format_error(f"Unknown action: {action}")

        except Exception as e:
            return self.format_error(f"Connection management error: {e!s}")
