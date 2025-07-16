"""Unit tests for HardwareMonitoringTools implementation."""

from unittest.mock import Mock

import pytest
from mcp.types import TextContent

from retromcp.config import RetroPieConfig
from retromcp.discovery import RetroPiePaths
from retromcp.domain.models import CommandResult
from retromcp.tools.hardware_monitoring_tools import HardwareMonitoringTools


class TestHardwareMonitoringTools:
    """Test cases for HardwareMonitoringTools class."""

    @pytest.fixture
    def mock_container(self, test_config: RetroPieConfig) -> Mock:
        """Provide mocked container."""
        mock = Mock()
        mock.retropie_client = Mock()
        mock.retropie_client.execute_command = Mock()
        mock.config = test_config
        return mock

    @pytest.fixture
    def test_config(self) -> RetroPieConfig:
        """Provide test configuration."""
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
            password="test_password",  # noqa: S106 # Test fixture, not real password
            port=22,
            paths=paths,
        )

    @pytest.fixture
    def hardware_monitoring_tools(
        self, mock_container: Mock
    ) -> HardwareMonitoringTools:
        """Provide HardwareMonitoringTools instance with mocked dependencies."""
        return HardwareMonitoringTools(mock_container)

    # Schema and Tool Structure Tests

    def test_get_tools_returns_single_manage_hardware_tool(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test that get_tools returns exactly one manage_hardware tool."""
        tools = hardware_monitoring_tools.get_tools()

        assert len(tools) == 1
        assert tools[0].name == "manage_hardware"
        assert "hardware monitoring" in tools[0].description.lower()

    def test_manage_hardware_tool_schema_validation(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test that manage_hardware tool has proper schema with all components and actions."""
        tools = hardware_monitoring_tools.get_tools()
        tool = tools[0]

        # Check required properties
        assert "component" in tool.inputSchema["properties"]
        assert "action" in tool.inputSchema["properties"]
        assert tool.inputSchema["required"] == ["component", "action"]

        # Check component enum
        component_enum = tool.inputSchema["properties"]["component"]["enum"]
        expected_components = ["temperature", "fan", "power", "gpio", "errors", "all"]
        assert set(component_enum) == set(expected_components)

    # Temperature Component Tests

    @pytest.mark.asyncio
    async def test_manage_hardware_temperature_check_normal(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test temperature check with normal readings."""
        # Mock temperature command results
        hardware_monitoring_tools.container.retropie_client.execute_command.side_effect = [
            CommandResult(
                command="vcgencmd measure_temp",
                exit_code=0,
                stdout="temp=55.4'C",
                stderr="",
                success=True,
                execution_time=0.1,
            ),
            CommandResult(
                command="vcgencmd measure_temp gpu",
                exit_code=0,
                stdout="temp=52.1'C",
                stderr="",
                success=True,
                execution_time=0.1,
            ),
            CommandResult(
                command="vcgencmd get_throttled",
                exit_code=0,
                stdout="throttled=0x0",
                stderr="",
                success=True,
                execution_time=0.1,
            ),
        ]

        # Execute temperature check
        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware",
            {
                "component": "temperature",
                "action": "check",
            },
        )

        # Verify result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "55.4°C" in result[0].text
        assert "52.1°C" in result[0].text
        assert "✅ NORMAL" in result[0].text

    @pytest.mark.asyncio
    async def test_manage_hardware_temperature_check_critical(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test temperature check with critical readings."""
        # Mock critical temperature
        hardware_monitoring_tools.container.retropie_client.execute_command.side_effect = [
            CommandResult(
                command="vcgencmd measure_temp",
                exit_code=0,
                stdout="temp=85.7'C",
                stderr="",
                success=True,
                execution_time=0.1,
            ),
            CommandResult(
                command="vcgencmd measure_temp gpu",
                exit_code=0,
                stdout="temp=83.2'C",
                stderr="",
                success=True,
                execution_time=0.1,
            ),
            CommandResult(
                command="vcgencmd get_throttled",
                exit_code=0,
                stdout="throttled=0x50000",
                stderr="",
                success=True,
                execution_time=0.1,
            ),
        ]

        # Execute temperature check
        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware",
            {
                "component": "temperature",
                "action": "check",
            },
        )

        # Verify result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "85.7°C" in result[0].text
        assert "🔥 CRITICAL" in result[0].text
        assert "throttling" in result[0].text.lower()

    # Fan Component Tests

    @pytest.mark.asyncio
    async def test_manage_hardware_fan_check_success(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test fan status check."""
        # Mock fan command results
        hardware_monitoring_tools.container.retropie_client.execute_command.side_effect = [
            CommandResult(
                command="vcgencmd measure_temp",
                exit_code=0,
                stdout="temp=65.2'C",
                stderr="",
                success=True,
                execution_time=0.1,
            ),
            CommandResult(
                command="ls -la /sys/class/thermal/cooling_device*/",
                exit_code=0,
                stdout="total 0\ndrwxr-xr-x 2 root root 0 Jan 1 00:00 .\n-rw-r--r-- 1 root root 4096 Jan 1 00:00 cur_state\n-rw-r--r-- 1 root root 4096 Jan 1 00:00 max_state",
                stderr="",
                success=True,
                execution_time=0.1,
            ),
        ]

        # Execute fan check
        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware",
            {
                "component": "fan",
                "action": "check",
            },
        )

        # Verify result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Fan Control Status" in result[0].text
        assert "65.2°C" in result[0].text

    # Power Component Tests

    @pytest.mark.asyncio
    async def test_manage_hardware_power_check_success(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test power supply check."""
        # Mock power command results
        hardware_monitoring_tools.container.retropie_client.execute_command.side_effect = [
            CommandResult(
                command="vcgencmd get_throttled",
                exit_code=0,
                stdout="throttled=0x0",
                stderr="",
                success=True,
                execution_time=0.1,
            ),
            CommandResult(
                command="dmesg | grep -i 'voltage' | tail -10",
                exit_code=0,
                stdout="",
                stderr="",
                success=True,
                execution_time=0.1,
            ),
        ]

        # Execute power check
        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware",
            {
                "component": "power",
                "action": "check",
            },
        )

        # Verify result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Power Supply Status" in result[0].text
        assert "✅ **HEALTHY**" in result[0].text

    # GPIO Component Tests

    @pytest.mark.asyncio
    async def test_manage_hardware_gpio_check_success(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test GPIO pin status check."""
        # Mock GPIO command results
        hardware_monitoring_tools.container.retropie_client.execute_command.return_value = CommandResult(
            command="gpio readall",
            exit_code=0,
            stdout=" +-----+-----+---------+------+---+---Pi 4---+---+------+---------+-----+-----+\n | BCM | wPi |   Name  | Mode | V | Physical | V | Mode | Name    | wPi | BCM |\n +-----+-----+---------+------+---+----++----+---+------+---------+-----+-----+\n |     |     |    3.3v |      |   |  1 || 2  |   |      | 5v      |     |     |",
            stderr="",
            success=True,
            execution_time=0.2,
        )

        # Execute GPIO check
        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware",
            {
                "component": "gpio",
                "action": "check",
            },
        )

        # Verify result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "GPIO Pin Status" in result[0].text
        assert "Physical" in result[0].text

    @pytest.mark.asyncio
    async def test_manage_hardware_gpio_test_specific_pin(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test specific GPIO pin testing."""
        # Mock GPIO pin test
        hardware_monitoring_tools.container.retropie_client.execute_command.return_value = CommandResult(
            command="gpio read 18",
            exit_code=0,
            stdout="1",
            stderr="",
            success=True,
            execution_time=0.1,
        )

        # Execute GPIO pin test
        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware",
            {
                "component": "gpio",
                "action": "test",
                "pin": 18,
            },
        )

        # Verify result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "GPIO Pin 18" in result[0].text
        assert "HIGH" in result[0].text

    # Errors Component Tests

    @pytest.mark.asyncio
    async def test_manage_hardware_errors_check_success(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test hardware error detection."""
        # Mock error detection commands
        hardware_monitoring_tools.container.retropie_client.execute_command.side_effect = [
            CommandResult(
                command="dmesg | grep -i 'error\\|fail\\|warn' | grep -i 'hardware\\|temp\\|power\\|usb' | tail -10",
                exit_code=0,
                stdout="",
                stderr="",
                success=True,
                execution_time=0.1,
            ),
            CommandResult(
                command="journalctl -p err -n 10 --no-pager",
                exit_code=0,
                stdout="-- No entries --",
                stderr="",
                success=True,
                execution_time=0.1,
            ),
        ]

        # Execute error check
        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware",
            {
                "component": "errors",
                "action": "check",
            },
        )

        # Verify result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Hardware Error Analysis" in result[0].text
        assert "✅ No hardware errors detected" in result[0].text

    # All Component Tests

    @pytest.mark.asyncio
    async def test_manage_hardware_all_check_success(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test comprehensive hardware overview."""
        # Mock all hardware commands
        call_count = [0]

        def mock_execute_command(command, use_sudo=False):
            call_count[0] += 1
            if "measure_temp" in command and "gpu" not in command:
                return CommandResult(command, 0, "temp=65.4'C", "", True, 0.1)
            elif "measure_temp gpu" in command:
                return CommandResult(command, 0, "temp=62.1'C", "", True, 0.1)
            elif "get_throttled" in command:
                return CommandResult(command, 0, "throttled=0x0", "", True, 0.1)
            elif "gpio readall" in command:
                return CommandResult(command, 0, "GPIO table output", "", True, 0.1)
            elif "dmesg" in command:
                return CommandResult(command, 0, "", "", True, 0.1)
            elif "journalctl" in command:
                return CommandResult(command, 0, "-- No entries --", "", True, 0.1)
            else:
                return CommandResult(command, 0, "", "", True, 0.1)

        hardware_monitoring_tools.container.retropie_client.execute_command.side_effect = mock_execute_command

        # Execute comprehensive check
        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware",
            {
                "component": "all",
                "action": "check",
            },
        )

        # Verify result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Hardware System Overview" in result[0].text
        assert "Temperature" in result[0].text
        assert "Power" in result[0].text
        assert "Errors" in result[0].text

    # Error Handling Tests

    @pytest.mark.asyncio
    async def test_invalid_component_error(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test error handling for invalid component."""
        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware",
            {
                "component": "invalid_component",
                "action": "check",
            },
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "invalid component" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_invalid_action_error(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test error handling for invalid action."""
        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware",
            {
                "component": "temperature",
                "action": "invalid_action",
            },
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "invalid action" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_missing_required_parameters(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test error handling for missing required parameters."""
        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware",
            {
                "component": "gpio",
                "action": "test",
                # Missing 'pin' parameter
            },
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "required" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_handle_unknown_tool(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test handling of unknown tool calls."""
        result = await hardware_monitoring_tools.handle_tool_call(
            "unknown_tool",
            {"test": "value"},
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "unknown tool" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_gpio_pin_validation(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test GPIO pin validation."""
        # Test invalid pin number
        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware",
            {
                "component": "gpio",
                "action": "test",
                "pin": 999,
            },
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "invalid pin" in result[0].text.lower()

    def test_inheritance_from_base_tool(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test that HardwareMonitoringTools inherits from BaseTool."""
        from retromcp.tools.base import BaseTool

        assert isinstance(hardware_monitoring_tools, BaseTool)
        assert hasattr(hardware_monitoring_tools, "format_success")
        assert hasattr(hardware_monitoring_tools, "format_error")
        assert hasattr(hardware_monitoring_tools, "format_info")
