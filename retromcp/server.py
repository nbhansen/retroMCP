#!/usr/bin/env python3
"""RetroMCP Server - MCP server for RetroPie configuration and management."""

import asyncio
import logging
from pathlib import Path
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

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
    from .tools import CommandQueueTools
    from .tools import DockerTools
    from .tools import GamingSystemTools
    from .tools import HardwareMonitoringTools
    from .tools import StateTools
    from .tools import SystemManagementTools
except ImportError:
    from .config import RetroPieConfig
    from .config import ServerConfig
    from .container import Container
    from .profile import SystemProfileManager
    from .tools import CommandQueueTools
    from .tools import DockerTools
    from .tools import GamingSystemTools
    from .tools import HardwareMonitoringTools
    from .tools import StateTools
    from .tools import SystemManagementTools

# Load environment variables
load_dotenv()


def configure_logging() -> None:
    """Configure logging based on environment variables."""
    import os

    log_level = os.getenv("RETROMCP_LOG_LEVEL", "INFO").upper()

    # Map string levels to logging constants
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }

    level = level_map.get(log_level, logging.INFO)

    # Configure basic logging
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # For debug mode, also log to file
    if level == logging.DEBUG:
        from pathlib import Path

        log_dir = Path.home() / ".retromcp"
        log_dir.mkdir(exist_ok=True)

        file_handler = logging.FileHandler(log_dir / "debug.log")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

        # Add file handler to root logger
        logging.getLogger().addHandler(file_handler)
        logging.info(f"Debug logging enabled - writing to {log_dir / 'debug.log'}")


# Logging will be configured in main() to avoid blocking during module import


class RetroMCPServer:
    """Main RetroMCP server class with proper dependency injection."""

    def __init__(self, config: RetroPieConfig, server_config: ServerConfig) -> None:
        """Initialize the server with configuration."""
        self.config = config
        self.server_config = server_config
        self.server = Server(server_config.name)
        self.container = Container(config)
        self._profile_manager: Optional[SystemProfileManager] = None

        # Register handlers
        self.server.list_tools()(self.list_tools)
        self.server.call_tool()(self.call_tool)
        self.server.list_resources()(self.list_resources)
        self.server.read_resource()(self.read_resource)

    @property
    def profile_manager(self) -> SystemProfileManager:
        """Lazy initialization of profile manager."""
        if self._profile_manager is None:
            self._profile_manager = SystemProfileManager()
        return self._profile_manager

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
            # Get tool instances from container (don't require connection for listing)
            tool_instances = {
                "system_management": SystemManagementTools(self.container),
                "hardware_monitoring": HardwareMonitoringTools(self.container),
                "gaming_system": GamingSystemTools(self.container),
                "state": StateTools(self.container),
                "docker": DockerTools(self.container),
                "command_queue": CommandQueueTools(self.container),
            }

            # Collect tools from all modules
            for _, tool_instance in tool_instances.items():
                module_tools = tool_instance.get_tools()
                tools.extend(module_tools)

            return tools
        except Exception as e:
            # Return connection_error tool on any exception
            return [
                Tool(
                    name="connection_error",
                    description=f"Connection failed: {e!s}",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                    },
                )
            ]

    async def call_tool(
        self, name: str, arguments: Dict[str, Any]
    ) -> List[TextContent | ImageContent | EmbeddedResource]:
        """Handle tool calls by routing to appropriate module."""
        logging.debug(f"Tool call received: {name} with arguments: {arguments}")

        # Get tool instances from container (created without connection requirement)
        tool_instances = {
            "system_management": SystemManagementTools(self.container),
            "hardware_monitoring": HardwareMonitoringTools(self.container),
            "gaming_system": GamingSystemTools(self.container),
            "state": StateTools(self.container),
            "docker": DockerTools(self.container),
            "command_queue": CommandQueueTools(self.container),
        }

        try:
            # Ensure connection is established for tool execution
            logging.debug("Attempting to establish connection to RetroPie")
            if not self.container.connect():
                # For test_connection, return the expected error format
                if name == "test_connection":
                    return [
                        TextContent(
                            type="text",
                            text=f"❌ Error executing {name}: Connection failed",
                        )
                    ]
                return [
                    TextContent(
                        type="text",
                        text="❌ Connection failed. Please check your .env configuration:\n- RETROPIE_HOST\n- RETROPIE_USERNAME\n- RETROPIE_PASSWORD or RETROPIE_SSH_KEY_PATH",
                    )
                ]

            # Special handling for connection_error tool
            if name == "connection_error":
                return [
                    TextContent(
                        type="text",
                        text="❌ Connection failed. Please check your .env configuration:\n- RETROPIE_HOST\n- RETROPIE_USERNAME\n- RETROPIE_PASSWORD or RETROPIE_SSH_KEY_PATH",
                    )
                ]

            # Define tool routing - maps tool names to modules
            # Individual tool names from the new architecture
            tool_routing = {
                # System Management individual tools
                "manage_service": "system_management",
                "manage_package": "system_management",
                "manage_file": "system_management",
                "execute_command": "system_management",
                "manage_connection": "system_management",
                "get_system_info": "system_management",
                "update_system": "system_management",
                # Hardware monitoring tools
                "check_temperature": "hardware_monitoring",
                "check_cpu": "hardware_monitoring",
                "check_memory": "hardware_monitoring",
                "check_disk": "hardware_monitoring",
                "check_network": "hardware_monitoring",
                "check_processes": "hardware_monitoring",
                # Gaming system tools
                "manage_emulationstation": "gaming_system",
                "manage_roms": "gaming_system",
                "manage_controller": "gaming_system",
                # State tools
                "save_state": "state",
                "restore_state": "state",
                "list_states": "state",
                "compare_states": "state",
                # Docker tools
                "manage_docker": "docker",
                # Command queue tool
                "manage_command_queue": "command_queue",
                # Unified tool names
                "manage_hardware": "hardware_monitoring",
                "manage_gaming": "gaming_system",
                "manage_state": "state",
                # Legacy names for backward compatibility
                "test_connection": "system_management",
                "system_info": "system_management",
                "install_packages": "system_management",
                "check_bios": "gaming_system",
                "detect_controllers": "gaming_system",
                "setup_controller": "gaming_system",
                "test_controller": "gaming_system",
                "configure_controller_mapping": "gaming_system",
                "run_retropie_setup": "gaming_system",
                "install_emulator": "gaming_system",
                "configure_overclock": "hardware_monitoring",
                "configure_audio": "gaming_system",
                "restart_emulationstation": "gaming_system",
                "configure_themes": "gaming_system",
                "manage_gamelists": "gaming_system",
                "configure_es_settings": "gaming_system",
                "check_temperatures": "hardware_monitoring",
                "monitor_fan_control": "hardware_monitoring",
                "check_power_supply": "hardware_monitoring",
                "inspect_hardware_errors": "hardware_monitoring",
                "check_gpio_status": "hardware_monitoring",
            }

            # Route tool call to appropriate module
            if name in tool_routing:
                module_name = tool_routing[name]
                tool_instance = tool_instances[module_name]
                logging.debug(f"Routing tool {name} to module {module_name}")

                # Map legacy tool names to new names
                actual_tool_name = name
                if name == "test_connection":
                    actual_tool_name = "manage_connection"
                    # Ensure the arguments have the correct action
                    if "action" not in arguments:
                        arguments = {"action": "test"}

                result = await tool_instance.handle_tool_call(
                    actual_tool_name, arguments
                )
                logging.debug(f"Tool {name} completed successfully")

                # Update profile with any new information learned
                if self.container.config.paths:
                    self._update_profile_from_tool_execution(name, arguments, result)

                return result
            else:
                logging.warning(f"Unknown tool requested: {name}")
                return [TextContent(type="text", text=f"❌ Unknown tool: {name}")]

        except Exception as e:
            logging.error(f"Tool execution failed for {name}: {e}", exc_info=True)
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
        import sys

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
        print("Attempting to initialize stdio_server...", file=sys.stderr)
        try:
            async with stdio_server() as (read_stream, write_stream):
                print("stdio_server initialized successfully", file=sys.stderr)
                print("Starting MCP server.run()...", file=sys.stderr)
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
        except Exception as e:
            print(
                f"Error during stdio_server initialization or MCP run: {e}",
                file=sys.stderr,
            )
            raise


async def main() -> None:
    """Main entry point for the MCP server."""
    try:
        # Configure logging first to avoid blocking during module import
        configure_logging()

        # Add startup diagnostics
        import sys

        print("RetroMCP Server starting...", file=sys.stderr)

        # Load configuration from environment
        config = RetroPieConfig.from_env()
        server_config = ServerConfig()

        print("Configuration loaded successfully", file=sys.stderr)

        # Create and run server
        print("Creating RetroMCPServer instance...", file=sys.stderr)
        server = RetroMCPServer(config, server_config)
        print("Server initialized, starting MCP protocol...", file=sys.stderr)
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
