"""Application use cases for RetroMCP."""

import re
import shlex
from typing import List
from typing import Optional

from ..domain.models import CommandResult
from ..domain.models import ConnectionInfo
from ..domain.models import Controller
from ..domain.models import EmulatorStatus
from ..domain.models import ExecuteCommandRequest
from ..domain.models import RomDirectory
from ..domain.models import SystemInfo
from ..domain.models import WriteFileRequest
from ..domain.ports import ControllerRepository
from ..domain.ports import EmulatorRepository
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

    def __init__(self, system_repo: SystemRepository) -> None:
        """Initialize with system repository."""
        self._system_repo = system_repo

    def execute(self) -> SystemInfo:
        """Get system information."""
        return self._system_repo.get_system_info()


class InstallPackagesUseCase:
    """Use case for installing system packages."""

    def __init__(self, system_repo: SystemRepository) -> None:
        """Initialize with system repository."""
        self._system_repo = system_repo

    def execute(self, packages: List[str]) -> CommandResult:
        """Install the specified packages."""
        if not packages:
            return CommandResult(
                command="",
                exit_code=0,
                stdout="No packages specified",
                stderr="",
                success=True,
                execution_time=0.0,
            )

        # Filter out already installed packages
        installed_packages = self._system_repo.get_packages()
        installed_names = {pkg.name for pkg in installed_packages if pkg.installed}

        packages_to_install = [pkg for pkg in packages if pkg not in installed_names]

        if not packages_to_install:
            return CommandResult(
                command="",
                exit_code=0,
                stdout="All packages are already installed",
                stderr="",
                success=True,
                execution_time=0.0,
            )

        return self._system_repo.install_packages(packages_to_install)


class UpdateSystemUseCase:
    """Use case for updating the system."""

    def __init__(self, system_repo: SystemRepository) -> None:
        """Initialize with system repository."""
        self._system_repo = system_repo

    def execute(self) -> CommandResult:
        """Update the system packages."""
        return self._system_repo.update_system()


class DetectControllersUseCase:
    """Use case for detecting connected controllers."""

    def __init__(self, controller_repo: ControllerRepository) -> None:
        """Initialize with controller repository."""
        self._controller_repo = controller_repo

    def execute(self) -> List[Controller]:
        """Detect and return connected controllers."""
        return self._controller_repo.detect_controllers()


class SetupControllerUseCase:
    """Use case for setting up a controller."""

    def __init__(self, controller_repo: ControllerRepository) -> None:
        """Initialize with controller repository."""
        self._controller_repo = controller_repo

    def execute(self, controller_type: str) -> CommandResult:
        """Set up a controller of the specified type."""
        # First detect controllers
        controllers = self._controller_repo.detect_controllers()

        # Find a controller matching the type
        target_controller = None
        for controller in controllers:
            if (
                controller_type.lower() in controller.name.lower()
                or controller_type.lower() == controller.controller_type.value
            ):
                target_controller = controller
                break

        if not target_controller:
            return CommandResult(
                command="",
                exit_code=1,
                stdout="",
                stderr=f"No {controller_type} controller detected",
                success=False,
                execution_time=0.0,
            )

        # Check if already configured
        if target_controller.is_configured and not target_controller.driver_required:
            return CommandResult(
                command="",
                exit_code=0,
                stdout=f"{controller_type} controller is already configured",
                stderr="",
                success=True,
                execution_time=0.0,
            )

        # Set up the controller
        return self._controller_repo.setup_controller(target_controller)


class InstallEmulatorUseCase:
    """Use case for installing an emulator."""

    def __init__(self, emulator_repo: EmulatorRepository) -> None:
        """Initialize with emulator repository."""
        self._emulator_repo = emulator_repo

    def execute(self, emulator_name: str) -> CommandResult:
        """Install the specified emulator."""
        # Check if emulator exists and its status
        emulators = self._emulator_repo.get_emulators()

        target_emulator = None
        for emulator in emulators:
            if emulator.name == emulator_name:
                target_emulator = emulator
                break

        if not target_emulator:
            return CommandResult(
                command="",
                exit_code=1,
                stdout="",
                stderr=f"Emulator '{emulator_name}' not found",
                success=False,
                execution_time=0.0,
            )

        if target_emulator.status == EmulatorStatus.INSTALLED:
            return CommandResult(
                command="",
                exit_code=0,
                stdout=f"Emulator '{emulator_name}' is already installed",
                stderr="",
                success=True,
                execution_time=0.0,
            )

        if target_emulator.status == EmulatorStatus.NOT_AVAILABLE:
            return CommandResult(
                command="",
                exit_code=1,
                stdout="",
                stderr=f"Emulator '{emulator_name}' is not available for installation",
                success=False,
                execution_time=0.0,
            )

        # Install the emulator
        return self._emulator_repo.install_emulator(emulator_name)


class ListRomsUseCase:
    """Use case for listing ROM directories and files."""

    def __init__(self, emulator_repo: EmulatorRepository) -> None:
        """Initialize with emulator repository."""
        self._emulator_repo = emulator_repo

    def execute(
        self, system_filter: Optional[str] = None, min_rom_count: Optional[int] = None
    ) -> List[RomDirectory]:
        """List ROM directories with optional filtering.

        Args:
            system_filter: Optional system name to filter by
            min_rom_count: Optional minimum ROM count to filter by

        Returns:
            List of RomDirectory objects, sorted by ROM count descending
        """
        # Get all ROM directories from repository
        rom_directories = self._emulator_repo.get_rom_directories()

        # Apply system filter if specified
        if system_filter:
            rom_directories = [
                rom_dir
                for rom_dir in rom_directories
                if rom_dir.system == system_filter
            ]

        # Apply minimum ROM count filter if specified
        if min_rom_count is not None:
            rom_directories = [
                rom_dir
                for rom_dir in rom_directories
                if rom_dir.rom_count >= min_rom_count
            ]

        # Sort by ROM count descending (most ROMs first)
        rom_directories.sort(key=lambda r: r.rom_count, reverse=True)

        return rom_directories


class ExecuteCommandUseCase:
    """Use case for secure command execution."""

    def __init__(self, client: RetroPieClient) -> None:
        """Initialize with RetroPie client."""
        self._client = client

    def execute(self, request: ExecuteCommandRequest) -> CommandResult:
        """Execute command with security validation.

        Args:
            request: ExecuteCommandRequest with command details

        Returns:
            CommandResult with execution details

        Raises:
            ValueError: If command fails security validation
        """
        # Validate command for security
        self._validate_command_security(request.command)

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
        """Validate command for security vulnerabilities.

        Args:
            command: Command to validate

        Raises:
            ValueError: If command contains dangerous patterns
        """
        if not command or not command.strip():
            raise ValueError("Command cannot be empty")

        # Block dangerous patterns
        dangerous_patterns = [
            r";.*rm\s+-rf\s*/",  # Destructive rm commands
            r"\$\(.*\)",  # Command substitution
            r"`.*`",  # Backtick execution
            r"\|.*>.*/",  # Pipe to system file overwrite
            r"&.*&",  # Background process chains
            r"nc\s+-l.*",  # Netcat listeners
            r"curl.*\|.*sh",  # Download and execute
            r"wget.*\|.*sh",  # Download and execute
            r"exec\s+.*",  # Direct exec calls
            r"eval\s+.*",  # Eval execution
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                raise ValueError(f"Command contains dangerous pattern: {pattern}")

        # Block destructive commands entirely
        destructive_commands = [
            "rm -rf /",
            "mkfs",
            "dd if=",
            "shutdown",
            "reboot",
            "halt",
            "init 0",
            "init 6",
        ]

        command_lower = command.lower()
        for destructive in destructive_commands:
            if destructive.lower() in command_lower:
                raise ValueError(
                    f"Command contains destructive operation: {destructive}"
                )

    def _build_secure_command(self, request: ExecuteCommandRequest) -> str:
        """Build secure command with proper escaping.

        Args:
            request: ExecuteCommandRequest with command details

        Returns:
            Safely escaped command string
        """
        # Start with base command (already validated)
        command = request.command.strip()

        # Add working directory if specified
        if request.working_directory:
            # Validate working directory path
            if ".." in request.working_directory:
                raise ValueError("Working directory contains path traversal")

            safe_dir = shlex.quote(request.working_directory)
            command = f"cd {safe_dir} && {command}"

        # Add sudo if requested
        if request.use_sudo:
            command = f"sudo {command}"

        # Add timeout if specified
        if request.timeout and request.timeout > 0:
            command = f"timeout {request.timeout} {command}"

        return command


class WriteFileUseCase:
    """Use case for secure file writing."""

    def __init__(self, client: RetroPieClient) -> None:
        """Initialize with RetroPie client."""
        self._client = client

    def execute(self, request: WriteFileRequest) -> CommandResult:
        """Write file with security validation.

        Args:
            request: WriteFileRequest with file details

        Returns:
            CommandResult with write operation details

        Raises:
            ValueError: If path fails security validation
        """
        # Validate path for security
        self._validate_path_security(request.path)

        # Create backup if requested
        if request.backup:
            backup_result = self._create_backup(request.path)
            if not backup_result.success:
                return backup_result

        # Write file content
        return self._write_file_secure(request)

    def _validate_path_security(self, path: str) -> None:
        """Validate file path for security.

        Args:
            path: File path to validate

        Raises:
            ValueError: If path is unsafe
        """
        if not path or not path.strip():
            raise ValueError("File path cannot be empty")

        path = path.strip()

        # Prevent path traversal
        if ".." in path:
            raise ValueError("Path traversal attempt detected in file path")

        # Block absolute paths to critical system directories
        forbidden_prefixes = [
            "/etc/",
            "/boot/",
            "/sys/",
            "/proc/",
            "/dev/",
            "/root/",
            "/usr/bin/",
            "/usr/sbin/",
            "/bin/",
            "/sbin/",
        ]

        for prefix in forbidden_prefixes:
            if path.startswith(prefix):
                raise ValueError(
                    f"Cannot write to protected system directory: {prefix}"
                )

        # Block specific critical files
        forbidden_files = [
            "/etc/passwd",
            "/etc/shadow",
            "/etc/sudoers",
            "/etc/hosts",
            "/etc/fstab",
            "/var/log/auth.log",
            "/var/log/syslog",
        ]

        if path in forbidden_files:
            raise ValueError(f"Cannot write to protected system file: {path}")

        # Ensure path is within allowed directories
        allowed_prefixes = [
            "/home/",
            "/tmp/",
            "/opt/retropie/configs/",
            "/var/tmp/",
        ]

        if not any(path.startswith(prefix) for prefix in allowed_prefixes):
            raise ValueError(f"File path not in allowed directories: {path}")

    def _create_backup(self, path: str) -> CommandResult:
        """Create backup of existing file.

        Args:
            path: Original file path

        Returns:
            CommandResult of backup operation
        """
        safe_path = shlex.quote(path)
        backup_path = f"{path}.backup.$(date +%Y%m%d_%H%M%S)"
        safe_backup = shlex.quote(backup_path)

        backup_command = (
            f"[ -f {safe_path} ] && sudo cp {safe_path} {safe_backup} || true"
        )

        return self._client.execute_command(backup_command)

    def _write_file_secure(self, request: WriteFileRequest) -> CommandResult:
        """Write file content securely.

        Args:
            request: WriteFileRequest with file details

        Returns:
            CommandResult of write operation
        """
        safe_path = shlex.quote(request.path)

        # Create parent directories if requested
        if request.create_directories:
            parent_dir = shlex.quote(str(request.path).rsplit("/", 1)[0])
            mkdir_result = self._client.execute_command(f"sudo mkdir -p {parent_dir}")
            if not mkdir_result.success:
                return mkdir_result

        # Write content using cat with here document for safety
        # This avoids shell injection issues with echo
        safe_content = request.content.replace("'", "'\"'\"'")  # Escape single quotes

        write_command = f"sudo tee {safe_path} > /dev/null << 'EOF_RETROMCP'\n{safe_content}\nEOF_RETROMCP"

        write_result = self._client.execute_command(write_command)

        # Set permissions if specified
        if request.mode and write_result.success:
            safe_mode = shlex.quote(request.mode)
            chmod_result = self._client.execute_command(
                f"sudo chmod {safe_mode} {safe_path}"
            )

            if not chmod_result.success:
                return CommandResult(
                    command=f"chmod {safe_mode} {safe_path}",
                    exit_code=chmod_result.exit_code,
                    stdout=write_result.stdout,
                    stderr=f"File written but chmod failed: {chmod_result.stderr}",
                    success=False,
                    execution_time=write_result.execution_time
                    + chmod_result.execution_time,
                )

        return write_result
