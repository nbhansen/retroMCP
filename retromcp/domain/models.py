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
    vendor_id: str
    product_id: str
    controller_type: ControllerType
    is_configured: bool
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

    def to_json(self) -> str:
        """Convert state to JSON string."""
        return json.dumps({
            "schema_version": self.schema_version,
            "last_updated": self.last_updated,
            "system": self.system,
            "emulators": self.emulators,
            "controllers": self.controllers,
            "roms": self.roms,
            "custom_configs": self.custom_configs,
            "known_issues": self.known_issues
        }, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "SystemState":
        """Create SystemState from JSON string."""
        data = json.loads(json_str)
        return cls(
            schema_version=data["schema_version"],
            last_updated=data["last_updated"],
            system=data["system"],
            emulators=data["emulators"],
            controllers=data["controllers"],
            roms=data["roms"],
            custom_configs=data["custom_configs"],
            known_issues=data["known_issues"]
        )


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
