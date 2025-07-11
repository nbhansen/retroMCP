#!/usr/bin/env python3
"""RetroMCP Server - MCP server for RetroPie configuration and management."""

import asyncio
import os
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
from mcp.types import TextContent
from mcp.types import Tool

try:
    from .config import RetroPieConfig
    from .config import ServerConfig
    from .ssh_handler import RetroPieSSH
    from .tools import ControllerTools
    from .tools import EmulationStationTools
    from .tools import RetroPieTools
    from .tools import SystemTools
except ImportError:
    from config import RetroPieConfig
    from config import ServerConfig
    from ssh_handler import RetroPieSSH
    from tools import ControllerTools
    from tools import EmulationStationTools
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
        self._ssh_connection: RetroPieSSH | None = None
        self._tool_instances: Dict[str, Any] = {}

        # Register handlers
        self.server.list_tools()(self.list_tools)
        self.server.call_tool()(self.call_tool)

    def _get_ssh_connection(self) -> RetroPieSSH:
        """Get or create SSH connection to RetroPie."""
        if self._ssh_connection and self._ssh_connection.test_connection():
            return self._ssh_connection

        # Expand ~ in key path if provided
        key_path = self.config.key_path
        if key_path:
            key_path = os.path.expanduser(key_path)

        self._ssh_connection = RetroPieSSH(
            host=self.config.host,
            username=self.config.username,
            password=self.config.password,
            key_path=key_path,
            port=self.config.port,
        )

        if not self._ssh_connection.connect():
            raise ConnectionError(
                f"Failed to connect to RetroPie at {self.config.host}"
            )

        return self._ssh_connection

    def _get_tool_instances(self) -> Dict[str, Any]:
        """Get or create tool instances."""
        if not self._tool_instances:
            ssh = self._get_ssh_connection()
            self._tool_instances = {
                "system": SystemTools(ssh),
                "controller": ControllerTools(ssh),
                "retropie": RetroPieTools(ssh),
                "emulationstation": EmulationStationTools(ssh),
            }

        return self._tool_instances

    async def list_tools(self) -> List[Tool]:
        """List available tools from all modules."""
        tools = []

        try:
            tool_instances = self._get_tool_instances()

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
            tool_instances = self._get_tool_instances()

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
            }

            # Route tool call to appropriate module
            if name in tool_routing:
                module_name = tool_routing[name]
                tool_instance = tool_instances[module_name]
                return await tool_instance.handle_tool_call(name, arguments)
            else:
                return [TextContent(type="text", text=f"❌ Unknown tool: {name}")]

        except Exception as e:
            return [TextContent(type="text", text=f"❌ Error executing {name}: {e!s}")]

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

Popular Tools:
- test_connection: Test SSH connection to your RetroPie
- detect_controllers: Detect connected game controllers
- install_packages: Install packages via apt-get
- setup_controller: Configure Xbox, PS4, or 8BitDo controllers
- install_emulator: Install emulators via RetroPie-Setup
- configure_overclock: Adjust Pi performance settings

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
