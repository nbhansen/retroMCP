"""Unit tests for ManageStateUseCase."""

from datetime import datetime
from unittest.mock import Mock

import pytest

from retromcp.application.use_cases import ManageStateUseCase
from retromcp.domain.models import EmulatorStatus
from retromcp.domain.models import StateAction
from retromcp.domain.models import StateManagementRequest
from retromcp.domain.models import StateManagementResult
from retromcp.domain.models import SystemState


class TestManageStateUseCase:
    """Test cases for ManageStateUseCase."""

    @pytest.fixture
    def mock_state_repository(self) -> Mock:
        """Provide mock state repository."""
        return Mock()

    @pytest.fixture
    def mock_system_repository(self) -> Mock:
        """Provide mock system repository."""
        return Mock()

    @pytest.fixture
    def mock_emulator_repository(self) -> Mock:
        """Provide mock emulator repository."""
        return Mock()

    @pytest.fixture
    def mock_controller_repository(self) -> Mock:
        """Provide mock controller repository."""
        return Mock()

    @pytest.fixture
    def sample_state(self) -> SystemState:
        """Provide sample system state."""
        return SystemState(
            schema_version="1.0",
            last_updated=datetime.now().isoformat(),
            system={
                "hardware": "Pi 4B",
                "overclocking": "medium",
                "temperatures": {"normal_range": "45-65°C"},
            },
            emulators={
                "installed": ["mupen64plus", "pcsx-rearmed"],
                "preferred": {"n64": "mupen64plus"},
            },
            controllers=[
                {"type": "xbox", "device": "/dev/input/js0", "configured": True}
            ],
            roms={
                "systems": ["nes", "snes", "psx"],
                "counts": {"nes": 150, "snes": 89},
            },
            custom_configs=["shaders", "bezels"],
            known_issues=["audio crackling"],
        )

    @pytest.fixture
    def use_case(
        self,
        mock_state_repository: Mock,
        mock_system_repository: Mock,
        mock_emulator_repository: Mock,
        mock_controller_repository: Mock,
    ) -> ManageStateUseCase:
        """Provide ManageStateUseCase instance."""
        return ManageStateUseCase(
            state_repository=mock_state_repository,
            system_repository=mock_system_repository,
            emulator_repository=mock_emulator_repository,
            controller_repository=mock_controller_repository,
        )

    def test_load_state_success(
        self,
        use_case: ManageStateUseCase,
        mock_state_repository: Mock,
        sample_state: SystemState,
    ) -> None:
        """Test successful state loading."""
        mock_state_repository.load_state.return_value = sample_state

        request = StateManagementRequest(action=StateAction.LOAD)
        result = use_case.execute(request)

        assert result.success is True
        assert result.action == StateAction.LOAD
        assert result.state == sample_state
        assert "loaded successfully" in result.message
        mock_state_repository.load_state.assert_called_once()

    def test_load_state_not_found(
        self, use_case: ManageStateUseCase, mock_state_repository: Mock
    ) -> None:
        """Test loading state when file doesn't exist."""
        mock_state_repository.load_state.side_effect = FileNotFoundError(
            "State file not found"
        )

        request = StateManagementRequest(action=StateAction.LOAD)
        result = use_case.execute(request)

        assert result.success is False
        assert result.action == StateAction.LOAD
        assert result.state is None
        assert "not found" in result.message

    def test_save_state_with_scan(
        self,
        use_case: ManageStateUseCase,
        mock_state_repository: Mock,
        mock_system_repository: Mock,
        mock_emulator_repository: Mock,
        mock_controller_repository: Mock,
    ) -> None:
        """Test saving state with system scan."""
        # Mock system info
        mock_system_info = Mock()
        mock_system_info.hostname = "retropie"
        mock_system_info.cpu_temperature = 60.0
        mock_system_info.memory_total = 8000000000
        mock_system_info.disk_total = 32000000000
        mock_system_repository.get_system_info.return_value = mock_system_info

        # Mock emulators
        mock_emulator = Mock()
        mock_emulator.name = "mupen64plus"
        mock_emulator.system = "n64"
        mock_emulator.status = EmulatorStatus.INSTALLED
        mock_emulator_repository.get_emulators.return_value = [mock_emulator]

        # Mock controllers
        mock_controller = Mock()
        mock_controller.controller_type.value = "xbox"
        mock_controller.device_path = "/dev/input/js0"
        mock_controller.is_configured = True
        mock_controller_repository.detect_controllers.return_value = [mock_controller]

        # Mock ROM directories
        mock_rom_dir = Mock()
        mock_rom_dir.system = "nes"
        mock_rom_dir.rom_count = 150
        mock_emulator_repository.get_rom_directories.return_value = [mock_rom_dir]

        # Mock save result
        expected_result = StateManagementResult(
            success=True,
            action=StateAction.SAVE,
            message="State saved successfully",
            state=None,
        )
        mock_state_repository.save_state.return_value = expected_result

        request = StateManagementRequest(action=StateAction.SAVE)
        result = use_case.execute(request)

        assert result.success is True
        assert result.action == StateAction.SAVE
        mock_state_repository.save_state.assert_called_once()

        # Verify the state was built correctly
        saved_state = mock_state_repository.save_state.call_args[0][0]
        assert saved_state.schema_version == "1.0"
        assert saved_state.system["hostname"] == "retropie"
        assert "mupen64plus" in saved_state.emulators["installed"]
        assert len(saved_state.controllers) == 1
        assert saved_state.roms["counts"]["nes"] == 150

    def test_update_state_field(
        self, use_case: ManageStateUseCase, mock_state_repository: Mock
    ) -> None:
        """Test updating a specific field in state."""
        expected_result = StateManagementResult(
            success=True,
            action=StateAction.UPDATE,
            message="Field updated successfully",
            state=None,
        )
        mock_state_repository.update_state_field.return_value = expected_result

        request = StateManagementRequest(
            action=StateAction.UPDATE, path="system.hardware", value="Pi 5"
        )
        result = use_case.execute(request)

        assert result.success is True
        assert result.action == StateAction.UPDATE
        mock_state_repository.update_state_field.assert_called_once_with(
            "system.hardware", "Pi 5"
        )

    def test_update_without_path(self, use_case: ManageStateUseCase) -> None:
        """Test update action without path."""
        request = StateManagementRequest(action=StateAction.UPDATE)
        result = use_case.execute(request)

        assert result.success is False
        assert "Path and value required" in result.message

    def test_compare_state(
        self,
        use_case: ManageStateUseCase,
        mock_state_repository: Mock,
        mock_system_repository: Mock,
        mock_emulator_repository: Mock,
        mock_controller_repository: Mock,
        sample_state: SystemState,
    ) -> None:
        """Test comparing current state with stored state."""
        mock_state_repository.load_state.return_value = sample_state

        # Mock current system state components
        mock_system_info = Mock()
        mock_system_info.hostname = "retropie"
        mock_system_info.cpu_temperature = 60.0
        mock_system_info.memory_total = 8000000000
        mock_system_info.disk_total = 32000000000
        mock_system_repository.get_system_info.return_value = mock_system_info

        # Mock emulators
        mock_emulator = Mock()
        mock_emulator.name = "mupen64plus"
        mock_emulator.system = "n64"
        mock_emulator.status = EmulatorStatus.INSTALLED
        mock_emulator_repository.get_emulators.return_value = [mock_emulator]

        # Mock controllers
        mock_controller = Mock()
        mock_controller.controller_type.value = "xbox"
        mock_controller.device_path = "/dev/input/js0"
        mock_controller.is_configured = True
        mock_controller_repository.detect_controllers.return_value = [mock_controller]

        # Mock ROM directories
        mock_rom_dir = Mock()
        mock_rom_dir.system = "nes"
        mock_rom_dir.rom_count = 150
        mock_emulator_repository.get_rom_directories.return_value = [mock_rom_dir]

        # Mock compare result
        mock_state_repository.compare_state.return_value = {
            "added": {"system.new_field": "value"},
            "changed": {"system.hardware": {"old": "Pi 4B", "new": "Pi 5"}},
            "removed": {},
        }

        request = StateManagementRequest(action=StateAction.COMPARE)
        result = use_case.execute(request)

        assert result.success is True
        assert result.action == StateAction.COMPARE
        assert result.diff is not None
        assert "added" in result.diff
        assert "changed" in result.diff

    def test_invalid_action(self, use_case: ManageStateUseCase) -> None:
        """Test handling of invalid action."""
        # Create a mock action that's not in our expected set
        invalid_request = Mock()
        invalid_request.action = Mock()
        invalid_request.action.value = "invalid"

        result = use_case.execute(invalid_request)

        assert result.success is False
        assert "Unknown action" in result.message
