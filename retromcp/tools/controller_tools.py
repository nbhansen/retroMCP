"""Controller-related tools for RetroPie."""

from typing import Any
from typing import Dict
from typing import List

from mcp.types import EmbeddedResource
from mcp.types import ImageContent
from mcp.types import TextContent
from mcp.types import Tool

from .base import BaseTool


class ControllerTools(BaseTool):
    """Tools for controller detection and configuration."""

    def get_tools(self) -> List[Tool]:
        """Return list of available controller tools.

        Returns:
            List of Tool objects for controller operations.
        """
        return [
            Tool(
                name="detect_controllers",
                description="Detect controllers connected to the RetroPie",
                inputSchema={"type": "object", "properties": {}, "required": []},
            ),
            Tool(
                name="setup_controller",
                description="Setup a specific controller type (xbox, ps4, 8bitdo)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "controller_type": {
                            "type": "string",
                            "enum": ["xbox", "ps4", "8bitdo"],
                            "description": "Type of controller to setup",
                        }
                    },
                    "required": ["controller_type"],
                },
            ),
            Tool(
                name="test_controller",
                description="Test a controller using jstest",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "device": {
                            "type": "string",
                            "description": "Controller device (e.g., /dev/input/js0)",
                            "default": "/dev/input/js0",
                        }
                    },
                    "required": [],
                },
            ),
            Tool(
                name="configure_controller_mapping",
                description="Configure controller button mappings for EmulationStation",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "force_reconfigure": {
                            "type": "boolean",
                            "description": "Force reconfiguration even if already configured",
                            "default": False,
                        }
                    },
                    "required": [],
                },
            ),
        ]

    async def handle_tool_call(
        self, name: str, arguments: Dict[str, Any]
    ) -> List[TextContent | ImageContent | EmbeddedResource]:
        """Handle tool calls for controller operations.

        Args:
            name: Name of the tool to call.
            arguments: Arguments for the tool.

        Returns:
            List of content objects with the tool's response.
        """
        try:
            if name == "detect_controllers":
                return await self._detect_controllers()
            elif name == "setup_controller":
                return await self._setup_controller(arguments)
            elif name == "test_controller":
                return await self._test_controller(arguments)
            elif name == "configure_controller_mapping":
                return await self._configure_controller_mapping(arguments)
            else:
                return self.format_error(f"Unknown tool: {name}")
        except Exception as e:
            return self.format_error(f"Error in {name}: {e!s}")

    async def _detect_controllers(self) -> List[TextContent]:
        """Detect connected controllers."""
        controllers = self.container.detect_controllers_use_case.execute()

        # Format the output nicely
        output = "🎮 Controller Detection Results:\\n\\n"

        if not controllers:
            output += "No controllers detected.\\n\\n"
        else:
            output += f"Controllers Found: {len(controllers)}\\n\\n"

            for controller in controllers:
                # Add controller icon based on type
                icon = "🎮"
                if (
                    "xbox" in controller.name.lower()
                    or "playstation" in controller.name.lower()
                    or "ps" in controller.controller_type.value
                    or "8bitdo" in controller.name.lower()
                ):
                    icon = "🎮"

                output += f"  {icon} {controller.name}\\n"
                output += f"    • Device: {controller.device_path}\\n"
                output += f"    • Type: {controller.controller_type.value}\\n"
                output += f"    • Vendor ID: {controller.vendor_id}\\n"
                output += f"    • Product ID: {controller.product_id}\\n"
                output += (
                    f"    • Configured: {'✅' if controller.is_configured else '❌'}\\n"
                )
                if controller.driver_required:
                    output += f"    • Driver Required: {controller.driver_required}\\n"
                output += "\\n"

        # Check jstest availability through retropie client
        client = self.container.retropie_client
        result = client.execute_command("which jstest")
        exit_code = result.exit_code
        if exit_code == 0:
            output += "✅ jstest is available for controller testing\\n"
            # If there are controllers, show info for the first one
            if controllers:
                first_device = controllers[0].device_path
                result = client.execute_command(
                    f"jstest --list {first_device} 2>/dev/null || echo 'Device not ready'"
                )
                exit_code = result.exit_code
                js_info = result.stdout
                if exit_code == 0 and js_info.strip():
                    output += f"\\nFirst controller info:\\n{js_info}\\n"
        else:
            output += "⚠️ jstest not installed (install with: sudo apt-get install joystick)\\n"

        return [TextContent(type="text", text=output)]

    async def _setup_controller(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Setup a specific controller type."""
        controller_type = arguments.get("controller_type")

        if not controller_type:
            return self.format_error("No controller type specified")

        result = self.container.setup_controller_use_case.execute(controller_type)

        if result.success:
            return self.format_success(
                f"{result.stdout}\\n\\nYou may need to restart EmulationStation or reboot your Pi for changes to take effect."
            )
        else:
            return self.format_error(result.stderr or "Failed to setup controller")

    async def _test_controller(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Test a controller using jstest."""
        device = arguments.get("device", "/dev/input/js0")

        # Check if jstest is available
        client = self.container.retropie_client
        result = client.execute_command("which jstest")
        exit_code = result.exit_code
        if exit_code != 0:
            return self.format_error(
                "jstest not found. Install with: sudo apt-get install joystick"
            )

        # Test if device exists
        result = client.execute_command(f"test -e {device}")
        exit_code = result.exit_code
        if exit_code != 0:
            return self.format_error(f"Controller device {device} not found")

        # Run jstest for a few seconds
        result = client.execute_command(f"timeout 3 jstest --normal {device} || true")
        exit_code = result.exit_code
        output = result.stdout

        if output:
            return [
                TextContent(
                    type="text",
                    text=f"🎮 Controller Test Results for {device}:\\n\\n{output}",
                )
            ]
        else:
            return self.format_warning(
                f"No output from jstest on {device}. Controller may not be responding."
            )

    async def _configure_controller_mapping(
        self, arguments: Dict[str, Any]
    ) -> List[TextContent]:
        """Configure controller button mappings."""
        force_reconfigure = arguments.get("force_reconfigure", False)

        # Check if a controller is connected
        controllers = self.container.detect_controllers_use_case.execute()
        if not controllers:
            return self.format_error(
                "No controllers detected. Please connect a controller first."
            )

        # Check if EmulationStation is running
        client = self.container.retropie_client
        result = client.execute_command("pgrep emulationstation")
        exit_code = result.exit_code
        if exit_code == 0:
            return self.format_warning(
                "EmulationStation is currently running. Please exit EmulationStation first to configure controllers."
            )

        # Run EmulationStation controller configuration
        if force_reconfigure:
            # Remove existing controller config to force reconfiguration
            result = client.execute_command(
                f"rm -f {self.config.home_dir}/.emulationstation/es_input.cfg"
            )
            exit_code = result.exit_code

        # Start EmulationStation in configuration mode
        output = "🎮 Controller Configuration:\\n\\n"
        output += "Starting EmulationStation controller configuration...\\n"
        output += (
            "Follow the on-screen prompts to configure your controller buttons.\\n\\n"
        )

        # This would typically launch an interactive session
        # For now, we'll provide instructions
        output += "Manual steps:\\n"
        output += "1. Connect your controller\\n"
        output += "2. Start EmulationStation\\n"
        output += "3. Follow the controller configuration wizard\\n"
        output += (
            "4. Press and hold any button on your controller to start configuration\\n"
        )

        return [TextContent(type="text", text=output)]
