"""Tests for timeout handling and hanging prevention."""

from unittest.mock import Mock

import pytest
from paramiko import SSHException

from retromcp.ssh_handler import SSHHandler
from retromcp.timeout_config import TimeoutConfig
from retromcp.timeout_config import get_timeout_config


class TestTimeoutConfig:
    """Test timeout configuration and command classification."""

    def test_quick_command_timeout(self) -> None:
        """Test that quick commands get short timeouts."""
        config = TimeoutConfig()

        quick_commands = ["echo test", "pwd", "whoami", "date", "hostname"]

        for cmd in quick_commands:
            timeout = config.get_timeout_for_command(cmd)
            assert timeout == config.quick_commands
            assert timeout == 10

    def test_system_info_timeout(self) -> None:
        """Test that system info commands get appropriate timeouts."""
        config = TimeoutConfig()

        system_commands = ["vcgencmd measure_temp", "free -m", "df -h", "lscpu"]

        for cmd in system_commands:
            timeout = config.get_timeout_for_command(cmd)
            assert timeout == config.system_info
            assert timeout == 30

    def test_package_operation_timeout(self) -> None:
        """Test that package operations get appropriate timeouts."""
        config = TimeoutConfig()

        # Regular package operations
        package_commands = [
            "sudo apt-get install package",
            "dpkg -i package.deb",
            "pip install package",
        ]

        for cmd in package_commands:
            timeout = config.get_timeout_for_command(cmd)
            assert timeout == config.package_operations
            assert timeout == 300

    def test_system_update_timeout(self) -> None:
        """Test that system update operations get very long timeouts."""
        config = TimeoutConfig()

        # System update operations (longer timeout)
        update_commands = [
            "apt update",
            "sudo apt-get update",
            "apt upgrade",
            "sudo apt-get upgrade -y",
        ]

        for cmd in update_commands:
            timeout = config.get_timeout_for_command(cmd)
            assert timeout == config.system_update
            assert timeout == 1800  # 30 minutes

    def test_retropie_setup_timeout(self) -> None:
        """Test that RetroPie setup gets very long timeout."""
        config = TimeoutConfig()

        retropie_commands = [
            "/home/pi/RetroPie-Setup/retropie_setup.sh",
            "retropie_setup update",
        ]

        for cmd in retropie_commands:
            timeout = config.get_timeout_for_command(cmd)
            assert timeout == config.retropie_setup
            assert timeout == 1800  # 30 minutes

    def test_controller_test_timeout(self) -> None:
        """Test that controller tests get short timeout."""
        config = TimeoutConfig()

        controller_commands = ["jstest /dev/input/js0", "evtest /dev/input/event0"]

        for cmd in controller_commands:
            timeout = config.get_timeout_for_command(cmd)
            assert timeout == config.controller_test
            assert timeout == 15

    def test_command_wrapping(self) -> None:
        """Test that commands are properly wrapped with timeout."""
        config = TimeoutConfig()

        # Test basic wrapping
        wrapped = config.wrap_command_with_timeout("echo test")
        assert wrapped.startswith("timeout ")
        assert "echo test" in wrapped

        # Test custom timeout
        wrapped = config.wrap_command_with_timeout("echo test", 30)
        assert "timeout 30" in wrapped

        # Test already wrapped command
        already_wrapped = "timeout 60 echo test"
        wrapped = config.wrap_command_with_timeout(already_wrapped)
        assert wrapped == already_wrapped  # Should not double-wrap

    def test_safe_retropie_command(self) -> None:
        """Test generation of safe RetroPie commands."""
        config = TimeoutConfig()

        safe_cmd = config.get_safe_retropie_command("update")
        assert "timeout" in safe_cmd
        assert "/home/pi/RetroPie-Setup/retropie_setup.sh" in safe_cmd
        assert "update" in safe_cmd


class TestSSHHandlerTimeout:
    """Test SSH handler timeout functionality."""

    @pytest.fixture
    def mock_ssh_client(self) -> Mock:
        """Create a mock SSH client."""
        mock_client = Mock()
        mock_stdin = Mock()
        mock_stdout = Mock()
        mock_stderr = Mock()

        # Setup normal execution
        mock_stdout.channel.recv_exit_status.return_value = 0
        mock_stdout.read.return_value = b"test output"
        mock_stderr.read.return_value = b""

        mock_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)
        return mock_client

    @pytest.fixture
    def ssh_handler(self, mock_ssh_client: Mock) -> SSHHandler:
        """Create SSH handler with mocked client."""
        handler = SSHHandler("test-host", "test-user")
        handler.client = mock_ssh_client
        return handler

    def test_execute_command_with_timeout(
        self, ssh_handler: SSHHandler, mock_ssh_client: Mock
    ) -> None:
        """Test that commands are executed with appropriate timeouts."""
        # Execute a quick command
        ssh_handler.execute_command("echo test")

        # Verify exec_command was called with timeout
        mock_ssh_client.exec_command.assert_called_once()
        args, kwargs = mock_ssh_client.exec_command.call_args
        assert "timeout" in kwargs

        # Quick commands should get 10 second timeout
        timeout_config = get_timeout_config()
        expected_timeout = timeout_config.get_timeout_for_command("echo test")
        assert kwargs["timeout"] == expected_timeout

    def test_execute_command_custom_timeout(
        self, ssh_handler: SSHHandler, mock_ssh_client: Mock
    ) -> None:
        """Test that custom timeouts override automatic detection."""
        # Execute with custom timeout
        ssh_handler.execute_command("echo test", custom_timeout=123)

        # Verify custom timeout was used
        args, kwargs = mock_ssh_client.exec_command.call_args
        assert kwargs["timeout"] == 123

    def test_timeout_exception_handling(
        self, ssh_handler: SSHHandler, mock_ssh_client: Mock
    ) -> None:
        """Test that timeout exceptions are properly handled."""
        # Mock a timeout exception
        mock_ssh_client.exec_command.side_effect = SSHException("Timeout")

        # Expect RuntimeError with timeout message
        with pytest.raises(RuntimeError) as exc_info:
            ssh_handler.execute_command("echo test")

        assert "timeout" in str(exc_info.value).lower()
        assert "echo test" in str(exc_info.value)

    def test_execute_command_safe_wrapping(
        self, ssh_handler: SSHHandler, mock_ssh_client: Mock
    ) -> None:
        """Test that execute_command_safe wraps commands with timeout."""
        # Execute a potentially hanging command
        ssh_handler.execute_command_safe("jstest /dev/input/js0")

        # Verify the command was wrapped
        args, kwargs = mock_ssh_client.exec_command.call_args
        command = args[0]
        assert command.startswith("timeout ")
        assert "jstest /dev/input/js0" in command

    def test_no_client_error(self) -> None:
        """Test that commands fail when not connected."""
        handler = SSHHandler("test-host", "test-user")
        # Don't set client (simulates not connected)

        with pytest.raises(RuntimeError, match="Not connected"):
            handler.execute_command("echo test")

    def test_different_command_types_get_different_timeouts(
        self, ssh_handler: SSHHandler, mock_ssh_client: Mock
    ) -> None:
        """Test that different command types get appropriately different timeouts."""
        test_cases = [
            ("echo test", 10),  # Quick command
            ("vcgencmd measure_temp", 30),  # System info
            ("sudo apt-get install vim", 300),  # Package operation
            ("apt update", 1800),  # System update (longer than regular package ops)
            ("/home/pi/RetroPie-Setup/retropie_setup.sh", 1800),  # RetroPie setup
            ("jstest /dev/input/js0", 15),  # Controller test
        ]

        for command, expected_timeout in test_cases:
            # Reset mock
            mock_ssh_client.reset_mock()

            # Execute command
            ssh_handler.execute_command(command)

            # Check timeout
            args, kwargs = mock_ssh_client.exec_command.call_args
            assert kwargs["timeout"] == expected_timeout, (
                f"Command '{command}' got wrong timeout"
            )

    def test_timeout_config_integration(self, ssh_handler: SSHHandler) -> None:
        """Test that SSH handler properly integrates with timeout config."""
        # Verify handler has access to timeout config
        assert ssh_handler.timeout_config is not None
        assert hasattr(ssh_handler.timeout_config, "get_timeout_for_command")

        # Test that config methods work
        timeout = ssh_handler.timeout_config.get_timeout_for_command("echo test")
        assert isinstance(timeout, int)
        assert timeout > 0
