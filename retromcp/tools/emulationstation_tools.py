"""EmulationStation-specific configuration tools."""

from typing import Any
from typing import Dict
from typing import List

from mcp.types import EmbeddedResource
from mcp.types import ImageContent
from mcp.types import TextContent
from mcp.types import Tool

from .base import BaseTool


class EmulationStationTools(BaseTool):
    """Tools for EmulationStation configuration."""

    def get_tools(self) -> List[Tool]:
        """Return list of available EmulationStation tools.

        Returns:
            List of Tool objects for EmulationStation operations.
        """
        return [
            Tool(
                name="restart_emulationstation",
                description="Restart EmulationStation service",
                inputSchema={"type": "object", "properties": {}, "required": []},
            ),
            Tool(
                name="configure_themes",
                description="Manage EmulationStation themes",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["list", "install", "set"],
                            "description": "Theme management action",
                        },
                        "theme_name": {
                            "type": "string",
                            "description": "Theme name (for install/set actions)",
                        },
                    },
                    "required": ["action"],
                },
            ),
            Tool(
                name="manage_gamelists",
                description="Manage game metadata and scraped information",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["backup", "restore", "regenerate"],
                            "description": "Gamelist management action",
                        },
                        "system": {
                            "type": "string",
                            "description": "System name (optional)",
                        },
                    },
                    "required": ["action"],
                },
            ),
            Tool(
                name="configure_es_settings",
                description="Configure EmulationStation settings",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "setting": {
                            "type": "string",
                            "enum": ["screensaver", "audio", "video", "ui"],
                            "description": "Setting category to configure",
                        },
                        "options": {
                            "type": "object",
                            "description": "Setting-specific options",
                        },
                    },
                    "required": ["setting"],
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
        """Handle tool calls for EmulationStation operations.

        Args:
            name: Name of the tool to call.
            arguments: Arguments for the tool.

        Returns:
            List of content objects with the tool's response.
        """
        try:
            if name == "restart_emulationstation":
                return await self._restart_emulationstation()
            elif name == "configure_themes":
                return await self._configure_themes(arguments)
            elif name == "manage_gamelists":
                return await self._manage_gamelists(arguments)
            elif name == "configure_es_settings":
                return await self._configure_es_settings(arguments)
            else:
                return self.format_error(f"Unknown tool: {name}")
        except Exception as e:
            return self.format_error(f"Error in {name}: {e!s}")

    async def _restart_emulationstation(self) -> List[TextContent]:
        """Restart EmulationStation."""
        # First, check if EmulationStation is running as a systemd service
        service_check_code, service_output, _ = self._execute_command(
            "systemctl is-active emulationstation 2>/dev/null"
        )

        if service_check_code == 0 and "active" in service_output:
            # It's a systemd service
            exit_code, _, _ = self._execute_command(
                "sudo systemctl stop emulationstation"
            )
            self._execute_command("sleep 2")
            exit_code, _, stderr = self._execute_command(
                "sudo systemctl start emulationstation"
            )
        else:
            # It's likely running as a user process
            # Kill any existing EmulationStation processes
            self._execute_command("pkill -f emulationstation")
            self._execute_command("sleep 2")

            # Start EmulationStation as the user
            exit_code, _, stderr = self._execute_command(
                "nohup emulationstation > /dev/null 2>&1 &",
                timeout=5,  # Don't wait for this to complete
            )

        if exit_code == 0:
            return self.format_success("EmulationStation restarted successfully")
        else:
            return self.format_error(f"Failed to restart EmulationStation: {stderr}")

    async def _configure_themes(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Manage EmulationStation themes."""
        action = arguments.get("action")
        theme_name = arguments.get("theme_name")

        if action == "list":
            # List installed themes
            exit_code, output, _ = self._execute_command(
                f"ls -la {self.config.home_dir}/.emulationstation/themes/ /etc/emulationstation/themes/ 2>/dev/null | grep '^d' | awk '{{print $9}}' | grep -v '^\\.$\\|^\\.\\.$'"
            )

            if exit_code == 0 and output:
                return [
                    TextContent(type="text", text=f"🎨 Available Themes:\\n\\n{output}")
                ]
            else:
                return self.format_info("No custom themes found")

        elif action == "install":
            if not theme_name:
                return self.format_error("Theme name required for install action")

            # This is a placeholder - in reality you'd need to implement theme installation
            # which might involve downloading from repositories or GitHub
            return self.format_info(
                f"Theme installation for '{theme_name}' not yet implemented. You can manually install themes to ~/.emulationstation/themes/"
            )

        elif action == "set":
            if not theme_name:
                return self.format_error("Theme name required for set action")

            # Check if theme exists
            exit_code, _, _ = self._execute_command(
                f"test -d {self.config.home_dir}/.emulationstation/themes/{theme_name} || test -d /etc/emulationstation/themes/{theme_name}"
            )

            if exit_code != 0:
                return self.format_error(f"Theme '{theme_name}' not found")

            # Update es_settings.cfg
            exit_code, _, stderr = self._execute_command(
                'sed -i \'s/<string name="ThemeSet" value=".*" \\/>/g\' ~/.emulationstation/es_settings.cfg'
            )
            exit_code, _, stderr = self._execute_command(
                f'echo \'<string name="ThemeSet" value="{theme_name}" />\' >> ~/.emulationstation/es_settings.cfg'
            )

            if exit_code == 0:
                return self.format_success(
                    f"Theme set to '{theme_name}'. Restart EmulationStation to apply changes."
                )
            else:
                return self.format_error(f"Failed to set theme: {stderr}")

        else:
            return self.format_error(f"Unknown theme action: {action}")

    async def _manage_gamelists(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Manage game metadata."""
        action = arguments.get("action")
        system = arguments.get("system")

        gamelist_path = "~/.emulationstation/gamelists"
        if system:
            gamelist_path += f"/{system}"

        if action == "backup":
            # Backup gamelists
            backup_path = f"~/gamelist_backup_{self._execute_command('date +%Y%m%d_%H%M%S')[1].strip()}"
            exit_code, _, stderr = self._execute_command(
                f"cp -r {gamelist_path} {backup_path}"
            )

            if exit_code == 0:
                return self.format_success(f"Gamelists backed up to {backup_path}")
            else:
                return self.format_error(f"Backup failed: {stderr}")

        elif action == "restore":
            return self.format_info(
                "Gamelist restore requires specifying a backup path. Please do this manually."
            )

        elif action == "regenerate":
            # Remove existing gamelists to force regeneration
            exit_code, _, stderr = self._execute_command(f"rm -rf {gamelist_path}")

            if exit_code == 0:
                return self.format_success(
                    "Gamelists cleared. They will be regenerated on next EmulationStation start."
                )
            else:
                return self.format_error(f"Failed to clear gamelists: {stderr}")

        else:
            return self.format_error(f"Unknown gamelist action: {action}")

    async def _configure_es_settings(
        self, arguments: Dict[str, Any]
    ) -> List[TextContent]:
        """Configure EmulationStation settings."""
        setting = arguments.get("setting")
        options = arguments.get("options", {})

        settings_file = f"{self.config.home_dir}/.emulationstation/es_settings.cfg"

        if setting == "screensaver":
            # Configure screensaver settings
            timeout = options.get("timeout", 600)  # 10 minutes default

            exit_code, _, stderr = self._execute_command(
                f'sed -i \'s/<int name="ScreenSaverTime" value=".*" \\/>/g\' {settings_file}'
            )
            exit_code, _, stderr = self._execute_command(
                f'echo \'<int name="ScreenSaverTime" value="{timeout}" />\' >> {settings_file}'
            )

            if exit_code == 0:
                return self.format_success(
                    f"Screensaver timeout set to {timeout} seconds"
                )
            else:
                return self.format_error(f"Failed to configure screensaver: {stderr}")

        elif setting == "audio":
            # Configure audio settings
            return self.format_info(
                "Audio configuration should be done via the configure_audio tool in RetroPie tools"
            )

        elif setting == "video":
            # Configure video settings
            return self.format_info(
                "Video configuration typically requires manual raspi-config or config.txt editing"
            )

        elif setting == "ui":
            # Configure UI settings
            transition = options.get("transition", "fade")

            exit_code, _, stderr = self._execute_command(
                f'sed -i \'s/<string name="TransitionStyle" value=".*" \\/>/g\' {settings_file}'
            )
            exit_code, _, stderr = self._execute_command(
                f'echo \'<string name="TransitionStyle" value="{transition}" />\' >> {settings_file}'
            )

            if exit_code == 0:
                return self.format_success(f"UI transition set to '{transition}'")
            else:
                return self.format_error(f"Failed to configure UI: {stderr}")

        else:
            return self.format_error(f"Unknown setting category: {setting}")
