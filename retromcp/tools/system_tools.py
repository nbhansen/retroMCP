"""System-level tools for RetroPie management."""

from typing import TYPE_CHECKING
from typing import Any
from typing import Dict
from typing import List

from mcp.types import EmbeddedResource
from mcp.types import ImageContent
from mcp.types import TextContent
from mcp.types import Tool

from .base import BaseTool

if TYPE_CHECKING:
    from ..domain.models import BiosFile
    from ..domain.models import CommandResult
    from ..domain.models import ConnectionInfo
    from ..domain.models import SystemInfo


class SystemTools(BaseTool):
    """Tools for system-level operations."""

    def get_tools(self) -> List[Tool]:
        """Return list of available system tools.

        Returns:
            List of Tool objects for system operations.
        """
        return [
            Tool(
                name="test_connection",
                description="Test SSH connection to RetroPie",
                inputSchema={"type": "object", "properties": {}, "required": []},
            ),
            Tool(
                name="system_info",
                description="Get detailed system information from RetroPie",
                inputSchema={"type": "object", "properties": {}, "required": []},
            ),
            Tool(
                name="install_packages",
                description="Install packages on RetroPie using apt-get",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "packages": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of package names to install",
                        }
                    },
                    "required": ["packages"],
                },
            ),
            Tool(
                name="check_bios",
                description="Check if required BIOS files are present for a system",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "system": {
                            "type": "string",
                            "enum": ["psx", "dreamcast", "neogeo", "segacd"],
                            "description": "System to check BIOS files for",
                        }
                    },
                    "required": ["system"],
                },
            ),
            Tool(
                name="update_system",
                description="Update RetroPie system packages",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "update_type": {
                            "type": "string",
                            "enum": ["basic", "full", "retropie-setup"],
                            "description": "Type of update to perform",
                            "default": "basic",
                        }
                    },
                    "required": [],
                },
            ),
        ]

    async def handle_tool_call(
        self, name: str, arguments: Dict[str, Any]
    ) -> List[TextContent | ImageContent | EmbeddedResource]:
        """Handle tool calls for system operations.

        Args:
            name: Name of the tool to call.
            arguments: Arguments for the tool.

        Returns:
            List of content objects with the tool's response.
        """
        try:
            if name == "test_connection":
                return await self._test_connection()
            elif name == "system_info":
                return await self._get_system_info()
            elif name == "install_packages":
                return await self._install_packages(arguments)
            elif name == "check_bios":
                return await self._check_bios(arguments)
            elif name == "update_system":
                return await self._update_system(arguments)
            else:
                return self.format_error(f"Unknown tool: {name}")
        except Exception as e:
            return self.format_error(f"Error in {name}: {e!s}")

    async def _test_connection(self) -> List[TextContent]:
        """Test SSH connection."""
        try:
            connection_info: ConnectionInfo = (
                self.container.test_connection_use_case.execute()
            )

            if connection_info.connected:
                return self.format_success(
                    f"Successfully connected to RetroPie!\\n\\n"
                    f"Host: {connection_info.host}:{connection_info.port}\\n"
                    f"Username: {connection_info.username}\\n"
                    f"Method: {connection_info.connection_method}\\n"
                    f"Last connected: {connection_info.last_connected or 'Just now'}"
                )
            else:
                return self.format_error("Connected but couldn't get system info")
        except Exception as e:
            return self.format_error(
                f"Connection failed: {e!s}\\n\\nPlease check your .env configuration:\\n- RETROPIE_HOST\\n- RETROPIE_USERNAME\\n- RETROPIE_PASSWORD or RETROPIE_SSH_KEY_PATH"
            )

    async def _get_system_info(self) -> List[TextContent]:
        """Get system information."""
        system_info: SystemInfo = self.container.get_system_info_use_case.execute()

        output = "🖥️ RetroPie System Information:\\n\\n"

        # Temperature
        temp = system_info.cpu_temperature
        temp_status = "🔥" if temp > 80 else "⚠️" if temp > 70 else "✅"
        output += f"Temperature: {temp_status} {temp}°C\\n"

        # Memory
        memory_total_mb = system_info.memory_total // (1024 * 1024)
        memory_used_mb = system_info.memory_used // (1024 * 1024)
        if system_info.memory_total > 0:
            used_pct = (system_info.memory_used / system_info.memory_total) * 100
            mem_status = "🔴" if used_pct > 90 else "🟡" if used_pct > 75 else "🟢"
            output += f"Memory: {mem_status} {memory_used_mb}MB / {memory_total_mb}MB ({used_pct:.1f}%)\\n"
        else:
            output += f"Memory: ⚠️ {memory_used_mb}MB / {memory_total_mb}MB (Unable to determine usage)\\n"

        # Disk
        disk_total_gb = system_info.disk_total // (1024 * 1024 * 1024)
        disk_used_gb = system_info.disk_used // (1024 * 1024 * 1024)
        if system_info.disk_total > 0:
            disk_used_pct = (system_info.disk_used / system_info.disk_total) * 100
            output += f"Disk Usage: {disk_used_gb}GB / {disk_total_gb}GB ({disk_used_pct:.1f}%)\\n"
        else:
            output += f"Disk Usage: {disk_used_gb}GB / {disk_total_gb}GB (Unable to determine usage)\\n"

        # Load average
        if system_info.load_average:
            load_1min = (
                system_info.load_average[0] if len(system_info.load_average) > 0 else 0
            )
            output += f"Load Average (1min): {load_1min:.2f}\\n"

        # Uptime
        uptime_hours = system_info.uptime // 3600
        uptime_minutes = (system_info.uptime % 3600) // 60
        output += f"Uptime: {uptime_hours}h {uptime_minutes}m\\n"

        # Hostname
        output += f"Hostname: {system_info.hostname}\\n"

        return [TextContent(type="text", text=output)]

    async def _install_packages(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Install packages."""
        packages = arguments.get("packages", [])

        if not packages:
            return self.format_error("No packages specified")

        result: CommandResult = self.container.install_packages_use_case.execute(
            packages
        )

        if result.success:
            return self.format_success(
                result.stdout
                or f"Successfully installed packages: {', '.join(packages)}"
            )
        else:
            return self.format_error(
                f"Package installation failed: {result.stderr or result.stdout}"
            )

    async def _check_bios(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Check BIOS files."""
        system = arguments.get("system")

        if not system:
            return self.format_error("No system specified")

        # Get all BIOS files and filter by system
        all_bios_files: List[BiosFile] = (
            self.container.system_repository.get_bios_files()
        )
        system_bios_files = [
            bf for bf in all_bios_files if bf.system.lower() == system.lower()
        ]

        output = f"🎮 BIOS Files for {system.upper()}:\\n\\n"

        if not system_bios_files:
            output += "✅ No BIOS files required for this system\\n"
        else:
            required_files = [bf for bf in system_bios_files if bf.required]

            if not required_files:
                output += "✅ No BIOS files required for this system\\n"
            else:
                output += "Required BIOS files:\\n"
                all_present = True

                for bios_file in required_files:
                    status = "✅" if bios_file.present else "❌"
                    output += f"  {status} {bios_file.name}\\n"
                    if not bios_file.present:
                        all_present = False

                if all_present:
                    output += "\\n🎉 All required BIOS files are present!\\n"
                else:
                    bios_dir = (
                        self.config.bios_dir or f"{self.config.home_dir}/RetroPie/BIOS"
                    )
                    output += f"\\n⚠️ Some BIOS files are missing. Place them in {bios_dir}/\\n"

        return [TextContent(type="text", text=output)]

    async def _update_system(self, arguments: Dict[str, Any]) -> List[TextContent]:  # noqa: ARG002
        """Update system packages."""
        result: CommandResult = self.container.update_system_use_case.execute()

        if result.success:
            return self.format_success(
                f"System packages updated successfully\n\n{result.stdout}"
            )
        else:
            return self.format_error(f"Update failed: {result.stderr or result.stdout}")
