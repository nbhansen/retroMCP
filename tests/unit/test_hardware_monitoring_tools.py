"""Unit tests for HardwareMonitoringTools implementation."""

from unittest.mock import Mock

import pytest
from mcp.types import TextContent

from retromcp.config import RetroPieConfig
from retromcp.discovery import RetroPiePaths
from retromcp.domain.models import CommandResult
from retromcp.tools.hardware_monitoring_tools import HardwareMonitoringTools


@pytest.mark.unit
@pytest.mark.tools
@pytest.mark.hardware_tools
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

    # Power Operations Tests

    @pytest.mark.asyncio
    async def test_power_monitor_not_implemented(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test power monitoring (not yet implemented)."""
        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware", {"component": "power", "action": "monitor"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "power monitoring not yet implemented" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_power_inspect_not_implemented(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test power inspection (not yet implemented)."""
        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware", {"component": "power", "action": "inspect"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "power inspection not yet implemented" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_power_invalid_action(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test invalid power action."""
        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware", {"component": "power", "action": "invalid"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "invalid action" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_power_check_undervoltage_detected(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test power check with undervoltage detection."""
        hardware_monitoring_tools.container.retropie_client.execute_command.side_effect = [
            CommandResult(
                command="vcgencmd get_throttled",
                exit_code=0,
                stdout="throttled=0x1",  # Under-voltage detected
                stderr="",
                success=True,
                execution_time=0.1,
            ),
            CommandResult(
                command="dmesg | grep -i 'voltage' | tail -10",
                exit_code=0,
                stdout="Under-voltage detected! (0x00050005)",
                stderr="",
                success=True,
                execution_time=0.1,
            ),
        ]

        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware", {"component": "power", "action": "check"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "⚠️ **UNDER-VOLTAGE DETECTED**" in result[0].text
        assert "Recent Voltage Warnings" in result[0].text

    @pytest.mark.asyncio
    async def test_power_check_undervoltage_occurred(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test power check with past undervoltage occurrence."""
        hardware_monitoring_tools.container.retropie_client.execute_command.side_effect = [
            CommandResult(
                command="vcgencmd get_throttled",
                exit_code=0,
                stdout="throttled=0x10000",  # Under-voltage occurred
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

        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware", {"component": "power", "action": "check"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "🟡 **UNDER-VOLTAGE OCCURRED** (resolved)" in result[0].text

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

    @pytest.mark.asyncio
    async def test_gpio_configure_not_implemented(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test GPIO configuration (not yet implemented)."""
        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware", {"component": "gpio", "action": "configure"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "gpio configuration not yet implemented" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_gpio_invalid_action(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test invalid GPIO action."""
        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware", {"component": "gpio", "action": "invalid"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "invalid action" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_gpio_check_command_failure(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test GPIO check with command failure."""
        hardware_monitoring_tools.container.retropie_client.execute_command.return_value = CommandResult(
            command="gpio readall",
            exit_code=1,
            stdout="",
            stderr="gpio: command not found",
            success=False,
            execution_time=0.1,
        )

        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware", {"component": "gpio", "action": "check"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "GPIO Pin Status" in result[0].text
        assert "❌ Failed to read GPIO status" in result[0].text
        assert "gpio` command may not be available" in result[0].text

    @pytest.mark.asyncio
    async def test_gpio_test_command_failure(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test GPIO pin test with command failure."""
        hardware_monitoring_tools.container.retropie_client.execute_command.return_value = CommandResult(
            command="gpio read 18",
            exit_code=1,
            stdout="",
            stderr="gpio: command not found",
            success=False,
            execution_time=0.1,
        )

        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware", {"component": "gpio", "action": "test", "pin": 18}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "GPIO Pin 18 Test" in result[0].text
        assert "❌ Failed to read GPIO pin 18" in result[0].text

    @pytest.mark.asyncio
    async def test_gpio_test_low_value(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test GPIO pin test with LOW value."""
        hardware_monitoring_tools.container.retropie_client.execute_command.return_value = CommandResult(
            command="gpio read 18",
            exit_code=0,
            stdout="0",
            stderr="",
            success=True,
            execution_time=0.1,
        )

        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware", {"component": "gpio", "action": "test", "pin": 18}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "LOW" in result[0].text
        assert "(0)" in result[0].text

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

    @pytest.mark.asyncio
    async def test_errors_check_with_errors_found(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test error checking with actual errors found."""
        hardware_monitoring_tools.container.retropie_client.execute_command.side_effect = [
            CommandResult(
                command="dmesg | grep -i 'error\\|fail\\|warn' | grep -i 'hardware\\|temp\\|power\\|usb' | tail -10",
                exit_code=0,
                stdout="[12345.678] WARNING: Hardware error detected\n[12346.789] ERROR: USB device disconnected",
                stderr="",
                success=True,
                execution_time=0.1,
            ),
            CommandResult(
                command="journalctl -p err -n 10 --no-pager",
                exit_code=0,
                stdout="Jan 01 00:00:00 retropie systemd[1]: Error: Service failed to start",
                stderr="",
                success=True,
                execution_time=0.1,
            ),
        ]

        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware", {"component": "errors", "action": "check"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Hardware Error Analysis" in result[0].text
        assert "System Log Errors" in result[0].text
        assert "Journal Errors" in result[0].text
        assert "WARNING: Hardware error detected" in result[0].text
        assert "Service failed to start" in result[0].text

    @pytest.mark.asyncio
    async def test_errors_inspect_not_implemented(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test error inspection (not yet implemented)."""
        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware", {"component": "errors", "action": "inspect", "lines": 25}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert (
            "hardware error inspection with 25 lines not yet implemented"
            in result[0].text.lower()
        )

    @pytest.mark.asyncio
    async def test_errors_invalid_action(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test invalid error action."""
        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware", {"component": "errors", "action": "invalid"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "invalid action" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_errors_check_journal_no_entries(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test error checking with journal entries containing 'No entries'."""
        hardware_monitoring_tools.container.retropie_client.execute_command.side_effect = [
            CommandResult(
                command="dmesg | grep -i 'error\\|fail\\|warn' | grep -i 'hardware\\|temp\\|power\\|usb' | tail -10",
                exit_code=0,
                stdout="[12345.678] WARNING: Hardware error detected",
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

        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware", {"component": "errors", "action": "check"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "System Log Errors" in result[0].text
        assert "WARNING: Hardware error detected" in result[0].text
        # Should not include journal errors section when "No entries" is present
        assert "Journal Errors" not in result[0].text

    # All Component Tests

    @pytest.mark.asyncio
    async def test_manage_hardware_all_check_success(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test comprehensive hardware overview."""
        # Mock all hardware commands
        call_count = [0]

        def mock_execute_command(command, use_sudo=False) -> CommandResult:  # noqa: ARG001
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

    @pytest.mark.asyncio
    async def test_all_inspect_not_implemented(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test comprehensive hardware inspection (not yet implemented)."""
        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware", {"component": "all", "action": "inspect"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert (
            "comprehensive hardware inspection not yet implemented"
            in result[0].text.lower()
        )

    @pytest.mark.asyncio
    async def test_all_invalid_action(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test invalid all action."""
        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware", {"component": "all", "action": "invalid"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "invalid action" in result[0].text.lower()

    # Helper Method Tests

    def test_get_temperature_status_normal(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test temperature status for normal range."""
        status = hardware_monitoring_tools._get_temperature_status(55.0)
        assert status == "✅ NORMAL"

    def test_get_temperature_status_warm(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test temperature status for warm range."""
        status = hardware_monitoring_tools._get_temperature_status(65.0)
        assert status == "🟡 WARM"

    def test_get_temperature_status_high(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test temperature status for high range."""
        status = hardware_monitoring_tools._get_temperature_status(75.0)
        assert status == "⚠️ HIGH"

    def test_get_temperature_status_critical(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test temperature status for critical range."""
        status = hardware_monitoring_tools._get_temperature_status(85.0)
        assert status == "🔥 CRITICAL"

    def test_get_temperature_status_boundary_60(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test temperature status at 60 degree boundary."""
        status = hardware_monitoring_tools._get_temperature_status(60.0)
        assert status == "🟡 WARM"

    def test_get_temperature_status_boundary_70(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test temperature status at 70 degree boundary."""
        status = hardware_monitoring_tools._get_temperature_status(70.0)
        assert status == "⚠️ HIGH"

    def test_get_temperature_status_boundary_80(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test temperature status at 80 degree boundary."""
        status = hardware_monitoring_tools._get_temperature_status(80.0)
        assert status == "🔥 CRITICAL"

    def test_parse_throttling_status_no_throttling(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test parsing throttling status with no throttling."""
        status = hardware_monitoring_tools._parse_throttling_status("0x0")
        assert "✅ No throttling detected" in status

    def test_parse_throttling_status_under_voltage(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test parsing throttling status with under-voltage."""
        status = hardware_monitoring_tools._parse_throttling_status("0x1")
        assert "🔥 Under-voltage detected" in status

    def test_parse_throttling_status_arm_frequency_cap(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test parsing throttling status with ARM frequency cap."""
        status = hardware_monitoring_tools._parse_throttling_status("0x2")
        assert "🌡️ ARM frequency capped" in status

    def test_parse_throttling_status_currently_throttled(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test parsing throttling status with current throttling."""
        status = hardware_monitoring_tools._parse_throttling_status("0x4")
        assert "⚠️ Currently throttled" in status

    def test_parse_throttling_status_soft_temp_limit(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test parsing throttling status with soft temperature limit."""
        status = hardware_monitoring_tools._parse_throttling_status("0x8")
        assert "🔥 Soft temperature limit active" in status

    def test_parse_throttling_status_historical_under_voltage(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test parsing throttling status with historical under-voltage."""
        status = hardware_monitoring_tools._parse_throttling_status("0x10000")
        assert "🟡 Under-voltage occurred" in status

    def test_parse_throttling_status_historical_arm_frequency(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test parsing throttling status with historical ARM frequency capping."""
        status = hardware_monitoring_tools._parse_throttling_status("0x20000")
        assert "🟡 ARM frequency capping occurred" in status

    def test_parse_throttling_status_historical_throttling(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test parsing throttling status with historical throttling."""
        status = hardware_monitoring_tools._parse_throttling_status("0x40000")
        assert "🟡 Throttling occurred" in status

    def test_parse_throttling_status_historical_soft_temp(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test parsing throttling status with historical soft temperature limit."""
        status = hardware_monitoring_tools._parse_throttling_status("0x80000")
        assert "🟡 Soft temperature limit occurred" in status

    def test_parse_throttling_status_combined_flags(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test parsing throttling status with combined flags."""
        status = hardware_monitoring_tools._parse_throttling_status("0x50005")
        assert "🔥 Under-voltage detected" in status
        assert "⚠️ Currently throttled" in status
        assert "🟡 Under-voltage occurred" in status
        assert "🟡 Throttling occurred" in status

    def test_parse_throttling_status_invalid_hex(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test parsing throttling status with invalid hex value."""
        status = hardware_monitoring_tools._parse_throttling_status("invalid")
        assert "❓ Unable to parse (invalid)" in status

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

    # Exception Handling Tests

    @pytest.mark.asyncio
    async def test_handle_tool_call_exception_handling(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test exception handling in handle_tool_call."""
        # Mock an exception during command execution
        hardware_monitoring_tools.container.retropie_client.execute_command.side_effect = Exception(
            "SSH connection failed"
        )

        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware", {"component": "temperature", "action": "check"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "failed" in result[0].text.lower()
        assert "SSH connection failed" in result[0].text

    @pytest.mark.asyncio
    async def test_temperature_check_exception_handling(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test exception handling in temperature checking."""
        # Mock SSH command to raise exception
        hardware_monitoring_tools.container.retropie_client.execute_command.side_effect = Exception(
            "Command execution failed"
        )

        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware", {"component": "temperature", "action": "check"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "failed to check temperatures" in result[0].text.lower()
        assert "Command execution failed" in result[0].text

    @pytest.mark.asyncio
    async def test_fan_check_exception_handling(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test exception handling in fan checking."""
        hardware_monitoring_tools.container.retropie_client.execute_command.side_effect = Exception(
            "Fan command failed"
        )

        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware", {"component": "fan", "action": "check"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "failed to check fan status" in result[0].text.lower()
        assert "Fan command failed" in result[0].text

    @pytest.mark.asyncio
    async def test_power_check_exception_handling(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test exception handling in power checking."""
        hardware_monitoring_tools.container.retropie_client.execute_command.side_effect = Exception(
            "Power command failed"
        )

        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware", {"component": "power", "action": "check"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "failed to check power supply" in result[0].text.lower()
        assert "Power command failed" in result[0].text

    @pytest.mark.asyncio
    async def test_gpio_check_exception_handling(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test exception handling in GPIO checking."""
        hardware_monitoring_tools.container.retropie_client.execute_command.side_effect = Exception(
            "GPIO command failed"
        )

        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware", {"component": "gpio", "action": "check"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "failed to check gpio status" in result[0].text.lower()
        assert "GPIO command failed" in result[0].text

    @pytest.mark.asyncio
    async def test_gpio_test_exception_handling(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test exception handling in GPIO pin testing."""
        hardware_monitoring_tools.container.retropie_client.execute_command.side_effect = Exception(
            "GPIO test failed"
        )

        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware", {"component": "gpio", "action": "test", "pin": 18}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "failed to test gpio pin 18" in result[0].text.lower()
        assert "GPIO test failed" in result[0].text

    @pytest.mark.asyncio
    async def test_errors_check_exception_handling(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test exception handling in error checking."""
        hardware_monitoring_tools.container.retropie_client.execute_command.side_effect = Exception(
            "Error command failed"
        )

        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware", {"component": "errors", "action": "check"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "failed to check hardware errors" in result[0].text.lower()
        assert "Error command failed" in result[0].text

    @pytest.mark.asyncio
    async def test_all_check_exception_handling(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test exception handling in comprehensive hardware check."""
        hardware_monitoring_tools.container.retropie_client.execute_command.side_effect = Exception(
            "Hardware check failed"
        )

        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware", {"component": "all", "action": "check"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "hardware system overview" in result[0].text.lower()
        assert "failed to check temperatures" in result[0].text.lower()
        assert "failed to check power supply" in result[0].text.lower()
        assert "failed to check hardware errors" in result[0].text.lower()
        assert "Hardware check failed" in result[0].text

    # Validation Error Tests

    @pytest.mark.asyncio
    async def test_missing_component_parameter(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test error handling for missing component parameter."""
        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware", {"action": "check"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "component is required" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_missing_action_parameter(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test error handling for missing action parameter."""
        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware", {"component": "temperature"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "action is required" in result[0].text.lower()

    # Temperature Monitoring Tests

    @pytest.mark.asyncio
    async def test_temperature_monitor_with_threshold(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test temperature monitoring with custom threshold."""
        # Mock temperature command results
        hardware_monitoring_tools.container.retropie_client.execute_command.side_effect = [
            CommandResult(
                command="vcgencmd measure_temp",
                exit_code=0,
                stdout="temp=78.5'C",
                stderr="",
                success=True,
                execution_time=0.1,
            ),
            CommandResult(
                command="vcgencmd measure_temp gpu",
                exit_code=0,
                stdout="temp=75.2'C",
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

        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware",
            {"component": "temperature", "action": "monitor", "threshold": 80.0},
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "78.5°C" in result[0].text
        assert "Monitor Threshold**: 80.0°C" in result[0].text

    @pytest.mark.asyncio
    async def test_temperature_configure_not_implemented(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test temperature configuration (not yet implemented)."""
        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware", {"component": "temperature", "action": "configure"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "temperature configuration not yet implemented" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_temperature_inspect_not_implemented(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test temperature inspection (not yet implemented)."""
        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware", {"component": "temperature", "action": "inspect"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "temperature inspection not yet implemented" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_temperature_invalid_action(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test invalid temperature action."""
        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware", {"component": "temperature", "action": "invalid"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "invalid action" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_temperature_parsing_failures(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test temperature parsing failures."""
        # Mock malformed temperature responses
        hardware_monitoring_tools.container.retropie_client.execute_command.side_effect = [
            CommandResult(
                command="vcgencmd measure_temp",
                exit_code=0,
                stdout="invalid_format",
                stderr="",
                success=True,
                execution_time=0.1,
            ),
            CommandResult(
                command="vcgencmd measure_temp gpu",
                exit_code=0,
                stdout="temp=invalid'C",
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

        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware", {"component": "temperature", "action": "check"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Failed to check temperatures" in result[0].text
        assert "could not convert string to float" in result[0].text

    @pytest.mark.asyncio
    async def test_temperature_command_failures(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test temperature command failures."""
        # Mock failed temperature commands
        hardware_monitoring_tools.container.retropie_client.execute_command.side_effect = [
            CommandResult(
                command="vcgencmd measure_temp",
                exit_code=1,
                stdout="",
                stderr="Command not found",
                success=False,
                execution_time=0.1,
            ),
            CommandResult(
                command="vcgencmd measure_temp gpu",
                exit_code=1,
                stdout="",
                stderr="Command not found",
                success=False,
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

        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware", {"component": "temperature", "action": "check"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "❌ Failed to read temperature" in result[0].text

    # Fan Operations Tests

    @pytest.mark.asyncio
    async def test_fan_monitor_not_implemented(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test fan monitoring (not yet implemented)."""
        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware", {"component": "fan", "action": "monitor"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "fan monitoring not yet implemented" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_fan_configure_not_implemented(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test fan configuration (not yet implemented)."""
        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware", {"component": "fan", "action": "configure", "speed": 75}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert (
            "fan speed configuration to 75% not yet implemented"
            in result[0].text.lower()
        )

    @pytest.mark.asyncio
    async def test_fan_test_not_implemented(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test fan operation testing (not yet implemented)."""
        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware", {"component": "fan", "action": "test"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "fan operation testing not yet implemented" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_fan_invalid_action(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test invalid fan action."""
        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware", {"component": "fan", "action": "invalid"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "invalid action" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_fan_check_no_cooling_devices(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test fan check with no cooling devices."""
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
                exit_code=1,
                stdout="",
                stderr="No such file or directory",
                success=False,
                execution_time=0.1,
            ),
        ]

        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware", {"component": "fan", "action": "check"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "No active cooling devices detected" in result[0].text

    # Additional Edge Cases and Coverage Tests

    @pytest.mark.asyncio
    async def test_temperature_check_empty_stdout(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test temperature check with empty stdout."""
        hardware_monitoring_tools.container.retropie_client.execute_command.side_effect = [
            CommandResult(
                command="vcgencmd measure_temp",
                exit_code=0,
                stdout="",
                stderr="",
                success=True,
                execution_time=0.1,
            ),
            CommandResult(
                command="vcgencmd measure_temp gpu",
                exit_code=0,
                stdout="",
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

        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware", {"component": "temperature", "action": "check"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "❌ Failed to read temperature" in result[0].text

    @pytest.mark.asyncio
    async def test_temperature_check_malformed_temp_output(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test temperature check with malformed temp output."""
        hardware_monitoring_tools.container.retropie_client.execute_command.side_effect = [
            CommandResult(
                command="vcgencmd measure_temp",
                exit_code=0,
                stdout="temperature=55.4C",  # Missing temp= prefix
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

        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware", {"component": "temperature", "action": "check"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "❓ Unable to read temperature" in result[0].text

    @pytest.mark.asyncio
    async def test_temperature_check_malformed_throttled_output(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test temperature check with malformed throttled output."""
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
                stdout="status=0x0",  # Missing throttled= prefix
                stderr="",
                success=True,
                execution_time=0.1,
            ),
        ]

        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware", {"component": "temperature", "action": "check"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "55.4°C" in result[0].text
        assert "52.1°C" in result[0].text
        # Should not include throttling status if malformed
        assert "throttled=" not in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_fan_check_empty_temperature(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test fan check with empty temperature output."""
        hardware_monitoring_tools.container.retropie_client.execute_command.side_effect = [
            CommandResult(
                command="vcgencmd measure_temp",
                exit_code=0,
                stdout="",
                stderr="",
                success=True,
                execution_time=0.1,
            ),
            CommandResult(
                command="ls -la /sys/class/thermal/cooling_device*/",
                exit_code=0,
                stdout="cooling device info",
                stderr="",
                success=True,
                execution_time=0.1,
            ),
        ]

        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware", {"component": "fan", "action": "check"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Fan Control Status" in result[0].text
        # Should not include temperature if empty
        assert "Current Temperature:" not in result[0].text

    @pytest.mark.asyncio
    async def test_fan_check_malformed_temperature(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test fan check with malformed temperature output."""
        hardware_monitoring_tools.container.retropie_client.execute_command.side_effect = [
            CommandResult(
                command="vcgencmd measure_temp",
                exit_code=0,
                stdout="invalid_temp_format",
                stderr="",
                success=True,
                execution_time=0.1,
            ),
            CommandResult(
                command="ls -la /sys/class/thermal/cooling_device*/",
                exit_code=0,
                stdout="cooling device info",
                stderr="",
                success=True,
                execution_time=0.1,
            ),
        ]

        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware", {"component": "fan", "action": "check"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Fan Control Status" in result[0].text
        # Should not include temperature if malformed
        assert "Current Temperature:" not in result[0].text

    @pytest.mark.asyncio
    async def test_power_check_malformed_throttled_value(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test power check with malformed throttled value."""
        hardware_monitoring_tools.container.retropie_client.execute_command.side_effect = [
            CommandResult(
                command="vcgencmd get_throttled",
                exit_code=0,
                stdout="status=invalid",  # Missing throttled= prefix
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

        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware", {"component": "power", "action": "check"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Power Supply Status" in result[0].text
        # Should not include power status if malformed
        assert "HEALTHY" not in result[0].text
        assert "UNDER-VOLTAGE" not in result[0].text

    @pytest.mark.asyncio
    async def test_power_check_empty_throttled_output(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test power check with empty throttled output."""
        hardware_monitoring_tools.container.retropie_client.execute_command.side_effect = [
            CommandResult(
                command="vcgencmd get_throttled",
                exit_code=0,
                stdout="",
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

        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware", {"component": "power", "action": "check"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Power Supply Status" in result[0].text

    @pytest.mark.asyncio
    async def test_gpio_test_pin_validation_negative(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test GPIO pin validation with negative pin number."""
        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware", {"component": "gpio", "action": "test", "pin": -1}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Invalid pin number" in result[0].text
        assert "between 0 and 40" in result[0].text

    @pytest.mark.asyncio
    async def test_gpio_test_pin_validation_string(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test GPIO pin validation with string pin number."""
        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware", {"component": "gpio", "action": "test", "pin": "invalid"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Invalid pin number" in result[0].text
        assert "between 0 and 40" in result[0].text

    @pytest.mark.asyncio
    async def test_gpio_test_empty_stdout(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test GPIO pin test with empty stdout."""
        hardware_monitoring_tools.container.retropie_client.execute_command.return_value = CommandResult(
            command="gpio read 18",
            exit_code=0,
            stdout="",
            stderr="",
            success=True,
            execution_time=0.1,
        )

        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware", {"component": "gpio", "action": "test", "pin": 18}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "GPIO Pin 18 Test" in result[0].text
        assert (
            "❌ Failed to read GPIO pin 18" in result[0].text
        )  # Empty stdout fails the condition

    @pytest.mark.asyncio
    async def test_errors_check_command_failures(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test error checking with both command failures."""
        hardware_monitoring_tools.container.retropie_client.execute_command.side_effect = [
            CommandResult(
                command="dmesg | grep -i 'error\\|fail\\|warn' | grep -i 'hardware\\|temp\\|power\\|usb' | tail -10",
                exit_code=1,
                stdout="",
                stderr="Command failed",
                success=False,
                execution_time=0.1,
            ),
            CommandResult(
                command="journalctl -p err -n 10 --no-pager",
                exit_code=1,
                stdout="",
                stderr="Command failed",
                success=False,
                execution_time=0.1,
            ),
        ]

        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware", {"component": "errors", "action": "check"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Hardware Error Analysis" in result[0].text
        assert "✅ No hardware errors detected" in result[0].text

    @pytest.mark.asyncio
    async def test_errors_check_only_dmesg_errors(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test error checking with only dmesg errors."""
        hardware_monitoring_tools.container.retropie_client.execute_command.side_effect = [
            CommandResult(
                command="dmesg | grep -i 'error\\|fail\\|warn' | grep -i 'hardware\\|temp\\|power\\|usb' | tail -10",
                exit_code=0,
                stdout="[12345.678] ERROR: Hardware failure detected",
                stderr="",
                success=True,
                execution_time=0.1,
            ),
            CommandResult(
                command="journalctl -p err -n 10 --no-pager",
                exit_code=1,
                stdout="",
                stderr="Command failed",
                success=False,
                execution_time=0.1,
            ),
        ]

        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware", {"component": "errors", "action": "check"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "System Log Errors" in result[0].text
        assert "Hardware failure detected" in result[0].text
        assert "Journal Errors" not in result[0].text

    @pytest.mark.asyncio
    async def test_errors_check_only_journal_errors(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test error checking with only journal errors."""
        hardware_monitoring_tools.container.retropie_client.execute_command.side_effect = [
            CommandResult(
                command="dmesg | grep -i 'error\\|fail\\|warn' | grep -i 'hardware\\|temp\\|power\\|usb' | tail -10",
                exit_code=1,
                stdout="",
                stderr="Command failed",
                success=False,
                execution_time=0.1,
            ),
            CommandResult(
                command="journalctl -p err -n 10 --no-pager",
                exit_code=0,
                stdout="Jan 01 00:00:00 retropie systemd[1]: Critical system error",
                stderr="",
                success=True,
                execution_time=0.1,
            ),
        ]

        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware", {"component": "errors", "action": "check"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Journal Errors" in result[0].text
        assert "Critical system error" in result[0].text
        assert "System Log Errors" not in result[0].text

    @pytest.mark.asyncio
    async def test_all_check_partial_failures(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test comprehensive hardware check with partial failures."""
        call_count = [0]

        def mock_execute_command(command, use_sudo=False) -> CommandResult:  # noqa: ARG001
            call_count[0] += 1
            if "measure_temp" in command and "gpu" not in command:
                return CommandResult(command, 1, "", "Command failed", False, 0.1)
            elif "measure_temp gpu" in command:
                return CommandResult(command, 0, "temp=62.1'C", "", True, 0.1)
            elif "get_throttled" in command:
                return CommandResult(command, 0, "throttled=0x0", "", True, 0.1)
            elif "dmesg" in command:
                return CommandResult(command, 0, "", "", True, 0.1)
            elif "journalctl" in command:
                return CommandResult(command, 0, "-- No entries --", "", True, 0.1)
            else:
                return CommandResult(command, 0, "", "", True, 0.1)

        hardware_monitoring_tools.container.retropie_client.execute_command.side_effect = mock_execute_command

        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware", {"component": "all", "action": "check"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Hardware System Overview" in result[0].text
        assert "Failed to read temperature" in result[0].text  # CPU temp failed
        assert "62.1°C" in result[0].text  # GPU temp succeeded

    @pytest.mark.asyncio
    async def test_all_check_complete_failure(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test comprehensive hardware check with complete failure."""
        hardware_monitoring_tools.container.retropie_client.execute_command.side_effect = Exception(
            "Complete system failure"
        )

        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware", {"component": "all", "action": "check"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        # The exception happens during temperature check, so we get temperature check error
        assert "Failed to check temperatures" in result[0].text
        assert "Complete system failure" in result[0].text

    # Boundary and Edge Case Tests for Helper Methods

    def test_parse_throttling_status_empty_string(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test parsing throttling status with empty string."""
        status = hardware_monitoring_tools._parse_throttling_status("")
        assert "❓ Unable to parse" in status

    def test_parse_throttling_status_none(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test parsing throttling status with None value."""
        # None will be passed as string "None" or cause TypeError
        try:
            status = hardware_monitoring_tools._parse_throttling_status(None)
            assert "❓ Unable to parse" in status
        except TypeError:
            # This is also acceptable since int(None, 16) would raise TypeError
            pass

    def test_parse_throttling_status_max_flags(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test parsing throttling status with all flags set."""
        status = hardware_monitoring_tools._parse_throttling_status("0xfffff")
        assert "🔥 Under-voltage detected" in status
        assert "🌡️ ARM frequency capped" in status
        assert "⚠️ Currently throttled" in status
        assert "🔥 Soft temperature limit active" in status
        assert "🟡 Under-voltage occurred" in status
        assert "🟡 ARM frequency capping occurred" in status
        assert "🟡 Throttling occurred" in status
        assert "🟡 Soft temperature limit occurred" in status

    def test_get_temperature_status_extreme_low(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test temperature status for extremely low temperature."""
        status = hardware_monitoring_tools._get_temperature_status(-10.0)
        assert status == "✅ NORMAL"

    def test_get_temperature_status_extreme_high(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test temperature status for extremely high temperature."""
        status = hardware_monitoring_tools._get_temperature_status(150.0)
        assert status == "🔥 CRITICAL"

    def test_get_temperature_status_fractional_boundaries(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test temperature status at fractional boundaries."""
        assert hardware_monitoring_tools._get_temperature_status(59.9) == "✅ NORMAL"
        assert hardware_monitoring_tools._get_temperature_status(60.1) == "🟡 WARM"
        assert hardware_monitoring_tools._get_temperature_status(69.9) == "🟡 WARM"
        assert hardware_monitoring_tools._get_temperature_status(70.1) == "⚠️ HIGH"
        assert hardware_monitoring_tools._get_temperature_status(79.9) == "⚠️ HIGH"
        assert hardware_monitoring_tools._get_temperature_status(80.1) == "🔥 CRITICAL"

    # Component Method Not Implemented Tests

    @pytest.mark.asyncio
    async def test_temperature_actions_not_implemented(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test all not-implemented temperature actions."""
        # Test all valid but not implemented actions
        for action in ["configure", "inspect"]:
            result = await hardware_monitoring_tools.handle_tool_call(
                "manage_hardware", {"component": "temperature", "action": action}
            )
            assert len(result) == 1
            assert isinstance(result[0], TextContent)
            assert "not yet implemented" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_fan_actions_not_implemented(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test all not-implemented fan actions."""
        # Test all valid but not implemented actions
        for action in ["monitor", "configure", "test"]:
            result = await hardware_monitoring_tools.handle_tool_call(
                "manage_hardware", {"component": "fan", "action": action}
            )
            assert len(result) == 1
            assert isinstance(result[0], TextContent)
            assert "not yet implemented" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_power_actions_not_implemented(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test all not-implemented power actions."""
        # Test all valid but not implemented actions
        for action in ["monitor", "inspect"]:
            result = await hardware_monitoring_tools.handle_tool_call(
                "manage_hardware", {"component": "power", "action": action}
            )
            assert len(result) == 1
            assert isinstance(result[0], TextContent)
            assert "not yet implemented" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_gpio_actions_not_implemented(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test all not-implemented GPIO actions."""
        # Test configure action
        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware", {"component": "gpio", "action": "configure"}
        )
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "not yet implemented" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_errors_actions_not_implemented(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test all not-implemented error actions."""
        # Test inspect action
        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware", {"component": "errors", "action": "inspect", "lines": 50}
        )
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "not yet implemented" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_all_actions_not_implemented(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test all not-implemented all component actions."""
        # Test inspect action
        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware", {"component": "all", "action": "inspect"}
        )
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "not yet implemented" in result[0].text.lower()

    # Additional Validation Tests

    @pytest.mark.asyncio
    async def test_monitor_temperature_default_threshold(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test temperature monitoring with default threshold."""
        # Mock temperature command results
        hardware_monitoring_tools.container.retropie_client.execute_command.side_effect = [
            CommandResult(
                command="vcgencmd measure_temp",
                exit_code=0,
                stdout="temp=68.5'C",
                stderr="",
                success=True,
                execution_time=0.1,
            ),
            CommandResult(
                command="vcgencmd measure_temp gpu",
                exit_code=0,
                stdout="temp=65.2'C",
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

        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware",
            {"component": "temperature", "action": "monitor"},  # No threshold specified
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "68.5°C" in result[0].text
        assert "Monitor Threshold**: 75.0°C" in result[0].text  # Default threshold

    # Comprehensive GPIO Pin Boundary Tests

    @pytest.mark.asyncio
    async def test_gpio_test_pin_boundary_0(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test GPIO pin 0 (valid boundary)."""
        hardware_monitoring_tools.container.retropie_client.execute_command.return_value = CommandResult(
            command="gpio read 0",
            exit_code=0,
            stdout="1",
            stderr="",
            success=True,
            execution_time=0.1,
        )

        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware", {"component": "gpio", "action": "test", "pin": 0}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "GPIO Pin 0 Test" in result[0].text
        assert "HIGH" in result[0].text

    @pytest.mark.asyncio
    async def test_gpio_test_pin_boundary_40(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test GPIO pin 40 (valid boundary)."""
        hardware_monitoring_tools.container.retropie_client.execute_command.return_value = CommandResult(
            command="gpio read 40",
            exit_code=0,
            stdout="0",
            stderr="",
            success=True,
            execution_time=0.1,
        )

        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware", {"component": "gpio", "action": "test", "pin": 40}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "GPIO Pin 40 Test" in result[0].text
        assert "LOW" in result[0].text

    @pytest.mark.asyncio
    async def test_gpio_test_pin_boundary_41(
        self, hardware_monitoring_tools: HardwareMonitoringTools
    ) -> None:
        """Test GPIO pin 41 (invalid boundary)."""
        result = await hardware_monitoring_tools.handle_tool_call(
            "manage_hardware", {"component": "gpio", "action": "test", "pin": 41}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Invalid pin number" in result[0].text
        assert "between 0 and 40" in result[0].text
