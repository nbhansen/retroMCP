"""State management use cases for RetroMCP."""

from datetime import datetime
from typing import Any
from typing import Optional

from ..domain.models import ConnectionError
from ..domain.models import EmulatorStatus
from ..domain.models import ExecutionError
from ..domain.models import Result
from ..domain.models import StateAction
from ..domain.models import StateManagementRequest
from ..domain.models import StateManagementResult
from ..domain.models import SystemState
from ..domain.models import ValidationError
from ..domain.ports import ControllerRepository
from ..domain.ports import EmulatorRepository
from ..domain.ports import StateRepository
from ..domain.ports import SystemRepository


class ManageStateUseCase:
    """Use case for managing system state."""

    def __init__(
        self,
        state_repository: StateRepository,
        system_repository: SystemRepository,
        emulator_repository: EmulatorRepository,
        controller_repository: ControllerRepository,
    ) -> None:
        """Initialize with required repositories."""
        self._state_repository = state_repository
        self._system_repository = system_repository
        self._emulator_repository = emulator_repository
        self._controller_repository = controller_repository

    def execute(
        self, request: StateManagementRequest
    ) -> Result[
        StateManagementResult, ValidationError | ConnectionError | ExecutionError
    ]:
        """Execute state management action."""
        try:
            if request.action == StateAction.LOAD:
                return self._load_state()
            elif request.action == StateAction.SAVE:
                return self._save_state(request.force_scan)
            elif request.action == StateAction.UPDATE:
                return self._update_state(request.path, request.value)
            elif request.action == StateAction.COMPARE:
                return self._compare_state()
            else:
                return Result.error(
                    ValidationError(
                        code="UNKNOWN_ACTION",
                        message=f"Unknown action: {request.action if isinstance(request.action, str) else request.action.value}",
                        details={"action": str(request.action)},
                    )
                )
        except OSError as e:
            return Result.error(
                ConnectionError(
                    code="STATE_CONNECTION_FAILED",
                    message=f"Failed to connect to state system: {e}",
                    details={"error": str(e)},
                )
            )
        except Exception as e:
            return Result.error(
                ExecutionError(
                    code="STATE_OPERATION_FAILED",
                    message="Failed to execute state operation",
                    command=f"state {request.action.value if hasattr(request.action, 'value') else request.action}",
                    exit_code=1,
                    stderr=str(e),
                )
            )

    def _load_state(self) -> Result[StateManagementResult, ValidationError]:
        """Load state from storage."""
        try:
            state = self._state_repository.load_state()
            result = StateManagementResult(
                success=True,
                action=StateAction.LOAD,
                message="State loaded successfully",
                state=state,
            )
            return Result.success(result)
        except FileNotFoundError:
            return Result.error(
                ValidationError(
                    code="STATE_FILE_NOT_FOUND",
                    message="State file not found - run save first",
                    details={"action": StateAction.LOAD.value},
                )
            )

    def _save_state(
        self, force_scan: bool = True
    ) -> Result[
        StateManagementResult, ValidationError | ConnectionError | ExecutionError
    ]:
        """Save current system state."""
        # Build current state from system
        state_result = self._build_current_state()
        if state_result.is_error():
            return state_result

        state = state_result.value

        # Save to repository
        return Result.success(self._state_repository.save_state(state))

    def _build_current_state(
        self,
    ) -> Result[SystemState, ConnectionError | ExecutionError]:
        """Build current system state by scanning the system."""
        # Get system info
        system_info_result = self._system_repository.get_system_info()
        if isinstance(system_info_result, Result):
            if system_info_result.is_error():
                return system_info_result  # Return the error
            system_info = system_info_result.value
        else:
            # Backward compatibility for repositories not yet returning Result
            system_info = system_info_result

        # Get emulators
        emulators = self._emulator_repository.get_emulators()
        installed_emulators = [
            e.name for e in emulators if e.status == EmulatorStatus.INSTALLED
        ]

        # Build preferred emulators map
        preferred = {}
        for emulator in emulators:
            if (
                emulator.status == EmulatorStatus.INSTALLED
                and emulator.system not in preferred
            ):
                # Simple heuristic: first installed emulator for a system is preferred
                preferred[emulator.system] = emulator.name

        # Get controllers
        controllers = self._controller_repository.detect_controllers()
        controller_data = [
            {
                "type": c.controller_type.value,
                "device": c.device_path,
                "configured": c.is_configured,
            }
            for c in controllers
        ]

        # Get ROM directories
        rom_dirs = self._emulator_repository.get_rom_directories()
        rom_systems = [d.system for d in rom_dirs]
        rom_counts = {d.system: d.rom_count for d in rom_dirs}

        # Build enhanced v2.0 state with additional system information
        state = SystemState(
            schema_version="2.0",
            last_updated=datetime.now().isoformat(),
            system={
                "hostname": system_info.hostname,
                "cpu_temperature": system_info.cpu_temperature,
                "memory_total": system_info.memory_total,
                "memory_used": system_info.memory_used,
                "memory_free": system_info.memory_free,
                "disk_total": system_info.disk_total,
                "disk_used": system_info.disk_used,
                "disk_free": system_info.disk_free,
                "load_average": system_info.load_average,
                "uptime": system_info.uptime,
            },
            emulators={
                "installed": installed_emulators,
                "preferred": preferred,
            },
            controllers=controller_data,
            roms={
                "systems": rom_systems,
                "counts": rom_counts,
            },
            custom_configs=[],  # TODO: Detect custom configs
            known_issues=[],  # TODO: Detect known issues
            # v2.0 enhanced fields - TODO: populate from enhanced data collection
            hardware=None,  # Will be populated when enhanced data collection is implemented
            network=None,  # Will be populated when enhanced data collection is implemented
            software=None,  # Will be populated when enhanced data collection is implemented
            services=None,  # Will be populated when enhanced data collection is implemented
            notes=None,  # Will be populated when enhanced data collection is implemented
        )
        return Result.success(state)

    def _update_state(
        self, path: Optional[str], value: Any
    ) -> Result[StateManagementResult, ValidationError]:
        """Update specific field in state."""
        if not path or value is None:
            return Result.error(
                ValidationError(
                    code="MISSING_UPDATE_PARAMS",
                    message="Path and value required for update",
                    details={
                        "path": path,
                        "value": str(value) if value is not None else None,
                    },
                )
            )

        return Result.success(self._state_repository.update_state_field(path, value))

    def _compare_state(
        self,
    ) -> Result[
        StateManagementResult, ValidationError | ConnectionError | ExecutionError
    ]:
        """Compare current state with stored state."""
        try:
            # Load stored state
            self._state_repository.load_state()

            # Get current state
            current_state_result = self._build_current_state()
            if current_state_result.is_error():
                return current_state_result

            current_state = current_state_result.value

            # Compare states
            diff = self._state_repository.compare_state(current_state)

            result = StateManagementResult(
                success=True,
                action=StateAction.COMPARE,
                message="State comparison complete",
                diff=diff,
            )
            return Result.success(result)
        except FileNotFoundError:
            return Result.error(
                ValidationError(
                    code="NO_STORED_STATE",
                    message="No stored state to compare against",
                    details={"action": StateAction.COMPARE.value},
                )
            )
