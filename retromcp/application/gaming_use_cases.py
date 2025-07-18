"""Gaming-related use cases for RetroMCP."""

from typing import List
from typing import Optional

from ..domain.models import Controller
from ..domain.models import EmulatorStatus
from ..domain.models import RomDirectory
from ..domain.ports import ControllerRepository
from ..domain.ports import EmulatorRepository


class DetectControllersUseCase:
    """Use case for detecting connected controllers."""

    def __init__(self, repository: ControllerRepository) -> None:
        """Initialize with controller repository."""
        self._repository = repository

    def execute(self) -> List[Controller]:
        """Detect connected controllers."""
        return self._repository.detect_controllers()


class SetupControllerUseCase:
    """Use case for setting up a specific controller."""

    def __init__(self, repository: ControllerRepository) -> None:
        """Initialize with controller repository."""
        self._repository = repository

    def execute(self, controller_id: str, driver_path: Optional[str] = None) -> Controller:
        """Setup a specific controller."""
        # Get current controllers
        controllers = self._repository.detect_controllers()

        # Find the target controller
        target_controller = None
        for controller in controllers:
            if controller.id == controller_id:
                target_controller = controller
                break

        if not target_controller:
            raise ValueError(f"Controller with ID {controller_id} not found")

        # Check if controller is already configured
        if target_controller.is_configured and not target_controller.driver_required:
            return target_controller

        # Setup the controller
        return self._repository.setup_controller(controller_id, driver_path)


class InstallEmulatorUseCase:
    """Use case for installing emulators."""

    def __init__(self, repository: EmulatorRepository) -> None:
        """Initialize with emulator repository."""
        self._repository = repository

    def execute(self, emulator_name: str) -> EmulatorStatus:
        """Install an emulator."""
        # Check if emulator is already installed
        status = self._repository.get_emulator_status(emulator_name)
        if status == EmulatorStatus.INSTALLED:
            return status

        # Check if emulator is available for installation
        if status == EmulatorStatus.NOT_AVAILABLE:
            raise ValueError(f"Emulator '{emulator_name}' is not available for installation")

        # Install the emulator
        return self._repository.install_emulator(emulator_name)


class ListRomsUseCase:
    """Use case for listing ROM directories and files."""

    def __init__(self, emulator_repository: EmulatorRepository) -> None:
        """Initialize with emulator repository."""
        self._repository = emulator_repository

    def execute(
        self,
        system_filter: Optional[str] = None,
        min_rom_count: Optional[int] = None
    ) -> List[RomDirectory]:
        """List ROM directories with optional filtering and sorting.
        
        Args:
            system_filter: Optional system name to filter by
            min_rom_count: Optional minimum ROM count filter
            
        Returns:
            List of ROM directories sorted by ROM count (descending)
        """
        # Get all ROM directories from repository
        rom_directories = self._repository.get_rom_directories()

        # Apply system filter if specified
        if system_filter is not None:
            rom_directories = [
                rom for rom in rom_directories
                if rom.system == system_filter
            ]

        # Apply minimum ROM count filter if specified
        if min_rom_count is not None:
            rom_directories = [
                rom for rom in rom_directories
                if rom.rom_count >= min_rom_count
            ]

        # Sort by ROM count in descending order
        rom_directories.sort(key=lambda r: r.rom_count, reverse=True)

        return rom_directories
