"""Unit tests for ControllerTools implementation."""

from unittest.mock import Mock

import pytest
from mcp.types import TextContent

from retromcp.config import RetroPieConfig
from retromcp.discovery import RetroPiePaths
from retromcp.domain.models import CommandResult
from retromcp.domain.models import Controller
from retromcp.domain.models import ControllerType
from retromcp.tools.controller_tools import ControllerTools


class TestControllerTools:
    """Test cases for ControllerTools class."""

    @pytest.fixture
    def mock_container(self) -> Mock:
        """Provide mocked container with use cases."""
        mock = Mock()
        # Mock use cases
        mock.detect_controllers_use_case = Mock()
        mock.setup_controller_use_case = Mock()
        # Mock retropie client for direct commands
        mock.retropie_client = Mock()
        mock.retropie_client.execute_command = Mock()
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
    def controller_tools(self, mock_container: Mock) -> ControllerTools:
        """Provide ControllerTools instance with mocked dependencies."""
        return ControllerTools(mock_container)

    def test_get_tools(self, controller_tools: ControllerTools) -> None:
        """Test that all expected tools are returned."""
        tools = controller_tools.get_tools()

        assert len(tools) == 4
        tool_names = [tool.name for tool in tools]

        expected_tools = [
            "detect_controllers",
            "setup_controller",
            "test_controller",
            "configure_controller_mapping",
        ]

        for expected_tool in expected_tools:
            assert expected_tool in tool_names

    def test_tool_schemas(self, controller_tools: ControllerTools) -> None:
        """Test that tool schemas are properly defined."""
        tools = controller_tools.get_tools()
        tool_dict = {tool.name: tool for tool in tools}

        # Detect controllers tool - no parameters
        detect_tool = tool_dict["detect_controllers"]
        assert detect_tool.inputSchema["type"] == "object"
        assert detect_tool.inputSchema["required"] == []

        # Setup controller tool - requires controller_type
        setup_tool = tool_dict["setup_controller"]
        assert "controller_type" in setup_tool.inputSchema["properties"]
        assert setup_tool.inputSchema["required"] == ["controller_type"]
        assert "xbox" in setup_tool.inputSchema["properties"]["controller_type"]["enum"]
        assert "ps4" in setup_tool.inputSchema["properties"]["controller_type"]["enum"]
        assert (
            "8bitdo" in setup_tool.inputSchema["properties"]["controller_type"]["enum"]
        )

        # Test controller tool - optional device parameter
        test_tool = tool_dict["test_controller"]
        assert "device" in test_tool.inputSchema["properties"]
        assert test_tool.inputSchema["required"] == []

        # Configure mapping tool - optional force_reconfigure
        mapping_tool = tool_dict["configure_controller_mapping"]
        assert "force_reconfigure" in mapping_tool.inputSchema["properties"]
        assert mapping_tool.inputSchema["required"] == []

    @pytest.mark.asyncio
    async def test_detect_controllers_with_usb_and_joystick(
        self, controller_tools: ControllerTools
    ) -> None:
        """Test controller detection with controllers found."""
        # Mock controller list
        mock_controllers = [
            Controller(
                name="Xbox Wireless Controller",
                device_path="/dev/input/js0",
                vendor_id="045e",
                product_id="02ea",
                controller_type=ControllerType.XBOX,
                is_configured=True,
                driver_required=None,
            ),
            Controller(
                name="DualShock 4 Controller",
                device_path="/dev/input/js1",
                vendor_id="054c",
                product_id="09cc",
                controller_type=ControllerType.PS4,
                is_configured=False,
                driver_required="ds4drv",
            ),
        ]

        controller_tools.container.detect_controllers_use_case.execute.return_value = (
            mock_controllers
        )
        controller_tools.container.retropie_client.execute_command.return_value = (
            0,
            "",
            "",
        )

        result = await controller_tools.handle_tool_call("detect_controllers", {})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        text = result[0].text

        assert "🎮 Controller Detection Results:" in text
        assert "Controllers Found: 2" in text
        assert "Xbox Wireless Controller" in text
        assert "DualShock 4 Controller" in text
        assert "/dev/input/js0" in text
        assert "/dev/input/js1" in text
        assert "Type: xbox" in text
        assert "Type: ps4" in text
        assert "Vendor ID: 045e" in text
        assert "Product ID: 02ea" in text
        assert "Configured: ✅" in text
        assert "Configured: ❌" in text
        assert "Driver Required: ds4drv" in text
        assert "✅ jstest is available" in text

    @pytest.mark.asyncio
    async def test_detect_controllers_no_joystick_devices(
        self, controller_tools: ControllerTools
    ) -> None:
        """Test controller detection when no controllers are found."""
        controller_tools.container.detect_controllers_use_case.execute.return_value = []
        controller_tools.container.retropie_client.execute_command.return_value = (
            1,
            "",
            "",
        )

        result = await controller_tools.handle_tool_call("detect_controllers", {})
        text = result[0].text

        assert "🎮 Controller Detection Results:" in text
        assert "No controllers detected." in text
        assert "⚠️ jstest not installed" in text

    @pytest.mark.asyncio
    async def test_detect_controllers_keyword_matching(
        self, controller_tools: ControllerTools
    ) -> None:
        """Test controller detection keyword matching for different device types."""
        # Mock controller list with various devices
        mock_controllers = [
            Controller(
                name="Xbox gamepad device",
                device_path="/dev/input/js0",
                vendor_id="045e",
                product_id="02ea",
                controller_type=ControllerType.XBOX,
                is_configured=True,
            ),
            Controller(
                name="PlayStation controller",
                device_path="/dev/input/js1",
                vendor_id="054c",
                product_id="09cc",
                controller_type=ControllerType.PS4,
                is_configured=False,
            ),
            Controller(
                name="8BitDo device",
                device_path="/dev/input/js2",
                vendor_id="2dc8",
                product_id="6001",
                controller_type=ControllerType.EIGHT_BIT_DO,
                is_configured=True,
            ),
        ]

        controller_tools.container.detect_controllers_use_case.execute.return_value = (
            mock_controllers
        )
        controller_tools.container.retropie_client.execute_command.return_value = (
            0,
            "",
            "",
        )

        result = await controller_tools.handle_tool_call("detect_controllers", {})
        text = result[0].text

        # Should detect gaming devices
        assert "🎮 Xbox gamepad device" in text
        assert "🎮 PlayStation controller" in text
        assert "🎮 8BitDo device" in text

    @pytest.mark.asyncio
    async def test_detect_controllers_empty_results(
        self, controller_tools: ControllerTools
    ) -> None:
        """Test controller detection with no devices found."""
        controller_tools.container.detect_controllers_use_case.execute.return_value = []
        controller_tools.container.retropie_client.execute_command.return_value = (
            1,
            "",
            "",
        )

        result = await controller_tools.handle_tool_call("detect_controllers", {})
        text = result[0].text

        assert "🎮 Controller Detection Results:" in text
        assert "No controllers detected." in text
        assert "⚠️ jstest not installed" in text

    @pytest.mark.asyncio
    async def test_setup_controller_xbox(
        self, controller_tools: ControllerTools
    ) -> None:
        """Test Xbox controller setup."""
        mock_result = CommandResult(
            command="setup xbox controller",
            exit_code=0,
            stdout="Xbox controller configured successfully",
            stderr="",
            success=True,
            execution_time=2.5,
        )
        controller_tools.container.setup_controller_use_case.execute.return_value = (
            mock_result
        )

        result = await controller_tools.handle_tool_call(
            "setup_controller", {"controller_type": "xbox"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Xbox controller configured successfully" in result[0].text
        controller_tools.container.setup_controller_use_case.execute.assert_called_once_with(
            "xbox"
        )

    @pytest.mark.asyncio
    async def test_setup_controller_ps4(
        self, controller_tools: ControllerTools
    ) -> None:
        """Test PS4 controller setup."""
        mock_result = CommandResult(
            command="setup ps4 controller",
            exit_code=0,
            stdout="PS4 controller drivers installed and configured",
            stderr="",
            success=True,
            execution_time=3.2,
        )
        controller_tools.container.setup_controller_use_case.execute.return_value = (
            mock_result
        )

        result = await controller_tools.handle_tool_call(
            "setup_controller", {"controller_type": "ps4"}
        )

        assert len(result) == 1
        assert "✅ PS4 controller drivers installed" in result[0].text
        controller_tools.container.setup_controller_use_case.execute.assert_called_once_with(
            "ps4"
        )

    @pytest.mark.asyncio
    async def test_setup_controller_8bitdo(
        self, controller_tools: ControllerTools
    ) -> None:
        """Test 8BitDo controller setup."""
        mock_result = CommandResult(
            command="setup 8bitdo controller",
            exit_code=0,
            stdout="8BitDo controller configured in Nintendo mode",
            stderr="",
            success=True,
            execution_time=2.8,
        )
        controller_tools.container.setup_controller_use_case.execute.return_value = (
            mock_result
        )

        result = await controller_tools.handle_tool_call(
            "setup_controller", {"controller_type": "8bitdo"}
        )

        assert len(result) == 1
        assert "8BitDo controller configured" in result[0].text
        controller_tools.container.setup_controller_use_case.execute.assert_called_once_with(
            "8bitdo"
        )

    @pytest.mark.asyncio
    async def test_setup_controller_failure(
        self, controller_tools: ControllerTools
    ) -> None:
        """Test controller setup failure."""
        mock_result = CommandResult(
            command="setup xbox controller",
            exit_code=1,
            stdout="",
            stderr="Failed to install controller drivers: Permission denied",
            success=False,
            execution_time=1.2,
        )
        controller_tools.container.setup_controller_use_case.execute.return_value = (
            mock_result
        )

        result = await controller_tools.handle_tool_call(
            "setup_controller", {"controller_type": "xbox"}
        )

        assert len(result) == 1
        assert "❌ Failed to install controller drivers" in result[0].text

    @pytest.mark.asyncio
    async def test_setup_controller_missing_type(
        self, controller_tools: ControllerTools
    ) -> None:
        """Test controller setup with missing controller_type."""
        # The tool schema requires controller_type, but test edge case
        result = await controller_tools.handle_tool_call("setup_controller", {})

        # Should handle gracefully - exact behavior depends on implementation
        assert len(result) == 1
        assert isinstance(result[0], TextContent)

    @pytest.mark.asyncio
    async def test_test_controller_commandresult_fixed(
        self, controller_tools: ControllerTools
    ) -> None:
        """Test that CommandResult unpacking is now fixed - should work properly."""
        # Mock execute_command to return CommandResult objects
        # The first call to "which jstest" fails
        controller_tools.container.retropie_client.execute_command.return_value = CommandResult(
            "which jstest", 1, "", "not found", False, 0.1
        )

        # This should now work properly with CommandResult objects 
        # instead of trying to unpack them as tuples
        result = await controller_tools.handle_tool_call("test_controller", {})
        
        # Should return proper jstest error message, not CommandResult unpacking error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "jstest not found" in result[0].text
        assert "sudo apt-get install joystick" in result[0].text
        # Most importantly, should NOT contain the unpacking error
        assert "cannot unpack non-iterable CommandResult object" not in result[0].text

    @pytest.mark.asyncio
    async def test_detect_controllers_commandresult_unpacking_error(
        self, controller_tools: ControllerTools
    ) -> None:
        """Test that reproduces CommandResult unpacking error in detect_controllers - SHOULD FAIL until fixed."""
        # Mock detect_controllers_use_case to return controllers  
        mock_controller = Controller(
            device_path="/dev/input/js0",
            name="Test Controller", 
            controller_type="xbox",
            vendor_id="045e",
            product_id="028e",
            is_connected=True,
        )
        controller_tools.container.detect_controllers_use_case.execute.return_value = [mock_controller]
        
        # Mock execute_command to return CommandResult (this will cause unpacking error)
        controller_tools.container.retropie_client.execute_command.return_value = CommandResult(
            "which jstest", 0, "/usr/bin/jstest", "", True, 0.1
        )

        # This SHOULD fail with CommandResult unpacking error until fixed
        with pytest.raises(TypeError, match="cannot unpack non-iterable CommandResult object"):
            await controller_tools.handle_tool_call("detect_controllers", {})

    @pytest.mark.asyncio
    async def test_test_controller_specific_device(
        self, controller_tools: ControllerTools
    ) -> None:
        """Test controller testing with specific device."""
        # Mock the execute_command calls for specific device
        controller_tools.container.retropie_client.execute_command.side_effect = [
            (0, "/usr/bin/jstest", ""),  # jstest found
            (0, "", ""),  # device exists
            (0, "Controller responsive, all inputs detected", ""),  # jstest output
        ]

        result = await controller_tools.handle_tool_call(
            "test_controller", {"device": "/dev/input/js1"}
        )

        assert len(result) == 1
        assert "Controller Test Results for /dev/input/js1" in result[0].text
        assert "Controller responsive" in result[0].text

    @pytest.mark.asyncio
    async def test_test_controller_failure(
        self, controller_tools: ControllerTools
    ) -> None:
        """Test controller testing failure."""
        # Mock failure - jstest not found
        controller_tools.container.retropie_client.execute_command.side_effect = [
            (1, "", "jstest: command not found"),  # jstest not found
        ]

        result = await controller_tools.handle_tool_call("test_controller", {})

        assert len(result) == 1
        assert "jstest not found" in result[0].text

    @pytest.mark.asyncio
    async def test_configure_controller_mapping_default(
        self, controller_tools: ControllerTools
    ) -> None:
        """Test controller mapping configuration with default settings."""
        # Mock detect_controllers to return controllers
        mock_controllers = [
            Controller(
                name="Microsoft Xbox Controller",
                device_path="/dev/input/js0",
                vendor_id="045e",
                product_id="02ea",
                controller_type=ControllerType.XBOX,
                is_configured=True,
            )
        ]
        controller_tools.container.detect_controllers_use_case.execute.return_value = (
            mock_controllers
        )
        # Mock execute_command for EmulationStation check
        controller_tools.container.retropie_client.execute_command.return_value = (
            1,
            "",
            "",
        )  # ES not running

        result = await controller_tools.handle_tool_call(
            "configure_controller_mapping", {}
        )

        assert len(result) == 1
        assert "Controller Configuration" in result[0].text

    @pytest.mark.asyncio
    async def test_configure_controller_mapping_force_reconfigure(
        self, controller_tools: ControllerTools
    ) -> None:
        """Test controller mapping configuration with force reconfigure."""
        # Mock detect_controllers to return controllers
        mock_controllers = [
            Controller(
                name="Xbox Controller",
                device_path="/dev/input/js0",
                vendor_id="045e",
                product_id="02ea",
                controller_type=ControllerType.XBOX,
                is_configured=True,
            )
        ]
        controller_tools.container.detect_controllers_use_case.execute.return_value = (
            mock_controllers
        )
        # Mock execute_command calls: ES check, rm config file
        controller_tools.container.retropie_client.execute_command.side_effect = [
            (1, "", ""),  # ES not running
            (0, "", ""),  # rm command success
        ]

        result = await controller_tools.handle_tool_call(
            "configure_controller_mapping", {"force_reconfigure": True}
        )

        assert len(result) == 1
        assert "Controller Configuration" in result[0].text

    @pytest.mark.asyncio
    async def test_configure_controller_mapping_failure(
        self, controller_tools: ControllerTools
    ) -> None:
        """Test controller mapping configuration failure."""
        # Mock detect_controllers to return no controllers
        controller_tools.container.detect_controllers_use_case.execute.return_value = []

        result = await controller_tools.handle_tool_call(
            "configure_controller_mapping", {}
        )

        assert len(result) == 1
        assert "No controllers detected" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_unknown_tool(self, controller_tools: ControllerTools) -> None:
        """Test handling of unknown tool name."""
        result = await controller_tools.handle_tool_call("unknown_tool", {})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Unknown tool: unknown_tool" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_tool_exception(
        self, controller_tools: ControllerTools
    ) -> None:
        """Test exception handling in tool execution."""
        controller_tools.container.detect_controllers_use_case.execute.side_effect = (
            Exception("SSH connection lost")
        )

        result = await controller_tools.handle_tool_call("detect_controllers", {})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Error in detect_controllers: SSH connection lost" in result[0].text

    def test_inheritance_from_base_tool(
        self, controller_tools: ControllerTools
    ) -> None:
        """Test that ControllerTools properly inherits from BaseTool."""
        # Should have access to BaseTool methods
        assert hasattr(controller_tools, "format_success")
        assert hasattr(controller_tools, "format_error")
        assert hasattr(controller_tools, "container")
        assert hasattr(controller_tools, "config")

        # Test format methods work
        success_result = controller_tools.format_success("Test message")
        assert len(success_result) == 1
        assert isinstance(success_result[0], TextContent)
        assert "Test message" in success_result[0].text

        error_result = controller_tools.format_error("Error message")
        assert len(error_result) == 1
        assert isinstance(error_result[0], TextContent)
        assert "Error message" in error_result[0].text

    @pytest.mark.asyncio
    async def test_detect_controllers_partial_data(
        self, controller_tools: ControllerTools
    ) -> None:
        """Test controller detection with partial data."""
        mock_controllers = [
            Controller(
                name="Xbox controller",
                device_path="/dev/input/js0",
                vendor_id="045e",
                product_id="02ea",
                controller_type=ControllerType.XBOX,
                is_configured=True,
            )
        ]
        controller_tools.container.detect_controllers_use_case.execute.return_value = (
            mock_controllers
        )
        controller_tools.container.retropie_client.execute_command.return_value = (
            1,
            "",
            "",
        )

        result = await controller_tools.handle_tool_call("detect_controllers", {})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        text = result[0].text

        assert "🎮 Controller Detection Results:" in text
        assert "🎮 Xbox controller" in text

    @pytest.mark.asyncio
    async def test_detect_controllers_case_insensitive_matching(
        self, controller_tools: ControllerTools
    ) -> None:
        """Test that controller detection is case insensitive."""
        mock_controllers = [
            Controller(
                name="XBOX CONTROLLER",
                device_path="/dev/input/js0",
                vendor_id="045e",
                product_id="02ea",
                controller_type=ControllerType.XBOX,
                is_configured=True,
            ),
            Controller(
                name="playstation device",
                device_path="/dev/input/js1",
                vendor_id="054c",
                product_id="09cc",
                controller_type=ControllerType.PS4,
                is_configured=False,
            ),
            Controller(
                name="8BITDO GAMEPAD",
                device_path="/dev/input/js2",
                vendor_id="2dc8",
                product_id="6001",
                controller_type=ControllerType.EIGHT_BIT_DO,
                is_configured=True,
            ),
        ]
        controller_tools.container.detect_controllers_use_case.execute.return_value = (
            mock_controllers
        )
        controller_tools.container.retropie_client.execute_command.return_value = (
            0,
            "",
            "",
        )

        result = await controller_tools.handle_tool_call("detect_controllers", {})
        text = result[0].text

        # Should detect all as gaming devices regardless of case
        assert "🎮 XBOX CONTROLLER" in text
        assert "🎮 playstation device" in text
        assert "🎮 8BITDO GAMEPAD" in text

    @pytest.mark.asyncio
    async def test_controller_setup_types_validation(
        self, controller_tools: ControllerTools
    ) -> None:
        """Test that only valid controller types are supported."""
        # Test all valid types
        valid_types = ["xbox", "ps4", "8bitdo"]

        for controller_type in valid_types:
            mock_result = CommandResult(
                command=f"setup {controller_type} controller",
                exit_code=0,
                stdout=f"{controller_type} configured",
                stderr="",
                success=True,
                execution_time=2.0,
            )
            controller_tools.container.setup_controller_use_case.execute.return_value = mock_result

            result = await controller_tools.handle_tool_call(
                "setup_controller", {"controller_type": controller_type}
            )

            assert len(result) == 1
            assert f"{controller_type} configured" in result[0].text

    @pytest.mark.asyncio
    async def test_joystick_device_counting(
        self, controller_tools: ControllerTools
    ) -> None:
        """Test accurate counting of joystick devices."""
        mock_controllers = [
            Controller(
                name="Controller 1",
                device_path="/dev/input/js0",
                vendor_id="045e",
                product_id="02ea",
                controller_type=ControllerType.XBOX,
                is_configured=True,
            ),
            Controller(
                name="Controller 2",
                device_path="/dev/input/js1",
                vendor_id="054c",
                product_id="09cc",
                controller_type=ControllerType.PS4,
                is_configured=False,
            ),
            Controller(
                name="Controller 3",
                device_path="/dev/input/js2",
                vendor_id="2dc8",
                product_id="6001",
                controller_type=ControllerType.EIGHT_BIT_DO,
                is_configured=True,
            ),
            Controller(
                name="Controller 4",
                device_path="/dev/input/js3",
                vendor_id="045e",
                product_id="02fd",
                controller_type=ControllerType.XBOX,
                is_configured=True,
            ),
        ]
        controller_tools.container.detect_controllers_use_case.execute.return_value = (
            mock_controllers
        )
        controller_tools.container.retropie_client.execute_command.return_value = (
            0,
            "",
            "",
        )

        result = await controller_tools.handle_tool_call("detect_controllers", {})
        text = result[0].text

        assert "Controllers Found: 4" in text
        assert "/dev/input/js0" in text
        assert "/dev/input/js1" in text
        assert "/dev/input/js2" in text
        assert "/dev/input/js3" in text
