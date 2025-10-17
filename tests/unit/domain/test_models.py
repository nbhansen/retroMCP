"""Unit tests for domain models."""

from dataclasses import FrozenInstanceError

import pytest

from retromcp.domain.models import BiosFile
from retromcp.domain.models import CommandResult
from retromcp.domain.models import ConnectionInfo
from retromcp.domain.models import Controller
from retromcp.domain.models import ControllerType
from retromcp.domain.models import Emulator
from retromcp.domain.models import EmulatorStatus
from retromcp.domain.models import Package
from retromcp.domain.models import ServiceStatus
from retromcp.domain.models import SystemInfo
from retromcp.domain.models import SystemService


class TestSystemInfo:
    """Test SystemInfo model."""

    def test_system_info_creation(self):
        """Test SystemInfo can be created with valid data."""
        info = SystemInfo(
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

        assert info.hostname == "test-retropie"
        assert info.cpu_temperature == 45.5
        assert info.memory_total == 4096
        assert len(info.load_average) == 3

    def test_system_info_immutable(self):
        """Test SystemInfo is immutable."""
        info = SystemInfo(
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

        with pytest.raises(FrozenInstanceError):
            info.hostname = "modified"


class TestController:
    """Test Controller model."""

    def test_controller_creation(self):
        """Test Controller can be created with valid data."""
        controller = Controller(
            name="Xbox Wireless Controller",
            device_path="/dev/input/js0",
            vendor_id="045e",
            product_id="02ea",
            controller_type=ControllerType.XBOX,
            connected=True,
            is_configured=True,
            driver_required="xboxdrv",
        )

        assert controller.name == "Xbox Wireless Controller"
        assert controller.controller_type == ControllerType.XBOX
        assert controller.connected is True
        assert controller.is_configured is True
        assert controller.driver_required == "xboxdrv"

    def test_controller_without_driver(self):
        """Test Controller can be created without driver requirement."""
        controller = Controller(
            name="Generic Controller",
            device_path="/dev/input/js1",
            vendor_id="1234",
            product_id="5678",
            controller_type=ControllerType.GENERIC,
            connected=True,
            is_configured=False,
        )

        assert controller.driver_required is None
        assert controller.is_configured is False
        assert controller.connected is True

    def test_controller_immutable(self):
        """Test Controller is immutable."""
        controller = Controller(
            name="Xbox Controller",
            device_path="/dev/input/js0",
            vendor_id="045e",
            product_id="02ea",
            controller_type=ControllerType.XBOX,
            connected=True,
            is_configured=True,
        )

        with pytest.raises(FrozenInstanceError):
            controller.name = "Modified"


class TestControllerType:
    """Test ControllerType enum."""

    def test_controller_type_values(self):
        """Test ControllerType enum has expected values."""
        assert ControllerType.XBOX.value == "xbox"
        assert ControllerType.PS4.value == "ps4"
        assert ControllerType.PS5.value == "ps5"
        assert ControllerType.NINTENDO_PRO.value == "nintendo_pro"
        assert ControllerType.EIGHT_BIT_DO.value == "8bitdo"
        assert ControllerType.GENERIC.value == "generic"
        assert ControllerType.UNKNOWN.value == "unknown"

    def test_controller_type_from_string(self):
        """Test ControllerType can be created from string value."""
        xbox_type = ControllerType("xbox")
        assert xbox_type == ControllerType.XBOX


class TestEmulator:
    """Test Emulator model."""

    def test_emulator_creation(self):
        """Test Emulator can be created with valid data."""
        emulator = Emulator(
            name="mupen64plus",
            system="n64",
            status=EmulatorStatus.INSTALLED,
            version="2.5.9",
            config_path="/opt/retropie/configs/n64/mupen64plus.cfg",
            bios_required=[],
        )

        assert emulator.name == "mupen64plus"
        assert emulator.system == "n64"
        assert emulator.status == EmulatorStatus.INSTALLED
        assert emulator.bios_required == []

    def test_emulator_with_bios(self):
        """Test Emulator with BIOS requirements."""
        emulator = Emulator(
            name="pcsx-rearmed",
            system="psx",
            status=EmulatorStatus.INSTALLED,
            bios_required=["scph1001.bin", "scph5501.bin"],
        )

        assert len(emulator.bios_required) == 2
        assert "scph1001.bin" in emulator.bios_required


class TestBiosFile:
    """Test BiosFile model."""

    def test_bios_file_creation(self):
        """Test BiosFile can be created with valid data."""
        bios = BiosFile(
            name="scph1001.bin",
            path="/home/retro/RetroPie/BIOS/scph1001.bin",
            system="psx",
            required=True,
            present=True,
            size=524288,
            checksum="abc123",
        )

        assert bios.name == "scph1001.bin"
        assert bios.required is True
        assert bios.present is True
        assert bios.size == 524288


class TestSystemService:
    """Test SystemService model."""

    def test_system_service_creation(self):
        """Test SystemService can be created with valid data."""
        service = SystemService(
            name="ssh",
            status=ServiceStatus.RUNNING,
            enabled=True,
            description="OpenSSH server daemon",
        )

        assert service.name == "ssh"
        assert service.status == ServiceStatus.RUNNING
        assert service.enabled is True


class TestPackage:
    """Test Package model."""

    def test_package_creation(self):
        """Test Package can be created with valid data."""
        package = Package(
            name="emulationstation",
            version="2.11.2",
            installed=True,
            available_version="2.11.3",
            description="A flexible emulator front-end",
        )

        assert package.name == "emulationstation"
        assert package.installed is True
        assert package.available_version == "2.11.3"


class TestCommandResult:
    """Test CommandResult model."""

    def test_command_result_success(self):
        """Test CommandResult for successful command."""
        result = CommandResult(
            command="echo test",
            exit_code=0,
            stdout="test",
            stderr="",
            success=True,
            execution_time=0.01,
        )

        assert result.success is True
        assert result.exit_code == 0
        assert result.stdout == "test"
        assert result.stderr == ""

    def test_command_result_failure(self):
        """Test CommandResult for failed command."""
        result = CommandResult(
            command="false",
            exit_code=1,
            stdout="",
            stderr="command failed",
            success=False,
            execution_time=0.02,
        )

        assert result.success is False
        assert result.exit_code == 1
        assert result.stderr == "command failed"


class TestConnectionInfo:
    """Test ConnectionInfo model."""

    def test_connection_info_creation(self):
        """Test ConnectionInfo can be created with valid data."""
        info = ConnectionInfo(
            host="retropie.local",
            port=22,
            username="retro",
            connected=True,
            last_connected="2024-01-01 12:00:00",
            connection_method="ssh",
        )

        assert info.host == "retropie.local"
        assert info.port == 22
        assert info.connected is True
        assert info.connection_method == "ssh"

    def test_connection_info_default_method(self):
        """Test ConnectionInfo uses default connection method."""
        info = ConnectionInfo(
            host="retropie.local",
            port=22,
            username="retro",
            connected=False,
        )

        assert info.connection_method == "ssh"
        assert info.last_connected is None
