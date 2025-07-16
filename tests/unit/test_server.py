"""Unit tests for the main RetroMCP server."""

from unittest.mock import AsyncMock
from unittest.mock import Mock
from unittest.mock import patch

import pytest
from mcp.types import Resource
from mcp.types import TextContent
from mcp.types import Tool

from retromcp.config import RetroPieConfig
from retromcp.config import ServerConfig
from retromcp.server import RetroMCPServer


class TestRetroMCPServer:
    """Test cases for RetroMCPServer class."""

    @pytest.fixture
    def server_config(self) -> ServerConfig:
        """Provide test server configuration."""
        return ServerConfig(
            name="retromcp-test",
            version="1.0.0",
            description="Test MCP server for RetroPie",
        )

    @pytest.fixture
    def mock_container(self) -> Mock:
        """Provide mocked container."""
        container = Mock()
        container.connect.return_value = True
        container.config = Mock()
        container.config.paths = Mock()
        container.ssh_handler = Mock()
        return container

    @pytest.fixture
    def mock_profile_manager(self) -> Mock:
        """Provide mocked profile manager."""
        profile_manager = Mock()
        profile = Mock()
        profile.to_context_summary.return_value = "Test system profile summary"
        profile.add_user_note = Mock()
        profile_manager.get_or_create_profile.return_value = profile
        profile_manager.save_profile = Mock()
        return profile_manager

    @pytest.fixture
    def server(
        self, test_config: RetroPieConfig, server_config: ServerConfig
    ) -> RetroMCPServer:
        """Provide RetroMCP server instance with mocked dependencies."""
        with patch("retromcp.server.Container") as mock_container_class, patch(
            "retromcp.server.SystemProfileManager"
        ) as mock_profile_class:
            # Setup container mock
            mock_container = Mock()
            mock_container.connect.return_value = True
            mock_container.config = Mock()
            mock_container.config.paths = Mock()
            mock_container.ssh_handler = Mock()
            mock_container_class.return_value = mock_container

            # Setup profile manager mock
            mock_profile_manager = Mock()
            mock_profile = Mock()
            mock_profile.to_context_summary.return_value = "Test system profile"
            mock_profile.add_user_note = Mock()
            mock_profile_manager.get_or_create_profile.return_value = mock_profile
            mock_profile_manager.save_profile = Mock()
            mock_profile_class.return_value = mock_profile_manager

            server = RetroMCPServer(test_config, server_config)
            server.container = mock_container
            server.profile_manager = mock_profile_manager
            return server

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_initialization(
        self, test_config: RetroPieConfig, server_config: ServerConfig
    ) -> None:
        """Test server initialization."""
        with patch("retromcp.server.Container") as mock_container_class, patch(
            "retromcp.server.SystemProfileManager"
        ) as mock_profile_class:
            server = RetroMCPServer(test_config, server_config)

            assert server.config == test_config
            assert server.server_config == server_config
            assert server.server is not None
            mock_container_class.assert_called_once_with(test_config)
            mock_profile_class.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_list_resources(self, server: RetroMCPServer) -> None:
        """Test listing MCP resources."""
        resources = await server.list_resources()

        assert len(resources) == 1
        assert isinstance(resources[0], Resource)
        assert str(resources[0].uri) == "retropie://system-profile"
        assert resources[0].name == "RetroPie System Profile"
        assert resources[0].mimeType == "text/plain"

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_read_resource_success(self, server: RetroMCPServer) -> None:
        """Test reading system profile resource successfully."""
        # Mock successful connection and profile retrieval
        server.container.connect.return_value = True
        server.container.config.paths = Mock()

        result = await server.read_resource("retropie://system-profile")

        assert result == "Test system profile"
        server.container.connect.assert_called_once()
        server.profile_manager.get_or_create_profile.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_read_resource_connection_failure(
        self, server: RetroMCPServer
    ) -> None:
        """Test reading resource when connection fails."""
        server.container.connect.return_value = False

        result = await server.read_resource("retropie://system-profile")

        assert result == "❌ Unable to connect to RetroPie system"

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_read_resource_no_discovery(self, server: RetroMCPServer) -> None:
        """Test reading resource when discovery not completed."""
        server.container.connect.return_value = True
        server.container.config.paths = None

        result = await server.read_resource("retropie://system-profile")

        assert result == "⚠️ System discovery not completed yet"

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_read_resource_exception(self, server: RetroMCPServer) -> None:
        """Test reading resource when exception occurs."""
        server.container.connect.side_effect = Exception("Test error")

        result = await server.read_resource("retropie://system-profile")

        assert "❌ Error loading system profile: Test error" in result

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_read_resource_unknown_uri(self, server: RetroMCPServer) -> None:
        """Test reading unknown resource URI."""
        result = await server.read_resource("unknown://resource")

        assert result == "❌ Unknown resource: unknown://resource"

    @pytest.mark.asyncio
    async def test_list_tools_success(self, server: RetroMCPServer) -> None:
        """Test listing tools when connection succeeds."""
        # Mock tool instances
        mock_system_tools = Mock()
        mock_system_tools.get_tools.return_value = [
            Tool(
                name="test_connection",
                description="Test connection",
                inputSchema={"type": "object", "properties": {}, "required": []},
            )
        ]

        mock_controller_tools = Mock()
        mock_controller_tools.get_tools.return_value = [
            Tool(
                name="detect_controllers",
                description="Detect controllers",
                inputSchema={"type": "object", "properties": {}, "required": []},
            )
        ]

        with patch(
            "retromcp.server.SystemManagementTools", return_value=mock_system_tools
        ) as mock_system_class, patch(
            "retromcp.server.GamingSystemTools", return_value=mock_controller_tools
        ) as mock_gaming_class, patch(
            "retromcp.server.HardwareMonitoringTools"
        ) as mock_hw_class:
            mock_hw_class.return_value.get_tools.return_value = []

            server.container.connect.return_value = True

            tools = await server.list_tools()

            assert len(tools) == 2
            assert tools[0].name == "test_connection"
            assert tools[1].name == "detect_controllers"
            server.container.connect.assert_called_once()

            # Verify tools are instantiated with container
            mock_system_class.assert_called_once_with(server.container)
            mock_gaming_class.assert_called_once_with(server.container)
            mock_hw_class.assert_called_once_with(server.container)

    @pytest.mark.asyncio
    async def test_list_tools_connection_failure(self, server: RetroMCPServer) -> None:
        """Test listing tools when connection fails."""
        server.container.connect.return_value = False

        tools = await server.list_tools()

        assert len(tools) == 1
        assert tools[0].name == "connection_error"
        assert "Error connecting to RetroPie" in tools[0].description

    @pytest.mark.asyncio
    async def test_list_tools_exception(self, server: RetroMCPServer) -> None:
        """Test listing tools when exception occurs."""
        server.container.connect.side_effect = Exception("Connection failed")

        tools = await server.list_tools()

        assert len(tools) == 1
        assert tools[0].name == "connection_error"
        assert "Connection failed" in tools[0].description

    @pytest.mark.asyncio
    async def test_call_tool_connection_error(self, server: RetroMCPServer) -> None:
        """Test calling connection_error tool."""
        result = await server.call_tool("connection_error", {})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "❌ Connection failed" in result[0].text

    @pytest.mark.asyncio
    async def test_call_tool_success(self, server: RetroMCPServer) -> None:
        """Test successful tool call."""
        # Mock tool instance
        mock_tool_result = [
            TextContent(type="text", text="✓ Tool executed successfully")
        ]
        mock_system_tools = Mock()
        mock_system_tools.handle_tool_call = AsyncMock(return_value=mock_tool_result)

        with patch(
            "retromcp.server.SystemManagementTools", return_value=mock_system_tools
        ) as mock_system_class, patch(
            "retromcp.server.GamingSystemTools"
        ) as mock_gaming_class, patch(
            "retromcp.server.HardwareMonitoringTools"
        ) as mock_hw_class:
            # Mock other tool classes to avoid instantiation issues
            mock_gaming_class.return_value = Mock()
            mock_hw_class.return_value = Mock()

            server.container.connect.return_value = True
            server.container.config.paths = Mock()

            result = await server.call_tool("test_connection", {})

            assert len(result) == 1
            assert isinstance(result[0], TextContent)
            assert "✓ Tool executed successfully" in result[0].text
            mock_system_tools.handle_tool_call.assert_called_once_with(
                "test_connection", {}
            )

            # Verify tools are instantiated with container
            mock_system_class.assert_called_once_with(server.container)
            mock_gaming_class.assert_called_once_with(server.container)
            mock_hw_class.assert_called_once_with(server.container)

    @pytest.mark.asyncio
    async def test_call_tool_connection_failure(self, server: RetroMCPServer) -> None:
        """Test tool call when connection fails."""
        server.container.connect.return_value = False

        result = await server.call_tool("test_connection", {})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "❌ Error executing test_connection" in result[0].text

    @pytest.mark.asyncio
    async def test_call_tool_unknown_tool(self, server: RetroMCPServer) -> None:
        """Test calling unknown tool."""
        server.container.connect.return_value = True

        result = await server.call_tool("unknown_tool", {})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "❌ Unknown tool: unknown_tool" in result[0].text

    @pytest.mark.asyncio
    async def test_call_tool_exception(self, server: RetroMCPServer) -> None:
        """Test tool call when exception occurs."""
        server.container.connect.side_effect = Exception("Test error")

        result = await server.call_tool("test_connection", {})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "❌ Error executing test_connection: Test error" in result[0].text

    @pytest.mark.asyncio
    async def test_update_profile_from_tool_execution_controller_setup(
        self, server: RetroMCPServer
    ) -> None:
        """Test profile update from successful controller setup."""
        server.container.config.paths = Mock()
        mock_profile = Mock()
        server.profile_manager.get_or_create_profile.return_value = mock_profile

        result = [TextContent(type="text", text="✓ Xbox controller configured")]
        arguments = {"controller_type": "xbox"}

        server._update_profile_from_tool_execution(
            "setup_controller", arguments, result
        )

        mock_profile.add_user_note.assert_called_once_with(
            "Successfully configured xbox controller"
        )
        server.profile_manager.save_profile.assert_called_once_with(mock_profile)

    @pytest.mark.asyncio
    async def test_update_profile_from_tool_execution_emulator_install(
        self, server: RetroMCPServer
    ) -> None:
        """Test profile update from successful emulator installation."""
        server.container.config.paths = Mock()
        mock_profile = Mock()
        server.profile_manager.get_or_create_profile.return_value = mock_profile

        result = [TextContent(type="text", text="✓ Emulator installed successfully")]
        arguments = {"emulator": "lr-mupen64plus", "system": "n64"}

        server._update_profile_from_tool_execution(
            "install_emulator", arguments, result
        )

        mock_profile.add_user_note.assert_called_once_with(
            "Successfully installed lr-mupen64plus for n64"
        )
        server.profile_manager.save_profile.assert_called_once_with(mock_profile)

    @pytest.mark.asyncio
    async def test_update_profile_no_paths(self, server: RetroMCPServer) -> None:
        """Test profile update when no paths available."""
        server.container.config.paths = None

        result = [TextContent(type="text", text="✓ Success")]
        server._update_profile_from_tool_execution("test_tool", {}, result)

        # Should not call profile manager when no paths
        server.profile_manager.get_or_create_profile.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_profile_exception_handling(
        self, server: RetroMCPServer
    ) -> None:
        """Test profile update handles exceptions gracefully."""
        server.container.config.paths = Mock()
        server.profile_manager.get_or_create_profile.side_effect = Exception(
            "Profile error"
        )

        result = [TextContent(type="text", text="✓ Success")]
        # Should not raise exception
        server._update_profile_from_tool_execution("test_tool", {}, result)

    @pytest.mark.asyncio
    async def test_run_creates_env_file(self, server: RetroMCPServer) -> None:
        """Test that run() creates .env file from example if it doesn't exist."""
        with patch("retromcp.server.Path") as mock_path, patch(
            "shutil.copy"
        ) as mock_shutil_copy, patch(
            "retromcp.server.stdio_server"
        ) as mock_stdio, patch.object(
            server.server, "run", new_callable=AsyncMock
        ) as mock_run:
            # Mock file existence checks
            env_path = Mock()
            env_path.exists.return_value = False
            env_example_path = Mock()
            env_example_path.exists.return_value = True

            mock_path.side_effect = lambda x: (
                env_path if x == ".env" else env_example_path
            )

            # Mock stdio server context manager
            mock_stdio.return_value.__aenter__ = AsyncMock(
                return_value=("read_stream", "write_stream")
            )
            mock_stdio.return_value.__aexit__ = AsyncMock(return_value=None)

            await server.run()

            mock_shutil_copy.assert_called_once_with(env_example_path, env_path)
            mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_tool_routing_completeness(self, server: RetroMCPServer) -> None:
        """Test that all expected tools are properly routed."""
        # This test ensures the tool routing dictionary is comprehensive
        expected_tools = {
            # System tools
            "test_connection",
            "system_info",
            "install_packages",
            "check_bios",
            "update_system",
            # Controller tools
            "detect_controllers",
            "setup_controller",
            "test_controller",
            "configure_controller_mapping",
            # RetroPie tools
            "run_retropie_setup",
            "install_emulator",
            "manage_roms",
            "configure_overclock",
            "configure_audio",
            # EmulationStation tools
            "restart_emulationstation",
            "configure_themes",
            "manage_gamelists",
            "configure_es_settings",
            # Hardware tools
            "check_temperatures",
            "monitor_fan_control",
            "check_power_supply",
            "inspect_hardware_errors",
            "check_gpio_status",
        }

        # Access the tool routing dictionary from the server method
        # We'll need to check this during a tool call
        server.container.connect.return_value = True

        with patch("retromcp.server.SystemManagementTools") as mock_system, patch(
            "retromcp.server.GamingSystemTools"
        ) as mock_gaming, patch("retromcp.server.HardwareMonitoringTools") as mock_hw:
            # Setup mocks
            for mock in [mock_system, mock_gaming, mock_hw]:
                mock.return_value.handle_tool_call = AsyncMock(
                    return_value=[TextContent(type="text", text="success")]
                )

            # Test that each expected tool can be called
            for tool_name in expected_tools:
                result = await server.call_tool(tool_name, {})
                assert len(result) == 1
                assert isinstance(result[0], TextContent)
                assert "success" in result[0].text

            # Verify tools are instantiated with container (each call creates instances)
            # Since we call tools multiple times, each class should be called with container
            mock_system.assert_called_with(server.container)
            mock_gaming.assert_called_with(server.container)
            mock_hw.assert_called_with(server.container)


class TestMainFunction:
    """Test cases for the main entry point."""

    @pytest.mark.asyncio
    async def test_main_success(self) -> None:
        """Test successful main function execution."""
        with patch("retromcp.server.RetroPieConfig") as mock_config_class, patch(
            "retromcp.server.ServerConfig"
        ) as mock_server_config_class, patch(
            "retromcp.server.RetroMCPServer"
        ) as mock_server_class:
            mock_config = Mock()
            mock_config_class.from_env.return_value = mock_config
            mock_server_config = Mock()
            mock_server_config_class.return_value = mock_server_config

            mock_server = Mock()
            mock_server.run = AsyncMock()
            mock_server_class.return_value = mock_server

            from retromcp.server import main

            await main()

            mock_config_class.from_env.assert_called_once()
            mock_server_config_class.assert_called_once()
            mock_server_class.assert_called_once_with(mock_config, mock_server_config)
            mock_server.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_main_configuration_error(self) -> None:
        """Test main function with configuration error."""
        with patch("retromcp.server.RetroPieConfig") as mock_config_class, patch(
            "builtins.print"
        ) as mock_print:
            mock_config_class.from_env.side_effect = ValueError("Config error")

            from retromcp.server import main

            await main()

            mock_print.assert_any_call("Configuration error: Config error")
            mock_print.assert_any_call(
                "Please ensure your .env file is properly configured."
            )

    @pytest.mark.asyncio
    async def test_main_server_error(self) -> None:
        """Test main function with server error."""
        with patch("retromcp.server.RetroPieConfig") as mock_config_class, patch(
            "retromcp.server.ServerConfig"
        ) as mock_server_config_class, patch(
            "retromcp.server.RetroMCPServer"
        ) as mock_server_class, patch("builtins.print") as mock_print:
            mock_config = Mock()
            mock_config_class.from_env.return_value = mock_config
            mock_server_config = Mock()
            mock_server_config_class.return_value = mock_server_config

            mock_server = Mock()
            mock_server.run = AsyncMock(side_effect=Exception("Server error"))
            mock_server_class.return_value = mock_server

            from retromcp.server import main

            await main()

            mock_print.assert_called_with("Server error: Server error")
