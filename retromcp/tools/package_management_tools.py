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
                description="Manage system packages (install, remove, update, list, search, check)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["install", "remove", "update", "list", "search", "check"],
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

            # Get the client from container
            client = self.container.retropie_client

            if action == "install":
                if not packages:
                    return self.format_error("Package names are required for install action")
                # Use the InstallPackagesUseCase for install
                use_case = self.container.install_packages_use_case
                result = use_case.execute(packages)
            elif action == "remove":
                if not packages:
                    return self.format_error("Package names are required for remove action")
                # Use direct command for remove
                package_list = " ".join(packages)
                result = client.execute_command(f"apt-get remove -y {package_list}", use_sudo=True)
            elif action == "update":
                if packages:
                    # Update specific packages
                    package_list = " ".join(packages)
                    result = client.execute_command(f"apt-get update && apt-get upgrade -y {package_list}", use_sudo=True)
                else:
                    # Update all packages using system use case
                    use_case = self.container.update_system_use_case
                    result = use_case.execute()
            elif action == "list":
                result = client.execute_command("dpkg --get-selections | grep -v deinstall")
            elif action == "search":
                if not query:
                    return self.format_error("Search query is required for search action")
                result = client.execute_command(f"apt-cache search {query}")
            elif action == "check":
                if not packages:
                    return self.format_error("Package names are required for check action")
                # Check if packages are installed
                package_list = " ".join(packages)
                result = client.execute_command(f"dpkg -l {package_list} 2>/dev/null | grep '^ii'")
            else:
                return self.format_error(f"Unknown action: {action}")

            if result.success:
                if action == "check":
                    # Parse package check output for better formatting
                    if result.stdout.strip():
                        formatted_output = "Package Status Check:\n"
                        for line in result.stdout.strip().split('\n'):
                            if line.startswith('ii '):
                                # Extract package name from dpkg output
                                parts = line.split()
                                if len(parts) >= 2:
                                    package_name = parts[1]
                                    formatted_output += f"✅ {package_name}: Installed\n"
                        return [TextContent(type="text", text=formatted_output.strip())]
                    else:
                        return self.format_error("No packages found")
                else:
                    return self.format_success(f"Package {action}: {result.stdout}")
            else:
                return self.format_error(f"Failed to {action} packages: {result.stderr}")

        except Exception as e:
            return self.format_error(f"Package management error: {e!s}")
