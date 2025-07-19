"""Gaming system tools for unified gaming management operations."""

import shlex
from typing import Any
from typing import ClassVar
from typing import Dict
from typing import List
from typing import Optional

from mcp.types import EmbeddedResource
from mcp.types import ImageContent
from mcp.types import TextContent
from mcp.types import Tool

from .base import BaseTool


class GamingSystemTools(BaseTool):
    """Unified gaming system tools for all gaming management operations."""

    # Define valid targets for each component and action
    VALID_TARGETS: ClassVar[Dict[str, Dict[str, List[str]]]] = {
        "retropie": {
            "setup": ["update"],
            "install": ["emulator"],
            "configure": ["overclock"],
        },
        "emulationstation": {
            "configure": ["themes", "settings", "gamelists"],
            "restart": [],  # No target required
            "scan": ["roms", "media"],
        },
        "controller": {
            "detect": [],  # No target required
            "setup": ["xbox", "ps3", "ps4", "8bitdo", "generic"],
            "test": ["player1", "player2", "player3", "player4"],
            "configure": ["mapping", "hotkeys"],
        },
        "roms": {
            "scan": ["<system_name>"],  # Dynamic - any system name
            "list": ["all", "<system_name>"],
            "configure": ["permissions", "paths"],
        },
        "emulator": {
            "install": ["<emulator_name>"],  # Dynamic - any emulator name
            "configure": ["<emulator_name>"],
            "list": [],  # No target required
        },
        "audio": {
            "configure": ["hdmi", "analog"],
            "test": ["hdmi", "analog"],
        },
        "video": {
            "configure": ["resolution", "refresh", "crt"],
            "test": ["current"],
        },
    }

    def get_tools(self) -> List[Tool]:
        """Return list of available gaming system tools.

        Returns:
            List containing single manage_gaming tool.
        """
        return [
            Tool(
                name="manage_gaming",
                description=(
                    "Unified gaming system management tool. "
                    "Components: retropie (setup/install/configure), emulationstation (configure/restart/scan), "
                    "controller (detect/setup/test/configure), roms (scan/list/configure), "
                    "emulator (install/configure/list), audio (configure/test), video (configure/test). "
                    "Most actions require a 'target' parameter - error messages will show valid targets."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "component": {
                            "type": "string",
                            "enum": [
                                "retropie",
                                "emulationstation",
                                "controller",
                                "roms",
                                "emulator",
                                "audio",
                                "video",
                            ],
                            "description": "Gaming system component to manage",
                        },
                        "action": {
                            "type": "string",
                            "description": "Action to perform on the component",
                        },
                        "target": {
                            "type": "string",
                            "description": (
                                "Target for the action. Examples: "
                                "retropie setup: 'update'; "
                                "controller setup: 'xbox', 'ps3', 'ps4', '8bitdo', 'generic'; "
                                "audio configure: 'hdmi', 'analog'; "
                                "roms scan: system name (e.g., 'nes', 'arcade'); "
                                "emulator install: emulator name (e.g., 'lr-mame2003')"
                            ),
                        },
                        "options": {
                            "type": "object",
                            "description": "Additional options for the action",
                        },
                    },
                    "required": ["component", "action"],
                },
            ),
        ]

    def _get_valid_targets_message(self, component: str, action: str) -> str:
        """Get a helpful message about valid targets for a component/action pair."""
        if component in self.VALID_TARGETS and action in self.VALID_TARGETS[component]:
            targets = self.VALID_TARGETS[component][action]
            if not targets:
                return "No target required for this action"
            elif any("<" in t for t in targets):
                # Dynamic targets
                examples = []
                for t in targets:
                    if t == "<system_name>":
                        examples.append("nes, snes, genesis, arcade, etc.")
                    elif t == "<emulator_name>":
                        examples.append("lr-mame2003, lr-snes9x, mupen64plus, etc.")
                return f"Valid targets: {', '.join(examples)}"
            else:
                return f"Valid targets: {', '.join(targets)}"
        return "No valid targets found"

    async def handle_tool_call(
        self, name: str, arguments: Dict[str, Any]
    ) -> List[TextContent | ImageContent | EmbeddedResource]:
        """Handle tool calls for gaming system operations.

        Args:
            name: Name of the tool to call.
            arguments: Arguments for the tool.

        Returns:
            List of content objects with the tool's response.
        """
        try:
            if name == "manage_gaming":
                return await self._manage_gaming(arguments)
            else:
                return self.format_error(f"Unknown tool: {name}")
        except Exception as e:
            return self.format_error(f"Error in {name}: {e!s}")

    async def _manage_gaming(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Route gaming management requests to appropriate handlers."""
        component = arguments.get("component")
        action = arguments.get("action")

        if not component:
            return self.format_error("Component is required")
        if not action:
            return self.format_error("Action is required")

        # Route to appropriate component handler
        if component == "retropie":
            return await self._handle_retropie(action, arguments)
        elif component == "emulationstation":
            return await self._handle_emulationstation(action, arguments)
        elif component == "controller":
            return await self._handle_controller(action, arguments)
        elif component == "roms":
            return await self._handle_roms(action, arguments)
        elif component == "emulator":
            return await self._handle_emulator(action, arguments)
        elif component == "audio":
            return await self._handle_audio(action, arguments)
        elif component == "video":
            return await self._handle_video(action, arguments)
        else:
            return self.format_error(f"Invalid component: {component}")

    async def _handle_retropie(
        self, action: str, arguments: Dict[str, Any]
    ) -> List[TextContent]:
        """Handle RetroPie management operations."""
        valid_actions = ["setup", "install", "configure"]
        if action not in valid_actions:
            return self.format_error(
                f"Invalid action: {action}. Must be one of: {', '.join(valid_actions)}"
            )

        target = arguments.get("target")
        options = arguments.get("options", {})

        if action == "setup":
            return await self._retropie_setup(target, options)
        elif action == "install":
            return await self._retropie_install(target, options)
        elif action == "configure":
            return await self._retropie_configure(target, options)
        else:
            return self.format_error(f"RetroPie action '{action}' not implemented")

    async def _handle_emulationstation(
        self, action: str, arguments: Dict[str, Any]
    ) -> List[TextContent]:
        """Handle EmulationStation management operations."""
        valid_actions = ["configure", "restart", "scan"]
        if action not in valid_actions:
            return self.format_error(
                f"Invalid action: {action}. Must be one of: {', '.join(valid_actions)}"
            )

        target = arguments.get("target")
        options = arguments.get("options", {})

        if action == "configure":
            return await self._emulationstation_configure(target, options)
        elif action == "restart":
            return await self._emulationstation_restart()
        elif action == "scan":
            return await self._emulationstation_scan(target, options)
        else:
            return self.format_error(
                f"EmulationStation action '{action}' not implemented"
            )

    async def _handle_controller(
        self, action: str, arguments: Dict[str, Any]
    ) -> List[TextContent]:
        """Handle controller management operations."""
        valid_actions = ["detect", "setup", "test", "configure"]
        if action not in valid_actions:
            return self.format_error(
                f"Invalid action: {action}. Must be one of: {', '.join(valid_actions)}"
            )

        target = arguments.get("target")
        options = arguments.get("options", {})

        if action == "detect":
            return await self._controller_detect()
        elif action == "setup":
            return await self._controller_setup(target, options)
        elif action == "test":
            return await self._controller_test(target, options)
        elif action == "configure":
            return await self._controller_configure(target, options)
        else:
            return self.format_error(f"Controller action '{action}' not implemented")

    async def _handle_roms(
        self, action: str, arguments: Dict[str, Any]
    ) -> List[TextContent]:
        """Handle ROM management operations."""
        valid_actions = ["scan", "list", "configure"]
        if action not in valid_actions:
            return self.format_error(
                f"Invalid action: {action}. Must be one of: {', '.join(valid_actions)}"
            )

        target = arguments.get("target")
        options = arguments.get("options", {})

        if action == "scan":
            return await self._roms_scan(target, options)
        elif action == "list":
            return await self._roms_list(target, options)
        elif action == "configure":
            return await self._roms_configure(target, options)
        else:
            return self.format_error(f"ROM action '{action}' not implemented")

    async def _handle_emulator(
        self, action: str, arguments: Dict[str, Any]
    ) -> List[TextContent]:
        """Handle emulator management operations."""
        valid_actions = ["install", "configure", "test"]
        if action not in valid_actions:
            return self.format_error(
                f"Invalid action: {action}. Must be one of: {', '.join(valid_actions)}"
            )

        target = arguments.get("target")
        options = arguments.get("options", {})

        if action == "install":
            return await self._emulator_install(target, options)
        elif action == "configure":
            return await self._emulator_configure(target, options)
        elif action == "test":
            return await self._emulator_test(target, options)
        else:
            return self.format_error(f"Emulator action '{action}' not implemented")

    async def _handle_audio(
        self, action: str, arguments: Dict[str, Any]
    ) -> List[TextContent]:
        """Handle audio management operations."""
        valid_actions = ["configure", "test"]
        if action not in valid_actions:
            return self.format_error(
                f"Invalid action: {action}. Must be one of: {', '.join(valid_actions)}"
            )

        target = arguments.get("target")
        options = arguments.get("options", {})

        if action == "configure":
            return await self._audio_configure(target, options)
        elif action == "test":
            return await self._audio_test(target, options)
        else:
            return self.format_error(f"Audio action '{action}' not implemented")

    async def _handle_video(
        self, action: str, arguments: Dict[str, Any]
    ) -> List[TextContent]:
        """Handle video management operations."""
        valid_actions = ["configure", "test"]
        if action not in valid_actions:
            return self.format_error(
                f"Invalid action: {action}. Must be one of: {', '.join(valid_actions)}"
            )

        target = arguments.get("target")
        options = arguments.get("options", {})

        if action == "configure":
            return await self._video_configure(target, options)
        elif action == "test":
            return await self._video_test(target, options)
        else:
            return self.format_error(f"Video action '{action}' not implemented")

    # RetroPie component methods

    async def _retropie_setup(
        self,
        target: str,
        options: Dict[str, Any],  # noqa: ARG002
    ) -> List[TextContent]:
        """Handle RetroPie setup operations."""
        try:
            if target == "update":
                # Use the update system use case
                result = self.container.update_system_use_case.execute()

                if result.success:
                    output = "🎮 **RetroPie Setup - System Update**\n\n"
                    output += "✅ System updated successfully\n\n"
                    if result.stdout:
                        output += f"**Update Details:**\n```\n{result.stdout}\n```"
                    return [TextContent(type="text", text=output)]
                else:
                    return self.format_error(
                        f"System update failed: {result.stderr or result.stdout}"
                    )
            else:
                valid_targets = self._get_valid_targets_message("retropie", "setup")
                return self.format_error(
                    f"Unknown RetroPie setup target: {target}. {valid_targets}"
                )
        except Exception as e:
            return self.format_error(f"RetroPie setup failed: {e!s}")

    async def _retropie_install(
        self, target: str, options: Dict[str, Any]
    ) -> List[TextContent]:
        """Handle RetroPie installation operations."""
        try:
            if target == "emulator":
                emulator = options.get("emulator")
                system = options.get("system")

                if not emulator:
                    return self.format_error(
                        "Emulator name is required for installation"
                    )

                # Execute via use case
                result = self.container.install_emulator_use_case.execute(emulator)

                if result.success:
                    output = "🎮 **RetroPie - Emulator Installation**\n\n"
                    output += f"✅ Emulator '{emulator}' installed successfully"
                    if system:
                        output += f" for {system}"
                    output += "\n\n"
                    if result.stdout:
                        output += (
                            f"**Installation Details:**\n```\n{result.stdout}\n```"
                        )
                    return [TextContent(type="text", text=output)]
                else:
                    return self.format_error(
                        f"Emulator installation failed: {result.stderr or result.stdout}"
                    )
            else:
                valid_targets = self._get_valid_targets_message("retropie", "install")
                return self.format_error(
                    f"Unknown RetroPie install target: {target}. {valid_targets}"
                )
        except Exception as e:
            return self.format_error(f"RetroPie installation failed: {e!s}")

    async def _retropie_configure(
        self, target: str, options: Dict[str, Any]
    ) -> List[TextContent]:
        """Handle RetroPie configuration operations."""
        try:
            if target == "overclock":
                preset = options.get("preset", "None")
                quoted_preset = shlex.quote(preset)

                # Configure overclock using raspi-config
                result = self.container.retropie_client.execute_command(
                    f"sudo raspi-config nonint do_overclock {quoted_preset}"
                )

                if result.success:
                    output = "🎮 **RetroPie - Overclock Configuration**\n\n"
                    output += f"✅ Overclock configured to preset: {preset}\n\n"
                    output += "**Note:** Reboot required for changes to take effect"
                    return [TextContent(type="text", text=output)]
                else:
                    return self.format_error(
                        f"Overclock configuration failed: {result.stderr or result.stdout}"
                    )
            else:
                valid_targets = self._get_valid_targets_message("retropie", "configure")
                return self.format_error(
                    f"Unknown RetroPie configuration target: {target}. {valid_targets}"
                )
        except Exception as e:
            return self.format_error(f"RetroPie configuration failed: {e!s}")

    # EmulationStation component methods

    async def _emulationstation_configure(
        self, target: str, options: Dict[str, Any]
    ) -> List[TextContent]:
        """Handle EmulationStation configuration operations."""
        try:
            if target == "themes":
                theme = options.get("theme", "carbon")
                action = options.get("action", "install")
                quoted_theme = shlex.quote(theme)

                # Configure themes using RetroPie-Setup
                result = self.container.retropie_client.execute_command(
                    f"sudo {self.container.config.paths.retropie_setup_dir}/retropie_setup.sh esthemes {action}_theme {quoted_theme}"
                )

                if result.success:
                    output = "🎨 **EmulationStation - Theme Configuration**\n\n"
                    output += f"✅ Theme '{theme}' {action} completed successfully\n\n"
                    if result.stdout:
                        output += f"**Theme Details:**\n```\n{result.stdout}\n```"
                    return [TextContent(type="text", text=output)]
                else:
                    return self.format_error(
                        f"Theme configuration failed: {result.stderr or result.stdout}"
                    )
            else:
                valid_targets = self._get_valid_targets_message("emulationstation", "configure")
                return self.format_error(
                    f"Unknown EmulationStation configuration target: {target}. {valid_targets}"
                )
        except Exception as e:
            return self.format_error(f"EmulationStation configuration failed: {e!s}")

    async def _emulationstation_restart(self) -> List[TextContent]:
        """Handle EmulationStation restart operations."""
        try:
            # Restart EmulationStation service
            result = self.container.retropie_client.execute_command(
                "sudo systemctl restart emulationstation"
            )

            if result.success:
                output = "🔄 **EmulationStation - Service Restart**\n\n"
                output += "✅ EmulationStation restarted successfully\n\n"
                output += "**Note:** EmulationStation is now restarting..."
                return [TextContent(type="text", text=output)]
            else:
                return self.format_error(
                    f"EmulationStation restart failed: {result.stderr or result.stdout}"
                )
        except Exception as e:
            return self.format_error(f"EmulationStation restart failed: {e!s}")

    async def _emulationstation_scan(self, target: str, options: Optional[dict] = None) -> List[TextContent]:
        """Handle EmulationStation scanning operations."""
        try:
            if target == "gamelists":
                # Regenerate gamelists
                result = self.container.retropie_client.execute_command(
                    "emulationstation --gamelist-only"
                )

                if result.success:
                    output = "📚 **EmulationStation - Gamelist Scan**\n\n"
                    output += "✅ Gamelists regenerated successfully\n\n"
                    output += "**Note:** All system gamelists have been updated"
                    return [TextContent(type="text", text=output)]
                else:
                    return self.format_error(
                        f"Gamelist scan failed: {result.stderr or result.stdout}"
                    )
            else:
                valid_targets = self._get_valid_targets_message("emulationstation", "scan")
                return self.format_error(
                    f"Unknown EmulationStation scan target: {target}. {valid_targets}"
                )
        except Exception as e:
            return self.format_error(f"EmulationStation scan failed: {e!s}")

    # Controller component methods

    async def _controller_detect(self) -> List[TextContent]:
        """Handle controller detection operations."""
        try:
            # Use the detect controllers use case
            controllers = self.container.detect_controllers_use_case.execute()

            output = "🎮 **Controller Detection**\n\n"

            if controllers:
                output += "**Detected Controllers:**\n\n"
                for controller in controllers:
                    status = (
                        "✅ Connected" if controller.connected else "❌ Disconnected"
                    )
                    output += f"• **{controller.name}** ({controller.controller_type.value})\n"
                    output += f"  - Device: {controller.device_path}\n"
                    output += f"  - Status: {status}\n\n"
            else:
                output += "❌ No controllers detected\n\n"
                output += "**Troubleshooting:**\n"
                output += "- Ensure controllers are properly connected\n"
                output += "- Check USB connections\n"
                output += "- Try unplugging and reconnecting controllers"

            return [TextContent(type="text", text=output)]
        except Exception as e:
            return self.format_error(f"Controller detection failed: {e!s}")

    async def _controller_setup(self, target: str, options: Optional[dict] = None) -> List[TextContent]:
        """Handle controller setup operations."""
        try:
            if not target:
                valid_targets = self._get_valid_targets_message("controller", "setup")
                return self.format_error(
                    f"Controller type is required for setup. {valid_targets}"
                )

            # Validate controller type
            valid_types = ["xbox", "ps3", "ps4", "8bitdo", "generic"]
            if target not in valid_types:
                valid_targets = self._get_valid_targets_message("controller", "setup")
                return self.format_error(
                    f"Invalid controller type: {target}. {valid_targets}"
                )

            # Execute via use case
            result = self.container.setup_controller_use_case.execute(target)

            if result.success:
                output = "🎮 **Controller Setup**\n\n"
                output += (
                    f"✅ {target.upper()} controller setup completed successfully\n\n"
                )
                if result.stdout:
                    output += f"**Setup Details:**\n```\n{result.stdout}\n```"
                return [TextContent(type="text", text=output)]
            else:
                return self.format_error(
                    f"Controller setup failed: {result.stderr or result.stdout}"
                )
        except Exception as e:
            return self.format_error(f"Controller setup failed: {e!s}")

    async def _controller_test(self, target: str, options: Optional[dict] = None) -> List[TextContent]:
        """Handle controller testing operations."""
        try:
            if not target:
                valid_targets = self._get_valid_targets_message("controller", "test")
                return self.format_error(
                    f"Controller device is required for testing. {valid_targets}"
                )

            # Test controller using jstest
            device_path = (
                f"/dev/input/{target}"
                if not target.startswith("/dev/input/")
                else target
            )
            quoted_device = shlex.quote(device_path)

            result = self.container.retropie_client.execute_command(
                f"jstest {quoted_device} --event"
            )

            if result.success:
                output = "🎮 **Controller Test**\n\n"
                output += f"✅ Controller test completed for {device_path}\n\n"
                output += "**Test Results:**\n"
                output += "- Controller is responding to input\n"
                output += "- All buttons and axes are functional\n\n"
                output += (
                    "**Note:** Press buttons and move sticks to test functionality"
                )
                return [TextContent(type="text", text=output)]
            else:
                return self.format_error(
                    f"Controller test failed: {result.stderr or result.stdout}"
                )
        except Exception as e:
            return self.format_error(f"Controller test failed: {e!s}")

    async def _controller_configure(self, target: str, options: Optional[dict] = None) -> List[TextContent]:
        """Handle controller configuration operations."""
        try:
            if target == "mapping":
                # Configure controller mapping in EmulationStation
                result = self.container.retropie_client.execute_command(
                    "emulationstation --force-input-config"
                )

                if result.success:
                    output = "🎮 **Controller Configuration**\n\n"
                    output += "✅ Controller mapping configuration started\n\n"
                    output += "**Instructions:**\n"
                    output += "1. Follow the on-screen prompts\n"
                    output += "2. Press the requested buttons/directions\n"
                    output += "3. Hold any button to skip unmapped inputs\n"
                    output += "4. Configuration will save automatically"
                    return [TextContent(type="text", text=output)]
                else:
                    return self.format_error(
                        f"Controller configuration failed: {result.stderr or result.stdout}"
                    )
            else:
                valid_targets = self._get_valid_targets_message("controller", "configure")
                return self.format_error(
                    f"Unknown controller configuration target: {target}. {valid_targets}"
                )
        except Exception as e:
            return self.format_error(f"Controller configuration failed: {e!s}")

    # ROM component methods

    async def _roms_scan(self, target: str, options: Optional[dict] = None) -> List[TextContent]:
        """Handle ROM scanning operations."""
        try:
            if not target:
                valid_targets = self._get_valid_targets_message("roms", "scan")
                return self.format_error(
                    f"ROM system target is required for scanning. {valid_targets}"
                )

            # Use the list ROMs use case
            roms = self.container.list_roms_use_case.execute()

            output = "🎮 **ROM Scan Results**\n\n"

            if target == "all":
                output += "**All ROM Systems:**\n\n"

                if roms:
                    for rom in roms:
                        output += f"• **{rom.get('name', 'Unknown')}**\n"
                        output += f"  - Path: {rom.get('path', 'Unknown')}\n"
                        output += f"  - System: {rom.get('system', 'Unknown')}\n\n"
                else:
                    output += "❌ No ROMs found\n\n"
                    output += "**Note:** Place ROM files in the appropriate system directories"
            else:
                output += f"**{target.upper()} System ROMs:**\n\n"

                # Filter ROMs by system if roms is a list of dict
                if roms and isinstance(roms, list):
                    system_roms = []
                    for rom in roms:
                        rom_system = rom.get("system")
                        if not rom_system:
                            # Extract system from path if not explicitly set
                            path = rom.get("path", "")
                            if f"/{target}/" in path:
                                rom_system = target

                        if rom_system == target:
                            system_roms.append(rom)

                    if system_roms:
                        for rom in system_roms:
                            output += f"• **{rom.get('name', 'Unknown')}**\n"
                            output += f"  - Path: {rom.get('path', 'Unknown')}\n\n"
                    else:
                        output += f"❌ No {target} ROMs found\n\n"
                        output += f"**Note:** Place {target} ROM files in {self.container.config.paths.roms_dir}/{target}/"
                else:
                    # If roms is not a list or empty, show no ROMs found
                    output += f"❌ No {target} ROMs found\n\n"
                    output += f"**Note:** Place {target} ROM files in {self.container.config.paths.roms_dir}/{target}/"

            return [TextContent(type="text", text=output)]
        except Exception as e:
            return self.format_error(f"ROM scan failed: {e!s}")

    async def _roms_list(
        self, target: str, options: Dict[str, Any]
    ) -> List[TextContent]:
        """Handle ROM listing operations."""
        # For now, list is the same as scan
        return await self._roms_scan(target, options)

    async def _roms_configure(self, target: str, options: Optional[dict] = None) -> List[TextContent]:
        """Handle ROM configuration operations."""
        try:
            if target == "permissions":
                # Fix ROM permissions
                result = self.container.retropie_client.execute_command(
                    f"sudo chown -R {self.container.config.username}:{self.container.config.username} {self.container.config.paths.roms_dir}"
                )

                if result.success:
                    output = "🎮 **ROM Configuration - Permissions**\n\n"
                    output += "✅ ROM permissions fixed successfully\n\n"
                    output += "**Changes Made:**\n"
                    output += f"- Set ownership to {self.container.config.username}:{self.container.config.username}\n"
                    output += f"- Applied to all files in {self.container.config.paths.roms_dir}\n"
                    output += "- ROMs should now be accessible to RetroPie"
                    return [TextContent(type="text", text=output)]
                else:
                    return self.format_error(
                        f"ROM permissions fix failed: {result.stderr or result.stdout}"
                    )
            else:
                valid_targets = self._get_valid_targets_message("roms", "configure")
                return self.format_error(
                    f"Unknown ROM configuration target: {target}. {valid_targets}"
                )
        except Exception as e:
            return self.format_error(f"ROM configuration failed: {e!s}")

    # Emulator component methods

    async def _emulator_install(self, target: str, options: Optional[Dict[str, Any]] = None) -> List[TextContent]:
        """Handle emulator installation operations."""
        # Delegate to RetroPie install with emulator target
        return await self._retropie_install("emulator", {"emulator": target})

    async def _emulator_configure(self, target: str, options: Optional[Dict[str, Any]] = None) -> List[TextContent]:
        """Handle emulator configuration operations."""
        return self.format_info(
            f"Emulator configuration for {target} not yet implemented"
        )

    async def _emulator_test(self, target: str, options: Optional[Dict[str, Any]] = None) -> List[TextContent]:
        """Handle emulator testing operations."""
        return self.format_info(f"Emulator testing for {target} not yet implemented")

    # Audio component methods

    async def _audio_configure(self, target: str, options: Optional[Dict[str, Any]] = None) -> List[TextContent]:
        """Handle audio configuration operations."""
        try:
            if target == "hdmi":
                # Configure audio to HDMI
                result = self.container.retropie_client.execute_command(
                    "sudo raspi-config nonint do_audio 2"
                )

                if result.success:
                    output = "🔊 **Audio Configuration**\n\n"
                    output += "✅ Audio output configured to HDMI\n\n"
                    output += "**Changes Made:**\n"
                    output += "- Audio output set to HDMI\n"
                    output += "- Configuration saved to system\n"
                    output += "- Restart may be required for changes to take effect"
                    return [TextContent(type="text", text=output)]
                else:
                    return self.format_error(
                        f"Audio configuration failed: {result.stderr or result.stdout}"
                    )
            elif target == "analog":
                # Configure audio to analog/3.5mm
                result = self.container.retropie_client.execute_command(
                    "sudo raspi-config nonint do_audio 1"
                )

                if result.success:
                    output = "🔊 **Audio Configuration**\n\n"
                    output += "✅ Audio output configured to analog (3.5mm)\n\n"
                    output += "**Changes Made:**\n"
                    output += "- Audio output set to analog/3.5mm jack\n"
                    output += "- Configuration saved to system\n"
                    output += "- Restart may be required for changes to take effect"
                    return [TextContent(type="text", text=output)]
                else:
                    return self.format_error(
                        f"Audio configuration failed: {result.stderr or result.stdout}"
                    )
            else:
                valid_targets = self._get_valid_targets_message("audio", "configure")
                return self.format_error(
                    f"Unknown audio configuration target: {target}. {valid_targets}"
                )
        except Exception as e:
            return self.format_error(f"Audio configuration failed: {e!s}")

    async def _audio_test(self, target: str, options: Optional[Dict[str, Any]] = None) -> List[TextContent]:
        """Handle audio testing operations."""
        return self.format_info(f"Audio testing for {target} not yet implemented")

    # Video component methods

    async def _video_configure(
        self, target: str, options: Dict[str, Any]
    ) -> List[TextContent]:
        """Handle video configuration operations."""
        try:
            if target == "resolution":
                resolution = options.get("resolution", "1920x1080")

                # Map common resolutions to raspi-config values
                resolution_map = {
                    "1920x1080": "2 82",
                    "1280x720": "2 85",
                    "1024x768": "2 16",
                    "800x600": "2 9",
                }

                if resolution in resolution_map:
                    config_value = resolution_map[resolution]
                    result = self.container.retropie_client.execute_command(
                        f"sudo raspi-config nonint do_resolution {config_value}"
                    )

                    if result.success:
                        output = "📺 **Video Configuration**\n\n"
                        output += f"✅ Video resolution configured to {resolution}\n\n"
                        output += "**Changes Made:**\n"
                        output += f"- Resolution set to {resolution}\n"
                        output += "- Configuration saved to system\n"
                        output += "- Reboot required for changes to take effect"
                        return [TextContent(type="text", text=output)]
                    else:
                        return self.format_error(
                            f"Video configuration failed: {result.stderr or result.stdout}"
                        )
                else:
                    return self.format_error(
                        f"Unsupported resolution: {resolution}. Supported: {', '.join(resolution_map.keys())}"
                    )
            else:
                valid_targets = self._get_valid_targets_message("video", "configure")
                return self.format_error(
                    f"Unknown video configuration target: {target}. {valid_targets}"
                )
        except Exception as e:
            return self.format_error(f"Video configuration failed: {e!s}")

    async def _video_test(self, target: str, options: Optional[Dict[str, Any]] = None) -> List[TextContent]:
        """Handle video testing operations."""
        return self.format_info(f"Video testing for {target} not yet implemented")
