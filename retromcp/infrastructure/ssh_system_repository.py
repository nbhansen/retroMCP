"""SSH implementation of system repository."""

import re
from typing import List

from ..config import RetroPieConfig
from ..domain.models import BiosFile
from ..domain.models import CommandResult
from ..domain.models import ConnectionError
from ..domain.models import ExecutionError
from ..domain.models import Package
from ..domain.models import Result
from ..domain.models import ServiceStatus
from ..domain.models import SystemInfo
from ..domain.models import SystemService
from ..domain.models import ValidationError
from ..domain.ports import RetroPieClient
from ..domain.ports import SystemRepository
from .cache_system import SystemCache


class SSHSystemRepository(SystemRepository):
    """SSH implementation of system repository interface."""

    def __init__(
        self, client: RetroPieClient, config: RetroPieConfig, cache: SystemCache
    ) -> None:
        """Initialize with RetroPie client, configuration, and cache."""
        self._client = client
        self._config = config
        self._cache = cache

    def get_system_info(
        self,
    ) -> Result[SystemInfo, ConnectionError | ExecutionError | ValidationError]:
        """Get system information."""
        try:
            # Check cache first
            cached_info = self._cache.get_system_info()
            if cached_info is not None:
                return Result.success(cached_info)

            # Get hostname
            hostname_result = self._client.execute_command("hostname")
            if not hostname_result.success:
                return Result.error(
                    ExecutionError(
                        code="HOSTNAME_COMMAND_FAILED",
                        message=f"Failed to get hostname: {hostname_result.stderr}",
                        command=hostname_result.command,
                        exit_code=hostname_result.exit_code,
                        stderr=hostname_result.stderr,
                    )
                )
            hostname = hostname_result.stdout.strip() or "unknown"

            # Get CPU temperature
            temp_result = self._client.execute_command("vcgencmd measure_temp")
            cpu_temperature = 0.0
            if temp_result.success:
                temp_str = temp_result.stdout.strip()
                temp_match = re.search(r"temp=(\d+\.\d+)'C", temp_str)
                if temp_match:
                    cpu_temperature = float(temp_match.group(1))
                else:
                    return Result.error(
                        ValidationError(
                            code="INVALID_TEMPERATURE_FORMAT",
                            message=f"Invalid temperature format: {temp_str}",
                            details={"raw_output": temp_str},
                        )
                    )

            # Get memory info
            mem_result = self._client.execute_command("free -b")
            memory_total = memory_used = memory_free = 0
            if mem_result.success:
                lines = mem_result.stdout.strip().split("\n")
                if len(lines) >= 2:
                    mem_line = lines[1].split()
                    if len(mem_line) >= 3:
                        memory_total = int(mem_line[1])
                        memory_used = int(mem_line[2])
                        memory_free = int(mem_line[3])

            # Get disk info
            disk_result = self._client.execute_command("df -B1 /")
            disk_total = disk_used = disk_free = 0
            if disk_result.success:
                lines = disk_result.stdout.strip().split("\n")
                if len(lines) >= 2:
                    disk_line = lines[1].split()
                    if len(disk_line) >= 4:
                        disk_total = int(disk_line[1])
                        disk_used = int(disk_line[2])
                        disk_free = int(disk_line[3])

            # Get load average
            load_result = self._client.execute_command("uptime")
            load_average = [0.0, 0.0, 0.0]
            if load_result.success:
                load_match = re.search(
                    r"load average: ([\d.]+), ([\d.]+), ([\d.]+)", load_result.stdout
                )
                if load_match:
                    load_average = [float(load_match.group(i)) for i in range(1, 4)]

            # Get uptime
            uptime_result = self._client.execute_command("cat /proc/uptime")
            uptime = 0
            if uptime_result.success:
                uptime_str = uptime_result.stdout.strip().split()[0]
                uptime = int(float(uptime_str))

            system_info = SystemInfo(
                hostname=hostname,
                cpu_temperature=cpu_temperature,
                memory_total=memory_total,
                memory_used=memory_used,
                memory_free=memory_free,
                disk_total=disk_total,
                disk_used=disk_used,
                disk_free=disk_free,
                load_average=load_average,
                uptime=uptime,
            )

            # Cache the result
            self._cache.cache_system_info(system_info)

            return Result.success(system_info)

        except Exception as e:
            return Result.error(
                ConnectionError(
                    code="CONNECTION_FAILED",
                    message=f"Failed to get system info: {e!s}",
                    details={"exception_type": type(e).__name__},
                )
            )

    def get_packages(self) -> Result[List[Package], ExecutionError]:
        """Get list of installed packages."""
        result = self._client.execute_command(
            "dpkg-query -W -f='${Package}|${Version}|${Status}\\n'"
        )

        if not result.success:
            return Result.error(
                ExecutionError(
                    code="PACKAGE_QUERY_FAILED",
                    message=f"Failed to get packages: {result.stderr}",
                    command=result.command,
                    exit_code=result.exit_code,
                    stderr=result.stderr,
                )
            )

        packages = []
        for line in result.stdout.strip().split("\n"):
            if line and "|" in line:
                parts = line.split("|")
                if len(parts) >= 3:
                    name = parts[0]
                    version = parts[1]
                    status = parts[2]
                    installed = "installed" in status

                    packages.append(
                        Package(
                            name=name,
                            version=version,
                            installed=installed,
                        )
                    )

        return Result.success(packages)

    def install_packages(
        self, packages: List[str] | None
    ) -> Result[CommandResult, ValidationError | ExecutionError]:
        """Install system packages."""
        if packages is None:
            return Result.error(
                ValidationError(
                    code="INVALID_INPUT",
                    message="Packages parameter cannot be None",
                    details={"parameter": "packages"},
                )
            )

        if not packages:
            no_op_result = CommandResult(
                command="",
                exit_code=0,
                stdout="No packages to install",
                stderr="",
                success=True,
                execution_time=0.0,
            )
            return Result.success(no_op_result)

        package_list = " ".join(packages)
        command = f"sudo apt-get update && sudo apt-get install -y {package_list}"
        result = self._client.execute_command(command, use_sudo=True)

        if not result.success:
            return Result.error(
                ExecutionError(
                    code="PACKAGE_INSTALL_FAILED",
                    message=f"Failed to install packages: {result.stderr}",
                    command=result.command,
                    exit_code=result.exit_code,
                    stderr=result.stderr,
                )
            )

        return Result.success(result)

    def update_system(self) -> CommandResult:
        """Update system packages."""
        command = "sudo apt-get update && sudo apt-get upgrade -y"
        return self._client.execute_command(command, use_sudo=True)

    def get_services(self) -> List[SystemService]:
        """Get list of system services."""
        result = self._client.execute_command(
            "systemctl list-units --type=service --no-pager"
        )
        services = []

        if result.success:
            lines = result.stdout.strip().split("\n")
            for line in lines[1:]:  # Skip header
                if line.strip() and not line.startswith("UNIT"):
                    parts = line.split()
                    if len(parts) >= 4:
                        name = parts[0].replace(".service", "")
                        load_state = parts[1]
                        active_state = parts[2]
                        _sub_state = parts[3]  # Not used but needed for unpacking

                        if active_state == "active":
                            status = ServiceStatus.RUNNING
                        elif active_state == "inactive":
                            status = ServiceStatus.STOPPED
                        elif active_state == "failed":
                            status = ServiceStatus.FAILED
                        else:
                            status = ServiceStatus.UNKNOWN

                        services.append(
                            SystemService(
                                name=name,
                                status=status,
                                enabled=load_state == "loaded",
                                description=" ".join(parts[4:])
                                if len(parts) > 4
                                else None,
                            )
                        )

        return services

    def restart_service(self, service_name: str) -> CommandResult:
        """Restart a system service."""
        command = f"sudo systemctl restart {service_name}"
        return self._client.execute_command(command, use_sudo=True)

    def get_bios_files(self) -> List[BiosFile]:
        """Get list of BIOS files."""
        bios_dir = self._config.bios_dir or f"{self._config.home_dir}/RetroPie/BIOS"
        result = self._client.execute_command(
            f"find {bios_dir} -type f -name '*.bin' -o -name '*.rom' -o -name '*.bios' 2>/dev/null"
        )

        bios_files = []
        if result.success:
            for line in result.stdout.strip().split("\n"):
                if line.strip():
                    path = line.strip()
                    name = path.split("/")[-1]

                    # Get file size
                    size_result = self._client.execute_command(f"stat -c%s '{path}'")
                    size = (
                        int(size_result.stdout.strip()) if size_result.success else None
                    )

                    # Determine system based on file name patterns
                    system = "unknown"
                    if "psx" in name.lower() or "scph" in name.lower():
                        system = "psx"
                    elif "dc_" in name.lower():
                        system = "dreamcast"
                    elif "kick" in name.lower():
                        system = "amiga"
                    elif "gba" in name.lower():
                        system = "gba"

                    bios_files.append(
                        BiosFile(
                            name=name,
                            path=path,
                            system=system,
                            required=True,  # Assume all BIOS files are required
                            present=True,  # If we found it, it's present
                            size=size,
                        )
                    )

        return bios_files
