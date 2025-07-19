"""System-related use cases for RetroMCP."""

import re

from ..domain.models import CommandExecutionMode
from ..domain.models import CommandResult
from ..domain.models import ConnectionInfo
from ..domain.models import ExecuteCommandRequest
from ..domain.models import SystemInfo
from ..domain.models import WriteFileRequest
from ..domain.ports import RetroPieClient
from ..domain.ports import SystemRepository


class TestConnectionUseCase:
    """Use case for testing connection to RetroPie."""

    def __init__(self, client: RetroPieClient) -> None:
        """Initialize with RetroPie client."""
        self._client = client

    def execute(self) -> ConnectionInfo:
        """Test the connection and return connection info."""
        # Ensure connection is established
        if not self._client.test_connection():
            self._client.connect()

        return self._client.get_connection_info()


class GetSystemInfoUseCase:
    """Use case for getting system information."""

    def __init__(self, client: RetroPieClient) -> None:
        """Initialize with RetroPie client."""
        self._client = client

    def execute(self) -> SystemInfo:
        """Get system information."""
        return self._client.get_system_info()


class UpdateSystemUseCase:
    """Use case for updating the system."""

    def __init__(self, client: RetroPieClient) -> None:
        """Initialize with RetroPie client."""
        self._client = client

    def execute(self) -> CommandResult:
        """Update the system."""
        return self._client.update_system()


class ExecuteCommandUseCase:
    """Use case for executing commands on the system."""

    def __init__(self, client: RetroPieClient) -> None:
        """Initialize with RetroPie client."""
        self._client = client

    def execute(self, request: ExecuteCommandRequest) -> CommandResult:
        """Execute a command on the system."""
        # Validate command for security
        self._validate_command_security(request.command)

        # Handle monitoring commands differently
        if request.mode == CommandExecutionMode.MONITORING:
            return self._execute_monitoring_command(request)

        # Build final command with proper escaping
        final_command = self._build_secure_command(request)

        # Execute with proper error handling
        try:
            result = self._client.execute_command(final_command)
            return result
        except Exception as e:
            return CommandResult(
                command=final_command,
                exit_code=1,
                stdout="",
                stderr=f"Command execution failed: {e!s}",
                success=False,
                execution_time=0.0,
            )

    def _validate_command_security(self, command: str) -> None:
        """Validate command for security issues."""
        # Define patterns for dangerous commands
        dangerous_patterns = [
            r";.*rm\s+-rf\s*/",  # Destructive rm commands
            r"\$\(.*\)",  # Command substitution
            r"`.*`",  # Backtick command substitution
            r">\s*/dev/",  # Writing to device files
            r"<\s*/dev/",  # Reading from device files
            r"sudo\s+.*passwd",  # Password changes
            r"sudo\s+.*userdel",  # User deletion
            r"sudo\s+.*groupdel",  # Group deletion
            r"mkfs\.",  # Format filesystem
            r"fdisk",  # Disk partitioning
            r"dd\s+if=",  # Disk duplication
            r"mount\s+.*loop",  # Loop device mounting
            r"umount\s+/",  # Unmounting root paths
            r"chmod\s+777",  # Overly permissive permissions
            r"chown\s+.*:",  # Ownership changes
            r"iptables",  # Firewall changes
            r"systemctl\s+.*networking",  # Network service changes
            r"ifconfig\s+.*down",  # Network interface down
            r"route\s+del",  # Route deletion
            r">/etc/",  # Writing to system config
            r"</etc/passwd",  # Reading sensitive files
            r"</etc/shadow",  # Reading password file
            r"wget\s+.*\|",  # Piped downloads
            r"curl\s+.*\|",  # Piped downloads
            r"nc\s+.*-l",  # Netcat listening
            r"python.*-c",  # Python code execution
            r"perl.*-e",  # Perl code execution
            r"ruby.*-e",  # Ruby code execution
            r"bash.*-c",  # Bash code execution
            r"sh.*-c",  # Shell code execution
            r"eval\s+",  # Eval command
            r"exec\s+",  # Exec command
            r"source\s+/dev/",  # Source from devices
            r"\.\s+/dev/",  # Dot source from devices
        ]

        # Check each pattern
        for pattern in dangerous_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                raise ValueError(f"Command contains dangerous pattern: {pattern}")

        # Additional checks for command injection
        if any(char in command for char in [";", "&", "|", "&&", "||"]):
            # Allow only specific safe combinations
            safe_patterns = [
                r"^sudo\s+.*&&\s+echo\s+",  # Safe sudo with echo
                r"^.*\s+\|\s+grep\s+",  # Piping to grep
                r"^.*\s+\|\s+head\s+",  # Piping to head
                r"^.*\s+\|\s+tail\s+",  # Piping to tail
                r"^.*\s+\|\s+wc\s+",  # Piping to wc
                r"^.*\s+\|\s+sort\s+",  # Piping to sort
                r"^.*\s+\|\s+uniq\s+",  # Piping to uniq
            ]

            if not any(re.match(pattern, command, re.IGNORECASE) for pattern in safe_patterns):
                raise ValueError("Command contains potentially dangerous operators")

    def _build_secure_command(self, request: ExecuteCommandRequest) -> str:
        """Build a secure command with proper escaping."""
        # Base command
        command = request.command

        # Add sudo if requested and not already present
        if request.use_sudo and not command.startswith("sudo"):
            command = f"sudo {command}"

        # Add timeout if specified
        if request.timeout:
            command = f"timeout {request.timeout} {command}"

        # Return the command (escaping handled at infrastructure layer)
        return command

    def _execute_monitoring_command(self, request: ExecuteCommandRequest) -> CommandResult:
        """Execute a monitoring command with appropriate handling.

        Args:
            request: Command execution request with monitoring mode

        Returns:
            CommandResult with guidance on termination
        """
        # Monitoring commands get special handling - delegate to client
        try:
            result = self._client.execute_monitoring_command(request.command)
            return result
        except Exception as e:
            return CommandResult(
                command=request.command,
                exit_code=1,
                stdout="",
                stderr=f"Monitoring command execution failed: {e!s}",
                success=False,
                execution_time=0.0,
            )


class WriteFileUseCase:
    """Use case for writing files to the system."""

    def __init__(self, repository: SystemRepository) -> None:
        """Initialize with system repository."""
        self._repository = repository

    def execute(self, request: WriteFileRequest) -> CommandResult:
        """Write a file to the system."""
        # Validate path for security
        self._validate_path_security(request.path)

        # Write the file
        return self._repository.write_file(request.path, request.content)

    def _validate_path_security(self, path: str) -> None:
        """Validate path for security issues."""
        # Prevent path traversal
        if ".." in path:
            raise ValueError("Path traversal attempt detected in file path")

        # Prevent writing to sensitive system locations
        sensitive_paths = [
            "/etc/passwd",
            "/etc/shadow",
            "/etc/sudoers",
            "/etc/ssh/",
            "/root/",
            "/home/*/.*",  # Hidden files in home directories
            "/var/log/",
            "/proc/",
            "/sys/",
            "/dev/",
            "/boot/",
        ]

        for sensitive_path in sensitive_paths:
            if path.startswith(sensitive_path) or sensitive_path.replace("*", "") in path:
                raise ValueError(f"Writing to sensitive path is not allowed: {path}")

        # Require absolute paths
        if not path.startswith("/"):
            raise ValueError("Only absolute paths are allowed")
