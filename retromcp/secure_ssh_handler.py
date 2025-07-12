"""Secure SSH connection handler for RetroPie communication."""

import logging
import os
import re
import shlex
import stat
from pathlib import Path
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union

import paramiko

logger = logging.getLogger(__name__)


class SecureSSHHandler:
    """Secure SSH connection handler with security hardening."""

    # Valid hostname pattern: alphanumeric, dots, hyphens, colons (for IPv6)
    VALID_HOST_PATTERN = re.compile(r'^[a-zA-Z0-9.-]+$')

    # Valid username pattern: alphanumeric, underscore, hyphen
    VALID_USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_-]+$')

    def __init__(
        self,
        host: str,
        username: str,
        password: Optional[str] = None,
        key_path: Optional[str] = None,
        port: int = 22,
        known_hosts_path: Optional[str] = None,
        timeout: int = 30,
        command_timeout: int = 60,
        max_retries: int = 3
    ) -> None:
        """Initialize secure SSH handler.

        Args:
            host: Hostname or IP of the Raspberry Pi
            username: SSH username
            password: SSH password (if using password auth)
            key_path: Path to SSH private key (if using key auth)
            port: SSH port (default 22)
            known_hosts_path: Path to known_hosts file
            timeout: Connection timeout in seconds
            command_timeout: Command execution timeout in seconds
            max_retries: Maximum connection retry attempts

        Raises:
            ValueError: If parameters are invalid
        """
        # Validate inputs
        self._validate_host(host)
        self._validate_username(username)
        self._validate_port(port)

        if key_path:
            self._validate_key_permissions(key_path)

        self.host = host
        self.username = username
        self.password = password
        self.key_path = key_path
        self.port = port
        self.known_hosts_path = known_hosts_path or os.path.expanduser("~/.ssh/known_hosts")
        self.timeout = timeout
        self.command_timeout = command_timeout
        self.max_retries = max_retries
        self.client: Optional[paramiko.SSHClient] = None
        self._retry_count = 0

    def _validate_host(self, host: str) -> None:
        """Validate host format to prevent injection."""
        if not host or not host.strip():
            raise ValueError("Invalid host format: host cannot be empty")

        if not self.VALID_HOST_PATTERN.match(host):
            raise ValueError("Invalid host format: contains invalid characters")

        # Check for obvious injection attempts
        dangerous_patterns = [';', '$', '`', '|', '&', ' ', '\n', '\r', '\t']
        for pattern in dangerous_patterns:
            if pattern in host:
                raise ValueError("Invalid host format: contains dangerous characters")

    def _validate_username(self, username: str) -> None:
        """Validate username format to prevent injection."""
        if not username or not username.strip():
            raise ValueError("Invalid username format: username cannot be empty")

        if not self.VALID_USERNAME_PATTERN.match(username):
            raise ValueError("Invalid username format: contains invalid characters")

        # Check for obvious injection attempts
        dangerous_patterns = [';', '$', '`', '|', '&', '/', '\\', '\x00', '\n', '\r', ' ']
        for pattern in dangerous_patterns:
            if pattern in username:
                raise ValueError("Invalid username format: contains dangerous characters")

    def _validate_port(self, port: int) -> None:
        """Validate port is in valid range."""
        if not isinstance(port, int) or port < 1 or port > 65535:
            raise ValueError(f"Invalid port: {port} (must be 1-65535)")

    def _validate_key_permissions(self, key_path: str) -> None:
        """Validate SSH key file has secure permissions."""
        path = Path(key_path)
        if path.exists():
            mode = path.stat().st_mode
            # Check if group or others have any permissions
            if mode & (stat.S_IRWXG | stat.S_IRWXO):
                raise ValueError(
                    f"SSH key has insecure permissions: {oct(stat.S_IMODE(mode))}. "
                    "Must be readable only by owner (600 or 400)."
                )

    def connect(self) -> bool:
        """Establish SSH connection with security hardening.

        Returns:
            True if connection successful, False otherwise
        """
        for attempt in range(self.max_retries):
            try:
                self.client = paramiko.SSHClient()

                # Load known hosts for verification
                if os.path.exists(self.known_hosts_path):
                    self.client.load_host_keys(self.known_hosts_path)
                    # Use RejectPolicy - reject connection if host not in known_hosts
                    self.client.set_missing_host_key_policy(paramiko.RejectPolicy())
                else:
                    # If no known_hosts file exists, fail secure
                    logger.error(f"Known hosts file not found: {self.known_hosts_path}")
                    return False

                connect_args = {
                    "hostname": self.host,
                    "port": self.port,
                    "username": self.username,
                    "timeout": self.timeout,
                    "allow_agent": False,  # Disable agent for security
                    "look_for_keys": False,  # Explicit auth only
                }

                if self.key_path:
                    connect_args["key_filename"] = self.key_path
                elif self.password:
                    connect_args["password"] = self.password
                else:
                    logger.error("No authentication method provided")
                    return False

                self.client.connect(**connect_args)
                logger.info(f"Connected to {self.host}")
                return True

            except (paramiko.ssh_exception.SSHException, paramiko.ssh_exception.NoValidConnectionsError) as e:
                # Sanitize error message to avoid exposing sensitive info
                safe_error = self._sanitize_error(str(e))
                logger.error(f"Failed to connect to {self.host}: {safe_error}")
                self._retry_count = attempt + 1

                if attempt >= self.max_retries - 1:
                    return False

            except Exception as e:
                # Sanitize any error message
                safe_error = self._sanitize_error(str(e))
                logger.error(f"Failed to connect to {self.host}: {safe_error}")
                self._retry_count = attempt + 1

                if attempt >= self.max_retries - 1:
                    return False

        return False

    def _sanitize_error(self, error_msg: str) -> str:
        """Remove sensitive information from error messages."""
        # Remove password if present
        if self.password:
            error_msg = error_msg.replace(self.password, "[REDACTED]")

        # Remove full paths
        error_msg = re.sub(r'/[/\w\-\.]+', '[PATH]', error_msg)

        # Remove IP addresses
        error_msg = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '[IP]', error_msg)

        return error_msg

    def disconnect(self) -> None:
        """Close SSH connection and clean up credentials."""
        if self.client:
            self.client.close()
            self.client = None
            logger.info(f"Disconnected from {self.host}")

        # Clear credentials from memory
        self.password = None

    def execute_command(self, command: str) -> Tuple[int, str, str]:
        """Execute command with timeout protection.

        Args:
            command: Command to execute

        Returns:
            Tuple of (exit_code, stdout, stderr)

        Raises:
            RuntimeError: If not connected or command times out
        """
        if not self.client:
            raise RuntimeError("Not connected to SSH server")

        try:
            # Set timeout for command execution
            stdin, stdout, stderr = self.client.exec_command(
                command,
                timeout=self.command_timeout
            )

            # Get exit status with timeout
            exit_code = stdout.channel.recv_exit_status()

            stdout_text = stdout.read().decode("utf-8").strip()
            stderr_text = stderr.read().decode("utf-8").strip()

            return exit_code, stdout_text, stderr_text

        except paramiko.SSHException as e:
            if "Timeout" in str(e):
                raise RuntimeError(f"Command execution timeout after {self.command_timeout}s") from e
            raise

        except Exception as e:
            logger.error(f"Failed to execute command: {self._sanitize_error(str(e))}")
            raise

    def __enter__(self) -> "SecureSSHHandler":
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        """Context manager exit - ensure cleanup."""
        self.disconnect()

    # Secure command execution methods

    def install_packages_secure(self, packages: List[str]) -> Tuple[bool, str]:
        """Install packages with proper escaping.

        Args:
            packages: List of package names to install

        Returns:
            Tuple of (success, message)
        """
        if not self.client:
            raise RuntimeError("Not connected to SSH server")

        # Validate and escape each package name
        safe_packages = []
        for package in packages:
            self.validate_package_name(package)
            safe_packages.append(shlex.quote(package))

        # Build safe command
        package_str = " ".join(safe_packages)

        # Update package list
        update_cmd = "sudo apt-get update"
        exit_code, _, stderr = self.execute_command(update_cmd)
        if exit_code != 0:
            return False, f"Failed to update package list: {self._sanitize_error(stderr)}"

        # Install packages with escaped names
        install_cmd = f"sudo apt-get install -y {package_str}"
        exit_code, stdout, stderr = self.execute_command(install_cmd)

        if exit_code == 0:
            return True, "Successfully installed packages"
        else:
            return False, f"Failed to install packages: {self._sanitize_error(stderr)}"

    def set_gpio_mode_secure(self, pin: int, mode: str) -> Tuple[bool, str]:
        """Set GPIO pin mode with validation.

        Args:
            pin: GPIO pin number
            mode: Pin mode (in, out, pwm, clock, up, down, tri)

        Returns:
            Tuple of (success, message)
        """
        if not self.client:
            raise RuntimeError("Not connected to SSH server")

        # Validate inputs
        self.validate_gpio_pin(pin)
        self.validate_gpio_mode(mode)

        # Build safe command - pin and mode are validated, no need to quote
        cmd = f"gpio -g mode {pin} {mode}"
        exit_code, stdout, stderr = self.execute_command(cmd)

        if exit_code == 0:
            return True, f"Set GPIO pin {pin} to mode {mode}"
        else:
            return False, f"Failed to set GPIO mode: {self._sanitize_error(stderr)}"

    def test_controller_secure(self, device: str) -> Tuple[bool, str]:
        """Test controller with proper escaping.

        Args:
            device: Device path

        Returns:
            Tuple of (success, message)
        """
        if not self.client:
            raise RuntimeError("Not connected to SSH server")

        # Validate and escape device path
        self.validate_device_path(device)
        safe_device = shlex.quote(device)

        # Build safe command
        cmd = f"timeout 2 jstest --normal {safe_device}"
        exit_code, stdout, stderr = self.execute_command(cmd)

        if exit_code == 0:
            return True, stdout
        else:
            return False, f"Failed to test controller: {self._sanitize_error(stderr)}"

    def set_theme_secure(self, theme: str) -> Tuple[bool, str]:
        """Set EmulationStation theme with validation.

        Args:
            theme: Theme name

        Returns:
            Tuple of (success, message)
        """
        if not self.client:
            raise RuntimeError("Not connected to SSH server")

        # Validate theme name
        self.validate_theme_name(theme)
        safe_theme = shlex.quote(theme)

        # Build safe command to update config
        config_path = "/opt/retropie/configs/all/emulationstation/es_settings.xml"
        cmd = f"xmlstarlet ed -u '//string[@name=\"ThemeSet\"]' -v {safe_theme} {config_path}"

        exit_code, stdout, stderr = self.execute_command(cmd)

        if exit_code == 0:
            return True, f"Set theme to {theme}"
        else:
            return False, f"Failed to set theme: {self._sanitize_error(stderr)}"

    # Validation methods

    def validate_gpio_pin(self, pin: Union[int, str]) -> None:
        """Validate GPIO pin number."""
        if not isinstance(pin, int) or pin < 0 or pin > 40:
            logger.warning(f"Security: Rejected invalid GPIO pin: {pin}")
            raise ValueError(f"Invalid GPIO pin: {pin} (must be 0-40)")

    def validate_gpio_mode(self, mode: str) -> None:
        """Validate GPIO mode."""
        valid_modes = ["in", "out", "pwm", "clock", "up", "down", "tri"]
        if mode not in valid_modes:
            raise ValueError(f"Invalid GPIO mode: {mode} (must be one of {valid_modes})")

    def validate_package_name(self, package: str) -> None:
        """Validate package name format."""
        if not package or not package.strip():
            logger.warning("Security: Rejected empty package name")
            raise ValueError("Invalid package name: cannot be empty")

        # Check for obvious dangerous characters
        dangerous_chars = [';', '$', '`', '|', '&', '\x00', '\n', '\r', '..']
        for char in dangerous_chars:
            if char in package:
                logger.warning(f"Security: Rejected package name with dangerous character: {package!r}")
                raise ValueError(f"Invalid package name: contains dangerous character '{char}'")

    def validate_theme_name(self, theme: str) -> None:
        """Validate theme name."""
        if not theme or not theme.strip():
            logger.warning("Security: Rejected empty theme name")
            raise ValueError("Invalid theme name: cannot be empty")

        # Check for path traversal and command injection
        if '..' in theme or '/' in theme:
            logger.warning(f"Security: Rejected theme name with path traversal: {theme!r}")
            raise ValueError("Invalid theme name: contains path characters")

        dangerous_chars = [';', '$', '`', '|', '&', '\x00', '\n', '\r']
        for char in dangerous_chars:
            if char in theme:
                logger.warning(f"Security: Rejected theme name with dangerous character: {theme!r}")
                raise ValueError("Invalid theme name: contains dangerous character")

    def validate_device_path(self, device: str) -> None:
        """Validate device path."""
        if not device.startswith('/dev/'):
            logger.warning(f"Security: Rejected invalid device path: {device!r}")
            raise ValueError("Invalid device path: must start with /dev/")

        # Check for command injection
        dangerous_chars = [';', '$', '`', '|', '&', '\x00', '\n', '\r']
        for char in dangerous_chars:
            if char in device:
                logger.warning(f"Security: Rejected device path with dangerous character: {device!r}")
                raise ValueError("Invalid device path: contains dangerous character")

    def validate_safe_path(self, path: str) -> None:
        """Validate path doesn't contain traversal attempts."""
        if '..' in path:
            logger.warning(f"Security: Path traversal attempt detected: {path!r}")
            raise ValueError("Path traversal attempt detected")

        # Additional checks for Windows-style paths
        if '\\' in path and '..' in path.replace('\\', '/'):
            raise ValueError("Path traversal attempt detected")
