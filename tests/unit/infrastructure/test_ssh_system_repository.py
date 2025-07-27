"""Unit tests for SSH system repository."""

from unittest.mock import Mock

import pytest

from retromcp.config import RetroPieConfig
from retromcp.discovery import RetroPiePaths
from retromcp.domain.models import CommandResult
from retromcp.domain.ports import RetroPieClient
from retromcp.infrastructure.cache_system import SystemCache
from retromcp.infrastructure.ssh_system_repository import SSHSystemRepository


class TestSSHSystemRepository:
    """Test cases for SSH system repository."""

    @pytest.fixture
    def mock_client(self) -> Mock:
        """Create mock RetroPie client."""
        return Mock(spec=RetroPieClient)

    @pytest.fixture
    def mock_cache(self) -> Mock:
        """Create mock system cache."""
        return Mock(spec=SystemCache)

    @pytest.fixture
    def test_config(self) -> RetroPieConfig:
        """Create test configuration."""
        paths = RetroPiePaths(
            home_dir="/home/retro",
            username="retro",
            retropie_dir="/home/retro/RetroPie",
            retropie_setup_dir="/home/retro/RetroPie-Setup",
            bios_dir="/home/retro/RetroPie/BIOS",
            roms_dir="/home/retro/RetroPie/roms",
            configs_dir="/opt/retropie/configs",
            emulators_dir="/opt/retropie/emulators",
        )
        return RetroPieConfig(
            host="test-retropie.local",
            username="retro",
            password="test_password",  # noqa: S106
            port=22,
            paths=paths,
        )

    @pytest.fixture
    def repository(
        self, mock_client: Mock, test_config: RetroPieConfig, mock_cache: Mock
    ) -> SSHSystemRepository:
        """Create SSH system repository instance."""
        return SSHSystemRepository(mock_client, test_config, mock_cache)

    def test_initialization(
        self, mock_client: Mock, test_config: RetroPieConfig, mock_cache: Mock
    ) -> None:
        """Test repository initialization."""
        repo = SSHSystemRepository(mock_client, test_config, mock_cache)
        assert repo._client == mock_client
        assert repo._config == test_config
        assert repo._cache == mock_cache

    def test_get_system_info_success(
        self, repository: SSHSystemRepository, mock_client: Mock, mock_cache: Mock
    ) -> None:
        """Test successful system info retrieval."""
        # Mock cache to return None (no cached data)
        mock_cache.get_system_info.return_value = None

        # Mock command results - get_system_info calls 6 commands: hostname, temp, memory, disk, uptime, proc/uptime
        mock_client.execute_command.side_effect = [
            CommandResult(
                command="hostname",
                exit_code=0,
                stdout="retropie",
                stderr="",
                success=True,
                execution_time=0.1,
            ),  # hostname
            CommandResult(
                command="vcgencmd measure_temp",
                exit_code=0,
                stdout="temp=55.4'C",
                stderr="",
                success=True,
                execution_time=0.1,
            ),  # temperature
            CommandResult(
                command="free -b",
                exit_code=0,
                stdout="              total        used        free\nMem:     1073741824   536870912   536870912",
                stderr="",
                success=True,
                execution_time=0.1,
            ),  # memory
            CommandResult(
                command="df -B1 /",
                exit_code=0,
                stdout="Filesystem     1B-blocks      Used Available Use%\n/dev/root     16000000000  8000000000  8000000000  50%",
                stderr="",
                success=True,
                execution_time=0.1,
            ),  # disk
            CommandResult(
                command="uptime",
                exit_code=0,
                stdout="up 1 day, 5:30,  load average: 0.15, 0.10, 0.05",
                stderr="",
                success=True,
                execution_time=0.1,
            ),  # uptime
            CommandResult(
                command="cat /proc/uptime",
                exit_code=0,
                stdout="105120.50 102345.67",
                stderr="",
                success=True,
                execution_time=0.1,
            ),  # proc uptime
        ]

        result = repository.get_system_info()

        # Verify Result is successful
        assert result.is_success()
        system_info = result.value

        assert system_info.hostname == "retropie"
        assert system_info.cpu_temperature == 55.4
        assert system_info.memory_total == 1073741824
        assert system_info.memory_used == 536870912
        assert system_info.memory_free == 536870912
        assert system_info.disk_total == 16000000000
        assert system_info.uptime == 105120

        # Verify cache was called to store the result
        mock_cache.cache_system_info.assert_called_once_with(system_info)

    def test_get_system_info_command_failures(
        self, repository: SSHSystemRepository, mock_client: Mock
    ) -> None:
        """Test system info retrieval with command failures."""
        # Mock failed command results - all 6 commands fail
        mock_client.execute_command.side_effect = [
            CommandResult(
                command="hostname",
                exit_code=1,
                stdout="",
                stderr="hostname error",
                success=False,
                execution_time=0.1,
            ),  # hostname
            CommandResult(
                command="vcgencmd measure_temp",
                exit_code=1,
                stdout="",
                stderr="temp error",
                success=False,
                execution_time=0.1,
            ),  # temperature
            CommandResult(
                command="free -b",
                exit_code=1,
                stdout="",
                stderr="memory error",
                success=False,
                execution_time=0.1,
            ),  # memory
            CommandResult(
                command="df -B1 /",
                exit_code=1,
                stdout="",
                stderr="disk error",
                success=False,
                execution_time=0.1,
            ),  # disk
            CommandResult(
                command="uptime",
                exit_code=1,
                stdout="",
                stderr="uptime error",
                success=False,
                execution_time=0.1,
            ),  # uptime
            CommandResult(
                command="cat /proc/uptime",
                exit_code=1,
                stdout="",
                stderr="proc uptime error",
                success=False,
                execution_time=0.1,
            ),  # proc uptime
        ]

        system_info = repository.get_system_info()

        assert system_info.hostname == "unknown"
        assert system_info.cpu_temperature == 0.0
        assert system_info.memory_total == 0
        assert system_info.memory_used == 0
        assert system_info.memory_free == 0

    def test_install_packages_success(
        self, repository: SSHSystemRepository, mock_client: Mock
    ) -> None:
        """Test successful package installation."""
        mock_client.execute_command.return_value = CommandResult(
            command="sudo apt-get update && sudo apt-get install -y package1",
            exit_code=0,
            stdout="Package installed successfully",
            stderr="",
            success=True,
            execution_time=5.0,
        )

        result = repository.install_packages(["package1"])

        assert result.success is True
        assert "Package installed successfully" in result.stdout
        mock_client.execute_command.assert_called_once_with(
            "sudo apt-get update && sudo apt-get install -y package1", use_sudo=True
        )

    def test_install_packages_multiple(
        self, repository: SSHSystemRepository, mock_client: Mock
    ) -> None:
        """Test installing multiple packages."""
        mock_client.execute_command.return_value = CommandResult(
            command="sudo apt-get update && sudo apt-get install -y package1 package2",
            exit_code=0,
            stdout="Packages installed",
            stderr="",
            success=True,
            execution_time=10.0,
        )

        result = repository.install_packages(["package1", "package2"])

        assert result.success is True
        mock_client.execute_command.assert_called_once_with(
            "sudo apt-get update && sudo apt-get install -y package1 package2",
            use_sudo=True,
        )

    def test_install_packages_failure(
        self, repository: SSHSystemRepository, mock_client: Mock
    ) -> None:
        """Test failed package installation."""
        mock_client.execute_command.return_value = CommandResult(
            command="sudo apt-get install -y nonexistent-package",
            exit_code=1,
            stdout="",
            stderr="Package not found",
            success=False,
            execution_time=2.0,
        )

        result = repository.install_packages(["nonexistent-package"])

        assert result.success is False
        assert "Package not found" in result.stderr

    def test_update_system_success(
        self, repository: SSHSystemRepository, mock_client: Mock
    ) -> None:
        """Test successful system update."""
        mock_client.execute_command.return_value = CommandResult(
            command="sudo apt-get update && sudo apt-get upgrade -y",
            exit_code=0,
            stdout="System updated successfully",
            stderr="",
            success=True,
            execution_time=30.0,
        )

        result = repository.update_system()

        assert result.success is True
        mock_client.execute_command.assert_called_once_with(
            "sudo apt-get update && sudo apt-get upgrade -y", use_sudo=True
        )

    def test_update_system_failure(
        self, repository: SSHSystemRepository, mock_client: Mock
    ) -> None:
        """Test failed system update."""
        mock_client.execute_command.return_value = CommandResult(
            command="apt-get update && apt-get upgrade -y",
            exit_code=1,
            stdout="",
            stderr="Update failed",
            success=False,
            execution_time=5.0,
        )

        result = repository.update_system()

        assert result.success is False
        assert "Update failed" in result.stderr

    def test_restart_service_success(
        self, repository: SSHSystemRepository, mock_client: Mock
    ) -> None:
        """Test successful service restart."""
        mock_client.execute_command.return_value = CommandResult(
            command="sudo systemctl restart emulationstation",
            exit_code=0,
            stdout="",
            stderr="",
            success=True,
            execution_time=2.0,
        )

        result = repository.restart_service("emulationstation")

        assert result.success is True
        mock_client.execute_command.assert_called_once_with(
            "sudo systemctl restart emulationstation", use_sudo=True
        )

    def test_restart_service_failure(
        self, repository: SSHSystemRepository, mock_client: Mock
    ) -> None:
        """Test failed service restart."""
        mock_client.execute_command.return_value = CommandResult(
            command="sudo systemctl restart failing-service",
            exit_code=1,
            stdout="",
            stderr="restart failed",
            success=False,
            execution_time=1.0,
        )

        result = repository.restart_service("failing-service")

        assert result.success is False
        assert result.stderr == "restart failed"

    def test_get_packages_success(
        self, repository: SSHSystemRepository, mock_client: Mock
    ) -> None:
        """Test successful package listing."""
        mock_client.execute_command.return_value = CommandResult(
            command="dpkg-query -W -f='${Package}|${Version}|${Status}\n'",
            exit_code=0,
            stdout="apt|2.0.6|install ok installed\nbase-files|11.1+deb11u7|install ok installed\nbash|5.1-2+deb11u1|install ok installed",
            stderr="",
            success=True,
            execution_time=1.0,
        )

        packages = repository.get_packages()

        assert len(packages) == 3
        assert packages[0].name == "apt"
        assert packages[0].version == "2.0.6"
        assert packages[0].installed is True

        assert packages[1].name == "base-files"
        assert packages[1].version == "11.1+deb11u7"

        assert packages[2].name == "bash"
        assert packages[2].version == "5.1-2+deb11u1"

    def test_get_packages_command_failure(
        self, repository: SSHSystemRepository, mock_client: Mock
    ) -> None:
        """Test package listing when command fails."""
        mock_client.execute_command.return_value = CommandResult(
            command="dpkg-query -W -f='${Package}|${Version}|${Status}\n'",
            exit_code=1,
            stdout="",
            stderr="Command failed",
            success=False,
            execution_time=0.5,
        )

        packages = repository.get_packages()

        assert len(packages) == 0

    def test_get_packages_malformed_output(
        self, repository: SSHSystemRepository, mock_client: Mock
    ) -> None:
        """Test package listing with malformed output."""
        mock_client.execute_command.return_value = CommandResult(
            command="dpkg-query -W -f='${Package}|${Version}|${Status}\n'",
            exit_code=0,
            stdout="malformed output without proper columns",
            stderr="",
            success=True,
            execution_time=1.0,
        )

        packages = repository.get_packages()

        # Should handle malformed output gracefully
        assert len(packages) == 0

    def test_get_services_success(
        self, repository: SSHSystemRepository, mock_client: Mock
    ) -> None:
        """Test getting system services successfully."""
        # Mock the systemctl list-units command output
        mock_output = """UNIT                     LOAD   ACTIVE SUB     DESCRIPTION
ssh.service              loaded active running OpenBSD Secure Shell server
emulationstation.service loaded active running EmulationStation
bluetooth.service        loaded failed failed  Bluetooth service"""

        mock_client.execute_command.return_value = CommandResult(
            command="systemctl list-units --type=service --no-pager",
            exit_code=0,
            stdout=mock_output,
            stderr="",
            success=True,
            execution_time=1.0,
        )

        services = repository.get_services()

        assert len(services) == 3

        # Check SSH service
        ssh_service = next((s for s in services if s.name == "ssh"), None)
        assert ssh_service is not None
        assert ssh_service.description == "OpenBSD Secure Shell server"

        # Check EmulationStation service
        es_service = next((s for s in services if s.name == "emulationstation"), None)
        assert es_service is not None
        assert es_service.description == "EmulationStation"

        # Check failed service
        bt_service = next((s for s in services if s.name == "bluetooth"), None)
        assert bt_service is not None
        assert bt_service.description == "Bluetooth service"

    def test_get_services_command_failure(
        self, repository: SSHSystemRepository, mock_client: Mock
    ) -> None:
        """Test getting services when command fails."""
        mock_client.execute_command.return_value = CommandResult(
            command="systemctl list-units --type=service --no-pager",
            exit_code=1,
            stdout="",
            stderr="Command failed",
            success=False,
            execution_time=0.5,
        )

        services = repository.get_services()

        assert len(services) == 0

    def test_get_bios_files_found(
        self, repository: SSHSystemRepository, mock_client: Mock
    ) -> None:
        """Test checking BIOS files when files are found."""
        mock_client.execute_command.return_value = CommandResult(
            command="find /home/retro/RetroPie/BIOS -type f -name '*.bin' -o -name '*.rom' -o -name '*.bios'",
            exit_code=0,
            stdout="/home/retro/RetroPie/BIOS/scph1001.bin\n/home/retro/RetroPie/BIOS/scph5501.bin",
            stderr="",
            success=True,
            execution_time=0.5,
        )

        # Mock file size commands
        mock_client.execute_command.side_effect = [
            CommandResult(
                command="find /home/retro/RetroPie/BIOS -type f -name '*.bin' -o -name '*.rom' -o -name '*.bios'",
                exit_code=0,
                stdout="/home/retro/RetroPie/BIOS/scph1001.bin\n/home/retro/RetroPie/BIOS/scph5501.bin",
                stderr="",
                success=True,
                execution_time=0.5,
            ),
            CommandResult(
                command="stat -c%s '/home/retro/RetroPie/BIOS/scph1001.bin'",
                exit_code=0,
                stdout="524288",
                stderr="",
                success=True,
                execution_time=0.1,
            ),
            CommandResult(
                command="stat -c%s '/home/retro/RetroPie/BIOS/scph5501.bin'",
                exit_code=0,
                stdout="524288",
                stderr="",
                success=True,
                execution_time=0.1,
            ),
        ]

        bios_files = repository.get_bios_files()

        assert len(bios_files) == 2
        assert bios_files[0].name == "scph1001.bin"
        assert bios_files[0].present is True
        assert bios_files[1].name == "scph5501.bin"
        assert bios_files[1].present is True

    def test_get_bios_files_not_found(
        self, repository: SSHSystemRepository, mock_client: Mock
    ) -> None:
        """Test checking BIOS files when no files are found."""
        mock_client.execute_command.return_value = CommandResult(
            command="find /home/retro/RetroPie/BIOS -type f -name '*.bin' -o -name '*.rom' -o -name '*.bios'",
            exit_code=0,
            stdout="",
            stderr="",
            success=True,
            execution_time=0.2,
        )

        bios_files = repository.get_bios_files()

        assert len(bios_files) == 0

    def test_get_bios_files_command_failure(
        self, repository: SSHSystemRepository, mock_client: Mock
    ) -> None:
        """Test checking BIOS files when command fails."""
        mock_client.execute_command.return_value = CommandResult(
            command="find /home/retro/RetroPie/BIOS -type f -name '*.bin' -o -name '*.rom' -o -name '*.bios'",
            exit_code=1,
            stdout="",
            stderr="Directory not found",
            success=False,
            execution_time=0.1,
        )

        bios_files = repository.get_bios_files()

        assert len(bios_files) == 0

    def test_memory_parsing_with_different_formats(
        self, repository: SSHSystemRepository, mock_client: Mock
    ) -> None:
        """Test memory parsing with various output formats."""
        # Test with different memory output formats including extra columns
        mock_client.execute_command.side_effect = [
            CommandResult(
                command="hostname",
                exit_code=0,
                stdout="hostname",
                stderr="",
                success=True,
                execution_time=0.1,
            ),  # hostname
            CommandResult(
                command="vcgencmd measure_temp",
                exit_code=0,
                stdout="temp=60.0'C",
                stderr="",
                success=True,
                execution_time=0.1,
            ),  # temperature
            CommandResult(
                command="free -b",
                exit_code=0,
                stdout="              total        used        free      shared  buff/cache   available\nMem:        1000000      500000      300000           0      200000      450000",
                stderr="",
                success=True,
                execution_time=0.1,
            ),  # memory with extra columns
            CommandResult(
                command="df -B1 /",
                exit_code=0,
                stdout="Filesystem     1B-blocks      Used Available Use%\n/dev/root     10000000000  5000000000  5000000000  50%",
                stderr="",
                success=True,
                execution_time=0.1,
            ),  # disk
            CommandResult(
                command="uptime",
                exit_code=0,
                stdout="up 1 day, load average: 0.10, 0.05, 0.01",
                stderr="",
                success=True,
                execution_time=0.1,
            ),  # uptime
            CommandResult(
                command="cat /proc/uptime",
                exit_code=0,
                stdout="86400.00 80000.00",
                stderr="",
                success=True,
                execution_time=0.1,
            ),  # proc uptime
        ]

        system_info = repository.get_system_info()

        # Should still parse the first 3 memory columns correctly
        assert system_info.memory_total == 1000000
        assert system_info.memory_used == 500000
        assert system_info.memory_free == 300000

    def test_temperature_parsing_edge_cases(
        self, repository: SSHSystemRepository, mock_client: Mock
    ) -> None:
        """Test temperature parsing with malformed output."""
        mock_client.execute_command.side_effect = [
            CommandResult(
                command="hostname",
                exit_code=0,
                stdout="retropie",
                stderr="",
                success=True,
                execution_time=0.1,
            ),  # hostname
            CommandResult(
                command="vcgencmd measure_temp",
                exit_code=0,
                stdout="malformed temp output",
                stderr="",
                success=True,
                execution_time=0.1,
            ),  # malformed temperature
            CommandResult(
                command="free -b",
                exit_code=0,
                stdout="              total        used        free\nMem:     1000   500   500",
                stderr="",
                success=True,
                execution_time=0.1,
            ),  # memory
            CommandResult(
                command="df -B1 /",
                exit_code=0,
                stdout="Filesystem     1B-blocks      Used Available Use%\n/dev/root     2000  1000  1000  50%",
                stderr="",
                success=True,
                execution_time=0.1,
            ),  # disk
            CommandResult(
                command="uptime",
                exit_code=0,
                stdout="up 1 day, load average: 0.01, 0.02, 0.03",
                stderr="",
                success=True,
                execution_time=0.1,
            ),  # uptime
            CommandResult(
                command="cat /proc/uptime",
                exit_code=0,
                stdout="3600.00 3000.00",
                stderr="",
                success=True,
                execution_time=0.1,
            ),  # proc uptime
        ]

        system_info = repository.get_system_info()

        assert system_info.hostname == "retropie"
        assert system_info.cpu_temperature == 0.0  # Should default to 0.0
        assert system_info.memory_total == 1000

    def test_bios_files_path_extraction(
        self, repository: SSHSystemRepository, mock_client: Mock
    ) -> None:
        """Test BIOS file path extraction from different outputs."""
        # Test with various path formats - mock find command and stat commands
        mock_client.execute_command.side_effect = [
            CommandResult(
                command="find /home/retro/RetroPie/BIOS -type f -name '*.bin' -o -name '*.rom' -o -name '*.bios' 2>/dev/null",
                exit_code=0,
                stdout="/full/path/to/bios.bin\n./relative/path.rom\nfilename_only.bin",
                stderr="",
                success=True,
                execution_time=0.3,
            ),
            CommandResult(
                command="stat -c%s '/full/path/to/bios.bin'",
                exit_code=0,
                stdout="1024",
                stderr="",
                success=True,
                execution_time=0.1,
            ),
            CommandResult(
                command="stat -c%s './relative/path.rom'",
                exit_code=0,
                stdout="2048",
                stderr="",
                success=True,
                execution_time=0.1,
            ),
            CommandResult(
                command="stat -c%s 'filename_only.bin'",
                exit_code=0,
                stdout="4096",
                stderr="",
                success=True,
                execution_time=0.1,
            ),
        ]

        bios_files = repository.get_bios_files()

        assert len(bios_files) == 3
        assert bios_files[0].name == "bios.bin"
        assert bios_files[1].name == "path.rom"
        assert bios_files[2].name == "filename_only.bin"

        # All should be marked as present since they were returned by the command
        assert all(bf.present for bf in bios_files)

    def test_privileged_commands_require_sudo(
        self, repository: SSHSystemRepository, mock_client: Mock
    ) -> None:
        """Test that all privileged operations use sudo for security compliance."""
        # Test package installation uses sudo
        mock_client.execute_command.return_value = CommandResult(
            command="sudo apt-get update && sudo apt-get install -y testpkg",
            exit_code=0,
            stdout="",
            stderr="",
            success=True,
            execution_time=1.0,
        )

        repository.install_packages(["testpkg"])

        # Verify command includes sudo and use_sudo=True
        mock_client.execute_command.assert_called_with(
            "sudo apt-get update && sudo apt-get install -y testpkg", use_sudo=True
        )

        # Test system restart uses sudo
        mock_client.reset_mock()
        mock_client.execute_command.return_value = CommandResult(
            command="sudo systemctl restart test-service",
            exit_code=0,
            stdout="",
            stderr="",
            success=True,
            execution_time=1.0,
        )

        repository.restart_service("test-service")

        # Verify service restart includes sudo and use_sudo=True
        mock_client.execute_command.assert_called_with(
            "sudo systemctl restart test-service", use_sudo=True
        )
