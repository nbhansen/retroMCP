"""SSH implementation of RetroPie client."""

import time
from typing import Optional

from ..domain.models import CommandResult
from ..domain.models import ConnectionInfo
from ..domain.ports import RetroPieClient
from ..ssh_handler import RetroPieSSH
from .structured_logger import StructuredLogger


class SSHRetroPieClient(RetroPieClient):
    """SSH implementation of RetroPie client interface."""

    def __init__(self, ssh_handler: RetroPieSSH) -> None:
        """Initialize with SSH handler."""
        self._ssh = ssh_handler
        self._last_connected: Optional[str] = None
        self._logger = StructuredLogger("ssh_client")

    def connect(self) -> bool:
        """Establish connection to RetroPie system."""
        success = self._ssh.connect()
        if success:
            self._last_connected = time.strftime("%Y-%m-%d %H:%M:%S")
        return success

    def disconnect(self) -> None:
        """Close connection to RetroPie system."""
        self._ssh.disconnect()

    def test_connection(self) -> bool:
        """Test if connection is active."""
        return self._ssh.test_connection()

    def get_connection_info(self) -> ConnectionInfo:
        """Get connection information."""
        return ConnectionInfo(
            host=self._ssh.host,
            port=self._ssh.port,
            username=self._ssh.username,
            connected=self.test_connection(),
            last_connected=self._last_connected,
            connection_method="ssh",
        )

    def execute_command(self, command: str, use_sudo: bool = False) -> CommandResult:
        """Execute a command on the RetroPie system."""
        start_time = time.time()

        try:
            # Handle sudo if needed
            if use_sudo and not command.startswith("sudo "):
                command = f"sudo {command}"

            exit_code, stdout, stderr = self._ssh.execute_command(command)
            execution_time = time.time() - start_time

            return CommandResult(
                command=command,
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                success=exit_code == 0,
                execution_time=execution_time,
            )
        except Exception as e:
            execution_time = time.time() - start_time
            return CommandResult(
                command=command,
                exit_code=1,
                stdout="",
                stderr=str(e),
                success=False,
                execution_time=execution_time,
            )

    def execute_monitoring_command(self, command: str) -> CommandResult:
        """Execute a monitoring command that runs indefinitely.

        This method delegates to the SSH handler's specialized monitoring
        command execution which provides user guidance on termination.
        """
        start_time = time.time()

        try:
            exit_code, stdout, stderr = self._ssh.execute_monitoring_command(command)
            execution_time = time.time() - start_time

            return CommandResult(
                command=command,
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                success=exit_code == 0,
                execution_time=execution_time,
            )
        except Exception as e:
            execution_time = time.time() - start_time
            return CommandResult(
                command=command,
                exit_code=1,
                stdout="",
                stderr=str(e),
                success=False,
                execution_time=execution_time,
            )

    def execute_command_with_retry(
        self, command: str, max_retries: int = 3, use_sudo: bool = False
    ) -> CommandResult:
        """Execute command with retry logic for transient failures."""
        last_exception = None
        start_time = time.time()

        # Handle sudo if needed
        if use_sudo and not command.startswith("sudo "):
            command = f"sudo {command}"

        for attempt in range(max_retries):
            try:
                self._logger.debug(
                    f"Executing command (attempt {attempt + 1}/{max_retries})",
                    command=command,
                    attempt=attempt + 1,
                    max_retries=max_retries,
                )
                exit_code, stdout, stderr = self._ssh.execute_command(command)
                execution_time = time.time() - start_time

                if attempt > 0:
                    self._logger.info(
                        "Command succeeded on retry",
                        command=command,
                        attempt=attempt + 1,
                        total_duration=round(execution_time * 1000, 2),
                    )

                return CommandResult(
                    command=command,
                    exit_code=exit_code,
                    stdout=stdout,
                    stderr=stderr,
                    success=exit_code == 0,
                    execution_time=execution_time,
                )
            except Exception as e:
                last_exception = e
                self._logger.warning(
                    f"Command execution failed (attempt {attempt + 1}/{max_retries}): {e}",
                    command=command,
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    error_type=type(e).__name__,
                )

                if attempt < max_retries - 1:
                    self._logger.info(
                        f"Retrying command execution, attempt {attempt + 2}/{max_retries}"
                    )
                    # Exponential backoff: wait 1s, 2s, 4s between retries
                    wait_time = 2**attempt
                    time.sleep(wait_time)

        # All retries exhausted
        self._logger.error_with_context(
            f"Command execution failed after {max_retries} attempts",
            error_type="retry_exhausted",
            command=command,
            max_retries=max_retries,
            final_error=str(last_exception),
        )
        execution_time = time.time() - start_time
        return CommandResult(
            command=command,
            exit_code=1,
            stdout="",
            stderr=str(last_exception),
            success=False,
            execution_time=execution_time,
        )

    def execute_command_with_timeout(
        self, command: str, timeout: float, use_sudo: bool = False
    ) -> CommandResult:
        """Execute command with timeout handling."""
        start_time = time.time()

        try:
            # This is a simplified timeout implementation
            # In practice, you'd use threading or asyncio for proper timeout handling
            result = self.execute_command(command, use_sudo=use_sudo)

            # Check if execution time exceeded timeout
            if result.execution_time > timeout:
                self._logger.warning(
                    f"Command timed out after {timeout}s",
                    command=command,
                    timeout=timeout,
                    actual_duration=round(result.execution_time, 2),
                )
                return CommandResult(
                    command=command,
                    exit_code=124,  # Standard timeout exit code
                    stdout=result.stdout,
                    stderr=f"Command timed out after {timeout} seconds",
                    success=False,
                    execution_time=result.execution_time,
                )

            return result

        except Exception as e:
            execution_time = time.time() - start_time
            self._logger.error_with_context(
                "Command execution failed with timeout",
                error_type="timeout",
                command=command,
                timeout=timeout,
                exception=str(e),
            )
            return CommandResult(
                command=command,
                exit_code=1,
                stdout="",
                stderr=str(e),
                success=False,
                execution_time=execution_time,
            )

    def execute_command_with_enhanced_error_handling(
        self, command: str, use_sudo: bool = False
    ) -> CommandResult:
        """Execute command with enhanced error categorization."""
        start_time = time.time()

        try:
            # Handle sudo if needed
            if use_sudo and not command.startswith("sudo "):
                command = f"sudo {command}"

            exit_code, stdout, stderr = self._ssh.execute_command(command)
            execution_time = time.time() - start_time

            return CommandResult(
                command=command,
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                success=exit_code == 0,
                execution_time=execution_time,
            )
        except Exception as e:
            execution_time = time.time() - start_time
            error_message = str(e).lower()

            # Categorize errors for better user experience
            if "connection" in error_message or "refused" in error_message:
                self._logger.error_with_context(
                    f"Connection error executing command: {e}",
                    error_type="connection",
                    command=command,
                    exit_code=2,
                )
                exit_code = 2  # Connection error
            elif "authentication" in error_message or "auth" in error_message:
                self._logger.error_with_context(
                    f"Authentication error executing command: {e}",
                    error_type="authentication",
                    command=command,
                    exit_code=3,
                )
                exit_code = 3  # Authentication error
            elif "permission" in error_message or "denied" in error_message:
                self._logger.error_with_context(
                    f"Permission error executing command: {e}",
                    error_type="permission",
                    command=command,
                    exit_code=126,
                )
                exit_code = 126  # Permission denied
            else:
                self._logger.error_with_context(
                    f"General error executing command: {e}",
                    error_type="general",
                    command=command,
                    exit_code=1,
                )
                exit_code = 1  # General error

            return CommandResult(
                command=command,
                exit_code=exit_code,
                stdout="",
                stderr=str(e),
                success=False,
                execution_time=execution_time,
            )
