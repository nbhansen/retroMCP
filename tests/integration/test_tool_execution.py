"""Integration tests for tool execution through MCP server.

This module ensures that all tools listed by the server can actually be called.
This prevents issues where tools appear in list_tools() but fail with "Unknown tool"
when actually called.
"""

from typing import List
from unittest.mock import AsyncMock
from unittest.mock import patch

import pytest
from mcp.types import TextContent

from retromcp.config import RetroPieConfig
from retromcp.config import ServerConfig
from retromcp.server import RetroMCPServer


class TestToolExecution:
    """Test that all listed tools can be executed."""

    @pytest.fixture
    def server_config(self) -> ServerConfig:
        """Provide server configuration."""
        return ServerConfig()

    @pytest.mark.asyncio
    async def test_all_listed_tools_are_callable(
        self, test_config: RetroPieConfig, server_config: ServerConfig
    ) -> None:
        """Test that every tool returned by list_tools() can be called."""
        server = RetroMCPServer(test_config, server_config)

        # Mock infrastructure
        with patch.object(server.container, "connect", return_value=True):
            # Get all available tools
            tools = await server.list_tools()
            tool_names = [tool.name for tool in tools]

            # Mock tool handlers to return success
            with patch("retromcp.server.SystemManagementTools") as mock_system, patch(
                "retromcp.server.GamingSystemTools"
            ) as mock_gaming, patch(
                "retromcp.server.HardwareMonitoringTools"
            ) as mock_hw, patch("retromcp.server.StateTools") as mock_state, patch(
                "retromcp.server.DockerTools"
            ) as mock_docker:
                # Setup mocks
                for mock_class in [
                    mock_system,
                    mock_gaming,
                    mock_hw,
                    mock_state,
                    mock_docker,
                ]:
                    mock_instance = mock_class.return_value
                    mock_instance.handle_tool_call = AsyncMock(
                        return_value=[
                            TextContent(
                                type="text", text="✅ Tool executed successfully"
                            )
                        ]
                    )
                    # Make get_tools return appropriate tools for each class
                    if mock_class == mock_system:
                        mock_instance.get_tools.return_value = [
                            t
                            for t in tools
                            if t.name
                            in [
                                "manage_connection",
                                "manage_service",
                                "manage_package",
                                "manage_file",
                                "execute_command",
                                "get_system_info",
                                "update_system",
                            ]
                        ]
                    elif mock_class == mock_gaming:
                        mock_instance.get_tools.return_value = [
                            t for t in tools if t.name == "manage_gaming"
                        ]
                    elif mock_class == mock_hw:
                        mock_instance.get_tools.return_value = [
                            t for t in tools if t.name == "manage_hardware"
                        ]
                    elif mock_class == mock_state:
                        mock_instance.get_tools.return_value = [
                            t for t in tools if t.name == "manage_state"
                        ]
                    elif mock_class == mock_docker:
                        mock_instance.get_tools.return_value = [
                            t for t in tools if t.name == "manage_docker"
                        ]

                # Test each tool can be called
                failed_tools: List[str] = []
                for tool_name in tool_names:
                    try:
                        result = await server.call_tool(tool_name, {})

                        # Verify successful response
                        assert len(result) == 1
                        assert isinstance(result[0], TextContent)

                        # Check for error indicators
                        if "Unknown tool" in result[0].text or "❌" in result[0].text:
                            failed_tools.append(f"{tool_name}: {result[0].text}")
                    except Exception as e:
                        failed_tools.append(f"{tool_name}: {e!s}")

                # Assert no tools failed
                assert len(failed_tools) == 0, (
                    "The following tools are listed but cannot be called:\n"
                    + "\n".join(failed_tools)
                )

    @pytest.mark.asyncio
    async def test_unified_tools_can_be_called(
        self, test_config: RetroPieConfig, server_config: ServerConfig
    ) -> None:
        """Test that the unified tools (manage_hardware, manage_gaming, manage_state) work."""
        server = RetroMCPServer(test_config, server_config)

        unified_tools = ["manage_hardware", "manage_gaming", "manage_state"]

        with patch.object(server.container, "connect", return_value=True), patch(
            "retromcp.server.HardwareMonitoringTools"
        ) as mock_hw, patch("retromcp.server.GamingSystemTools") as mock_gaming, patch(
            "retromcp.server.StateTools"
        ) as mock_state:
            # Map tool names to their mocks
            tool_mocks = {
                "manage_hardware": mock_hw,
                "manage_gaming": mock_gaming,
                "manage_state": mock_state,
            }

            # Setup each mock
            for tool_name, mock_class in tool_mocks.items():
                mock_instance = mock_class.return_value
                mock_instance.handle_tool_call = AsyncMock(
                    return_value=[
                        TextContent(
                            type="text", text=f"✅ {tool_name} executed successfully"
                        )
                    ]
                )

            # Test each unified tool
            for tool_name in unified_tools:
                result = await server.call_tool(tool_name, {"action": "test"})

                # Verify success
                assert len(result) == 1
                assert isinstance(result[0], TextContent)
                assert "✅" in result[0].text
                assert tool_name in result[0].text
                assert "Unknown tool" not in result[0].text

                # Verify the appropriate handler was called
                mock_instance = tool_mocks[tool_name].return_value
                mock_instance.handle_tool_call.assert_called_with(
                    tool_name, {"action": "test"}
                )

    @pytest.mark.asyncio
    async def test_tool_routing_matches_list_tools(
        self, test_config: RetroPieConfig, server_config: ServerConfig
    ) -> None:
        """Test that all tools in list_tools() exist in the routing dictionary."""
        server = RetroMCPServer(test_config, server_config)

        # Get all tools
        tools = await server.list_tools()
        tool_names = {tool.name for tool in tools}

        # Get the routing dictionary by attempting to access it during tool call
        with patch.object(server.container, "connect", return_value=True):
            # Call a non-existent tool to trigger the routing logic
            await server.call_tool("_test_nonexistent_tool_", {})

            # Now check that all listed tools would be routable
            # We need to access the tool_routing from within call_tool
            # Let's verify by attempting to call each tool
            missing_routes: List[str] = []

            for tool_name in tool_names:
                # Special handling for connection_error which is always available
                if tool_name == "connection_error":
                    continue

                # Try to call the tool and check if it's unknown
                result = await server.call_tool(tool_name, {})
                if len(result) > 0 and "Unknown tool" in result[0].text:
                    missing_routes.append(tool_name)

            assert len(missing_routes) == 0, (
                "The following tools are listed but not routed:\n"
                + "\n".join(missing_routes)
            )
