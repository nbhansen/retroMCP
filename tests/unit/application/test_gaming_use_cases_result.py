"""Tests for Result pattern conversion in gaming use cases.

Following TDD approach - these tests will initially fail until use cases handle Result types.
"""

from unittest.mock import Mock

from retromcp.application.gaming_use_cases import DetectControllersUseCase
from retromcp.application.gaming_use_cases import InstallEmulatorUseCase
from retromcp.application.gaming_use_cases import ListRomsUseCase
from retromcp.application.gaming_use_cases import SetupControllerUseCase
from retromcp.domain.models import CommandResult
from retromcp.domain.models import ConnectionError
from retromcp.domain.models import Controller
from retromcp.domain.models import ControllerType
from retromcp.domain.models import Emulator
from retromcp.domain.models import EmulatorStatus
from retromcp.domain.models import ExecutionError
from retromcp.domain.models import Result
from retromcp.domain.models import RomDirectory
from retromcp.domain.models import ValidationError
from retromcp.domain.ports import ControllerRepository
from retromcp.domain.ports import EmulatorRepository


class TestDetectControllersUseCaseResult:
    """Test Result pattern conversion in DetectControllersUseCase."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_controller_repo = Mock(spec=ControllerRepository)
        self.use_case = DetectControllersUseCase(self.mock_controller_repo)

    def test_execute_returns_result_success_when_controllers_detected(self):
        """Test that execute returns Result.success when controllers are detected successfully."""
        # Arrange
        controllers = [
            Controller(
                name="Xbox Controller",
                device_path="/dev/input/js0",
                controller_type=ControllerType.XBOX,
                connected=True,
                vendor_id="045e",
                product_id="02ea",
            ),
            Controller(
                name="PlayStation Controller",
                device_path="/dev/input/js1",
                controller_type=ControllerType.PS4,
                connected=True,
                vendor_id="054c",
                product_id="0ce6",
            ),
        ]
        self.mock_controller_repo.detect_controllers.return_value = controllers

        # Act
        result = self.use_case.execute()

        # Assert
        assert isinstance(result, Result)
        assert result.is_success()
        assert not result.is_error()
        assert isinstance(result.value, list)
        assert len(result.value) == 2
        assert all(isinstance(controller, Controller) for controller in result.value)
        assert result.value[0].name == "Xbox Controller"
        assert result.value[1].controller_type == ControllerType.PS4

    def test_execute_returns_result_success_when_no_controllers_found(self):
        """Test that execute returns Result.success with empty list when no controllers found."""
        # Arrange
        self.mock_controller_repo.detect_controllers.return_value = []

        # Act
        result = self.use_case.execute()

        # Assert
        assert isinstance(result, Result)
        assert result.is_success()
        assert not result.is_error()
        assert isinstance(result.value, list)
        assert len(result.value) == 0

    def test_execute_returns_result_error_when_detection_fails(self):
        """Test that execute returns Result.error when controller detection fails."""
        # Arrange
        # Mock detect_controllers to raise Python exception
        self.mock_controller_repo.detect_controllers.side_effect = OSError(
            "Unable to access USB controller interface"
        )

        # Act
        result = self.use_case.execute()

        # Assert
        assert isinstance(result, Result)
        assert not result.is_success()
        assert result.is_error()
        assert isinstance(result.error_or_none, ConnectionError)
        assert result.error_or_none.code == "CONTROLLER_CONNECTION_FAILED"
        assert (
            "Failed to connect to controller interface" in result.error_or_none.message
        )


class TestSetupControllerUseCaseResult:
    """Test Result pattern conversion in SetupControllerUseCase."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_controller_repo = Mock(spec=ControllerRepository)
        self.use_case = SetupControllerUseCase(self.mock_controller_repo)

    def test_execute_returns_result_success_when_controller_setup_succeeds(self):
        """Test that execute returns Result.success when controller setup succeeds."""
        # Arrange
        controller_device_path = "/dev/input/js0"
        driver_path = "/opt/retropie/configs/all/controllers/xbox.cfg"

        # Mock detect_controllers to return available controllers
        available_controllers = [
            Controller(
                name="Xbox Controller",
                device_path="/dev/input/js0",
                controller_type=ControllerType.XBOX,
                connected=True,
                vendor_id="045e",
                product_id="02ea",
            )
        ]
        self.mock_controller_repo.detect_controllers.return_value = (
            available_controllers
        )

        # Mock setup_controller to return success result
        setup_result = CommandResult(
            command="sudo /opt/retropie/scripts/retropie_setup.sh configure_controller",
            exit_code=0,
            stdout="Controller configured successfully",
            stderr="",
            success=True,
            execution_time=2.5,
        )
        self.mock_controller_repo.setup_controller.return_value = setup_result

        # Act
        result = self.use_case.execute(controller_device_path, driver_path)

        # Assert
        assert isinstance(result, Result)
        assert result.is_success()
        assert not result.is_error()
        assert isinstance(result.value, CommandResult)
        assert result.value.success is True
        assert "Controller configured successfully" in result.value.stdout

    def test_execute_returns_result_error_when_controller_not_found(self):
        """Test that execute returns Result.error when controller ID not found."""
        # Arrange
        controller_device_path = "/dev/input/js99"

        # Mock detect_controllers to return empty list
        self.mock_controller_repo.detect_controllers.return_value = []

        # Act
        result = self.use_case.execute(controller_device_path)

        # Assert
        assert isinstance(result, Result)
        assert not result.is_success()
        assert result.is_error()
        assert isinstance(result.error_or_none, ValidationError)
        assert result.error_or_none.code == "CONTROLLER_NOT_FOUND"
        assert "/dev/input/js99" in result.error_or_none.message

    def test_execute_returns_result_error_when_detection_fails(self):
        """Test that execute returns Result.error when controller detection fails."""
        # Arrange
        controller_device_path = "/dev/input/js0"

        # Mock detect_controllers to raise Python exception
        self.mock_controller_repo.detect_controllers.side_effect = OSError(
            "Failed to scan for controllers"
        )

        # Act
        result = self.use_case.execute(controller_device_path)

        # Assert
        assert isinstance(result, Result)
        assert not result.is_success()
        assert result.is_error()
        assert isinstance(result.error_or_none, ConnectionError)
        assert result.error_or_none.code == "CONTROLLER_CONNECTION_FAILED"

    def test_execute_returns_result_error_when_setup_fails(self):
        """Test that execute returns Result.error when controller setup fails."""
        # Arrange
        controller_device_path = "/dev/input/js0"

        # Mock detect_controllers to return available controllers
        available_controllers = [
            Controller(
                name="Xbox Controller",
                device_path="/dev/input/js0",
                controller_type=ControllerType.XBOX,
                connected=True,
                vendor_id="045e",
                product_id="02ea",
            )
        ]
        self.mock_controller_repo.detect_controllers.return_value = (
            available_controllers
        )

        # Mock setup_controller to raise exception
        # Mock setup_controller to raise Python exception
        self.mock_controller_repo.setup_controller.side_effect = RuntimeError(
            "Failed to configure controller drivers"
        )

        # Act
        result = self.use_case.execute(controller_device_path)

        # Assert
        assert isinstance(result, Result)
        assert not result.is_success()
        assert result.is_error()
        assert isinstance(result.error_or_none, ExecutionError)
        assert result.error_or_none.code == "CONTROLLER_SETUP_FAILED"


class TestInstallEmulatorUseCaseResult:
    """Test Result pattern conversion in InstallEmulatorUseCase."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_emulator_repo = Mock(spec=EmulatorRepository)
        self.use_case = InstallEmulatorUseCase(self.mock_emulator_repo)

    def test_execute_returns_result_success_when_emulator_installed(self):
        """Test that execute returns Result.success when emulator is installed successfully."""
        # Arrange
        emulator_name = "mupen64plus"

        # Mock get_emulators to return available emulators including the target
        available_emulators = [
            Emulator(name="mupen64plus", system="n64", status=EmulatorStatus.INSTALLED),
            Emulator(
                name="pcsx-rearmed", system="psx", status=EmulatorStatus.INSTALLED
            ),
        ]
        self.mock_emulator_repo.get_emulators.return_value = available_emulators

        # Mock install_emulator to return success result
        install_result = CommandResult(
            command="sudo apt-get install mupen64plus",
            exit_code=0,
            stdout="Emulator installed successfully",
            stderr="",
            success=True,
            execution_time=45.0,
        )
        self.mock_emulator_repo.install_emulator.return_value = install_result

        # Act
        result = self.use_case.execute(emulator_name)

        # Assert
        assert isinstance(result, Result)
        assert result.is_success()
        assert not result.is_error()
        assert isinstance(result.value, CommandResult)
        assert result.value.success is True
        assert "Emulator installed successfully" in result.value.stdout

    def test_execute_returns_result_error_when_emulator_name_empty(self):
        """Test that execute returns Result.error when emulator name is empty."""
        # Arrange
        emulator_name = ""

        # Act
        result = self.use_case.execute(emulator_name)

        # Assert
        assert isinstance(result, Result)
        assert not result.is_success()
        assert result.is_error()
        assert isinstance(result.error_or_none, ValidationError)
        assert result.error_or_none.code == "INVALID_EMULATOR_NAME"
        assert "cannot be empty" in result.error_or_none.message

    def test_execute_returns_result_error_when_emulator_not_available(self):
        """Test that execute returns Result.error when emulator is not available."""
        # Arrange
        emulator_name = "invalid-emulator"

        # Mock get_emulators to return available emulators NOT including the target
        available_emulators = [
            Emulator(name="mupen64plus", system="n64", status=EmulatorStatus.INSTALLED),
            Emulator(
                name="pcsx-rearmed", system="psx", status=EmulatorStatus.INSTALLED
            ),
        ]
        self.mock_emulator_repo.get_emulators.return_value = available_emulators

        # Act
        result = self.use_case.execute(emulator_name)

        # Assert
        assert isinstance(result, Result)
        assert not result.is_success()
        assert result.is_error()
        assert isinstance(result.error_or_none, ValidationError)
        assert result.error_or_none.code == "EMULATOR_NOT_AVAILABLE"
        assert "invalid-emulator" in result.error_or_none.message

    def test_execute_returns_result_error_when_get_emulators_fails(self):
        """Test that execute returns Result.error when getting emulators list fails."""
        # Arrange
        emulator_name = "mupen64plus"

        # Mock get_emulators to raise a Python exception
        self.mock_emulator_repo.get_emulators.side_effect = OSError(
            "Failed to connect to RetroPie system"
        )

        # Act
        result = self.use_case.execute(emulator_name)

        # Assert
        assert isinstance(result, Result)
        assert not result.is_success()
        assert result.is_error()
        assert isinstance(result.error_or_none, ConnectionError)
        assert result.error_or_none.code == "EMULATOR_CONNECTION_FAILED"

    def test_execute_returns_result_error_when_installation_fails(self):
        """Test that execute returns Result.error when emulator installation fails."""
        # Arrange
        emulator_name = "mupen64plus"

        # Mock get_emulators to return available emulators including the target
        available_emulators = [
            Emulator(name="mupen64plus", system="n64", status=EmulatorStatus.INSTALLED),
            Emulator(
                name="pcsx-rearmed", system="psx", status=EmulatorStatus.INSTALLED
            ),
        ]
        self.mock_emulator_repo.get_emulators.return_value = available_emulators

        # Mock install_emulator to raise an exception
        self.mock_emulator_repo.install_emulator.side_effect = Exception(
            "Installation failed"
        )

        # Act
        result = self.use_case.execute(emulator_name)

        # Assert
        assert isinstance(result, Result)
        assert not result.is_success()
        assert result.is_error()
        assert isinstance(result.error_or_none, ExecutionError)
        assert result.error_or_none.code == "EMULATOR_INSTALL_FAILED"


class TestListRomsUseCaseResult:
    """Test Result pattern conversion in ListRomsUseCase."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_emulator_repo = Mock(spec=EmulatorRepository)
        self.use_case = ListRomsUseCase(self.mock_emulator_repo)

    def test_execute_returns_result_success_when_roms_listed(self):
        """Test that execute returns Result.success when ROM directories are listed successfully."""
        # Arrange
        rom_directories = [
            RomDirectory(
                system="nes",
                path="/home/pi/RetroPie/roms/nes",
                rom_count=150,
                total_size=2048000,
                supported_extensions=[".nes", ".zip"],
            ),
            RomDirectory(
                system="snes",
                path="/home/pi/RetroPie/roms/snes",
                rom_count=89,
                total_size=4096000,
                supported_extensions=[".sfc", ".smc", ".zip"],
            ),
            RomDirectory(
                system="n64",
                path="/home/pi/RetroPie/roms/n64",
                rom_count=12,
                total_size=8192000,
                supported_extensions=[".n64", ".z64", ".v64"],
            ),
        ]
        self.mock_emulator_repo.get_rom_directories.return_value = rom_directories

        # Act
        result = self.use_case.execute()

        # Assert
        assert isinstance(result, Result)
        assert result.is_success()
        assert not result.is_error()
        assert isinstance(result.value, list)
        assert len(result.value) == 3
        assert all(isinstance(rom_dir, RomDirectory) for rom_dir in result.value)
        # Should be sorted by ROM count descending
        assert result.value[0].rom_count == 150  # nes
        assert result.value[1].rom_count == 89  # snes
        assert result.value[2].rom_count == 12  # n64

    def test_execute_returns_result_success_with_system_filter(self):
        """Test that execute returns Result.success with system filtering applied."""
        # Arrange
        rom_directories = [
            RomDirectory(
                system="nes",
                path="/home/pi/RetroPie/roms/nes",
                rom_count=150,
                total_size=2048000,
                supported_extensions=[".nes", ".zip"],
            ),
            RomDirectory(
                system="snes",
                path="/home/pi/RetroPie/roms/snes",
                rom_count=89,
                total_size=4096000,
                supported_extensions=[".sfc", ".smc", ".zip"],
            ),
        ]
        self.mock_emulator_repo.get_rom_directories.return_value = rom_directories

        # Act
        result = self.use_case.execute(system_filter="nes")

        # Assert
        assert isinstance(result, Result)
        assert result.is_success()
        assert isinstance(result.value, list)
        assert len(result.value) == 1
        assert result.value[0].system == "nes"
        assert result.value[0].rom_count == 150

    def test_execute_returns_result_success_with_min_rom_count_filter(self):
        """Test that execute returns Result.success with minimum ROM count filtering."""
        # Arrange
        rom_directories = [
            RomDirectory(
                system="nes",
                path="/home/pi/RetroPie/roms/nes",
                rom_count=150,
                total_size=2048000,
                supported_extensions=[".nes", ".zip"],
            ),
            RomDirectory(
                system="n64",
                path="/home/pi/RetroPie/roms/n64",
                rom_count=12,
                total_size=8192000,
                supported_extensions=[".n64", ".z64", ".v64"],
            ),
        ]
        self.mock_emulator_repo.get_rom_directories.return_value = rom_directories

        # Act
        result = self.use_case.execute(min_rom_count=50)

        # Assert
        assert isinstance(result, Result)
        assert result.is_success()
        assert isinstance(result.value, list)
        assert len(result.value) == 1
        assert result.value[0].system == "nes"
        assert result.value[0].rom_count == 150

    def test_execute_returns_result_error_when_rom_listing_fails(self):
        """Test that execute returns Result.error when ROM directory listing fails."""
        # Arrange
        # Mock get_rom_directories to raise Python exception
        self.mock_emulator_repo.get_rom_directories.side_effect = PermissionError(
            "Failed to access ROM directories"
        )

        # Act
        result = self.use_case.execute()

        # Assert
        assert isinstance(result, Result)
        assert not result.is_success()
        assert result.is_error()
        assert isinstance(result.error_or_none, ConnectionError)
        assert result.error_or_none.code == "ROM_ACCESS_FAILED"
        assert "Failed to access ROM directories" in result.error_or_none.message

    def test_execute_returns_result_success_when_no_roms_found(self):
        """Test that execute returns Result.success with empty list when no ROMs found."""
        # Arrange
        self.mock_emulator_repo.get_rom_directories.return_value = []

        # Act
        result = self.use_case.execute()

        # Assert
        assert isinstance(result, Result)
        assert result.is_success()
        assert not result.is_error()
        assert isinstance(result.value, list)
        assert len(result.value) == 0
