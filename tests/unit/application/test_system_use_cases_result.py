"""Tests for Result pattern conversion in system use cases.

Following TDD approach - these tests will initially fail until use cases handle Result types.
"""

from unittest.mock import Mock

from retromcp.application.system_use_cases import GetSystemInfoUseCase
from retromcp.application.system_use_cases import UpdateSystemUseCase
from retromcp.domain.models import CommandResult
from retromcp.domain.models import ConnectionError
from retromcp.domain.models import ExecutionError
from retromcp.domain.models import Result
from retromcp.domain.models import SystemInfo
from retromcp.domain.models import ValidationError
from retromcp.domain.ports import SystemRepository


class TestGetSystemInfoUseCaseResult:
    """Test Result pattern conversion in GetSystemInfoUseCase."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_system_repo = Mock(spec=SystemRepository)
        self.use_case = GetSystemInfoUseCase(self.mock_system_repo)

    def test_execute_returns_result_success_when_system_info_retrieved(self):
        """Test that execute returns Result.success when system info is retrieved successfully."""
        # Arrange
        system_info = SystemInfo(
            hostname="retropie",
            cpu_temperature=45.2,
            memory_total=4096000000,
            memory_used=2048000000,
            memory_free=2048000000,
            disk_total=64000000000,
            disk_used=32000000000,
            disk_free=32000000000,
            load_average=[0.1, 0.2, 0.3],
            uptime=172800,
        )
        self.mock_system_repo.get_system_info.return_value = Result.success(system_info)

        # Act
        result = self.use_case.execute()

        # Assert
        assert isinstance(result, Result)
        assert result.is_success()
        assert not result.is_error()
        assert isinstance(result.value, SystemInfo)
        assert result.value.hostname == "retropie"
        assert result.value.cpu_temperature == 45.2

    def test_execute_returns_result_error_when_system_info_fails(self):
        """Test that execute returns Result.error when system info retrieval fails."""
        # Arrange
        execution_error = ExecutionError(
            code="SYSTEM_INFO_FAILED",
            message="Failed to retrieve system information",
            command="uname -a",
            exit_code=1,
            stderr="Command not found",
        )
        self.mock_system_repo.get_system_info.return_value = Result.error(
            execution_error
        )

        # Act
        result = self.use_case.execute()

        # Assert
        assert isinstance(result, Result)
        assert not result.is_success()
        assert result.is_error()
        assert isinstance(result.error_or_none, ExecutionError)
        assert result.error_or_none.code == "SYSTEM_INFO_FAILED"
        assert "Failed to retrieve system information" in result.error_or_none.message

    def test_execute_returns_result_error_when_connection_fails(self):
        """Test that execute returns Result.error when connection fails."""
        # Arrange
        connection_error = ConnectionError(
            code="CONNECTION_FAILED",
            message="Unable to connect to system",
            details={"host": "retropie.local", "port": 22},
        )
        self.mock_system_repo.get_system_info.return_value = Result.error(
            connection_error
        )

        # Act
        result = self.use_case.execute()

        # Assert
        assert isinstance(result, Result)
        assert not result.is_success()
        assert result.is_error()
        assert isinstance(result.error_or_none, ConnectionError)
        assert result.error_or_none.code == "CONNECTION_FAILED"
        assert "Unable to connect to system" in result.error_or_none.message


class TestUpdateSystemUseCaseResult:
    """Test Result pattern conversion in UpdateSystemUseCase."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_system_repo = Mock(spec=SystemRepository)
        self.use_case = UpdateSystemUseCase(self.mock_system_repo)

    def test_execute_returns_result_success_when_update_succeeds(self):
        """Test that execute returns Result.success when system update succeeds."""
        # Arrange
        update_result = CommandResult(
            command="sudo apt-get update && sudo apt-get upgrade -y",
            exit_code=0,
            stdout="System updated successfully",
            stderr="",
            success=True,
            execution_time=120.0,
        )
        self.mock_system_repo.update_system.return_value = Result.success(update_result)

        # Act
        result = self.use_case.execute()

        # Assert
        assert isinstance(result, Result)
        assert result.is_success()
        assert not result.is_error()
        assert isinstance(result.value, CommandResult)
        assert result.value.success is True
        assert "System updated successfully" in result.value.stdout

    def test_execute_returns_result_error_when_update_fails(self):
        """Test that execute returns Result.error when system update fails."""
        # Arrange
        execution_error = ExecutionError(
            code="UPDATE_FAILED",
            message="System update failed",
            command="sudo apt-get update && sudo apt-get upgrade -y",
            exit_code=100,
            stderr="E: Could not get lock /var/lib/dpkg/lock",
        )
        self.mock_system_repo.update_system.return_value = Result.error(execution_error)

        # Act
        result = self.use_case.execute()

        # Assert
        assert isinstance(result, Result)
        assert not result.is_success()
        assert result.is_error()
        assert isinstance(result.error_or_none, ExecutionError)
        assert result.error_or_none.code == "UPDATE_FAILED"
        assert "System update failed" in result.error_or_none.message

    def test_execute_returns_result_error_when_connection_fails(self):
        """Test that execute returns Result.error when connection fails."""
        # Arrange
        connection_error = ConnectionError(
            code="CONNECTION_FAILED",
            message="SSH connection lost during update",
            details={"operation": "system_update", "duration": "45s"},
        )
        self.mock_system_repo.update_system.return_value = Result.error(
            connection_error
        )

        # Act
        result = self.use_case.execute()

        # Assert
        assert isinstance(result, Result)
        assert not result.is_success()
        assert result.is_error()
        assert isinstance(result.error_or_none, ConnectionError)
        assert result.error_or_none.code == "CONNECTION_FAILED"
        assert "SSH connection lost during update" in result.error_or_none.message

    def test_execute_propagates_validation_errors_from_update_system(self):
        """Test that execute propagates ValidationError from update_system."""
        # Arrange
        validation_error = ValidationError(
            code="INVALID_STATE",
            message="System is not in a valid state for updates",
            details={"lock_held": True, "active_updates": 1},
        )
        self.mock_system_repo.update_system.return_value = Result.error(
            validation_error
        )

        # Act
        result = self.use_case.execute()

        # Assert
        assert isinstance(result, Result)
        assert not result.is_success()
        assert result.is_error()
        assert isinstance(result.error_or_none, ValidationError)
        assert result.error_or_none.code == "INVALID_STATE"
        assert "not in a valid state for updates" in result.error_or_none.message
