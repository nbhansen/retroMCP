"""Unit tests for gaming system tools error messages and validation."""

from unittest.mock import Mock

import pytest

from retromcp.config import RetroPieConfig
from retromcp.discovery import RetroPiePaths
from retromcp.tools.gaming_system_tools import GamingSystemTools


class TestGamingSystemToolsErrorMessages:
    """Test error messages provide helpful information about valid targets."""

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
            host="test-pi.local",
            username="retro",
            password="test_password",
            paths=paths,
        )

    @pytest.fixture
    def local_mock_container(self, test_config: RetroPieConfig) -> Mock:
        """Provide mocked container."""
        mock = Mock()
        mock.retropie_client = Mock()
        mock.retropie_client.execute_command = Mock()
        mock.config = test_config

        # Mock use cases
        mock.detect_controllers_use_case = Mock()
        mock.setup_controller_use_case = Mock()
        mock.install_emulator_use_case = Mock()
        mock.list_roms_use_case = Mock()
        mock.update_system_use_case = Mock()

        return mock

    @pytest.fixture
    def gaming_tools(self, local_mock_container: Mock) -> GamingSystemTools:
        """Create gaming system tools instance."""
        return GamingSystemTools(local_mock_container)

    @pytest.mark.asyncio
    async def test_retropie_setup_invalid_target(self, gaming_tools: GamingSystemTools) -> None:
        """Test RetroPie setup with invalid target shows valid options."""
        result = await gaming_tools.handle_tool_call(
            "manage_gaming",
            {"component": "retropie", "action": "setup", "target": "invalid"}
        )

        assert len(result) == 1
        assert "Unknown RetroPie setup target: invalid" in result[0].text
        assert "Valid targets: update" in result[0].text

    @pytest.mark.asyncio
    async def test_controller_setup_no_target(self, gaming_tools: GamingSystemTools) -> None:
        """Test controller setup without target shows valid options."""
        result = await gaming_tools.handle_tool_call(
            "manage_gaming",
            {"component": "controller", "action": "setup"}
        )

        assert len(result) == 1
        assert "Controller type is required for setup" in result[0].text
        assert "Valid targets: xbox, ps3, ps4, 8bitdo, generic" in result[0].text

    @pytest.mark.asyncio
    async def test_controller_setup_invalid_target(self, gaming_tools: GamingSystemTools) -> None:
        """Test controller setup with invalid target shows valid options."""
        result = await gaming_tools.handle_tool_call(
            "manage_gaming",
            {"component": "controller", "action": "setup", "target": "nintendo"}
        )

        assert len(result) == 1
        assert "Invalid controller type: nintendo" in result[0].text
        assert "Valid targets: xbox, ps3, ps4, 8bitdo, generic" in result[0].text

    @pytest.mark.asyncio
    async def test_audio_configure_invalid_target(self, gaming_tools: GamingSystemTools) -> None:
        """Test audio configure with invalid target shows valid options."""
        result = await gaming_tools.handle_tool_call(
            "manage_gaming",
            {"component": "audio", "action": "configure", "target": "bluetooth"}
        )

        assert len(result) == 1
        assert "Unknown audio configuration target: bluetooth" in result[0].text
        assert "Valid targets: hdmi, analog" in result[0].text

    @pytest.mark.asyncio
    async def test_roms_scan_no_target(self, gaming_tools: GamingSystemTools) -> None:
        """Test ROM scan without target shows helpful message."""
        result = await gaming_tools.handle_tool_call(
            "manage_gaming",
            {"component": "roms", "action": "scan"}
        )

        assert len(result) == 1
        assert "ROM system target is required for scanning" in result[0].text
        assert "Valid targets: nes, snes, genesis, arcade, etc." in result[0].text

    @pytest.mark.asyncio
    async def test_emulationstation_restart_no_target(self, gaming_tools: GamingSystemTools) -> None:
        """Test EmulationStation restart doesn't require target."""
        # Mock the restart method to avoid actual execution
        gaming_tools.container.retropie_client.execute_command.return_value.success = True
        gaming_tools.container.retropie_client.execute_command.return_value.stdout = "Restarted"

        result = await gaming_tools.handle_tool_call(
            "manage_gaming",
            {"component": "emulationstation", "action": "restart"}
        )

        assert len(result) == 1
        assert "EmulationStation restarted successfully" in result[0].text

    @pytest.mark.asyncio
    async def test_video_configure_invalid_target(self, gaming_tools: GamingSystemTools) -> None:
        """Test video configure with invalid target shows valid options."""
        result = await gaming_tools.handle_tool_call(
            "manage_gaming",
            {"component": "video", "action": "configure", "target": "4k"}
        )

        assert len(result) == 1
        assert "Unknown video configuration target: 4k" in result[0].text
        assert "Valid targets: resolution, refresh, crt" in result[0].text

    @pytest.mark.asyncio
    async def test_tool_description_is_helpful(self, gaming_tools: GamingSystemTools) -> None:
        """Test that tool description includes component and action information."""
        tools = gaming_tools.get_tools()
        assert len(tools) == 1

        tool = tools[0]
        assert "retropie (setup/install/configure)" in tool.description
        assert "controller (detect/setup/test/configure)" in tool.description
        assert "error messages will show valid targets" in tool.description

    @pytest.mark.asyncio
    async def test_target_parameter_description(self, gaming_tools: GamingSystemTools) -> None:
        """Test that target parameter description includes examples."""
        tools = gaming_tools.get_tools()
        tool = tools[0]

        target_desc = tool.inputSchema["properties"]["target"]["description"]
        assert "controller setup: 'xbox', 'ps3', 'ps4'" in target_desc
        assert "audio configure: 'hdmi', 'analog'" in target_desc
        assert "roms scan: system name (e.g., 'nes', 'arcade')" in target_desc
