"""System management tools for unified administrative operations."""

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


class SystemManagementTools(BaseTool):
    """Unified system management tools for all administrative operations."""

    def get_tools(self) -> List[Tool]:
        """Return list of available system management tools.

        Returns:
            List containing single manage_system tool.
        """
        return [
            Tool(
                name="manage_system",
                description="Unified system administration tool for services, packages, files, commands, connection, info, and updates",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "resource": {
                            "type": "string",
                            "enum": [
                                "service",
                                "package",
                                "file",
                                "command",
                                "connection",
                                "info",
                                "update",
                            ],
                            "description": "Resource type to manage",
                        },
                        "action": {
                            "type": "string",
                            "description": "Action to perform on the resource",
                        },
                        # Service-specific parameters
                        "name": {
                            "type": "string",
                            "description": "Name of service or resource",
                        },
                        # Package-specific parameters
                        "packages": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of package names",
                        },
                        # File-specific parameters
                        "path": {
                            "type": "string",
                            "description": "File or directory path",
                        },
                        "content": {
                            "type": "string",
                            "description": "Content to write/append to file",
                        },
                        "destination": {
                            "type": "string",
                            "description": "Destination path for copy/move operations",
                        },
                        "mode": {
                            "type": "string",
                            "description": "Permission mode (e.g., '755')",
                        },
                        "owner": {
                            "type": "string",
                            "description": "Owner (user:group format)",
                        },
                        "lines": {
                            "type": "integer",
                            "description": "Number of lines to read (for read action)",
                        },
                        "create_parents": {
                            "type": "boolean",
                            "description": "Create parent directories if they don't exist",
                        },
                        "type": {
                            "type": "string",
                            "enum": ["file", "directory"],
                            "description": "Type of item to create",
                        },
                        "url": {
                            "type": "string",
                            "description": "URL to download from",
                        },
                        # Command-specific parameters
                        "command": {
                            "type": "string",
                            "description": "Shell command to execute",
                        },
                        "use_sudo": {
                            "type": "boolean",
                            "description": "Execute command with sudo privileges",
                        },
                        "working_directory": {
                            "type": "string",
                            "description": "Working directory for command execution",
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Command timeout in seconds",
                        },
                        "backup": {
                            "type": "boolean",
                            "description": "Create backup of existing file",
                        },
                        "create_directories": {
                            "type": "boolean",
                            "description": "Create parent directories if they don't exist",
                        },
                        # Info-specific parameters
                        "check_ports": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "List of ports to check",
                        },
                        # Update-specific parameters
                        "update_type": {
                            "type": "string",
                            "enum": ["basic", "full", "retropie-setup"],
                            "description": "Type of update to perform",
                        },
                        # BIOS check parameters
                        "system": {
                            "type": "string",
                            "enum": ["psx", "dreamcast", "neogeo", "segacd"],
                            "description": "System to check BIOS files for",
                        },
                    },
                    "required": ["resource", "action"],
                },
            ),
        ]

    async def handle_tool_call(
        self, name: str, arguments: Dict[str, Any]
    ) -> List[TextContent | ImageContent | EmbeddedResource]:
        """Handle tool calls for system management operations.

        Args:
            name: Name of the tool to call.
            arguments: Arguments for the tool.

        Returns:
            List of content objects with the tool's response.
        """
        try:
            if name == "manage_system":
                return await self._manage_system(arguments)
            else:
                return self.format_error(f"Unknown tool: {name}")
        except Exception as e:
            return self.format_error(f"Error in {name}: {e!s}")

    async def _manage_system(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Route system management requests to appropriate handlers."""
        resource = arguments.get("resource")
        action = arguments.get("action")

        if not resource:
            return self.format_error("Resource is required")
        if not action:
            return self.format_error("Action is required")

        # Route to appropriate resource handler
        if resource == "service":
            return await self._handle_service(action, arguments)
        elif resource == "package":
            return await self._handle_package(action, arguments)
        elif resource == "file":
            return await self._handle_file(action, arguments)
        elif resource == "command":
            return await self._handle_command(action, arguments)
        elif resource == "connection":
            return await self._handle_connection(action, arguments)
        elif resource == "info":
            return await self._handle_info(action, arguments)
        elif resource == "update":
            return await self._handle_update(action, arguments)
        else:
            return self.format_error(f"Invalid resource: {resource}")

    async def _handle_service(
        self, action: str, arguments: Dict[str, Any]
    ) -> List[TextContent]:
        """Handle service management operations."""
        valid_actions = ["start", "stop", "restart", "enable", "disable", "status"]
        if action not in valid_actions:
            return self.format_error(
                f"Invalid action: {action}. Must be one of: {', '.join(valid_actions)}"
            )

        name = arguments.get("name")
        if not name:
            return self.format_error("Service name is required")

        # Execute the appropriate systemctl command
        if action == "status":
            # Status doesn't require sudo
            exit_code, stdout, stderr = self._execute_command(
                f"systemctl status {name} --no-pager"
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
            output = f"**Service Status: {name}**\n\n"
            output += f"Status: {status}\n"
            output += f"Startup: {enabled_status}\n\n"

            # Include relevant parts of systemctl output
            if stdout:
                lines = stdout.strip().split("\n")
                for line in lines[:10]:
                    if line.strip():
                        output += f"{line}\n"

            return [TextContent(type="text", text=output)]
        else:
            # All other actions require sudo
            quoted_name = shlex.quote(name)
            command = f"sudo systemctl {action} {quoted_name}"
            exit_code, stdout, stderr = self._execute_command(command)

            if exit_code == 0:
                action_past = {
                    "start": "started",
                    "stop": "stopped",
                    "restart": "restarted",
                    "enable": "enabled",
                    "disable": "disabled",
                }
                message = (
                    f"Service '{name}' {action_past.get(action, action)} successfully"
                )
                if stdout:
                    message += f"\n\n{stdout}"
                return self.format_success(message)
            else:
                error_msg = stderr or stdout or f"Failed to {action} service"
                return self.format_error(f"Failed to {action} '{name}': {error_msg}")

    async def _handle_package(
        self, action: str, arguments: Dict[str, Any]
    ) -> List[TextContent]:
        """Handle package management operations."""
        valid_actions = [
            "install",
            "remove",
            "update",
            "upgrade",
            "search",
            "list",
            "check",
        ]
        if action not in valid_actions:
            return self.format_error(
                f"Invalid action: {action}. Must be one of: {', '.join(valid_actions)}"
            )

        packages = arguments.get("packages", [])

        # Check if packages are required for this action
        if action in ["install", "remove", "search", "check"] and not packages:
            return self.format_error(f"Package names required for '{action}' action")

        if action == "install":
            package_list = " ".join(shlex.quote(pkg) for pkg in packages)
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
            package_list = " ".join(shlex.quote(pkg) for pkg in packages)
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
            exit_code, stdout, stderr = self._execute_command("sudo apt-get update")
            if exit_code == 0:
                message = "Package lists updated successfully"
                if stdout:
                    message += f"\n\n{stdout}"
                return self.format_success(message)
            else:
                return self.format_error(f"Failed to update package lists: {stderr}")

        elif action == "upgrade":
            # First update package lists
            exit_code, stdout, stderr = self._execute_command("sudo apt-get update")
            if exit_code != 0:
                return self.format_error(f"Failed to update package lists: {stderr}")

            # Then upgrade packages
            exit_code, stdout, stderr = self._execute_command("sudo apt-get upgrade -y")
            if exit_code == 0:
                message = "System packages upgraded successfully"
                if stdout:
                    message += f"\n\n{stdout}"
                return self.format_success(message)
            else:
                error_msg = stderr or stdout or "Upgrade failed"
                return self.format_error(f"Failed to upgrade packages: {error_msg}")

        elif action == "search":
            search_term = packages[0] if packages else ""
            quoted_term = shlex.quote(search_term)
            exit_code, stdout, stderr = self._execute_command(
                f"apt-cache search {quoted_term}"
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
            exit_code, stdout, stderr = self._execute_command("dpkg -l | grep '^ii'")
            if exit_code == 0:
                if stdout.strip():
                    output = "**Installed Packages:**\n\n"
                    lines = stdout.strip().split("\n")
                    for line in lines[:20]:
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

        elif action == "check":
            results = []
            for package in packages:
                quoted_package = shlex.quote(package)
                exit_code, stdout, stderr = self._execute_command(
                    f"dpkg -l {quoted_package} 2>/dev/null | grep '^ii'"
                )
                if exit_code == 0 and stdout.strip():
                    results.append(f"✅ {package}: Installed")
                else:
                    results.append(f"❌ {package}: Not installed")

            output = "**Package Installation Status:**\n\n"
            output += "\n".join(results)
            return [TextContent(type="text", text=output)]

        return self.format_error(f"Unknown package action: {action}")

    async def _handle_file(
        self, action: str, arguments: Dict[str, Any]
    ) -> List[TextContent]:
        """Handle file management operations."""
        valid_actions = [
            "list",
            "create",
            "delete",
            "copy",
            "move",
            "permissions",
            "backup",
            "download",
            "write",
            "read",
            "append",
            "info",
            "ownership",
        ]
        if action not in valid_actions:
            return self.format_error(
                f"Invalid action: {action}. Must be one of: {', '.join(valid_actions)}"
            )

        path = arguments.get("path")
        if not path:
            return self.format_error("Path is required for file operations")

        # Implementation of file operations from ManagementTools
        if action == "read":
            lines = arguments.get("lines")
            quoted_path = shlex.quote(path)

            if lines and lines > 0:
                exit_code, stdout, stderr = self._execute_command(
                    f"head -n {lines} {quoted_path}"
                )
            else:
                exit_code, stdout, stderr = self._execute_command(f"cat {quoted_path}")

            if exit_code == 0:
                output = f"**File Contents: {path}**\n\n"
                if lines:
                    output += f"*(First {lines} lines)*\n\n"
                output += "```\n"
                output += stdout
                output += "\n```"
                return [TextContent(type="text", text=output)]
            else:
                error_msg = stderr or stdout or "Read failed"
                return self.format_error(f"Failed to read file: {error_msg}")

        elif action == "write":
            content = arguments.get("content")
            if not content:
                return self.format_error("Content required for write action")

            create_parents = arguments.get("create_parents", False)
            if create_parents:
                parent_dir = "/".join(path.split("/")[:-1])
                if parent_dir:
                    quoted_parent = shlex.quote(parent_dir)
                    self._execute_command(f"sudo mkdir -p {quoted_parent}")

            quoted_path = shlex.quote(path)
            quoted_content = shlex.quote(content)
            exit_code, stdout, stderr = self._execute_command(
                f"echo {quoted_content} | sudo tee {quoted_path} > /dev/null"
            )
            if exit_code == 0:
                return self.format_success(f"Content written to '{path}' successfully")
            else:
                error_msg = stderr or stdout or "Write failed"
                return self.format_error(f"Failed to write file: {error_msg}")

        elif action == "list":
            quoted_path = shlex.quote(path)
            exit_code, stdout, stderr = self._execute_command(f"ls -la {quoted_path}")
            if exit_code == 0:
                output = f"**Directory Contents: {path}**\n\n"
                output += "```\n"
                output += stdout
                output += "\n```"
                return [TextContent(type="text", text=output)]
            else:
                error_msg = stderr or stdout or "List failed"
                return self.format_error(f"Failed to list directory: {error_msg}")

        # Add other file operations as needed
        return self.format_error(f"File action '{action}' not yet implemented")

    async def _handle_command(
        self, action: str, arguments: Dict[str, Any]
    ) -> List[TextContent]:
        """Handle command execution operations."""
        if action != "execute":
            return self.format_error(f"Invalid action: {action}. Must be 'execute'")

        command = arguments.get("command")
        if not command:
            return self.format_error("Command is required")

        # Create request object
        request = ExecuteCommandRequest(
            command=command,
            use_sudo=arguments.get("use_sudo", False),
            working_directory=arguments.get("working_directory"),
            timeout=arguments.get("timeout"),
        )

        try:
            # Execute via use case
            result = self.container.execute_command_use_case.execute(request)

            if result.success:
                output = "**Command Executed Successfully**\n\n"
                output += f"Command: `{result.command}`\n"
                output += f"Exit Code: {result.exit_code}\n"
                output += f"Execution Time: {result.execution_time:.2f}s\n\n"

                if result.stdout:
                    output += "**Output:**\n```\n"
                    output += result.stdout
                    output += "\n```\n"

                if result.stderr:
                    output += "\n**Warnings/Errors:**\n```\n"
                    output += result.stderr
                    output += "\n```"

                return self.format_success(output)
            else:
                error_msg = f"Command failed with exit code {result.exit_code}"
                if result.stderr:
                    error_msg += f": {result.stderr}"
                elif result.stdout:
                    error_msg += f". Output: {result.stdout}"
                return self.format_error(error_msg)

        except ValueError as e:
            return self.format_error(f"Security validation failed: {e!s}")
        except Exception as e:
            return self.format_error(f"Command execution failed: {e!s}")

    async def _handle_connection(
        self, action: str, _arguments: Dict[str, Any]
    ) -> List[TextContent]:
        """Handle connection operations."""
        if action != "test":
            return self.format_error(f"Invalid action: {action}. Must be 'test'")

        try:
            connection_info = self.container.test_connection_use_case.execute()

            if connection_info.connected:
                return self.format_success(
                    f"Successfully connected to RetroPie!\n\n"
                    f"Host: {connection_info.host}:{connection_info.port}\n"
                    f"Username: {connection_info.username}\n"
                    f"Method: {connection_info.connection_method}\n"
                    f"Last connected: {connection_info.last_connected or 'Just now'}"
                )
            else:
                return self.format_error("Connected but couldn't get system info")
        except Exception as e:
            return self.format_error(
                f"Connection failed: {e!s}\n\nPlease check your .env configuration:\n- RETROPIE_HOST\n- RETROPIE_USERNAME\n- RETROPIE_PASSWORD or RETROPIE_SSH_KEY_PATH"
            )

    async def _handle_info(
        self, action: str, arguments: Dict[str, Any]
    ) -> List[TextContent]:
        """Handle system information operations."""
        if action != "get":
            return self.format_error(f"Invalid action: {action}. Must be 'get'")

        system_info = self.container.get_system_info_use_case.execute()
        check_ports = arguments.get("check_ports", [])

        output = "🖥️ RetroPie System Information:\n\n"

        # Temperature
        temp = system_info.cpu_temperature
        temp_status = "🔥" if temp > 80 else "⚠️" if temp > 70 else "✅"
        output += f"Temperature: {temp_status} {temp}°C\n"

        # Memory
        memory_total_mb = system_info.memory_total // (1024 * 1024)
        memory_used_mb = system_info.memory_used // (1024 * 1024)
        if system_info.memory_total > 0:
            used_pct = (system_info.memory_used / system_info.memory_total) * 100
            mem_status = "🔴" if used_pct > 90 else "🟡" if used_pct > 75 else "🟢"
            output += f"Memory: {mem_status} {memory_used_mb}MB / {memory_total_mb}MB ({used_pct:.1f}%)\n"
        else:
            output += f"Memory: ⚠️ {memory_used_mb}MB / {memory_total_mb}MB (Unable to determine usage)\n"

        # Disk
        disk_total_gb = system_info.disk_total // (1024 * 1024 * 1024)
        disk_used_gb = system_info.disk_used // (1024 * 1024 * 1024)
        if system_info.disk_total > 0:
            disk_used_pct = (system_info.disk_used / system_info.disk_total) * 100
            output += f"Disk Usage: {disk_used_gb}GB / {disk_total_gb}GB ({disk_used_pct:.1f}%)\n"
        else:
            output += f"Disk Usage: {disk_used_gb}GB / {disk_total_gb}GB (Unable to determine usage)\n"

        # Load average
        if system_info.load_average:
            load_1min = (
                system_info.load_average[0] if len(system_info.load_average) > 0 else 0
            )
            output += f"Load Average (1min): {load_1min:.2f}\n"

        # Uptime
        uptime_hours = system_info.uptime // 3600
        uptime_minutes = (system_info.uptime % 3600) // 60
        output += f"Uptime: {uptime_hours}h {uptime_minutes}m\n"

        # Hostname
        output += f"Hostname: {system_info.hostname}\n"

        # Port monitoring (if requested)
        if check_ports:
            output += "\n🔌 Port Status:\n"
            for port in check_ports:
                if isinstance(port, int) and 1 <= port <= 65535:
                    port_status = self._check_port(port)
                    status_emoji = "🟢" if port_status else "🔴"
                    status_text = "Open" if port_status else "Closed"
                    output += f"  {status_emoji} Port {port}: {status_text}\n"
                else:
                    output += f"  ⚠️ Port {port}: Invalid port number\n"

        return [TextContent(type="text", text=output)]

    async def _handle_update(
        self, action: str, _arguments: Dict[str, Any]
    ) -> List[TextContent]:
        """Handle system update operations."""
        if action != "run":
            return self.format_error(f"Invalid action: {action}. Must be 'run'")

        try:
            result = self.container.update_system_use_case.execute()

            if result.success:
                return self.format_success(
                    f"System packages updated successfully\n\n{result.stdout}"
                )
            else:
                return self.format_error(
                    f"Update failed: {result.stderr or result.stdout}"
                )
        except Exception as e:
            return self.format_error(f"Update failed: {e!s}")

    def _execute_command(self, command: str) -> tuple[int, str, str]:
        """Execute command via container and return tuple for compatibility."""
        result = self.container.retropie_client.execute_command(command)
        return result.exit_code, result.stdout, result.stderr

    def _check_port(self, port: int) -> bool:
        """Check if a port is open on the remote system."""
        try:
            result = self.container.retropie_client.execute_command(
                f"netstat -tuln | grep ':{port} '"
            )
            return result.success and result.stdout.strip() != ""
        except Exception:
            return False
