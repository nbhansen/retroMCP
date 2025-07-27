"""Unit tests for SSH RetroPie client."""

import logging
from unittest.mock import Mock
from unittest.mock import patch

import pytest

from retromcp.domain.models import CommandResult
from retromcp.domain.models import ConnectionInfo
from retromcp.infrastructure.ssh_retropie_client import SSHRetroPieClient
from retromcp.ssh_handler import RetroPieSSH


class TestSSHRetroPieClient:
    """Test SSHRetroPieClient."""

    @pytest.fixture
    def mock_ssh_handler(self) -> Mock:
        """Provide mocked SSH handler."""
        mock = Mock(spec=RetroPieSSH)
        mock.host = "test-retropie.local"
        mock.port = 22
        mock.username = "retro"
        return mock

    @pytest.fixture
    def client(self, mock_ssh_handler: Mock) -> SSHRetroPieClient:
        """Provide SSH RetroPie client with mocked handler."""
        return SSHRetroPieClient(mock_ssh_handler)

    def test_init(self, mock_ssh_handler: Mock):
        """Test client initialization."""
        client = SSHRetroPieClient(mock_ssh_handler)

        assert client._ssh == mock_ssh_handler
        assert client._last_connected is None

    def test_connect_success(self, client: SSHRetroPieClient, mock_ssh_handler: Mock):
        """Test successful connection."""
        # Arrange
        mock_ssh_handler.connect.return_value = True

        # Act
        with patch("time.strftime", return_value="2024-01-01 12:00:00"):
            result = client.connect()

        # Assert
        assert result is True
        assert client._last_connected == "2024-01-01 12:00:00"
        mock_ssh_handler.connect.assert_called_once()

    def test_connect_failure(self, client: SSHRetroPieClient, mock_ssh_handler: Mock):
        """Test failed connection."""
        # Arrange
        mock_ssh_handler.connect.return_value = False

        # Act
        result = client.connect()

        # Assert
        assert result is False
        assert client._last_connected is None
        mock_ssh_handler.connect.assert_called_once()

    def test_disconnect(self, client: SSHRetroPieClient, mock_ssh_handler: Mock):
        """Test disconnection."""
        # Act
        client.disconnect()

        # Assert
        mock_ssh_handler.disconnect.assert_called_once()

    def test_test_connection(self, client: SSHRetroPieClient, mock_ssh_handler: Mock):
        """Test connection testing."""
        # Arrange
        mock_ssh_handler.test_connection.return_value = True

        # Act
        result = client.test_connection()

        # Assert
        assert result is True
        mock_ssh_handler.test_connection.assert_called_once()

    def test_get_connection_info(
        self, client: SSHRetroPieClient, mock_ssh_handler: Mock
    ):
        """Test getting connection info."""
        # Arrange
        client._last_connected = "2024-01-01 12:00:00"
        mock_ssh_handler.test_connection.return_value = True

        # Act
        result = client.get_connection_info()

        # Assert
        expected = ConnectionInfo(
            host="test-retropie.local",
            port=22,
            username="retro",
            connected=True,
            last_connected="2024-01-01 12:00:00",
            connection_method="ssh",
        )
        assert result == expected

    def test_get_connection_info_not_connected(
        self, client: SSHRetroPieClient, mock_ssh_handler: Mock
    ):
        """Test getting connection info when not connected."""
        # Arrange
        mock_ssh_handler.test_connection.return_value = False

        # Act
        result = client.get_connection_info()

        # Assert
        assert result.connected is False
        assert result.last_connected is None

    def test_execute_command_success(
        self, client: SSHRetroPieClient, mock_ssh_handler: Mock
    ):
        """Test successful command execution."""
        # Arrange
        mock_ssh_handler.execute_command.return_value = (0, "success output", "")

        # Act
        with patch("time.time", side_effect=[1000.0, 1000.1]):
            result = client.execute_command("echo test")

        # Assert
        assert result.command == "echo test"
        assert result.exit_code == 0
        assert result.stdout == "success output"
        assert result.stderr == ""
        assert result.success is True
        assert abs(result.execution_time - 0.1) < 0.001
        mock_ssh_handler.execute_command.assert_called_once_with("echo test")

    def test_execute_command_with_sudo(
        self, client: SSHRetroPieClient, mock_ssh_handler: Mock
    ):
        """Test command execution with sudo."""
        # Arrange
        mock_ssh_handler.execute_command.return_value = (0, "success output", "")

        # Act
        result = client.execute_command("apt update", use_sudo=True)

        # Assert
        assert result.success is True
        mock_ssh_handler.execute_command.assert_called_once_with("sudo apt update")

    def test_execute_command_failure(
        self, client: SSHRetroPieClient, mock_ssh_handler: Mock
    ):
        """Test failed command execution."""
        # Arrange
        mock_ssh_handler.execute_command.return_value = (1, "", "command not found")

        # Act
        with patch("time.time", side_effect=[1000.0, 1000.2]):
            result = client.execute_command("invalid_command")

        # Assert
        assert result.command == "invalid_command"
        assert result.exit_code == 1
        assert result.stdout == ""
        assert result.stderr == "command not found"
        assert result.success is False
        assert abs(result.execution_time - 0.2) < 0.001

    def test_execute_command_exception(
        self, client: SSHRetroPieClient, mock_ssh_handler: Mock
    ):
        """Test command execution with exception."""
        # Arrange
        mock_ssh_handler.execute_command.side_effect = Exception("SSH connection lost")

        # Act
        with patch("time.time", side_effect=[1000.0, 1000.3]):
            result = client.execute_command("echo test")

        # Assert
        assert result.command == "echo test"
        assert result.exit_code == 1
        assert result.stdout == ""
        assert result.stderr == "SSH connection lost"
        assert result.success is False
        assert (
            abs(result.execution_time - 0.3) < 0.001
        )  # Allow small floating point differences

    def test_execute_command_with_retry_success_on_second_attempt(
        self, client: SSHRetroPieClient, mock_ssh_handler: Mock
    ):
        """Test command execution with retry succeeding on second attempt."""
        # Arrange
        mock_ssh_handler.execute_command.side_effect = [
            Exception("Connection lost"),  # First attempt fails
            (0, "success output", ""),  # Second attempt succeeds
        ]

        # Act
        with patch("time.time", side_effect=[1000.0, 1000.1, 1000.2, 1000.3]):
            result = client.execute_command_with_retry("echo test", max_retries=2)

        # Assert
        assert result.command == "echo test"
        assert result.exit_code == 0
        assert result.stdout == "success output"
        assert result.success is True
        assert mock_ssh_handler.execute_command.call_count == 2

    def test_execute_command_with_retry_exhausts_retries(
        self, client: SSHRetroPieClient, mock_ssh_handler: Mock
    ):
        """Test command execution with retry exhausting all attempts."""
        # Arrange
        mock_ssh_handler.execute_command.side_effect = Exception(
            "Persistent connection error"
        )

        # Act
        with patch(
            "time.time", side_effect=[1000.0, 1000.1, 1000.2, 1000.3, 1000.4, 1000.5]
        ):
            result = client.execute_command_with_retry("echo test", max_retries=3)

        # Assert
        assert result.command == "echo test"
        assert result.exit_code == 1
        assert "Persistent connection error" in result.stderr
        assert result.success is False
        assert mock_ssh_handler.execute_command.call_count == 3

    def test_execute_command_with_timeout(
        self, client: SSHRetroPieClient, mock_ssh_handler: Mock
    ):
        """Test command execution with timeout handling."""
        # Arrange
        # Mock the execute_command to return a result that took 1.5 seconds
        mock_result = CommandResult(
            command="slow_command",
            exit_code=0,
            stdout="output",
            stderr="",
            success=True,
            execution_time=1.5,  # This simulates a command that took 1.5 seconds
        )

        # Mock execute_command to return our mock result
        with patch.object(client, "execute_command", return_value=mock_result):
            # Act
            result = client.execute_command_with_timeout("slow_command", timeout=1.0)

        # Assert
        assert result.command == "slow_command"
        assert result.exit_code == 124  # Standard timeout exit code
        assert "Command timed out" in result.stderr
        assert result.success is False

    def test_execute_command_logs_retry_attempts(
        self, client: SSHRetroPieClient, mock_ssh_handler: Mock, caplog
    ):
        """Test that retry attempts are properly logged."""
        # Arrange - Make first attempt fail, then have retry logic kick in
        mock_ssh_handler.execute_command.side_effect = [
            Exception("Transient error"),
            (0, "success", ""),
        ]

        # Act
        with patch("time.time", side_effect=[1000.0, 1000.1, 1000.2, 1000.3]), patch(
            "time.sleep"
        ):  # Mock sleep to speed up test
            with caplog.at_level(logging.INFO):  # Capture INFO level logs
                result = client.execute_command_with_retry(
                    "test_command", max_retries=3
                )

        # Assert
        assert result.success is True
        assert "Command execution failed (attempt 1/3)" in caplog.text
        # Since first attempt failed and second succeeded, expect retry message
        assert "Retrying command execution, attempt 2/3" in caplog.text

    def test_execute_command_categorizes_connection_errors(
        self, client: SSHRetroPieClient, mock_ssh_handler: Mock
    ):
        """Test that connection errors are properly categorized."""
        # Arrange
        mock_ssh_handler.execute_command.side_effect = Exception("Connection refused")

        # Act
        result = client.execute_command_with_enhanced_error_handling("echo test")

        # Assert
        assert result.command == "echo test"
        assert result.exit_code == 2  # Connection error code
        assert "Connection refused" in result.stderr
        assert result.success is False

    def test_execute_command_categorizes_authentication_errors(
        self, client: SSHRetroPieClient, mock_ssh_handler: Mock
    ):
        """Test that authentication errors are properly categorized."""
        # Arrange
        mock_ssh_handler.execute_command.side_effect = Exception(
            "Authentication failed"
        )

        # Act
        result = client.execute_command_with_enhanced_error_handling("echo test")

        # Assert
        assert result.command == "echo test"
        assert result.exit_code == 3  # Authentication error code
        assert "Authentication failed" in result.stderr
        assert result.success is False

    def test_execute_command_categorizes_permission_errors(
        self, client: SSHRetroPieClient, mock_ssh_handler: Mock
    ):
        """Test that permission errors are properly categorized."""
        # Arrange
        mock_ssh_handler.execute_command.side_effect = Exception("Permission denied")

        # Act
        result = client.execute_command_with_enhanced_error_handling(
            "sudo restricted_command"
        )

        # Assert
        assert result.command == "sudo restricted_command"
        assert result.exit_code == 126  # Permission denied exit code
        assert "Permission denied" in result.stderr
        assert result.success is False
