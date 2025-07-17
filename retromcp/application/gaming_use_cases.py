"""Gaming-related use cases for RetroMCP."""

from typing import List
from typing import Optional

from ..domain.models import Controller
from ..domain.models import EmulatorStatus
from ..domain.models import RomDirectory
from ..domain.ports import ControllerRepository
from ..domain.ports import EmulatorRepository
from ..domain.ports import RetroPieClient


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

    def __init__(self, client: RetroPieClient) -> None:
        """Initialize with RetroPie client."""
        self._client = client

    def execute(self, system: Optional[str] = None) -> List[RomDirectory]:
        """List ROM directories and files."""
        return self._client.list_roms(system)