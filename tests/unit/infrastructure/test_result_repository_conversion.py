"""Tests for Result pattern conversion in repository layer.

Following TDD approach - these tests will initially fail until repositories return Result types.
"""

from unittest.mock import Mock

from retromcp.config import RetroPieConfig
from retromcp.domain.models import ConnectionError
from retromcp.domain.models import ExecutionError
from retromcp.domain.models import Result
from retromcp.domain.models import SystemInfo
from retromcp.domain.models import ValidationError
from retromcp.domain.ports import RetroPieClient
from retromcp.infrastructure.cache_system import SystemCache
from retromcp.infrastructure.ssh_system_repository import SSHSystemRepository


class TestResultRepositoryConversion:
    """Test Result pattern conversion in repository layer."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = RetroPieConfig(
            host="test-host",
            username="test-user",
            password="test-pass",
        )
        self.mock_client = Mock(spec=RetroPieClient)
        self.cache = SystemCache()
        self.repository = SSHSystemRepository(self.mock_client, self.config, self.cache)

    def test_get_system_info_returns_result_success_when_data_available(self):
        """Test that get_system_info returns Result.success when data is available."""
        # Arrange
        cached_info = SystemInfo(
            hostname="test-hostname",
            cpu_temperature=42.0,
            memory_total=4000000000,
            memory_used=2000000000,
            memory_free=2000000000,
            disk_total=100000000000,
            disk_used=50000000000,
            disk_free=50000000000,
            load_average=[0.5, 0.3, 0.2],
            uptime=86400,
        )
        self.cache.cache_system_info(cached_info)

        # Act
        result = self.repository.get_system_info()

        # Assert
        assert isinstance(result, Result)
        assert result.is_success()
        assert not result.is_error()
        assert result.value == cached_info
        assert result.error_or_none is None

    def test_get_system_info_returns_result_error_when_client_connection_fails(self):
        """Test that get_system_info returns Result.error when client connection fails."""
        # Arrange - Mock client connection failure
        self.mock_client.execute_command.side_effect = Exception("Connection refused")

        # Act
        result = self.repository.get_system_info()

        # Assert
        assert isinstance(result, Result)
        assert not result.is_success()
        assert result.is_error()
        assert result.value is None
        assert isinstance(result.error_or_none, ConnectionError)
        assert "Connection refused" in result.error_or_none.message

    def test_get_system_info_returns_result_error_when_commands_fail(self):
        """Test that get_system_info returns Result.error when SSH commands fail."""
        # Arrange - Mock command failures (all commands return exit_code=1)
        from retromcp.domain.models import CommandResult

        self.mock_client.execute_command.return_value = CommandResult(
            command="hostname",
            exit_code=1,
            stdout="",
            stderr="Command failed",
            success=False,
            execution_time=0.1,
        )

        # Act
        result = self.repository.get_system_info()

        # Assert
        assert isinstance(result, Result)
        assert not result.is_success()
        assert result.is_error()
        assert result.value is None
        assert isinstance(result.error_or_none, ExecutionError)
        assert result.error_or_none.command == "hostname"
        assert result.error_or_none.exit_code == 1

    def test_get_system_info_returns_result_error_when_data_parsing_fails(self):
        """Test that get_system_info returns Result.error when data parsing fails."""
        # Arrange - Mock commands that return unparseable data
        from retromcp.domain.models import CommandResult

        self.mock_client.execute_command.side_effect = [
            CommandResult(
                command="hostname",
                exit_code=0,
                stdout="valid-hostname",
                stderr="",
                success=True,
                execution_time=0.1,
            ),
            CommandResult(
                command="vcgencmd measure_temp",
                exit_code=0,
                stdout="invalid-temp-data",  # Invalid format
                stderr="",
                success=True,
                execution_time=0.1,
            ),
        ]

        # Act
        result = self.repository.get_system_info()

        # Assert
        assert isinstance(result, Result)
        assert not result.is_success()
        assert result.is_error()
        assert result.value is None
        assert isinstance(result.error_or_none, ValidationError)
        assert "temperature" in result.error_or_none.message.lower()

    def test_get_packages_returns_result_success_when_packages_found(self):
        """Test that get_packages returns Result.success when packages are found."""
        # Arrange
        from retromcp.domain.models import CommandResult

        self.mock_client.execute_command.return_value = CommandResult(
            command="dpkg-query -W -f='${Package}|${Version}|${Status}\\n'",
            exit_code=0,
            stdout="vim|8.2.0|install ok installed\nhtop|3.0.5|install ok installed",
            stderr="",
            success=True,
            execution_time=0.1,
        )

        # Act
        result = self.repository.get_packages()

        # Assert
        assert isinstance(result, Result)
        assert result.is_success()
        assert not result.is_error()
        assert len(result.value) == 2
        assert result.value[0].name == "vim"
        assert result.value[1].name == "htop"

    def test_get_packages_returns_result_error_when_command_fails(self):
        """Test that get_packages returns Result.error when dpkg command fails."""
        # Arrange
        from retromcp.domain.models import CommandResult

        self.mock_client.execute_command.return_value = CommandResult(
            command="dpkg-query -W -f='${Package}|${Version}|${Status}\\n'",
            exit_code=1,
            stdout="",
            stderr="dpkg-query: no packages found",
            success=False,
            execution_time=0.1,
        )

        # Act
        result = self.repository.get_packages()

        # Assert
        assert isinstance(result, Result)
        assert not result.is_success()
        assert result.is_error()
        assert result.value is None
        assert isinstance(result.error_or_none, ExecutionError)
        assert "dpkg-query" in result.error_or_none.command

    def test_install_packages_returns_result_success_when_installation_succeeds(self):
        """Test that install_packages returns Result.success when installation succeeds."""
        # Arrange
        from retromcp.domain.models import CommandResult

        self.mock_client.execute_command.return_value = CommandResult(
            command="sudo apt-get update && sudo apt-get install -y vim htop",
            exit_code=0,
            stdout="Reading package lists...\nInstallation completed",
            stderr="",
            success=True,
            execution_time=5.0,
        )

        # Act
        result = self.repository.install_packages(["vim", "htop"])

        # Assert
        assert isinstance(result, Result)
        assert result.is_success()
        assert not result.is_error()
        assert "Installation completed" in result.value.stdout

    def test_install_packages_returns_result_error_when_installation_fails(self):
        """Test that install_packages returns Result.error when installation fails."""
        # Arrange
        from retromcp.domain.models import CommandResult

        self.mock_client.execute_command.return_value = CommandResult(
            command="sudo apt-get update && sudo apt-get install -y invalid-package",
            exit_code=100,
            stdout="",
            stderr="E: Unable to locate package invalid-package",
            success=False,
            execution_time=2.0,
        )

        # Act
        result = self.repository.install_packages(["invalid-package"])

        # Assert
        assert isinstance(result, Result)
        assert not result.is_success()
        assert result.is_error()
        assert result.value is None
        assert isinstance(result.error_or_none, ExecutionError)
        assert result.error_or_none.exit_code == 100
        assert "invalid-package" in result.error_or_none.stderr

    def test_install_packages_returns_result_success_when_no_packages_provided(self):
        """Test that install_packages returns Result.success when no packages provided."""
        # Act
        result = self.repository.install_packages([])

        # Assert
        assert isinstance(result, Result)
        assert result.is_success()
        assert not result.is_error()
        assert "No packages to install" in result.value.stdout
        # Should not call client when no packages provided
        self.mock_client.execute_command.assert_not_called()

    def test_install_packages_returns_result_error_with_validation_error_for_invalid_input(
        self,
    ):
        """Test that install_packages returns Result.error for invalid input."""
        # Act - None input should be validated
        result = self.repository.install_packages(None)

        # Assert
        assert isinstance(result, Result)
        assert not result.is_success()
        assert result.is_error()
        assert result.value is None
        assert isinstance(result.error_or_none, ValidationError)
        assert "packages" in result.error_or_none.message.lower()
