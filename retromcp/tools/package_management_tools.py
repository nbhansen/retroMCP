"""Package management tools for system packages."""

from typing import Any
from typing import Dict
from typing import List
from typing import Union

from mcp.types import EmbeddedResource
from mcp.types import ImageContent
from mcp.types import TextContent
from mcp.types import Tool

from ..domain.models import ExecutionError, ValidationError
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
                            "enum": [
                                "install",
                                "remove",
                                "update",
                                "list",
                                "search",
                                "check",
                            ],
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
                    return self.format_error(
                        "Package names are required for install action"
                    )
                # Use the InstallPackagesUseCase for install
                use_case = self.container.install_packages_use_case
                install_result = use_case.execute(packages)

                # Handle Result pattern from use case
                if install_result.is_error():
                    error = install_result.error_or_none
                    # Check for details in the error to provide better feedback
                    error_msg = self._format_install_error(packages, error)
                    return [TextContent(type="text", text=error_msg)]

                result = install_result.value
            elif action == "remove":
                if not packages:
                    return self.format_error(
                        "Package names are required for remove action"
                    )
                # Use direct command for remove
                package_list = " ".join(packages)
                result = client.execute_command(
                    f"sudo apt-get remove -y {package_list}"
                )
            elif action == "update":
                if packages:
                    # Update specific packages
                    package_list = " ".join(packages)
                    result = client.execute_command(
                        f"sudo apt-get update && sudo apt-get upgrade -y {package_list}"
                    )
                else:
                    # Update all packages using system use case
                    use_case = self.container.update_system_use_case
                    update_result = use_case.execute()

                    # Handle Result pattern from use case
                    if update_result.is_error():
                        error = update_result.error_or_none
                        return self.format_error(
                            f"System update failed: {error.message}"
                        )

                    result = update_result.value
            elif action == "list":
                result = client.execute_command(
                    "dpkg --get-selections | grep -v deinstall"
                )
            elif action == "search":
                if not query:
                    return self.format_error(
                        "Search query is required for search action"
                    )
                result = client.execute_command(f"apt-cache search {query}")
            elif action == "check":
                if not packages:
                    return self.format_error(
                        "Package names are required for check action"
                    )
                # Check each package individually to get precise status
                return await self._check_packages_status(client, packages)
            else:
                return self.format_error(f"Unknown action: {action}")

            if result.success:
                return self.format_success(f"Package {action}: {result.stdout}")
            else:
                return self.format_error(
                    f"Failed to {action} packages: {result.stderr}"
                )

        except Exception as e:
            return self.format_error(f"Package management error: {e!s}")

    def _format_install_error(self, packages: List[str], error: Union[ExecutionError, ValidationError]) -> str:
        """Format installation error with detailed package information."""
        base_msg = "❌ Package installation failed"

        # Check for details in error object first (higher priority than stderr parsing)
        if hasattr(error, "details") and error.details:
            details = error.details
            if "suggestions" in details:
                failed_pkg = details.get(
                    "failed_package", packages[0] if packages else "package"
                )
                suggestions = details["suggestions"]
                msg = f"{base_msg}: Unable to locate package '{failed_pkg}'\n"
                if suggestions:
                    msg += f"💡 Did you mean: {', '.join(suggestions[:3])}?"
                else:
                    msg += f"💡 Try searching with: manage_package action=search query={failed_pkg}"
                return msg
            elif "failed_packages" in details:
                failed = details["failed_packages"]
                return f"{base_msg}: Unable to locate packages: {', '.join(failed)}"
            elif "succeeded" in details and "failed" in details:
                succeeded = details["succeeded"]
                failed = details["failed"]
                total = details.get("total", len(succeeded) + len(failed))
                msg = f"{base_msg}: {len(succeeded)}/{total} packages installed\n"
                if succeeded:
                    msg += f"✅ Succeeded: {', '.join(succeeded)}\n"
                if failed:
                    msg += f"❌ Failed: {', '.join(failed)}\n"
                # Add summary count
                msg += f"\nSummary: {len(succeeded)}/{total} packages installed"
                return msg

        # Extract package-specific information from error
        if hasattr(error, "stderr") and error.stderr:
            stderr = error.stderr
            failed_packages = []

            # Look for "Unable to locate package" errors
            for line in stderr.split("\n"):
                if "Unable to locate package" in line:
                    # Extract package name from error
                    parts = line.split("Unable to locate package")
                    if len(parts) > 1:
                        pkg_name = parts[1].strip()
                        if pkg_name:
                            failed_packages.append(pkg_name)

            if failed_packages:
                if len(failed_packages) == len(packages):
                    # All packages failed
                    return f"{base_msg}: Unable to locate packages: {', '.join(failed_packages)}"
                else:
                    # Some packages failed
                    succeeded = [p for p in packages if p not in failed_packages]
                    msg = f"{base_msg}: Partial failure\n"
                    if succeeded:
                        msg += f"✅ Succeeded: {', '.join(succeeded)}\n"
                    msg += f"❌ Failed: {', '.join(failed_packages)}\n"
                    # Add summary
                    total = len(packages)
                    msg += f"\nSummary: {len(succeeded)}/{total} packages installed"
                    return msg

        # Fallback to include package names in error
        pkg_list = ", ".join(packages) if packages else "packages"
        return f"{base_msg} for {pkg_list}: {error.message}"

    async def _check_packages_status(
        self, client: "RetroPieClient", packages: List[str]
    ) -> List[TextContent | ImageContent | EmbeddedResource]:
        """Check the status of multiple packages individually."""
        installed_packages = []
        not_found_packages = []
        error_packages = []

        for package in packages:
            # Check individual package status
            result = client.execute_command(
                f"dpkg -l {package} 2>/dev/null | grep '^ii'"
            )

            if result.success:
                if result.stdout.strip():
                    # Package is installed - extract package name from dpkg output
                    # Only look for the specific package we're checking
                    found_package = False
                    for line in result.stdout.strip().split("\n"):
                        if line.startswith("ii "):
                            parts = line.split()
                            if len(parts) >= 2 and parts[1] == package:
                                installed_packages.append(package)
                                found_package = True
                                break

                    if not found_package:
                        # dpkg output didn't contain our specific package
                        not_found_packages.append(package)
                else:
                    # No output means package not installed or doesn't exist
                    # Check if package exists in repositories
                    search_result = client.execute_command(
                        f"apt-cache show {package} >/dev/null 2>&1 && echo 'exists' || echo 'not_found'"
                    )
                    if search_result.success and "not_found" in search_result.stdout:
                        not_found_packages.append(package)
                    else:
                        # Package exists but not installed
                        not_found_packages.append(package)
            else:
                # Command failed
                error_packages.append(package)

        # Format comprehensive status report
        if not installed_packages and not not_found_packages and error_packages:
            # All packages had errors - still show individual status
            status_lines = ["Package Status Check:"]
            for package in error_packages:
                status_lines.append(f"⚠️ {package}: Check failed")

            status_lines.append("")
            status_lines.append(
                f"Summary: 0/{len(packages)} installed, {len(error_packages)}/{len(packages)} check failed"
            )

            return [TextContent(type="text", text="\n".join(status_lines))]

        # Build status report
        status_lines = ["Package Status Check:"]

        # Show installed packages
        for package in installed_packages:
            status_lines.append(f"✅ {package}: Installed")

        # Show not found packages
        for package in not_found_packages:
            status_lines.append(f"❌ {package}: Not installed")

        # Show error packages
        for package in error_packages:
            status_lines.append(f"⚠️ {package}: Check failed")

        # Add summary if there are mixed results
        if len(packages) > 1:
            total = len(packages)
            installed_count = len(installed_packages)
            not_found_count = len(not_found_packages)
            error_count = len(error_packages)

            status_lines.append("")
            status_lines.append(f"Summary: {installed_count}/{total} installed")
            if not_found_count > 0:
                status_lines.append(f"         {not_found_count}/{total} not installed")
            if error_count > 0:
                status_lines.append(f"         {error_count}/{total} check failed")

        return [TextContent(type="text", text="\n".join(status_lines))]
