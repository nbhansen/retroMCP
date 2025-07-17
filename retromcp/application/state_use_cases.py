"""State management use cases for RetroMCP."""

from datetime import datetime
from typing import Any
from typing import Optional

from ..domain.models import EmulatorStatus
from ..domain.models import StateAction
from ..domain.models import StateManagementRequest
from ..domain.models import StateManagementResult
from ..domain.models import SystemState
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

    def execute(self, request: StateManagementRequest) -> StateManagementResult:
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
                return StateManagementResult(
                    success=False,
                    action=request.action,
                    message=f"Unknown action: {request.action.value}",
                )
        except Exception as e:
            return StateManagementResult(
                success=False,
                action=request.action,
                message=f"Error: {e!s}",
            )

    def _load_state(self) -> StateManagementResult:
        """Load state from storage."""
        try:
            state = self._state_repository.load_state()
            return StateManagementResult(
                success=True,
                action=StateAction.LOAD,
                message="State loaded successfully",
                state=state,
            )
        except FileNotFoundError:
            return StateManagementResult(
                success=False,
                action=StateAction.LOAD,
                message="State file not found - run save first",
            )

    def _save_state(self, force_scan: bool = True) -> StateManagementResult:  # noqa: ARG002
        """Save current system state."""
        # Build current state from system
        state = self._build_current_state()

        # Save to repository
        return self._state_repository.save_state(state)

    def _build_current_state(self) -> SystemState:
        """Build current system state by scanning the system."""
        # Get system info
        system_info = self._system_repository.get_system_info()

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
        return SystemState(
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
            network=None,   # Will be populated when enhanced data collection is implemented
            software=None,  # Will be populated when enhanced data collection is implemented
            services=None,  # Will be populated when enhanced data collection is implemented
            notes=None,     # Will be populated when enhanced data collection is implemented
        )

    def _update_state(self, path: Optional[str], value: Any) -> StateManagementResult:  # noqa: ANN401
        """Update specific field in state."""
        if not path or value is None:
            return StateManagementResult(
                success=False,
                action=StateAction.UPDATE,
                message="Path and value required for update",
            )

        return self._state_repository.update_state_field(path, value)

    def _compare_state(self) -> StateManagementResult:
        """Compare current state with stored state."""
        try:
            # Load stored state
            self._state_repository.load_state()

            # Get current state
            current_state = self._build_current_state()

            # Compare states
            diff = self._state_repository.compare_state(current_state)

            return StateManagementResult(
                success=True,
                action=StateAction.COMPARE,
                message="State comparison complete",
                diff=diff,
            )
        except FileNotFoundError:
            return StateManagementResult(
                success=False,
                action=StateAction.COMPARE,
                message="No stored state to compare against",
            )