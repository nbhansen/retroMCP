"""Configuration objects for RetroMCP server."""

import os
from dataclasses import dataclass
from dataclasses import replace
from typing import Optional

from .discovery import RetroPiePaths


@dataclass(frozen=True)
class RetroPieConfig:
    """Immutable configuration for RetroPie SSH connection."""

    host: str
    username: str
    password: Optional[str] = None
    key_path: Optional[str] = None
    port: int = 22

    # Discovered paths (populated after connection)
    paths: Optional[RetroPiePaths] = None

    @classmethod
    def from_env(cls) -> "RetroPieConfig":
        """Create configuration from environment variables."""
        host = os.getenv("RETROPIE_HOST")
        username = os.getenv("RETROPIE_USERNAME")
        password = os.getenv("RETROPIE_PASSWORD")
        key_path = os.getenv("RETROPIE_KEY_PATH")
        port = int(os.getenv("RETROPIE_PORT", "22"))

        if not host or not username:
            msg = "RETROPIE_HOST and RETROPIE_USERNAME must be set"
            raise ValueError(msg)

        return cls(
            host=host,
            username=username,
            password=password,
            key_path=key_path,
            port=port,
        )

    def with_paths(self, paths: RetroPiePaths) -> "RetroPieConfig":
        """Create new config with discovered paths."""
        return replace(self, paths=paths)

    @property
    def home_dir(self) -> str:
        """Get home directory path."""
        return self.paths.home_dir if self.paths else f"/home/{self.username}"

    @property
    def retropie_dir(self) -> Optional[str]:
        """Get RetroPie directory path."""
        return self.paths.retropie_dir if self.paths else None

    @property
    def retropie_setup_dir(self) -> Optional[str]:
        """Get RetroPie-Setup directory path."""
        return self.paths.retropie_setup_dir if self.paths else None

    @property
    def bios_dir(self) -> Optional[str]:
        """Get BIOS directory path."""
        return self.paths.bios_dir if self.paths else None

    @property
    def roms_dir(self) -> Optional[str]:
        """Get ROMs directory path."""
        return self.paths.roms_dir if self.paths else None

    @property
    def configs_dir(self) -> str:
        """Get configs directory path."""
        return self.paths.configs_dir if self.paths else "/opt/retropie/configs"

    @property
    def emulators_dir(self) -> str:
        """Get emulators directory path."""
        return self.paths.emulators_dir if self.paths else "/opt/retropie/emulators"


@dataclass(frozen=True)
class ServerConfig:
    """Immutable configuration for MCP server."""

    name: str = "RetroMCP"
    version: str = "1.0.0"
    description: str = "Model Context Protocol server for RetroPie control"
