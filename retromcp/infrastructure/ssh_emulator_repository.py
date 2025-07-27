"""SSH implementation of emulator repository."""

import re
from typing import List
from typing import Optional

from ..config import RetroPieConfig
from ..domain.models import CommandResult
from ..domain.models import ConfigFile
from ..domain.models import Emulator
from ..domain.models import EmulatorStatus
from ..domain.models import ESSystemsConfig
from ..domain.models import RomDirectory
from ..domain.models import Theme
from ..domain.ports import ConfigurationParser
from ..domain.ports import EmulatorRepository
from ..domain.ports import RetroPieClient
from .es_systems_parser import ESSystemsConfigParser


class SSHEmulatorRepository(EmulatorRepository):
    """SSH implementation of emulator repository interface."""

    def __init__(
        self,
        client: RetroPieClient,
        config: RetroPieConfig,
        config_parser: Optional[ConfigurationParser] = None
    ) -> None:
        """Initialize with RetroPie client and configuration.

        Args:
            client: RetroPie SSH client
            config: RetroPie configuration
            config_parser: Optional configuration parser (defaults to ESSystemsConfigParser)
        """
        self._client = client
        self._config = config
        self._config_parser = config_parser or ESSystemsConfigParser()
        self._cached_es_config: Optional[ESSystemsConfig] = None

    def get_emulators(self) -> List[Emulator]:
        """Get list of available emulators."""
        emulators = []

        # Check installed emulators in /opt/retropie/emulators
        installed_result = self._client.execute_command(
            "ls -la /opt/retropie/emulators/ 2>/dev/null"
        )
        installed_emulators = set()

        if installed_result.success:
            for line in installed_result.stdout.strip().split("\n"):
                if line.startswith("d") and not line.endswith("."):
                    parts = line.split()
                    if len(parts) >= 9:
                        emulator_name = parts[-1]
                        installed_emulators.add(emulator_name)

        # Define known emulator mappings
        emulator_systems = {
            "retroarch": ["arcade", "nes", "snes", "genesis", "psx", "n64"],
            "mupen64plus": ["n64"],
            "pcsx-rearmed": ["psx"],
            "ppsspp": ["psp"],
            "reicast": ["dreamcast"],
            "dolphin": ["gamecube", "wii"],
            "vice": ["c64"],
            "dosbox": ["dos", "pc"],
            "scummvm": ["scummvm"],
            "mame": ["arcade", "mame"],
            "fba": ["arcade", "neogeo", "cps"],
        }

        # Get available emulators from RetroPie-Setup
        retropie_setup_dir = (
            self._config.retropie_setup_dir or f"{self._config.home_dir}/RetroPie-Setup"
        )
        available_result = self._client.execute_command(
            f"ls -la {retropie_setup_dir}/scriptmodules/emulators/ 2>/dev/null | grep '.sh$'"
        )
        available_emulators = set()

        if available_result.success:
            for line in available_result.stdout.strip().split("\n"):
                if ".sh" in line:
                    parts = line.split()
                    if len(parts) >= 9:
                        script_name = parts[-1].replace(".sh", "")
                        available_emulators.add(script_name)

        # Build emulator list
        all_emulators = installed_emulators.union(available_emulators)

        for emulator_name in all_emulators:
            # Determine status
            if emulator_name in installed_emulators:
                status = EmulatorStatus.INSTALLED
            elif emulator_name in available_emulators:
                status = EmulatorStatus.AVAILABLE
            else:
                status = EmulatorStatus.UNKNOWN

            # Get systems this emulator supports
            systems = emulator_systems.get(emulator_name, [emulator_name])

            # Get version if installed
            version = None
            if status == EmulatorStatus.INSTALLED:
                version_result = self._client.execute_command(
                    f"/opt/retropie/emulators/{emulator_name}/{emulator_name} --version 2>&1 | head -1"
                )
                if version_result.success and version_result.stdout:
                    version = version_result.stdout.strip()

            # Get config path
            config_path = None
            if status == EmulatorStatus.INSTALLED:
                config_path = (
                    f"/opt/retropie/configs/{systems[0] if systems else emulator_name}"
                )

            # Get BIOS requirements
            bios_required = []
            if emulator_name in ["pcsx-rearmed", "psx"]:
                bios_required = ["scph1001.bin", "scph5501.bin", "scph7001.bin"]
            elif emulator_name == "reicast":
                bios_required = ["dc_boot.bin", "dc_flash.bin"]
            elif emulator_name == "ppsspp":
                bios_required = []  # PSP doesn't require BIOS

            for system in systems:
                emulators.append(
                    Emulator(
                        name=emulator_name,
                        system=system,
                        status=status,
                        version=version,
                        config_path=config_path,
                        bios_required=bios_required,
                    )
                )

        return emulators

    def install_emulator(self, emulator_name: str) -> CommandResult:
        """Install an emulator."""
        # Use RetroPie-Setup to install the emulator
        retropie_setup_dir = (
            self._config.retropie_setup_dir or f"{self._config.home_dir}/RetroPie-Setup"
        )
        command = f"cd {retropie_setup_dir} && sudo ./retropie_packages.sh {emulator_name} install_bin"
        return self._client.execute_command(command, use_sudo=True)

    def get_rom_directories(self) -> List[RomDirectory]:
        """Get ROM directories information."""
        rom_dirs = []
        base_dir = self._config.roms_dir or f"{self._config.home_dir}/RetroPie/roms"

        # Get list of ROM directories
        result = self._client.execute_command(f"ls -la {base_dir} 2>/dev/null")

        if result.success:
            for line in result.stdout.strip().split("\n"):
                if line.startswith("d") and not line.endswith("."):
                    parts = line.split()
                    if len(parts) >= 9:
                        system = parts[-1]
                        system_path = f"{base_dir}/{system}"

                        # Count ROM files using system-specific extensions
                        find_command = self._build_find_command_for_system(
                            system_path, system
                        )
                        count_result = self._client.execute_command(find_command)
                        rom_count = (
                            int(count_result.stdout.strip())
                            if count_result.success
                            else 0
                        )

                        # Get total size
                        size_result = self._client.execute_command(
                            f"du -sb {system_path} 2>/dev/null | cut -f1"
                        )
                        total_size = (
                            int(size_result.stdout.strip())
                            if size_result.success
                            else 0
                        )

                        # Get supported extensions from es_systems.cfg
                        extensions = self._get_supported_extensions(system)

                        rom_dirs.append(
                            RomDirectory(
                                system=system,
                                path=system_path,
                                rom_count=rom_count,
                                total_size=total_size,
                                supported_extensions=extensions,
                            )
                        )

        return rom_dirs

    def get_config_files(self, system: str) -> List[ConfigFile]:
        """Get configuration files for a system."""
        config_files = []
        base_config_dir = f"/opt/retropie/configs/{system}"

        # Common config files to look for
        config_patterns = [
            "retroarch.cfg",
            "emulators.cfg",
            f"{system}.cfg",
            "advmame.rc",
            "config.ini",
        ]

        for pattern in config_patterns:
            path = f"{base_config_dir}/{pattern}"
            result = self._client.execute_command(f"cat {path} 2>/dev/null")

            if result.success:
                # Check for backup
                backup_result = self._client.execute_command(
                    f"ls -la {path}.backup 2>/dev/null"
                )
                backup_path = f"{path}.backup" if backup_result.success else None

                config_files.append(
                    ConfigFile(
                        name=pattern,
                        path=path,
                        system=system,
                        content=result.stdout,
                        backup_path=backup_path,
                    )
                )

        return config_files

    def update_config_file(self, config_file: ConfigFile) -> CommandResult:
        """Update a configuration file."""
        # Create backup if it doesn't exist
        if not config_file.backup_path:
            backup_command = f"cp {config_file.path} {config_file.path}.backup"
            self._client.execute_command(backup_command, use_sudo=True)

        # Write new content
        # Escape single quotes in content
        escaped_content = config_file.content.replace("'", "'\"'\"'")
        command = f"echo '{escaped_content}' > {config_file.path}"
        return self._client.execute_command(command, use_sudo=True)

    def get_themes(self) -> List[Theme]:
        """Get available themes."""
        themes = []
        theme_dir = "/etc/emulationstation/themes"

        # Get current theme
        current_theme = None
        theme_config_result = self._client.execute_command(
            "grep '<string name=\"ThemeSet\"' /opt/retropie/configs/all/emulationstation/es_settings.cfg 2>/dev/null"
        )
        if theme_config_result.success:
            match = re.search(r'value="([^"]+)"', theme_config_result.stdout)
            if match:
                current_theme = match.group(1)

        # List available themes
        result = self._client.execute_command(f"ls -la {theme_dir} 2>/dev/null")

        if result.success:
            for line in result.stdout.strip().split("\n"):
                if line.startswith("d") and not line.endswith("."):
                    parts = line.split()
                    if len(parts) >= 9:
                        theme_name = parts[-1]
                        theme_path = f"{theme_dir}/{theme_name}"

                        # Try to get theme description from theme.xml
                        desc_result = self._client.execute_command(
                            f"grep '<string name=\"description\"' {theme_path}/theme.xml 2>/dev/null | head -1"
                        )
                        description = None
                        if desc_result.success:
                            desc_match = re.search(r">([^<]+)<", desc_result.stdout)
                            if desc_match:
                                description = desc_match.group(1).strip()

                        themes.append(
                            Theme(
                                name=theme_name,
                                path=theme_path,
                                active=theme_name == current_theme,
                                description=description,
                            )
                        )

        return themes

    def set_theme(self, theme_name: str) -> CommandResult:
        """Set active theme."""
        # Update the es_settings.cfg file
        settings_path = "/opt/retropie/configs/all/emulationstation/es_settings.cfg"

        # First, check if the theme exists
        theme_check = self._client.execute_command(
            f"test -d /etc/emulationstation/themes/{theme_name}"
        )
        if not theme_check.success:
            return CommandResult(
                command="",
                exit_code=1,
                stdout="",
                stderr=f"Theme '{theme_name}' not found",
                success=False,
                execution_time=0.0,
            )

        # Update the theme setting
        command = f'sed -i \'s|<string name="ThemeSet" value="[^"]*"|<string name="ThemeSet" value="{theme_name}"|\' {settings_path}'
        result = self._client.execute_command(command, use_sudo=True)

        # Restart EmulationStation to apply the theme
        if result.success:
            restart_result = self._client.execute_command(
                "sudo systemctl restart emulationstation", use_sudo=True
            )
            if restart_result.success:
                result.stdout += "\nEmulationStation restarted to apply theme"

        return result

    def _get_supported_extensions(self, system: str) -> List[str]:
        """Get supported file extensions for a system.

        First attempts to parse extensions from es_systems.cfg file.
        Falls back to hard-coded extensions if parsing fails.
        """
        # Try to get extensions from parsed es_systems.cfg
        try:
            es_config = self._get_or_parse_es_systems_config()
            if es_config:
                # Find system in parsed config
                for system_def in es_config.systems:
                    if system_def.name == system:
                        return system_def.extensions
        except Exception:
            # Silently fall back to hard-coded extensions on any error
            pass

        # Fallback to hard-coded extensions
        return self._get_hardcoded_extensions(system)

    def _get_or_parse_es_systems_config(self) -> Optional[ESSystemsConfig]:
        """Get parsed es_systems.cfg config, with caching."""
        if self._cached_es_config is not None:
            return self._cached_es_config

        # Try different common locations for es_systems.cfg
        config_paths = [
            "/etc/emulationstation/es_systems.cfg",
            "~/.emulationstation/es_systems.cfg",
            "/opt/retropie/configs/all/emulationstation/es_systems.cfg"
        ]

        for config_path in config_paths:
            try:
                # Try to read the config file
                result = self._client.execute_command(f"cat {config_path}")
                if result.success and result.stdout.strip():
                    # Parse the content
                    parse_result = self._config_parser.parse_es_systems_config(result.stdout)
                    if parse_result.is_success():
                        self._cached_es_config = parse_result.success_value
                        return self._cached_es_config
            except Exception:
                # Continue to next path on error
                continue

        # No valid config found
        return None

    def _get_hardcoded_extensions(self, system: str) -> List[str]:
        """Get hard-coded file extensions for a system (fallback)."""
        # Common extensions by system (fallback when es_systems.cfg unavailable)
        extension_map = {
            "nes": [".nes", ".zip", ".7z"],
            "snes": [".smc", ".sfc", ".zip", ".7z"],
            "genesis": [".gen", ".md", ".bin", ".zip", ".7z"],
            "psx": [".cue", ".bin", ".iso", ".pbp", ".chd"],
            "n64": [".n64", ".z64", ".v64", ".zip", ".7z"],
            "arcade": [".zip", ".7z"],
            "mame": [".zip", ".7z"],
            "psp": [".iso", ".cso", ".pbp"],
            "dreamcast": [".cdi", ".gdi", ".chd"],
            "gamecube": [".iso", ".gcm", ".gcz"],
        }

        return extension_map.get(system, [".zip", ".7z"])

    def _build_find_command_for_system(self, system_path: str, system: str) -> str:
        """Build find command using system-specific extensions with graceful fallback."""
        try:
            # Get system-specific extensions
            extensions = self._get_supported_extensions(system)

            # If no specific extensions found, use common fallback extensions
            if not extensions:
                extensions = [".zip", ".7z", ".rom", ".bin", ".iso", ".cue"]

            # Build find command with system-specific extensions
            name_patterns = [f"-name '*{ext}'" for ext in extensions]
            find_patterns = " -o ".join(name_patterns)

            return f"find {system_path} -type f \\( {find_patterns} \\) 2>/dev/null | wc -l"

        except Exception:
            # Graceful fallback to original generic command if anything goes wrong
            return f"find {system_path} -type f \\( -name '*.rom' -o -name '*.bin' -o -name '*.iso' -o -name '*.cue' -o -name '*.zip' -o -name '*.7z' \\) 2>/dev/null | wc -l"
