"""Domain models for RetroMCP."""

from dataclasses import dataclass
from enum import Enum
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
