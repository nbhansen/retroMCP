"""Package management tools for system packages."""

from typing import Any
from typing import Dict
from typing import List

from mcp.types import EmbeddedResource
from mcp.types import ImageContent
from mcp.types import TextContent
from mcp.types import Tool

from .base import BaseTool


class PackageManagementTools(BaseTool):
    """Tools for managing system packages."""

    def get_tools(self) -> List[Tool]:
        """Return list of available package management tools."""
        return [
            Tool(
                name="manage_package",
                description="Manage system packages (install, remove, update, list, search)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["install", "remove", "update", "list", "search"],
                            "description": "Action to perform on packages",
                        },
                        "packages": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of package names",
                        },
                        "query": {
                            "type": "string",
                            "description": "Search query for packages",
                        },
                    },
                    "required": ["action"],
                },
            )
        ]

    async def handle_tool_call(
        self, name: str, arguments: Dict[str, Any]
    ) -> List[TextContent | ImageContent | EmbeddedResource]:
        """Handle package management tool calls."""
        if name == "manage_package":
            return await self._handle_package_management(arguments)
        else:
            return self.format_error(f"Unknown tool: {name}")

    async def _handle_package_management(
        self, arguments: Dict[str, Any]
    ) -> List[TextContent | ImageContent | EmbeddedResource]:
        """Handle package management operations."""
        try:
            action = arguments.get("action")
            packages = arguments.get("packages", [])
            query = arguments.get("query", "")

            if not action:
                return self.format_error("'action' is required")

            # Get the use case from container
            use_case = self.container.get_package_management_use_case()
            
            if action == "install":
                if not packages:
                    return self.format_error("Package names are required for install action")
                result = use_case.install_packages(packages)
            elif action == "remove":
                if not packages:
                    return self.format_error("Package names are required for remove action")
                result = use_case.remove_packages(packages)
            elif action == "update":
                if packages:
                    result = use_case.update_packages(packages)
                else:
                    result = use_case.update_all_packages()
            elif action == "list":
                result = use_case.list_packages()
            elif action == "search":
                if not query:
                    return self.format_error("Search query is required for search action")
                result = use_case.search_packages(query)
            else:
                return self.format_error(f"Unknown action: {action}")

            if result.success:
                return self.format_success(f"Package {action}: {result.stdout}")
            else:
                return self.format_error(f"Failed to {action} packages: {result.stderr}")

        except Exception as e:
            return self.format_error(f"Package management error: {e!s}")