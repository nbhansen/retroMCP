"""Unit tests for state management domain models."""

import json
from datetime import datetime

import pytest

from retromcp.domain.models import HardwareInfo
from retromcp.domain.models import NetworkInterface
from retromcp.domain.models import NetworkStatus
from retromcp.domain.models import ServiceStatus
from retromcp.domain.models import SoftwareInfo
from retromcp.domain.models import StateAction
from retromcp.domain.models import StateManagementRequest
from retromcp.domain.models import StateManagementResult
from retromcp.domain.models import StorageDevice
from retromcp.domain.models import SystemNote
from retromcp.domain.models import SystemService
from retromcp.domain.models import SystemState


class TestStateModels:
    """Test cases for state management domain models."""

    def test_state_action_enum(self) -> None:
        """Test StateAction enum has expected values."""
        assert StateAction.LOAD.value == "load"
        assert StateAction.SAVE.value == "save"
        assert StateAction.UPDATE.value == "update"
        assert StateAction.COMPARE.value == "compare"

    def test_system_state_immutability(self) -> None:
        """Test that SystemState is immutable."""
        state = SystemState(
            schema_version="1.0",
            last_updated=datetime.now().isoformat(),
            system={
                "hardware": "Pi 4B",
                "overclocking": "medium",
                "temperatures": {"normal_range": "45-65°C"},
            },
            emulators={
                "installed": ["mupen64plus"],
                "preferred": {"n64": "mupen64plus"},
            },
            controllers=[],
            roms={"systems": ["nes"], "counts": {"nes": 10}},
            custom_configs=["shaders"],
            known_issues=[],
        )

        # Test that state is frozen
        with pytest.raises(AttributeError):
            state.schema_version = "2.0"  # type: ignore

    def test_system_state_to_json(self) -> None:
        """Test SystemState can be serialized to JSON."""
        state = SystemState(
            schema_version="1.0",
            last_updated="2025-07-15T12:00:00Z",
            system={
                "hardware": "Pi 4B",
                "overclocking": "medium",
                "temperatures": {"normal_range": "45-65°C"},
            },
            emulators={
                "installed": ["mupen64plus", "pcsx-rearmed"],
                "preferred": {"n64": "mupen64plus-gliden64"},
            },
            controllers=[
                {"type": "xbox", "device": "/dev/input/js0", "configured": True}
            ],
            roms={"systems": ["nes", "snes"], "counts": {"nes": 150, "snes": 89}},
            custom_configs=["shaders", "bezels"],
            known_issues=["audio crackling"],
        )

        # Convert to JSON and back
        json_str = state.to_json()
        data = json.loads(json_str)

        assert data["schema_version"] == "1.0"
        assert data["last_updated"] == "2025-07-15T12:00:00Z"
        assert data["system"]["hardware"] == "Pi 4B"
        assert len(data["emulators"]["installed"]) == 2
        assert data["controllers"][0]["type"] == "xbox"
        assert data["roms"]["counts"]["nes"] == 150

    def test_system_state_from_json(self) -> None:
        """Test SystemState can be deserialized from JSON."""
        json_data = {
            "schema_version": "1.0",
            "last_updated": "2025-07-15T12:00:00Z",
            "system": {
                "hardware": "Pi 4B",
                "overclocking": "medium",
                "temperatures": {"normal_range": "45-65°C"},
            },
            "emulators": {
                "installed": ["mupen64plus"],
                "preferred": {"n64": "mupen64plus"},
            },
            "controllers": [],
            "roms": {"systems": ["nes"], "counts": {"nes": 10}},
            "custom_configs": ["shaders"],
            "known_issues": [],
        }

        state = SystemState.from_json(json.dumps(json_data))

        assert state.schema_version == "1.0"
        assert state.system["hardware"] == "Pi 4B"
        assert len(state.emulators["installed"]) == 1
        assert state.roms["counts"]["nes"] == 10

    def test_state_management_request_immutability(self) -> None:
        """Test StateManagementRequest is immutable."""
        request = StateManagementRequest(
            action=StateAction.UPDATE, path="system.hardware", value="Pi 5"
        )

        with pytest.raises(AttributeError):
            request.action = StateAction.LOAD  # type: ignore

    def test_state_management_request_optional_fields(self) -> None:
        """Test StateManagementRequest with optional fields."""
        # Load action doesn't need path or value
        load_request = StateManagementRequest(action=StateAction.LOAD)
        assert load_request.path is None
        assert load_request.value is None
        assert load_request.force_scan is False

        # Update action needs path and value
        update_request = StateManagementRequest(
            action=StateAction.UPDATE,
            path="system.hardware",
            value="Pi 5",
            force_scan=True,
        )
        assert update_request.path == "system.hardware"
        assert update_request.value == "Pi 5"
        assert update_request.force_scan is True

    def test_state_management_result_immutability(self) -> None:
        """Test StateManagementResult is immutable."""
        result = StateManagementResult(
            success=True,
            action=StateAction.SAVE,
            message="State saved successfully",
            state=None,
        )

        with pytest.raises(AttributeError):
            result.success = False  # type: ignore

    def test_state_management_result_with_state(self) -> None:
        """Test StateManagementResult can include state data."""
        state = SystemState(
            schema_version="1.0",
            last_updated="2025-07-15T12:00:00Z",
            system={"hardware": "Pi 4B"},
            emulators={"installed": [], "preferred": {}},
            controllers=[],
            roms={"systems": [], "counts": {}},
            custom_configs=[],
            known_issues=[],
        )

        result = StateManagementResult(
            success=True,
            action=StateAction.LOAD,
            message="State loaded successfully",
            state=state,
        )

        assert result.state is not None
        assert result.state.schema_version == "1.0"

    def test_state_management_result_with_diff(self) -> None:
        """Test StateManagementResult can include diff data."""
        diff = {
            "added": {"system.new_field": "value"},
            "changed": {"system.hardware": {"old": "Pi 4B", "new": "Pi 5"}},
            "removed": {"system.old_field": "old_value"},
        }

        result = StateManagementResult(
            success=True,
            action=StateAction.COMPARE,
            message="Comparison complete",
            diff=diff,
        )

        assert result.diff is not None
        assert "added" in result.diff
        assert result.diff["changed"]["system.hardware"]["new"] == "Pi 5"


class TestV2StateModels:
    """Test cases for v2.0 state management domain models."""

    def test_hardware_info_immutability(self) -> None:
        """Test that HardwareInfo is immutable."""
        storage = StorageDevice(
            device="/dev/sda1",
            mount="/",
            size="500GB",
            used="45GB",
            filesystem_type="ext4"
        )

        hardware = HardwareInfo(
            model="Raspberry Pi 5 Model B Rev 1.1",
            revision="e04171",
            cpu_temperature=46.6,
            memory_total="15.8GB",
            memory_used="2.1GB",
            storage=[storage],
            gpio_usage={"614": "fan_control", "573": "argon_button"},
            cooling_active=True,
            case_type="Argon Neo V5",
            fan_speed=65
        )

        # Test that hardware is frozen
        with pytest.raises(AttributeError):
            hardware.model = "Pi 4B"  # type: ignore

    def test_network_interface_immutability(self) -> None:
        """Test that NetworkInterface is immutable."""
        interface = NetworkInterface(
            name="eth0",
            ip="192.168.1.100",
            status=NetworkStatus.UP,
            speed="1000Mbps",
            ssid=None,
            signal_strength=None
        )

        # Test that interface is frozen
        with pytest.raises(AttributeError):
            interface.ip = "192.168.1.101"  # type: ignore

    def test_software_info_immutability(self) -> None:
        """Test that SoftwareInfo is immutable."""
        software = SoftwareInfo(
            os_name="Debian GNU/Linux",
            os_version="12 (bookworm)",
            kernel="6.1.0-rpi7-rpi-v8",
            python_version="3.13.5",
            python_path="/usr/bin/python3",
            docker_version="28.3.2",
            docker_status=ServiceStatus.RUNNING,
            retropie_version="4.8.5",
            retropie_status=ServiceStatus.STOPPED
        )

        # Test that software is frozen
        with pytest.raises(AttributeError):
            software.os_name = "Ubuntu"  # type: ignore

    def test_system_service_immutability(self) -> None:
        """Test that SystemService is immutable."""
        service = SystemService(
            name="docker.service",
            status=ServiceStatus.RUNNING,
            enabled=True,
            description="Docker Application Container Engine"
        )

        # Test that service is frozen
        with pytest.raises(AttributeError):
            service.status = ServiceStatus.STOPPED  # type: ignore


    def test_system_note_immutability(self) -> None:
        """Test that SystemNote is immutable."""
        note = SystemNote(
            date="2025-07-17T16:50:00",
            action="install_mealie",
            description="Installed Mealie recipe manager via Docker on port 9925",
            user="nbhansen"
        )

        # Test that note is frozen
        with pytest.raises(AttributeError):
            note.description = "Updated description"  # type: ignore

    def test_network_status_enum(self) -> None:
        """Test NetworkStatus enum has expected values."""
        assert NetworkStatus.UP.value == "up"
        assert NetworkStatus.DOWN.value == "down"
        assert NetworkStatus.UNKNOWN.value == "unknown"

    def test_storage_device_immutability(self) -> None:
        """Test that StorageDevice is immutable."""
        storage = StorageDevice(
            device="/dev/sda1",
            mount="/",
            size="500GB",
            used="45GB",
            filesystem_type="ext4"
        )

        # Test that storage is frozen
        with pytest.raises(AttributeError):
            storage.size = "1TB"  # type: ignore

    def test_v2_system_state_with_extended_schema(self) -> None:
        """Test SystemState with v2.0 schema extensions."""
        hardware = HardwareInfo(
            model="Raspberry Pi 5 Model B Rev 1.1",
            revision="e04171",
            cpu_temperature=46.6,
            memory_total="15.8GB",
            memory_used="2.1GB",
            storage=[
                StorageDevice(
                    device="/dev/sda1",
                    mount="/",
                    size="500GB",
                    used="45GB",
                    filesystem_type="ext4"
                )
            ],
            gpio_usage={"614": "fan_control"},
            cooling_active=True,
            case_type="Argon Neo V5",
            fan_speed=65
        )

        network = [
            NetworkInterface(
                name="eth0",
                ip="192.168.1.100",
                status=NetworkStatus.UP,
                speed="1000Mbps",
                ssid=None,
                signal_strength=None
            )
        ]

        software = SoftwareInfo(
            os_name="Debian GNU/Linux",
            os_version="12 (bookworm)",
            kernel="6.1.0-rpi7-rpi-v8",
            python_version="3.13.5",
            python_path="/usr/bin/python3",
            docker_version="28.3.2",
            docker_status=ServiceStatus.RUNNING,
            retropie_version="4.8.5",
            retropie_status=ServiceStatus.STOPPED
        )

        services = [
            SystemService(
                name="docker.service",
                status=ServiceStatus.RUNNING,
                enabled=True,
                description="Docker Application Container Engine"
            )
        ]

        notes = [
            SystemNote(
                date="2025-07-17T16:50:00",
                action="install_mealie",
                description="Installed Mealie recipe manager via Docker on port 9925",
                user="nbhansen"
            )
        ]

        state = SystemState(
            schema_version="2.0",
            last_updated="2025-07-17T16:56:11",
            system={"hostname": "raspberrypi", "uptime": "2 days, 14:23:45"},
            emulators={"installed": ["mupen64plus"], "preferred": {"n64": "mupen64plus"}},
            controllers=[],
            roms={"systems": [], "counts": {}},
            custom_configs=[],
            known_issues=[],
            hardware=hardware,
            network=network,
            software=software,
            services=services,
            notes=notes
        )

        # Test that state is frozen
        with pytest.raises(AttributeError):
            state.schema_version = "1.0"  # type: ignore

        # Test that v2.0 fields are accessible
        assert state.hardware.model == "Raspberry Pi 5 Model B Rev 1.1"
        assert len(state.network) == 1
        assert state.network[0].name == "eth0"
        assert state.software.os_name == "Debian GNU/Linux"
        assert len(state.services) == 1
        assert state.services[0].name == "docker.service"
        assert len(state.notes) == 1
        assert state.notes[0].action == "install_mealie"


class TestSchemaVersionMigration:
    """Test cases for schema version migration logic."""

    def test_v1_to_v2_migration(self) -> None:
        """Test migration from v1.0 to v2.0 schema."""
        # Create v1.0 state
        v1_state = SystemState(
            schema_version="1.0",
            last_updated="2025-07-17T16:56:11",
            system={"hostname": "raspberrypi", "cpu_temperature": 46.6},
            emulators={"installed": ["mupen64plus"], "preferred": {"n64": "mupen64plus"}},
            controllers=[{"type": "xbox", "device": "/dev/input/js0", "configured": True}],
            roms={"systems": ["n64"], "counts": {"n64": 45}},
            custom_configs=["shaders"],
            known_issues=["audio crackling"],
        )

        # Migrate to v2.0
        v2_state = v1_state.migrate_to_v2()

        # Verify migration
        assert v2_state.schema_version == "2.0"
        assert v2_state.last_updated == v1_state.last_updated
        assert v2_state.system == v1_state.system
        assert v2_state.emulators == v1_state.emulators
        assert v2_state.controllers == v1_state.controllers
        assert v2_state.roms == v1_state.roms
        assert v2_state.custom_configs == v1_state.custom_configs
        assert v2_state.known_issues == v1_state.known_issues

        # Verify v2.0 fields are initialized as None
        assert v2_state.hardware is None
        assert v2_state.network is None
        assert v2_state.software is None
        assert v2_state.services is None
        assert v2_state.notes is None

    def test_v2_state_already_v2(self) -> None:
        """Test that v2.0 state returns itself when migrated."""
        v2_state = SystemState(
            schema_version="2.0",
            last_updated="2025-07-17T16:56:11",
            system={"hostname": "raspberrypi"},
            emulators={"installed": [], "preferred": {}},
            controllers=[],
            roms={"systems": [], "counts": {}},
            custom_configs=[],
            known_issues=[],
            hardware=None,
            network=None,
            software=None,
            services=None,
            notes=None,
        )

        # Migration should return the same state
        migrated_state = v2_state.migrate_to_v2()
        assert migrated_state is v2_state

    def test_unknown_schema_version_raises_error(self) -> None:
        """Test that unknown schema version raises an error."""
        future_state = SystemState(
            schema_version="3.0",
            last_updated="2025-07-17T16:56:11",
            system={"hostname": "raspberrypi"},
            emulators={"installed": [], "preferred": {}},
            controllers=[],
            roms={"systems": [], "counts": {}},
            custom_configs=[],
            known_issues=[],
        )

        with pytest.raises(ValueError, match="Unsupported schema version"):
            future_state.migrate_to_v2()

    def test_migration_preserves_immutability(self) -> None:
        """Test that migration preserves immutability."""
        v1_state = SystemState(
            schema_version="1.0",
            last_updated="2025-07-17T16:56:11",
            system={"hostname": "raspberrypi"},
            emulators={"installed": [], "preferred": {}},
            controllers=[],
            roms={"systems": [], "counts": {}},
            custom_configs=[],
            known_issues=[],
        )

        v2_state = v1_state.migrate_to_v2()

        # Test that migrated state is frozen
        with pytest.raises(AttributeError):
            v2_state.schema_version = "3.0"  # type: ignore

    def test_json_serialization_after_migration(self) -> None:
        """Test that JSON serialization works correctly after migration."""
        v1_state = SystemState(
            schema_version="1.0",
            last_updated="2025-07-17T16:56:11",
            system={"hostname": "raspberrypi"},
            emulators={"installed": ["mupen64plus"], "preferred": {"n64": "mupen64plus"}},
            controllers=[],
            roms={"systems": [], "counts": {}},
            custom_configs=[],
            known_issues=[],
        )

        v2_state = v1_state.migrate_to_v2()
        json_str = v2_state.to_json()

        # Verify JSON structure
        import json
        data = json.loads(json_str)
        assert data["schema_version"] == "2.0"
        assert data["last_updated"] == v1_state.last_updated
        assert data["system"] == v1_state.system
        assert data["emulators"] == v1_state.emulators

        # v2.0 fields should not be in JSON if they're None
        assert "hardware" not in data
        assert "network" not in data
        assert "software" not in data
        assert "services" not in data
        assert "notes" not in data

        # Test round-trip
        recovered_state = SystemState.from_json(json_str)
        assert recovered_state.schema_version == "2.0"
        assert recovered_state.system == v1_state.system
