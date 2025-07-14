"""Shared pytest fixtures for RetroMCP tests."""

from typing import Any
from typing import Dict
from unittest.mock import MagicMock
from unittest.mock import Mock

import pytest

from retromcp.config import RetroPieConfig
from retromcp.container import Container
from retromcp.discovery import RetroPiePaths
from retromcp.domain.models import CommandResult
from retromcp.domain.models import ConnectionInfo
from retromcp.domain.models import Controller
from retromcp.domain.models import ControllerType
from retromcp.domain.models import SystemInfo
from retromcp.domain.ports import ControllerRepository
from retromcp.domain.ports import EmulatorRepository
from retromcp.domain.ports import RetroPieClient
from retromcp.domain.ports import SystemRepository
from retromcp.ssh_handler import RetroPieSSH


@pytest.fixture
def test_config() -> RetroPieConfig:
    """Provide test configuration."""
    return RetroPieConfig(
        host="test-retropie.local",
        username="retro",
        password="test_password",
        port=22,
    )


@pytest.fixture
def test_paths() -> RetroPiePaths:
    """Provide test RetroPie paths."""
    return RetroPiePaths(
        home_dir="/home/retro",
        username="retro",
        retropie_dir="/home/retro/RetroPie",
        retropie_setup_dir="/home/retro/RetroPie-Setup",
        bios_dir="/home/retro/RetroPie/BIOS",
        roms_dir="/home/retro/RetroPie/roms",
        configs_dir="/opt/retropie/configs",
        emulators_dir="/opt/retropie/emulators",
    )


@pytest.fixture
def mock_ssh_handler() -> Mock:
    """Provide mocked SSH handler."""
    mock = Mock(spec=RetroPieSSH)
    mock.host = "test-retropie.local"
    mock.port = 22
    mock.username = "retro"
    mock.connect.return_value = True
    mock.disconnect.return_value = None
    mock.test_connection.return_value = True
    mock.execute_command.return_value = (0, "success", "")
    return mock


@pytest.fixture
def mock_retropie_client() -> Mock:
    """Provide mocked RetroPie client."""
    mock = Mock(spec=RetroPieClient)
    mock.connect.return_value = True
    mock.disconnect.return_value = None
    mock.test_connection.return_value = True
    mock.get_connection_info.return_value = ConnectionInfo(
        host="test-retropie.local",
        port=22,
        username="retro",
        connected=True,
        last_connected="2024-01-01 12:00:00",
        connection_method="ssh",
    )
    mock.execute_command.return_value = CommandResult(
        command="test",
        exit_code=0,
        stdout="success",
        stderr="",
        success=True,
        execution_time=0.1,
    )
    return mock


@pytest.fixture
def mock_system_repository() -> Mock:
    """Provide mocked system repository."""
    mock = Mock(spec=SystemRepository)
    mock.get_system_info.return_value = SystemInfo(
        hostname="test-retropie",
        cpu_temperature=45.5,
        memory_total=4096,
        memory_used=1024,
        memory_free=3072,
        disk_total=32000,
        disk_used=8500,
        disk_free=21000,
        load_average=[0.08, 0.03, 0.01],
        uptime=200000,
    )
    return mock


@pytest.fixture
def mock_controller_repository() -> Mock:
    """Provide mocked controller repository."""
    mock = Mock(spec=ControllerRepository)
    mock.detect_controllers.return_value = [
        Controller(
            name="Xbox Wireless Controller",
            device_path="/dev/input/js0",
            vendor_id="045e",
            product_id="02ea",
            controller_type=ControllerType.XBOX,
            is_configured=True,
        )
    ]
    return mock


@pytest.fixture
def mock_emulator_repository() -> Mock:
    """Provide mocked emulator repository."""
    mock = Mock(spec=EmulatorRepository)
    return mock


@pytest.fixture
def mock_container(
    test_config: RetroPieConfig,
    mock_retropie_client: Mock,
    mock_system_repository: Mock,
    mock_controller_repository: Mock,
    mock_emulator_repository: Mock,
) -> Container:
    """Provide container with mocked dependencies."""
    container = Container(test_config)
    container._instances["retropie_client"] = mock_retropie_client
    container._instances["system_repository"] = mock_system_repository
    container._instances["controller_repository"] = mock_controller_repository
    container._instances["emulator_repository"] = mock_emulator_repository
    container._discovery_completed = True
    return container


@pytest.fixture
def sample_system_responses() -> Dict[str, Any]:
    """Provide sample SSH command responses for system operations."""
    return {
        "vcgencmd measure_temp": "temp=45.5'C",
        "free -m | grep Mem": "Mem:        4096    1024    3072     16     128    2944",
        "df -h / | tail -1": "/dev/root        32G  8.5G   21G  29% /",
        "pgrep emulationstation": "1234",
        "uname -r": "6.1.21-v8+",
        "uname -m": "aarch64",
        "lsb_release -d": "Description:\tRaspbian GNU/Linux 11 (bullseye)",
        "hostname": "test-retropie",
        "uptime": " 15:45:32 up  2 days,  3:45,  1 user,  load average: 0.08, 0.03, 0.01",
    }


@pytest.fixture
def sample_controller_responses() -> Dict[str, Any]:
    """Provide sample SSH command responses for controller operations."""
    return {
        "lsusb": "Bus 001 Device 002: ID 045e:02ea Microsoft Corp. Xbox Wireless Controller",
        "ls /dev/input/js* 2>/dev/null": "/dev/input/js0",
        "which jstest": "/usr/bin/jstest",
        "timeout 1 jstest --normal /dev/input/js0 2>/dev/null | head -3": (
            "Driver version is 2.1.0.\n"
            "Joystick (Xbox Wireless Controller) has 8 axes (X, Y, Z, Rx, Ry, Rz, Hat0X, Hat0Y)\n"
            "and 11 buttons (A, B, X, Y, LB, RB, View, Menu, Guide, LS, RS)."
        ),
    }


@pytest.fixture
def sample_hardware_responses() -> Dict[str, Any]:
    """Provide sample SSH command responses for hardware operations."""
    return {
        "vcgencmd measure_temp": "temp=45.5'C",
        "vcgencmd measure_volts core": "volt=1.2000V",
        "vcgencmd get_throttled": "throttled=0x0",
        "vcgencmd get_config int | grep fan": "gpio_fan_temp=60000",
        "cat /sys/class/thermal/thermal_zone0/temp": "45500",
        "dmesg | tail -20": "[ 1234.567] USB disconnect, address 1",
        "journalctl -n 10 --no-pager": "[INFO] System boot completed",
        "gpio readall": "GPIO readall output...",
    }


class AsyncMock(MagicMock):
    """Async mock for testing async functions."""

    async def __call__(self, *args: object, **kwargs: object) -> object:
        """Call the mock asynchronously."""
        return super().__call__(*args, **kwargs)
