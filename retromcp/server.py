#!/usr/bin/env python3
"""RetroMCP Server - MCP server for RetroPie configuration and management."""

import asyncio
import logging
from pathlib import Path
from typing import Any
from typing import Dict
from typing import List

from dotenv import load_dotenv
from mcp.server import NotificationOptions
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import EmbeddedResource
from mcp.types import ImageContent
from mcp.types import Resource
from mcp.types import TextContent
from mcp.types import Tool

try:
    from .config import RetroPieConfig
    from .config import ServerConfig
    from .container import Container
    from .profile import SystemProfileManager
    from .tools import ControllerTools
    from .tools import EmulationStationTools
    from .tools import HardwareTools
    from .tools import RetroPieTools
    from .tools import SystemTools
except ImportError:
    from profile import SystemProfileManager

    from config import RetroPieConfig
    from config import ServerConfig
    from container import Container
    from tools import ControllerTools
    from tools import EmulationStationTools
    from tools import HardwareTools
    from tools import RetroPieTools
    from tools import SystemTools

# Load environment variables
load_dotenv()


class RetroMCPServer:
    """Main RetroMCP server class with proper dependency injection."""

    def __init__(self, config: RetroPieConfig, server_config: ServerConfig) -> None:
        """Initialize the server with configuration."""
        self.config = config
        self.server_config = server_config
        self.server = Server(server_config.name)
        self.container = Container(config)
        self.profile_manager = SystemProfileManager()

        # Register handlers
        self.server.list_tools()(self.list_tools)
        self.server.call_tool()(self.call_tool)
        self.server.list_resources()(self.list_resources)
        self.server.read_resource()(self.read_resource)

    async def list_resources(self) -> List[Resource]:
        """List available MCP resources."""
        return [
            Resource(
                uri="retropie://system-profile",
                name="RetroPie System Profile",
                description="Current system configuration and learned context",
                mimeType="text/plain",
            )
        ]

    async def read_resource(self, uri: str) -> str:
        """Read an MCP resource."""
        if uri == "retropie://system-profile":
            try:
                # Ensure discovery and get current profile
                if not self.container.connect():
                    return "❌ Unable to connect to RetroPie system"

                # Get or create system profile
                if self.container.config.paths:
                    profile = self.profile_manager.get_or_create_profile(
                        self.container.config.paths
                    )
                    return profile.to_context_summary()
                else:
                    return "⚠️ System discovery not completed yet"

            except Exception as e:
                return f"❌ Error loading system profile: {e}"
        else:
            return f"❌ Unknown resource: {uri}"

    async def list_tools(self) -> List[Tool]:
        """List available tools from all modules."""
        tools = []

        try:
            # Ensure connection is established
            if not self.container.connect():
                raise ConnectionError("Failed to connect to RetroPie")

            # Get tool instances from container
            tool_instances = {
                "system": SystemTools(
                    self.container.ssh_handler, self.container.config
                ),
                "controller": ControllerTools(
                    self.container.ssh_handler, self.container.config
                ),
                "retropie": RetroPieTools(
                    self.container.ssh_handler, self.container.config
                ),
                "emulationstation": EmulationStationTools(
                    self.container.ssh_handler, self.container.config
                ),
                "hardware": HardwareTools(
                    self.container.ssh_handler, self.container.config
                ),
            }

            # Collect tools from all modules
            for _, tool_instance in tool_instances.items():
                module_tools = tool_instance.get_tools()
                tools.extend(module_tools)

        except Exception as e:
            # Return a basic error tool if we can't connect
            tools = [
                Tool(
                    name="connection_error",
                    description=f"Error connecting to RetroPie: {e!s}",
                    inputSchema={"type": "object", "properties": {}, "required": []},
                )
            ]

        return tools

    async def call_tool(
        self, name: str, arguments: Dict[str, Any]
    ) -> List[TextContent | ImageContent | EmbeddedResource]:
        """Handle tool calls by routing to appropriate module."""
        if name == "connection_error":
            return [
                TextContent(
                    type="text",
                    text="❌ Connection failed. Please check your .env configuration:\n- RETROPIE_HOST\n- RETROPIE_USERNAME\n- RETROPIE_PASSWORD or RETROPIE_SSH_KEY_PATH",
                )
            ]

        try:
            # Ensure connection is established
            if not self.container.connect():
                raise ConnectionError("Failed to connect to RetroPie")

            # Get tool instances from container
            tool_instances = {
                "system": SystemTools(
                    self.container.ssh_handler, self.container.config
                ),
                "controller": ControllerTools(
                    self.container.ssh_handler, self.container.config
                ),
                "retropie": RetroPieTools(
                    self.container.ssh_handler, self.container.config
                ),
                "emulationstation": EmulationStationTools(
                    self.container.ssh_handler, self.container.config
                ),
                "hardware": HardwareTools(
                    self.container.ssh_handler, self.container.config
                ),
            }

            # Define tool routing - maps tool names to modules
            tool_routing = {
                # System tools
                "test_connection": "system",
                "system_info": "system",
                "install_packages": "system",
                "check_bios": "system",
                "update_system": "system",
                # Controller tools
                "detect_controllers": "controller",
                "setup_controller": "controller",
                "test_controller": "controller",
                "configure_controller_mapping": "controller",
                # RetroPie tools
                "run_retropie_setup": "retropie",
                "install_emulator": "retropie",
                "manage_roms": "retropie",
                "configure_overclock": "retropie",
                "configure_audio": "retropie",
                # EmulationStation tools
                "restart_emulationstation": "emulationstation",
                "configure_themes": "emulationstation",
                "manage_gamelists": "emulationstation",
                "configure_es_settings": "emulationstation",
                # Hardware tools
                "check_temperatures": "hardware",
                "monitor_fan_control": "hardware",
                "check_power_supply": "hardware",
                "inspect_hardware_errors": "hardware",
                "check_gpio_status": "hardware",
            }

            # Route tool call to appropriate module
            if name in tool_routing:
                module_name = tool_routing[name]
                tool_instance = tool_instances[module_name]
                result = await tool_instance.handle_tool_call(name, arguments)

                # Update profile with any new information learned
                if self.container.config.paths:
                    self._update_profile_from_tool_execution(name, arguments, result)

                return result
            else:
                return [TextContent(type="text", text=f"❌ Unknown tool: {name}")]

        except Exception as e:
            return [TextContent(type="text", text=f"❌ Error executing {name}: {e!s}")]

    def _update_profile_from_tool_execution(
        self, tool_name: str, arguments: Dict[str, Any], result: List[Any]
    ) -> None:
        """Update system profile based on tool execution results."""
        try:
            if not self.container.config.paths:
                return

            profile = self.profile_manager.get_or_create_profile(
                self.container.config.paths
            )

            # Extract successful result text
            result_text = ""
            for item in result:
                if hasattr(item, "text"):
                    result_text += item.text + "\n"

            # Update profile based on tool type
            if (
                tool_name == "detect_controllers"
                and "Detected controllers:" in result_text
            ):
                # Could parse controller detection results and update profile
                pass
            elif tool_name == "setup_controller" and "✓" in result_text:
                # Could record successful controller setup
                controller_type = arguments.get("controller_type", "unknown")
                profile.add_user_note(
                    f"Successfully configured {controller_type} controller"
                )
                self.profile_manager.save_profile(profile)
            elif tool_name == "install_emulator" and "✓" in result_text:
                # Could record successful emulator installation
                emulator = arguments.get("emulator", "unknown")
                system = arguments.get("system", "unknown")
                profile.add_user_note(f"Successfully installed {emulator} for {system}")
                self.profile_manager.save_profile(profile)

        except Exception as e:
            # Don't fail tool execution if profile update fails
            logging.debug(f"Failed to update profile from tool execution: {e}")

    async def run(self) -> None:
        """Run the MCP server."""
        # Check if .env file exists, if not create from example
        env_path = Path(".env")
        env_example_path = Path(".env.example")

        if not env_path.exists() and env_example_path.exists():
            import shutil

            shutil.copy(env_example_path, env_path)
            print(
                "Created .env file from .env.example - please configure it with your RetroPie details"
            )

        # Run the server using stdio transport
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name=self.server_config.name,
                    server_version=self.server_config.version,
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                    instructions=f"""{self.server_config.description}

This MCP server helps you configure and manage RetroPie installations.

Tool Categories:
🔧 System Tools: Connection testing, package installation, system updates
🎮 Controller Tools: Detection, setup, testing, configuration
🚀 RetroPie Tools: Emulator installation, ROM management, overclocking
🎨 EmulationStation Tools: Theme management, settings, service control
🔬 Hardware Tools: Temperature monitoring, fan control, power analysis, GPIO debugging

Popular Tools:
- test_connection: Test SSH connection to your RetroPie
- check_temperatures: Monitor CPU/GPU temperatures and thermal throttling
- monitor_fan_control: Check fan operation and cooling system
- detect_controllers: Detect connected game controllers
- install_packages: Install packages via apt-get
- setup_controller: Configure Xbox, PS4, or 8BitDo controllers
- install_emulator: Install emulators via RetroPie-Setup
- configure_overclock: Adjust Pi performance settings
- check_power_supply: Monitor power health and under-voltage warnings
- inspect_hardware_errors: Analyze system logs for hardware issues

Before using, ensure your .env file is configured with:
- RETROPIE_HOST: IP address of your Raspberry Pi
- RETROPIE_USERNAME: SSH username (usually 'pi')
- RETROPIE_PASSWORD or RETROPIE_SSH_KEY_PATH: Authentication method

⚠️ Some tools require sudo access and may modify your system.""",
                ),
                raise_exceptions=True,
            )


async def main() -> None:
    """Main entry point for the MCP server."""
    try:
        # Load configuration from environment
        config = RetroPieConfig.from_env()
        server_config = ServerConfig()

        # Create and run server
        server = RetroMCPServer(config, server_config)
        await server.run()

    except ValueError as e:
        print(f"Configuration error: {e}")
        print("Please ensure your .env file is properly configured.")
        return
    except Exception as e:
        print(f"Server error: {e}")
        return


if __name__ == "__main__":
    asyncio.run(main())
