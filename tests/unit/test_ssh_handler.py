"""Unit tests for SSH handler."""

from unittest.mock import Mock
from unittest.mock import patch

import paramiko
import pytest

from retromcp.ssh_handler import RetroPieSSH
from retromcp.ssh_handler import SSHHandler


class TestSSHHandler:
    """Test cases for SSH handler."""

    @pytest.fixture
    def ssh_handler(self) -> SSHHandler:
        """Create SSH handler instance."""
        return SSHHandler(
            host="test-pi.local",
            username="retro",
            password="test_password",  # noqa: S106
            port=22,
        )

    @pytest.fixture
    def ssh_handler_with_key(self) -> SSHHandler:
        """Create SSH handler instance with key authentication."""
        return SSHHandler(
            host="test-pi.local",
            username="retro",
            key_path="/home/user/.ssh/id_rsa",
            port=22,
        )

    def test_initialization(self, ssh_handler: SSHHandler) -> None:
        """Test SSH handler initialization."""
        assert ssh_handler.host == "test-pi.local"
        assert ssh_handler.username == "retro"
        assert ssh_handler.password == "test_password"
        assert ssh_handler.key_path is None
        assert ssh_handler.port == 22
        assert ssh_handler.client is None

    def test_initialization_with_key(self, ssh_handler_with_key: SSHHandler) -> None:
        """Test SSH handler initialization with key."""
        assert ssh_handler_with_key.host == "test-pi.local"
        assert ssh_handler_with_key.username == "retro"
        assert ssh_handler_with_key.password is None
        assert ssh_handler_with_key.key_path == "/home/user/.ssh/id_rsa"
        assert ssh_handler_with_key.port == 22
        assert ssh_handler_with_key.client is None

    @patch("paramiko.SSHClient")
    def test_connect_success_with_password(
        self, mock_ssh_client_class: Mock, ssh_handler: SSHHandler
    ) -> None:
        """Test successful connection with password."""
        mock_client = Mock()
        mock_ssh_client_class.return_value = mock_client

        result = ssh_handler.connect()

        assert result is True
        assert ssh_handler.client == mock_client
        mock_client.set_missing_host_key_policy.assert_called_once()

        # Check the actual call to connect
        expected_args = {
            "hostname": "test-pi.local",
            "port": 22,
            "username": "retro",
            "timeout": 10,
            "password": "test_password",
        }
        mock_client.connect.assert_called_once_with(**expected_args)

    @patch("paramiko.SSHClient")
    def test_connect_success_with_key(
        self, mock_ssh_client_class: Mock, ssh_handler_with_key: SSHHandler
    ) -> None:
        """Test successful connection with key."""
        mock_client = Mock()
        mock_ssh_client_class.return_value = mock_client

        result = ssh_handler_with_key.connect()

        assert result is True
        assert ssh_handler_with_key.client == mock_client
        mock_client.set_missing_host_key_policy.assert_called_once()

        # Check the actual call to connect
        expected_args = {
            "hostname": "test-pi.local",
            "port": 22,
            "username": "retro",
            "timeout": 10,
            "key_filename": "/home/user/.ssh/id_rsa",
        }
        mock_client.connect.assert_called_once_with(**expected_args)

    @patch("paramiko.SSHClient")
    def test_connect_failure(
        self, mock_ssh_client_class: Mock, ssh_handler: SSHHandler
    ) -> None:
        """Test connection failure."""
        mock_client = Mock()
        mock_ssh_client_class.return_value = mock_client
        mock_client.connect.side_effect = paramiko.SSHException("Connection failed")

        result = ssh_handler.connect()

        assert result is False
        assert ssh_handler.client == mock_client

    def test_disconnect_with_active_connection(self, ssh_handler: SSHHandler) -> None:
        """Test disconnecting active connection."""
        mock_client = Mock()
        ssh_handler.client = mock_client

        ssh_handler.disconnect()

        mock_client.close.assert_called_once()
        assert ssh_handler.client is None

    def test_disconnect_without_connection(self, ssh_handler: SSHHandler) -> None:
        """Test disconnecting when not connected."""
        # Should not fail
        ssh_handler.disconnect()
        assert ssh_handler.client is None

    def test_execute_command_not_connected(self, ssh_handler: SSHHandler) -> None:
        """Test executing command when not connected."""
        with pytest.raises(RuntimeError, match="Not connected"):
            ssh_handler.execute_command("ls")

    def test_execute_command_success(self, ssh_handler: SSHHandler) -> None:
        """Test successful command execution."""
        # Set up mock client
        mock_client = Mock()
        mock_stdin = Mock()
        mock_stdout = Mock()
        mock_stderr = Mock()

        mock_stdout.read.return_value = b"file1.txt\nfile2.txt\n"
        mock_stderr.read.return_value = b""
        mock_stdout.channel.recv_exit_status.return_value = 0

        mock_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)
        ssh_handler.client = mock_client

        exit_code, stdout, stderr = ssh_handler.execute_command("ls")

        assert exit_code == 0
        assert stdout == "file1.txt\nfile2.txt"
        assert stderr == ""
        mock_client.exec_command.assert_called_once_with("ls")

    def test_execute_command_with_error(self, ssh_handler: SSHHandler) -> None:
        """Test command execution with error output."""
        # Set up mock client
        mock_client = Mock()
        mock_stdin = Mock()
        mock_stdout = Mock()
        mock_stderr = Mock()

        mock_stdout.read.return_value = b""
        mock_stderr.read.return_value = b"Command not found"
        mock_stdout.channel.recv_exit_status.return_value = 127

        mock_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)
        ssh_handler.client = mock_client

        exit_code, stdout, stderr = ssh_handler.execute_command("invalid_command")

        assert exit_code == 127
        assert stdout == ""
        assert stderr == "Command not found"

    def test_execute_command_exception(self, ssh_handler: SSHHandler) -> None:
        """Test command execution with SSH exception."""
        # Set up mock client
        mock_client = Mock()
        mock_client.exec_command.side_effect = paramiko.SSHException("SSH error")
        ssh_handler.client = mock_client

        with pytest.raises(paramiko.SSHException, match="SSH error"):
            ssh_handler.execute_command("ls")

    def test_test_connection_success(self, ssh_handler: SSHHandler) -> None:
        """Test connection test success."""
        # Set up mock client
        mock_client = Mock()
        mock_stdin = Mock()
        mock_stdout = Mock()
        mock_stderr = Mock()

        mock_stdout.read.return_value = b"test"
        mock_stderr.read.return_value = b""
        mock_stdout.channel.recv_exit_status.return_value = 0

        mock_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)
        ssh_handler.client = mock_client

        result = ssh_handler.test_connection()

        assert result is True

    def test_test_connection_failure(self, ssh_handler: SSHHandler) -> None:
        """Test connection test failure."""
        # Set up mock client that raises exception
        mock_client = Mock()
        mock_client.exec_command.side_effect = Exception("Connection lost")
        ssh_handler.client = mock_client

        result = ssh_handler.test_connection()

        assert result is False

    def test_test_connection_wrong_output(self, ssh_handler: SSHHandler) -> None:
        """Test connection test with wrong output."""
        # Set up mock client
        mock_client = Mock()
        mock_stdin = Mock()
        mock_stdout = Mock()
        mock_stderr = Mock()

        mock_stdout.read.return_value = b"wrong"
        mock_stderr.read.return_value = b""
        mock_stdout.channel.recv_exit_status.return_value = 0

        mock_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)
        ssh_handler.client = mock_client

        result = ssh_handler.test_connection()

        assert result is False

    @patch.object(SSHHandler, "connect")
    @patch.object(SSHHandler, "disconnect")
    def test_context_manager_success(
        self, mock_disconnect: Mock, mock_connect: Mock, ssh_handler: SSHHandler
    ) -> None:
        """Test using SSH handler as context manager."""
        with ssh_handler as handler:
            assert handler == ssh_handler
            mock_connect.assert_called_once()

        mock_disconnect.assert_called_once()

    @patch.object(SSHHandler, "connect")
    @patch.object(SSHHandler, "disconnect")
    def test_context_manager_with_exception(
        self, mock_disconnect: Mock, mock_connect: Mock, ssh_handler: SSHHandler
    ) -> None:
        """Test context manager when exception occurs."""
        with pytest.raises(ValueError), ssh_handler:
            raise ValueError("Test error")

        mock_connect.assert_called_once()
        mock_disconnect.assert_called_once()


class TestRetroPieSSH:
    """Test cases for RetroPie-specific SSH operations."""

    @pytest.fixture
    def retropie_ssh(self) -> RetroPieSSH:
        """Create RetroPieSSH instance."""
        return RetroPieSSH(
            host="test-pi.local",
            username="retro",
            password="test_password",  # noqa: S106
            port=22,
        )

    def test_retropie_ssh_inheritance(self, retropie_ssh: RetroPieSSH) -> None:
        """Test that RetroPieSSH inherits from SSHHandler."""
        assert isinstance(retropie_ssh, SSHHandler)
        assert retropie_ssh.host == "test-pi.local"
        assert retropie_ssh.username == "retro"

    def test_get_system_info_not_connected(self, retropie_ssh: RetroPieSSH) -> None:
        """Test getting system info when not connected."""
        with pytest.raises(RuntimeError, match="Not connected"):
            retropie_ssh.get_system_info()

    def test_get_system_info_success(self, retropie_ssh: RetroPieSSH) -> None:
        """Test successful system info retrieval."""
        # Set up mock client with system info commands
        mock_client = Mock()

        # Mock responses for different commands
        def mock_exec_command(command: str):
            mock_stdin = Mock()
            mock_stdout = Mock()
            mock_stderr = Mock()

            if "measure_temp" in command:
                mock_stdout.read.return_value = b"temp=55.4'C"
                mock_stdout.channel.recv_exit_status.return_value = 0
            elif "free -m" in command:
                mock_stdout.read.return_value = b"Mem: 1024 512 512"
                mock_stdout.channel.recv_exit_status.return_value = 0
            elif "hostname" in command:
                mock_stdout.read.return_value = b"retropie"
                mock_stdout.channel.recv_exit_status.return_value = 0
            else:
                mock_stdout.read.return_value = b""
                mock_stdout.channel.recv_exit_status.return_value = 0

            mock_stderr.read.return_value = b""
            return (mock_stdin, mock_stdout, mock_stderr)

        mock_client.exec_command = Mock(side_effect=mock_exec_command)
        retropie_ssh.client = mock_client

        info = retropie_ssh.get_system_info()

        assert "temperature" in info
        # Temperature is parsed as float in the implementation
        assert info["temperature"] == 55.4

    def test_detect_controllers_success(self, retropie_ssh: RetroPieSSH) -> None:
        """Test successful controller detection."""
        # Set up mock client
        mock_client = Mock()
        mock_stdin = Mock()
        mock_stdout = Mock()
        mock_stderr = Mock()

        mock_stdout.read.return_value = b"Bus 001 Device 002: ID 045e:02ea Microsoft Xbox Wireless Controller\nBus 001 Device 003: ID 054c:0ce6 Sony DualShock 4"
        mock_stderr.read.return_value = b""
        mock_stdout.channel.recv_exit_status.return_value = 0

        mock_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)
        retropie_ssh.client = mock_client

        result = retropie_ssh.detect_controllers()

        # The implementation returns different structure
        assert isinstance(result, dict)
        # Should have detected some USB devices or controller info
        assert len(result) > 0

    def test_install_packages_success(self, retropie_ssh: RetroPieSSH) -> None:
        """Test successful package installation."""
        # Set up mock client
        mock_client = Mock()
        mock_stdin = Mock()
        mock_stdout = Mock()
        mock_stderr = Mock()

        mock_stdout.read.return_value = b"Package installed successfully"
        mock_stderr.read.return_value = b""
        mock_stdout.channel.recv_exit_status.return_value = 0

        mock_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)
        retropie_ssh.client = mock_client

        success, message = retropie_ssh.install_packages(["jstest-gtk"])

        assert success is True
        assert "installed" in message.lower() or "success" in message.lower()

    def test_install_packages_failure(self, retropie_ssh: RetroPieSSH) -> None:
        """Test package installation failure."""
        # Set up mock client
        mock_client = Mock()
        mock_stdin = Mock()
        mock_stdout = Mock()
        mock_stderr = Mock()

        mock_stdout.read.return_value = b""
        mock_stderr.read.return_value = b"Package not found"
        mock_stdout.channel.recv_exit_status.return_value = 1

        mock_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)
        retropie_ssh.client = mock_client

        success, message = retropie_ssh.install_packages(["nonexistent-package"])

        assert success is False
        assert "Package not found" in message

    def test_configure_controller_success(self, retropie_ssh: RetroPieSSH) -> None:
        """Test successful controller configuration."""
        # Set up mock client
        mock_client = Mock()
        mock_stdin = Mock()
        mock_stdout = Mock()
        mock_stderr = Mock()

        mock_stdout.read.return_value = b"Controller configured successfully"
        mock_stderr.read.return_value = b""
        mock_stdout.channel.recv_exit_status.return_value = 0

        mock_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)
        retropie_ssh.client = mock_client

        success, message = retropie_ssh.configure_controller("xbox")

        assert success is True
        assert "configured" in message.lower() or "success" in message.lower()

    def test_setup_emulator_success(self, retropie_ssh: RetroPieSSH) -> None:
        """Test successful emulator setup."""
        # Set up mock client
        mock_client = Mock()
        mock_stdin = Mock()
        mock_stdout = Mock()
        mock_stderr = Mock()

        mock_stdout.read.return_value = b"Emulator setup completed"
        mock_stderr.read.return_value = b""
        mock_stdout.channel.recv_exit_status.return_value = 0

        mock_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)
        retropie_ssh.client = mock_client

        success, message = retropie_ssh.setup_emulator("nes", "lr-fceumm")

        assert success is True
        assert "setup" in message.lower() or "completed" in message.lower()

    def test_check_bios_files_success(self, retropie_ssh: RetroPieSSH) -> None:
        """Test successful BIOS file checking."""
        # Set up mock client
        mock_client = Mock()
        mock_stdin = Mock()
        mock_stdout = Mock()
        mock_stderr = Mock()

        mock_stdout.read.return_value = b"bios.bin found"
        mock_stderr.read.return_value = b""
        mock_stdout.channel.recv_exit_status.return_value = 0

        mock_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)
        retropie_ssh.client = mock_client

        result = retropie_ssh.check_bios_files("psx")

        assert "system" in result
        assert result["system"] == "psx"

    def test_run_retropie_setup_update(self, retropie_ssh: RetroPieSSH) -> None:
        """Test RetroPie setup update."""
        # Set up mock client
        mock_client = Mock()
        mock_stdin = Mock()
        mock_stdout = Mock()
        mock_stderr = Mock()

        mock_stdout.read.return_value = b"RetroPie-Setup updated"
        mock_stderr.read.return_value = b""
        mock_stdout.channel.recv_exit_status.return_value = 0

        mock_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)
        retropie_ssh.client = mock_client

        success, message = retropie_ssh.run_retropie_setup()

        assert success is True
        assert "updated" in message.lower() or "success" in message.lower()

    def test_run_retropie_setup_with_module(self, retropie_ssh: RetroPieSSH) -> None:
        """Test RetroPie setup with specific module."""
        # Set up mock client
        mock_client = Mock()
        mock_stdin = Mock()
        mock_stdout = Mock()
        mock_stderr = Mock()

        mock_stdout.read.return_value = b"Module configured"
        mock_stderr.read.return_value = b""
        mock_stdout.channel.recv_exit_status.return_value = 0

        mock_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)
        retropie_ssh.client = mock_client

        success, message = retropie_ssh.run_retropie_setup("lr-mame")

        assert success is True
        assert "configured" in message.lower() or message != ""
