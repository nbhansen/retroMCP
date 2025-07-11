"""RetroPie-specific setup and configuration tools."""

from typing import Any
from typing import Dict
from typing import List

from mcp.types import EmbeddedResource
from mcp.types import ImageContent
from mcp.types import TextContent
from mcp.types import Tool

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

    async def _run_retropie_setup(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Run RetroPie-Setup script."""
        action = arguments.get("action")
        package = arguments.get("package")

        if action == "update":
            success, message = self.ssh.run_retropie_setup()
            if success:
                return self.format_success(message)
            else:
                return self.format_error(message)

        elif action in ["install", "remove", "configure"]:
            if not package:
                return self.format_error(f"Package name required for {action} action")

            # Run specific package action
            success, message = self.ssh.run_retropie_setup(f"{action} {package}")
            if success:
                return self.format_success(
                    f"{action.capitalize()}ed {package} successfully"
                )
            else:
                return self.format_error(f"Failed to {action} {package}: {message}")

        else:
            return self.format_error(f"Unknown action: {action}")

    async def _install_emulator(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Install a specific emulator."""
        emulator = arguments.get("emulator")
        arguments.get("install_type", "binary")

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

        success, message = self.ssh.setup_emulator("retropie", package_name)

        if success:
            return self.format_success(f"Successfully installed {emulator} emulator")
        else:
            return self.format_error(f"Failed to install {emulator}: {message}")

    async def _manage_roms(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Manage ROM files."""
        action = arguments.get("action")
        system = arguments.get("system")

        if action == "list":
            # List ROM directories
            rom_path = self.config.roms_dir or f"{self.config.home_dir}/RetroPie/roms"
            if system:
                rom_path += f"/{system}"

            exit_code, output, _ = self.ssh.execute_command(
                f"find {rom_path} -type f -name '*.zip' -o -name '*.rom' -o -name '*.iso' -o -name '*.bin' | head -20"
            )

            if exit_code == 0:
                if output:
                    return [
                        TextContent(type="text", text=f"📁 ROM Files:\\n\\n{output}")
                    ]
                else:
                    return self.format_info("No ROM files found")
            else:
                return self.format_error("Failed to list ROM files")

        elif action == "scan":
            # Scan for new ROMs and update game lists
            # Use the same logic as EmulationStation restart
            service_check_code, service_output, _ = self.ssh.execute_command(
                "systemctl is-active emulationstation 2>/dev/null"
            )

            if service_check_code == 0 and "active" in service_output:
                exit_code, _, _ = self.ssh.execute_command(
                    "sudo systemctl restart emulationstation"
                )
            else:
                # Restart as user process
                self.ssh.execute_command("pkill -f emulationstation")
                self.ssh.execute_command("sleep 2")
                exit_code, _, _ = self.ssh.execute_command(
                    "nohup emulationstation > /dev/null 2>&1 &",
                    timeout=5
                )

            if exit_code == 0:
                return self.format_success(
                    "EmulationStation restarted to scan for new ROMs"
                )
            else:
                return self.format_error("Failed to restart EmulationStation")

        elif action == "permissions":
            # Fix ROM file permissions
            exit_code, _, stderr = self.ssh.execute_command(
                f"sudo chown -R {self.config.username}:{self.config.username} {self.config.roms_dir or f'{self.config.home_dir}/RetroPie/roms'} && sudo chmod -R 755 {self.config.roms_dir or f'{self.config.home_dir}/RetroPie/roms'}"
            )

            if exit_code == 0:
                return self.format_success("ROM file permissions fixed")
            else:
                return self.format_error(f"Failed to fix permissions: {stderr}")

        else:
            return self.format_error(f"Unknown ROM action: {action}")

    async def _configure_overclock(
        self, arguments: Dict[str, Any]
    ) -> List[TextContent]:
        """Configure overclocking settings."""
        preset = arguments.get("preset")

        # Overclocking presets for different Pi models
        presets = {
            "none": {"arm_freq": 700, "gpu_freq": 250},
            "modest": {"arm_freq": 800, "gpu_freq": 250},
            "medium": {"arm_freq": 900, "gpu_freq": 250},
            "high": {"arm_freq": 950, "gpu_freq": 250},
            "turbo": {"arm_freq": 1000, "gpu_freq": 500},
        }

        if preset == "custom":
            arm_freq = arguments.get("arm_freq")
            gpu_freq = arguments.get("gpu_freq")
            if not arm_freq or not gpu_freq:
                return self.format_error("Custom preset requires arm_freq and gpu_freq")
            settings = {"arm_freq": arm_freq, "gpu_freq": gpu_freq}
        elif preset in presets:
            settings = presets[preset]
        else:
            return self.format_error(f"Unknown preset: {preset}")

        # Update config.txt
        commands = []
        for key, value in settings.items():
            commands.append(
                f"sudo sed -i 's/^{key}=.*/{key}={value}/' /boot/config.txt || echo '{key}={value}' | sudo tee -a /boot/config.txt"
            )

        for cmd in commands:
            exit_code, _, stderr = self.ssh.execute_command(cmd)
            if exit_code != 0:
                return self.format_error(f"Failed to update config: {stderr}")

        return self.format_success(
            f"Overclocking configured to {preset} preset. Reboot required for changes to take effect."
        )

    async def _configure_audio(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Configure audio settings."""
        output = arguments.get("output")
        volume = arguments.get("volume")

        commands = []

        if output:
            # Configure audio output
            audio_map = {"auto": 0, "headphone": 1, "hdmi": 2, "both": 3}

            if output in audio_map:
                commands.append(f"sudo amixer cset numid=3 {audio_map[output]}")
            else:
                return self.format_error(f"Unknown audio output: {output}")

        if volume is not None:
            # Set volume
            commands.append(f"sudo amixer set PCM -- {volume}%")

        success_messages = []
        for cmd in commands:
            exit_code, output_text, stderr = self.ssh.execute_command(cmd)
            if exit_code == 0:
                success_messages.append(f"✅ {cmd}")
            else:
                return self.format_error(f"Audio configuration failed: {stderr}")

        return self.format_success(
            "Audio configured successfully:\\n" + "\\n".join(success_messages)
        )
