"""RetroPie system discovery utilities."""

import logging
from dataclasses import dataclass
from typing import Optional

from .domain.ports import RetroPieClient

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RetroPiePaths:
    """Discovered RetroPie system paths."""

    home_dir: str
    username: str
    retropie_dir: Optional[str] = None
    retropie_setup_dir: Optional[str] = None
    bios_dir: Optional[str] = None
    roms_dir: Optional[str] = None
    configs_dir: str = "/opt/retropie/configs"
    emulators_dir: str = "/opt/retropie/emulators"


class RetroPieDiscovery:
    """Discovers RetroPie system configuration and paths."""

    def __init__(self, client: RetroPieClient) -> None:
        """Initialize with RetroPie client."""
        self._client = client

    def discover_system_paths(self) -> RetroPiePaths:
        """Discover all RetroPie system paths and configuration."""
        logger.info("Starting RetroPie system discovery")

        # Get basic user info
        home_dir = self._discover_home_directory()
        username = self._discover_username()

        # Discover RetroPie directories using simple directory checks
        retropie_dir = self._check_directory(f"{home_dir}/RetroPie")
        retropie_setup_dir = self._check_directory(f"{home_dir}/RetroPie-Setup")
        bios_dir = self._check_directory(f"{home_dir}/RetroPie/BIOS")
        roms_dir = self._check_directory(f"{home_dir}/RetroPie/roms")

        paths = RetroPiePaths(
            home_dir=home_dir,
            username=username,
            retropie_dir=retropie_dir,
            retropie_setup_dir=retropie_setup_dir,
            bios_dir=bios_dir,
            roms_dir=roms_dir,
        )

        logger.info(f"Discovery complete: {paths}")
        return paths

    def _discover_home_directory(self) -> str:
        """Discover user's home directory."""
        result = self._client.execute_command("echo $HOME")
        if result.success and result.stdout.strip():
            home_dir = result.stdout.strip()
            logger.debug(f"Discovered home directory: {home_dir}")
            return home_dir

        # Fallback
        logger.warning("Could not discover home directory, using unknown")
        return "unknown"

    def _discover_username(self) -> str:
        """Discover current username."""
        result = self._client.execute_command("whoami")
        if result.success:
            username = result.stdout.strip()
            logger.debug(f"Discovered username: {username}")
            return username

        # Fallback
        logger.warning("Could not discover username, using unknown")
        return "unknown"

    def _check_directory(self, path: str) -> Optional[str]:
        """Check if a directory exists and return the path if it does."""
        result = self._client.execute_command(f"test -d {path}")
        if result.success:
            logger.debug(f"Found directory: {path}")
            return path
        else:
            logger.debug(f"Directory not found: {path}")
            return None
