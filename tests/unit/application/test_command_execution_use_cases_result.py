"""Unit tests for Command Execution use cases with Result pattern."""

from unittest.mock import Mock

import pytest

from retromcp.application.system_use_cases import ExecuteCommandUseCase
from retromcp.application.system_use_cases import WriteFileUseCase
from retromcp.domain.models import CommandExecutionMode
from retromcp.domain.models import CommandResult
from retromcp.domain.models import ConnectionError
from retromcp.domain.models import ExecuteCommandRequest
from retromcp.domain.models import ExecutionError
from retromcp.domain.models import Result
from retromcp.domain.models import ValidationError
from retromcp.domain.models import WriteFileRequest
from retromcp.domain.ports import RetroPieClient


class TestExecuteCommandUseCaseResult:
    """Test ExecuteCommandUseCase with Result pattern."""

    @pytest.fixture
    def mock_client(self):
        """Create mock RetroPie client."""
        return Mock(spec=RetroPieClient)

    @pytest.fixture
    def use_case(self, mock_client):
        """Create ExecuteCommandUseCase instance."""
        return ExecuteCommandUseCase(mock_client)

    @pytest.fixture
    def sample_command_result(self):
        """Create sample command result."""
        return CommandResult(
            command="echo 'Hello World'",
            exit_code=0,
            stdout="Hello World\n",
            stderr="",
            success=True,
            execution_time=0.1,
        )

    # Success cases
    def test_execute_returns_result_success_when_command_succeeds(
        self, use_case, mock_client, sample_command_result
    ):
        """Test that execute returns Result.success when command execution succeeds."""
        # Arrange
        request = ExecuteCommandRequest(
            command="echo 'Hello World'",
            use_sudo=False,
            working_directory=None,
            timeout=None,
            mode=CommandExecutionMode.NORMAL,
        )
        mock_client.execute_command.return_value = sample_command_result

        # Act
        result = use_case.execute(request)

        # Assert
        assert isinstance(result, Result)
        assert result.is_success()
        assert not result.is_error()
        assert result.value == sample_command_result
        assert result.value.success is True
        assert result.value.stdout == "Hello World\n"
        mock_client.execute_command.assert_called_once_with("echo 'Hello World'")

    def test_execute_returns_result_success_when_sudo_command_succeeds(
        self, use_case, mock_client
    ):
        """Test that execute returns Result.success when sudo command succeeds."""
        # Arrange
        request = ExecuteCommandRequest(
            command="apt-get update",
            use_sudo=True,
            working_directory=None,
            timeout=None,
            mode=CommandExecutionMode.NORMAL,
        )
        expected_result = CommandResult(
            command="sudo apt-get update",
            exit_code=0,
            stdout="Reading package lists... Done\n",
            stderr="",
            success=True,
            execution_time=5.2,
        )
        mock_client.execute_command.return_value = expected_result

        # Act
        result = use_case.execute(request)

        # Assert
        assert isinstance(result, Result)
        assert result.is_success()
        assert result.value.success is True
        assert "Reading package lists... Done" in result.value.stdout
        mock_client.execute_command.assert_called_once_with("sudo apt-get update")

    def test_execute_returns_result_success_when_command_with_timeout_succeeds(
        self, use_case, mock_client
    ):
        """Test that execute returns Result.success when command with timeout succeeds."""
        # Arrange
        request = ExecuteCommandRequest(
            command="ping -c 3 google.com",
            use_sudo=False,
            working_directory=None,
            timeout=10,
            mode=CommandExecutionMode.NORMAL,
        )
        expected_result = CommandResult(
            command="timeout 10 ping -c 3 google.com",
            exit_code=0,
            stdout="PING google.com (142.250.191.14) 56(84) bytes of data.\n",
            stderr="",
            success=True,
            execution_time=3.1,
        )
        mock_client.execute_command.return_value = expected_result

        # Act
        result = use_case.execute(request)

        # Assert
        assert isinstance(result, Result)
        assert result.is_success()
        assert "PING google.com" in result.value.stdout
        mock_client.execute_command.assert_called_once_with(
            "timeout 10 ping -c 3 google.com"
        )

    def test_execute_returns_result_success_when_monitoring_command_succeeds(
        self, use_case, mock_client
    ):
        """Test that execute returns Result.success when monitoring command succeeds."""
        # Arrange
        request = ExecuteCommandRequest(
            command="top -n 1",
            use_sudo=False,
            working_directory=None,
            timeout=None,
            mode=CommandExecutionMode.MONITORING,
        )
        expected_result = CommandResult(
            command="top -n 1",
            exit_code=0,
            stdout="top - 15:30:01 up 1 day,  2:15,  1 user\n",
            stderr="",
            success=True,
            execution_time=1.0,
        )
        mock_client.execute_monitoring_command.return_value = expected_result

        # Act
        result = use_case.execute(request)

        # Assert
        assert isinstance(result, Result)
        assert result.is_success()
        assert "top - 15:30:01" in result.value.stdout
        mock_client.execute_monitoring_command.assert_called_once_with("top -n 1")

    def test_execute_returns_result_success_when_safe_pipe_command_succeeds(
        self, use_case, mock_client
    ):
        """Test that execute returns Result.success when safe pipe command succeeds."""
        # Arrange
        request = ExecuteCommandRequest(
            command="ps aux | grep python",
            use_sudo=False,
            working_directory=None,
            timeout=None,
            mode=CommandExecutionMode.NORMAL,
        )
        expected_result = CommandResult(
            command="ps aux | grep python",
            exit_code=0,
            stdout="pi        1234  0.1  0.5  12345  6789 ?        S    14:30   0:00 python3 script.py\n",
            stderr="",
            success=True,
            execution_time=0.2,
        )
        mock_client.execute_command.return_value = expected_result

        # Act
        result = use_case.execute(request)

        # Assert
        assert isinstance(result, Result)
        assert result.is_success()
        assert "python3 script.py" in result.value.stdout

    # Error cases
    def test_execute_returns_result_error_when_dangerous_command_detected(
        self, use_case, mock_client
    ):
        """Test that execute returns Result.error when dangerous command is detected."""
        # Arrange
        request = ExecuteCommandRequest(
            command="rm -rf /",
            use_sudo=False,
            working_directory=None,
            timeout=None,
            mode=CommandExecutionMode.NORMAL,
        )

        # Act
        result = use_case.execute(request)

        # Assert
        assert isinstance(result, Result)
        assert result.is_error()
        assert isinstance(result.error_or_none, ValidationError)
        assert result.error_or_none.code == "DANGEROUS_COMMAND"
        assert "dangerous pattern" in result.error_or_none.message
        mock_client.execute_command.assert_not_called()

    def test_execute_returns_result_error_when_command_injection_detected(
        self, use_case, mock_client
    ):
        """Test that execute returns Result.error when command injection is detected."""
        # Arrange - use a command that has dangerous operators but no dangerous patterns
        request = ExecuteCommandRequest(
            command="echo hello; cat /etc/hostname",
            use_sudo=False,
            working_directory=None,
            timeout=None,
            mode=CommandExecutionMode.NORMAL,
        )

        # Act
        result = use_case.execute(request)

        # Assert
        assert isinstance(result, Result)
        assert result.is_error()
        assert isinstance(result.error_or_none, ValidationError)
        assert result.error_or_none.code == "COMMAND_INJECTION"
        assert "dangerous operators" in result.error_or_none.message

    def test_execute_returns_result_error_when_command_substitution_detected(
        self, use_case, mock_client
    ):
        """Test that execute returns Result.error when command substitution is detected."""
        # Arrange
        request = ExecuteCommandRequest(
            command="echo $(cat /etc/passwd)",
            use_sudo=False,
            working_directory=None,
            timeout=None,
            mode=CommandExecutionMode.NORMAL,
        )

        # Act
        result = use_case.execute(request)

        # Assert
        assert isinstance(result, Result)
        assert result.is_error()
        assert isinstance(result.error_or_none, ValidationError)
        assert result.error_or_none.code == "DANGEROUS_COMMAND"
        assert "dangerous pattern" in result.error_or_none.message

    def test_execute_returns_result_error_when_client_throws_exception(
        self, use_case, mock_client
    ):
        """Test that execute returns Result.error when client throws exception."""
        # Arrange
        request = ExecuteCommandRequest(
            command="echo 'test'",
            use_sudo=False,
            working_directory=None,
            timeout=None,
            mode=CommandExecutionMode.NORMAL,
        )
        mock_client.execute_command.side_effect = ConnectionError(
            code="SSH_CONNECTION_LOST",
            message="SSH connection was lost during command execution",
        )

        # Act
        result = use_case.execute(request)

        # Assert
        assert isinstance(result, Result)
        assert result.is_error()
        assert isinstance(result.error_or_none, ExecutionError)
        assert result.error_or_none.code == "COMMAND_EXECUTION_FAILED"
        assert "Command execution failed" in result.error_or_none.message

    def test_execute_returns_result_error_when_monitoring_command_fails(
        self, use_case, mock_client
    ):
        """Test that execute returns Result.error when monitoring command fails."""
        # Arrange
        request = ExecuteCommandRequest(
            command="top",
            use_sudo=False,
            working_directory=None,
            timeout=None,
            mode=CommandExecutionMode.MONITORING,
        )
        mock_client.execute_monitoring_command.side_effect = OSError(
            "Terminal not available"
        )

        # Act
        result = use_case.execute(request)

        # Assert
        assert isinstance(result, Result)
        assert result.is_error()
        assert isinstance(result.error_or_none, ExecutionError)
        assert result.error_or_none.code == "MONITORING_COMMAND_FAILED"
        assert "Monitoring command execution failed" in result.error_or_none.message

    # Edge cases
    def test_execute_handles_command_with_existing_sudo(self, use_case, mock_client):
        """Test that execute handles commands that already have sudo."""
        # Arrange
        request = ExecuteCommandRequest(
            command="sudo systemctl status ssh",
            use_sudo=True,  # Should not add another sudo
            working_directory=None,
            timeout=None,
            mode=CommandExecutionMode.NORMAL,
        )
        expected_result = CommandResult(
            command="sudo systemctl status ssh",
            exit_code=0,
            stdout="● ssh.service - OpenBSD Secure Shell server\n",
            stderr="",
            success=True,
            execution_time=0.3,
        )
        mock_client.execute_command.return_value = expected_result

        # Act
        result = use_case.execute(request)

        # Assert
        assert isinstance(result, Result)
        assert result.is_success()
        # Should not have double sudo
        mock_client.execute_command.assert_called_once_with("sudo systemctl status ssh")

    def test_execute_handles_empty_command(self, use_case, mock_client):
        """Test that execute handles empty command."""
        # Arrange
        request = ExecuteCommandRequest(
            command="",
            use_sudo=False,
            working_directory=None,
            timeout=None,
            mode=CommandExecutionMode.NORMAL,
        )

        # Act
        result = use_case.execute(request)

        # Assert
        assert isinstance(result, Result)
        assert result.is_error()
        assert isinstance(result.error_or_none, ValidationError)
        assert result.error_or_none.code == "EMPTY_COMMAND"
        assert "empty" in result.error_or_none.message.lower()

    def test_execute_handles_complex_safe_pipe_commands(self, use_case, mock_client):
        """Test that execute handles complex but safe pipe commands."""
        # Arrange
        request = ExecuteCommandRequest(
            command="cat /proc/meminfo | grep MemTotal | head -1",
            use_sudo=False,
            working_directory=None,
            timeout=None,
            mode=CommandExecutionMode.NORMAL,
        )
        expected_result = CommandResult(
            command="cat /proc/meminfo | grep MemTotal | head -1",
            exit_code=0,
            stdout="MemTotal:        4194304 kB\n",
            stderr="",
            success=True,
            execution_time=0.1,
        )
        mock_client.execute_command.return_value = expected_result

        # Act
        result = use_case.execute(request)

        # Assert
        assert isinstance(result, Result)
        assert result.is_success()
        assert "MemTotal:" in result.value.stdout


class TestWriteFileUseCaseResult:
    """Test WriteFileUseCase with Result pattern."""

    @pytest.fixture
    def mock_client(self):
        """Create mock RetroPie client."""
        return Mock(spec=RetroPieClient)

    @pytest.fixture
    def use_case(self, mock_client):
        """Create WriteFileUseCase instance."""
        return WriteFileUseCase(mock_client)

    # Success cases
    def test_execute_returns_result_success_when_file_write_succeeds(
        self, use_case, mock_client
    ):
        """Test that execute returns Result.success when file write succeeds."""
        # Arrange
        request = WriteFileRequest(path="/home/pi/test.txt", content="Hello, World!")

        # Mock mkdir command result
        mkdir_result = CommandResult(
            command="mkdir -p /home/pi",
            exit_code=0,
            stdout="",
            stderr="",
            success=True,
            execution_time=0.05,
        )

        # Mock file write command result
        write_result = CommandResult(
            command="cat > '/home/pi/test.txt' << 'EOF'\nHello, World!\nEOF",
            exit_code=0,
            stdout="",
            stderr="",
            success=True,
            execution_time=0.1,
        )

        # Set up mock to return different results for different calls
        mock_client.execute_command.side_effect = [mkdir_result, write_result]

        # Act
        result = use_case.execute(request)

        # Assert
        assert isinstance(result, Result)
        assert result.is_success()
        assert result.value == write_result  # Should return the final write result
        assert result.value.success is True
        assert mock_client.execute_command.call_count == 2

    def test_execute_returns_result_success_when_config_file_write_succeeds(
        self, use_case, mock_client
    ):
        """Test that execute returns Result.success when config file write succeeds."""
        # Arrange
        request = WriteFileRequest(
            path="/opt/retropie/configs/all/retroarch.cfg",
            content='input_driver = "sdl2"\nvideo_driver = "gl"',
        )
        expected_result = CommandResult(
            command="cat > '/opt/retropie/configs/all/retroarch.cfg' << 'EOF'\ninput_driver = \"sdl2\"\nvideo_driver = \"gl\"\nEOF",
            exit_code=0,
            stdout="",
            stderr="",
            success=True,
            execution_time=0.2,
        )
        mock_client.execute_command.return_value = expected_result

        # Act
        result = use_case.execute(request)

        # Assert
        assert isinstance(result, Result)
        assert result.is_success()
        assert result.value.success is True

    # Error cases
    def test_execute_returns_result_error_when_path_traversal_detected(
        self, use_case, mock_client
    ):
        """Test that execute returns Result.error when path traversal is detected."""
        # Arrange
        request = WriteFileRequest(
            path="/home/pi/../../../etc/passwd", content="malicious content"
        )

        # Act
        result = use_case.execute(request)

        # Assert
        assert isinstance(result, Result)
        assert result.is_error()
        assert isinstance(result.error_or_none, ValidationError)
        assert result.error_or_none.code == "PATH_TRAVERSAL"
        assert "path traversal" in result.error_or_none.message.lower()
        mock_client.execute_command.assert_not_called()

    def test_execute_returns_result_error_when_sensitive_path_detected(
        self, use_case, mock_client
    ):
        """Test that execute returns Result.error when writing to sensitive path."""
        # Arrange
        request = WriteFileRequest(path="/etc/passwd", content="malicious content")

        # Act
        result = use_case.execute(request)

        # Assert
        assert isinstance(result, Result)
        assert result.is_error()
        assert isinstance(result.error_or_none, ValidationError)
        assert result.error_or_none.code == "SENSITIVE_PATH"
        assert "sensitive path" in result.error_or_none.message.lower()

    def test_execute_returns_result_error_when_relative_path_used(
        self, use_case, mock_client
    ):
        """Test that execute returns Result.error when relative path is used."""
        # Arrange
        request = WriteFileRequest(path="relative/path/file.txt", content="content")

        # Act
        result = use_case.execute(request)

        # Assert
        assert isinstance(result, Result)
        assert result.is_error()
        assert isinstance(result.error_or_none, ValidationError)
        assert result.error_or_none.code == "RELATIVE_PATH"
        assert "absolute path" in result.error_or_none.message.lower()

    def test_execute_returns_result_error_when_repository_fails(
        self, use_case, mock_client
    ):
        """Test that execute returns Result.error when repository fails."""
        # Arrange
        request = WriteFileRequest(path="/home/pi/test.txt", content="content")
        mock_client.execute_command.side_effect = OSError("Permission denied")

        # Act
        result = use_case.execute(request)

        # Assert
        assert isinstance(result, Result)
        assert result.is_error()
        assert isinstance(result.error_or_none, ConnectionError)
        assert result.error_or_none.code == "FILE_WRITE_CONNECTION_FAILED"
        assert "Failed to connect for file write" in result.error_or_none.message

    # Edge cases
    def test_execute_handles_empty_content(self, use_case, mock_client):
        """Test that execute handles empty content."""
        # Arrange
        request = WriteFileRequest(path="/home/pi/empty.txt", content="")
        expected_result = CommandResult(
            command="touch /home/pi/empty.txt",
            exit_code=0,
            stdout="",
            stderr="",
            success=True,
            execution_time=0.05,
        )
        mock_client.execute_command.return_value = expected_result

        # Act
        result = use_case.execute(request)

        # Assert
        assert isinstance(result, Result)
        assert result.is_success()
        assert result.value.success is True

    def test_execute_handles_special_characters_in_content(self, use_case, mock_client):
        """Test that execute handles special characters in content."""
        # Arrange
        request = WriteFileRequest(
            path="/home/pi/special.txt",
            content="Special chars: !@#$%^&*(){}[]|\\:;\"'<>?,./",
        )
        expected_result = CommandResult(
            command="cat > /home/pi/special.txt",
            exit_code=0,
            stdout="",
            stderr="",
            success=True,
            execution_time=0.1,
        )
        mock_client.execute_command.return_value = expected_result

        # Act
        result = use_case.execute(request)

        # Assert
        assert isinstance(result, Result)
        assert result.is_success()
        assert result.value.success is True

    def test_execute_validates_multiple_sensitive_paths(self, use_case, mock_client):
        """Test that execute validates against multiple sensitive paths."""
        sensitive_paths = [
            "/etc/shadow",
            "/etc/sudoers",
            "/etc/ssh/sshd_config",
            "/root/.bashrc",
            "/var/log/syslog",
            "/proc/version",
            "/sys/kernel/hostname",
            "/dev/random",
            "/boot/config.txt",
        ]

        for path in sensitive_paths:
            # Arrange
            request = WriteFileRequest(path=path, content="malicious")

            # Act
            result = use_case.execute(request)

            # Assert
            assert isinstance(result, Result)
            assert result.is_error()
            assert isinstance(result.error_or_none, ValidationError)
            assert result.error_or_none.code == "SENSITIVE_PATH"
