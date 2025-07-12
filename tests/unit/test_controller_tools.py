"""Unit tests for ControllerTools implementation."""

from unittest.mock import Mock

import pytest
from mcp.types import TextContent

from retromcp.config import RetroPieConfig
from retromcp.discovery import RetroPiePaths
from retromcp.tools.controller_tools import ControllerTools


class TestControllerTools:
    """Test cases for ControllerTools class."""

    @pytest.fixture
    def mock_ssh_handler(self) -> Mock:
        """Provide mocked SSH handler."""
        mock = Mock()
        mock.detect_controllers = Mock()
        mock.configure_controller = Mock()
        mock.execute_command = Mock()
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
    def controller_tools(
        self, mock_ssh_handler: Mock, test_config: RetroPieConfig
    ) -> ControllerTools:
        """Provide ControllerTools instance with mocked dependencies."""
        return ControllerTools(mock_ssh_handler, test_config)

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
        """Test controller detection with both USB and joystick devices."""
        controller_tools.ssh.detect_controllers.return_value = {
            "usb_devices": [
                "Bus 001 Device 002: ID 045e:02ea Microsoft Corp. Xbox Wireless Controller",
                "Bus 001 Device 003: ID 054c:09cc Sony Corp. DualShock 4 Controller",
                "Bus 001 Device 004: ID 2dc8:ab11 8BitDo SN30 Pro+",
                "Bus 001 Device 005: ID 1234:5678 Random Device Corp. Not a gamepad",
            ],
            "joystick_devices": ["/dev/input/js0", "/dev/input/js1", "/dev/input/js2"],
            "jstest_available": True,
            "js0_info": "Joystick (Xbox Wireless Controller) has 8 axes and 11 buttons",
        }

        result = await controller_tools.handle_tool_call("detect_controllers", {})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        text = result[0].text

        assert "🎮 Controller Detection Results:" in text
        assert "USB Devices:" in text
        assert (
            "🎮 Bus 001 Device 002: ID 045e:02ea Microsoft Corp. Xbox Wireless Controller"
            in text
        )
        assert (
            "🎮 Bus 001 Device 003: ID 054c:09cc Sony Corp. DualShock 4 Controller"
            in text
        )
        assert "🎮 Bus 001 Device 004: ID 2dc8:ab11 8BitDo SN30 Pro+" in text
        assert (
            "Random Device Corp. Not a gamepad" in text
        )  # Should be listed but without gamepad emoji
        assert "Joystick Devices Found: 3" in text
        assert "/dev/input/js0" in text
        assert "/dev/input/js1" in text
        assert "/dev/input/js2" in text
        assert "✅ jstest is available" in text
        assert "Xbox Wireless Controller) has 8 axes and 11 buttons" in text

    @pytest.mark.asyncio
    async def test_detect_controllers_no_joystick_devices(
        self, controller_tools: ControllerTools
    ) -> None:
        """Test controller detection when no joystick devices are found."""
        controller_tools.ssh.detect_controllers.return_value = {
            "usb_devices": [
                "Bus 001 Device 002: ID 045e:02ea Microsoft Corp. Xbox Wireless Controller",
            ],
            "jstest_available": False,
        }

        result = await controller_tools.handle_tool_call("detect_controllers", {})
        text = result[0].text

        assert "🎮 Controller Detection Results:" in text
        assert (
            "🎮 Bus 001 Device 002: ID 045e:02ea Microsoft Corp. Xbox Wireless Controller"
            in text
        )
        assert "No joystick devices found in /dev/input/" in text
        assert "⚠️ jstest not installed" in text
        assert "sudo apt-get install joystick" in text

    @pytest.mark.asyncio
    async def test_detect_controllers_keyword_matching(
        self, controller_tools: ControllerTools
    ) -> None:
        """Test controller detection keyword matching for different device types."""
        controller_tools.ssh.detect_controllers.return_value = {
            "usb_devices": [
                "Xbox gamepad device",
                "PlayStation controller",
                "Generic joystick",
                "Sony DualShock",
                "8BitDo device",
                "Random keyboard",
                "Gamepad Pro",
            ],
            "joystick_devices": [],
            "jstest_available": True,
        }

        result = await controller_tools.handle_tool_call("detect_controllers", {})
        text = result[0].text

        # Should detect gaming devices
        assert "🎮 Xbox gamepad device" in text
        assert "🎮 PlayStation controller" in text
        assert "🎮 Generic joystick" in text
        assert "🎮 Sony DualShock" in text
        assert "🎮 8BitDo device" in text
        assert "🎮 Gamepad Pro" in text

        # Should not mark keyboard as gaming device
        assert "🎮 Random keyboard" not in text
        assert "Random keyboard" in text  # Should still be listed

    @pytest.mark.asyncio
    async def test_detect_controllers_empty_results(
        self, controller_tools: ControllerTools
    ) -> None:
        """Test controller detection with no devices found."""
        controller_tools.ssh.detect_controllers.return_value = {
            "usb_devices": [],
            "jstest_available": False,
        }

        result = await controller_tools.handle_tool_call("detect_controllers", {})
        text = result[0].text

        assert "🎮 Controller Detection Results:" in text
        assert "USB Devices:" in text
        assert "No joystick devices found in /dev/input/" in text
        assert "⚠️ jstest not installed" in text

    @pytest.mark.asyncio
    async def test_setup_controller_xbox(
        self, controller_tools: ControllerTools
    ) -> None:
        """Test Xbox controller setup."""
        controller_tools.ssh.configure_controller.return_value = (
            True,
            "Xbox controller configured successfully",
        )

        result = await controller_tools.handle_tool_call(
            "setup_controller", {"controller_type": "xbox"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Xbox controller configured successfully" in result[0].text
        controller_tools.ssh.configure_controller.assert_called_once_with("xbox")

    @pytest.mark.asyncio
    async def test_setup_controller_ps4(
        self, controller_tools: ControllerTools
    ) -> None:
        """Test PS4 controller setup."""
        controller_tools.ssh.configure_controller.return_value = (
            True,
            "PS4 controller drivers installed and configured",
        )

        result = await controller_tools.handle_tool_call(
            "setup_controller", {"controller_type": "ps4"}
        )

        assert len(result) == 1
        assert "✅ PS4 controller drivers installed" in result[0].text
        controller_tools.ssh.configure_controller.assert_called_once_with("ps4")

    @pytest.mark.asyncio
    async def test_setup_controller_8bitdo(
        self, controller_tools: ControllerTools
    ) -> None:
        """Test 8BitDo controller setup."""
        controller_tools.ssh.configure_controller.return_value = (
            True,
            "8BitDo controller configured in Nintendo mode",
        )

        result = await controller_tools.handle_tool_call(
            "setup_controller", {"controller_type": "8bitdo"}
        )

        assert len(result) == 1
        assert "8BitDo controller configured" in result[0].text
        controller_tools.ssh.configure_controller.assert_called_once_with("8bitdo")

    @pytest.mark.asyncio
    async def test_setup_controller_failure(
        self, controller_tools: ControllerTools
    ) -> None:
        """Test controller setup failure."""
        controller_tools.ssh.configure_controller.return_value = (
            False,
            "Failed to install controller drivers: Permission denied",
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
    async def test_test_controller_default_device(
        self, controller_tools: ControllerTools
    ) -> None:
        """Test controller testing with default device."""
        # Mock the execute_command calls in sequence: which jstest, test device exists, run jstest
        controller_tools.ssh.execute_command.side_effect = [
            (0, "/usr/bin/jstest", ""),  # jstest found
            (0, "", ""),  # device exists
            (0, "Buttons: A, B, X, Y working\nAxes: Left stick, Right stick working", ""),  # jstest output
        ]

        result = await controller_tools.handle_tool_call("test_controller", {})

        assert len(result) == 1
        assert "Controller Test Results" in result[0].text
        assert "Buttons: A, B, X, Y working" in result[0].text

    @pytest.mark.asyncio
    async def test_test_controller_specific_device(
        self, controller_tools: ControllerTools
    ) -> None:
        """Test controller testing with specific device."""
        # Mock the execute_command calls for specific device
        controller_tools.ssh.execute_command.side_effect = [
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
        controller_tools.ssh.execute_command.side_effect = [
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
        # Mock detect_controllers to return joystick devices
        controller_tools.ssh.detect_controllers.return_value = {
            "joystick_devices": ["/dev/input/js0"],
            "usb_devices": ["Microsoft Xbox Controller"]
        }
        # Mock execute_command for EmulationStation check
        controller_tools.ssh.execute_command.return_value = (1, "", "")  # ES not running

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
        # Mock detect_controllers to return joystick devices
        controller_tools.ssh.detect_controllers.return_value = {
            "joystick_devices": ["/dev/input/js0"]
        }
        # Mock execute_command calls: ES check, rm config file
        controller_tools.ssh.execute_command.side_effect = [
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
        # Mock detect_controllers to return no joystick devices
        controller_tools.ssh.detect_controllers.return_value = {
            "usb_devices": []  # No joystick devices
        }

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
        controller_tools.ssh.detect_controllers.side_effect = Exception(
            "SSH connection lost"
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
        assert hasattr(controller_tools, "ssh")
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
        controller_tools.ssh.detect_controllers.return_value = {
            "usb_devices": ["Xbox controller"],
            # Missing joystick_devices, jstest_available, etc.
        }

        result = await controller_tools.handle_tool_call("detect_controllers", {})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        text = result[0].text

        assert "🎮 Controller Detection Results:" in text
        assert "🎮 Xbox controller" in text
        # Should handle missing keys gracefully
        assert "No joystick devices found" in text

    @pytest.mark.asyncio
    async def test_detect_controllers_case_insensitive_matching(
        self, controller_tools: ControllerTools
    ) -> None:
        """Test that controller detection is case insensitive."""
        controller_tools.ssh.detect_controllers.return_value = {
            "usb_devices": [
                "XBOX CONTROLLER",
                "playstation device",
                "8BITDO GAMEPAD",
                "sony DUALSHOCK",
            ],
            "joystick_devices": [],
            "jstest_available": True,
        }

        result = await controller_tools.handle_tool_call("detect_controllers", {})
        text = result[0].text

        # Should detect all as gaming devices regardless of case
        assert "🎮 XBOX CONTROLLER" in text
        assert "🎮 playstation device" in text
        assert "🎮 8BITDO GAMEPAD" in text
        assert "🎮 sony DUALSHOCK" in text

    @pytest.mark.asyncio
    async def test_controller_setup_types_validation(
        self, controller_tools: ControllerTools
    ) -> None:
        """Test that only valid controller types are supported."""
        # Test all valid types
        valid_types = ["xbox", "ps4", "8bitdo"]

        for controller_type in valid_types:
            controller_tools.ssh.configure_controller.return_value = (
                True,
                f"{controller_type} configured",
            )

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
        controller_tools.ssh.detect_controllers.return_value = {
            "usb_devices": [],
            "joystick_devices": [
                "/dev/input/js0",
                "/dev/input/js1",
                "/dev/input/js2",
                "/dev/input/js3",
            ],
            "jstest_available": True,
        }

        result = await controller_tools.handle_tool_call("detect_controllers", {})
        text = result[0].text

        assert "Joystick Devices Found: 4" in text
        assert "/dev/input/js0" in text
        assert "/dev/input/js1" in text
        assert "/dev/input/js2" in text
        assert "/dev/input/js3" in text
