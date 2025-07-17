"""Service management tools for system services."""

from typing import Any
from typing import Dict
from typing import List

from mcp.types import EmbeddedResource
from mcp.types import ImageContent
from mcp.types import TextContent
from mcp.types import Tool

from .base import BaseTool


class ServiceManagementTools(BaseTool):
    """Tools for managing system services."""

    def get_tools(self) -> List[Tool]:
        """Return list of available service management tools."""
        return [
            Tool(
                name="manage_service",
                description="Manage system services (start, stop, restart, enable, disable, status)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["start", "stop", "restart", "enable", "disable", "status"],
                            "description": "Action to perform on the service",
                        },
                        "name": {
                            "type": "string",
                            "description": "Name of the service",
                        },
                    },
                    "required": ["action", "name"],
                },
            )
        ]

    async def handle_tool_call(
        self, name: str, arguments: Dict[str, Any]
    ) -> List[TextContent | ImageContent | EmbeddedResource]:
        """Handle service management tool calls."""
        if name == "manage_service":
            return await self._handle_service_management(arguments)
        else:
            return self.format_error(f"Unknown tool: {name}")

    async def _handle_service_management(
        self, arguments: Dict[str, Any]
    ) -> List[TextContent | ImageContent | EmbeddedResource]:
        """Handle service management operations."""
        try:
            action = arguments.get("action")
            service_name = arguments.get("name")

            if not action or not service_name:
                return self.format_error("Both 'action' and 'name' are required")

            # Get the use case from container
            use_case = self.container.get_service_management_use_case()
            
            if action == "start":
                result = use_case.start_service(service_name)
            elif action == "stop":
                result = use_case.stop_service(service_name)
            elif action == "restart":
                result = use_case.restart_service(service_name)
            elif action == "enable":
                result = use_case.enable_service(service_name)
            elif action == "disable":
                result = use_case.disable_service(service_name)
            elif action == "status":
                result = use_case.get_service_status(service_name)
            else:
                return self.format_error(f"Unknown action: {action}")

            if result.success:
                return self.format_success(f"Service {service_name} {action}: {result.stdout}")
            else:
                return self.format_error(f"Failed to {action} service {service_name}: {result.stderr}")

        except Exception as e:
            return self.format_error(f"Service management error: {e!s}")