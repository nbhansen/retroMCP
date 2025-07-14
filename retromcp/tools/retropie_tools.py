"""RetroPie-specific setup and configuration tools."""

from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from mcp.types import EmbeddedResource
from mcp.types import ImageContent
from mcp.types import TextContent
from mcp.types import Tool

from ..domain.models import CommandResult
from .base import BaseTool


class RetroPieTools(BaseTool):
    """Tools for RetroPie-specific operations."""

    def get_tools(self) -> List[Tool]:
        """Return list of available RetroPie tools.

        Returns:
            List of Tool objects for RetroPie operations.
        """
        return [
            Tool(
                name="run_retropie_setup",
                description="Run RetroPie-Setup script for package management",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["update", "install", "remove", "configure"],
                            "description": "Action to perform",
                        },
                        "package": {
                            "type": "string",
                            "description": "Package name (for install/remove/configure actions)",
                        },
                    },
                    "required": ["action"],
                },
            ),
            Tool(
                name="install_emulator",
                description="Install a specific emulator via RetroPie-Setup",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "emulator": {
                            "type": "string",
                            "description": "Emulator name (e.g., mupen64plus, pcsx-rearmed)",
                            "examples": [
                                "mupen64plus",
                                "pcsx-rearmed",
                                "dolphin",
                                "ppsspp",
                            ],
                        },
                        "install_type": {
                            "type": "string",
                            "enum": ["binary", "source"],
                            "description": "Installation method",
                            "default": "binary",
                        },
                    },
                    "required": ["emulator"],
                },
            ),
            Tool(
                name="manage_roms",
                description="Manage ROM files and directories",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["list", "scan", "permissions"],
                            "description": "ROM management action",
                        },
                        "system": {
                            "type": "string",
                            "description": "System name (optional, for system-specific actions)",
                        },
                    },
                    "required": ["action"],
                },
            ),
            Tool(
                name="configure_overclock",
                description="Configure Raspberry Pi overclocking settings",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "preset": {
                            "type": "string",
                            "enum": [
                                "none",
                                "modest",
                                "medium",
                                "high",
                                "turbo",
                                "custom",
                            ],
                            "description": "Overclocking preset",
                        },
                        "arm_freq": {
                            "type": "integer",
                            "description": "ARM frequency (for custom preset)",
                        },
                        "gpu_freq": {
                            "type": "integer",
                            "description": "GPU frequency (for custom preset)",
                        },
                    },
                    "required": ["preset"],
                },
            ),
            Tool(
                name="configure_audio",
                description="Configure audio output settings",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "output": {
                            "type": "string",
                            "enum": ["auto", "hdmi", "headphone", "both"],
                            "description": "Audio output device",
                        },
                        "volume": {
                            "type": "integer",
                            "minimum": 0,
                            "maximum": 100,
                            "description": "Audio volume percentage",
                        },
                    },
                    "required": [],
                },
            ),
        ]

    async def handle_tool_call(
        self, name: str, arguments: Dict[str, Any]
    ) -> List[TextContent | ImageContent | EmbeddedResource]:
        """Handle tool calls for RetroPie operations.

        Args:
            name: Name of the tool to call.
            arguments: Arguments for the tool.

        Returns:
            List of content objects with the tool's response.
        """
        try:
            if name == "run_retropie_setup":
                return await self._run_retropie_setup(arguments)
            elif name == "install_emulator":
                return await self._install_emulator(arguments)
            elif name == "manage_roms":
                return await self._manage_roms(arguments)
            elif name == "configure_overclock":
                return await self._configure_overclock(arguments)
            elif name == "configure_audio":
                return await self._configure_audio(arguments)
            else:
                return self.format_error(f"Unknown tool: {name}")
        except Exception as e:
            return self.format_error(f"Error in {name}: {e!s}")

    def _format_command_result(
        self,
        result: CommandResult,
        success_message: Optional[str] = None,
        error_prefix: Optional[str] = None,
    ) -> List[TextContent]:
        """Format a CommandResult domain object as MCP TextContent.

        Args:
            result: Domain CommandResult object
            success_message: Custom success message (uses result.stdout if None)
            error_prefix: Prefix for error messages (uses result.stderr if None)

        Returns:
            List of TextContent for MCP response
        """
        if result.success:
            message = success_message or result.stdout
            return self.format_success(message)
        else:
            if error_prefix:
                error_msg = (
                    f"{error_prefix}: {result.stderr}"
                    if result.stderr
                    else error_prefix
                )
            else:
                error_msg = result.stderr or "Command failed"
            return self.format_error(error_msg)

    async def _run_retropie_setup(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Run RetroPie-Setup script."""
        action = arguments.get("action")
        package = arguments.get("package")

        if action == "update":
            # Use domain use case for system updates
            result = self.container.update_system_use_case.execute()
            return self._format_command_result(
                result, success_message="RetroPie system updated successfully"
            )

        elif action in ["install", "remove", "configure"]:
            if not package:
                return self.format_error(f"Package name required for {action} action")

            # TODO: Implement RunRetroPieSetupUseCase for package management
            # For now, return an error indicating missing use case
            return self.format_error(
                f"RetroPie package {action} not yet implemented. "
                f"Missing RunRetroPieSetupUseCase for: {action} {package}"
            )

        else:
            return self.format_error(f"Unknown action: {action}")

    async def _install_emulator(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Install a specific emulator."""
        emulator = arguments.get("emulator")
        arguments.get(
            "install_type", "binary"
        )  # TODO: Support install_type in use case

        if not emulator:
            return self.format_error("No emulator specified")

        # Map common emulator names to RetroPie package names
        emulator_map = {
            "mupen64plus": "mupen64plus",
            "n64": "mupen64plus",
            "psx": "pcsx-rearmed",
            "playstation": "pcsx-rearmed",
            "dreamcast": "reicast",
            "psp": "ppsspp",
            "gamecube": "dolphin",
            "wii": "dolphin",
        }

        package_name = emulator_map.get(emulator.lower(), emulator)

        # Use domain use case instead of direct SSH
        result = self.container.install_emulator_use_case.execute(package_name)

        return self._format_command_result(
            result,
            success_message=f"Successfully installed {emulator} emulator",
            error_prefix=f"Failed to install {emulator}",
        )

    async def _manage_roms(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Manage ROM files.

        TODO: Replace with domain use cases:
        - ✅ ListRomsUseCase: IMPLEMENTED for listing ROM files by system
        - ScanRomsUseCase: for EmulationStation ROM scanning
        - FixRomPermissionsUseCase: for fixing ROM file permissions
        """
        action = arguments.get("action")
        system = arguments.get("system")  # Now used by ListRomsUseCase

        if action == "list":
            # Use ListRomsUseCase for ROM directory listing
            rom_directories = self.container.list_roms_use_case.execute(
                system_filter=system,
                min_rom_count=0,  # Show all directories, even empty ones
            )

            # Format the output nicely
            output = "📁 **ROM Directory Listing**\\n\\n"

            if not rom_directories:
                if system:
                    output += f"No ROM directories found for system: {system}\\n"
                else:
                    output += "No ROM directories found.\\n"
                output += "\\nConsider adding ROMs to ~/RetroPie/roms/ directories.\\n"
            else:
                total_roms = sum(rom_dir.rom_count for rom_dir in rom_directories)
                total_size = sum(rom_dir.total_size for rom_dir in rom_directories)

                output += f"**Summary:** {len(rom_directories)} systems, {total_roms} ROMs total, {total_size / 1024 / 1024:.1f} MB\\n\\n"

                for rom_dir in rom_directories:
                    # Add system icon
                    icon = "🎮"
                    if (
                        "nintendo" in rom_dir.system.lower()
                        or "nes" in rom_dir.system.lower()
                    ):
                        icon = "🟥"
                    elif (
                        "playstation" in rom_dir.system.lower()
                        or "psx" in rom_dir.system.lower()
                    ) or "sega" in rom_dir.system.lower():
                        icon = "🔵"
                    elif (
                        "arcade" in rom_dir.system.lower()
                        or "mame" in rom_dir.system.lower()
                    ):
                        icon = "🕹️"

                    output += f"  {icon} **{rom_dir.system.upper()}**\\n"
                    output += f"    • Path: {rom_dir.path}\\n"
                    output += f"    • ROMs: {rom_dir.rom_count}\\n"
                    output += (
                        f"    • Size: {rom_dir.total_size / 1024 / 1024:.1f} MB\\n"
                    )
                    if rom_dir.supported_extensions:
                        extensions = ", ".join(
                            rom_dir.supported_extensions[:5]
                        )  # Show first 5
                        if len(rom_dir.supported_extensions) > 5:
                            extensions += "..."
                        output += f"    • Formats: {extensions}\\n"
                    output += "\\n"

            return [TextContent(type="text", text=output)]

        elif action == "scan":
            # TODO: Replace with ScanRomsUseCase
            return self.format_error(
                "ROM scanning not yet implemented. "
                "Missing ScanRomsUseCase for EmulationStation restart and ROM scanning."
            )

        elif action == "permissions":
            # TODO: Replace with FixRomPermissionsUseCase
            return self.format_error(
                "ROM permissions fix not yet implemented. "
                "Missing FixRomPermissionsUseCase for fixing ROM file ownership and permissions."
            )

        else:
            return self.format_error(f"Unknown ROM action: {action}")

    async def _configure_overclock(
        self, arguments: Dict[str, Any]
    ) -> List[TextContent]:
        """Configure overclocking settings.

        TODO: Replace with domain use case:
        - ConfigureOverclockUseCase: for /boot/config.txt management
        """
        preset = arguments.get("preset")

        # TODO: Replace with ConfigureOverclockUseCase
        return self.format_error(
            f"Overclocking configuration not yet implemented. "
            f"Missing ConfigureOverclockUseCase for managing /boot/config.txt overclocking settings. "
            f"Requested preset: {preset}"
        )

    async def _configure_audio(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Configure audio settings.

        TODO: Replace with domain use case:
        - ConfigureAudioUseCase: for amixer audio configuration
        """
        output = arguments.get("output")
        volume = arguments.get("volume")

        # TODO: Replace with ConfigureAudioUseCase
        config_details = []
        if output:
            config_details.append(f"output={output}")
        if volume is not None:
            config_details.append(f"volume={volume}")

        config_str = ", ".join(config_details) if config_details else "no parameters"

        return self.format_error(
            f"Audio configuration not yet implemented. "
            f"Missing ConfigureAudioUseCase for amixer audio management. "
            f"Requested configuration: {config_str}"
        )
