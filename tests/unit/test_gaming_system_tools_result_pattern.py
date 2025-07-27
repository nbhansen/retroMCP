"""Test Result pattern implementation for GamingSystemTools."""

from unittest.mock import Mock

import pytest
from mcp.types import TextContent

from retromcp.config import RetroPieConfig
from retromcp.discovery import RetroPiePaths
from retromcp.domain.models import CommandResult
from retromcp.domain.models import Controller
from retromcp.domain.models import ControllerType
from retromcp.domain.models import DomainError
from retromcp.domain.models import Result
from retromcp.domain.models import RomDirectory
from retromcp.tools.gaming_system_tools import GamingSystemTools


@pytest.mark.unit
@pytest.mark.tools
@pytest.mark.gaming_tools
class TestGamingSystemToolsResultPattern:
    """Test Result pattern implementation in GamingSystemTools."""

    @pytest.fixture
    def mock_container(self, test_config: RetroPieConfig) -> Mock:
        """Provide mocked container with Result pattern support."""
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

    # RetroPie Component - Result Pattern Tests

    @pytest.mark.asyncio
    async def test_retropie_setup_success_result_pattern(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test RetroPie setup with successful Result pattern."""
        # Mock successful update with Result.success
        mock_result = CommandResult(
            command="sudo apt-get update && sudo apt-get upgrade -y",
            exit_code=0,
            stdout="RetroPie updated successfully",
            stderr="",
            success=True,
            execution_time=60.0,
        )
        gaming_system_tools.container.update_system_use_case.execute.return_value = (
            Result.success(mock_result)
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
    async def test_retropie_setup_error_result_pattern(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test RetroPie setup with error Result pattern."""
        # Mock failed update with Result.error
        error = DomainError(
            code="UPDATE_FAILED",
            message="Update failed",
            details={"reason": "Network error"},
        )
        gaming_system_tools.container.update_system_use_case.execute.return_value = (
            Result.error(error)
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

        # Verify error result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "system update failed" in result[0].text.lower()
        assert "update failed" in result[0].text

    @pytest.mark.asyncio
    async def test_retropie_install_success_result_pattern(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test RetroPie emulator installation with successful Result pattern."""
        # Mock successful installation with Result.success
        mock_result = CommandResult(
            command="sudo ./retropie_setup.sh mupen64plus install",
            exit_code=0,
            stdout="Emulator mupen64plus installed successfully",
            stderr="",
            success=True,
            execution_time=120.0,
        )
        gaming_system_tools.container.install_emulator_use_case.execute.return_value = (
            Result.success(mock_result)
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
    async def test_retropie_install_error_result_pattern(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test RetroPie emulator installation with error Result pattern."""
        # Mock failed installation with Result.error
        error = DomainError(
            code="INSTALL_FAILED",
            message="Installation failed",
            details={"reason": "Dependency error"},
        )
        gaming_system_tools.container.install_emulator_use_case.execute.return_value = (
            Result.error(error)
        )

        # Execute emulator installation
        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "retropie",
                "action": "install",
                "target": "emulator",
                "options": {"emulator": "mupen64plus"},
            },
        )

        # Verify error result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "emulator installation failed" in result[0].text.lower()
        assert "installation failed" in result[0].text

    # Controller Component - Result Pattern Tests

    @pytest.mark.asyncio
    async def test_controller_detect_success_result_pattern(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test controller detection with successful Result pattern."""
        # Mock successful controller detection with Result.success
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
        gaming_system_tools.container.detect_controllers_use_case.execute.return_value = Result.success(
            mock_controllers
        )

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
    async def test_controller_detect_error_result_pattern(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test controller detection with error Result pattern."""
        # Mock failed detection with Result.error
        error = DomainError(
            code="DETECT_FAILED",
            message="Detection failed",
            details={"reason": "USB error"},
        )
        gaming_system_tools.container.detect_controllers_use_case.execute.return_value = Result.error(
            error
        )

        # Execute controller detection
        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "controller",
                "action": "detect",
            },
        )

        # Verify error result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "controller detection failed" in result[0].text.lower()
        assert "detection failed" in result[0].text

    @pytest.mark.asyncio
    async def test_controller_setup_success_result_pattern(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test controller setup with successful Result pattern."""
        # Mock successful setup with Result.success
        mock_result = CommandResult(
            command="sudo ./retropie_setup.sh xboxdrv install",
            exit_code=0,
            stdout="Xbox controller driver installed successfully",
            stderr="",
            success=True,
            execution_time=30.0,
        )
        gaming_system_tools.container.setup_controller_use_case.execute.return_value = (
            Result.success(mock_result)
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
        assert "controller setup completed successfully" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_controller_setup_error_result_pattern(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test controller setup with error Result pattern."""
        # Mock failed setup with Result.error
        error = DomainError(
            code="SETUP_FAILED",
            message="Setup failed",
            details={"reason": "Driver error"},
        )
        gaming_system_tools.container.setup_controller_use_case.execute.return_value = (
            Result.error(error)
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

        # Verify error result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "controller setup failed" in result[0].text.lower()
        assert "setup failed" in result[0].text

    # ROM Component - Result Pattern Tests

    @pytest.mark.asyncio
    async def test_roms_scan_success_result_pattern(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test ROM scanning with successful Result pattern."""
        # Mock successful ROM scanning with Result.success
        mock_roms = [
            {
                "name": "Super Mario 64",
                "path": "/home/retro/RetroPie/roms/n64/mario64.z64",
                "system": "n64",
            },
            {
                "name": "Zelda OoT",
                "path": "/home/retro/RetroPie/roms/n64/zelda.z64",
                "system": "n64",
            },
        ]
        gaming_system_tools.container.list_roms_use_case.execute.return_value = (
            Result.success(mock_roms)
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
    async def test_roms_scan_error_result_pattern(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test ROM scanning with error Result pattern."""
        # Mock failed scanning with Result.error
        error = DomainError(
            code="SCAN_FAILED",
            message="Scan failed",
            details={"reason": "Directory not accessible"},
        )
        gaming_system_tools.container.list_roms_use_case.execute.return_value = (
            Result.error(error)
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

        # Verify error result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "rom scan failed" in result[0].text.lower()
        assert "scan failed" in result[0].text

    # Missing Coverage Tests - Error Paths and Edge Cases

    @pytest.mark.asyncio
    async def test_get_valid_targets_no_targets_required(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test _get_valid_targets_message for actions with no targets required."""
        # Test EmulationStation restart (no target required)
        message = gaming_system_tools._get_valid_targets_message(
            "emulationstation", "restart"
        )
        assert "No target required for this action" in message

    @pytest.mark.asyncio
    async def test_get_valid_targets_dynamic_targets(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test _get_valid_targets_message for dynamic target types."""
        # Test ROM scan with system name
        message = gaming_system_tools._get_valid_targets_message("roms", "scan")
        assert "nes, snes, genesis, arcade" in message

        # Test emulator install with emulator name
        message = gaming_system_tools._get_valid_targets_message("emulator", "install")
        assert "lr-mame2003, lr-snes9x" in message

    @pytest.mark.asyncio
    async def test_get_valid_targets_no_valid_targets(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test _get_valid_targets_message for invalid component/action."""
        message = gaming_system_tools._get_valid_targets_message("invalid", "invalid")
        assert "No valid targets found" in message

    @pytest.mark.asyncio
    async def test_roms_scan_all_systems(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test ROM scanning for all systems."""
        # Mock ROM data with multiple systems
        mock_roms = [
            RomDirectory(
                system="nes",
                path="/roms/nes",
                rom_count=5,
                total_size=1024,
                supported_extensions=[".nes"],
            ),
            RomDirectory(
                system="snes",
                path="/roms/snes",
                rom_count=3,
                total_size=2048,
                supported_extensions=[".sfc"],
            ),
        ]
        gaming_system_tools.container.list_roms_use_case.execute.return_value = (
            Result.success(mock_roms)
        )

        # Execute ROM scanning for all systems
        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "roms",
                "action": "scan",
                "target": "all",
            },
        )

        # Verify result shows all systems
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "nes" in result[0].text.lower()
        assert "snes" in result[0].text.lower()
        assert "ROM Count:" in result[0].text

    @pytest.mark.asyncio
    async def test_emulator_configure_not_implemented(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test emulator configure action (not yet implemented)."""
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
        """Test emulator test action (not yet implemented)."""
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
    async def test_audio_test_not_implemented(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test audio test action (not yet implemented)."""
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
    async def test_video_test_not_implemented(
        self, gaming_system_tools: GamingSystemTools
    ) -> None:
        """Test video test action (not yet implemented)."""
        result = await gaming_system_tools.handle_tool_call(
            "manage_gaming",
            {
                "component": "video",
                "action": "test",
                "target": "current",
            },
        )

        # Verify info message
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "not yet implemented" in result[0].text.lower()
