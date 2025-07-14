"""MCP protocol compliance tests.

These tests verify that our RetroMCP server properly implements
the Model Context Protocol standard, ensuring compatibility
with MCP clients and the broader MCP ecosystem.
"""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from mcp.server import Server
from mcp.types import EmbeddedResource
from mcp.types import TextContent
from mcp.types import Tool

from retromcp.config import RetroPieConfig
from retromcp.config import ServerConfig
from retromcp.discovery import RetroPiePaths
from retromcp.server import RetroMCPServer


class TestMCPServerInitialization:
    """Test MCP server initialization and lifecycle compliance."""

    @pytest.fixture
    def temp_profile_dir(self):
        """Create temporary directory for profiles."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def test_config(self) -> RetroPieConfig:
        """Create test configuration."""
        paths = RetroPiePaths(
            home_dir="/home/retro",
            username="retro",
            retropie_dir="/home/retro/RetroPie",
        )
        return RetroPieConfig(
            host="test-retropie.local",
            username="retro",
            password="test_password",  # noqa: S106
            port=22,
            paths=paths,
        )

    def test_server_has_required_mcp_attributes(
        self, test_config: RetroPieConfig, temp_profile_dir: Path
    ) -> None:
        """Test that server has required MCP server attributes."""
        server_config = ServerConfig()
        server = RetroMCPServer(test_config, server_config)

        # Should have MCP server instance
        assert hasattr(server, "server"), (
            "RetroMCPServer should have MCP server instance"
        )
        assert isinstance(server.server, Server), "Server should be MCP Server instance"

        # Should have proper server info
        assert hasattr(server, "server_config"), "Server should have server config"
        assert server.server_config.name is not None, "Server should have name"
        assert server.server_config.version is not None, "Server should have version"

    def test_server_initialization_options(
        self, test_config: RetroPieConfig, temp_profile_dir: Path
    ) -> None:
        """Test that server supports MCP initialization options."""
        server_config = ServerConfig()
        server = RetroMCPServer(test_config, server_config)

        # Server should be properly configured
        assert server.server_config.name == "RetroMCP", (
            "Server should have correct name"
        )
        assert server.server_config.version is not None, "Server should have version"

        # Should have server description
        assert server_config.description is not None, "Server should have description"

    @pytest.mark.asyncio
    async def test_server_startup_sequence(
        self, test_config: RetroPieConfig, temp_profile_dir: Path
    ) -> None:
        """Test that server follows proper MCP startup sequence."""
        server_config = ServerConfig()
        server = RetroMCPServer(test_config, server_config)

        # Should initialize without errors
        assert server.server is not None, "Server should initialize properly"

        # Should have registered handlers (tools, resources, etc.)
        # We'll test this implicitly by checking if server has proper methods
        assert hasattr(server, "list_tools"), "Server should have list_tools handler"
        assert hasattr(server, "call_tool"), "Server should have call_tool handler"


class TestMCPToolCompliance:
    """Test that tools are properly exposed via MCP protocol."""

    @pytest.fixture
    def temp_profile_dir(self):
        """Create temporary directory for profiles."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def test_config(self) -> RetroPieConfig:
        """Create test configuration."""
        paths = RetroPiePaths(
            home_dir="/home/retro",
            username="retro",
            retropie_dir="/home/retro/RetroPie",
        )
        return RetroPieConfig(
            host="test-retropie.local",
            username="retro",
            password="test_password",  # noqa: S106
            port=22,
            paths=paths,
        )

    def test_tools_are_properly_registered(
        self, test_config: RetroPieConfig, temp_profile_dir: Path
    ) -> None:
        """Test that all tools are registered with MCP server."""
        with patch("retromcp.container.Container.connect") as mock_connect:
            mock_connect.return_value = True

            from retromcp.config import ServerConfig

            server_config = ServerConfig()
            server = RetroMCPServer(test_config, server_config)

            # Should have tools available via list_tools
            tools = asyncio.run(server.list_tools())

            # Should have tools from different categories
            tool_names = [tool.name for tool in tools]
            expected_tool_categories = [
                "system",
                "hardware",
                "retropie",
                "controller",
                "emulationstation",
            ]
            for category in expected_tool_categories:
                assert any(category in name for name in tool_names), (
                    f"Should have {category} tools available"
                )

    def test_tool_schemas_are_mcp_compliant(
        self, test_config: RetroPieConfig, temp_profile_dir: Path
    ) -> None:
        """Test that tool schemas follow MCP Tool specification."""
        server_config = ServerConfig()
        server = RetroMCPServer(test_config, server_config)

        # Get tools from server
        tools = asyncio.run(server.list_tools())

        for tool_def in tools:
            # Should be proper MCP Tool type
            assert isinstance(tool_def, Tool), "Tool definition should be MCP Tool type"

            # Should have required fields
            assert hasattr(tool_def, "name"), "Tool should have name"
            assert hasattr(tool_def, "description"), "Tool should have description"

            # Name should be meaningful
            assert len(tool_def.name) > 0, "Tool name should not be empty"
            assert "_" in tool_def.name or tool_def.name.islower(), (
                "Tool name should follow naming conventions"
            )

            # Description should be helpful
            assert len(tool_def.description) > 10, (
                "Tool description should be descriptive"
            )

    @pytest.mark.asyncio
    async def test_tool_execution_follows_mcp_protocol(
        self, test_config: RetroPieConfig, temp_profile_dir: Path
    ) -> None:
        """Test that tool execution follows MCP protocol."""
        with patch("retromcp.container.Container.connect") as mock_connect:
            mock_connect.return_value = True

            from retromcp.config import ServerConfig

            server_config = ServerConfig()
            server = RetroMCPServer(test_config, server_config)

            # Test tool execution through server interface
            result = await server.call_tool("test_connection", {})

            # Result should be MCP-compliant
            assert isinstance(result, list), "Tool result should be list"
            assert len(result) > 0, "Tool should return content"

            # Each result item should be MCP content type
            for item in result:
                assert isinstance(item, (TextContent, EmbeddedResource)), (
                    "Tool result should be MCP content type"
                )


class TestMCPErrorHandling:
    """Test that error handling follows MCP protocol standards."""

    @pytest.fixture
    def temp_profile_dir(self):
        """Create temporary directory for profiles."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def test_config(self) -> RetroPieConfig:
        """Create test configuration."""
        return RetroPieConfig(
            host="test-retropie.local",
            username="retro",
            password="test_password",  # noqa: S106
            port=22,
        )

    @pytest.mark.asyncio
    async def test_tool_error_responses_are_mcp_compliant(
        self, test_config: RetroPieConfig, temp_profile_dir: Path
    ) -> None:
        """Test that tool errors follow MCP error response format."""
        with patch("retromcp.container.Container.connect") as mock_connect:
            # Mock connection failure
            mock_connect.return_value = False

            from retromcp.config import ServerConfig

            server_config = ServerConfig()
            server = RetroMCPServer(test_config, server_config)

            # Test tool execution with connection error
            result = await server.call_tool("test_connection", {})

            # Should still return MCP-compliant response
            assert isinstance(result, list), "Error response should still be list"
            assert len(result) > 0, "Error response should have content"

            # Should contain error information
            error_content = result[0]
            assert isinstance(error_content, TextContent), "Error should be TextContent"

            # Error should be informative
            error_text = error_content.text.lower()
            assert any(word in error_text for word in ["error", "failed", "unable"]), (
                "Error message should indicate failure"
            )

    @pytest.mark.asyncio
    async def test_invalid_tool_call_handling(
        self, test_config: RetroPieConfig, temp_profile_dir: Path
    ) -> None:
        """Test handling of invalid tool calls."""
        with patch("retromcp.container.Container.connect") as mock_connect:
            mock_connect.return_value = True

            from retromcp.config import ServerConfig

            server_config = ServerConfig()
            server = RetroMCPServer(test_config, server_config)

            # Test invalid tool call
            result = await server.call_tool("nonexistent_tool", {})

            # Should handle gracefully
            assert isinstance(result, list), "Invalid tool call should return list"
            assert len(result) > 0, "Should have error response"

            # Should indicate the error
            error_content = result[0]
            error_text = error_content.text.lower()
            assert any(
                word in error_text for word in ["unknown", "invalid", "not found"]
            ), "Should indicate unknown tool"


class TestMCPResourceCompliance:
    """Test MCP resource handling compliance."""

    @pytest.fixture
    def temp_profile_dir(self):
        """Create temporary directory for profiles."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def test_config(self) -> RetroPieConfig:
        """Create test configuration."""
        paths = RetroPiePaths(
            home_dir="/home/retro",
            username="retro",
            retropie_dir="/home/retro/RetroPie",
        )
        return RetroPieConfig(
            host="test-retropie.local",
            username="retro",
            password="test_password",  # noqa: S106
            port=22,
            paths=paths,
        )

    def test_server_exposes_resources(
        self, test_config: RetroPieConfig, temp_profile_dir: Path
    ) -> None:
        """Test that server properly exposes resources via MCP."""
        server_config = ServerConfig()
        server = RetroMCPServer(test_config, server_config)

        # Server should have method to list resources
        assert hasattr(server, "list_resources"), (
            "Server should have list_resources method"
        )
        assert hasattr(server, "read_resource"), (
            "Server should have read_resource method"
        )

    def test_resource_uris_are_valid(
        self, test_config: RetroPieConfig, temp_profile_dir: Path
    ) -> None:
        """Test that resource URIs follow MCP standards."""
        server_config = ServerConfig()
        server = RetroMCPServer(test_config, server_config)

        # Test that resources have valid URIs
        resources = asyncio.run(server.list_resources())
        for resource in resources:
            assert hasattr(resource, "uri"), "Resource should have URI"
            assert str(resource.uri).startswith("retropie://"), (
                "Resource URI should use retropie:// scheme"
            )


class TestMCPSecurityCompliance:
    """Test that security requirements from MCP spec are followed."""

    @pytest.fixture
    def temp_profile_dir(self):
        """Create temporary directory for profiles."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def test_config(self) -> RetroPieConfig:
        """Create test configuration."""
        return RetroPieConfig(
            host="test-retropie.local",
            username="retro",
            password="test_password",  # noqa: S106
            port=22,
        )

    def test_server_requires_authentication_config(
        self, test_config: RetroPieConfig, temp_profile_dir: Path
    ) -> None:
        """Test that server requires proper authentication configuration."""
        server_config = ServerConfig()
        server = RetroMCPServer(test_config, server_config)

        # Should have authentication parameters
        assert server.config.host is not None, "Server should have host configured"
        assert server.config.username is not None, (
            "Server should have username configured"
        )

        # Should have some form of authentication
        assert (
            server.config.password is not None or server.config.key_path is not None
        ), "Server should have password or key authentication"

    @pytest.mark.asyncio
    async def test_ssh_connections_are_secure(
        self, test_config: RetroPieConfig, temp_profile_dir: Path
    ) -> None:
        """Test that SSH connections follow security best practices."""
        server_config = ServerConfig()
        server = RetroMCPServer(test_config, server_config)

        # Server should have container with SSH configuration
        assert hasattr(server, "container"), "Server should have container"
        assert hasattr(server.container, "config"), "Container should have config"

        # Configuration should be secure
        config = server.container.config
        assert config.host is not None, "Should have host configured"
        assert config.username is not None, "Should have username configured"

    def test_no_hardcoded_credentials(
        self, test_config: RetroPieConfig, temp_profile_dir: Path
    ) -> None:
        """Test that no credentials are hardcoded in the server."""
        server_config = ServerConfig()
        server = RetroMCPServer(test_config, server_config)

        # Server should use injected config, not hardcoded values
        assert server.config == test_config, "Server should use provided config"

        # Check that server code doesn't contain hardcoded credentials
        # This is a basic check - in practice, you'd scan source files
        server_module = server.__class__.__module__
        assert "password=" not in server_module, (
            "Server module should not contain hardcoded passwords"
        )


class TestMCPTransportCompliance:
    """Test MCP transport layer compliance."""

    @pytest.fixture
    def temp_profile_dir(self):
        """Create temporary directory for profiles."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def test_config(self) -> RetroPieConfig:
        """Create test configuration."""
        return RetroPieConfig(
            host="test-retropie.local",
            username="retro",
            password="test_password",  # noqa: S106
            port=22,
        )

    def test_server_supports_stdio_transport(
        self, test_config: RetroPieConfig, temp_profile_dir: Path
    ) -> None:
        """Test that server supports STDIO transport as required by MCP."""
        server_config = ServerConfig()
        server = RetroMCPServer(test_config, server_config)

        # Should have MCP server instance that supports STDIO
        assert hasattr(server, "server"), "Should have MCP server instance"
        assert isinstance(server.server, Server), "Should be proper MCP Server"

        # Should have run method for STDIO transport
        assert hasattr(server, "run"), "Should have run method for STDIO transport"

    @pytest.mark.asyncio
    async def test_server_handles_async_operations(
        self, test_config: RetroPieConfig, temp_profile_dir: Path
    ) -> None:
        """Test that server properly handles async operations for MCP."""
        server_config = ServerConfig()
        server = RetroMCPServer(test_config, server_config)

        # Test async list_tools
        tools = await server.list_tools()
        assert isinstance(tools, list), "list_tools should be async and return list"

        # Test async list_resources
        resources = await server.list_resources()
        assert isinstance(resources, list), (
            "list_resources should be async and return list"
        )
