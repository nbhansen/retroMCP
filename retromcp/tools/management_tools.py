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
            Tool(
                name="manage_packages",
                description="Manage system packages (install, remove, update, search, list)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["install", "remove", "update", "search", "list"],
                            "description": "Package management action",
                        },
                        "packages": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of package names (required for install, remove, search)",
                        },
                    },
                    "required": ["action"],
                },
            ),
            Tool(
                name="manage_files",
                description="Manage files and directories (list, create, delete, copy, move, permissions, backup)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": [
                                "list",
                                "create",
                                "delete",
                                "copy",
                                "move",
                                "permissions",
                                "backup",
                            ],
                            "description": "File management action",
                        },
                        "path": {
                            "type": "string",
                            "description": "File or directory path",
                        },
                        "destination": {
                            "type": "string",
                            "description": "Destination path (for copy/move actions)",
                        },
                        "mode": {
                            "type": "string",
                            "description": "Permission mode (for permissions action, e.g., '755')",
                        },
                        "type": {
                            "type": "string",
                            "enum": ["file", "directory"],
                            "description": "Type of item to create",
                        },
                    },
                    "required": ["action", "path"],
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
            elif name == "manage_packages":
                return await self._manage_packages(arguments)
            elif name == "manage_files":
                return await self._manage_files(arguments)
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

    async def _manage_packages(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Manage system packages."""
        action = arguments.get("action")
        packages = arguments.get("packages", [])

        valid_actions = ["install", "remove", "update", "search", "list"]
        if action not in valid_actions:
            return self.format_error(
                f"Invalid action: {action}. Must be one of: {', '.join(valid_actions)}"
            )

        # Check if packages are required for this action
        if action in ["install", "remove", "search"] and not packages:
            return self.format_error(f"Package names required for '{action}' action")

        if action == "install":
            # Install packages
            package_list = " ".join(packages)
            exit_code, stdout, stderr = self._execute_command(
                f"sudo apt-get install -y {package_list}"
            )

            if exit_code == 0:
                message = f"Successfully installed packages: {', '.join(packages)}"
                if stdout:
                    message += f"\n\n{stdout}"
                return self.format_success(message)
            else:
                error_msg = stderr or stdout or "Installation failed"
                return self.format_error(f"Failed to install packages: {error_msg}")

        elif action == "remove":
            # Remove packages
            package_list = " ".join(packages)
            exit_code, stdout, stderr = self._execute_command(
                f"sudo apt-get remove -y {package_list}"
            )

            if exit_code == 0:
                message = f"Successfully removed packages: {', '.join(packages)}"
                if stdout:
                    message += f"\n\n{stdout}"
                return self.format_success(message)
            else:
                error_msg = stderr or stdout or "Removal failed"
                return self.format_error(f"Failed to remove packages: {error_msg}")

        elif action == "update":
            # Update package lists and upgrade
            # First update package lists
            exit_code, stdout, stderr = self._execute_command("sudo apt-get update")
            if exit_code != 0:
                return self.format_error(f"Failed to update package lists: {stderr}")

            # Then upgrade packages
            exit_code, stdout, stderr = self._execute_command("sudo apt-get upgrade -y")
            if exit_code == 0:
                message = "System packages updated successfully"
                if stdout:
                    message += f"\n\n{stdout}"
                return self.format_success(message)
            else:
                error_msg = stderr or stdout or "Upgrade failed"
                return self.format_error(f"Failed to upgrade packages: {error_msg}")

        elif action == "search":
            # Search for packages
            search_term = packages[0] if packages else ""
            exit_code, stdout, stderr = self._execute_command(
                f"apt-cache search {search_term}"
            )

            if exit_code == 0:
                if stdout.strip():
                    output = f"**Package Search Results for '{search_term}':**\n\n"
                    output += stdout
                    return [TextContent(type="text", text=output)]
                else:
                    return self.format_info(
                        f"No packages found matching '{search_term}'"
                    )
            else:
                error_msg = stderr or stdout or "Search failed"
                return self.format_error(f"Package search failed: {error_msg}")

        elif action == "list":
            # List installed packages
            exit_code, stdout, stderr = self._execute_command("dpkg -l | grep '^ii'")

            if exit_code == 0:
                if stdout.strip():
                    output = "**Installed Packages:**\n\n"
                    # Format the output nicely
                    lines = stdout.strip().split("\n")
                    for line in lines[:20]:  # Limit to first 20 packages
                        if line.strip():
                            parts = line.split()
                            if len(parts) >= 3:
                                package_name = parts[1]
                                version = parts[2]
                                output += f"- {package_name} ({version})\n"

                    if len(lines) > 20:
                        output += f"\n... and {len(lines) - 20} more packages"

                    return [TextContent(type="text", text=output)]
                else:
                    return self.format_info("No packages found")
            else:
                error_msg = stderr or stdout or "List failed"
                return self.format_error(f"Failed to list packages: {error_msg}")

        return self.format_error(f"Unknown package action: {action}")

    async def _manage_files(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Manage files and directories."""
        action = arguments.get("action")
        path = arguments.get("path")
        destination = arguments.get("destination")
        mode = arguments.get("mode")
        file_type = arguments.get("type")

        valid_actions = [
            "list",
            "create",
            "delete",
            "copy",
            "move",
            "permissions",
            "backup",
        ]
        if action not in valid_actions:
            return self.format_error(
                f"Invalid action: {action}. Must be one of: {', '.join(valid_actions)}"
            )

        if not path:
            return self.format_error("Path is required for file operations")

        if action == "list":
            # List directory contents
            exit_code, stdout, stderr = self._execute_command(f"ls -la {path}")

            if exit_code == 0:
                output = f"**Directory Contents: {path}**\n\n"
                output += "```\n"
                output += stdout
                output += "\n```"
                return [TextContent(type="text", text=output)]
            else:
                error_msg = stderr or stdout or "List failed"
                return self.format_error(f"Failed to list directory: {error_msg}")

        elif action == "create":
            # Create file or directory (use sudo for system locations)
            if file_type == "directory":
                exit_code, stdout, stderr = self._execute_command(
                    f"sudo mkdir -p {path}"
                )
                if exit_code == 0:
                    return self.format_success(
                        f"Directory '{path}' created successfully"
                    )
                else:
                    error_msg = stderr or stdout or "Creation failed"
                    return self.format_error(f"Failed to create directory: {error_msg}")
            else:
                # Create empty file
                exit_code, stdout, stderr = self._execute_command(f"sudo touch {path}")
                if exit_code == 0:
                    return self.format_success(f"File '{path}' created successfully")
                else:
                    error_msg = stderr or stdout or "Creation failed"
                    return self.format_error(f"Failed to create file: {error_msg}")

        elif action == "delete":
            # Delete file or directory (use sudo for system files)
            exit_code, stdout, stderr = self._execute_command(f"sudo rm -rf {path}")

            if exit_code == 0:
                return self.format_success(f"'{path}' deleted successfully")
            else:
                error_msg = stderr or stdout or "Deletion failed"
                return self.format_error(f"Failed to delete: {error_msg}")

        elif action == "copy":
            # Copy file or directory (use sudo for system files)
            if not destination:
                return self.format_error("Destination path required for copy operation")

            exit_code, stdout, stderr = self._execute_command(
                f"sudo cp -r {path} {destination}"
            )

            if exit_code == 0:
                return self.format_success(
                    f"'{path}' copied to '{destination}' successfully"
                )
            else:
                error_msg = stderr or stdout or "Copy failed"
                return self.format_error(f"Failed to copy: {error_msg}")

        elif action == "move":
            # Move file or directory (use sudo for system files)
            if not destination:
                return self.format_error("Destination path required for move operation")

            exit_code, stdout, stderr = self._execute_command(
                f"sudo mv {path} {destination}"
            )

            if exit_code == 0:
                return self.format_success(
                    f"'{path}' moved to '{destination}' successfully"
                )
            else:
                error_msg = stderr or stdout or "Move failed"
                return self.format_error(f"Failed to move: {error_msg}")

        elif action == "permissions":
            # Change permissions (use sudo for system files)
            if not mode:
                return self.format_error(
                    "Permission mode required for permissions operation"
                )

            exit_code, stdout, stderr = self._execute_command(
                f"sudo chmod {mode} {path}"
            )

            if exit_code == 0:
                return self.format_success(
                    f"Permissions for '{path}' set to {mode} successfully"
                )
            else:
                error_msg = stderr or stdout or "Permission change failed"
                return self.format_error(f"Failed to change permissions: {error_msg}")

        elif action == "backup":
            # Create backup with timestamp (use sudo for system files)
            import datetime

            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{path}.backup_{timestamp}"

            exit_code, stdout, stderr = self._execute_command(
                f"sudo cp -r {path} {backup_path}"
            )

            if exit_code == 0:
                return self.format_success(f"Backup created: '{backup_path}'")
            else:
                error_msg = stderr or stdout or "Backup failed"
                return self.format_error(f"Failed to create backup: {error_msg}")

        return self.format_error(f"Unknown file action: {action}")
