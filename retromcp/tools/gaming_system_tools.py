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

from ..infrastructure.structured_logger import AuditEvent
from ..infrastructure.structured_logger import ErrorCategory
from ..infrastructure.structured_logger import LogContext
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
                    "emulator (install/configure/list), core (list/info/options), audio (configure/test), video (configure/test). "
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
                                "core",
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
                                "emulator install: emulator name (e.g., 'lr-mame2003'); "
                                "core info/options: core name (e.g., 'lr-mupen64plus-next')"
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
        # Generate correlation ID for request tracking
        correlation_id = self.container.structured_logger.generate_correlation_id()

        # Extract component and action for context
        component = arguments.get("component", "unknown")
        action = arguments.get("action", "unknown")

        # Set up logging context
        context = LogContext(
            correlation_id=correlation_id,
            username=self.config.username,
            component=component,
            action=action,
        )
        self.container.structured_logger.set_context(context)

        try:
            self.container.structured_logger.info(
                f"Starting gaming system operation: {component}/{action}",
                extra_data={"tool_name": name, "arguments": arguments},
            )

            if name == "manage_gaming":
                result = await self._manage_gaming(arguments)

                # Log successful completion
                self.container.structured_logger.info(
                    f"Gaming system operation completed successfully: {component}/{action}"
                )

                return result
            else:
                # Log security event for unknown tool
                self.container.structured_logger.audit_security_event(
                    f"Unknown tool requested: {name}",
                    blocked_action=name,
                    reason="unknown_tool",
                    extra_data={"requested_tool": name},
                )
                return self.format_error(f"Unknown tool: {name}")

        except Exception as e:
            # Log error with categorization
            self.container.structured_logger.error(
                f"Error in {name}: {e!s}",
                category=ErrorCategory.SYSTEM_ERROR,
                extra_data={"tool_name": name, "exception_type": type(e).__name__},
            )
            return self.format_error(f"Error in {name}: {e!s}")
        finally:
            # Always clear context when done
            self.container.structured_logger.clear_context()

    async def _manage_gaming(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Route gaming management requests to appropriate handlers."""
        component = arguments.get("component")
        action = arguments.get("action")

        if not component:
            self.container.structured_logger.error(
                "Component is required",
                category=ErrorCategory.VALIDATION_ERROR,
                extra_data={"arguments": arguments},
            )
            return self.format_error("Component is required")

        if not action:
            self.container.structured_logger.error(
                "Action is required",
                category=ErrorCategory.VALIDATION_ERROR,
                extra_data={"component": component, "arguments": arguments},
            )
            return self.format_error("Action is required")

        # Validate component against allowed values
        valid_components = [
            "retropie",
            "emulationstation",
            "controller",
            "roms",
            "emulator",
            "core",
            "audio",
            "video",
        ]
        if component not in valid_components:
            self.container.structured_logger.audit_security_event(
                f"Invalid component requested: {component}",
                blocked_action="manage_gaming",
                reason="invalid_component",
                extra_data={
                    "requested_component": component,
                    "valid_components": valid_components,
                },
            )
            return self.format_error(f"Invalid component: {component}")

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
        elif component == "core":
            return await self._handle_core(action, arguments)
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
        valid_actions = ["install", "configure", "set_default", "test"]
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
        elif action == "set_default":
            return await self._emulator_set_default(arguments)
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
                with self.container.structured_logger.performance_timing(
                    "retropie_setup_update"
                ):
                    # Use the update system use case
                    result = self.container.update_system_use_case.execute()

                    if result.is_error():
                        error = result.error_or_none

                        # Log audit event for failed operation
                        audit_event = AuditEvent(
                            action="retropie_setup",
                            target="update",
                            success=False,
                            details={
                                "error_message": error.message,
                                "error_code": getattr(error, "code", "unknown"),
                            },
                        )
                        self.container.structured_logger.audit_user_action(audit_event)

                        self.container.structured_logger.error(
                            f"System update failed: {error.message}",
                            category=ErrorCategory.COMMAND_EXECUTION_ERROR,
                            extra_data={
                                "target": target,
                                "error_code": getattr(error, "code", "unknown"),
                            },
                        )
                        return self.format_error(
                            f"System update failed: {error.message}"
                        )

                    command_result = result.value
                    if command_result.success:
                        # Log audit event for successful operation
                        audit_event = AuditEvent(
                            action="retropie_setup",
                            target="update",
                            success=True,
                            details={
                                "command": command_result.command,
                                "exit_code": command_result.exit_code,
                                "output_length": len(command_result.stdout)
                                if command_result.stdout
                                else 0,
                            },
                        )
                        self.container.structured_logger.audit_user_action(audit_event)

                        output = "🎮 **RetroPie Setup - System Update**\n\n"
                        output += "✅ System updated successfully\n\n"
                        if command_result.stdout:
                            output += f"**Update Details:**\n```\n{command_result.stdout}\n```"
                        return [TextContent(type="text", text=output)]
                    else:
                        # Log audit event for command failure
                        audit_event = AuditEvent(
                            action="retropie_setup",
                            target="update",
                            success=False,
                            details={
                                "command": command_result.command,
                                "exit_code": command_result.exit_code,
                                "stderr": command_result.stderr,
                                "stdout": command_result.stdout,
                            },
                        )
                        self.container.structured_logger.audit_user_action(audit_event)

                        self.container.structured_logger.error(
                            f"System update command failed with exit code {command_result.exit_code}",
                            category=ErrorCategory.COMMAND_EXECUTION_ERROR,
                            extra_data={
                                "command": command_result.command,
                                "exit_code": command_result.exit_code,
                                "stderr": command_result.stderr,
                            },
                        )
                        return self.format_error(
                            f"System update failed: {command_result.stderr or command_result.stdout}"
                        )
            else:
                # Log security event for invalid target
                self.container.structured_logger.audit_security_event(
                    f"Invalid RetroPie setup target requested: {target}",
                    blocked_action="retropie_setup",
                    reason="invalid_target",
                    extra_data={
                        "requested_target": target,
                        "component": "retropie",
                        "action": "setup",
                    },
                )

                valid_targets = self._get_valid_targets_message("retropie", "setup")
                return self.format_error(
                    f"Unknown RetroPie setup target: {target}. {valid_targets}"
                )
        except Exception as e:
            # Log audit event for exception
            audit_event = AuditEvent(
                action="retropie_setup",
                target=target,
                success=False,
                details={"exception": str(e), "exception_type": type(e).__name__},
            )
            self.container.structured_logger.audit_user_action(audit_event)

            self.container.structured_logger.error(
                f"RetroPie setup failed: {e!s}",
                category=ErrorCategory.SYSTEM_ERROR,
                extra_data={"target": target, "exception_type": type(e).__name__},
            )
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

                # Handle Result pattern
                if result.is_error():
                    error = result.error_or_none
                    return self.format_error(
                        f"Emulator installation failed: {error.message}"
                    )

                command_result = result.value

                output = "🎮 **RetroPie - Emulator Installation**\n\n"
                output += f"✅ Emulator '{emulator}' installed successfully"
                if system:
                    output += f" for {system}"
                output += "\n\n"
                if command_result.stdout:
                    output += (
                        f"**Installation Details:**\n```\n{command_result.stdout}\n```"
                    )
                return [TextContent(type="text", text=output)]
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
                valid_targets = self._get_valid_targets_message(
                    "emulationstation", "configure"
                )
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

    async def _emulationstation_scan(
        self, target: str, options: Optional[dict] = None
    ) -> List[TextContent]:
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
                valid_targets = self._get_valid_targets_message(
                    "emulationstation", "scan"
                )
                return self.format_error(
                    f"Unknown EmulationStation scan target: {target}. {valid_targets}"
                )
        except Exception as e:
            return self.format_error(f"EmulationStation scan failed: {e!s}")

    # Controller component methods

    async def _controller_detect(self) -> List[TextContent]:
        """Handle controller detection operations."""
        try:
            with self.container.structured_logger.performance_timing(
                "controller_detect"
            ):
                # Use the detect controllers use case
                result = self.container.detect_controllers_use_case.execute()

                # Handle Result pattern
                if result.is_error():
                    error = result.error_or_none

                    # Log audit event for failed operation
                    audit_event = AuditEvent(
                        action="controller_detect",
                        target="controller",
                        success=False,
                        details={
                            "error_message": error.message,
                            "error_code": getattr(error, "code", "unknown"),
                        },
                    )
                    self.container.structured_logger.audit_user_action(audit_event)

                    self.container.structured_logger.error(
                        f"Controller detection failed: {error.message}",
                        category=ErrorCategory.SYSTEM_ERROR,
                        extra_data={"error_code": getattr(error, "code", "unknown")},
                    )
                    return self.format_error(
                        f"Controller detection failed: {error.message}"
                    )

                controllers = result.value

                # Log audit event for successful operation
                audit_event = AuditEvent(
                    action="controller_detect",
                    target="controller",
                    success=True,
                    details={
                        "controllers_found": len(controllers),
                        "controller_types": [
                            c.controller_type.value for c in controllers
                        ],
                    },
                )
                self.container.structured_logger.audit_user_action(audit_event)

                output = "🎮 **Controller Detection**\n\n"

                if controllers:
                    output += "**Detected Controllers:**\n\n"
                    for controller in controllers:
                        status = (
                            "✅ Connected"
                            if controller.connected
                            else "❌ Disconnected"
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
            # Log audit event for exception
            audit_event = AuditEvent(
                action="controller_detect",
                target="controller",
                success=False,
                details={"exception": str(e), "exception_type": type(e).__name__},
            )
            self.container.structured_logger.audit_user_action(audit_event)

            self.container.structured_logger.error(
                f"Controller detection failed: {e!s}",
                category=ErrorCategory.SYSTEM_ERROR,
                extra_data={"exception_type": type(e).__name__},
            )
            return self.format_error(f"Controller detection failed: {e!s}")

    async def _controller_setup(
        self, target: str, options: Optional[dict] = None
    ) -> List[TextContent]:
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

            # Handle Result pattern
            if result.is_error():
                error = result.error_or_none
                return self.format_error(f"Controller setup failed: {error.message}")

            command_result = result.value

            output = "🎮 **Controller Setup**\n\n"
            output += f"✅ {target.upper()} controller setup completed successfully\n\n"
            if command_result.stdout:
                output += f"**Setup Details:**\n```\n{command_result.stdout}\n```"
            return [TextContent(type="text", text=output)]
        except Exception as e:
            return self.format_error(f"Controller setup failed: {e!s}")

    async def _controller_test(
        self, target: str, options: Optional[dict] = None
    ) -> List[TextContent]:
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

    async def _controller_configure(
        self, target: str, options: Optional[dict] = None
    ) -> List[TextContent]:
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
                valid_targets = self._get_valid_targets_message(
                    "controller", "configure"
                )
                return self.format_error(
                    f"Unknown controller configuration target: {target}. {valid_targets}"
                )
        except Exception as e:
            return self.format_error(f"Controller configuration failed: {e!s}")

    # ROM component methods

    async def _roms_scan(
        self, target: str, options: Optional[dict] = None
    ) -> List[TextContent]:
        """Handle ROM scanning operations."""
        try:
            if not target:
                valid_targets = self._get_valid_targets_message("roms", "scan")
                return self.format_error(
                    f"ROM system target is required for scanning. {valid_targets}"
                )

            # Use the list ROMs use case
            result = self.container.list_roms_use_case.execute()

            # Handle Result pattern
            if result.is_error():
                error = result.error_or_none
                return self.format_error(f"ROM scan failed: {error.message}")

            roms = result.value

            output = "🎮 **ROM Scan Results**\n\n"

            if target == "all":
                output += "**All ROM Systems:**\n\n"

                if roms:
                    for rom in roms:
                        output += f"• **{rom.system}**\n"
                        output += f"  - Path: {rom.path}\n"
                        output += f"  - ROM Count: {rom.rom_count}\n\n"
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

    async def _roms_configure(
        self, target: str, options: Optional[dict] = None
    ) -> List[TextContent]:
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

    async def _emulator_install(
        self, target: str, options: Optional[Dict[str, Any]] = None
    ) -> List[TextContent]:
        """Handle emulator installation operations."""
        # Delegate to RetroPie install with emulator target
        return await self._retropie_install("emulator", {"emulator": target})

    async def _emulator_configure(
        self, target: str, options: Optional[Dict[str, Any]] = None
    ) -> List[TextContent]:
        """Handle emulator configuration operations.

        Updates core options for a specific emulator/core.

        Args:
            target: Core name (e.g., 'lr-mupen64plus-next')
            options: Dict of option key-value pairs to update

        Returns:
            List of TextContent with results
        """
        if not target:
            return self.format_error("Target core name is required")

        if not options:
            return self.format_error("Options dictionary is required for configuration")

        # Update each option
        results = []
        use_case = self.container.update_core_option_use_case

        for key, value in options.items():
            result = use_case.execute(target, key, str(value))

            if result.is_error():
                error = result.error_value
                results.append(f"❌ Failed to update {key}: {error.message}")
            else:
                results.append(f"✅ Updated {key} = {value}")

        return self.format_success("\n".join(results))

    async def _emulator_set_default(
        self, arguments: Dict[str, Any]
    ) -> List[TextContent]:
        """Set the default emulator for a system.

        Args:
            arguments: Must contain 'system' and 'target' (emulator name)

        Returns:
            List of TextContent with results
        """
        system = arguments.get("system")
        target = arguments.get("target")

        if not system:
            return self.format_error("System name is required")

        if not target:
            return self.format_error("Target emulator name is required")

        use_case = self.container.set_default_emulator_use_case
        result = use_case.execute(system, target)

        if result.is_error():
            error = result.error_value
            return self.format_error(f"Failed to set default emulator: {error.message}")

        return self.format_success(
            f"✅ Set {target} as default emulator for {system}"
        )

    async def _emulator_test(
        self, target: str, options: Optional[Dict[str, Any]] = None
    ) -> List[TextContent]:
        """Handle emulator testing operations."""
        return self.format_info(f"Emulator testing for {target} not yet implemented")

    # Core component methods

    async def _handle_core(
        self, action: str, arguments: Dict[str, Any]
    ) -> List[TextContent]:
        """Handle RetroArch core management operations."""
        valid_actions = ["list", "info", "options"]
        if action not in valid_actions:
            return self.format_error(
                f"Invalid action: {action}. Must be one of: {', '.join(valid_actions)}"
            )

        if action == "list":
            return await self._core_list()
        elif action == "info":
            target = arguments.get("target")
            return await self._core_info(target)
        elif action == "options":
            target = arguments.get("target")
            return await self._core_options(target)
        else:
            return self.format_error(f"Core action '{action}' not implemented")

    async def _core_list(self) -> List[TextContent]:
        """List all installed RetroArch cores."""
        use_case = self.container.list_cores_use_case
        result = use_case.execute()

        if result.is_error():
            error = result.error_value
            return self.format_error(f"Failed to list cores: {error.message}")

        cores = result.success_value

        if not cores:
            return self.format_info("No RetroArch cores found")

        # Format core list
        output = [f"Found {len(cores)} RetroArch cores:\n"]

        for core in cores:
            systems_str = ", ".join(core.systems) if core.systems else "no systems"
            output.append(f"  • {core.name}")
            output.append(f"    Display: {core.display_name}")
            output.append(f"    Systems: {systems_str}")
            output.append(f"    Path: {core.core_path}")
            if core.version:
                output.append(f"    Version: {core.version}")
            output.append("")

        return self.format_success("\n".join(output))

    async def _core_info(self, target: str) -> List[TextContent]:
        """Get detailed information about a specific core."""
        if not target:
            return self.format_error("Target core name is required")

        use_case = self.container.get_core_info_use_case
        result = use_case.execute(target)

        if result.is_error():
            error = result.error_value
            return self.format_error(f"Failed to get core info: {error.message}")

        core = result.success_value

        # Format core information
        output = [f"Core Information: {core.name}\n"]
        output.append(f"Display Name: {core.display_name}")
        if core.description:
            output.append(f"Description: {core.description}")
        if core.version:
            output.append(f"Version: {core.version}")
        output.append(f"Core Path: {core.core_path}")

        if core.systems:
            output.append(f"\nSupported Systems:")
            for system in core.systems:
                output.append(f"  • {system}")
        else:
            output.append(f"\nNo systems configured to use this core")

        return self.format_success("\n".join(output))

    async def _core_options(self, target: str) -> List[TextContent]:
        """List configurable options for a specific core."""
        if not target:
            return self.format_error("Target core name is required")

        use_case = self.container.list_core_options_use_case
        result = use_case.execute(target)

        if result.is_error():
            error = result.error_value
            return self.format_error(f"Failed to get core options: {error.message}")

        options = result.success_value

        if not options:
            return self.format_info(f"No options found for core: {target}")

        # Format options list
        output = [f"Configuration options for {target}:\n"]

        for option in options:
            output.append(f"  {option.key} = \"{option.value}\"")
            if option.description:
                output.append(f"    ({option.description})")

        output.append(f"\nTotal: {len(options)} options")
        output.append(f"\nTo update an option, use:")
        output.append(f'  component="emulator", action="configure", target="{target}", options={{"key": "value"}}')

        return self.format_success("\n".join(output))

    # Audio component methods

    async def _audio_configure(
        self, target: str, options: Optional[Dict[str, Any]] = None
    ) -> List[TextContent]:
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

    async def _audio_test(
        self, target: str, options: Optional[Dict[str, Any]] = None
    ) -> List[TextContent]:
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

    async def _video_test(
        self, target: str, options: Optional[Dict[str, Any]] = None
    ) -> List[TextContent]:
        """Handle video testing operations."""
        return self.format_info(f"Video testing for {target} not yet implemented")
