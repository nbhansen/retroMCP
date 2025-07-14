"""Unit tests for application use cases."""

from unittest.mock import Mock

from retromcp.application.use_cases import DetectControllersUseCase
from retromcp.application.use_cases import GetSystemInfoUseCase
from retromcp.application.use_cases import InstallEmulatorUseCase
from retromcp.application.use_cases import InstallPackagesUseCase
from retromcp.application.use_cases import SetupControllerUseCase
from retromcp.application.use_cases import TestConnectionUseCase
from retromcp.application.use_cases import UpdateSystemUseCase
from retromcp.domain.models import CommandResult
from retromcp.domain.models import ConnectionInfo
from retromcp.domain.models import Controller
from retromcp.domain.models import ControllerType
from retromcp.domain.models import Emulator
from retromcp.domain.models import EmulatorStatus
from retromcp.domain.models import Package
from retromcp.domain.models import SystemInfo
from retromcp.domain.ports import ControllerRepository
from retromcp.domain.ports import EmulatorRepository
from retromcp.domain.ports import RetroPieClient
from retromcp.domain.ports import SystemRepository


class TestTestConnectionUseCase:
    """Test TestConnectionUseCase."""

    def test_execute_when_connected(self):
        """Test execute when client is already connected."""
        # Arrange
        mock_client = Mock(spec=RetroPieClient)
        mock_client.test_connection.return_value = True
        expected_info = ConnectionInfo(
            host="test-host",
            port=22,
            username="retro",
            connected=True,
            last_connected="2024-01-01 12:00:00",
        )
        mock_client.get_connection_info.return_value = expected_info

        use_case = TestConnectionUseCase(mock_client)

        # Act
        result = use_case.execute()

        # Assert
        assert result == expected_info
        mock_client.test_connection.assert_called_once()
        mock_client.connect.assert_not_called()
        mock_client.get_connection_info.assert_called_once()

    def test_execute_when_not_connected(self):
        """Test execute when client is not connected."""
        # Arrange
        mock_client = Mock(spec=RetroPieClient)
        mock_client.test_connection.return_value = False
        mock_client.connect.return_value = True
        expected_info = ConnectionInfo(
            host="test-host",
            port=22,
            username="retro",
            connected=True,
        )
        mock_client.get_connection_info.return_value = expected_info

        use_case = TestConnectionUseCase(mock_client)

        # Act
        result = use_case.execute()

        # Assert
        assert result == expected_info
        mock_client.test_connection.assert_called_once()
        mock_client.connect.assert_called_once()
        mock_client.get_connection_info.assert_called_once()


class TestGetSystemInfoUseCase:
    """Test GetSystemInfoUseCase."""

    def test_execute(self):
        """Test execute returns system info from repository."""
        # Arrange
        mock_repo = Mock(spec=SystemRepository)
        expected_info = SystemInfo(
            hostname="test-retropie",
            cpu_temperature=45.5,
            memory_total=4096,
            memory_used=1024,
            memory_free=3072,
            disk_total=32000,
            disk_used=8500,
            disk_free=21000,
            load_average=[0.08, 0.03, 0.01],
            uptime=200000,
        )
        mock_repo.get_system_info.return_value = expected_info

        use_case = GetSystemInfoUseCase(mock_repo)

        # Act
        result = use_case.execute()

        # Assert
        assert result == expected_info
        mock_repo.get_system_info.assert_called_once()


class TestInstallPackagesUseCase:
    """Test InstallPackagesUseCase."""

    def test_execute_empty_packages(self):
        """Test execute with empty package list."""
        # Arrange
        mock_repo = Mock(spec=SystemRepository)
        use_case = InstallPackagesUseCase(mock_repo)

        # Act
        result = use_case.execute([])

        # Assert
        assert result.success is True
        assert result.stdout == "No packages specified"
        mock_repo.get_packages.assert_not_called()

    def test_execute_all_packages_installed(self):
        """Test execute when all packages are already installed."""
        # Arrange
        mock_repo = Mock(spec=SystemRepository)
        installed_packages = [
            Package(name="git", version="2.30.2", installed=True),
            Package(name="vim", version="8.2", installed=True),
        ]
        mock_repo.get_packages.return_value = installed_packages

        use_case = InstallPackagesUseCase(mock_repo)

        # Act
        result = use_case.execute(["git", "vim"])

        # Assert
        assert result.success is True
        assert result.stdout == "All packages are already installed"
        mock_repo.install_packages.assert_not_called()

    def test_execute_install_new_packages(self):
        """Test execute installing new packages."""
        # Arrange
        mock_repo = Mock(spec=SystemRepository)
        installed_packages = [
            Package(name="git", version="2.30.2", installed=True),
        ]
        mock_repo.get_packages.return_value = installed_packages

        expected_result = CommandResult(
            command="apt install vim htop",
            exit_code=0,
            stdout="Successfully installed packages",
            stderr="",
            success=True,
            execution_time=5.2,
        )
        mock_repo.install_packages.return_value = expected_result

        use_case = InstallPackagesUseCase(mock_repo)

        # Act
        result = use_case.execute(["git", "vim", "htop"])

        # Assert
        assert result == expected_result
        mock_repo.install_packages.assert_called_once_with(["vim", "htop"])


class TestUpdateSystemUseCase:
    """Test UpdateSystemUseCase."""

    def test_execute(self):
        """Test execute calls system repository update."""
        # Arrange
        mock_repo = Mock(spec=SystemRepository)
        expected_result = CommandResult(
            command="apt update && apt upgrade",
            exit_code=0,
            stdout="System updated successfully",
            stderr="",
            success=True,
            execution_time=30.5,
        )
        mock_repo.update_system.return_value = expected_result

        use_case = UpdateSystemUseCase(mock_repo)

        # Act
        result = use_case.execute()

        # Assert
        assert result == expected_result
        mock_repo.update_system.assert_called_once()


class TestDetectControllersUseCase:
    """Test DetectControllersUseCase."""

    def test_execute(self):
        """Test execute returns controllers from repository."""
        # Arrange
        mock_repo = Mock(spec=ControllerRepository)
        expected_controllers = [
            Controller(
                name="Xbox Wireless Controller",
                device_path="/dev/input/js0",
                vendor_id="045e",
                product_id="02ea",
                controller_type=ControllerType.XBOX,
                is_configured=True,
            ),
            Controller(
                name="DualShock 4 Controller",
                device_path="/dev/input/js1",
                vendor_id="054c",
                product_id="09cc",
                controller_type=ControllerType.PS4,
                is_configured=False,
            ),
        ]
        mock_repo.detect_controllers.return_value = expected_controllers

        use_case = DetectControllersUseCase(mock_repo)

        # Act
        result = use_case.execute()

        # Assert
        assert result == expected_controllers
        mock_repo.detect_controllers.assert_called_once()


class TestSetupControllerUseCase:
    """Test SetupControllerUseCase."""

    def test_execute_controller_not_found(self):
        """Test execute when specified controller type is not found."""
        # Arrange
        mock_repo = Mock(spec=ControllerRepository)
        mock_repo.detect_controllers.return_value = []

        use_case = SetupControllerUseCase(mock_repo)

        # Act
        result = use_case.execute("xbox")

        # Assert
        assert result.success is False
        assert "No xbox controller detected" in result.stderr
        mock_repo.setup_controller.assert_not_called()

    def test_execute_controller_already_configured(self):
        """Test execute when controller is already configured."""
        # Arrange
        mock_repo = Mock(spec=ControllerRepository)
        xbox_controller = Controller(
            name="Xbox Wireless Controller",
            device_path="/dev/input/js0",
            vendor_id="045e",
            product_id="02ea",
            controller_type=ControllerType.XBOX,
            is_configured=True,
            driver_required=None,
        )
        mock_repo.detect_controllers.return_value = [xbox_controller]

        use_case = SetupControllerUseCase(mock_repo)

        # Act
        result = use_case.execute("xbox")

        # Assert
        assert result.success is True
        assert "already configured" in result.stdout
        mock_repo.setup_controller.assert_not_called()

    def test_execute_setup_controller(self):
        """Test execute setting up a controller."""
        # Arrange
        mock_repo = Mock(spec=ControllerRepository)
        xbox_controller = Controller(
            name="Xbox Wireless Controller",
            device_path="/dev/input/js0",
            vendor_id="045e",
            product_id="02ea",
            controller_type=ControllerType.XBOX,
            is_configured=False,
            driver_required="xboxdrv",
        )
        mock_repo.detect_controllers.return_value = [xbox_controller]

        expected_result = CommandResult(
            command="setup xbox controller",
            exit_code=0,
            stdout="Controller setup successfully",
            stderr="",
            success=True,
            execution_time=2.1,
        )
        mock_repo.setup_controller.return_value = expected_result

        use_case = SetupControllerUseCase(mock_repo)

        # Act
        result = use_case.execute("xbox")

        # Assert
        assert result == expected_result
        mock_repo.setup_controller.assert_called_once_with(xbox_controller)

    def test_execute_match_by_controller_type(self):
        """Test execute matches controller by type enum value."""
        # Arrange
        mock_repo = Mock(spec=ControllerRepository)
        ps4_controller = Controller(
            name="DualShock 4 Controller",
            device_path="/dev/input/js0",
            vendor_id="054c",
            product_id="09cc",
            controller_type=ControllerType.PS4,
            is_configured=False,
        )
        mock_repo.detect_controllers.return_value = [ps4_controller]

        expected_result = CommandResult(
            command="setup ps4 controller",
            exit_code=0,
            stdout="Controller setup successfully",
            stderr="",
            success=True,
            execution_time=1.8,
        )
        mock_repo.setup_controller.return_value = expected_result

        use_case = SetupControllerUseCase(mock_repo)

        # Act
        result = use_case.execute("ps4")

        # Assert
        assert result == expected_result
        mock_repo.setup_controller.assert_called_once_with(ps4_controller)


class TestInstallEmulatorUseCase:
    """Test InstallEmulatorUseCase."""

    def test_execute_emulator_not_found(self):
        """Test execute when emulator is not found."""
        # Arrange
        mock_repo = Mock(spec=EmulatorRepository)
        mock_repo.get_emulators.return_value = []

        use_case = InstallEmulatorUseCase(mock_repo)

        # Act
        result = use_case.execute("nonexistent-emulator")

        # Assert
        assert result.success is False
        assert "not found" in result.stderr
        mock_repo.install_emulator.assert_not_called()

    def test_execute_emulator_already_installed(self):
        """Test execute when emulator is already installed."""
        # Arrange
        mock_repo = Mock(spec=EmulatorRepository)
        emulator = Emulator(
            name="mupen64plus",
            system="n64",
            status=EmulatorStatus.INSTALLED,
        )
        mock_repo.get_emulators.return_value = [emulator]

        use_case = InstallEmulatorUseCase(mock_repo)

        # Act
        result = use_case.execute("mupen64plus")

        # Assert
        assert result.success is True
        assert "already installed" in result.stdout
        mock_repo.install_emulator.assert_not_called()

    def test_execute_emulator_not_available(self):
        """Test execute when emulator is not available for installation."""
        # Arrange
        mock_repo = Mock(spec=EmulatorRepository)
        emulator = Emulator(
            name="unavailable-emulator",
            system="test",
            status=EmulatorStatus.NOT_AVAILABLE,
        )
        mock_repo.get_emulators.return_value = [emulator]

        use_case = InstallEmulatorUseCase(mock_repo)

        # Act
        result = use_case.execute("unavailable-emulator")

        # Assert
        assert result.success is False
        assert "not available for installation" in result.stderr
        mock_repo.install_emulator.assert_not_called()

    def test_execute_install_emulator(self):
        """Test execute installing an available emulator."""
        # Arrange
        mock_repo = Mock(spec=EmulatorRepository)
        emulator = Emulator(
            name="pcsx-rearmed",
            system="psx",
            status=EmulatorStatus.AVAILABLE,
        )
        mock_repo.get_emulators.return_value = [emulator]

        expected_result = CommandResult(
            command="install pcsx-rearmed",
            exit_code=0,
            stdout="Emulator installed successfully",
            stderr="",
            success=True,
            execution_time=45.3,
        )
        mock_repo.install_emulator.return_value = expected_result

        use_case = InstallEmulatorUseCase(mock_repo)

        # Act
        result = use_case.execute("pcsx-rearmed")

        # Assert
        assert result == expected_result
        mock_repo.install_emulator.assert_called_once_with("pcsx-rearmed")
