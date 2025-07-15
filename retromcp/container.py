"""Dependency injection container for RetroMCP."""

import logging
from typing import Any
from typing import Callable
from typing import Dict

from .application.use_cases import DetectControllersUseCase
from .application.use_cases import ExecuteCommandUseCase
from .application.use_cases import GetSystemInfoUseCase
from .application.use_cases import InstallEmulatorUseCase
from .application.use_cases import InstallPackagesUseCase
from .application.use_cases import ListRomsUseCase
from .application.use_cases import ManageStateUseCase
from .application.use_cases import SetupControllerUseCase
from .application.use_cases import TestConnectionUseCase
from .application.use_cases import UpdateSystemUseCase
from .application.use_cases import WriteFileUseCase
from .config import RetroPieConfig
from .discovery import RetroPieDiscovery
from .domain.ports import ControllerRepository
from .domain.ports import EmulatorRepository
from .domain.ports import RetroPieClient
from .domain.ports import StateRepository
from .domain.ports import SystemRepository
from .infrastructure import SSHControllerRepository
from .infrastructure import SSHEmulatorRepository
from .infrastructure import SSHRetroPieClient
from .infrastructure import SSHSystemRepository
from .infrastructure.ssh_state_repository import SSHStateRepository
from .ssh_handler import RetroPieSSH

logger = logging.getLogger(__name__)


class Container:
    """Dependency injection container."""

    def __init__(self, config: RetroPieConfig) -> None:
        """Initialize container with configuration."""
        self._initial_config = config
        self.config = config
        self._instances: Dict[str, Any] = {}
        self._discovery_completed = False

    def _get_or_create(self, key: str, factory: Callable[[], Any]) -> Any:  # noqa: ANN401
        """Get existing instance or create new one."""
        if key not in self._instances:
            self._instances[key] = factory()
        return self._instances[key]

    def _ensure_discovery(self) -> None:
        """Ensure system discovery has been performed."""
        if not self._discovery_completed:
            try:
                logger.info("Performing RetroPie system discovery")
                client = self.retropie_client
                discovery = RetroPieDiscovery(client)
                paths = discovery.discover_system_paths()
                self.config = self._initial_config.with_paths(paths)
                self._discovery_completed = True
                logger.info("System discovery completed successfully")
            except Exception as e:
                logger.warning(f"System discovery failed: {e}, using defaults")
                self._discovery_completed = True  # Don't retry on every call

    @property
    def ssh_handler(self) -> RetroPieSSH:
        """Get SSH handler instance."""
        return self._get_or_create(
            "ssh_handler",
            lambda: RetroPieSSH(
                host=self.config.host,
                username=self.config.username,
                password=self.config.password,
                key_path=self.config.key_path,
                port=self.config.port,
            ),
        )

    @property
    def retropie_client(self) -> RetroPieClient:
        """Get RetroPie client instance."""
        return self._get_or_create(
            "retropie_client",
            lambda: SSHRetroPieClient(self.ssh_handler),
        )

    @property
    def system_repository(self) -> SystemRepository:
        """Get system repository instance."""
        self._ensure_discovery()
        return self._get_or_create(
            "system_repository",
            lambda: SSHSystemRepository(self.retropie_client, self.config),
        )

    @property
    def controller_repository(self) -> ControllerRepository:
        """Get controller repository instance."""
        self._ensure_discovery()
        return self._get_or_create(
            "controller_repository",
            lambda: SSHControllerRepository(self.retropie_client),
        )

    @property
    def emulator_repository(self) -> EmulatorRepository:
        """Get emulator repository instance."""
        self._ensure_discovery()
        return self._get_or_create(
            "emulator_repository",
            lambda: SSHEmulatorRepository(self.retropie_client, self.config),
        )

    @property
    def state_repository(self) -> StateRepository:
        """Get state repository instance."""
        self._ensure_discovery()
        return self._get_or_create(
            "state_repository",
            lambda: SSHStateRepository(self.retropie_client, self.config),
        )

    # Use cases

    @property
    def test_connection_use_case(self) -> TestConnectionUseCase:
        """Get test connection use case."""
        return self._get_or_create(
            "test_connection_use_case",
            lambda: TestConnectionUseCase(self.retropie_client),
        )

    @property
    def get_system_info_use_case(self) -> GetSystemInfoUseCase:
        """Get system info use case."""
        return self._get_or_create(
            "get_system_info_use_case",
            lambda: GetSystemInfoUseCase(self.system_repository),
        )

    @property
    def install_packages_use_case(self) -> InstallPackagesUseCase:
        """Get install packages use case."""
        return self._get_or_create(
            "install_packages_use_case",
            lambda: InstallPackagesUseCase(self.system_repository),
        )

    @property
    def update_system_use_case(self) -> UpdateSystemUseCase:
        """Get update system use case."""
        return self._get_or_create(
            "update_system_use_case",
            lambda: UpdateSystemUseCase(self.system_repository),
        )

    @property
    def detect_controllers_use_case(self) -> DetectControllersUseCase:
        """Get detect controllers use case."""
        return self._get_or_create(
            "detect_controllers_use_case",
            lambda: DetectControllersUseCase(self.controller_repository),
        )

    @property
    def setup_controller_use_case(self) -> SetupControllerUseCase:
        """Get setup controller use case."""
        return self._get_or_create(
            "setup_controller_use_case",
            lambda: SetupControllerUseCase(self.controller_repository),
        )

    @property
    def install_emulator_use_case(self) -> InstallEmulatorUseCase:
        """Get install emulator use case."""
        return self._get_or_create(
            "install_emulator_use_case",
            lambda: InstallEmulatorUseCase(self.emulator_repository),
        )

    @property
    def list_roms_use_case(self) -> ListRomsUseCase:
        """Get list ROMs use case."""
        return self._get_or_create(
            "list_roms_use_case",
            lambda: ListRomsUseCase(self.emulator_repository),
        )

    @property
    def execute_command_use_case(self) -> ExecuteCommandUseCase:
        """Get execute command use case."""
        return self._get_or_create(
            "execute_command_use_case",
            lambda: ExecuteCommandUseCase(self.retropie_client),
        )

    @property
    def write_file_use_case(self) -> WriteFileUseCase:
        """Get write file use case."""
        return self._get_or_create(
            "write_file_use_case",
            lambda: WriteFileUseCase(self.retropie_client),
        )

    @property
    def manage_state_use_case(self) -> ManageStateUseCase:
        """Get manage state use case."""
        return self._get_or_create(
            "manage_state_use_case",
            lambda: ManageStateUseCase(
                self.state_repository,
                self.system_repository,
                self.emulator_repository,
                self.controller_repository,
            ),
        )

    def connect(self) -> bool:
        """Establish connection to RetroPie."""
        return self.retropie_client.connect()

    def disconnect(self) -> None:
        """Close all connections."""
        if "retropie_client" in self._instances:
            self.retropie_client.disconnect()
