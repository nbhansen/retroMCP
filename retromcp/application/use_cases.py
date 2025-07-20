"""Application use cases for RetroMCP - consolidated imports."""

# Import all use cases from their domain-specific modules
from .docker_use_cases import ManageDockerUseCase
from .gaming_use_cases import DetectControllersUseCase
from .gaming_use_cases import InstallEmulatorUseCase
from .gaming_use_cases import ListRomsUseCase
from .gaming_use_cases import SetupControllerUseCase
from .package_use_cases import InstallPackagesUseCase
from .state_use_cases import ManageStateUseCase
from .system_use_cases import CheckConnectionUseCase
from .system_use_cases import ExecuteCommandUseCase
from .system_use_cases import GetSystemInfoUseCase
from .system_use_cases import UpdateSystemUseCase
from .system_use_cases import WriteFileUseCase

# Export all use cases for backward compatibility
__all__ = [
    "CheckConnectionUseCase",
    "DetectControllersUseCase",
    "ExecuteCommandUseCase",
    "GetSystemInfoUseCase",
    "InstallEmulatorUseCase",
    "InstallPackagesUseCase",
    "ListRomsUseCase",
    "ManageDockerUseCase",
    "ManageStateUseCase",
    "SetupControllerUseCase",
    "UpdateSystemUseCase",
    "WriteFileUseCase",
]
