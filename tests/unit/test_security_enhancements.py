"""Unit tests for enhanced security features."""

import pytest
from unittest.mock import MagicMock, patch

from retromcp.secure_ssh_handler_v2 import SecureSSHHandlerV2


pytestmark = [pytest.mark.security, pytest.mark.unit]


class TestSecurityEnhancements:
    """Test enhanced security features in SSH handler."""

    def test_blocks_root_username(self) -> None:
        """Test that root username is blocked."""
        blocked_usernames = ["root", "admin", "administrator"]
        
        for username in blocked_usernames:
            with pytest.raises(ValueError, match="not allowed for security reasons"):
                SecureSSHHandlerV2(
                    host="example.com",
                    username=username,
                    password="password"
                )

    def test_blocks_dangerous_usernames_case_insensitive(self) -> None:
        """Test that dangerous usernames are blocked regardless of case."""
        dangerous_usernames = ["ROOT", "Root", "ADMIN", "Admin", "ADMINISTRATOR"]
        
        for username in dangerous_usernames:
            with pytest.raises(ValueError, match="not allowed for security reasons"):
                SecureSSHHandlerV2(
                    host="example.com",
                    username=username,
                    password="password"
                )

    def test_allows_safe_usernames(self) -> None:
        """Test that safe usernames are allowed."""
        safe_usernames = ["pi", "retro", "user", "gaming", "test-user", "user_123"]
        
        for username in safe_usernames:
            handler = SecureSSHHandlerV2(
                host="example.com",
                username=username,
                password="password"
            )
            assert handler.username == username

    def test_sudo_command_validation_allows_safe_commands(self) -> None:
        """Test that safe sudo commands are allowed."""
        handler = SecureSSHHandlerV2(
            host="example.com",
            username="pi",
            password="password"
        )
        
        safe_commands = [
            "apt-get update",
            "apt-get install vim",
            "systemctl start emulationstation",
            "systemctl stop bluetooth",
            "chmod 600 /home/pi/.retromcp/config.json",
            "vcgencmd measure_temp",
            "gpio mode 18 out",
        ]
        
        for command in safe_commands:
            # Should not raise an exception
            handler._validate_sudo_command(command)

    def test_sudo_command_validation_blocks_dangerous_commands(self) -> None:
        """Test that dangerous sudo commands are blocked."""
        handler = SecureSSHHandlerV2(
            host="example.com",
            username="pi",
            password="password"
        )
        
        dangerous_commands = [
            "rm -rf /",
            "dd if=/dev/zero of=/dev/sda",
            "mkfs.ext4 /dev/sda1",
            "passwd root",
            "sudo su",
            "chmod 777 /etc/passwd",
            "chown root /home/pi/.bashrc",
            "echo malicious > /etc/passwd",
            "apt-get install vim && rm -rf /",
            "systemctl start nginx; cat /etc/shadow",
        ]
        
        for command in dangerous_commands:
            with pytest.raises(ValueError, match="not allowed|dangerous pattern"):
                handler._validate_sudo_command(command)

    def test_sudo_command_preparation_with_password(self) -> None:
        """Test sudo command preparation with password."""
        handler = SecureSSHHandlerV2(
            host="example.com",
            username="pi",
            sudo_password="test_password"
        )
        
        result = handler._prepare_sudo_command("apt-get update")
        assert result == "sudo -S apt-get update"

    def test_sudo_command_preparation_without_password(self) -> None:
        """Test sudo command preparation without password."""
        handler = SecureSSHHandlerV2(
            host="example.com",
            username="pi"
        )
        
        result = handler._prepare_sudo_command("apt-get update")
        assert result == "sudo apt-get update"

    @patch('getpass.getpass')
    def test_sudo_password_prompt_success(self, mock_getpass) -> None:
        """Test successful sudo password prompt."""
        mock_getpass.return_value = "test_password"
        
        handler = SecureSSHHandlerV2(
            host="example.com",
            username="pi"
        )
        
        result = handler.prompt_sudo_password()
        assert result is True
        assert handler.sudo_password == "test_password"

    @patch('getpass.getpass')
    def test_sudo_password_prompt_cancelled(self, mock_getpass) -> None:
        """Test cancelled sudo password prompt."""
        mock_getpass.side_effect = KeyboardInterrupt()
        
        handler = SecureSSHHandlerV2(
            host="example.com",
            username="pi"
        )
        
        result = handler.prompt_sudo_password()
        assert result is False
        assert handler.sudo_password is None

    def test_credential_cleanup_on_disconnect(self) -> None:
        """Test that credentials are cleaned up on disconnect."""
        handler = SecureSSHHandlerV2(
            host="example.com",
            username="pi",
            password="ssh_password",
            sudo_password="sudo_password"
        )
        
        # Mock client
        handler.client = MagicMock()
        
        handler.disconnect()
        
        assert handler.password is None
        assert handler.sudo_password is None
        assert handler.client is None

    def test_error_message_sanitization(self) -> None:
        """Test that error messages are sanitized."""
        handler = SecureSSHHandlerV2(
            host="example.com",
            username="pi",
            password="secret_ssh_pass",
            sudo_password="secret_sudo_pass"
        )
        
        error_msg = "Authentication failed with password secret_ssh_pass and sudo secret_sudo_pass at /home/user/key from 192.168.1.100"
        
        sanitized = handler._sanitize_error(error_msg)
        
        assert "secret_ssh_pass" not in sanitized
        assert "secret_sudo_pass" not in sanitized
        assert "[REDACTED]" in sanitized
        assert "192.168.1.100" not in sanitized
        assert "[IP]" in sanitized
        assert "/home/user/key" not in sanitized
        assert "[PATH]" in sanitized

    @patch('retromcp.secure_ssh_handler_v2.paramiko.SSHClient')
    def test_execute_command_with_sudo_password(self, mock_ssh_client) -> None:
        """Test command execution with sudo password."""
        handler = SecureSSHHandlerV2(
            host="example.com",
            username="pi",
            sudo_password="test_password"
        )
        
        # Mock SSH components
        mock_client = MagicMock()
        mock_stdin = MagicMock()
        mock_stdout = MagicMock()
        mock_stderr = MagicMock()
        
        mock_stdout.channel.recv_exit_status.return_value = 0
        mock_stdout.read.return_value = b"Success"
        mock_stderr.read.return_value = b""
        
        mock_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)
        handler.client = mock_client
        
        exit_code, stdout, stderr = handler.execute_command("apt-get update", use_sudo=True)
        
        # Verify password was written to stdin
        mock_stdin.write.assert_called_with("test_password\n")
        mock_stdin.flush.assert_called_once()
        
        assert exit_code == 0
        assert stdout == "Success"

    def test_package_name_validation(self) -> None:
        """Test package name validation."""
        handler = SecureSSHHandlerV2(
            host="example.com",
            username="pi"
        )
        
        # Valid package names
        valid_packages = ["vim", "nano", "git", "python3-pip", "curl"]
        for package in valid_packages:
            handler.validate_package_name(package)  # Should not raise
        
        # Invalid package names
        invalid_packages = [
            "",  # Empty
            "package;rm -rf /",  # Command injection
            "package$(whoami)",  # Command substitution
            "package`date`",  # Backtick injection
            "package|ls",  # Pipe injection
            "package&id",  # Background command
            "package\x00name",  # Null byte
            "package..traversal",  # Path traversal
        ]
        
        for package in invalid_packages:
            with pytest.raises(ValueError, match="Invalid package name"):
                handler.validate_package_name(package)

    def test_install_packages_requires_sudo_password(self) -> None:
        """Test that package installation requires sudo password."""
        handler = SecureSSHHandlerV2(
            host="example.com",
            username="pi"
        )
        handler.client = MagicMock()
        
        with patch.object(handler, 'prompt_sudo_password', return_value=False):
            success, message = handler.install_packages_secure(["vim"])
            
            assert success is False
            assert "Sudo password required" in message
