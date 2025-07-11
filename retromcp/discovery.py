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

        # Discover RetroPie directories
        retropie_dir = self._discover_retropie_directory(home_dir)
        retropie_setup_dir = self._discover_retropie_setup_directory(home_dir)
        bios_dir = self._discover_bios_directory(retropie_dir)
        roms_dir = self._discover_roms_directory(retropie_dir)

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

        # Fallback: try to get from whoami
        result = self._client.execute_command("eval echo ~$(whoami)")
        if result.success and result.stdout.strip():
            home_dir = result.stdout.strip()
            logger.debug(f"Discovered home directory (fallback): {home_dir}")
            return home_dir

        # Last resort fallback
        logger.warning("Could not discover home directory, using /home/pi")
        return "/home/pi"

    def _discover_username(self) -> str:
        """Discover current username."""
        result = self._client.execute_command("whoami")
        if result.success and result.stdout.strip():
            username = result.stdout.strip()
            logger.debug(f"Discovered username: {username}")
            return username

        # Fallback
        logger.warning("Could not discover username, using pi")
        return "pi"

    def _discover_retropie_directory(self, home_dir: str) -> Optional[str]:
        """Discover RetroPie directory location."""
        # Check standard location first
        standard_path = f"{home_dir}/RetroPie"
        result = self._client.execute_command(f"test -d '{standard_path}' && echo 'exists'")
        if result.success and "exists" in result.stdout:
            logger.debug(f"Found RetroPie directory: {standard_path}")
            return standard_path

        # Search in home directory
        result = self._client.execute_command(
            f"find '{home_dir}' -maxdepth 2 -name 'RetroPie' -type d 2>/dev/null | head -1"
        )
        if result.success and result.stdout.strip():
            retropie_dir = result.stdout.strip()
            logger.debug(f"Found RetroPie directory: {retropie_dir}")
            return retropie_dir

        # Search system-wide (last resort)
        result = self._client.execute_command(
            "find /home -name 'RetroPie' -type d 2>/dev/null | head -1"
        )
        if result.success and result.stdout.strip():
            retropie_dir = result.stdout.strip()
            logger.debug(f"Found RetroPie directory (system-wide): {retropie_dir}")
            return retropie_dir

        logger.warning("Could not find RetroPie directory")
        return None

    def _discover_retropie_setup_directory(self, home_dir: str) -> Optional[str]:
        """Discover RetroPie-Setup directory location."""
        # Check standard location first
        standard_path = f"{home_dir}/RetroPie-Setup"
        result = self._client.execute_command(f"test -d '{standard_path}' && echo 'exists'")
        if result.success and "exists" in result.stdout:
            logger.debug(f"Found RetroPie-Setup directory: {standard_path}")
            return standard_path

        # Search in home directory
        result = self._client.execute_command(
            f"find '{home_dir}' -maxdepth 2 -name 'RetroPie-Setup' -type d 2>/dev/null | head -1"
        )
        if result.success and result.stdout.strip():
            setup_dir = result.stdout.strip()
            logger.debug(f"Found RetroPie-Setup directory: {setup_dir}")
            return setup_dir

        # Search system-wide (last resort)
        result = self._client.execute_command(
            "find /home -name 'RetroPie-Setup' -type d 2>/dev/null | head -1"
        )
        if result.success and result.stdout.strip():
            setup_dir = result.stdout.strip()
            logger.debug(f"Found RetroPie-Setup directory (system-wide): {setup_dir}")
            return setup_dir

        logger.warning("Could not find RetroPie-Setup directory")
        return None

    def _discover_bios_directory(self, retropie_dir: Optional[str]) -> Optional[str]:
        """Discover BIOS directory location."""
        if retropie_dir:
            # Check in RetroPie directory
            bios_path = f"{retropie_dir}/BIOS"
            result = self._client.execute_command(f"test -d '{bios_path}' && echo 'exists'")
            if result.success and "exists" in result.stdout:
                logger.debug(f"Found BIOS directory: {bios_path}")
                return bios_path

        # Check standard system location
        result = self._client.execute_command(
            "find /home -name 'BIOS' -path '*/RetroPie/BIOS' -type d 2>/dev/null | head -1"
        )
        if result.success and result.stdout.strip():
            bios_dir = result.stdout.strip()
            logger.debug(f"Found BIOS directory: {bios_dir}")
            return bios_dir

        logger.warning("Could not find BIOS directory")
        return None

    def _discover_roms_directory(self, retropie_dir: Optional[str]) -> Optional[str]:
        """Discover ROMs directory location."""
        if retropie_dir:
            # Check in RetroPie directory
            roms_path = f"{retropie_dir}/roms"
            result = self._client.execute_command(f"test -d '{roms_path}' && echo 'exists'")
            if result.success and "exists" in result.stdout:
                logger.debug(f"Found ROMs directory: {roms_path}")
                return roms_path

        # Check standard system location
        result = self._client.execute_command(
            "find /home -name 'roms' -path '*/RetroPie/roms' -type d 2>/dev/null | head -1"
        )
        if result.success and result.stdout.strip():
            roms_dir = result.stdout.strip()
            logger.debug(f"Found ROMs directory: {roms_dir}")
            return roms_dir

        logger.warning("Could not find ROMs directory")
        return None
