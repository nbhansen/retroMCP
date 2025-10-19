"""SSH implementation of emulator repository."""

import re
import shlex
from typing import Dict
from typing import List
from typing import Optional

from ..config import RetroPieConfig
from ..domain.models import CommandResult
from ..domain.models import ConfigFile
from ..domain.models import CoreOption
from ..domain.models import DomainError
from ..domain.models import Emulator
from ..domain.models import EmulatorMapping
from ..domain.models import EmulatorStatus
from ..domain.models import ESSystemsConfig
from ..domain.models import Result
from ..domain.models import RetroArchCore
from ..domain.models import RomDirectory
from ..domain.models import Theme
from ..domain.models import ValidationError
from ..domain.ports import ConfigurationParser
from ..domain.ports import EmulatorRepository
from ..domain.ports import RetroPieClient
from .es_systems_parser import ESSystemsConfigParser
from .security_validator import SecurityValidator


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
        self._validator = SecurityValidator()

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

    def list_cores(self) -> Result[List[RetroArchCore], DomainError]:
        """List all installed RetroArch cores.

        Returns:
            Result containing list of RetroArchCore objects or DomainError.
        """
        try:
            cores: List[RetroArchCore] = []
            cores_dir = "/opt/retropie/libretrocores"

            # List all core directories
            result = self._client.execute_command(f"ls -1 {cores_dir} 2>/dev/null")

            if not result.success:
                return Result.error(
                    ValidationError(
                        code="CORES_DIR_NOT_FOUND",
                        message=f"RetroArch cores directory not found: {cores_dir}",
                        details={"stderr": result.stderr},
                    )
                )

            # Parse each core directory
            for line in result.stdout.strip().split("\n"):
                core_name = line.strip()
                if not core_name or core_name.startswith("."):
                    continue

                # Get core .so file path
                core_path_result = self._client.execute_command(
                    f"find {cores_dir}/{core_name} -name '*.so' -type f 2>/dev/null | head -1"
                )

                if not core_path_result.success or not core_path_result.stdout.strip():
                    continue

                core_path = core_path_result.stdout.strip()

                # Map core to systems by scanning emulators.cfg files
                systems = self._get_systems_for_core(core_name)

                # Try to extract version (optional)
                version = None

                # Get display name (clean up lr- prefix)
                display_name = core_name.replace("lr-", "").replace("-", " ").title()

                cores.append(
                    RetroArchCore(
                        name=core_name,
                        core_path=core_path,
                        systems=systems,
                        version=version,
                        display_name=display_name,
                        description=f"RetroArch libretro core: {display_name}",
                    )
                )

            return Result.success(cores)

        except Exception as e:
            return Result.error(
                DomainError(
                    code="LIST_CORES_FAILED",
                    message=f"Failed to list cores: {str(e)}",
                    details={"error": str(e)},
                )
            )

    def get_core_info(self, core_name: str) -> Result[RetroArchCore, DomainError]:
        """Get detailed information about a specific core.

        Args:
            core_name: Name of the core (e.g., 'lr-mupen64plus-next').

        Returns:
            Result containing RetroArchCore object or DomainError.
        """
        # Validate core name
        validation_result = self._validator.validate_package_name(core_name)
        if not validation_result.is_success():
            return Result.error(validation_result.error_value)

        try:
            cores_result = self.list_cores()
            if cores_result.is_error():
                return Result.error(cores_result.error_value)

            # Find the specific core
            cores = cores_result.success_value
            for core in cores:
                if core.name == core_name:
                    return Result.success(core)

            return Result.error(
                ValidationError(
                    code="CORE_NOT_FOUND",
                    message=f"Core '{core_name}' not found",
                    details={"core_name": core_name},
                )
            )

        except Exception as e:
            return Result.error(
                DomainError(
                    code="GET_CORE_INFO_FAILED",
                    message=f"Failed to get core info: {str(e)}",
                    details={"error": str(e), "core_name": core_name},
                )
            )

    def get_core_options(self, core_name: str) -> Result[List[CoreOption], DomainError]:
        """Get configurable options for a specific core.

        Args:
            core_name: Name of the core (e.g., 'lr-mupen64plus-next').

        Returns:
            Result containing list of CoreOption objects or DomainError.
        """
        # Validate core name
        validation_result = self._validator.validate_package_name(core_name)
        if not validation_result.is_success():
            return Result.error(validation_result.error_value)

        try:
            options: List[CoreOption] = []
            options_file = "/opt/retropie/configs/all/retroarch-core-options.cfg"

            # Read the core options file
            result = self._client.execute_command(f"cat {options_file} 2>/dev/null")

            if not result.success:
                return Result.error(
                    ValidationError(
                        code="OPTIONS_FILE_NOT_FOUND",
                        message=f"RetroArch core options file not found: {options_file}",
                        details={"stderr": result.stderr},
                    )
                )

            # Parse core options
            # Format: key = "value"
            # Core-specific options start with core name prefix
            # For lr-* cores, options usually use the core name without the lr- prefix
            # E.g., lr-mupen64plus-next -> mupen64plus-next-*
            core_prefix = core_name.replace("lr-", "") if core_name.startswith("lr-") else core_name

            for line in result.stdout.strip().split("\n"):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                # Parse key = "value" format
                match = re.match(r'^([^=]+)\s*=\s*"([^"]*)"', line)
                if match:
                    key = match.group(1).strip()
                    value = match.group(2).strip()

                    # Check if this option belongs to the specified core
                    # Match both with and without lr- prefix
                    if key.startswith(core_prefix) or key.startswith(core_name):
                        options.append(
                            CoreOption(
                                key=key,
                                value=value,
                                core_name=core_name,
                                description=None,
                            )
                        )

            return Result.success(options)

        except Exception as e:
            return Result.error(
                DomainError(
                    code="GET_CORE_OPTIONS_FAILED",
                    message=f"Failed to get core options: {str(e)}",
                    details={"error": str(e), "core_name": core_name},
                )
            )

    def update_core_option(
        self, core_name: str, option: CoreOption
    ) -> Result[bool, DomainError]:
        """Update a core-specific configuration option.

        Args:
            core_name: Name of the core (e.g., 'lr-mupen64plus-next').
            option: CoreOption object with key and value to update.

        Returns:
            Result containing success boolean or DomainError.
        """
        # Validate core name
        validation_result = self._validator.validate_package_name(core_name)
        if not validation_result.is_success():
            return Result.error(validation_result.error_value)

        # Validate option key (alphanumeric, hyphens, underscores)
        if not re.match(r'^[a-zA-Z0-9_-]+$', option.key):
            return Result.error(
                ValidationError(
                    code="INVALID_OPTION_KEY",
                    message=f"Invalid option key: {option.key}",
                    details={"key": option.key},
                )
            )

        try:
            options_file = "/opt/retropie/configs/all/retroarch-core-options.cfg"

            # Create backup first
            backup_command = f"cp {options_file} {options_file}.backup"
            self._client.execute_command(backup_command, use_sudo=True)

            # Use sed to update the option value
            # Escape special characters for sed
            safe_key = shlex.quote(option.key)
            safe_value = option.value.replace("/", "\\/").replace("&", "\\&")

            # Update existing option or append if not found
            command = f"""
            if grep -q "^{safe_key} =" {options_file}; then
                sed -i 's/^{safe_key} = ".*"/{safe_key} = "{safe_value}"/' {options_file}
            else
                echo '{option.key} = "{option.value}"' >> {options_file}
            fi
            """

            result = self._client.execute_command(command, use_sudo=True)

            if not result.success:
                return Result.error(
                    DomainError(
                        code="UPDATE_OPTION_FAILED",
                        message=f"Failed to update core option: {result.stderr}",
                        details={"stderr": result.stderr, "exit_code": result.exit_code},
                    )
                )

            return Result.success(True)

        except Exception as e:
            return Result.error(
                DomainError(
                    code="UPDATE_CORE_OPTION_FAILED",
                    message=f"Failed to update core option: {str(e)}",
                    details={"error": str(e), "core_name": core_name, "option": option.key},
                )
            )

    def get_emulator_mappings(
        self, system: str
    ) -> Result[List[EmulatorMapping], DomainError]:
        """Get available emulators/cores for a system.

        Args:
            system: System name (e.g., 'n64', 'nes').

        Returns:
            Result containing list of EmulatorMapping objects or DomainError.
        """
        # Validate system name
        validation_result = self._validator.validate_package_name(system)
        if not validation_result.is_success():
            return Result.error(validation_result.error_value)

        try:
            mappings: List[EmulatorMapping] = []
            emulators_cfg = f"/opt/retropie/configs/{system}/emulators.cfg"

            # Read the emulators.cfg file
            result = self._client.execute_command(f"cat {emulators_cfg} 2>/dev/null")

            if not result.success:
                return Result.error(
                    ValidationError(
                        code="EMULATORS_CFG_NOT_FOUND",
                        message=f"Emulators config not found for system: {system}",
                        details={"path": emulators_cfg},
                    )
                )

            # Parse emulators.cfg
            # Format:
            # emulator_name = "command"
            # default = "emulator_name"
            default_emulator = None

            for line in result.stdout.strip().split("\n"):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                if line.startswith("default ="):
                    match = re.match(r'default\s*=\s*"([^"]+)"', line)
                    if match:
                        default_emulator = match.group(1).strip()
                else:
                    match = re.match(r'^([^=]+)\s*=\s*"([^"]*)"', line)
                    if match:
                        emulator_name = match.group(1).strip()
                        command = match.group(2).strip()

                        # Extract core path if it's a libretro core
                        core_path = None
                        core_match = re.search(r"-L\s+([^\s]+\.so)", command)
                        if core_match:
                            core_path = core_match.group(1)

                        is_default = False  # Will update in second pass

                        mappings.append(
                            EmulatorMapping(
                                system=system,
                                emulator_name=emulator_name,
                                command=command,
                                is_default=is_default,
                                core_path=core_path,
                            )
                        )

            # Update default flag
            if default_emulator:
                for mapping in mappings:
                    if mapping.emulator_name == default_emulator:
                        # Need to recreate due to frozen dataclass
                        mappings[mappings.index(mapping)] = EmulatorMapping(
                            system=mapping.system,
                            emulator_name=mapping.emulator_name,
                            command=mapping.command,
                            is_default=True,
                            core_path=mapping.core_path,
                        )

            return Result.success(mappings)

        except Exception as e:
            return Result.error(
                DomainError(
                    code="GET_EMULATOR_MAPPINGS_FAILED",
                    message=f"Failed to get emulator mappings: {str(e)}",
                    details={"error": str(e), "system": system},
                )
            )

    def set_default_emulator(
        self, system: str, emulator_name: str
    ) -> Result[bool, DomainError]:
        """Set the default emulator/core for a system.

        Args:
            system: System name (e.g., 'n64', 'nes').
            emulator_name: Emulator name (e.g., 'lr-mupen64plus-next').

        Returns:
            Result containing success boolean or DomainError.
        """
        # Validate inputs
        system_validation = self._validator.validate_package_name(system)
        if not system_validation.is_success():
            return Result.error(system_validation.error_value)

        emulator_validation = self._validator.validate_package_name(emulator_name)
        if not emulator_validation.is_success():
            return Result.error(emulator_validation.error_value)

        try:
            emulators_cfg = f"/opt/retropie/configs/{system}/emulators.cfg"

            # First, verify the emulator exists in the config
            mappings_result = self.get_emulator_mappings(system)
            if mappings_result.is_error():
                return Result.error(mappings_result.error_value)

            mappings = mappings_result.success_value
            emulator_exists = any(m.emulator_name == emulator_name for m in mappings)

            if not emulator_exists:
                return Result.error(
                    ValidationError(
                        code="EMULATOR_NOT_FOUND",
                        message=f"Emulator '{emulator_name}' not found for system '{system}'",
                        details={"system": system, "emulator_name": emulator_name},
                    )
                )

            # Create backup
            backup_command = f"cp {emulators_cfg} {emulators_cfg}.backup"
            self._client.execute_command(backup_command, use_sudo=True)

            # Update default emulator using sed
            safe_emulator = shlex.quote(emulator_name)
            command = f'sed -i \'s/^default = ".*"/default = "{emulator_name}"/\' {emulators_cfg}'

            result = self._client.execute_command(command, use_sudo=True)

            if not result.success:
                return Result.error(
                    DomainError(
                        code="SET_DEFAULT_FAILED",
                        message=f"Failed to set default emulator: {result.stderr}",
                        details={"stderr": result.stderr, "exit_code": result.exit_code},
                    )
                )

            return Result.success(True)

        except Exception as e:
            return Result.error(
                DomainError(
                    code="SET_DEFAULT_EMULATOR_FAILED",
                    message=f"Failed to set default emulator: {str(e)}",
                    details={"error": str(e), "system": system, "emulator_name": emulator_name},
                )
            )

    def _get_systems_for_core(self, core_name: str) -> List[str]:
        """Map a core to its supported systems by scanning emulators.cfg files.

        Args:
            core_name: Core name (e.g., 'lr-mupen64plus-next').

        Returns:
            List of system names that use this core.
        """
        systems: List[str] = []

        try:
            configs_dir = "/opt/retropie/configs"

            # List all system directories
            result = self._client.execute_command(f"ls -1 {configs_dir} 2>/dev/null")

            if not result.success:
                return systems

            # Check each system's emulators.cfg
            for line in result.stdout.strip().split("\n"):
                system = line.strip()
                if not system or system.startswith(".") or system == "all":
                    continue

                emulators_cfg = f"{configs_dir}/{system}/emulators.cfg"
                cfg_result = self._client.execute_command(
                    f"grep '{core_name}' {emulators_cfg} 2>/dev/null"
                )

                if cfg_result.success and core_name in cfg_result.stdout:
                    systems.append(system)

        except Exception:
            # Return whatever we found so far
            pass

        return systems
