"""Unit tests for State Management use cases with Result pattern."""

from datetime import datetime
from unittest.mock import Mock

import pytest

from retromcp.application.state_use_cases import ManageStateUseCase
from retromcp.domain.models import ConnectionError
from retromcp.domain.models import Controller
from retromcp.domain.models import ControllerType
from retromcp.domain.models import Emulator
from retromcp.domain.models import EmulatorStatus
from retromcp.domain.models import Result
from retromcp.domain.models import RomDirectory
from retromcp.domain.models import StateAction
from retromcp.domain.models import StateManagementRequest
from retromcp.domain.models import StateManagementResult
from retromcp.domain.models import SystemInfo
from retromcp.domain.models import SystemState
from retromcp.domain.models import ValidationError
from retromcp.domain.ports import ControllerRepository
from retromcp.domain.ports import EmulatorRepository
from retromcp.domain.ports import StateRepository
from retromcp.domain.ports import SystemRepository


class TestManageStateUseCaseResult:
    """Test ManageStateUseCase with Result pattern."""

    @pytest.fixture
    def mock_state_repo(self):
        """Create mock state repository."""
        return Mock(spec=StateRepository)

    @pytest.fixture
    def mock_system_repo(self):
        """Create mock system repository."""
        return Mock(spec=SystemRepository)

    @pytest.fixture
    def mock_emulator_repo(self):
        """Create mock emulator repository."""
        return Mock(spec=EmulatorRepository)

    @pytest.fixture
    def mock_controller_repo(self):
        """Create mock controller repository."""
        return Mock(spec=ControllerRepository)

    @pytest.fixture
    def use_case(
        self,
        mock_state_repo,
        mock_system_repo,
        mock_emulator_repo,
        mock_controller_repo,
    ):
        """Create ManageStateUseCase instance."""
        return ManageStateUseCase(
            state_repository=mock_state_repo,
            system_repository=mock_system_repo,
            emulator_repository=mock_emulator_repo,
            controller_repository=mock_controller_repo,
        )

    @pytest.fixture
    def sample_system_state(self):
        """Create sample system state."""
        return SystemState(
            schema_version="2.0",
            last_updated=datetime.now().isoformat(),
            system={
                "hostname": "retropie",
                "cpu_temperature": 45.2,
                "memory_total": 4096,
                "memory_used": 2048,
                "memory_free": 2048,
                "disk_total": 32000,
                "disk_used": 16000,
                "disk_free": 16000,
                "load_average": [0.5, 0.6, 0.7],
                "uptime": 86400,
            },
            emulators={
                "installed": ["mupen64plus", "pcsx-rearmed", "snes9x"],
                "preferred": {
                    "n64": "mupen64plus",
                    "psx": "pcsx-rearmed",
                    "snes": "snes9x",
                },
            },
            controllers=[
                {"type": "xbox", "device": "/dev/input/js0", "configured": True},
                {"type": "ps4", "device": "/dev/input/js1", "configured": False},
            ],
            roms={
                "systems": ["n64", "psx", "snes"],
                "counts": {"n64": 25, "psx": 50, "snes": 100},
            },
            custom_configs=[],
            known_issues=[],
            hardware=None,
            network=None,
            software=None,
            services=None,
            notes=None,
        )

    # Success cases
    def test_execute_returns_result_success_when_load_state_succeeds(
        self, use_case, mock_state_repo, sample_system_state
    ):
        """Test that execute returns Result.success when loading state succeeds."""
        # Arrange
        request = StateManagementRequest(action=StateAction.LOAD)
        mock_state_repo.load_state.return_value = sample_system_state

        # Act
        result = use_case.execute(request)

        # Assert
        assert isinstance(result, Result)
        assert result.is_success()
        assert not result.is_error()
        value = result.value
        assert value.success is True
        assert value.action == StateAction.LOAD
        assert value.message == "State loaded successfully"
        assert value.state == sample_system_state

    def test_execute_returns_result_success_when_save_state_succeeds(
        self,
        use_case,
        mock_state_repo,
        mock_system_repo,
        mock_emulator_repo,
        mock_controller_repo,
    ):
        """Test that execute returns Result.success when saving state succeeds."""
        # Arrange
        request = StateManagementRequest(action=StateAction.SAVE, force_scan=True)

        # Mock system info
        system_info = SystemInfo(
            hostname="retropie",
            cpu_temperature=45.2,
            memory_total=4096,
            memory_used=2048,
            memory_free=2048,
            disk_total=32000,
            disk_used=16000,
            disk_free=16000,
            load_average=[0.5, 0.6, 0.7],
            uptime=86400,
        )
        mock_system_repo.get_system_info.return_value = Result.success(system_info)

        # Mock emulators
        emulators = [
            Emulator(name="mupen64plus", system="n64", status=EmulatorStatus.INSTALLED),
            Emulator(
                name="pcsx-rearmed", system="psx", status=EmulatorStatus.INSTALLED
            ),
            Emulator(name="snes9x", system="snes", status=EmulatorStatus.INSTALLED),
        ]
        mock_emulator_repo.get_emulators.return_value = emulators

        # Mock controllers
        controllers = [
            Controller(
                name="Xbox Controller",
                device_path="/dev/input/js0",
                controller_type=ControllerType.XBOX,
                connected=True,
                is_configured=True,
            ),
        ]
        mock_controller_repo.detect_controllers.return_value = controllers

        # Mock ROM directories
        rom_dirs = [
            RomDirectory(
                system="n64",
                path="/home/pi/RetroPie/roms/n64",
                rom_count=25,
                total_size=1024000000,
                supported_extensions=[".n64"],
            ),
            RomDirectory(
                system="psx",
                path="/home/pi/RetroPie/roms/psx",
                rom_count=50,
                total_size=2048000000,
                supported_extensions=[".bin"],
            ),
        ]
        mock_emulator_repo.get_rom_directories.return_value = rom_dirs

        # Mock save result
        save_result = StateManagementResult(
            success=True,
            action=StateAction.SAVE,
            message="State saved successfully",
        )
        mock_state_repo.save_state.return_value = save_result

        # Act
        result = use_case.execute(request)

        # Assert
        assert isinstance(result, Result)
        assert result.is_success()
        assert result.value.success is True
        assert result.value.action == StateAction.SAVE
        assert "saved successfully" in result.value.message

    def test_execute_returns_result_success_when_update_state_succeeds(
        self, use_case, mock_state_repo
    ):
        """Test that execute returns Result.success when updating state succeeds."""
        # Arrange
        request = StateManagementRequest(
            action=StateAction.UPDATE,
            path="emulators.preferred.n64",
            value="parallel-n64",
        )

        update_result = StateManagementResult(
            success=True,
            action=StateAction.UPDATE,
            message="State field updated successfully",
        )
        mock_state_repo.update_state_field.return_value = update_result

        # Act
        result = use_case.execute(request)

        # Assert
        assert isinstance(result, Result)
        assert result.is_success()
        assert result.value.success is True
        assert result.value.action == StateAction.UPDATE

    def test_execute_returns_result_success_when_compare_state_succeeds(
        self,
        use_case,
        mock_state_repo,
        mock_system_repo,
        mock_emulator_repo,
        mock_controller_repo,
        sample_system_state,
    ):
        """Test that execute returns Result.success when comparing state succeeds."""
        # Arrange
        request = StateManagementRequest(action=StateAction.COMPARE)

        # Mock load state
        mock_state_repo.load_state.return_value = sample_system_state

        # Mock system info for current state
        system_info = SystemInfo(
            hostname="retropie",
            cpu_temperature=50.1,  # Changed
            memory_total=4096,
            memory_used=3072,  # Changed
            memory_free=1024,  # Changed
            disk_total=32000,
            disk_used=16000,
            disk_free=16000,
            load_average=[0.8, 0.9, 1.0],  # Changed
            uptime=172800,  # Changed
        )
        mock_system_repo.get_system_info.return_value = Result.success(system_info)

        # Mock other repositories (same as save test)
        mock_emulator_repo.get_emulators.return_value = [
            Emulator(name="mupen64plus", system="n64", status=EmulatorStatus.INSTALLED),
        ]
        mock_controller_repo.detect_controllers.return_value = []
        mock_emulator_repo.get_rom_directories.return_value = []

        # Mock compare result
        diff = {
            "system.cpu_temperature": {"old": 45.2, "new": 50.1},
            "system.memory_used": {"old": 2048, "new": 3072},
        }
        mock_state_repo.compare_state.return_value = diff

        compare_result = StateManagementResult(
            success=True,
            action=StateAction.COMPARE,
            message="State comparison complete",
            diff=diff,
        )

        # Act
        result = use_case.execute(request)

        # Assert
        assert isinstance(result, Result)
        assert result.is_success()
        assert result.value.success is True
        assert result.value.action == StateAction.COMPARE
        assert result.value.diff == diff

    # Error cases
    def test_execute_returns_result_error_when_invalid_action(self, use_case):
        """Test that execute returns Result.error for invalid action."""
        # Arrange
        request = Mock(spec=StateManagementRequest)
        request.action = "invalid_action"  # Not a valid StateAction

        # Act
        result = use_case.execute(request)

        # Assert
        assert isinstance(result, Result)
        assert result.is_error()
        assert isinstance(result.error_or_none, ValidationError)
        assert result.error_or_none.code == "UNKNOWN_ACTION"
        assert "Unknown action" in result.error_or_none.message

    def test_execute_returns_result_error_when_load_state_file_not_found(
        self, use_case, mock_state_repo
    ):
        """Test that execute returns Result.error when state file not found."""
        # Arrange
        request = StateManagementRequest(action=StateAction.LOAD)
        mock_state_repo.load_state.side_effect = FileNotFoundError(
            "State file not found"
        )

        # Act
        result = use_case.execute(request)

        # Assert
        assert isinstance(result, Result)
        assert result.is_error()
        assert isinstance(result.error_or_none, ValidationError)
        assert result.error_or_none.code == "STATE_FILE_NOT_FOUND"
        assert "State file not found" in result.error_or_none.message

    def test_execute_returns_result_error_when_update_missing_path_or_value(
        self, use_case
    ):
        """Test that execute returns Result.error when update is missing path or value."""
        # Arrange
        request = StateManagementRequest(
            action=StateAction.UPDATE
        )  # Missing path and value

        # Act
        result = use_case.execute(request)

        # Assert
        assert isinstance(result, Result)
        assert result.is_error()
        assert isinstance(result.error_or_none, ValidationError)
        assert result.error_or_none.code == "MISSING_UPDATE_PARAMS"
        assert "Path and value required" in result.error_or_none.message

    def test_execute_returns_result_error_when_system_repo_fails(
        self,
        use_case,
        mock_system_repo,
        mock_emulator_repo,
        mock_controller_repo,
        mock_state_repo,
    ):
        """Test that execute returns Result.error when system repository fails."""
        # Arrange
        request = StateManagementRequest(action=StateAction.SAVE)

        # Mock system repo to return error Result
        mock_system_repo.get_system_info.return_value = Result.error(
            ConnectionError(
                code="SSH_CONNECTION_FAILED", message="Failed to connect to SSH"
            )
        )

        # Act
        result = use_case.execute(request)

        # Assert
        assert isinstance(result, Result)
        assert result.is_error()
        assert isinstance(result.error_or_none, ConnectionError)
        assert result.error_or_none.code == "SSH_CONNECTION_FAILED"

    def test_execute_returns_result_error_when_repository_throws_exception(
        self,
        use_case,
        mock_system_repo,
        mock_emulator_repo,
        mock_controller_repo,
        mock_state_repo,
    ):
        """Test that execute returns Result.error when repository throws exception."""
        # Arrange
        request = StateManagementRequest(action=StateAction.SAVE)

        # Mock system info success
        system_info = SystemInfo(
            hostname="retropie",
            cpu_temperature=45.2,
            memory_total=4096,
            memory_used=2048,
            memory_free=2048,
            disk_total=32000,
            disk_used=16000,
            disk_free=16000,
            load_average=[0.5, 0.6, 0.7],
            uptime=86400,
        )
        mock_system_repo.get_system_info.return_value = Result.success(system_info)

        # Mock emulator repo to throw exception
        mock_emulator_repo.get_emulators.side_effect = OSError("Connection lost")

        # Act
        result = use_case.execute(request)

        # Assert
        assert isinstance(result, Result)
        assert result.is_error()
        assert isinstance(result.error_or_none, ConnectionError)
        assert "Connection lost" in result.error_or_none.message

    def test_execute_returns_result_error_when_compare_without_stored_state(
        self,
        use_case,
        mock_state_repo,
        mock_system_repo,
        mock_emulator_repo,
        mock_controller_repo,
    ):
        """Test that execute returns Result.error when comparing without stored state."""
        # Arrange
        request = StateManagementRequest(action=StateAction.COMPARE)

        # Mock load state to raise FileNotFoundError
        mock_state_repo.load_state.side_effect = FileNotFoundError("No state file")

        # Act
        result = use_case.execute(request)

        # Assert
        assert isinstance(result, Result)
        assert result.is_error()
        assert isinstance(result.error_or_none, ValidationError)
        assert result.error_or_none.code == "NO_STORED_STATE"
        assert "No stored state to compare" in result.error_or_none.message

    # Edge cases
    def test_execute_handles_empty_emulator_list(
        self,
        use_case,
        mock_state_repo,
        mock_system_repo,
        mock_emulator_repo,
        mock_controller_repo,
    ):
        """Test that execute handles empty emulator list correctly."""
        # Arrange
        request = StateManagementRequest(action=StateAction.SAVE)

        # Mock system info
        system_info = SystemInfo(
            hostname="retropie",
            cpu_temperature=45.2,
            memory_total=4096,
            memory_used=2048,
            memory_free=2048,
            disk_total=32000,
            disk_used=16000,
            disk_free=16000,
            load_average=[0.5, 0.6, 0.7],
            uptime=86400,
        )
        mock_system_repo.get_system_info.return_value = Result.success(system_info)

        # Mock empty emulators
        mock_emulator_repo.get_emulators.return_value = []
        mock_controller_repo.detect_controllers.return_value = []
        mock_emulator_repo.get_rom_directories.return_value = []

        save_result = StateManagementResult(
            success=True,
            action=StateAction.SAVE,
            message="State saved successfully",
        )
        mock_state_repo.save_state.return_value = save_result

        # Act
        result = use_case.execute(request)

        # Assert
        assert isinstance(result, Result)
        assert result.is_success()
        # Verify the state was built with empty emulators
        mock_state_repo.save_state.assert_called_once()
        saved_state = mock_state_repo.save_state.call_args[0][0]
        assert saved_state.emulators["installed"] == []
        assert saved_state.emulators["preferred"] == {}

    def test_execute_handles_repository_returning_non_result_types(
        self,
        use_case,
        mock_state_repo,
        mock_system_repo,
        mock_emulator_repo,
        mock_controller_repo,
    ):
        """Test that execute handles repositories that don't return Result types."""
        # Arrange
        request = StateManagementRequest(action=StateAction.SAVE)

        # Mock system repo returning non-Result (backward compatibility)
        system_info = SystemInfo(
            hostname="retropie",
            cpu_temperature=45.2,
            memory_total=4096,
            memory_used=2048,
            memory_free=2048,
            disk_total=32000,
            disk_used=16000,
            disk_free=16000,
            load_average=[0.5, 0.6, 0.7],
            uptime=86400,
        )
        # Return raw SystemInfo instead of Result
        mock_system_repo.get_system_info.return_value = system_info

        # Mock other repos
        mock_emulator_repo.get_emulators.return_value = []
        mock_controller_repo.detect_controllers.return_value = []
        mock_emulator_repo.get_rom_directories.return_value = []

        save_result = StateManagementResult(
            success=True,
            action=StateAction.SAVE,
            message="State saved successfully",
        )
        mock_state_repo.save_state.return_value = save_result

        # Act
        result = use_case.execute(request)

        # Assert
        assert isinstance(result, Result)
        assert result.is_success()
