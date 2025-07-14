"""SSH implementation of RetroPie client."""

import time
from typing import Optional

from ..domain.models import CommandResult
from ..domain.models import ConnectionInfo
from ..domain.ports import RetroPieClient
from ..ssh_handler import RetroPieSSH


class SSHRetroPieClient(RetroPieClient):
    """SSH implementation of RetroPie client interface."""

    def __init__(self, ssh_handler: RetroPieSSH) -> None:
        """Initialize with SSH handler."""
        self._ssh = ssh_handler
        self._last_connected: Optional[str] = None

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
