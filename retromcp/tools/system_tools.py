"""System-level tools for RetroPie management."""

from typing import Any
from typing import Dict
from typing import List

from mcp.types import EmbeddedResource
from mcp.types import ImageContent
from mcp.types import TextContent
from mcp.types import Tool

from .base import BaseTool


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
            exit_code, output, _ = self.ssh.execute_command("uname -a")

            if exit_code == 0:
                return self.format_success(
                    f"Successfully connected to RetroPie!\\n\\nSystem info:\\n{output}"
                )
            else:
                return self.format_error("Connected but couldn't get system info")
        except Exception as e:
            return self.format_error(
                f"Connection failed: {e!s}\\n\\nPlease check your .env configuration:\\n- RETROPIE_HOST\\n- RETROPIE_USERNAME\\n- RETROPIE_PASSWORD or RETROPIE_SSH_KEY_PATH"
            )

    async def _get_system_info(self) -> List[TextContent]:
        """Get system information."""
        info = self.ssh.get_system_info()

        output = "🖥️ RetroPie System Information:\\n\\n"

        if "temperature" in info:
            temp = info["temperature"]
            temp_status = "🔥" if temp > 80 else "⚠️" if temp > 70 else "✅"
            output += f"Temperature: {temp_status} {temp}°C\\n"

        if "memory" in info:
            mem = info["memory"]
            used_pct = (mem["used"] / mem["total"]) * 100
            mem_status = "🔴" if used_pct > 90 else "🟡" if used_pct > 75 else "🟢"
            output += f"Memory: {mem_status} {mem['used']}MB / {mem['total']}MB ({used_pct:.1f}%)\\n"

        if "disk" in info:
            disk = info["disk"]
            output += f"Disk Usage: {disk['used']} / {disk['total']} ({disk['use_percent']})\\n"

        if "emulationstation_running" in info:
            es_status = (
                "✅ Running" if info["emulationstation_running"] else "❌ Not running"
            )
            output += f"EmulationStation: {es_status}\\n"

        return [TextContent(type="text", text=output)]

    async def _install_packages(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Install packages."""
        packages = arguments.get("packages", [])

        if not packages:
            return self.format_error("No packages specified")

        success, message = self.ssh.install_packages(packages)

        if success:
            return self.format_success(message)
        else:
            return self.format_error(message)

    async def _check_bios(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Check BIOS files."""
        system = arguments.get("system")

        if not system:
            return self.format_error("No system specified")

        bios_info = self.ssh.check_bios_files(system)

        output = f"🎮 BIOS Files for {system.upper()}:\\n\\n"

        if not bios_info["bios_required"]:
            output += "✅ No BIOS files required for this system\\n"
        else:
            output += "Required BIOS files:\\n"
            for filename, present in bios_info["files"].items():
                status = "✅" if present else "❌"
                output += f"  {status} {filename}\\n"

            if bios_info["all_present"]:
                output += "\\n🎉 All required BIOS files are present!\\n"
            else:
                output += "\\n⚠️ Some BIOS files are missing. Place them in /home/pi/RetroPie/BIOS/\\n"

        return [TextContent(type="text", text=output)]

    async def _update_system(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Update system packages."""
        update_type = arguments.get("update_type", "basic")

        if update_type == "basic":
            # Update package lists and upgrade system packages
            exit_code, stdout, stderr = self.ssh.execute_command(
                "sudo apt-get update && sudo apt-get upgrade -y"
            )
            if exit_code == 0:
                return self.format_success("System packages updated successfully")
            else:
                return self.format_error(f"Update failed: {stderr}")

        elif update_type == "retropie-setup":
            # Run RetroPie-Setup update
            success, message = self.ssh.run_retropie_setup("update")
            if success:
                return self.format_success(message)
            else:
                return self.format_error(message)

        else:
            return self.format_error(f"Unknown update type: {update_type}")
