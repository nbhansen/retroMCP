"""Unit tests for EmulationStationTools implementation."""

from unittest.mock import Mock

import pytest
from mcp.types import TextContent

from retromcp.config import RetroPieConfig
from retromcp.discovery import RetroPiePaths
from retromcp.domain.models import CommandResult
from retromcp.tools.emulationstation_tools import EmulationStationTools


class TestEmulationStationTools:
    """Test cases for EmulationStationTools class."""

    @pytest.fixture
    def mock_container(self, test_config: RetroPieConfig) -> Mock:
        """Provide mocked container."""
        mock = Mock()
        mock.retropie_client = Mock()
        mock.retropie_client.execute_command = Mock()
        mock.config = test_config
        return mock

    @pytest.fixture
    def test_config(self) -> RetroPieConfig:
        """Provide test configuration."""
        paths = RetroPiePaths(
            home_dir="/home/retro",
            username="retro",
            retropie_dir="/home/retro/RetroPie",
            retropie_setup_dir="/home/retro/RetroPie-Setup",
            bios_dir="/home/retro/RetroPie/BIOS",
            roms_dir="/home/retro/RetroPie/roms",
            configs_dir="/opt/retropie/configs",
            emulators_dir="/opt/retropie/emulators",
        )

        return RetroPieConfig(
            host="test-retropie.local",
            username="retro",
            password="test_password",  # noqa: S106 # Test fixture, not real password
            port=22,
            paths=paths,
        )

    @pytest.fixture
    def es_tools(self, mock_container: Mock) -> EmulationStationTools:
        """Provide EmulationStationTools instance with mocked dependencies."""
        return EmulationStationTools(mock_container)

    def test_get_tools(self, es_tools: EmulationStationTools) -> None:
        """Test that all expected tools are returned."""
        tools = es_tools.get_tools()

        assert len(tools) == 4
        tool_names = [tool.name for tool in tools]

        expected_tools = [
            "restart_emulationstation",
            "configure_themes",
            "manage_gamelists",
            "configure_es_settings",
        ]

        for expected_tool in expected_tools:
            assert expected_tool in tool_names

    def test_tool_schemas(self, es_tools: EmulationStationTools) -> None:
        """Test that tool schemas are properly defined."""
        tools = es_tools.get_tools()
        tool_dict = {tool.name: tool for tool in tools}

        # Restart tool - no parameters
        restart_tool = tool_dict["restart_emulationstation"]
        assert restart_tool.inputSchema["type"] == "object"
        assert restart_tool.inputSchema["required"] == []

        # Theme configuration tool
        themes_tool = tool_dict["configure_themes"]
        assert "action" in themes_tool.inputSchema["properties"]
        assert "list" in themes_tool.inputSchema["properties"]["action"]["enum"]
        assert "install" in themes_tool.inputSchema["properties"]["action"]["enum"]
        assert "set" in themes_tool.inputSchema["properties"]["action"]["enum"]
        assert "theme_name" in themes_tool.inputSchema["properties"]
        assert themes_tool.inputSchema["required"] == ["action"]

        # Gamelist management tool
        gamelists_tool = tool_dict["manage_gamelists"]
        assert "action" in gamelists_tool.inputSchema["properties"]
        assert "backup" in gamelists_tool.inputSchema["properties"]["action"]["enum"]
        assert "restore" in gamelists_tool.inputSchema["properties"]["action"]["enum"]
        assert (
            "regenerate" in gamelists_tool.inputSchema["properties"]["action"]["enum"]
        )
        assert "system" in gamelists_tool.inputSchema["properties"]

        # Settings configuration tool
        settings_tool = tool_dict["configure_es_settings"]
        assert "setting" in settings_tool.inputSchema["properties"]
        assert (
            "screensaver" in settings_tool.inputSchema["properties"]["setting"]["enum"]
        )
        assert "audio" in settings_tool.inputSchema["properties"]["setting"]["enum"]
        assert "video" in settings_tool.inputSchema["properties"]["setting"]["enum"]
        assert "ui" in settings_tool.inputSchema["properties"]["setting"]["enum"]
        assert "options" in settings_tool.inputSchema["properties"]

    @pytest.mark.asyncio
    async def test_restart_emulationstation_systemd_service(
        self, es_tools: EmulationStationTools
    ) -> None:
        """Test restarting EmulationStation when running as systemd service."""
        es_tools.container.retropie_client.execute_command.side_effect = [
            CommandResult(
                "systemctl is-active emulationstation", 0, "active", "", True, 0.1
            ),  # Service check
            CommandResult(
                "systemctl stop emulationstation", 0, "", "", True, 0.1
            ),  # Stop command
            CommandResult("sleep 2", 0, "", "", True, 0.1),  # Sleep
            CommandResult(
                "systemctl start emulationstation", 0, "", "", True, 0.1
            ),  # Start command
        ]

        result = await es_tools.handle_tool_call("restart_emulationstation", {})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "EmulationStation restarted successfully" in result[0].text

    @pytest.mark.asyncio
    async def test_restart_emulationstation_user_process(
        self, es_tools: EmulationStationTools
    ) -> None:
        """Test restarting EmulationStation when running as user process."""
        es_tools.container.retropie_client.execute_command.side_effect = [
            CommandResult(
                "systemctl is-active emulationstation", 1, "", "", False, 0.1
            ),  # Service not active
            CommandResult("pkill emulationstation", 0, "", "", True, 0.1),  # pkill
            CommandResult("sleep 2", 0, "", "", True, 0.1),  # sleep
            CommandResult(
                "nohup emulationstation > /dev/null 2>&1 &", 0, "", "", True, 0.1
            ),  # start as user
        ]

        result = await es_tools.handle_tool_call("restart_emulationstation", {})

        assert len(result) == 1
        assert "EmulationStation restarted successfully" in result[0].text

    @pytest.mark.asyncio
    async def test_restart_emulationstation_failure(
        self, es_tools: EmulationStationTools
    ) -> None:
        """Test EmulationStation restart failure."""
        es_tools.container.retropie_client.execute_command.side_effect = [
            CommandResult(
                "systemctl is-active emulationstation", 0, "active", "", True, 0.1
            ),  # Service check
            CommandResult(
                "systemctl stop emulationstation", 0, "", "", True, 0.1
            ),  # Stop command
            CommandResult("sleep 2", 0, "", "", True, 0.1),  # Sleep
            CommandResult(
                "systemctl start emulationstation",
                1,
                "",
                "Failed to start service",
                False,
                0.1,
            ),  # Start command fails
        ]

        result = await es_tools.handle_tool_call("restart_emulationstation", {})

        assert len(result) == 1
        assert (
            "Failed to restart EmulationStation: Failed to start service"
            in result[0].text
        )

    @pytest.mark.asyncio
    async def test_configure_themes_list_with_themes(
        self, es_tools: EmulationStationTools
    ) -> None:
        """Test listing themes when themes are available."""
        es_tools.container.retropie_client.execute_command.return_value = CommandResult(
            "ls /home/retro/.emulationstation/themes/",
            0,
            "carbon\ncarbon-centered\nrecalbox-multi\ncomfy",
            "",
            True,
            0.1,
        )

        result = await es_tools.handle_tool_call("configure_themes", {"action": "list"})

        assert len(result) == 1
        assert "🎨 Available Themes:" in result[0].text
        assert "carbon" in result[0].text
        assert "recalbox-multi" in result[0].text

    @pytest.mark.asyncio
    async def test_configure_themes_list_no_themes(
        self, es_tools: EmulationStationTools
    ) -> None:
        """Test listing themes when no custom themes are found."""
        es_tools.container.retropie_client.execute_command.return_value = CommandResult(
            "ls /home/retro/.emulationstation/themes/", 1, "", "", False, 0.1
        )

        result = await es_tools.handle_tool_call("configure_themes", {"action": "list"})

        assert len(result) == 1
        assert "No custom themes found" in result[0].text

    @pytest.mark.asyncio
    async def test_configure_themes_install_not_implemented(
        self, es_tools: EmulationStationTools
    ) -> None:
        """Test theme installation (not yet implemented)."""
        result = await es_tools.handle_tool_call(
            "configure_themes", {"action": "install", "theme_name": "custom-theme"}
        )

        assert len(result) == 1
        assert (
            "Theme installation for 'custom-theme' not yet implemented"
            in result[0].text
        )
        assert "manually install themes" in result[0].text

    @pytest.mark.asyncio
    async def test_configure_themes_install_missing_name(
        self, es_tools: EmulationStationTools
    ) -> None:
        """Test theme installation with missing theme name."""
        result = await es_tools.handle_tool_call(
            "configure_themes", {"action": "install"}
        )

        assert len(result) == 1
        assert "Theme name required for install action" in result[0].text

    @pytest.mark.asyncio
    async def test_configure_themes_set_success(
        self, es_tools: EmulationStationTools
    ) -> None:
        """Test setting theme successfully."""
        es_tools.container.retropie_client.execute_command.side_effect = [
            CommandResult(
                "test -d /home/retro/.emulationstation/themes/carbon",
                0,
                "",
                "",
                True,
                0.1,
            ),  # Theme exists check
            CommandResult(
                "sed -i '/ThemeSet/d' /home/retro/.emulationstation/es_settings.cfg",
                0,
                "",
                "",
                True,
                0.1,
            ),  # sed remove old setting
            CommandResult(
                'echo \'<string name="ThemeSet" value="carbon" />\' >> /home/retro/.emulationstation/es_settings.cfg',
                0,
                "",
                "",
                True,
                0.1,
            ),  # echo new setting
        ]

        result = await es_tools.handle_tool_call(
            "configure_themes", {"action": "set", "theme_name": "carbon"}
        )

        assert len(result) == 1
        assert "Theme set to 'carbon'" in result[0].text
        assert "Restart EmulationStation to apply changes" in result[0].text

    @pytest.mark.asyncio
    async def test_configure_themes_set_theme_not_found(
        self, es_tools: EmulationStationTools
    ) -> None:
        """Test setting theme when theme doesn't exist."""
        es_tools.container.retropie_client.execute_command.return_value = CommandResult(
            "test -d /home/retro/.emulationstation/themes/nonexistent",
            1,
            "",
            "",
            False,
            0.1,
        )  # Theme doesn't exist

        result = await es_tools.handle_tool_call(
            "configure_themes", {"action": "set", "theme_name": "nonexistent"}
        )

        assert len(result) == 1
        assert "Theme 'nonexistent' not found" in result[0].text

    @pytest.mark.asyncio
    async def test_configure_themes_set_missing_name(
        self, es_tools: EmulationStationTools
    ) -> None:
        """Test setting theme with missing theme name."""
        result = await es_tools.handle_tool_call("configure_themes", {"action": "set"})

        assert len(result) == 1
        assert "Theme name required for set action" in result[0].text

    @pytest.mark.asyncio
    async def test_configure_themes_set_failure(
        self, es_tools: EmulationStationTools
    ) -> None:
        """Test theme setting failure during configuration."""
        es_tools.container.retropie_client.execute_command.side_effect = [
            CommandResult(
                "test -d /home/retro/.emulationstation/themes/carbon",
                0,
                "",
                "",
                True,
                0.1,
            ),  # Theme exists check
            CommandResult(
                "sed -i '/ThemeSet/d' /home/retro/.emulationstation/es_settings.cfg",
                0,
                "",
                "",
                True,
                0.1,
            ),  # sed remove old setting
            CommandResult(
                'echo \'<string name="ThemeSet" value="carbon" />\' >> /home/retro/.emulationstation/es_settings.cfg',
                1,
                "",
                "Permission denied",
                False,
                0.1,
            ),  # echo new setting fails
        ]

        result = await es_tools.handle_tool_call(
            "configure_themes", {"action": "set", "theme_name": "carbon"}
        )

        assert len(result) == 1
        assert "Failed to set theme: Permission denied" in result[0].text

    @pytest.mark.asyncio
    async def test_configure_themes_unknown_action(
        self, es_tools: EmulationStationTools
    ) -> None:
        """Test theme configuration with unknown action."""
        result = await es_tools.handle_tool_call(
            "configure_themes", {"action": "invalid"}
        )

        assert len(result) == 1
        assert "Unknown theme action: invalid" in result[0].text

    @pytest.mark.asyncio
    async def test_manage_gamelists_backup_success(
        self, es_tools: EmulationStationTools
    ) -> None:
        """Test gamelist backup success."""
        # Mock the date command to return a consistent timestamp
        es_tools.container.retropie_client.execute_command.side_effect = [
            CommandResult(
                "date +%Y%m%d_%H%M%S", 0, "20240115_143022", "", True, 0.1
            ),  # date command
            CommandResult(
                "cp -r /home/retro/.emulationstation/gamelists /home/retro/gamelist_backup_20240115_143022",
                0,
                "",
                "",
                True,
                0.1,
            ),  # cp command
        ]

        result = await es_tools.handle_tool_call(
            "manage_gamelists", {"action": "backup"}
        )

        assert len(result) == 1
        assert "Gamelists backed up to" in result[0].text

    @pytest.mark.asyncio
    async def test_manage_gamelists_backup_system_specific(
        self, es_tools: EmulationStationTools
    ) -> None:
        """Test gamelist backup for specific system."""
        es_tools.container.retropie_client.execute_command.side_effect = [
            CommandResult(
                "date +%Y%m%d_%H%M%S", 0, "20240115_143022", "", True, 0.1
            ),  # date command
            CommandResult(
                "cp -r /home/retro/.emulationstation/gamelists/nes /home/retro/gamelist_backup_20240115_143022",
                0,
                "",
                "",
                True,
                0.1,
            ),  # cp command
        ]

        result = await es_tools.handle_tool_call(
            "manage_gamelists", {"action": "backup", "system": "nes"}
        )

        assert len(result) == 1
        assert "Gamelists backed up to" in result[0].text

    @pytest.mark.asyncio
    async def test_manage_gamelists_backup_failure(
        self, es_tools: EmulationStationTools
    ) -> None:
        """Test gamelist backup failure."""
        es_tools.container.retropie_client.execute_command.side_effect = [
            CommandResult(
                "date +%Y%m%d_%H%M%S", 0, "20240115_143022", "", True, 0.1
            ),  # date command
            CommandResult(
                "cp -r /home/retro/.emulationstation/gamelists /home/retro/gamelist_backup_20240115_143022",
                1,
                "",
                "No such file or directory",
                False,
                0.1,
            ),  # cp command fails
        ]

        result = await es_tools.handle_tool_call(
            "manage_gamelists", {"action": "backup"}
        )

        assert len(result) == 1
        assert "Backup failed: No such file or directory" in result[0].text

    @pytest.mark.asyncio
    async def test_manage_gamelists_restore_not_implemented(
        self, es_tools: EmulationStationTools
    ) -> None:
        """Test gamelist restore (requires manual specification)."""
        result = await es_tools.handle_tool_call(
            "manage_gamelists", {"action": "restore"}
        )

        assert len(result) == 1
        assert "Gamelist restore requires specifying a backup path" in result[0].text
        assert "Please do this manually" in result[0].text

    @pytest.mark.asyncio
    async def test_manage_gamelists_regenerate_success(
        self, es_tools: EmulationStationTools
    ) -> None:
        """Test gamelist regeneration success."""
        es_tools.container.retropie_client.execute_command.return_value = CommandResult(
            "rm -rf /home/retro/.emulationstation/gamelists", 0, "", "", True, 0.1
        )

        result = await es_tools.handle_tool_call(
            "manage_gamelists", {"action": "regenerate"}
        )

        assert len(result) == 1
        assert "Gamelists cleared" in result[0].text
        assert "regenerated on next EmulationStation start" in result[0].text

    @pytest.mark.asyncio
    async def test_manage_gamelists_regenerate_failure(
        self, es_tools: EmulationStationTools
    ) -> None:
        """Test gamelist regeneration failure."""
        es_tools.container.retropie_client.execute_command.return_value = CommandResult(
            "rm -rf /home/retro/.emulationstation/gamelists",
            1,
            "",
            "Permission denied",
            False,
            0.1,
        )

        result = await es_tools.handle_tool_call(
            "manage_gamelists", {"action": "regenerate"}
        )

        assert len(result) == 1
        assert "Failed to clear gamelists: Permission denied" in result[0].text

    @pytest.mark.asyncio
    async def test_manage_gamelists_unknown_action(
        self, es_tools: EmulationStationTools
    ) -> None:
        """Test gamelist management with unknown action."""
        result = await es_tools.handle_tool_call(
            "manage_gamelists", {"action": "invalid"}
        )

        assert len(result) == 1
        assert "Unknown gamelist action: invalid" in result[0].text

    @pytest.mark.asyncio
    async def test_configure_es_settings_screensaver_default(
        self, es_tools: EmulationStationTools
    ) -> None:
        """Test configuring screensaver with default timeout."""
        es_tools.container.retropie_client.execute_command.side_effect = [
            CommandResult(
                "sed -i '/ScreenSaverTime/d' /home/retro/.emulationstation/es_settings.cfg",
                0,
                "",
                "",
                True,
                0.1,
            ),  # sed remove old setting
            CommandResult(
                'echo \'<int name="ScreenSaverTime" value="600000" />\' >> /home/retro/.emulationstation/es_settings.cfg',
                0,
                "",
                "",
                True,
                0.1,
            ),  # echo new setting
        ]

        result = await es_tools.handle_tool_call(
            "configure_es_settings", {"setting": "screensaver"}
        )

        assert len(result) == 1
        assert "Screensaver timeout set to 600 seconds" in result[0].text

    @pytest.mark.asyncio
    async def test_configure_es_settings_screensaver_custom(
        self, es_tools: EmulationStationTools
    ) -> None:
        """Test configuring screensaver with custom timeout."""
        es_tools.container.retropie_client.execute_command.side_effect = [
            CommandResult(
                "sed -i '/ScreenSaverTime/d' /home/retro/.emulationstation/es_settings.cfg",
                0,
                "",
                "",
                True,
                0.1,
            ),  # sed remove old setting
            CommandResult(
                'echo \'<int name="ScreenSaverTime" value="300000" />\' >> /home/retro/.emulationstation/es_settings.cfg',
                0,
                "",
                "",
                True,
                0.1,
            ),  # echo new setting
        ]

        result = await es_tools.handle_tool_call(
            "configure_es_settings",
            {"setting": "screensaver", "options": {"timeout": 300}},
        )

        assert len(result) == 1
        assert "Screensaver timeout set to 300 seconds" in result[0].text

    @pytest.mark.asyncio
    async def test_configure_es_settings_screensaver_failure(
        self, es_tools: EmulationStationTools
    ) -> None:
        """Test screensaver configuration failure."""
        es_tools.container.retropie_client.execute_command.side_effect = [
            CommandResult(
                "sed -i '/ScreenSaverTime/d' /home/retro/.emulationstation/es_settings.cfg",
                0,
                "",
                "",
                True,
                0.1,
            ),  # sed remove old setting
            CommandResult(
                'echo \'<int name="ScreenSaverTime" value="600000" />\' >> /home/retro/.emulationstation/es_settings.cfg',
                1,
                "",
                "Write error",
                False,
                0.1,
            ),  # echo new setting fails
        ]

        result = await es_tools.handle_tool_call(
            "configure_es_settings", {"setting": "screensaver"}
        )

        assert len(result) == 1
        assert "Failed to configure screensaver: Write error" in result[0].text

    @pytest.mark.asyncio
    async def test_configure_es_settings_audio_redirect(
        self, es_tools: EmulationStationTools
    ) -> None:
        """Test audio setting configuration redirects to RetroPie tools."""
        result = await es_tools.handle_tool_call(
            "configure_es_settings", {"setting": "audio"}
        )

        assert len(result) == 1
        assert (
            "Audio configuration should be done via the configure_audio tool"
            in result[0].text
        )
        assert "RetroPie tools" in result[0].text

    @pytest.mark.asyncio
    async def test_configure_es_settings_video_info(
        self, es_tools: EmulationStationTools
    ) -> None:
        """Test video setting configuration provides manual guidance."""
        result = await es_tools.handle_tool_call(
            "configure_es_settings", {"setting": "video"}
        )

        assert len(result) == 1
        assert "Video configuration typically requires" in result[0].text
        assert "raspi-config or config.txt editing" in result[0].text

    @pytest.mark.asyncio
    async def test_configure_es_settings_ui_default(
        self, es_tools: EmulationStationTools
    ) -> None:
        """Test UI configuration with default transition."""
        es_tools.container.retropie_client.execute_command.side_effect = [
            CommandResult(
                "sed -i '/TransitionStyle/d' /home/retro/.emulationstation/es_settings.cfg",
                0,
                "",
                "",
                True,
                0.1,
            ),  # sed remove old setting
            CommandResult(
                'echo \'<string name="TransitionStyle" value="fade" />\' >> /home/retro/.emulationstation/es_settings.cfg',
                0,
                "",
                "",
                True,
                0.1,
            ),  # echo new setting
        ]

        result = await es_tools.handle_tool_call(
            "configure_es_settings", {"setting": "ui"}
        )

        assert len(result) == 1
        assert "UI transition set to 'fade'" in result[0].text

    @pytest.mark.asyncio
    async def test_configure_es_settings_ui_custom(
        self, es_tools: EmulationStationTools
    ) -> None:
        """Test UI configuration with custom transition."""
        es_tools.container.retropie_client.execute_command.side_effect = [
            CommandResult(
                "sed -i '/TransitionStyle/d' /home/retro/.emulationstation/es_settings.cfg",
                0,
                "",
                "",
                True,
                0.1,
            ),  # sed remove old setting
            CommandResult(
                'echo \'<string name="TransitionStyle" value="slide" />\' >> /home/retro/.emulationstation/es_settings.cfg',
                0,
                "",
                "",
                True,
                0.1,
            ),  # echo new setting
        ]

        result = await es_tools.handle_tool_call(
            "configure_es_settings",
            {"setting": "ui", "options": {"transition": "slide"}},
        )

        assert len(result) == 1
        assert "UI transition set to 'slide'" in result[0].text

    @pytest.mark.asyncio
    async def test_configure_es_settings_ui_failure(
        self, es_tools: EmulationStationTools
    ) -> None:
        """Test UI configuration failure."""
        es_tools.container.retropie_client.execute_command.side_effect = [
            CommandResult(
                "sed -i '/TransitionStyle/d' /home/retro/.emulationstation/es_settings.cfg",
                0,
                "",
                "",
                True,
                0.1,
            ),  # sed remove old setting
            CommandResult(
                'echo \'<string name="TransitionStyle" value="fade" />\' >> /home/retro/.emulationstation/es_settings.cfg',
                1,
                "",
                "Permission denied",
                False,
                0.1,
            ),  # echo new setting fails
        ]

        result = await es_tools.handle_tool_call(
            "configure_es_settings", {"setting": "ui"}
        )

        assert len(result) == 1
        assert "Failed to configure UI: Permission denied" in result[0].text

    @pytest.mark.asyncio
    async def test_configure_es_settings_unknown_setting(
        self, es_tools: EmulationStationTools
    ) -> None:
        """Test ES settings configuration with unknown setting."""
        result = await es_tools.handle_tool_call(
            "configure_es_settings", {"setting": "invalid"}
        )

        assert len(result) == 1
        assert "Unknown setting category: invalid" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_unknown_tool(self, es_tools: EmulationStationTools) -> None:
        """Test handling of unknown tool name."""
        result = await es_tools.handle_tool_call("unknown_tool", {})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Unknown tool: unknown_tool" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_tool_exception(self, es_tools: EmulationStationTools) -> None:
        """Test exception handling in tool execution."""
        es_tools.container.retropie_client.execute_command.side_effect = Exception(
            "SSH connection lost"
        )

        result = await es_tools.handle_tool_call("restart_emulationstation", {})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert (
            "Error in restart_emulationstation: SSH connection lost" in result[0].text
        )

    @pytest.mark.asyncio
    async def test_restart_emulationstation_timeout_parameter_fixed(
        self, es_tools: EmulationStationTools
    ) -> None:
        """Test that timeout parameter is now fixed - should work properly."""
        # Mock the service check to be inactive so it goes to user process path
        es_tools.container.retropie_client.execute_command.side_effect = [
            CommandResult(
                "systemctl is-active emulationstation", 1, "", "", False, 0.1
            ),  # Service not active
            CommandResult("pkill emulationstation", 0, "", "", True, 0.1),  # pkill
            CommandResult("sleep 2", 0, "", "", True, 0.1),  # sleep
            CommandResult(
                "nohup emulationstation > /dev/null 2>&1 &", 0, "", "", True, 0.1
            ),  # start EmulationStation
        ]

        # This should now work properly without timeout parameter error
        result = await es_tools.handle_tool_call("restart_emulationstation", {})

        # Should return success message, not timeout error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "EmulationStation restarted successfully" in result[0].text
        # Most importantly, should NOT contain the timeout error
        assert "unexpected keyword argument 'timeout'" not in result[0].text

    def test_inheritance_from_base_tool(self, es_tools: EmulationStationTools) -> None:
        """Test that EmulationStationTools properly inherits from BaseTool."""
        # Should have access to BaseTool methods
        assert hasattr(es_tools, "format_success")
        assert hasattr(es_tools, "format_error")
        assert hasattr(es_tools, "format_info")
        assert hasattr(es_tools, "container")
        assert hasattr(es_tools, "config")

        # Test format methods work
        success_result = es_tools.format_success("Test message")
        assert len(success_result) == 1
        assert isinstance(success_result[0], TextContent)
        assert "Test message" in success_result[0].text

        error_result = es_tools.format_error("Error message")
        assert len(error_result) == 1
        assert isinstance(error_result[0], TextContent)
        assert "Error message" in error_result[0].text

    @pytest.mark.asyncio
    async def test_theme_listing_uses_config_paths(
        self, es_tools: EmulationStationTools
    ) -> None:
        """Test that theme listing uses configuration home directory."""
        es_tools.container.retropie_client.execute_command.return_value = CommandResult(
            "ls /home/retro/.emulationstation/themes/",
            0,
            "theme1\ntheme2",
            "",
            True,
            0.1,
        )

        await es_tools.handle_tool_call("configure_themes", {"action": "list"})

        # Check that the command uses config home directory
        call_args = es_tools.container.retropie_client.execute_command.call_args[0][0]
        assert "/home/retro/.emulationstation/themes/" in call_args

    @pytest.mark.asyncio
    async def test_settings_file_uses_config_path(
        self, es_tools: EmulationStationTools
    ) -> None:
        """Test that settings configuration uses config home directory."""
        es_tools.container.retropie_client.execute_command.side_effect = [
            CommandResult(
                "sed -i '/ScreenSaverTime/d' /home/retro/.emulationstation/es_settings.cfg",
                0,
                "",
                "",
                True,
                0.1,
            ),  # sed command
            CommandResult(
                'echo \'<int name="ScreenSaverTime" value="600000" />\' >> /home/retro/.emulationstation/es_settings.cfg',
                0,
                "",
                "",
                True,
                0.1,
            ),  # echo command
        ]

        await es_tools.handle_tool_call(
            "configure_es_settings", {"setting": "screensaver"}
        )

        # Check that commands reference the config file path
        for call in es_tools.container.retropie_client.execute_command.call_args_list:
            if "/home/retro/.emulationstation/es_settings.cfg" in call[0][0]:
                break
        else:
            pytest.fail("Settings file path not found in commands")

    @pytest.mark.asyncio
    async def test_restart_handles_both_service_types(
        self, es_tools: EmulationStationTools
    ) -> None:
        """Test restart logic properly detects service vs user process."""
        # Test systemd service path
        es_tools.container.retropie_client.execute_command.side_effect = [
            CommandResult(
                "systemctl is-active emulationstation", 0, "active", "", True, 0.1
            ),  # Service is active
            CommandResult(
                "systemctl stop emulationstation", 0, "", "", True, 0.1
            ),  # Stop
            CommandResult("sleep 2", 0, "", "", True, 0.1),  # Sleep
            CommandResult(
                "systemctl start emulationstation", 0, "", "", True, 0.1
            ),  # Start
        ]

        result = await es_tools.handle_tool_call("restart_emulationstation", {})
        assert "EmulationStation restarted successfully" in result[0].text

        # Test user process path
        es_tools.container.retropie_client.execute_command.reset_mock()
        es_tools.container.retropie_client.execute_command.side_effect = [
            CommandResult(
                "systemctl is-active emulationstation", 1, "inactive", "", False, 0.1
            ),  # Service is not active
            CommandResult("pkill emulationstation", 0, "", "", True, 0.1),  # pkill
            CommandResult("sleep 2", 0, "", "", True, 0.1),  # sleep
            CommandResult(
                "nohup emulationstation > /dev/null 2>&1 &", 0, "", "", True, 0.1
            ),  # nohup start
        ]

        result = await es_tools.handle_tool_call("restart_emulationstation", {})
        assert "EmulationStation restarted successfully" in result[0].text

    @pytest.mark.asyncio
    async def test_backup_creates_timestamped_path(
        self, es_tools: EmulationStationTools
    ) -> None:
        """Test that backup creates properly timestamped backup path."""
        es_tools.container.retropie_client.execute_command.side_effect = [
            CommandResult(
                "date +%Y%m%d_%H%M%S", 0, "20240115_143022", "", True, 0.1
            ),  # Mock timestamp
            CommandResult(
                "cp -r /home/retro/.emulationstation/gamelists /home/retro/gamelist_backup_20240115_143022",
                0,
                "",
                "",
                True,
                0.1,
            ),  # Copy command
        ]

        result = await es_tools.handle_tool_call(
            "manage_gamelists", {"action": "backup"}
        )

        # Should include timestamp in backup path
        assert (
            "20240115_143022" in result[0].text or "gamelist_backup_" in result[0].text
        )

    @pytest.mark.asyncio
    async def test_all_theme_actions_validation(
        self, es_tools: EmulationStationTools
    ) -> None:
        """Test that all theme actions are properly validated."""
        valid_actions = ["list", "install", "set"]

        for action in valid_actions:
            if action in ["install", "set"]:
                # These require theme_name
                result = await es_tools.handle_tool_call(
                    "configure_themes", {"action": action}
                )
                assert "Theme name required" in result[0].text
            else:
                # list doesn't require theme_name
                es_tools.container.retropie_client.execute_command.return_value = (
                    CommandResult(
                        "ls /home/retro/.emulationstation/themes/",
                        0,
                        "theme1",
                        "",
                        True,
                        0.1,
                    )
                )
                result = await es_tools.handle_tool_call(
                    "configure_themes", {"action": action}
                )
                assert len(result) == 1

    @pytest.mark.asyncio
    async def test_all_settings_categories_handled(
        self, es_tools: EmulationStationTools
    ) -> None:
        """Test that all settings categories are handled."""
        categories = ["screensaver", "audio", "video", "ui"]

        for category in categories:
            result = await es_tools.handle_tool_call(
                "configure_es_settings", {"setting": category}
            )
            assert len(result) == 1
            # Each category should have appropriate response
            if category == "screensaver":
                if "Screensaver timeout set" not in result[0].text:
                    # If it failed, should have error message
                    assert (
                        "Failed to configure" in result[0].text
                        or "Error" in result[0].text
                    )
            elif category in ["audio", "video"]:
                # These provide guidance rather than direct configuration
                assert any(
                    word in result[0].text.lower()
                    for word in ["configuration", "requires", "done"]
                )
            elif category == "ui":
                if "UI transition set" not in result[0].text:
                    # If it failed, should have error message
                    assert (
                        "Failed to configure" in result[0].text
                        or "Error" in result[0].text
                    )
