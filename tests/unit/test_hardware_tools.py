"""Unit tests for HardwareTools implementation."""

from unittest.mock import Mock

import pytest
from mcp.types import TextContent

from retromcp.config import RetroPieConfig
from retromcp.discovery import RetroPiePaths
from retromcp.tools.hardware_tools import HardwareTools


class TestHardwareTools:
    """Test cases for HardwareTools class."""

    @pytest.fixture
    def mock_ssh_handler(self) -> Mock:
        """Provide mocked SSH handler."""
        mock = Mock()
        mock.execute_command = Mock()
        # Reset the mock for each test
        mock.execute_command.reset_mock()
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
    def hardware_tools(
        self, mock_ssh_handler: Mock, test_config: RetroPieConfig
    ) -> HardwareTools:
        """Provide HardwareTools instance with mocked dependencies."""
        return HardwareTools(mock_ssh_handler, test_config)

    def test_get_tools(self, hardware_tools: HardwareTools) -> None:
        """Test that all expected tools are returned."""
        tools = hardware_tools.get_tools()

        assert len(tools) == 5
        tool_names = [tool.name for tool in tools]

        expected_tools = [
            "check_temperatures",
            "monitor_fan_control",
            "check_power_supply",
            "inspect_hardware_errors",
            "check_gpio_status",
        ]

        for expected_tool in expected_tools:
            assert expected_tool in tool_names

    def test_tool_schemas(self, hardware_tools: HardwareTools) -> None:
        """Test that tool schemas are properly defined."""
        tools = hardware_tools.get_tools()
        tool_dict = {tool.name: tool for tool in tools}

        # Check temperatures tool
        temp_tool = tool_dict["check_temperatures"]
        assert temp_tool.inputSchema["type"] == "object"
        assert temp_tool.inputSchema["required"] == []
        assert "include_history" in temp_tool.inputSchema["properties"]
        assert "check_throttling" in temp_tool.inputSchema["properties"]

        # Fan control tool
        fan_tool = tool_dict["monitor_fan_control"]
        assert "action" in fan_tool.inputSchema["properties"]
        assert "status" in fan_tool.inputSchema["properties"]["action"]["enum"]
        assert "target_speed" in fan_tool.inputSchema["properties"]

        # Power supply tool
        power_tool = tool_dict["check_power_supply"]
        assert "detailed" in power_tool.inputSchema["properties"]

        # Hardware errors tool
        errors_tool = tool_dict["inspect_hardware_errors"]
        assert "hours" in errors_tool.inputSchema["properties"]
        assert "error_types" in errors_tool.inputSchema["properties"]

        # GPIO tool
        gpio_tool = tool_dict["check_gpio_status"]
        assert "pins" in gpio_tool.inputSchema["properties"]
        assert "show_all" in gpio_tool.inputSchema["properties"]

    @pytest.mark.asyncio
    async def test_check_temperatures_normal(
        self, hardware_tools: HardwareTools
    ) -> None:
        """Test temperature check with normal readings."""
        # Mock CPU temperature reading - need to track call order
        call_count = [0]

        def mock_execute_command(command):
            call_count[0] += 1
            if "measure_temp" in command and "gpu" not in command:
                return (0, "temp=55.4'C", "")  # CPU temp
            elif "get_throttled" in command:
                return (0, "throttled=0x0", "")  # No throttling
            elif "measure_temp" in command and "gpu" in command:
                return (0, "temp=52.1'C", "")  # GPU temp
            else:
                return (1, "", "Unknown command")

        hardware_tools.ssh.execute_command.side_effect = mock_execute_command

        result = await hardware_tools.handle_tool_call("check_temperatures", {})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        text = result[0].text

        assert "🌡️ **Temperature Monitoring**" in text
        assert "**CPU Temperature:** 55.4°C" in text
        assert "✅ **NORMAL**" in text
        assert "✅ No thermal issues detected" in text

    @pytest.mark.asyncio
    async def test_check_temperatures_high_warning(
        self, hardware_tools: HardwareTools
    ) -> None:
        """Test temperature check with high temperature warnings."""

        # Test warm temperature (60-70°C)
        def mock_warm_temp(command):
            if "measure_temp" in command and "gpu" not in command:
                return (0, "temp=65.7'C", "")
            elif "get_throttled" in command:
                return (0, "throttled=0x0", "")
            elif "measure_temp" in command and "gpu" in command:
                return (0, "", "")
            return (1, "", "Unknown command")

        hardware_tools.ssh.execute_command.side_effect = mock_warm_temp
        result = await hardware_tools.handle_tool_call("check_temperatures", {})
        text = result[0].text

        assert "**CPU Temperature:** 65.7°C" in text
        assert "🟡 **WARM**" in text

        # Test high temperature (70-80°C)
        def mock_high_temp(command):
            if "measure_temp" in command and "gpu" not in command:
                return (0, "temp=75.2'C", "")
            elif "get_throttled" in command:
                return (0, "throttled=0x0", "")
            elif "measure_temp" in command and "gpu" in command:
                return (0, "", "")
            return (1, "", "Unknown command")

        hardware_tools.ssh.execute_command.side_effect = mock_high_temp
        result = await hardware_tools.handle_tool_call("check_temperatures", {})
        text = result[0].text

        assert "**CPU Temperature:** 75.2°C" in text
        assert "⚠️ **HIGH**" in text

    @pytest.mark.asyncio
    async def test_check_temperatures_critical(
        self, hardware_tools: HardwareTools
    ) -> None:
        """Test temperature check with critical overheating."""

        def mock_critical_temp(command):
            if "measure_temp" in command and "gpu" not in command:
                return (0, "temp=85.9'C", "")
            elif "get_throttled" in command:
                return (0, "throttled=0x0", "")
            elif "measure_temp" in command and "gpu" in command:
                return (0, "", "")
            return (1, "", "Unknown command")

        hardware_tools.ssh.execute_command.side_effect = mock_critical_temp
        result = await hardware_tools.handle_tool_call("check_temperatures", {})
        text = result[0].text

        assert "**CPU Temperature:** 85.9°C" in text
        assert "🔥 **CRITICAL - OVERHEATING!**" in text

    @pytest.mark.asyncio
    async def test_check_temperatures_throttling_active(
        self, hardware_tools: HardwareTools
    ) -> None:
        """Test temperature check with active throttling."""
        hardware_tools.ssh.execute_command.side_effect = [
            (0, "temp=82.3'C", ""),  # CPU temp
            (0, "throttled=0x50004", ""),  # Active throttling + history
            (0, "", ""),  # No GPU temp
            (0, "not-running", ""),  # pigpiod service check
            (0, "No fan scripts found", ""),  # fan scripts check
        ]

        result = await hardware_tools.handle_tool_call("check_temperatures", {})
        text = result[0].text

        assert "**CPU Temperature:** 82.3°C" in text
        assert "🔥 **CRITICAL - OVERHEATING!**" in text
        assert "**Thermal Status:**" in text
        assert "⚡ Currently throttled" in text
        assert "⚠️ Throttling has occurred" in text

    @pytest.mark.asyncio
    async def test_check_temperatures_undervoltage(
        self, hardware_tools: HardwareTools
    ) -> None:
        """Test temperature check with undervoltage detection."""
        hardware_tools.ssh.execute_command.side_effect = [
            (0, "temp=65.0'C", ""),  # CPU temp
            (0, "throttled=0x10001", ""),  # Undervoltage active + history
            (0, "", ""),  # No GPU temp
            (0, "not-running", ""),  # pigpiod service check
            (0, "No fan scripts found", ""),  # fan scripts check
        ]

        result = await hardware_tools.handle_tool_call("check_temperatures", {})
        text = result[0].text

        assert "🔥 Under-voltage detected" in text
        assert "⚠️ Under-voltage has occurred" in text

    @pytest.mark.asyncio
    async def test_check_temperatures_cpu_read_failure(
        self, hardware_tools: HardwareTools
    ) -> None:
        """Test temperature check when CPU temp read fails."""
        hardware_tools.ssh.execute_command.side_effect = [
            (1, "", "Command not found"),  # CPU temp fails
            (0, "throttled=0x0", ""),  # Throttling ok
            (0, "", ""),  # No GPU temp
            (0, "not-running", ""),  # pigpiod service check
            (0, "No fan scripts found", ""),  # fan scripts check
        ]

        result = await hardware_tools.handle_tool_call("check_temperatures", {})
        text = result[0].text

        assert "❌ Could not read CPU temperature" in text
        assert "✅ No thermal issues detected" in text

    @pytest.mark.asyncio
    async def test_check_temperatures_malformed_output(
        self, hardware_tools: HardwareTools
    ) -> None:
        """Test temperature check with malformed command output."""
        hardware_tools.ssh.execute_command.side_effect = [
            (1, "invalid output format", ""),  # CPU temp command fails
            (0, "throttled=0x0", ""),  # Valid throttling (no issues)
            (0, "", ""),  # No GPU temp
            (0, "not-running", ""),  # pigpiod service check
            (0, "No fan scripts found", ""),  # fan scripts check
        ]

        result = await hardware_tools.handle_tool_call("check_temperatures", {})
        text = result[0].text

        assert "❌ Could not read CPU temperature" in text

    @pytest.mark.asyncio
    async def test_check_temperatures_skip_throttling(
        self, hardware_tools: HardwareTools
    ) -> None:
        """Test temperature check with throttling check disabled."""
        hardware_tools.ssh.execute_command.side_effect = [
            (0, "temp=60.5'C", ""),  # CPU temp
            # No throttling check should be made
            (0, "", ""),  # No GPU temp
            (0, "not-running", ""),  # pigpiod service check
            (0, "No fan scripts found", ""),  # fan scripts check
        ]

        result = await hardware_tools.handle_tool_call(
            "check_temperatures", {"check_throttling": False}
        )
        text = result[0].text

        assert "**CPU Temperature:** 60.5°C" in text
        assert "**Thermal Status:**" not in text
        # Should call execute_command 4 times (CPU temp + GPU temp + fan service + fan scripts)
        assert hardware_tools.ssh.execute_command.call_count == 4

    @pytest.mark.asyncio
    async def test_check_temperatures_with_gpu(
        self, hardware_tools: HardwareTools
    ) -> None:
        """Test temperature check including GPU temperature."""
        hardware_tools.ssh.execute_command.side_effect = [
            (0, "temp=58.2'C", ""),  # CPU temp
            (0, "throttled=0x0", ""),  # No throttling
            (0, "temp=45.7'C", ""),  # GPU temp
            (0, "not-running", ""),  # pigpiod service check
            (0, "No fan scripts found", ""),  # fan scripts check
        ]

        result = await hardware_tools.handle_tool_call("check_temperatures", {})
        text = result[0].text

        assert "**CPU Temperature:** 58.2°C" in text
        assert "✅ **NORMAL**" in text
        # GPU temp should be displayed somewhere in output
        assert "45.7" in text

    @pytest.mark.asyncio
    async def test_check_temperatures_complex_throttling(
        self, hardware_tools: HardwareTools
    ) -> None:
        """Test temperature check with complex throttling status."""
        # Test all throttling flags
        hardware_tools.ssh.execute_command.side_effect = [
            (0, "temp=80.1'C", ""),  # CPU temp
            (0, "throttled=0xF000F", ""),  # All flags set
            (0, "", ""),  # No GPU temp
            (0, "not-running", ""),  # pigpiod service check
            (0, "No fan scripts found", ""),  # fan scripts check
        ]

        result = await hardware_tools.handle_tool_call("check_temperatures", {})
        text = result[0].text

        # Should contain all throttling messages
        assert "🔥 Under-voltage detected" in text
        assert "🌡️ ARM frequency capped" in text
        assert "⚡ Currently throttled" in text
        assert "🌡️ Soft temperature limit active" in text
        assert "⚠️ Under-voltage has occurred" in text
        assert "⚠️ ARM frequency capping has occurred" in text
        assert "⚠️ Throttling has occurred" in text
        assert "⚠️ Soft temperature limit has occurred" in text

    @pytest.mark.asyncio
    async def test_check_temperatures_hex_parsing_edge_cases(
        self, hardware_tools: HardwareTools
    ) -> None:
        """Test throttling hex value parsing edge cases."""
        # Test different hex formats
        test_cases = [
            "throttled=0x50004",  # Standard format
            "throttled=50004",  # No 0x prefix
            "throttled=0x0",  # Zero value
            "0x10001",  # No equals sign
        ]

        for throttle_output in test_cases:
            hardware_tools.ssh.execute_command.side_effect = [
                (0, "temp=65.0'C", ""),  # CPU temp
                (0, throttle_output, ""),  # Throttling
                (0, "", ""),  # No GPU temp
            ]

            result = await hardware_tools.handle_tool_call("check_temperatures", {})
            assert len(result) == 1
            assert isinstance(result[0], TextContent)
            # Should not crash on any format

    @pytest.mark.asyncio
    async def test_monitor_fan_control_status(
        self, hardware_tools: HardwareTools
    ) -> None:
        """Test fan control status monitoring."""
        # Mock fan control commands
        hardware_tools.ssh.execute_command.side_effect = [
            (0, "gpio_fan_temp=60000", ""),  # Fan temp threshold
            (0, "some fan status", ""),  # Fan status
        ]

        result = await hardware_tools.handle_tool_call(
            "monitor_fan_control", {"action": "status"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        # Should contain fan monitoring information
        text = result[0].text
        assert len(text) > 0

    @pytest.mark.asyncio
    async def test_check_power_supply_basic(
        self, hardware_tools: HardwareTools
    ) -> None:
        """Test basic power supply monitoring."""
        hardware_tools.ssh.execute_command.side_effect = [
            (0, "volt=1.2000V", ""),  # Core voltage
        ]

        result = await hardware_tools.handle_tool_call("check_power_supply", {})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        text = result[0].text
        assert len(text) > 0

    @pytest.mark.asyncio
    async def test_inspect_hardware_errors_default(
        self, hardware_tools: HardwareTools
    ) -> None:
        """Test hardware error inspection with default parameters."""
        hardware_tools.ssh.execute_command.side_effect = [
            (0, "some dmesg output", ""),  # dmesg
            (0, "some journal output", ""),  # journalctl
        ]

        result = await hardware_tools.handle_tool_call("inspect_hardware_errors", {})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)

    @pytest.mark.asyncio
    async def test_inspect_hardware_errors_specific_types(
        self, hardware_tools: HardwareTools
    ) -> None:
        """Test hardware error inspection with specific error types."""
        hardware_tools.ssh.execute_command.side_effect = [
            (0, "thermal error in logs", ""),  # dmesg
            (0, "power error in journal", ""),  # journalctl
        ]

        result = await hardware_tools.handle_tool_call(
            "inspect_hardware_errors",
            {"hours": 12, "error_types": ["thermal", "power"]},
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)

    @pytest.mark.asyncio
    async def test_check_gpio_status_show_all(
        self, hardware_tools: HardwareTools
    ) -> None:
        """Test GPIO status check showing all pins."""
        hardware_tools.ssh.execute_command.side_effect = [
            (0, "available", ""),  # GPIO tools check
            (0, "gpio readall output", ""),  # GPIO readall
            (0, "No I2C devices found", ""),  # I2C check
            (0, "SPI not enabled", ""),  # SPI check
        ]

        result = await hardware_tools.handle_tool_call(
            "check_gpio_status", {"show_all": True}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert hardware_tools.ssh.execute_command.call_count == 4

    @pytest.mark.asyncio
    async def test_check_gpio_status_specific_pins(
        self, hardware_tools: HardwareTools
    ) -> None:
        """Test GPIO status check for specific pins."""
        hardware_tools.ssh.execute_command.side_effect = [
            (0, "available", ""),  # GPIO tools check
            (0, "pin 18 output", ""),  # GPIO 18
            (0, "pin 24 output", ""),  # GPIO 24
            (0, "No I2C devices found", ""),  # I2C check
            (0, "SPI not enabled", ""),  # SPI check
        ]

        result = await hardware_tools.handle_tool_call(
            "check_gpio_status", {"pins": [18, 24]}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        # Should call execute_command for GPIO tools + pins + I2C + SPI
        assert hardware_tools.ssh.execute_command.call_count == 5

    @pytest.mark.asyncio
    async def test_handle_unknown_tool(self, hardware_tools: HardwareTools) -> None:
        """Test handling of unknown tool name."""
        result = await hardware_tools.handle_tool_call("unknown_tool", {})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Unknown tool: unknown_tool" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_tool_exception(self, hardware_tools: HardwareTools) -> None:
        """Test exception handling in tool execution."""
        hardware_tools.ssh.execute_command.side_effect = Exception(
            "SSH connection lost"
        )

        result = await hardware_tools.handle_tool_call("check_temperatures", {})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Error in check_temperatures: SSH connection lost" in result[0].text

    @pytest.mark.asyncio
    async def test_command_execution_failure(
        self, hardware_tools: HardwareTools
    ) -> None:
        """Test handling of command execution failures."""
        hardware_tools.ssh.execute_command.return_value = (1, "", "Permission denied")

        result = await hardware_tools.handle_tool_call("check_power_supply", {})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        # Should handle gracefully without crashing

    def test_inheritance_from_base_tool(self, hardware_tools: HardwareTools) -> None:
        """Test that HardwareTools properly inherits from BaseTool."""
        # Should have access to BaseTool methods
        assert hasattr(hardware_tools, "format_success")
        assert hasattr(hardware_tools, "format_error")
        assert hasattr(hardware_tools, "ssh")
        assert hasattr(hardware_tools, "config")

        # Test format methods work
        success_result = hardware_tools.format_success("Test message")
        assert len(success_result) == 1
        assert isinstance(success_result[0], TextContent)
        assert "Test message" in success_result[0].text

        error_result = hardware_tools.format_error("Error message")
        assert len(error_result) == 1
        assert isinstance(error_result[0], TextContent)
        assert "Error message" in error_result[0].text

    @pytest.mark.asyncio
    async def test_temperature_parsing_precision(
        self, hardware_tools: HardwareTools
    ) -> None:
        """Test temperature parsing with different precision levels."""
        test_temps = [
            "temp=45'C",  # No decimal
            "temp=45.0'C",  # One decimal
            "temp=45.67'C",  # Two decimals
            "temp=45.123'C",  # Three decimals
        ]

        for temp_output in test_temps:
            hardware_tools.ssh.execute_command.side_effect = [
                (0, temp_output, ""),  # CPU temp
                (0, "throttled=0x0", ""),  # No throttling
                (0, "", ""),  # No GPU temp
            ]

            result = await hardware_tools.handle_tool_call("check_temperatures", {})
            assert len(result) == 1
            assert isinstance(result[0], TextContent)
            # Should handle all precision levels

    @pytest.mark.asyncio
    async def test_fan_control_test_action(self, hardware_tools: HardwareTools) -> None:
        """Test fan control test action with target speed."""
        result = await hardware_tools.handle_tool_call(
            "monitor_fan_control", {"action": "test", "target_speed": 75}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)

    @pytest.mark.asyncio
    async def test_power_supply_detailed_analysis(
        self, hardware_tools: HardwareTools
    ) -> None:
        """Test power supply monitoring with detailed analysis."""
        result = await hardware_tools.handle_tool_call(
            "check_power_supply", {"detailed": True}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)

    @pytest.mark.asyncio
    async def test_gpio_empty_pins_list(self, hardware_tools: HardwareTools) -> None:
        """Test GPIO status check with empty pins list."""
        result = await hardware_tools.handle_tool_call(
            "check_gpio_status", {"pins": []}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
