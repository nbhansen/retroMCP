"""Enhanced secure SSH handler with sudo password prompts."""

import getpass
import logging
import os
import re
import shlex
import stat
from pathlib import Path
from typing import List, Optional, Tuple, Union

import paramiko

logger = logging.getLogger(__name__)


class SecureSSHHandlerV2:
    """Enhanced secure SSH connection handler with sudo password management."""

    # Valid hostname pattern: alphanumeric, dots, hyphens, colons (for IPv6)
    VALID_HOST_PATTERN = re.compile(r"^[a-zA-Z0-9.-]+$")

    # Valid username pattern: alphanumeric, underscore, hyphen (NO ROOT)
    VALID_USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")

    # Blocked usernames for security
    BLOCKED_USERNAMES = {"root", "admin", "administrator"}

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
        max_retries: int = 3,
        sudo_password: Optional[str] = None,
    ) -> None:
        """Initialize enhanced secure SSH handler.

        Args:
            host: Hostname or IP of the Raspberry Pi
            username: SSH username (NOT root)
            password: SSH password (if using password auth)
            key_path: Path to SSH private key (if using key auth)
            port: SSH port (default 22)
            known_hosts_path: Path to known_hosts file
            timeout: Connection timeout in seconds
            command_timeout: Command execution timeout in seconds
            max_retries: Maximum connection retry attempts
            sudo_password: Password for sudo operations

        Raises:
            ValueError: If parameters are invalid
        """
        # Validate inputs
        self._validate_host(host)
        self._validate_username(username)
        self._validate_port(port)

        # Block root user explicitly
        if username.lower() in self.BLOCKED_USERNAMES:
            raise ValueError(f"Username '{username}' is not allowed for security reasons")

        if key_path:
            self._validate_key_permissions(key_path)

        self.host = host
        self.username = username
        self.password = password
        self.key_path = key_path
        self.port = port
        self.known_hosts_path = known_hosts_path or os.path.expanduser(
            "~/.ssh/known_hosts"
        )
        self.timeout = timeout
        self.command_timeout = command_timeout
        self.max_retries = max_retries
        self.sudo_password = sudo_password
        self.client: Optional[paramiko.SSHClient] = None
        self._retry_count = 0
        
        # Set user home path based on username for flexible path validation
        self.user_home = f"/home/{self.username}"

    def _validate_host(self, host: str) -> None:
        """Validate host format to prevent injection."""
        if not host or not host.strip():
            raise ValueError("Invalid host format: host cannot be empty")

        if not self.VALID_HOST_PATTERN.match(host):
            raise ValueError("Invalid host format: contains invalid characters")

        # Check for obvious injection attempts
        dangerous_patterns = [";", "$", "`", "|", "&", " ", "\n", "\r", "\t"]
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
        dangerous_patterns = [
            ";",
            "$",
            "`",
            "|",
            "&",
            "/",
            "\\",
            "\x00",
            "\n",
            "\r",
            " ",
        ]
        for pattern in dangerous_patterns:
            if pattern in username:
                raise ValueError(
                    "Invalid username format: contains dangerous characters"
                )

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

            except (
                paramiko.ssh_exception.SSHException,
                paramiko.ssh_exception.NoValidConnectionsError,
            ) as e:
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
        if self.sudo_password:
            error_msg = error_msg.replace(self.sudo_password, "[REDACTED]")

        # Remove full paths
        error_msg = re.sub(r"/[/\w\-\.]+", "[PATH]", error_msg)

        # Remove IP addresses
        error_msg = re.sub(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "[IP]", error_msg)

        return error_msg

    def disconnect(self) -> None:
        """Close SSH connection and clean up credentials."""
        if self.client:
            self.client.close()
            self.client = None
            logger.info(f"Disconnected from {self.host}")

        # Clear credentials from memory
        self.password = None
        self.sudo_password = None

    def test_connection(self) -> bool:
        """Test if connection is active.

        Returns:
            True if connection is active, False otherwise
        """
        try:
            exit_code, stdout, _ = self.execute_command("echo 'test'")
            return exit_code == 0 and stdout.strip() == "test"
        except Exception:
            return False

    def execute_command(self, command: str, use_sudo: bool = False) -> Tuple[int, str, str]:
        """Execute command with optional sudo and timeout protection.

        Args:
            command: Command to execute
            use_sudo: Whether to execute with sudo

        Returns:
            Tuple of (exit_code, stdout, stderr)

        Raises:
            RuntimeError: If not connected or command times out
        """
        if not self.client:
            raise RuntimeError("Not connected to SSH server")

        # If sudo is requested, validate and prepend
        if use_sudo:
            command = self._prepare_sudo_command(command)

        try:
            # Set timeout for command execution
            stdin, stdout, stderr = self.client.exec_command(
                command, timeout=self.command_timeout
            )

            # If using sudo and password is set, provide password
            if use_sudo and self.sudo_password:
                stdin.write(f"{self.sudo_password}\n")
                stdin.flush()

            # Get exit status with timeout
            exit_code = stdout.channel.recv_exit_status()

            stdout_text = stdout.read().decode("utf-8").strip()
            stderr_text = stderr.read().decode("utf-8").strip()

            return exit_code, stdout_text, stderr_text

        except paramiko.SSHException as e:
            if "Timeout" in str(e):
                raise RuntimeError(
                    f"Command execution timeout after {self.command_timeout}s"
                ) from e
            raise

        except Exception as e:
            logger.error(f"Failed to execute command: {self._sanitize_error(str(e))}")
            raise

    def _prepare_sudo_command(self, command: str) -> str:
        """Prepare command for sudo execution with validation.

        Args:
            command: Base command to execute

        Returns:
            Command prepared for sudo execution

        Raises:
            ValueError: If command is not allowed
        """
        # Validate command is allowed
        self._validate_sudo_command(command)

        # If sudo password is available, use -S for stdin password
        if self.sudo_password:
            return f"sudo -S {command}"
        else:
            return f"sudo {command}"

    def _validate_sudo_command(self, command: str) -> None:
        """Validate that command is allowed for sudo execution.

        Args:
            command: Command to validate

        Raises:
            ValueError: If command is not allowed
        """
        # List of allowed command patterns for sudo
        allowed_patterns = [
            # Package management - exact commands with safe arguments
            r"^apt-get update$",
            r"^apt-get install [a-zA-Z0-9\-\.\_\+]+( [a-zA-Z0-9\-\.\_\+]+)*$",
            r"^apt-get remove [a-zA-Z0-9\-\.\_\+]+( [a-zA-Z0-9\-\.\_\+]+)*$",
            r"^apt-get purge [a-zA-Z0-9\-\.\_\+]+( [a-zA-Z0-9\-\.\_\+]+)*$",
            r"^apt-get autoremove$",
            r"^apt-get autoclean$",
            r"^apt update$",
            r"^apt upgrade [a-zA-Z0-9\-\.\_\+]+( [a-zA-Z0-9\-\.\_\+]+)*$",
            r"^apt autoremove [a-zA-Z0-9\-\.\_\+]*$",
            r"^apt list [a-zA-Z0-9\-\.\_\+]*$",
            
            # System services - exact service names only
            r"^systemctl (start|stop|restart|reload|status|enable|disable) [a-zA-Z0-9\-\.\_]+$",
            
            # RetroPie configuration - safe arguments only
            r"^raspi-config nonint [a-zA-Z0-9\-\_]+ [a-zA-Z0-9\-\_]+$",
            r"^raspi-config --expand-rootfs$",
            r"^raspi-config --memory-split [0-9]+$",
            
            # File operations - specific paths only (using actual username)
            rf"^chmod 600 {re.escape(self.user_home)}/.retromcp/[a-zA-Z0-9\-\.\_]+$",
            rf"^chmod 644 {re.escape(self.user_home)}/.retromcp/[a-zA-Z0-9\-\.\_]+\.log$",
            rf"^chmod 755 {re.escape(self.user_home)}/RetroPie/roms/[a-zA-Z0-9\-\.\_/]+$",
            rf"^chown {re.escape(self.username)}:{re.escape(self.username)} {re.escape(self.user_home)}/.retromcp/[a-zA-Z0-9\-\.\_]+$",
            rf"^chown -R {re.escape(self.username)}:{re.escape(self.username)} {re.escape(self.user_home)}/RetroPie/(roms|BIOS)/[a-zA-Z0-9\-\.\_/]*$",
            
            # Process management
            r"^killall emulationstation$",
            r"^pkill emulationstation$",
            r"^kill -(TERM|HUP) [0-9]+$",
            
            # Hardware monitoring
            r"^vcgencmd [a-zA-Z0-9\_\-]+( [a-zA-Z0-9\_\-]+)*$",
            r"^gpio [a-zA-Z0-9\_\-]+( [a-zA-Z0-9\_\-]+)*$",
            
            # Network management
            r"^ifconfig [a-zA-Z0-9\_\-]+ [a-zA-Z0-9\.\_\-]+$",
            r"^iwconfig [a-zA-Z0-9\_\-]+ [a-zA-Z0-9\.\_\-]+$",
            
            # RetroPie executables - exact paths only (using actual username)
            r"^/opt/retropie/supplementary/emulationstation/emulationstation$",
            rf"^{re.escape(self.user_home)}/RetroPie-Setup/retropie_packages\.sh [a-zA-Z0-9\-\.\_]+( [a-zA-Z0-9\-\.\_]+)*$",
            rf"^{re.escape(self.user_home)}/RetroPie-Setup/retropie_setup\.sh$",
            
            # System control (use with extreme caution)
            r"^reboot$",
            r"^shutdown (-h|-r) (now|[0-9]+)$",
        ]

        # Check if command matches any allowed pattern
        command_stripped = command.strip()
        
        import re
        for pattern in allowed_patterns:
            if re.match(pattern, command_stripped):
                # Additional security validation
                self._validate_command_security(command_stripped)
                return

        logger.warning(f"Security: Blocked unauthorized sudo command: {command!r}")
        raise ValueError(f"Command not allowed for sudo execution: {command}")

    def _validate_command_security(self, command: str) -> None:
        """Additional security validation for commands.
        
        Args:
            command: Command to validate
            
        Raises:
            ValueError: If command contains dangerous patterns
        """
        # Block dangerous patterns that could bypass validation
        dangerous_patterns = [
            # Command injection
            "&&", "||", ";", "|", "`", "$(",
            # Redirection and pipes
            ">", "<", ">>", "<<",
            # Dangerous operations
            "rm -rf", "dd if=", "mkfs", "fdisk",
            # Privilege escalation
            "passwd", "sudo", "su ", "su\t", "su\n",
            # Permission changes
            "chmod 777", "chmod +s", "chown root",
            # System file modification
            ">/etc/", ">>/etc/", "</etc/",
            # Network tools that could be misused
            "wget", "curl", "nc ", "netcat",
            # Execution
            "exec", "eval", "source", "\\.\\./",
        ]

        command_lower = command.lower()
        for pattern in dangerous_patterns:
            if pattern in command_lower:
                logger.warning(f"Security: Blocked dangerous command pattern '{pattern}': {command!r}")
                raise ValueError(f"Command contains dangerous pattern: {pattern}")

    def set_sudo_password(self, password: str) -> None:
        """Set sudo password for privileged operations.

        Args:
            password: Sudo password
        """
        self.sudo_password = password

    def prompt_sudo_password(self) -> bool:
        """Prompt user for sudo password if not set.

        Returns:
            True if password was obtained, False otherwise
        """
        if not self.sudo_password:
            try:
                self.sudo_password = getpass.getpass("Enter sudo password for remote host: ")
                return bool(self.sudo_password)
            except (KeyboardInterrupt, EOFError):
                logger.info("Sudo password prompt cancelled")
                return False
        return True

    def install_packages_secure(self, packages: List[str]) -> Tuple[bool, str]:
        """Install packages with proper validation and sudo.

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

        # Ensure sudo password is available
        if not self.prompt_sudo_password():
            return False, "Sudo password required for package installation"

        # Update package list
        update_cmd = "apt-get update"
        exit_code, _, stderr = self.execute_command(update_cmd, use_sudo=True)
        if exit_code != 0:
            return (
                False,
                f"Failed to update package list: {self._sanitize_error(stderr)}",
            )

        # Install packages with escaped names
        install_cmd = f"apt-get install -y {package_str}"
        exit_code, stdout, stderr = self.execute_command(install_cmd, use_sudo=True)

        if exit_code == 0:
            return True, "Successfully installed packages"
        else:
            return False, f"Failed to install packages: {self._sanitize_error(stderr)}"

    def validate_package_name(self, package: str) -> None:
        """Validate package name format."""
        if not package or not package.strip():
            logger.warning("Security: Rejected empty package name")
            raise ValueError("Invalid package name: cannot be empty")

        # Check for obvious dangerous characters
        dangerous_chars = [";", "$", "`", "|", "&", "\x00", "\n", "\r", ".."]
        for char in dangerous_chars:
            if char in package:
                logger.warning(
                    f"Security: Rejected package name with dangerous character: {package!r}"
                )
                raise ValueError(
                    f"Invalid package name: contains dangerous character '{char}'"
                )

    def __enter__(self) -> "SecureSSHHandlerV2":
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        """Context manager exit - ensure cleanup."""
        self.disconnect()
