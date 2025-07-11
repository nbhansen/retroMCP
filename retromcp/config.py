"""Configuration objects for RetroMCP server."""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class RetroPieConfig:
    """Immutable configuration for RetroPie SSH connection."""

    host: str
    username: str
    password: Optional[str] = None
    key_path: Optional[str] = None
    port: int = 22

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


@dataclass(frozen=True)
class ServerConfig:
    """Immutable configuration for MCP server."""

    name: str = "RetroMCP"
    version: str = "1.0.0"
    description: str = "Model Context Protocol server for RetroPie control"
