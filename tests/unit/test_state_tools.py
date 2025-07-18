"""Unit tests for StateTools implementation."""

from unittest.mock import Mock

import pytest
from mcp.types import TextContent

from retromcp.config import RetroPieConfig
from retromcp.domain.models import HardwareInfo
from retromcp.domain.models import NetworkInterface
from retromcp.domain.models import NetworkStatus
from retromcp.domain.models import ServiceStatus
from retromcp.domain.models import SoftwareInfo
from retromcp.domain.models import StateAction
from retromcp.domain.models import StateManagementResult
from retromcp.domain.models import StorageDevice
from retromcp.domain.models import SystemState
from retromcp.tools.state_tools import StateTools


class TestStateTools:
    """Test cases for StateTools class."""

    @pytest.fixture
    def mock_container(self, test_config: RetroPieConfig) -> Mock:
        """Provide mocked container with use cases."""
        mock = Mock()
        mock.manage_state_use_case = Mock()
        mock.config = test_config
        return mock

    @pytest.fixture
    def test_config(self) -> RetroPieConfig:
        """Provide test configuration."""
        from retromcp.discovery import RetroPiePaths

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
    def state_tools(self, mock_container: Mock) -> StateTools:
        """Provide StateTools instance with mocked dependencies."""
        return StateTools(mock_container)

    def test_get_tools(self, state_tools: StateTools) -> None:
        """Test that manage_state tool is returned."""
        tools = state_tools.get_tools()

        assert len(tools) == 1
        tool = tools[0]
        assert tool.name == "manage_state"
        assert "persistent system state" in tool.description

        # Check input schema
        assert tool.inputSchema["type"] == "object"
        assert "action" in tool.inputSchema["properties"]
        assert tool.inputSchema["required"] == ["action"]

        # Check action enum
        action_enum = tool.inputSchema["properties"]["action"]["enum"]
        assert "load" in action_enum
        assert "save" in action_enum
        assert "update" in action_enum
        assert "compare" in action_enum

    @pytest.mark.asyncio
    async def test_handle_load_action(
        self, state_tools: StateTools, mock_container: Mock
    ) -> None:
        """Test handling load action."""
        sample_state = SystemState(
            schema_version="1.0",
            last_updated="2025-07-15T12:00:00Z",
            system={"hostname": "retropie"},
            emulators={"installed": ["mupen64plus"], "preferred": {}},
            controllers=[],
            roms={"systems": [], "counts": {}},
            custom_configs=[],
            known_issues=[],
        )

        mock_container.manage_state_use_case.execute.return_value = (
            StateManagementResult(
                success=True,
                action=StateAction.LOAD,
                message="State loaded successfully",
                state=sample_state,
            )
        )

        result = await state_tools.handle_tool_call("manage_state", {"action": "load"})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "State loaded successfully" in result[0].text
        assert "retropie" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_save_action(
        self, state_tools: StateTools, mock_container: Mock
    ) -> None:
        """Test handling save action."""
        mock_container.manage_state_use_case.execute.return_value = (
            StateManagementResult(
                success=True,
                action=StateAction.SAVE,
                message="State saved successfully",
            )
        )

        result = await state_tools.handle_tool_call("manage_state", {"action": "save"})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "State saved successfully" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_save_action_with_force_scan(
        self, state_tools: StateTools, mock_container: Mock
    ) -> None:
        """Test handling save action with force_scan."""
        mock_container.manage_state_use_case.execute.return_value = (
            StateManagementResult(
                success=True,
                action=StateAction.SAVE,
                message="State saved successfully",
            )
        )

        result = await state_tools.handle_tool_call(
            "manage_state", {"action": "save", "force_scan": True}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "State saved successfully" in result[0].text

        # Verify force_scan was passed to the use case
        call_args = mock_container.manage_state_use_case.execute.call_args[0][0]
        assert call_args.force_scan is True

    @pytest.mark.asyncio
    async def test_handle_update_action(
        self, state_tools: StateTools, mock_container: Mock
    ) -> None:
        """Test handling update action."""
        mock_container.manage_state_use_case.execute.return_value = (
            StateManagementResult(
                success=True,
                action=StateAction.UPDATE,
                message="Field updated successfully",
            )
        )

        result = await state_tools.handle_tool_call(
            "manage_state",
            {"action": "update", "path": "system.hostname", "value": "new-hostname"},
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Field updated successfully" in result[0].text

        # Verify path and value were passed to the use case
        call_args = mock_container.manage_state_use_case.execute.call_args[0][0]
        assert call_args.path == "system.hostname"
        assert call_args.value == "new-hostname"

    @pytest.mark.asyncio
    async def test_handle_compare_action(
        self, state_tools: StateTools, mock_container: Mock
    ) -> None:
        """Test handling compare action."""
        diff = {
            "added": {"system.new_field": "value"},
            "changed": {"system.hostname": {"old": "old-name", "new": "new-name"}},
            "removed": {},
        }

        mock_container.manage_state_use_case.execute.return_value = (
            StateManagementResult(
                success=True,
                action=StateAction.COMPARE,
                message="Comparison complete",
                diff=diff,
            )
        )

        result = await state_tools.handle_tool_call(
            "manage_state", {"action": "compare"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Comparison complete" in result[0].text
        assert "Added fields:" in result[0].text
        assert "Changed fields:" in result[0].text
        assert "system.new_field" in result[0].text
        assert "system.hostname" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_compare_action_no_differences(
        self, state_tools: StateTools, mock_container: Mock
    ) -> None:
        """Test handling compare action with no differences."""
        diff = {"added": {}, "changed": {}, "removed": {}}

        mock_container.manage_state_use_case.execute.return_value = (
            StateManagementResult(
                success=True,
                action=StateAction.COMPARE,
                message="Comparison complete",
                diff=diff,
            )
        )

        result = await state_tools.handle_tool_call(
            "manage_state", {"action": "compare"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "No differences found" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_invalid_action(self, state_tools: StateTools) -> None:
        """Test handling invalid action."""
        result = await state_tools.handle_tool_call(
            "manage_state", {"action": "invalid"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Invalid action" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_missing_action(self, state_tools: StateTools) -> None:
        """Test handling missing action."""
        result = await state_tools.handle_tool_call("manage_state", {})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Action is required" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_update_missing_path(self, state_tools: StateTools) -> None:
        """Test handling update action with missing path."""
        result = await state_tools.handle_tool_call(
            "manage_state", {"action": "update"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Path and value are required" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_update_missing_value(self, state_tools: StateTools) -> None:
        """Test handling update action with missing value."""
        result = await state_tools.handle_tool_call(
            "manage_state", {"action": "update", "path": "system.hostname"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Path and value are required" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_error_from_use_case(
        self, state_tools: StateTools, mock_container: Mock
    ) -> None:
        """Test handling error from use case."""
        mock_container.manage_state_use_case.execute.return_value = (
            StateManagementResult(
                success=False, action=StateAction.LOAD, message="File not found"
            )
        )

        result = await state_tools.handle_tool_call("manage_state", {"action": "load"})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "File not found" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_exception(
        self, state_tools: StateTools, mock_container: Mock
    ) -> None:
        """Test handling exception from use case."""
        mock_container.manage_state_use_case.execute.side_effect = Exception(
            "Database error"
        )

        result = await state_tools.handle_tool_call("manage_state", {"action": "load"})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Error" in result[0].text
        assert "Database error" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_unknown_tool(self, state_tools: StateTools) -> None:
        """Test handling unknown tool call."""
        result = await state_tools.handle_tool_call("unknown_tool", {})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Unknown tool" in result[0].text

    # Test uncovered validation error paths (lines 119-120, 122-124, 126-128)
    @pytest.mark.asyncio
    async def test_handle_watch_missing_path(self, state_tools: StateTools) -> None:
        """Test handling watch action with missing path."""
        result = await state_tools.handle_tool_call("manage_state", {"action": "watch"})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Path is required for watch action" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_import_missing_state_data(
        self, state_tools: StateTools
    ) -> None:
        """Test handling import action with missing state_data."""
        result = await state_tools.handle_tool_call(
            "manage_state", {"action": "import"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "state_data is required for import action" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_diff_missing_other_state_data(
        self, state_tools: StateTools
    ) -> None:
        """Test handling diff action with missing other_state_data."""
        result = await state_tools.handle_tool_call("manage_state", {"action": "diff"})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "other_state_data is required for diff action" in result[0].text

    # Test enhanced display formatting for system info (lines 169-171, 175-184, 188-197, 201-203, 206-211)
    @pytest.mark.asyncio
    async def test_load_with_cpu_temperature_formatting(
        self, state_tools: StateTools, mock_container: Mock
    ) -> None:
        """Test load action with CPU temperature formatting."""
        sample_state = SystemState(
            schema_version="1.0",
            last_updated="2025-07-15T12:00:00Z",
            system={
                "hostname": "retropie",
                "cpu_temperature": 65.5,  # This will trigger temperature formatting
            },
            emulators={"installed": [], "preferred": {}},
            controllers=[],
            roms={"systems": [], "counts": {}},
            custom_configs=[],
            known_issues=[],
        )

        mock_container.manage_state_use_case.execute.return_value = (
            StateManagementResult(
                success=True,
                action=StateAction.LOAD,
                message="State loaded successfully",
                state=sample_state,
            )
        )

        result = await state_tools.handle_tool_call("manage_state", {"action": "load"})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "CPU Temperature: 65.5°C" in result[0].text
        assert "🌡️" in result[0].text  # Temperature emoji

    @pytest.mark.asyncio
    async def test_load_with_memory_formatting(
        self, state_tools: StateTools, mock_container: Mock
    ) -> None:
        """Test load action with memory formatting."""
        sample_state = SystemState(
            schema_version="1.0",
            last_updated="2025-07-15T12:00:00Z",
            system={
                "hostname": "retropie",
                "memory_total": 4294967296,  # 4GB
                "memory_used": 2147483648,  # 2GB
                "memory_free": 2147483648,  # 2GB
            },
            emulators={"installed": [], "preferred": {}},
            controllers=[],
            roms={"systems": [], "counts": {}},
            custom_configs=[],
            known_issues=[],
        )

        mock_container.manage_state_use_case.execute.return_value = (
            StateManagementResult(
                success=True,
                action=StateAction.LOAD,
                message="State loaded successfully",
                state=sample_state,
            )
        )

        result = await state_tools.handle_tool_call("manage_state", {"action": "load"})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Memory: 4.0GB total" in result[0].text
        assert "2.0GB used" in result[0].text
        assert "2.0GB free" in result[0].text
        assert "50.0% used" in result[0].text

    @pytest.mark.asyncio
    async def test_load_with_disk_formatting(
        self, state_tools: StateTools, mock_container: Mock
    ) -> None:
        """Test load action with disk formatting."""
        sample_state = SystemState(
            schema_version="1.0",
            last_updated="2025-07-15T12:00:00Z",
            system={
                "hostname": "retropie",
                "disk_total": 32212254720,  # 30GB
                "disk_used": 16106127360,  # 15GB
                "disk_free": 16106127360,  # 15GB
            },
            emulators={"installed": [], "preferred": {}},
            controllers=[],
            roms={"systems": [], "counts": {}},
            custom_configs=[],
            known_issues=[],
        )

        mock_container.manage_state_use_case.execute.return_value = (
            StateManagementResult(
                success=True,
                action=StateAction.LOAD,
                message="State loaded successfully",
                state=sample_state,
            )
        )

        result = await state_tools.handle_tool_call("manage_state", {"action": "load"})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Storage: 30.0GB total" in result[0].text
        assert "15.0GB used" in result[0].text
        assert "15.0GB free" in result[0].text
        assert "50.0% used" in result[0].text

    @pytest.mark.asyncio
    async def test_load_with_load_average_formatting(
        self, state_tools: StateTools, mock_container: Mock
    ) -> None:
        """Test load action with load average formatting."""
        sample_state = SystemState(
            schema_version="1.0",
            last_updated="2025-07-15T12:00:00Z",
            system={
                "hostname": "retropie",
                "load_average": [0.5, 0.3, 0.1],
            },
            emulators={"installed": [], "preferred": {}},
            controllers=[],
            roms={"systems": [], "counts": {}},
            custom_configs=[],
            known_issues=[],
        )

        mock_container.manage_state_use_case.execute.return_value = (
            StateManagementResult(
                success=True,
                action=StateAction.LOAD,
                message="State loaded successfully",
                state=sample_state,
            )
        )

        result = await state_tools.handle_tool_call("manage_state", {"action": "load"})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Load Average: 0.50, 0.30, 0.10 (1m, 5m, 15m)" in result[0].text

    @pytest.mark.asyncio
    async def test_load_with_uptime_hours_formatting(
        self, state_tools: StateTools, mock_container: Mock
    ) -> None:
        """Test load action with uptime formatting in hours."""
        sample_state = SystemState(
            schema_version="1.0",
            last_updated="2025-07-15T12:00:00Z",
            system={
                "hostname": "retropie",
                "uptime": 7200,  # 2 hours
            },
            emulators={"installed": [], "preferred": {}},
            controllers=[],
            roms={"systems": [], "counts": {}},
            custom_configs=[],
            known_issues=[],
        )

        mock_container.manage_state_use_case.execute.return_value = (
            StateManagementResult(
                success=True,
                action=StateAction.LOAD,
                message="State loaded successfully",
                state=sample_state,
            )
        )

        result = await state_tools.handle_tool_call("manage_state", {"action": "load"})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Uptime: 2.0 hours" in result[0].text

    @pytest.mark.asyncio
    async def test_load_with_uptime_days_formatting(
        self, state_tools: StateTools, mock_container: Mock
    ) -> None:
        """Test load action with uptime formatting in days."""
        sample_state = SystemState(
            schema_version="1.0",
            last_updated="2025-07-15T12:00:00Z",
            system={
                "hostname": "retropie",
                "uptime": 172800,  # 48 hours = 2 days
            },
            emulators={"installed": [], "preferred": {}},
            controllers=[],
            roms={"systems": [], "counts": {}},
            custom_configs=[],
            known_issues=[],
        )

        mock_container.manage_state_use_case.execute.return_value = (
            StateManagementResult(
                success=True,
                action=StateAction.LOAD,
                message="State loaded successfully",
                state=sample_state,
            )
        )

        result = await state_tools.handle_tool_call("manage_state", {"action": "load"})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Uptime: 2.0 days" in result[0].text

    # Test enhanced display formatting for emulators (lines 224, 228)
    @pytest.mark.asyncio
    async def test_load_with_emulators_preferred_formatting(
        self, state_tools: StateTools, mock_container: Mock
    ) -> None:
        """Test load action with emulators preferred formatting."""
        sample_state = SystemState(
            schema_version="1.0",
            last_updated="2025-07-15T12:00:00Z",
            system={"hostname": "retropie"},
            emulators={
                "installed": ["mupen64plus", "pcsx2"],
                "preferred": {"n64": "mupen64plus"},
            },
            controllers=[],
            roms={"systems": [], "counts": {}},
            custom_configs=[],
            known_issues=[],
        )

        mock_container.manage_state_use_case.execute.return_value = (
            StateManagementResult(
                success=True,
                action=StateAction.LOAD,
                message="State loaded successfully",
                state=sample_state,
            )
        )

        result = await state_tools.handle_tool_call("manage_state", {"action": "load"})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "mupen64plus (preferred for: n64)" in result[0].text
        assert "pcsx2" in result[0].text

    @pytest.mark.asyncio
    async def test_load_with_no_emulators_formatting(
        self, state_tools: StateTools, mock_container: Mock
    ) -> None:
        """Test load action with no emulators formatting."""
        sample_state = SystemState(
            schema_version="1.0",
            last_updated="2025-07-15T12:00:00Z",
            system={"hostname": "retropie"},
            emulators={"installed": [], "preferred": {}},
            controllers=[],
            roms={"systems": [], "counts": {}},
            custom_configs=[],
            known_issues=[],
        )

        mock_container.manage_state_use_case.execute.return_value = (
            StateManagementResult(
                success=True,
                action=StateAction.LOAD,
                message="State loaded successfully",
                state=sample_state,
            )
        )

        result = await state_tools.handle_tool_call("manage_state", {"action": "load"})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "No emulators installed" in result[0].text

    # Test enhanced display formatting for controllers (lines 234-243)
    @pytest.mark.asyncio
    async def test_load_with_controllers_formatting(
        self, state_tools: StateTools, mock_container: Mock
    ) -> None:
        """Test load action with controllers formatting."""
        sample_state = SystemState(
            schema_version="1.0",
            last_updated="2025-07-15T12:00:00Z",
            system={"hostname": "retropie"},
            emulators={"installed": [], "preferred": {}},
            controllers=[
                {
                    "type": "xbox_controller",
                    "device": "/dev/input/js0",
                    "configured": True,
                },
                {
                    "type": "generic_gamepad",
                    "device": "/dev/input/js1",
                    "configured": False,
                },
            ],
            roms={"systems": [], "counts": {}},
            custom_configs=[],
            known_issues=[],
        )

        mock_container.manage_state_use_case.execute.return_value = (
            StateManagementResult(
                success=True,
                action=StateAction.LOAD,
                message="State loaded successfully",
                state=sample_state,
            )
        )

        result = await state_tools.handle_tool_call("manage_state", {"action": "load"})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Detected Controllers: 2" in result[0].text
        assert "Xbox Controller" in result[0].text
        assert "Generic Gamepad" in result[0].text
        assert "js0" in result[0].text
        assert "js1" in result[0].text
        assert "Configured" in result[0].text
        assert "Not configured" in result[0].text

    # Test enhanced display formatting for ROMs (lines 254-263)
    @pytest.mark.asyncio
    async def test_load_with_roms_formatting(
        self, state_tools: StateTools, mock_container: Mock
    ) -> None:
        """Test load action with ROMs formatting."""
        sample_state = SystemState(
            schema_version="1.0",
            last_updated="2025-07-15T12:00:00Z",
            system={"hostname": "retropie"},
            emulators={"installed": [], "preferred": {}},
            controllers=[],
            roms={
                "systems": ["n64", "nes", "snes"],
                "counts": {"n64": 25, "nes": 150, "snes": 75},
            },
            custom_configs=[],
            known_issues=[],
        )

        mock_container.manage_state_use_case.execute.return_value = (
            StateManagementResult(
                success=True,
                action=StateAction.LOAD,
                message="State loaded successfully",
                state=sample_state,
            )
        )

        result = await state_tools.handle_tool_call("manage_state", {"action": "load"})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Total ROMs: 250 across 3 systems" in result[0].text
        assert "NES: 150 ROMs" in result[0].text  # Sorted by count
        assert "SNES: 75 ROMs" in result[0].text
        assert "N64: 25 ROMs" in result[0].text

    # Test enhanced display formatting for custom configs and issues (lines 269-280)
    @pytest.mark.asyncio
    async def test_load_with_custom_configs_and_issues_formatting(
        self, state_tools: StateTools, mock_container: Mock
    ) -> None:
        """Test load action with custom configs and issues formatting."""
        sample_state = SystemState(
            schema_version="1.0",
            last_updated="2025-07-15T12:00:00Z",
            system={"hostname": "retropie"},
            emulators={"installed": [], "preferred": {}},
            controllers=[],
            roms={"systems": [], "counts": {}},
            custom_configs=["mupen64plus.cfg", "retroarch.cfg"],
            known_issues=["Audio lag in N64 games", "Controller disconnect issue"],
        )

        mock_container.manage_state_use_case.execute.return_value = (
            StateManagementResult(
                success=True,
                action=StateAction.LOAD,
                message="State loaded successfully",
                state=sample_state,
            )
        )

        result = await state_tools.handle_tool_call("manage_state", {"action": "load"})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Custom Configurations: 2" in result[0].text
        assert "mupen64plus.cfg" in result[0].text
        assert "retroarch.cfg" in result[0].text
        assert "Known Issues: 2" in result[0].text
        assert "Audio lag in N64 games" in result[0].text
        assert "Controller disconnect issue" in result[0].text

    # Test v2.0 enhanced fields display (lines 284-295, 298-306, 309-317)
    @pytest.mark.asyncio
    async def test_load_with_v2_hardware_formatting(
        self, state_tools: StateTools, mock_container: Mock
    ) -> None:
        """Test load action with v2.0 hardware formatting."""
        storage_device = StorageDevice(
            device="/dev/sda1",
            mount="/",
            size="32GB",
            used="15GB",
            filesystem_type="ext4",
        )

        hardware_info = HardwareInfo(
            model="Raspberry Pi 4",
            revision="c03114",
            cpu_temperature=55.2,
            memory_total="4GB",
            memory_used="2GB",
            storage=[storage_device],
            gpio_usage={"18": "LED", "19": "Button"},
            cooling_active=True,
            case_type="Official",
            fan_speed=2000,
        )

        sample_state = SystemState(
            schema_version="2.0",
            last_updated="2025-07-15T12:00:00Z",
            system={"hostname": "retropie"},
            emulators={"installed": [], "preferred": {}},
            controllers=[],
            roms={"systems": [], "counts": {}},
            custom_configs=[],
            known_issues=[],
            hardware=hardware_info,
        )

        mock_container.manage_state_use_case.execute.return_value = (
            StateManagementResult(
                success=True,
                action=StateAction.LOAD,
                message="State loaded successfully",
                state=sample_state,
            )
        )

        result = await state_tools.handle_tool_call("manage_state", {"action": "load"})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Hardware Details:" in result[0].text
        assert "Model: Raspberry Pi 4" in result[0].text
        assert "Revision: c03114" in result[0].text
        assert "Storage Devices: 1" in result[0].text
        assert "/dev/sda1: /" in result[0].text
        assert "GPIO Usage: 2 pins" in result[0].text
        assert "Cooling Active: Yes" in result[0].text

    @pytest.mark.asyncio
    async def test_load_with_v2_network_formatting(
        self, state_tools: StateTools, mock_container: Mock
    ) -> None:
        """Test load action with v2.0 network formatting."""
        network_interfaces = [
            NetworkInterface(
                name="wlan0",
                ip="192.168.1.100",
                status=NetworkStatus.UP,
                speed="54Mbps",
                ssid="HomeWiFi",
                signal_strength=75,
            ),
            NetworkInterface(
                name="eth0",
                ip="192.168.1.101",
                status=NetworkStatus.DOWN,
                speed="1Gbps",
            ),
        ]

        sample_state = SystemState(
            schema_version="2.0",
            last_updated="2025-07-15T12:00:00Z",
            system={"hostname": "retropie"},
            emulators={"installed": [], "preferred": {}},
            controllers=[],
            roms={"systems": [], "counts": {}},
            custom_configs=[],
            known_issues=[],
            network=network_interfaces,
        )

        mock_container.manage_state_use_case.execute.return_value = (
            StateManagementResult(
                success=True,
                action=StateAction.LOAD,
                message="State loaded successfully",
                state=sample_state,
            )
        )

        result = await state_tools.handle_tool_call("manage_state", {"action": "load"})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Network Interfaces:" in result[0].text
        assert "wlan0 (192.168.1.100)" in result[0].text
        assert "eth0 (192.168.1.101)" in result[0].text
        assert "Speed: 54Mbps" in result[0].text
        assert "Speed: 1Gbps" in result[0].text
        assert "WiFi: HomeWiFi" in result[0].text

    @pytest.mark.asyncio
    async def test_load_with_v2_software_formatting(
        self, state_tools: StateTools, mock_container: Mock
    ) -> None:
        """Test load action with v2.0 software formatting."""
        software_info = SoftwareInfo(
            os_name="Raspberry Pi OS",
            os_version="11 (bullseye)",
            kernel="5.15.0-rpi",
            python_version="3.9.2",
            python_path="/usr/bin/python3",
            docker_version="20.10.21",
            docker_status=ServiceStatus.RUNNING,
            retropie_version="4.8.0",
            retropie_status=ServiceStatus.RUNNING,
        )

        sample_state = SystemState(
            schema_version="2.0",
            last_updated="2025-07-15T12:00:00Z",
            system={"hostname": "retropie"},
            emulators={"installed": [], "preferred": {}},
            controllers=[],
            roms={"systems": [], "counts": {}},
            custom_configs=[],
            known_issues=[],
            software=software_info,
        )

        mock_container.manage_state_use_case.execute.return_value = (
            StateManagementResult(
                success=True,
                action=StateAction.LOAD,
                message="State loaded successfully",
                state=sample_state,
            )
        )

        result = await state_tools.handle_tool_call("manage_state", {"action": "load"})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Software Environment:" in result[0].text
        assert "OS: Raspberry Pi OS 11 (bullseye)" in result[0].text
        assert "Kernel: 5.15.0-rpi" in result[0].text
        assert "Python: 3.9.2" in result[0].text
        assert "Docker: 20.10.21" in result[0].text
        assert "RetroPie: 4.8.0" in result[0].text

    # Test specific response formatting for actions (lines 321-325, 329-330, 336-338, 372-375)
    @pytest.mark.asyncio
    async def test_handle_export_action_formatting(
        self, state_tools: StateTools, mock_container: Mock
    ) -> None:
        """Test handling export action with formatting."""
        exported_json = '{"system": {"hostname": "retropie"}}'

        mock_container.manage_state_use_case.execute.return_value = (
            StateManagementResult(
                success=True,
                action=StateAction.EXPORT,
                message="Export completed successfully",
                exported_data=exported_json,
            )
        )

        result = await state_tools.handle_tool_call(
            "manage_state", {"action": "export"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "State exported successfully!" in result[0].text
        assert "Exported JSON Data:" in result[0].text
        assert "```json" in result[0].text
        assert exported_json in result[0].text

    @pytest.mark.asyncio
    async def test_handle_import_action_formatting(
        self, state_tools: StateTools, mock_container: Mock
    ) -> None:
        """Test handling import action with formatting."""
        mock_container.manage_state_use_case.execute.return_value = (
            StateManagementResult(
                success=True,
                action=StateAction.IMPORT,
                message="Import completed successfully",
            )
        )

        result = await state_tools.handle_tool_call(
            "manage_state",
            {"action": "import", "state_data": '{"system": {"hostname": "test"}}'},
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "State imported successfully!" in result[0].text
        assert (
            "The system state has been restored from the provided backup."
            in result[0].text
        )

    @pytest.mark.asyncio
    async def test_handle_watch_action_formatting(
        self, state_tools: StateTools, mock_container: Mock
    ) -> None:
        """Test handling watch action with formatting."""
        mock_container.manage_state_use_case.execute.return_value = (
            StateManagementResult(
                success=True,
                action=StateAction.WATCH,
                message="Watch started successfully",
                watch_value="test-hostname",
            )
        )

        result = await state_tools.handle_tool_call(
            "manage_state", {"action": "watch", "path": "system.hostname"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Watching field: system.hostname" in result[0].text
        assert "Current value: test-hostname" in result[0].text
        assert "Monitor will track changes to this field." in result[0].text

    @pytest.mark.asyncio
    async def test_handle_diff_action_with_removed_fields_formatting(
        self, state_tools: StateTools, mock_container: Mock
    ) -> None:
        """Test handling diff action with removed fields formatting."""
        diff = {
            "added": {},
            "changed": {},
            "removed": {"system.old_field": "old_value", "emulators.removed": "data"},
        }

        mock_container.manage_state_use_case.execute.return_value = (
            StateManagementResult(
                success=True,
                action=StateAction.DIFF,
                message="Diff complete",
                diff=diff,
            )
        )

        result = await state_tools.handle_tool_call(
            "manage_state",
            {"action": "diff", "other_state_data": '{"system": {"hostname": "test"}}'},
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Configuration drift detected:" in result[0].text
        assert "- Removed fields:" in result[0].text
        assert "system.old_field: old_value" in result[0].text
        assert "emulators.removed: data" in result[0].text
