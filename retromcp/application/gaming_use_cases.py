"""Gaming-related use cases for RetroMCP."""

from typing import List
from typing import Optional

from ..domain.models import CommandResult
from ..domain.models import ConnectionError
from ..domain.models import Controller
from ..domain.models import EmulatorStatus
from ..domain.models import ExecutionError
from ..domain.models import Result
from ..domain.models import RomDirectory
from ..domain.models import ValidationError
from ..domain.ports import ControllerRepository
from ..domain.ports import EmulatorRepository


class DetectControllersUseCase:
    """Use case for detecting connected controllers."""

    def __init__(self, repository: ControllerRepository) -> None:
        """Initialize with controller repository."""
        self._repository = repository

    def execute(self) -> Result[List[Controller], ConnectionError | ExecutionError]:
        """Detect connected controllers."""
        try:
            controllers = self._repository.detect_controllers()
            return Result.success(controllers)
        except OSError as e:
            return Result.error(ConnectionError(
                code="CONTROLLER_CONNECTION_FAILED",
                message=f"Failed to connect to controller interface: {e}",
                details={"error": str(e)}
            ))
        except Exception as e:
            return Result.error(ExecutionError(
                code="CONTROLLER_DETECTION_FAILED",
                message="Failed to detect controllers",
                command="controller detection",
                exit_code=1,
                stderr=str(e)
            ))


class SetupControllerUseCase:
    """Use case for setting up a specific controller."""

    def __init__(self, repository: ControllerRepository) -> None:
        """Initialize with controller repository."""
        self._repository = repository

    def execute(
        self, controller_device_path: str, driver_path: Optional[str] = None
    ) -> Result[CommandResult, ValidationError | ConnectionError | ExecutionError]:
        """Setup a specific controller."""
        try:
            # Get current controllers
            controllers = self._repository.detect_controllers()

            # Find the target controller by device path or controller type
            target_controller = None

            # First try exact device path match
            for controller in controllers:
                if controller.device_path == controller_device_path:
                    target_controller = controller
                    break

            # If not found by device path, try matching by controller type
            if not target_controller:
                for controller in controllers:
                    if controller.controller_type.value == controller_device_path:
                        target_controller = controller
                        break

            if not target_controller:
                return Result.error(ValidationError(
                    code="CONTROLLER_NOT_FOUND",
                    message=f"Controller with device path or type '{controller_device_path}' not found",
                    details={"device_path": controller_device_path}
                ))

            # Check if controller is already configured
            if target_controller.is_configured and not target_controller.driver_required:
                already_configured_result = CommandResult(
                    command="",
                    exit_code=0,
                    stdout="Controller is already configured",
                    stderr="",
                    success=True,
                    execution_time=0.0,
                )
                return Result.success(already_configured_result)

            # Setup the controller
            result = self._repository.setup_controller(target_controller)
            return Result.success(result)

        except OSError as e:
            return Result.error(ConnectionError(
                code="CONTROLLER_CONNECTION_FAILED",
                message=f"Failed to connect to controller interface: {e}",
                details={"error": str(e)}
            ))
        except Exception as e:
            return Result.error(ExecutionError(
                code="CONTROLLER_SETUP_FAILED",
                message="Failed to setup controller",
                command="controller setup",
                exit_code=1,
                stderr=str(e)
            ))


class InstallEmulatorUseCase:
    """Use case for installing emulators."""

    def __init__(self, repository: EmulatorRepository) -> None:
        """Initialize with emulator repository."""
        self._repository = repository

    def execute(self, emulator_name: str) -> Result[CommandResult, ValidationError | ConnectionError | ExecutionError]:
        """Install an emulator."""
        try:
            # Validate emulator name
            if not emulator_name or not emulator_name.strip():
                return Result.error(ValidationError(
                    code="INVALID_EMULATOR_NAME",
                    message="Emulator name cannot be empty",
                    details={"emulator_name": emulator_name}
                ))

            # Get available emulators to check if this one exists and its status
            available_emulators = self._repository.get_emulators()
            target_emulator = None
            for emulator in available_emulators:
                if emulator.name == emulator_name:
                    target_emulator = emulator
                    break

            if not target_emulator:
                emulator_names = [emulator.name for emulator in available_emulators]
                return Result.error(ValidationError(
                    code="EMULATOR_NOT_AVAILABLE",
                    message=f"Emulator '{emulator_name}' is not available for installation",
                    details={"emulator_name": emulator_name, "available": emulator_names}
                ))

            # Check if emulator is already installed
            if target_emulator.status == EmulatorStatus.INSTALLED:
                already_installed_result = CommandResult(
                    command="",
                    exit_code=0,
                    stdout=f"Emulator '{emulator_name}' is already installed",
                    stderr="",
                    success=True,
                    execution_time=0.0,
                )
                return Result.success(already_installed_result)

            # Check if emulator is available for installation
            if target_emulator.status != EmulatorStatus.AVAILABLE:
                return Result.error(ValidationError(
                    code="EMULATOR_NOT_AVAILABLE",
                    message=f"Emulator '{emulator_name}' is not available for installation",
                    details={"emulator_name": emulator_name, "status": target_emulator.status.value}
                ))

            # Install the emulator
            result = self._repository.install_emulator(emulator_name)
            return Result.success(result)

        except OSError as e:
            return Result.error(ConnectionError(
                code="EMULATOR_CONNECTION_FAILED",
                message=f"Failed to connect to emulator system: {e}",
                details={"error": str(e)}
            ))
        except Exception as e:
            return Result.error(ExecutionError(
                code="EMULATOR_INSTALL_FAILED",
                message="Failed to install emulator",
                command=f"install emulator {emulator_name}",
                exit_code=1,
                stderr=str(e)
            ))


class ListRomsUseCase:
    """Use case for listing ROM directories and files."""

    def __init__(self, emulator_repository: EmulatorRepository) -> None:
        """Initialize with emulator repository."""
        self._repository = emulator_repository

    def execute(
        self, system_filter: Optional[str] = None, min_rom_count: Optional[int] = None
    ) -> Result[List[RomDirectory], ConnectionError | ExecutionError]:
        """List ROM directories with optional filtering and sorting.

        Args:
            system_filter: Optional system name to filter by
            min_rom_count: Optional minimum ROM count filter

        Returns:
            Result containing list of ROM directories sorted by ROM count (descending)
        """
        try:
            # Get all ROM directories from repository
            rom_directories = self._repository.get_rom_directories()

            # Apply system filter if specified
            if system_filter is not None:
                rom_directories = [
                    rom for rom in rom_directories if rom.system == system_filter
                ]

            # Apply minimum ROM count filter if specified
            if min_rom_count is not None:
                rom_directories = [
                    rom for rom in rom_directories if rom.rom_count >= min_rom_count
                ]

            # Sort by ROM count in descending order
            rom_directories.sort(key=lambda r: r.rom_count, reverse=True)

            return Result.success(rom_directories)

        except (OSError, PermissionError) as e:
            return Result.error(ConnectionError(
                code="ROM_ACCESS_FAILED",
                message=f"Failed to access ROM directories: {e}",
                details={"error": str(e)}
            ))
        except Exception as e:
            return Result.error(ExecutionError(
                code="ROM_LISTING_FAILED",
                message="Failed to list ROM directories",
                command="list ROM directories",
                exit_code=1,
                stderr=str(e)
            ))
