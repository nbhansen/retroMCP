"""Domain models for RetroMCP."""

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any
from typing import Dict
from typing import List
from typing import Optional


class ControllerType(Enum):
    """Supported controller types."""

    XBOX = "xbox"
    PS4 = "ps4"
    PS5 = "ps5"
    NINTENDO_PRO = "nintendo_pro"
    EIGHT_BIT_DO = "8bitdo"
    GENERIC = "generic"
    UNKNOWN = "unknown"


class EmulatorStatus(Enum):
    """Emulator installation status."""

    INSTALLED = "installed"
    AVAILABLE = "available"
    NOT_AVAILABLE = "not_available"
    UNKNOWN = "unknown"


class ServiceStatus(Enum):
    """System service status."""

    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"
    UNKNOWN = "unknown"


class NetworkStatus(Enum):
    """Network interface status."""

    UP = "up"
    DOWN = "down"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class SystemInfo:
    """System information model."""

    hostname: str
    cpu_temperature: float
    memory_total: int
    memory_used: int
    memory_free: int
    disk_total: int
    disk_used: int
    disk_free: int
    load_average: List[float]
    uptime: int


@dataclass(frozen=True)
class Controller:
    """Controller model."""

    name: str
    device_path: str
    controller_type: ControllerType
    connected: bool
    vendor_id: str = ""
    product_id: str = ""
    is_configured: bool = False
    driver_required: Optional[str] = None


@dataclass(frozen=True)
class Emulator:
    """Emulator model."""

    name: str
    system: str
    status: EmulatorStatus
    version: Optional[str] = None
    config_path: Optional[str] = None
    bios_required: List[str] = None


@dataclass(frozen=True)
class BiosFile:
    """BIOS file model."""

    name: str
    path: str
    system: str
    required: bool
    present: bool
    size: Optional[int] = None
    checksum: Optional[str] = None


@dataclass(frozen=True)
class SystemService:
    """System service model."""

    name: str
    status: ServiceStatus
    enabled: bool
    description: Optional[str] = None


@dataclass(frozen=True)
class Package:
    """System package model."""

    name: str
    version: str
    installed: bool
    available_version: Optional[str] = None
    description: Optional[str] = None


@dataclass(frozen=True)
class GameList:
    """Game list model."""

    system: str
    path: str
    game_count: int
    last_modified: Optional[str] = None


@dataclass(frozen=True)
class RomDirectory:
    """ROM directory model."""

    system: str
    path: str
    rom_count: int
    total_size: int
    supported_extensions: List[str]


@dataclass(frozen=True)
class ConfigFile:
    """Configuration file model."""

    name: str
    path: str
    system: str
    content: str
    backup_path: Optional[str] = None


@dataclass(frozen=True)
class Theme:
    """EmulationStation theme model."""

    name: str
    path: str
    active: bool
    description: Optional[str] = None


@dataclass(frozen=True)
class CommandResult:
    """Command execution result."""

    command: str
    exit_code: int
    stdout: str
    stderr: str
    success: bool
    execution_time: float


@dataclass(frozen=True)
class ConnectionInfo:
    """SSH connection information."""

    host: str
    port: int
    username: str
    connected: bool
    last_connected: Optional[str] = None
    connection_method: str = "ssh"


@dataclass(frozen=True)
class ExecuteCommandRequest:
    """Command execution request model."""

    command: str
    use_sudo: bool = False
    working_directory: Optional[str] = None
    timeout: Optional[int] = None


@dataclass(frozen=True)
class WriteFileRequest:
    """File write request model."""

    path: str
    content: str
    mode: Optional[str] = None
    backup: bool = False
    create_directories: bool = False


class StateAction(Enum):
    """State management actions."""

    LOAD = "load"
    SAVE = "save"
    UPDATE = "update"
    COMPARE = "compare"
    EXPORT = "export"
    IMPORT = "import"
    DIFF = "diff"
    WATCH = "watch"


@dataclass(frozen=True)
class SystemState:
    """System state model for persistent storage."""

    schema_version: str
    last_updated: str
    system: Dict[str, Any]
    emulators: Dict[str, Any]
    controllers: List[Dict[str, Any]]
    roms: Dict[str, Any]
    custom_configs: List[str]
    known_issues: List[str]
    # v2.0 schema extensions (optional for backward compatibility)
    hardware: Optional["HardwareInfo"] = None
    network: Optional[List["NetworkInterface"]] = None
    software: Optional["SoftwareInfo"] = None
    services: Optional[List["SystemService"]] = None
    notes: Optional[List["SystemNote"]] = None

    def to_json(self) -> str:
        """Convert state to JSON string."""
        data = {
            "schema_version": self.schema_version,
            "last_updated": self.last_updated,
            "system": self.system,
            "emulators": self.emulators,
            "controllers": self.controllers,
            "roms": self.roms,
            "custom_configs": self.custom_configs,
            "known_issues": self.known_issues,
        }

        # Add v2.0 fields if present
        if self.hardware is not None:
            data["hardware"] = self._hardware_to_dict(self.hardware)
        if self.network is not None:
            data["network"] = [self._network_interface_to_dict(ni) for ni in self.network]
        if self.software is not None:
            data["software"] = self._software_to_dict(self.software)
        if self.services is not None:
            data["services"] = [self._service_to_dict(s) for s in self.services]
        if self.notes is not None:
            data["notes"] = [self._note_to_dict(n) for n in self.notes]

        return json.dumps(data, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "SystemState":
        """Create SystemState from JSON string."""
        data = json.loads(json_str)

        # Handle v2.0 fields if present
        hardware = None
        if "hardware" in data:
            hardware = cls._dict_to_hardware(data["hardware"])

        network = None
        if "network" in data:
            network = [cls._dict_to_network_interface(ni) for ni in data["network"]]

        software = None
        if "software" in data:
            software = cls._dict_to_software(data["software"])

        services = None
        if "services" in data:
            services = [cls._dict_to_service(s) for s in data["services"]]

        notes = None
        if "notes" in data:
            notes = [cls._dict_to_note(n) for n in data["notes"]]

        return cls(
            schema_version=data["schema_version"],
            last_updated=data["last_updated"],
            system=data["system"],
            emulators=data["emulators"],
            controllers=data["controllers"],
            roms=data["roms"],
            custom_configs=data["custom_configs"],
            known_issues=data["known_issues"],
            hardware=hardware,
            network=network,
            software=software,
            services=services,
            notes=notes,
        )

    def _hardware_to_dict(self, hardware: "HardwareInfo") -> Dict[str, Any]:
        """Convert HardwareInfo to dictionary."""
        return {
            "model": hardware.model,
            "revision": hardware.revision,
            "cpu_temperature": hardware.cpu_temperature,
            "memory_total": hardware.memory_total,
            "memory_used": hardware.memory_used,
            "storage": [
                {
                    "device": s.device,
                    "mount": s.mount,
                    "size": s.size,
                    "used": s.used,
                    "filesystem_type": s.filesystem_type,
                }
                for s in hardware.storage
            ],
            "gpio_usage": hardware.gpio_usage,
            "cooling_active": hardware.cooling_active,
            "case_type": hardware.case_type,
            "fan_speed": hardware.fan_speed,
        }

    def _network_interface_to_dict(self, interface: "NetworkInterface") -> Dict[str, Any]:
        """Convert NetworkInterface to dictionary."""
        return {
            "name": interface.name,
            "ip": interface.ip,
            "status": interface.status.value,
            "speed": interface.speed,
            "ssid": interface.ssid,
            "signal_strength": interface.signal_strength,
        }

    def _software_to_dict(self, software: "SoftwareInfo") -> Dict[str, Any]:
        """Convert SoftwareInfo to dictionary."""
        return {
            "os_name": software.os_name,
            "os_version": software.os_version,
            "kernel": software.kernel,
            "python_version": software.python_version,
            "python_path": software.python_path,
            "docker_version": software.docker_version,
            "docker_status": software.docker_status.value,
            "retropie_version": software.retropie_version,
            "retropie_status": software.retropie_status.value,
        }

    def _service_to_dict(self, service: "SystemService") -> Dict[str, Any]:
        """Convert SystemService to dictionary."""
        return {
            "name": service.name,
            "status": service.status.value,
            "enabled": service.enabled,
            "description": service.description,
        }

    def _note_to_dict(self, note: "SystemNote") -> Dict[str, Any]:
        """Convert SystemNote to dictionary."""
        return {
            "date": note.date,
            "action": note.action,
            "description": note.description,
            "user": note.user,
        }

    @classmethod
    def _dict_to_hardware(cls, data: Dict[str, Any]) -> "HardwareInfo":
        """Convert dictionary to HardwareInfo."""
        storage = [
            StorageDevice(
                device=s["device"],
                mount=s["mount"],
                size=s["size"],
                used=s["used"],
                filesystem_type=s["filesystem_type"],
            )
            for s in data["storage"]
        ]
        return HardwareInfo(
            model=data["model"],
            revision=data["revision"],
            cpu_temperature=data["cpu_temperature"],
            memory_total=data["memory_total"],
            memory_used=data["memory_used"],
            storage=storage,
            gpio_usage=data["gpio_usage"],
            cooling_active=data["cooling_active"],
            case_type=data["case_type"],
            fan_speed=data["fan_speed"],
        )

    @classmethod
    def _dict_to_network_interface(cls, data: Dict[str, Any]) -> "NetworkInterface":
        """Convert dictionary to NetworkInterface."""
        return NetworkInterface(
            name=data["name"],
            ip=data["ip"],
            status=NetworkStatus(data["status"]),
            speed=data["speed"],
            ssid=data.get("ssid"),
            signal_strength=data.get("signal_strength"),
        )

    @classmethod
    def _dict_to_software(cls, data: Dict[str, Any]) -> "SoftwareInfo":
        """Convert dictionary to SoftwareInfo."""
        return SoftwareInfo(
            os_name=data["os_name"],
            os_version=data["os_version"],
            kernel=data["kernel"],
            python_version=data["python_version"],
            python_path=data["python_path"],
            docker_version=data["docker_version"],
            docker_status=ServiceStatus(data["docker_status"]),
            retropie_version=data["retropie_version"],
            retropie_status=ServiceStatus(data["retropie_status"]),
        )

    @classmethod
    def _dict_to_service(cls, data: Dict[str, Any]) -> "SystemService":
        """Convert dictionary to SystemService."""
        return SystemService(
            name=data["name"],
            status=ServiceStatus(data["status"]),
            enabled=data["enabled"],
            description=data["description"],
        )

    @classmethod
    def _dict_to_note(cls, data: Dict[str, Any]) -> "SystemNote":
        """Convert dictionary to SystemNote."""
        return SystemNote(
            date=data["date"],
            action=data["action"],
            description=data["description"],
            user=data["user"],
        )

    def migrate_to_v2(self) -> "SystemState":
        """Migrate state to v2.0 schema.

        Returns:
            SystemState with v2.0 schema.

        Raises:
            ValueError: If schema version is not supported.
        """
        if self.schema_version == "2.0":
            # Already v2.0, return self
            return self
        elif self.schema_version == "1.0":
            # Migrate from v1.0 to v2.0
            return SystemState(
                schema_version="2.0",
                last_updated=self.last_updated,
                system=self.system,
                emulators=self.emulators,
                controllers=self.controllers,
                roms=self.roms,
                custom_configs=self.custom_configs,
                known_issues=self.known_issues,
                hardware=None,
                network=None,
                software=None,
                services=None,
                notes=None,
            )
        else:
            raise ValueError(f"Unsupported schema version: {self.schema_version}")

    @classmethod
    def ensure_v2_schema(cls, state: "SystemState") -> "SystemState":
        """Ensure state uses v2.0 schema, migrating if necessary.

        Args:
            state: SystemState to check and potentially migrate.

        Returns:
            SystemState with v2.0 schema.
        """
        return state.migrate_to_v2()


@dataclass(frozen=True)
class StateManagementRequest:
    """State management request model."""

    action: StateAction
    path: Optional[str] = None
    value: Optional[Any] = None
    force_scan: bool = False


@dataclass(frozen=True)
class StateManagementResult:
    """State management operation result."""

    success: bool
    action: StateAction
    message: str
    state: Optional[SystemState] = None
    diff: Optional[Dict[str, Any]] = None
    exported_data: Optional[str] = None
    watch_value: Optional[Any] = None


class DockerResource(Enum):
    """Docker resource types."""

    CONTAINER = "container"
    COMPOSE = "compose"
    VOLUME = "volume"


class DockerAction(Enum):
    """Docker management actions."""

    # Container actions
    PULL = "pull"
    RUN = "run"
    PS = "ps"
    STOP = "stop"
    START = "start"
    RESTART = "restart"
    REMOVE = "remove"
    LOGS = "logs"
    INSPECT = "inspect"
    # Compose actions
    UP = "up"
    DOWN = "down"
    # Volume actions
    CREATE = "create"
    LIST = "list"


@dataclass(frozen=True)
class DockerContainer:
    """Docker container model."""

    container_id: str
    name: str
    image: str
    status: str
    created: str
    ports: Dict[str, str]
    command: str


@dataclass(frozen=True)
class DockerVolume:
    """Docker volume model."""

    name: str
    driver: str
    mountpoint: str
    created: str
    labels: Dict[str, str]


@dataclass(frozen=True)
class DockerManagementRequest:
    """Docker management request model."""

    resource: DockerResource
    action: DockerAction
    name: Optional[str] = None
    image: Optional[str] = None
    command: Optional[str] = None
    ports: Optional[Dict[str, str]] = None
    environment: Optional[Dict[str, str]] = None
    volumes: Optional[Dict[str, str]] = None
    detach: bool = True
    remove_on_exit: bool = False
    compose_file: Optional[str] = None
    service: Optional[str] = None
    follow_logs: bool = False
    tail_lines: Optional[int] = None


@dataclass(frozen=True)
class DockerManagementResult:
    """Docker management operation result."""

    success: bool
    resource: DockerResource
    action: DockerAction
    message: str
    containers: Optional[List[DockerContainer]] = None
    volumes: Optional[List[DockerVolume]] = None
    output: Optional[str] = None
    inspect_data: Optional[Dict[str, Any]] = None


# V2.0 State Management Models


@dataclass(frozen=True)
class StorageDevice:
    """Storage device model for v2.0 schema."""

    device: str
    mount: str
    size: str
    used: str
    filesystem_type: str


@dataclass(frozen=True)
class HardwareInfo:
    """Hardware information model for v2.0 schema."""

    model: str
    revision: str
    cpu_temperature: float
    memory_total: str
    memory_used: str
    storage: List[StorageDevice]
    gpio_usage: Dict[str, str]
    cooling_active: bool
    case_type: str
    fan_speed: int


@dataclass(frozen=True)
class NetworkInterface:
    """Network interface model for v2.0 schema."""

    name: str
    ip: str
    status: NetworkStatus
    speed: str
    ssid: Optional[str] = None
    signal_strength: Optional[int] = None


@dataclass(frozen=True)
class SoftwareInfo:
    """Software information model for v2.0 schema."""

    os_name: str
    os_version: str
    kernel: str
    python_version: str
    python_path: str
    docker_version: str
    docker_status: ServiceStatus
    retropie_version: str
    retropie_status: ServiceStatus




@dataclass(frozen=True)
class SystemNote:
    """System note model for v2.0 schema."""

    date: str
    action: str
    description: str
    user: str
