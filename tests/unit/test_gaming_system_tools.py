"""Unit tests for GamingSystemTools implementation."""

from unittest.mock import Mock

import pytest
from mcp.types import TextContent

from retromcp.config import RetroPieConfig
from retromcp.discovery import RetroPiePaths
from retromcp.domain.models import CommandResult
from retromcp.domain.models import Controller
from retromcp.domain.models import ControllerType
from retromcp.tools.gaming_system_tools import GamingSystemTools


@pytest.mark.unit
@pytest.mark.tools
@pytest.mark.gaming_tools
class TestGamingSystemTools:
    """Test cases for GamingSystemTools class."""

    @pytest.fixture
    def mock_container(self, test_config: RetroPieConfig) -> Mock:
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
    def gaming_system_tools(self, mock_container: Mock) -> GamingSystemTools:
        """Provide GamingSystemTools instance with mocked dependencies."""
        return GamingSystemTools(mock_container)

    # Schema and Tool Structure Tests

    def test_get_tools_returns_single_manage_gaming_tool(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test that get_tools returns exactly one manage_gaming tool."""
        tools = gaming_system_tools.get_tools()

        assert len(tools) == 1
        assert tools[0].name == "manage_gaming"
        assert "gaming system" in tools[0].description.lower()

    def test_manage_gaming_tool_schema_validation(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test that manage_gaming tool has proper schema with all components and actions."""
        tools = gaming_system_tools.get_tools()
        tool = tools[0]

        # Check required properties
        assert "component" in tool.inputSchema["properties"]
        assert "action" in tool.inputSchema["properties"]
        assert tool.inputSchema["required"] == ["component", "action"]

        # Check component enum
        component_enum = tool.inputSchema["properties"]["component"]["enum"]
        expected_components = [
            "retropie",
            "emulationstation",
            "controller",
            "roms",
            "emulator",
            "audio",
            "video",
        ]
        assert set(component_enum) == set(expected_components)

    # RetroPie Component Tests

    @pytest.mark.asyncio
    async def test_manage_gaming_retropie_setup_success(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test RetroPie setup operation."""
        # Mock successful update
        mock_result = CommandResult(
            command="sudo apt-get update && sudo apt-get upgrade -y",
            exit_code=0,
            stdout="RetroPie updated successfully",
            stderr="",
            success=True,
            execution_time=60.0,
        )
        gaming_system_tools.container.update_system_use_case.execute.return_value = (
            mock_result
        )

        # Execute RetroPie setup
        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "retropie",
                "action": "setup",
                "target": "update",
            },
        )

        # Verify result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "updated successfully" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_manage_gaming_retropie_install_emulator(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test RetroPie emulator installation."""
        # Mock successful emulator installation
        mock_result = CommandResult(
            command="sudo ./retropie_setup.sh mupen64plus install",
            exit_code=0,
            stdout="Emulator mupen64plus installed successfully",
            stderr="",
            success=True,
            execution_time=120.0,
        )
        gaming_system_tools.container.install_emulator_use_case.execute.return_value = (
            mock_result
        )

        # Execute emulator installation
        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "retropie",
                "action": "install",
                "target": "emulator",
                "options": {"emulator": "mupen64plus", "system": "n64"},
            },
        )

        # Verify result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "installed successfully" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_manage_gaming_retropie_configure_overclock(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test RetroPie overclock configuration."""
        # Mock successful overclock configuration
        gaming_system_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                command="sudo raspi-config nonint do_overclock Pi4",
                exit_code=0,
                stdout="Overclock configured successfully",
                stderr="",
                success=True,
                execution_time=5.0,
            )
        )

        # Execute overclock configuration
        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "retropie",
                "action": "configure",
                "target": "overclock",
                "options": {"preset": "Pi4"},
            },
        )

        # Verify result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "overclock" in result[0].text.lower()

    # EmulationStation Component Tests

    @pytest.mark.asyncio
    async def test_manage_gaming_emulationstation_restart_success(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test EmulationStation restart operation."""
        # Mock successful restart
        gaming_system_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                command="sudo systemctl restart emulationstation",
                exit_code=0,
                stdout="EmulationStation restarted successfully",
                stderr="",
                success=True,
                execution_time=10.0,
            )
        )

        # Execute EmulationStation restart
        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "emulationstation",
                "action": "restart",
            },
        )

        # Verify result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "restarted successfully" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_manage_gaming_emulationstation_configure_themes(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test EmulationStation theme configuration."""
        # Mock successful theme configuration
        gaming_system_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                command="sudo ./retropie_setup.sh esthemes install_theme carbon",
                exit_code=0,
                stdout="Theme carbon installed successfully",
                stderr="",
                success=True,
                execution_time=30.0,
            )
        )

        # Execute theme configuration
        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "emulationstation",
                "action": "configure",
                "target": "themes",
                "options": {"theme": "carbon", "action": "install"},
            },
        )

        # Verify result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "theme" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_manage_gaming_emulationstation_scan_gamelists(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test EmulationStation gamelist scanning."""
        # Mock successful gamelist operation
        gaming_system_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                command="emulationstation --gamelist-only",
                exit_code=0,
                stdout="Gamelists regenerated successfully",
                stderr="",
                success=True,
                execution_time=45.0,
            )
        )

        # Execute gamelist scanning
        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "emulationstation",
                "action": "scan",
                "target": "gamelists",
            },
        )

        # Verify result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "gamelist" in result[0].text.lower()

    # Controller Component Tests

    @pytest.mark.asyncio
    async def test_manage_gaming_controller_detect_success(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test controller detection."""
        # Mock successful controller detection
        mock_controllers = [
            Controller(
                name="Xbox Controller",
                device_path="/dev/input/js0",
                controller_type=ControllerType.XBOX,
                connected=True,
            ),
            Controller(
                name="PlayStation 4 Controller",
                device_path="/dev/input/js1",
                controller_type=ControllerType.PS4,
                connected=True,
            ),
        ]
        gaming_system_tools.container.detect_controllers_use_case.execute.return_value = mock_controllers

        # Execute controller detection
        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "controller",
                "action": "detect",
            },
        )

        # Verify result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Xbox Controller" in result[0].text
        assert "PlayStation 4 Controller" in result[0].text

    @pytest.mark.asyncio
    async def test_manage_gaming_controller_setup_success(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test controller setup."""
        # Mock successful controller setup
        mock_result = CommandResult(
            command="sudo ./retropie_setup.sh xboxdrv install",
            exit_code=0,
            stdout="Xbox controller driver installed successfully",
            stderr="",
            success=True,
            execution_time=30.0,
        )
        gaming_system_tools.container.setup_controller_use_case.execute.return_value = (
            mock_result
        )

        # Execute controller setup
        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "controller",
                "action": "setup",
                "target": "xbox",
            },
        )

        # Verify result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "controller" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_manage_gaming_controller_test_success(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test controller testing."""
        # Mock successful controller test
        gaming_system_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                command="jstest /dev/input/js0",
                exit_code=0,
                stdout="Controller test completed successfully",
                stderr="",
                success=True,
                execution_time=5.0,
            )
        )

        # Execute controller test
        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "controller",
                "action": "test",
                "target": "js0",
            },
        )

        # Verify result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "test" in result[0].text.lower()

    # ROM Component Tests

    @pytest.mark.asyncio
    async def test_manage_gaming_roms_scan_success(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test ROM scanning."""
        # Mock successful ROM scanning
        mock_roms = [
            {
                "name": "Super Mario 64",
                "path": "/home/retro/RetroPie/roms/n64/mario64.z64",
            },
            {"name": "Zelda OoT", "path": "/home/retro/RetroPie/roms/n64/zelda.z64"},
        ]
        gaming_system_tools.container.list_roms_use_case.execute.return_value = (
            mock_roms
        )

        # Execute ROM scanning
        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "roms",
                "action": "scan",
                "target": "n64",
            },
        )

        # Verify result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Super Mario 64" in result[0].text
        assert "Zelda OoT" in result[0].text

    @pytest.mark.asyncio
    async def test_manage_gaming_roms_configure_permissions(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test ROM permissions configuration."""
        # Mock successful permissions fix
        gaming_system_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                command="sudo chown -R retro:retro /home/retro/RetroPie/roms/",
                exit_code=0,
                stdout="ROM permissions fixed successfully",
                stderr="",
                success=True,
                execution_time=10.0,
            )
        )

        # Execute ROM permissions fix
        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "roms",
                "action": "configure",
                "target": "permissions",
            },
        )

        # Verify result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "permissions" in result[0].text.lower()

    # Audio Component Tests

    @pytest.mark.asyncio
    async def test_manage_gaming_audio_configure_success(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test audio configuration."""
        # Mock successful audio configuration
        gaming_system_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                command="sudo raspi-config nonint do_audio 1",
                exit_code=0,
                stdout="Audio output configured to HDMI",
                stderr="",
                success=True,
                execution_time=5.0,
            )
        )

        # Execute audio configuration
        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "audio",
                "action": "configure",
                "target": "hdmi",
            },
        )

        # Verify result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "audio" in result[0].text.lower()

    # Video Component Tests

    @pytest.mark.asyncio
    async def test_manage_gaming_video_configure_success(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test video configuration."""
        # Mock successful video configuration
        gaming_system_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                command="sudo raspi-config nonint do_resolution 2 82",
                exit_code=0,
                stdout="Video resolution configured to 1920x1080",
                stderr="",
                success=True,
                execution_time=5.0,
            )
        )

        # Execute video configuration
        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "video",
                "action": "configure",
                "target": "resolution",
                "options": {"resolution": "1920x1080"},
            },
        )

        # Verify result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "video" in result[0].text.lower()

    # Error Handling Tests

    @pytest.mark.asyncio
    async def test_invalid_component_error(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test error handling for invalid component."""
        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "invalid_component",
                "action": "test",
            },
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "invalid component" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_invalid_action_error(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test error handling for invalid action."""
        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "controller",
                "action": "invalid_action",
            },
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "invalid action" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_invalid_target_error(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test error handling for invalid target."""
        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "controller",
                "action": "setup",
                "target": "invalid_controller",
            },
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "invalid" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_missing_required_target(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test error handling for missing required target."""
        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "controller",
                "action": "setup",
                # Missing 'target' parameter
            },
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "required" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_handle_unknown_tool(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test handling of unknown tool calls."""
        result = await gaming_system_tools.handle_tool_call(
            "unknown_tool",
            {"test": "value"},
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "unknown tool" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_use_case_integration(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test that use cases are properly integrated."""
        # Mock controller detection use case
        mock_controllers = [
            Controller(
                name="Test Controller",
                device_path="/dev/input/js0",
                controller_type=ControllerType.XBOX,
                connected=True,
            )
        ]
        gaming_system_tools.container.detect_controllers_use_case.execute.return_value = mock_controllers

        # Execute controller detection
        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "controller",
                "action": "detect",
            },
        )

        # Verify use case was called
        gaming_system_tools.container.detect_controllers_use_case.execute.assert_called_once()
        assert len(result) == 1
        assert isinstance(result[0], TextContent)

    def test_inheritance_from_base_tool(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test that GamingSystemTools inherits from BaseTool."""
        from retromcp.tools.base import BaseTool

        assert isinstance(gaming_system_tools, BaseTool)
        assert hasattr(gaming_system_tools, "format_success")
        assert hasattr(gaming_system_tools, "format_error")
        assert hasattr(gaming_system_tools, "format_info")

    # Comprehensive Error Handling Tests

    @pytest.mark.asyncio
    async def test_missing_component_error(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test error handling for missing component."""
        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "action": "test",
                # Missing 'component' parameter
            },
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "component is required" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_missing_action_error(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test error handling for missing action."""
        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "controller",
                # Missing 'action' parameter
            },
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "action is required" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_handle_tool_call_exception(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test exception handling in handle_tool_call."""
        # Mock an exception in _manage_gaming by making the use case throw
        gaming_system_tools.container.detect_controllers_use_case.execute.side_effect = Exception(
            "Test exception"
        )

        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "controller",
                "action": "detect",
            },
        )

        # Should handle exception gracefully
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "controller detection failed" in result[0].text.lower()

    # RetroPie Component Error Tests

    @pytest.mark.asyncio
    async def test_retropie_invalid_actions(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test RetroPie component with invalid actions."""
        invalid_actions = ["invalid_action", "delete", "remove", "test"]

        for action in invalid_actions:
            result = await gaming_system_tools.handle_tool_call(
                "manage_gaming",
                {
                    "component": "retropie",
                    "action": action,
                },
            )

            # Verify error
            assert len(result) == 1
            assert isinstance(result[0], TextContent)
            assert "invalid action" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_retropie_setup_failure(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test RetroPie setup failure scenarios."""
        # Mock failed update
        mock_result = CommandResult(
            command="sudo apt-get update && sudo apt-get upgrade -y",
            exit_code=1,
            stdout="",
            stderr="Update failed",
            success=False,
            execution_time=60.0,
        )
        gaming_system_tools.container.update_system_use_case.execute.return_value = (
            mock_result
        )

        # Execute RetroPie setup
        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "retropie",
                "action": "setup",
                "target": "update",
            },
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "failed" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_retropie_setup_invalid_target(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test RetroPie setup with invalid target."""
        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "retropie",
                "action": "setup",
                "target": "invalid_target",
            },
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "unknown retropie setup target" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_retropie_setup_exception(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test RetroPie setup exception handling."""
        # Mock exception in use case
        gaming_system_tools.container.update_system_use_case.execute.side_effect = (
            Exception("Test exception")
        )

        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "retropie",
                "action": "setup",
                "target": "update",
            },
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "retropie setup failed" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_retropie_install_failure(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test RetroPie installation failure scenarios."""
        # Mock failed installation
        mock_result = CommandResult(
            command="sudo ./retropie_setup.sh mupen64plus install",
            exit_code=1,
            stdout="",
            stderr="Installation failed",
            success=False,
            execution_time=120.0,
        )
        gaming_system_tools.container.install_emulator_use_case.execute.return_value = (
            mock_result
        )

        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "retropie",
                "action": "install",
                "target": "emulator",
                "options": {"emulator": "mupen64plus"},
            },
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "failed" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_retropie_install_missing_emulator(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test RetroPie installation with missing emulator parameter."""
        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "retropie",
                "action": "install",
                "target": "emulator",
                "options": {},  # Missing 'emulator' key
            },
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "emulator name is required" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_retropie_install_invalid_target(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test RetroPie installation with invalid target."""
        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "retropie",
                "action": "install",
                "target": "invalid_target",
            },
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "unknown retropie install target" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_retropie_install_exception(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test RetroPie installation exception handling."""
        # Mock exception in use case
        gaming_system_tools.container.install_emulator_use_case.execute.side_effect = (
            Exception("Test exception")
        )

        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "retropie",
                "action": "install",
                "target": "emulator",
                "options": {"emulator": "mupen64plus"},
            },
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "retropie installation failed" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_retropie_configure_failure(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test RetroPie configuration failure scenarios."""
        # Mock failed configuration
        gaming_system_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                command="sudo raspi-config nonint do_overclock Pi4",
                exit_code=1,
                stdout="",
                stderr="Configuration failed",
                success=False,
                execution_time=5.0,
            )
        )

        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "retropie",
                "action": "configure",
                "target": "overclock",
                "options": {"preset": "Pi4"},
            },
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "failed" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_retropie_configure_invalid_target(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test RetroPie configuration with invalid target."""
        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "retropie",
                "action": "configure",
                "target": "invalid_target",
            },
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "unknown retropie configuration target" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_retropie_configure_exception(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test RetroPie configuration exception handling."""
        # Mock exception in client
        gaming_system_tools.container.retropie_client.execute_command.side_effect = (
            Exception("Test exception")
        )

        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "retropie",
                "action": "configure",
                "target": "overclock",
                "options": {"preset": "Pi4"},
            },
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "retropie configuration failed" in result[0].text.lower()

    # EmulationStation Component Error Tests

    @pytest.mark.asyncio
    async def test_emulationstation_invalid_actions(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test EmulationStation component with invalid actions."""
        invalid_actions = ["invalid_action", "delete", "remove", "test"]

        for action in invalid_actions:
            result = await gaming_system_tools.handle_tool_call(
                "manage_gaming",
                {
                    "component": "emulationstation",
                    "action": action,
                },
            )

            # Verify error
            assert len(result) == 1
            assert isinstance(result[0], TextContent)
            assert "invalid action" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_emulationstation_configure_failure(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test EmulationStation configuration failure scenarios."""
        # Mock failed configuration
        gaming_system_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                command="sudo ./retropie_setup.sh esthemes install_theme carbon",
                exit_code=1,
                stdout="",
                stderr="Theme installation failed",
                success=False,
                execution_time=30.0,
            )
        )

        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "emulationstation",
                "action": "configure",
                "target": "themes",
                "options": {"theme": "carbon", "action": "install"},
            },
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "failed" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_emulationstation_configure_invalid_target(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test EmulationStation configuration with invalid target."""
        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "emulationstation",
                "action": "configure",
                "target": "invalid_target",
            },
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "unknown emulationstation configuration target" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_emulationstation_configure_exception(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test EmulationStation configuration exception handling."""
        # Mock exception in client
        gaming_system_tools.container.retropie_client.execute_command.side_effect = (
            Exception("Test exception")
        )

        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "emulationstation",
                "action": "configure",
                "target": "themes",
                "options": {"theme": "carbon", "action": "install"},
            },
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "emulationstation configuration failed" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_emulationstation_restart_failure(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test EmulationStation restart failure scenarios."""
        # Mock failed restart
        gaming_system_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                command="sudo systemctl restart emulationstation",
                exit_code=1,
                stdout="",
                stderr="Restart failed",
                success=False,
                execution_time=10.0,
            )
        )

        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "emulationstation",
                "action": "restart",
            },
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "failed" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_emulationstation_restart_exception(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test EmulationStation restart exception handling."""
        # Mock exception in client
        gaming_system_tools.container.retropie_client.execute_command.side_effect = (
            Exception("Test exception")
        )

        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "emulationstation",
                "action": "restart",
            },
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "emulationstation restart failed" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_emulationstation_scan_failure(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test EmulationStation scan failure scenarios."""
        # Mock failed scan
        gaming_system_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                command="emulationstation --gamelist-only",
                exit_code=1,
                stdout="",
                stderr="Scan failed",
                success=False,
                execution_time=45.0,
            )
        )

        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "emulationstation",
                "action": "scan",
                "target": "gamelists",
            },
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "failed" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_emulationstation_scan_invalid_target(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test EmulationStation scan with invalid target."""
        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "emulationstation",
                "action": "scan",
                "target": "invalid_target",
            },
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "unknown emulationstation scan target" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_emulationstation_scan_exception(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test EmulationStation scan exception handling."""
        # Mock exception in client
        gaming_system_tools.container.retropie_client.execute_command.side_effect = (
            Exception("Test exception")
        )

        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "emulationstation",
                "action": "scan",
                "target": "gamelists",
            },
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "emulationstation scan failed" in result[0].text.lower()

    # Controller Component Error Tests

    @pytest.mark.asyncio
    async def test_controller_invalid_actions(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test Controller component with invalid actions."""
        invalid_actions = ["invalid_action", "delete", "remove", "install"]

        for action in invalid_actions:
            result = await gaming_system_tools.handle_tool_call(
                "manage_gaming",
                {
                    "component": "controller",
                    "action": action,
                },
            )

            # Verify error
            assert len(result) == 1
            assert isinstance(result[0], TextContent)
            assert "invalid action" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_controller_detect_no_controllers(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test controller detection with no controllers found."""
        # Mock no controllers detected
        gaming_system_tools.container.detect_controllers_use_case.execute.return_value = []

        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "controller",
                "action": "detect",
            },
        )

        # Verify result shows no controllers
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "no controllers detected" in result[0].text.lower()
        assert "troubleshooting" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_controller_detect_exception(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test controller detection exception handling."""
        # Mock exception in use case
        gaming_system_tools.container.detect_controllers_use_case.execute.side_effect = Exception(
            "Test exception"
        )

        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "controller",
                "action": "detect",
            },
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "controller detection failed" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_controller_setup_missing_target(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test controller setup with missing target."""
        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "controller",
                "action": "setup",
                # Missing 'target' parameter
            },
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "controller type is required" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_controller_setup_invalid_type(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test controller setup with invalid controller type."""
        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "controller",
                "action": "setup",
                "target": "invalid_controller_type",
            },
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "invalid controller type" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_controller_setup_failure(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test controller setup failure scenarios."""
        # Mock failed setup
        mock_result = CommandResult(
            command="sudo ./retropie_setup.sh xboxdrv install",
            exit_code=1,
            stdout="",
            stderr="Setup failed",
            success=False,
            execution_time=30.0,
        )
        gaming_system_tools.container.setup_controller_use_case.execute.return_value = (
            mock_result
        )

        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "controller",
                "action": "setup",
                "target": "xbox",
            },
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "failed" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_controller_setup_exception(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test controller setup exception handling."""
        # Mock exception in use case
        gaming_system_tools.container.setup_controller_use_case.execute.side_effect = (
            Exception("Test exception")
        )

        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "controller",
                "action": "setup",
                "target": "xbox",
            },
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "controller setup failed" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_controller_test_missing_target(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test controller test with missing target."""
        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "controller",
                "action": "test",
                # Missing 'target' parameter
            },
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "controller device is required" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_controller_test_failure(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test controller test failure scenarios."""
        # Mock failed test
        gaming_system_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                command="jstest /dev/input/js0 --event",
                exit_code=1,
                stdout="",
                stderr="Test failed",
                success=False,
                execution_time=5.0,
            )
        )

        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "controller",
                "action": "test",
                "target": "js0",
            },
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "failed" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_controller_test_exception(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test controller test exception handling."""
        # Mock exception in client
        gaming_system_tools.container.retropie_client.execute_command.side_effect = (
            Exception("Test exception")
        )

        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "controller",
                "action": "test",
                "target": "js0",
            },
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "controller test failed" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_controller_configure_failure(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test controller configuration failure scenarios."""
        # Mock failed configuration
        gaming_system_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                command="emulationstation --force-input-config",
                exit_code=1,
                stdout="",
                stderr="Configuration failed",
                success=False,
                execution_time=10.0,
            )
        )

        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "controller",
                "action": "configure",
                "target": "mapping",
            },
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "failed" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_controller_configure_invalid_target(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test controller configuration with invalid target."""
        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "controller",
                "action": "configure",
                "target": "invalid_target",
            },
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "unknown controller configuration target" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_controller_configure_exception(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test controller configuration exception handling."""
        # Mock exception in client
        gaming_system_tools.container.retropie_client.execute_command.side_effect = (
            Exception("Test exception")
        )

        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "controller",
                "action": "configure",
                "target": "mapping",
            },
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "controller configuration failed" in result[0].text.lower()

    # Error Message Validation Tests (from test_gaming_system_tools_error_messages.py)

    @pytest.mark.asyncio
    async def test_retropie_setup_invalid_target_shows_valid_options(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test RetroPie setup with invalid target shows valid options."""
        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {"component": "retropie", "action": "setup", "target": "invalid"},
        )

        assert len(result) == 1
        assert "Unknown RetroPie setup target: invalid" in result[0].text
        assert "Valid targets: update" in result[0].text

    @pytest.mark.asyncio
    async def test_controller_setup_no_target_shows_valid_options(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test controller setup without target shows valid options."""
        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming", {"component": "controller", "action": "setup"}
        )

        assert len(result) == 1
        assert "Controller type is required for setup" in result[0].text
        assert "Valid targets: xbox, ps3, ps4, 8bitdo, generic" in result[0].text

    @pytest.mark.asyncio
    async def test_controller_setup_invalid_target_shows_valid_options(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test controller setup with invalid target shows valid options."""
        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {"component": "controller", "action": "setup", "target": "nintendo"},
        )

        assert len(result) == 1
        assert "Invalid controller type: nintendo" in result[0].text
        assert "Valid targets: xbox, ps3, ps4, 8bitdo, generic" in result[0].text

    @pytest.mark.asyncio
    async def test_audio_configure_invalid_target_shows_valid_options(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test audio configure with invalid target shows valid options."""
        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {"component": "audio", "action": "configure", "target": "bluetooth"},
        )

        assert len(result) == 1
        assert "Unknown audio configuration target: bluetooth" in result[0].text
        assert "Valid targets: hdmi, analog" in result[0].text

    @pytest.mark.asyncio
    async def test_roms_scan_no_target_shows_helpful_message(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test ROM scan without target shows helpful message."""
        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming", {"component": "roms", "action": "scan"}
        )

        assert len(result) == 1
        assert "ROM system target is required for scanning" in result[0].text
        assert "Valid targets: nes, snes, genesis, arcade, etc." in result[0].text

    @pytest.mark.asyncio
    async def test_video_configure_invalid_target_shows_valid_options(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test video configure with invalid target shows valid options."""
        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {"component": "video", "action": "configure", "target": "4k"},
        )

        assert len(result) == 1
        assert "Unknown video configuration target: 4k" in result[0].text
        assert "Valid targets: resolution, refresh, crt" in result[0].text

    def test_tool_description_is_helpful(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test that tool description includes component and action information."""
        tools = gaming_system_tools.get_tools()
        assert len(tools) == 1

        tool = tools[0]
        assert "retropie (setup/install/configure)" in tool.description
        assert "controller (detect/setup/test/configure)" in tool.description
        assert "error messages will show valid targets" in tool.description

    def test_target_parameter_description(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test that target parameter description includes examples."""
        tools = gaming_system_tools.get_tools()
        tool = tools[0]

        target_desc = tool.inputSchema["properties"]["target"]["description"]
        assert "controller setup: 'xbox', 'ps3', 'ps4'" in target_desc
        assert "audio configure: 'hdmi', 'analog'" in target_desc
        assert "roms scan: system name (e.g., 'nes', 'arcade')" in target_desc

    # Extended Tests (from test_gaming_system_tools_extended.py)

    @pytest.mark.asyncio
    async def test_roms_scan_no_roms_found(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test ROM scan with no ROMs found."""
        # Mock no ROMs found
        gaming_system_tools.container.list_roms_use_case.execute.return_value = []

        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "roms",
                "action": "scan",
                "target": "n64",
            },
        )

        # Verify result shows no ROMs
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "no n64 roms found" in result[0].text.lower()
        assert "place n64 rom files" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_roms_scan_with_system_filtering(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test ROM scan with system filtering logic."""
        # Mock ROMs with different systems
        mock_roms = [
            {
                "name": "Mario 64",
                "path": "/home/retro/RetroPie/roms/n64/mario64.z64",
                "system": "n64",
            },
            {
                "name": "Sonic",
                "path": "/home/retro/RetroPie/roms/genesis/sonic.gen",
                "system": "genesis",
            },
            {
                "name": "Zelda",
                "path": "/home/retro/RetroPie/roms/n64/zelda.z64",
                # Missing system field - should be inferred from path
            },
        ]
        gaming_system_tools.container.list_roms_use_case.execute.return_value = (
            mock_roms
        )

        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "roms",
                "action": "scan",
                "target": "n64",
            },
        )

        # Verify result shows only N64 ROMs
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "mario 64" in result[0].text.lower()
        assert "zelda" in result[0].text.lower()
        assert "sonic" not in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_roms_list_delegates_to_scan(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test ROM list delegates to scan method."""
        # Mock ROMs
        mock_roms = [
            {
                "name": "Test ROM",
                "path": "/home/retro/RetroPie/roms/n64/test.z64",
                "system": "n64",
            },
        ]
        gaming_system_tools.container.list_roms_use_case.execute.return_value = (
            mock_roms
        )

        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "roms",
                "action": "list",
                "target": "n64",
            },
        )

        # Verify result (should be same as scan)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "test rom" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_emulator_install_delegates_to_retropie(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test emulator install delegates to RetroPie install."""
        # Mock successful emulator installation
        mock_result = CommandResult(
            command="sudo ./retropie_setup.sh lr-mupen64plus install",
            exit_code=0,
            stdout="Emulator lr-mupen64plus installed successfully",
            stderr="",
            success=True,
            execution_time=120.0,
        )
        gaming_system_tools.container.install_emulator_use_case.execute.return_value = (
            mock_result
        )

        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "emulator",
                "action": "install",
                "target": "lr-mupen64plus",
            },
        )

        # Verify result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "installed successfully" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_emulator_configure_not_implemented(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test emulator configure not yet implemented."""
        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "emulator",
                "action": "configure",
                "target": "lr-mupen64plus",
            },
        )

        # Verify info message
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "not yet implemented" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_emulator_test_not_implemented(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test emulator test not yet implemented."""
        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "emulator",
                "action": "test",
                "target": "lr-mupen64plus",
            },
        )

        # Verify info message
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "not yet implemented" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_audio_configure_analog_success(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test audio analog configuration success."""
        # Mock successful configuration
        gaming_system_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                command="sudo raspi-config nonint do_audio 1",
                exit_code=0,
                stdout="Audio configured to analog",
                stderr="",
                success=True,
                execution_time=5.0,
            )
        )

        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "audio",
                "action": "configure",
                "target": "analog",
            },
        )

        # Verify success
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "analog" in result[0].text.lower()
        assert "3.5mm" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_audio_test_not_implemented(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test audio test not yet implemented."""
        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "audio",
                "action": "test",
                "target": "hdmi",
            },
        )

        # Verify info message
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "not yet implemented" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_video_configure_supported_resolutions(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test video configuration with all supported resolutions."""
        supported_resolutions = ["1920x1080", "1280x720", "1024x768", "800x600"]

        for resolution in supported_resolutions:
            # Mock successful configuration
            gaming_system_tools.container.retropie_client.execute_command.return_value = CommandResult(
                command="sudo raspi-config nonint do_resolution 2 82",
                exit_code=0,
                stdout=f"Resolution set to {resolution}",
                stderr="",
                success=True,
                execution_time=5.0,
            )

            result = await gaming_system_tools.handle_tool_call(
                "manage_gaming",
                {
                    "component": "video",
                    "action": "configure",
                    "target": "resolution",
                    "options": {"resolution": resolution},
                },
            )

            # Verify success
            assert len(result) == 1
            assert isinstance(result[0], TextContent)
            assert resolution in result[0].text.lower()
            assert "reboot required" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_video_configure_unsupported_resolution(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test video configuration with unsupported resolution."""
        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "video",
                "action": "configure",
                "target": "resolution",
                "options": {"resolution": "4096x2160"},
            },
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "unsupported resolution" in result[0].text.lower()
        assert "1920x1080" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_video_test_not_implemented(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test video test not yet implemented."""
        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "video",
                "action": "test",
                "target": "resolution",
            },
        )

        # Verify info message
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "not yet implemented" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_controller_test_device_path_handling(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test controller test with different device path formats."""
        # Mock successful test
        gaming_system_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                command="jstest /dev/input/js0 --event",
                exit_code=0,
                stdout="Controller test successful",
                stderr="",
                success=True,
                execution_time=5.0,
            )
        )

        # Test with full device path
        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "controller",
                "action": "test",
                "target": "/dev/input/js0",
            },
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "test completed" in result[0].text.lower()

        # Test with short device name
        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "controller",
                "action": "test",
                "target": "js0",
            },
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "test completed" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_controller_configure_mapping_success(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test controller configuration mapping success path."""
        # Mock successful configuration
        gaming_system_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                command="emulationstation --force-input-config",
                exit_code=0,
                stdout="Configuration started",
                stderr="",
                success=True,
                execution_time=10.0,
            )
        )

        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "controller",
                "action": "configure",
                "target": "mapping",
            },
        )

        # Verify success
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "controller mapping configuration started" in result[0].text.lower()
        assert "follow the on-screen prompts" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_roms_scan_with_none_roms(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test ROM scan when use case returns None."""
        # Mock None return
        gaming_system_tools.container.list_roms_use_case.execute.return_value = None

        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "roms",
                "action": "scan",
                "target": "n64",
            },
        )

        # Verify result shows no ROMs
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "no n64 roms found" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_roms_scan_with_non_list_roms(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test ROM scan when use case returns non-list data."""
        # Mock non-list return
        gaming_system_tools.container.list_roms_use_case.execute.return_value = (
            "not a list"
        )

        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "roms",
                "action": "scan",
                "target": "n64",
            },
        )

        # Verify result shows no ROMs
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "no n64 roms found" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_roms_scan_with_missing_name_or_path(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test ROM scan with ROMs missing name or path fields."""
        # Mock ROM data with missing fields
        mock_roms = [
            {
                "name": "Game 1",
                # Missing path
                "system": "nes",
            },
            {
                # Missing name
                "path": "/home/retro/RetroPie/roms/nes/game2.nes",
                "system": "nes",
            },
            {
                "name": "Game 3",
                "path": "/home/retro/RetroPie/roms/nes/game3.nes",
                "system": "nes",
            },
        ]
        gaming_system_tools.container.list_roms_use_case.execute.return_value = (
            mock_roms
        )

        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "roms",
                "action": "scan",
                "target": "nes",
            },
        )

        # Verify result shows ROMs with "Unknown" for missing fields
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "unknown" in result[0].text.lower()  # Should appear for missing fields
