"""Dependency injection container for RetroMCP."""

from typing import Any
from typing import Dict

from .application.use_cases import DetectControllersUseCase
from .application.use_cases import GetSystemInfoUseCase
from .application.use_cases import InstallEmulatorUseCase
from .application.use_cases import InstallPackagesUseCase
from .application.use_cases import SetupControllerUseCase
from .application.use_cases import TestConnectionUseCase
from .application.use_cases import UpdateSystemUseCase
from .config import RetroPieConfig
from .domain.ports import ControllerRepository
from .domain.ports import EmulatorRepository
from .domain.ports import RetroPieClient
from .domain.ports import SystemRepository
from .infrastructure import SSHControllerRepository
from .infrastructure import SSHEmulatorRepository
from .infrastructure import SSHRetroPieClient
from .infrastructure import SSHSystemRepository
from .ssh_handler import RetroPieSSH


class Container:
    """Dependency injection container."""

    def __init__(self, config: RetroPieConfig) -> None:
        """Initialize container with configuration."""
        self.config = config
        self._instances: Dict[str, Any] = {}

    def _get_or_create(self, key: str, factory: Any) -> Any:
        """Get existing instance or create new one."""
        if key not in self._instances:
            self._instances[key] = factory()
        return self._instances[key]

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
        return self._get_or_create(
            "system_repository",
            lambda: SSHSystemRepository(self.retropie_client),
        )

    @property
    def controller_repository(self) -> ControllerRepository:
        """Get controller repository instance."""
        return self._get_or_create(
            "controller_repository",
            lambda: SSHControllerRepository(self.retropie_client),
        )

    @property
    def emulator_repository(self) -> EmulatorRepository:
        """Get emulator repository instance."""
        return self._get_or_create(
            "emulator_repository",
            lambda: SSHEmulatorRepository(self.retropie_client),
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

    def connect(self) -> bool:
        """Establish connection to RetroPie."""
        return self.retropie_client.connect()

    def disconnect(self) -> None:
        """Close all connections."""
        if "retropie_client" in self._instances:
            self.retropie_client.disconnect()
