"""Domain ports (interfaces) for RetroMCP."""

from abc import ABC
from abc import abstractmethod
from typing import Any
from typing import Dict
from typing import List

from .models import BiosFile
from .models import CommandResult
from .models import ConfigFile
from .models import ConnectionInfo
from .models import Controller
from .models import DockerManagementRequest
from .models import DockerManagementResult
from .models import Emulator
from .models import Package
from .models import RomDirectory
from .models import StateManagementResult
from .models import SystemInfo
from .models import SystemService
from .models import SystemState
from .models import Theme


class RetroPieClient(ABC):
    """Interface for RetroPie system communication."""

    @abstractmethod
    def connect(self) -> bool:
        """Establish connection to RetroPie system."""

    @abstractmethod
    def disconnect(self) -> None:
        """Close connection to RetroPie system."""

    @abstractmethod
    def test_connection(self) -> bool:
        """Test if connection is active."""

    @abstractmethod
    def get_connection_info(self) -> ConnectionInfo:
        """Get connection information."""

    @abstractmethod
    def execute_command(self, command: str, use_sudo: bool = False) -> CommandResult:
        """Execute a command on the RetroPie system."""


class SystemRepository(ABC):
    """Interface for system-level operations."""

    @abstractmethod
    def get_system_info(self) -> SystemInfo:
        """Get system information."""

    @abstractmethod
    def get_packages(self) -> List[Package]:
        """Get list of installed packages."""

    @abstractmethod
    def install_packages(self, packages: List[str]) -> CommandResult:
        """Install system packages."""

    @abstractmethod
    def update_system(self) -> CommandResult:
        """Update system packages."""

    @abstractmethod
    def get_services(self) -> List[SystemService]:
        """Get list of system services."""

    @abstractmethod
    def restart_service(self, service_name: str) -> CommandResult:
        """Restart a system service."""

    @abstractmethod
    def get_bios_files(self) -> List[BiosFile]:
        """Get list of BIOS files."""


class ControllerRepository(ABC):
    """Interface for controller management."""

    @abstractmethod
    def detect_controllers(self) -> List[Controller]:
        """Detect connected controllers."""

    @abstractmethod
    def setup_controller(self, controller: Controller) -> CommandResult:
        """Set up a controller with appropriate drivers."""

    @abstractmethod
    def test_controller(self, controller: Controller) -> CommandResult:
        """Test controller functionality."""

    @abstractmethod
    def configure_controller_mapping(
        self, controller: Controller, mapping: dict
    ) -> CommandResult:
        """Configure controller button mapping."""


class EmulatorRepository(ABC):
    """Interface for emulator management."""

    @abstractmethod
    def get_emulators(self) -> List[Emulator]:
        """Get list of available emulators."""

    @abstractmethod
    def install_emulator(self, emulator_name: str) -> CommandResult:
        """Install an emulator."""

    @abstractmethod
    def get_rom_directories(self) -> List[RomDirectory]:
        """Get ROM directories information."""

    @abstractmethod
    def get_config_files(self, system: str) -> List[ConfigFile]:
        """Get configuration files for a system."""

    @abstractmethod
    def update_config_file(self, config_file: ConfigFile) -> CommandResult:
        """Update a configuration file."""

    @abstractmethod
    def get_themes(self) -> List[Theme]:
        """Get available themes."""

    @abstractmethod
    def set_theme(self, theme_name: str) -> CommandResult:
        """Set active theme."""


class StateRepository(ABC):
    """Interface for state persistence."""

    @abstractmethod
    def load_state(self) -> SystemState:
        """Load state from storage."""

    @abstractmethod
    def save_state(self, state: SystemState) -> StateManagementResult:
        """Save state to storage."""

    @abstractmethod
    def update_state_field(self, path: str, value: Any) -> StateManagementResult:  # noqa: ANN401
        """Update specific field in state."""

    @abstractmethod
    def compare_state(self, current_state: SystemState) -> Dict[str, Any]:
        """Compare current state with stored state."""

    @abstractmethod
    def export_state(self) -> StateManagementResult:
        """Export state for backup/migration."""

    @abstractmethod
    def import_state(self, state_data: str) -> StateManagementResult:
        """Import state from backup/migration."""

    @abstractmethod
    def diff_states(self, other_state: SystemState) -> StateManagementResult:
        """Compare with another state."""

    @abstractmethod
    def watch_field(self, path: str) -> StateManagementResult:
        """Monitor specific field changes."""


class DockerRepository(ABC):
    """Interface for Docker management."""

    @abstractmethod
    def manage_containers(
        self, request: DockerManagementRequest
    ) -> DockerManagementResult:
        """Manage Docker containers."""

    @abstractmethod
    def manage_compose(
        self, request: DockerManagementRequest
    ) -> DockerManagementResult:
        """Manage Docker Compose services."""

    @abstractmethod
    def manage_volumes(
        self, request: DockerManagementRequest
    ) -> DockerManagementResult:
        """Manage Docker volumes."""

    @abstractmethod
    def is_docker_available(self) -> bool:
        """Check if Docker is available on the system."""
