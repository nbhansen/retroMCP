"""Application use cases for RetroMCP."""

from typing import List
from typing import Optional

from ..domain.models import CommandResult
from ..domain.models import ConnectionInfo
from ..domain.models import Controller
from ..domain.models import EmulatorStatus
from ..domain.models import RomDirectory
from ..domain.models import SystemInfo
from ..domain.ports import ControllerRepository
from ..domain.ports import EmulatorRepository
from ..domain.ports import RetroPieClient
from ..domain.ports import SystemRepository


class TestConnectionUseCase:
    """Use case for testing connection to RetroPie."""

    def __init__(self, client: RetroPieClient) -> None:
        """Initialize with RetroPie client."""
        self._client = client

    def execute(self) -> ConnectionInfo:
        """Test the connection and return connection info."""
        # Ensure connection is established
        if not self._client.test_connection():
            self._client.connect()

        return self._client.get_connection_info()


class GetSystemInfoUseCase:
    """Use case for getting system information."""

    def __init__(self, system_repo: SystemRepository) -> None:
        """Initialize with system repository."""
        self._system_repo = system_repo

    def execute(self) -> SystemInfo:
        """Get system information."""
        return self._system_repo.get_system_info()


class InstallPackagesUseCase:
    """Use case for installing system packages."""

    def __init__(self, system_repo: SystemRepository) -> None:
        """Initialize with system repository."""
        self._system_repo = system_repo

    def execute(self, packages: List[str]) -> CommandResult:
        """Install the specified packages."""
        if not packages:
            return CommandResult(
                command="",
                exit_code=0,
                stdout="No packages specified",
                stderr="",
                success=True,
                execution_time=0.0,
            )

        # Filter out already installed packages
        installed_packages = self._system_repo.get_packages()
        installed_names = {pkg.name for pkg in installed_packages if pkg.installed}

        packages_to_install = [pkg for pkg in packages if pkg not in installed_names]

        if not packages_to_install:
            return CommandResult(
                command="",
                exit_code=0,
                stdout="All packages are already installed",
                stderr="",
                success=True,
                execution_time=0.0,
            )

        return self._system_repo.install_packages(packages_to_install)


class UpdateSystemUseCase:
    """Use case for updating the system."""

    def __init__(self, system_repo: SystemRepository) -> None:
        """Initialize with system repository."""
        self._system_repo = system_repo

    def execute(self) -> CommandResult:
        """Update the system packages."""
        return self._system_repo.update_system()


class DetectControllersUseCase:
    """Use case for detecting connected controllers."""

    def __init__(self, controller_repo: ControllerRepository) -> None:
        """Initialize with controller repository."""
        self._controller_repo = controller_repo

    def execute(self) -> List[Controller]:
        """Detect and return connected controllers."""
        return self._controller_repo.detect_controllers()


class SetupControllerUseCase:
    """Use case for setting up a controller."""

    def __init__(self, controller_repo: ControllerRepository) -> None:
        """Initialize with controller repository."""
        self._controller_repo = controller_repo

    def execute(self, controller_type: str) -> CommandResult:
        """Set up a controller of the specified type."""
        # First detect controllers
        controllers = self._controller_repo.detect_controllers()

        # Find a controller matching the type
        target_controller = None
        for controller in controllers:
            if (
                controller_type.lower() in controller.name.lower()
                or controller_type.lower() == controller.controller_type.value
            ):
                target_controller = controller
                break

        if not target_controller:
            return CommandResult(
                command="",
                exit_code=1,
                stdout="",
                stderr=f"No {controller_type} controller detected",
                success=False,
                execution_time=0.0,
            )

        # Check if already configured
        if target_controller.is_configured and not target_controller.driver_required:
            return CommandResult(
                command="",
                exit_code=0,
                stdout=f"{controller_type} controller is already configured",
                stderr="",
                success=True,
                execution_time=0.0,
            )

        # Set up the controller
        return self._controller_repo.setup_controller(target_controller)


class InstallEmulatorUseCase:
    """Use case for installing an emulator."""

    def __init__(self, emulator_repo: EmulatorRepository) -> None:
        """Initialize with emulator repository."""
        self._emulator_repo = emulator_repo

    def execute(self, emulator_name: str) -> CommandResult:
        """Install the specified emulator."""
        # Check if emulator exists and its status
        emulators = self._emulator_repo.get_emulators()

        target_emulator = None
        for emulator in emulators:
            if emulator.name == emulator_name:
                target_emulator = emulator
                break

        if not target_emulator:
            return CommandResult(
                command="",
                exit_code=1,
                stdout="",
                stderr=f"Emulator '{emulator_name}' not found",
                success=False,
                execution_time=0.0,
            )

        if target_emulator.status == EmulatorStatus.INSTALLED:
            return CommandResult(
                command="",
                exit_code=0,
                stdout=f"Emulator '{emulator_name}' is already installed",
                stderr="",
                success=True,
                execution_time=0.0,
            )

        if target_emulator.status == EmulatorStatus.NOT_AVAILABLE:
            return CommandResult(
                command="",
                exit_code=1,
                stdout="",
                stderr=f"Emulator '{emulator_name}' is not available for installation",
                success=False,
                execution_time=0.0,
            )

        # Install the emulator
        return self._emulator_repo.install_emulator(emulator_name)


class ListRomsUseCase:
    """Use case for listing ROM directories and files."""

    def __init__(self, emulator_repo: EmulatorRepository) -> None:
        """Initialize with emulator repository."""
        self._emulator_repo = emulator_repo

    def execute(
        self, system_filter: Optional[str] = None, min_rom_count: Optional[int] = None
    ) -> List[RomDirectory]:
        """List ROM directories with optional filtering.

        Args:
            system_filter: Optional system name to filter by
            min_rom_count: Optional minimum ROM count to filter by

        Returns:
            List of RomDirectory objects, sorted by ROM count descending
        """
        # Get all ROM directories from repository
        rom_directories = self._emulator_repo.get_rom_directories()

        # Apply system filter if specified
        if system_filter:
            rom_directories = [
                rom_dir
                for rom_dir in rom_directories
                if rom_dir.system == system_filter
            ]

        # Apply minimum ROM count filter if specified
        if min_rom_count is not None:
            rom_directories = [
                rom_dir
                for rom_dir in rom_directories
                if rom_dir.rom_count >= min_rom_count
            ]

        # Sort by ROM count descending (most ROMs first)
        rom_directories.sort(key=lambda r: r.rom_count, reverse=True)

        return rom_directories
