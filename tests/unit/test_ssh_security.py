"""Unit tests for SSH security hardening."""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

import paramiko
import pytest

from retromcp.secure_ssh_handler import SecureSSHHandler as SSHHandler


class TestSSHSecurity:
    """Test SSH security features."""

    def test_ssh_handler_rejects_unknown_hosts_by_default(self) -> None:
        """Test that SSHHandler rejects unknown hosts by default."""
        # Create a temporary known_hosts file
        with tempfile.TemporaryDirectory() as temp_dir:
            known_hosts_path = Path(temp_dir) / "known_hosts"
            known_hosts_path.write_text("")  # Empty known_hosts

            handler = SSHHandler(
                host="example.com",
                username="pi",
                password="password",  # noqa: S106
                port=22,
                known_hosts_path=str(known_hosts_path),
            )

            mock_client = MagicMock(spec=paramiko.SSHClient)
            mock_client.connect.side_effect = paramiko.ssh_exception.SSHException(
                "Server 'example.com' not found in known_hosts"
            )

            with patch(
                "retromcp.secure_ssh_handler.paramiko.SSHClient",
                return_value=mock_client,
            ):
                result = handler.connect()

            assert result is False
            # Check that RejectPolicy was set
            mock_client.set_missing_host_key_policy.assert_called()
            call_args = mock_client.set_missing_host_key_policy.call_args[0][0]
            assert isinstance(call_args, paramiko.RejectPolicy)

    def test_ssh_handler_uses_known_hosts_file(self) -> None:
        """Test that SSHHandler uses known_hosts file for verification."""
        with tempfile.TemporaryDirectory() as temp_dir:
            known_hosts_path = Path(temp_dir) / "known_hosts"
            known_hosts_path.write_text("example.com ssh-rsa AAAAB3NzaC1yc2E...")

            handler = SSHHandler(
                host="example.com",
                username="pi",
                password="password",  # noqa: S106
                port=22,
                known_hosts_path=str(known_hosts_path),
            )

            mock_client = MagicMock(spec=paramiko.SSHClient)

            with patch(
                "retromcp.secure_ssh_handler.paramiko.SSHClient",
                return_value=mock_client,
            ):
                handler.connect()

            mock_client.load_host_keys.assert_called_once_with(str(known_hosts_path))
            # Should still set RejectPolicy even with known_hosts
            mock_client.set_missing_host_key_policy.assert_called()
            call_args = mock_client.set_missing_host_key_policy.call_args[0][0]
            assert isinstance(call_args, paramiko.RejectPolicy)

    def test_ssh_handler_adds_timeout_to_connections(self) -> None:
        """Test that SSH connections have proper timeouts."""
        handler = SSHHandler(
            host="example.com",
            username="pi",
            password="password",
            port=22,
            timeout=30,  # 30 second timeout
        )

        mock_client = MagicMock(spec=paramiko.SSHClient)

        with patch("paramiko.SSHClient", return_value=mock_client):
            handler.connect()

        mock_client.connect.assert_called_once()
        connect_call = mock_client.connect.call_args
        assert connect_call.kwargs["timeout"] == 30

    def test_ssh_handler_cleans_up_credentials_after_use(self) -> None:
        """Test that credentials are cleaned up after connection."""
        password = "secret_password"  # noqa: S105
        handler = SSHHandler(
            host="example.com", username="pi", password=password, port=22
        )

        mock_client = MagicMock(spec=paramiko.SSHClient)

        with patch("paramiko.SSHClient", return_value=mock_client):
            handler.connect()
            handler.disconnect()

        # Password should be cleared after disconnect
        assert handler.password is None
        assert password not in str(handler.__dict__)

    def test_ssh_handler_validates_host_format(self) -> None:
        """Test that SSH handler validates host format."""
        # Test invalid host formats
        invalid_hosts = [
            "",  # Empty host
            " ",  # Whitespace only
            "host with spaces",  # Spaces in hostname
            "host;rm -rf /",  # Command injection attempt
            "host$(whoami)",  # Command substitution
            "host`date`",  # Backtick command
            "host|ls",  # Pipe command
            "host&id",  # Background command
        ]

        for invalid_host in invalid_hosts:
            with pytest.raises(ValueError, match="Invalid host format"):
                SSHHandler(host=invalid_host, username="pi", password="password")

    def test_ssh_handler_validates_username_format(self) -> None:
        """Test that SSH handler validates username format."""
        # Test invalid username formats
        invalid_usernames = [
            "",  # Empty username
            " ",  # Whitespace only
            "user;ls",  # Command injection
            "user$(id)",  # Command substitution
            "user`whoami`",  # Backtick command
            "../user",  # Path traversal
            "user\x00name",  # Null byte
            "user\nname",  # Newline
        ]

        for invalid_username in invalid_usernames:
            with pytest.raises(ValueError, match="Invalid username format"):
                SSHHandler(
                    host="example.com", username=invalid_username, password="password"
                )

    def test_ssh_handler_validates_port_range(self) -> None:
        """Test that SSH handler validates port range."""
        # Test invalid port values
        invalid_ports = [-1, 0, 65536, 100000]

        for invalid_port in invalid_ports:
            with pytest.raises(ValueError, match="Invalid port"):
                SSHHandler(
                    host="example.com",
                    username="pi",
                    password="password",  # noqa: S106
                    port=invalid_port,
                )

    def test_ssh_handler_sanitizes_error_messages(self) -> None:
        """Test that error messages don't expose sensitive information."""
        handler = SSHHandler(
            host="example.com", username="pi", password="secret_password", port=22
        )

        mock_client = MagicMock(spec=paramiko.SSHClient)
        mock_client.connect.side_effect = paramiko.AuthenticationException(
            "Authentication failed for user pi with password secret_password"
        )

        with patch("paramiko.SSHClient", return_value=mock_client), patch(
            "logging.Logger.error"
        ) as mock_logger:
            result = handler.connect()

        assert result is False
        # Check that password is not in logged error message
        error_calls = mock_logger.call_args_list
        for call in error_calls:
            assert "secret_password" not in str(call)

    def test_ssh_handler_limits_connection_attempts(self) -> None:
        """Test that SSH handler limits connection retry attempts."""
        handler = SSHHandler(
            host="example.com",
            username="pi",
            password="password",
            port=22,
            max_retries=3,
        )

        mock_client = MagicMock(spec=paramiko.SSHClient)
        mock_client.connect.side_effect = (
            paramiko.ssh_exception.NoValidConnectionsError(
                {("example.com", 22): "Connection refused"}
            )
        )

        with patch("paramiko.SSHClient", return_value=mock_client):
            result = handler.connect()

        assert result is False
        # Should attempt exactly max_retries times
        assert mock_client.connect.call_count == 3

    def test_ssh_handler_uses_strict_host_key_checking(self) -> None:
        """Test that strict host key checking is enabled by default."""
        handler = SSHHandler(
            host="example.com",
            username="pi",
            password="password",  # noqa: S106, port=22
        )

        mock_client = MagicMock(spec=paramiko.SSHClient)

        with patch("paramiko.SSHClient", return_value=mock_client):
            # Should fail if host not in known_hosts
            handler.connect()

        # Should NOT set AutoAddPolicy
        for call in mock_client.set_missing_host_key_policy.call_args_list:
            assert not isinstance(call[0][0], paramiko.AutoAddPolicy)

    def test_execute_command_timeout(self) -> None:
        """Test that command execution has proper timeout."""
        handler = SSHHandler(
            host="example.com",
            username="pi",
            password="password",
            port=22,
            command_timeout=10,  # 10 second command timeout
        )

        mock_client = MagicMock(spec=paramiko.SSHClient)
        mock_channel = MagicMock()
        mock_channel.recv_exit_status.side_effect = paramiko.SSHException("Timeout")

        mock_stdout = MagicMock()
        mock_stdout.channel = mock_channel
        mock_stdout.read.return_value = b""

        mock_stderr = MagicMock()
        mock_stderr.read.return_value = b""

        mock_client.exec_command.return_value = (MagicMock(), mock_stdout, mock_stderr)
        handler.client = mock_client

        with pytest.raises(RuntimeError, match="Command execution timeout"):
            handler.execute_command("sleep 100")

    def test_ssh_key_permissions_validated(self) -> None:
        """Test that SSH key file permissions are validated."""
        with tempfile.TemporaryDirectory() as temp_dir:
            key_path = Path(temp_dir) / "id_rsa"
            key_path.write_text("FAKE_PRIVATE_KEY")

            # Set insecure permissions
            os.chmod(key_path, 0o644)

            with pytest.raises(ValueError, match="SSH key has insecure permissions"):
                SSHHandler(
                    host="example.com", username="pi", key_path=str(key_path), port=22
                )
