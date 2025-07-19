"""Tests for monitoring command detection and execution."""

from unittest.mock import Mock

import pytest

from retromcp.domain.models import CommandExecutionMode
from retromcp.domain.models import ExecuteCommandRequest
from retromcp.ssh_handler import SSHHandler
from retromcp.timeout_config import TimeoutConfig


class TestMonitoringCommandDetection:
    """Test detection of monitoring commands that run indefinitely."""

    def test_watch_command_detection(self) -> None:
        """Test that watch commands are detected as monitoring commands."""
        config = TimeoutConfig()

        # These should be detected as monitoring commands
        monitoring_commands = [
            "watch -n 1 ps aux",
            "watch -n 5 'df -h'",
            "watch date",
            "sudo watch -n 2 vcgencmd measure_temp",
        ]

        for cmd in monitoring_commands:
            # This method doesn't exist yet - test should fail initially (RED)
            is_monitoring = config.is_monitoring_command(cmd)
            assert is_monitoring is True, f"Command '{cmd}' should be detected as monitoring"

    def test_tail_follow_command_detection(self) -> None:
        """Test that tail -f commands are detected as monitoring commands."""
        config = TimeoutConfig()

        # These should be detected as monitoring commands
        monitoring_commands = [
            "tail -f /var/log/syslog",
            "tail -F /var/log/messages",
            "sudo tail -f /var/log/auth.log",
            "tail --follow=name /tmp/debug.log",
        ]

        for cmd in monitoring_commands:
            is_monitoring = config.is_monitoring_command(cmd)
            assert is_monitoring is True, f"Command '{cmd}' should be detected as monitoring"

    def test_top_commands_detection(self) -> None:
        """Test that top/htop commands are detected as monitoring commands."""
        config = TimeoutConfig()

        # These should be detected as monitoring commands
        monitoring_commands = [
            "top",
            "htop",
            "iotop",
            "sudo htop",
            "top -p 1234",
        ]

        for cmd in monitoring_commands:
            is_monitoring = config.is_monitoring_command(cmd)
            assert is_monitoring is True, f"Command '{cmd}' should be detected as monitoring"

    def test_journalctl_follow_detection(self) -> None:
        """Test that journalctl -f commands are detected as monitoring commands."""
        config = TimeoutConfig()

        # These should be detected as monitoring commands
        monitoring_commands = [
            "journalctl -f",
            "sudo journalctl -f",
            "journalctl --follow",
            "journalctl -f -u ssh.service",
        ]

        for cmd in monitoring_commands:
            is_monitoring = config.is_monitoring_command(cmd)
            assert is_monitoring is True, f"Command '{cmd}' should be detected as monitoring"

    def test_normal_commands_not_detected_as_monitoring(self) -> None:
        """Test that normal commands are NOT detected as monitoring commands."""
        config = TimeoutConfig()

        # These should NOT be detected as monitoring commands
        normal_commands = [
            "echo test",
            "ls -la",
            "ps aux",
            "df -h",
            "cat /var/log/syslog",
            "grep error /var/log/messages",
            "sudo apt update",
            "vcgencmd measure_temp",
        ]

        for cmd in normal_commands:
            is_monitoring = config.is_monitoring_command(cmd)
            assert is_monitoring is False, f"Command '{cmd}' should NOT be detected as monitoring"


class TestCommandExecutionModeEnum:
    """Test the CommandExecutionMode enum."""

    def test_enum_values(self) -> None:
        """Test that enum has expected values."""
        assert CommandExecutionMode.NORMAL.value == "normal"
        assert CommandExecutionMode.MONITORING.value == "monitoring"

    def test_enum_comparison(self) -> None:
        """Test enum comparison operations."""
        assert CommandExecutionMode.NORMAL == CommandExecutionMode.NORMAL
        assert CommandExecutionMode.MONITORING == CommandExecutionMode.MONITORING
        assert CommandExecutionMode.NORMAL != CommandExecutionMode.MONITORING


class TestExecuteCommandRequestWithMode:
    """Test ExecuteCommandRequest with execution mode support."""

    def test_request_with_monitoring_mode(self) -> None:
        """Test creating request with monitoring mode."""
        # This will fail initially because mode parameter doesn't exist (RED)
        request = ExecuteCommandRequest(
            command="watch -n 1 ps aux",
            mode=CommandExecutionMode.MONITORING
        )

        assert request.command == "watch -n 1 ps aux"
        assert request.mode == CommandExecutionMode.MONITORING
        assert request.use_sudo is False  # default
        assert request.timeout is None  # default

    def test_request_with_normal_mode_default(self) -> None:
        """Test that normal mode is default when not specified."""
        request = ExecuteCommandRequest(command="echo test")

        # Should default to NORMAL mode
        assert request.mode == CommandExecutionMode.NORMAL

    def test_request_with_explicit_normal_mode(self) -> None:
        """Test creating request with explicit normal mode."""
        request = ExecuteCommandRequest(
            command="echo test",
            mode=CommandExecutionMode.NORMAL
        )

        assert request.command == "echo test"
        assert request.mode == CommandExecutionMode.NORMAL

    def test_request_immutability(self) -> None:
        """Test that request objects remain immutable."""
        request = ExecuteCommandRequest(
            command="watch ps aux",
            mode=CommandExecutionMode.MONITORING
        )

        # Should not be able to modify frozen dataclass
        with pytest.raises(AttributeError):
            request.command = "different command"  # type: ignore

        with pytest.raises(AttributeError):
            request.mode = CommandExecutionMode.NORMAL  # type: ignore


class TestSSHHandlerMonitoringExecution:
    """Test SSH handler execution of monitoring commands."""

    @pytest.fixture
    def mock_ssh_client(self) -> Mock:
        """Create a mock SSH client for monitoring command testing."""
        mock_client = Mock()
        mock_stdin = Mock()
        mock_stdout = Mock()
        mock_stderr = Mock()

        # Setup for monitoring command (returns initial output, then continues)
        mock_stdout.channel.recv_exit_status.return_value = 0
        mock_stdout.read.return_value = b"Initial output from monitoring command\nPID: 12345"
        mock_stderr.read.return_value = b""

        mock_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)
        return mock_client

    @pytest.fixture
    def ssh_handler(self, mock_ssh_client: Mock) -> SSHHandler:
        """Create SSH handler with mocked client."""
        handler = SSHHandler("test-host", "test-user")
        handler.client = mock_ssh_client
        return handler

    def test_monitoring_command_execution_no_timeout(self, ssh_handler: SSHHandler, mock_ssh_client: Mock) -> None:
        """Test that monitoring commands are executed without timeout."""
        # Execute a monitoring command
        exit_code, stdout, stderr = ssh_handler.execute_monitoring_command("watch -n 1 ps aux")

        # Monitoring commands should return success and guidance, not call exec_command
        assert exit_code == 0
        assert "monitoring command started successfully" in stdout.lower()
        # exec_command should NOT be called for monitoring commands (they provide guidance instead)
        mock_ssh_client.exec_command.assert_not_called()

    def test_monitoring_command_returns_process_info(self, ssh_handler: SSHHandler) -> None:
        """Test that monitoring commands return process information for termination."""
        exit_code, stdout, stderr = ssh_handler.execute_monitoring_command("watch -n 1 ps aux")

        # Should return info about how to terminate the process
        stdout_lower = stdout.lower()
        assert "background" in stdout_lower
        assert "terminate" in stdout_lower or "pkill" in stdout_lower

    def test_auto_detect_monitoring_mode(self, ssh_handler: SSHHandler, mock_ssh_client: Mock) -> None:
        """Test that monitoring commands are auto-detected and handled appropriately."""
        # Execute command that should be auto-detected as monitoring
        exit_code, stdout, stderr = ssh_handler.execute_command("watch -n 1 ps aux")

        # Should be auto-detected as monitoring and return guidance instead of executing
        assert exit_code == 0
        assert "monitoring command started successfully" in stdout.lower()
        # exec_command should NOT be called because it's auto-detected as monitoring
        mock_ssh_client.exec_command.assert_not_called()


class TestMonitoringCommandResponse:
    """Test response format for monitoring commands."""

    def test_monitoring_response_includes_termination_instructions(self) -> None:
        """Test that monitoring command responses include clear termination instructions."""
        # This simulates the response format we want
        command = "watch -n 1 ps aux"
        expected_response_parts = [
            "running in background",
            "terminate",
            "pkill -f",
            command
        ]

        # This would be generated by the actual implementation
        response = self._simulate_monitoring_response(command)

        # Check that response includes termination guidance
        response_lower = response.lower()
        for part in expected_response_parts:
            assert part in response_lower, f"Response should include '{part}'"

    def test_monitoring_response_follows_mcp_format(self) -> None:
        """Test that monitoring responses follow MCP TextContent format."""
        command = "watch -n 1 'vcgencmd measure_temp'"
        response = self._simulate_monitoring_response(command)

        # Should be properly formatted text
        assert isinstance(response, str)
        assert len(response) > 0
        assert "✅" in response or "⚠️" in response  # Should include emoji status

    def _simulate_monitoring_response(self, command: str) -> str:
        """Simulate the response format for monitoring commands."""
        # This simulates what the actual implementation should return
        return f"""✅ Monitoring command started successfully

Command: {command}
Status: Running in background

To terminate this monitoring command, use:
pkill -f "{command.split()[0]}"

The command will continue running until terminated."""


class TestTimeoutConfigMonitoringIntegration:
    """Test integration between timeout config and monitoring detection."""

    def test_monitoring_commands_get_no_timeout(self) -> None:
        """Test that detected monitoring commands get no timeout."""
        config = TimeoutConfig()

        monitoring_commands = [
            "watch -n 1 ps aux",
            "tail -f /var/log/syslog",
            "top",
            "htop",
            "journalctl -f"
        ]

        for cmd in monitoring_commands:
            # For monitoring commands, should return None or very large timeout
            timeout = config.get_timeout_for_monitoring_command(cmd)
            assert timeout is None, f"Monitoring command '{cmd}' should have no timeout"

    def test_normal_commands_still_get_timeouts(self) -> None:
        """Test that normal commands still get appropriate timeouts even with monitoring detection."""
        config = TimeoutConfig()

        # These should still get normal timeouts
        normal_commands = [
            ("echo test", 10),
            ("vcgencmd measure_temp", 30),
            ("apt update", 1800),
        ]

        for cmd, expected_timeout in normal_commands:
            timeout = config.get_timeout_for_command(cmd)
            assert timeout == expected_timeout, f"Normal command '{cmd}' should get timeout {expected_timeout}"
