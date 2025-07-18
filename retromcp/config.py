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

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        self._validate_security_requirements(self.username, self.password, self.key_path)

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

        # Security validation
        cls._validate_security_requirements(username, password, key_path)

        return cls(
            host=host,
            username=username,
            password=password,
            key_path=key_path,
            port=port,
        )

    @classmethod
    def _validate_security_requirements(
        cls, username: str, password: Optional[str], key_path: Optional[str]
    ) -> None:
        """Validate security requirements for SSH connection."""
        # Block root user
        if username.lower() in {"root", "admin", "administrator"}:
            raise ValueError(
                f"Username '{username}' is not allowed for security reasons. "
                "Use a non-privileged user account instead."
            )

        # Require either key-based auth or password (prefer keys)
        if not key_path and not password:
            raise ValueError(
                "Either RETROPIE_KEY_PATH or RETROPIE_PASSWORD must be set for authentication. "
                "SSH key authentication is recommended for better security."
            )

        # Warn about password authentication
        if password and not key_path:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                "Using password authentication. SSH key authentication is more secure."
            )

    def with_paths(self, paths: RetroPiePaths) -> "RetroPieConfig":
        """Create new config with discovered paths."""
        return replace(self, paths=paths)

    def validate_security(self) -> None:
        """Validate configuration meets security requirements.
        
        Raises:
            ValueError: If configuration is insecure
        """
        self._validate_security_requirements(self.username, self.password, self.key_path)

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
