"""System-related use cases for RetroMCP."""

import re

from ..domain.models import CommandExecutionMode
from ..domain.models import CommandResult
from ..domain.models import ConnectionError
from ..domain.models import ConnectionInfo
from ..domain.models import ExecuteCommandRequest
from ..domain.models import ExecutionError
from ..domain.models import Result
from ..domain.models import SystemInfo
from ..domain.models import ValidationError
from ..domain.models import WriteFileRequest
from ..domain.ports import RetroPieClient
from ..domain.ports import SystemRepository


class TestConnectionUseCase:
    """Use case for testing connection to RetroPie."""

    def __init__(self, client: RetroPieClient) -> None:
        """Initialize with RetroPie client."""
        self._client = client

    def execute(self) -> Result[ConnectionInfo, ConnectionError]:
        """Test the connection and return connection info."""
        try:
            # Ensure connection is established
            if not self._client.test_connection():
                self._client.connect()

            connection_info = self._client.get_connection_info()
            return Result.success(connection_info)
        except Exception as e:
            return Result.error(ConnectionError(
                code="CONNECTION_TEST_FAILED",
                message=f"Failed to test connection: {e}",
                details={"error": str(e)}
            ))


class GetSystemInfoUseCase:
    """Use case for getting system information."""

    def __init__(self, system_repo: SystemRepository) -> None:
        """Initialize with system repository."""
        self._system_repo = system_repo

    def execute(
        self,
    ) -> Result[SystemInfo, ConnectionError | ExecutionError | ValidationError]:
        """Get system information."""
        return self._system_repo.get_system_info()


class UpdateSystemUseCase:
    """Use case for updating the system."""

    def __init__(self, system_repo: SystemRepository) -> None:
        """Initialize with system repository."""
        self._system_repo = system_repo

    def execute(
        self,
    ) -> Result[CommandResult, ConnectionError | ExecutionError | ValidationError]:
        """Update the system."""
        return self._system_repo.update_system()


class ExecuteCommandUseCase:
    """Use case for executing commands on the system."""

    def __init__(self, client: RetroPieClient) -> None:
        """Initialize with RetroPie client."""
        self._client = client

    def execute(self, request: ExecuteCommandRequest) -> Result[CommandResult, ValidationError | ConnectionError | ExecutionError]:
        """Execute a command on the system."""
        try:
            # Validate command for security
            self._validate_command_security(request.command)

            # Handle monitoring commands differently
            if request.mode == CommandExecutionMode.MONITORING:
                return self._execute_monitoring_command(request)

            # Build final command with proper escaping
            final_command = self._build_secure_command(request)

            # Execute with proper error handling
            result = self._client.execute_command(final_command)
            return Result.success(result)
        except ValueError as e:
            # Security validation errors
            if "dangerous pattern" in str(e):
                return Result.error(ValidationError(
                    code="DANGEROUS_COMMAND",
                    message=f"Command contains dangerous pattern: {e}",
                    details={"command": request.command}
                ))
            elif "dangerous operators" in str(e):
                return Result.error(ValidationError(
                    code="COMMAND_INJECTION",
                    message=f"Command contains potentially dangerous operators: {e}",
                    details={"command": request.command}
                ))
            elif "empty" in str(e).lower():
                return Result.error(ValidationError(
                    code="EMPTY_COMMAND",
                    message=str(e),
                    details={"command": request.command}
                ))
            else:
                return Result.error(ValidationError(
                    code="INVALID_COMMAND",
                    message=str(e),
                    details={"command": request.command}
                ))
        except OSError as e:
            return Result.error(ConnectionError(
                code="SSH_CONNECTION_FAILED",
                message=f"Failed to connect to system: {e}",
                details={"error": str(e)}
            ))
        except Exception as e:
            return Result.error(ExecutionError(
                code="COMMAND_EXECUTION_FAILED",
                message="Command execution failed",
                command=request.command,
                exit_code=1,
                stderr=str(e)
            ))

    def _validate_command_security(self, command: str) -> None:
        """Validate command for security issues."""
        # Check for empty command
        if not command or not command.strip():
            raise ValueError("Command cannot be empty")

        # Define patterns for dangerous commands
        dangerous_patterns = [
            r"rm\s+-rf\s*/",  # Destructive rm commands (direct)
            r";.*rm\s+-rf\s*/",  # Destructive rm commands (after semicolon)
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

            if not any(
                re.match(pattern, command, re.IGNORECASE) for pattern in safe_patterns
            ):
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

    def _execute_monitoring_command(
        self, request: ExecuteCommandRequest
    ) -> Result[CommandResult, ExecutionError]:
        """Execute a monitoring command with appropriate handling.

        Args:
            request: Command execution request with monitoring mode

        Returns:
            Result with CommandResult or ExecutionError
        """
        # Monitoring commands get special handling - delegate to client
        try:
            result = self._client.execute_monitoring_command(request.command)
            return Result.success(result)
        except Exception as e:
            return Result.error(ExecutionError(
                code="MONITORING_COMMAND_FAILED",
                message="Monitoring command execution failed",
                command=request.command,
                exit_code=1,
                stderr=str(e)
            ))


class WriteFileUseCase:
    """Use case for writing files to the system."""

    def __init__(self, client: RetroPieClient) -> None:
        """Initialize with RetroPie client."""
        self._client = client

    def execute(self, request: WriteFileRequest) -> Result[CommandResult, ValidationError | ConnectionError | ExecutionError]:
        """Write a file to the system."""
        try:
            # Validate path for security
            self._validate_path_security(request.path)

            # Write the file using command execution
            result = self._write_file_via_command(request.path, request.content)
            return Result.success(result)
        except ValueError as e:
            # Path validation errors
            if "path traversal" in str(e).lower():
                return Result.error(ValidationError(
                    code="PATH_TRAVERSAL",
                    message=str(e),
                    details={"path": request.path}
                ))
            elif "sensitive path" in str(e).lower():
                return Result.error(ValidationError(
                    code="SENSITIVE_PATH",
                    message=str(e),
                    details={"path": request.path}
                ))
            elif "absolute path" in str(e).lower():
                return Result.error(ValidationError(
                    code="RELATIVE_PATH",
                    message=str(e),
                    details={"path": request.path}
                ))
            else:
                return Result.error(ValidationError(
                    code="INVALID_PATH",
                    message=str(e),
                    details={"path": request.path}
                ))
        except OSError as e:
            return Result.error(ConnectionError(
                code="FILE_WRITE_CONNECTION_FAILED",
                message=f"Failed to connect for file write: {e}",
                details={"path": request.path, "error": str(e)}
            ))
        except Exception as e:
            return Result.error(ExecutionError(
                code="FILE_WRITE_FAILED",
                message="Failed to write file",
                command=f"write file {request.path}",
                exit_code=1,
                stderr=str(e)
            ))

    def _write_file_via_command(self, path: str, content: str) -> CommandResult:
        """Write file content using command execution."""
        import shlex

        # Create parent directories if they don't exist
        parent_dir = path.rsplit('/', 1)[0] if '/' in path else '/'
        if parent_dir != '/':
            mkdir_command = f"mkdir -p {shlex.quote(parent_dir)}"
            mkdir_result = self._client.execute_command(mkdir_command)
            if not mkdir_result.success:
                raise OSError(f"Failed to create parent directories: {mkdir_result.stderr}")

        # Handle empty content case
        if not content:
            touch_command = f"touch {shlex.quote(path)}"
            return self._client.execute_command(touch_command)

        # For non-empty content, use cat with here-document for safe content writing
        # This approach handles special characters and newlines properly
        escaped_content = content.replace("'", "'\"'\"'")  # Escape single quotes
        cat_command = f"cat > {shlex.quote(path)} << 'EOF'\n{escaped_content}\nEOF"

        return self._client.execute_command(cat_command)

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
            if (
                path.startswith(sensitive_path)
                or sensitive_path.replace("*", "") in path
            ):
                raise ValueError(f"Writing to sensitive path is not allowed: {path}")

        # Require absolute paths
        if not path.startswith("/"):
            raise ValueError("Only absolute paths are allowed")
