"""Unit tests for ConnectionManagementTools implementation."""

from unittest.mock import Mock

import pytest
from mcp.types import TextContent

from retromcp.config import RetroPieConfig
from retromcp.domain.models import ConnectionError
from retromcp.domain.models import ConnectionInfo
from retromcp.domain.models import Result
from retromcp.tools.connection_management_tools import ConnectionManagementTools


@pytest.mark.unit
@pytest.mark.tools
@pytest.mark.connection_management_tools
class TestConnectionManagementTools:
    """Test cases for ConnectionManagementTools class."""

    @pytest.fixture
    def mock_container(self, test_config: RetroPieConfig) -> Mock:
        """Provide mocked container with use cases."""
        mock = Mock()
        mock.test_connection_use_case = Mock()
        mock.config = test_config
        return mock

    @pytest.fixture
    def test_config(self) -> RetroPieConfig:
        """Provide test configuration."""
        from retromcp.discovery import RetroPiePaths

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
            password="test_password",  # noqa: S106
            port=22,
            paths=paths,
        )

    @pytest.fixture
    def connection_tools(self, mock_container: Mock) -> ConnectionManagementTools:
        """Provide ConnectionManagementTools instance with mocked dependencies."""
        return ConnectionManagementTools(mock_container)

    def test_get_tools(self, connection_tools: ConnectionManagementTools) -> None:
        """Test that manage_connection tool is returned."""
        tools = connection_tools.get_tools()

        assert len(tools) == 1
        tool = tools[0]
        assert tool.name == "manage_connection"
        assert "Test and manage system connections" in tool.description

        # Check input schema
        assert tool.inputSchema["type"] == "object"
        assert "action" in tool.inputSchema["properties"]
        assert tool.inputSchema["required"] == ["action"]

        # Check action enum
        action_enum = tool.inputSchema["properties"]["action"]["enum"]
        assert "test" in action_enum
        assert "status" in action_enum
        assert "reconnect" in action_enum

    @pytest.mark.asyncio
    async def test_handle_test_action_success(
        self, connection_tools: ConnectionManagementTools, mock_container: Mock
    ) -> None:
        """Test handling test action with successful connection."""
        connection_info = ConnectionInfo(
            host="test-retropie.local",
            port=22,
            username="retro",
            connected=True,
            last_connected="2025-07-26T06:00:00Z",
        )

        mock_container.test_connection_use_case.execute.return_value = Result.success(
            connection_info
        )

        result = await connection_tools.handle_tool_call(
            "manage_connection", {"action": "test"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Connection test successful!" in result[0].text
        assert "test-retropie.local" in result[0].text
        assert "retro" in result[0].text
        assert "22" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_test_action_failure(
        self, connection_tools: ConnectionManagementTools, mock_container: Mock
    ) -> None:
        """Test handling test action with failed connection."""
        connection_info = ConnectionInfo(
            host="test-retropie.local",
            port=22,
            username="retro",
            connected=False,
        )

        mock_container.test_connection_use_case.execute.return_value = Result.success(
            connection_info
        )

        result = await connection_tools.handle_tool_call(
            "manage_connection", {"action": "test"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Connection test failed" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_test_action_error(
        self, connection_tools: ConnectionManagementTools, mock_container: Mock
    ) -> None:
        """Test handling test action with error from use case."""
        mock_container.test_connection_use_case.execute.return_value = Result.error(
            ConnectionError(
                code="CONNECTION_TEST_FAILED",
                message="SSH connection timeout",
            )
        )

        result = await connection_tools.handle_tool_call(
            "manage_connection", {"action": "test"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Connection test failed" in result[0].text
        assert "SSH connection timeout" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_status_action_connected(
        self, connection_tools: ConnectionManagementTools, mock_container: Mock
    ) -> None:
        """Test handling status action when connected."""
        connection_info = ConnectionInfo(
            host="test-retropie.local",
            port=22,
            username="retro",
            connected=True,
            last_connected="2025-07-26T06:00:00Z",
        )

        mock_container.test_connection_use_case.execute.return_value = Result.success(
            connection_info
        )

        result = await connection_tools.handle_tool_call(
            "manage_connection", {"action": "status"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Connection Status: Connected" in result[0].text
        assert "test-retropie.local" in result[0].text
        assert "retro" in result[0].text
        assert "22" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_status_action_disconnected(
        self, connection_tools: ConnectionManagementTools, mock_container: Mock
    ) -> None:
        """Test handling status action when disconnected."""
        connection_info = ConnectionInfo(
            host="test-retropie.local",
            port=22,
            username="retro",
            connected=False,
        )

        mock_container.test_connection_use_case.execute.return_value = Result.success(
            connection_info
        )

        result = await connection_tools.handle_tool_call(
            "manage_connection", {"action": "status"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Connection Status: Disconnected" in result[0].text
        assert "test-retropie.local" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_status_action_error(
        self, connection_tools: ConnectionManagementTools, mock_container: Mock
    ) -> None:
        """Test handling status action with error from use case."""
        mock_container.test_connection_use_case.execute.return_value = Result.error(
            ConnectionError(
                code="CONNECTION_STATUS_FAILED",
                message="Network unreachable",
            )
        )

        result = await connection_tools.handle_tool_call(
            "manage_connection", {"action": "status"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Failed to get connection status" in result[0].text
        assert "Network unreachable" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_reconnect_action_success(
        self, connection_tools: ConnectionManagementTools, mock_container: Mock
    ) -> None:
        """Test handling reconnect action with successful reconnection."""
        connection_info = ConnectionInfo(
            host="test-retropie.local",
            port=22,
            username="retro",
            connected=True,
            last_connected="2025-07-26T06:00:00Z",
        )

        mock_container.test_connection_use_case.execute.return_value = Result.success(
            connection_info
        )

        result = await connection_tools.handle_tool_call(
            "manage_connection", {"action": "reconnect"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Reconnection successful" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_reconnect_action_failure(
        self, connection_tools: ConnectionManagementTools, mock_container: Mock
    ) -> None:
        """Test handling reconnect action with failed reconnection."""
        connection_info = ConnectionInfo(
            host="test-retropie.local",
            port=22,
            username="retro",
            connected=False,
        )

        mock_container.test_connection_use_case.execute.return_value = Result.success(
            connection_info
        )

        result = await connection_tools.handle_tool_call(
            "manage_connection", {"action": "reconnect"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Reconnection failed" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_reconnect_action_error(
        self, connection_tools: ConnectionManagementTools, mock_container: Mock
    ) -> None:
        """Test handling reconnect action with error from use case."""
        mock_container.test_connection_use_case.execute.return_value = Result.error(
            ConnectionError(
                code="RECONNECTION_FAILED",
                message="Authentication failed",
            )
        )

        result = await connection_tools.handle_tool_call(
            "manage_connection", {"action": "reconnect"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Reconnection failed" in result[0].text
        assert "Authentication failed" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_missing_action(
        self, connection_tools: ConnectionManagementTools
    ) -> None:
        """Test handling missing action."""
        result = await connection_tools.handle_tool_call("manage_connection", {})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Action is required" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_invalid_action(
        self, connection_tools: ConnectionManagementTools
    ) -> None:
        """Test handling invalid action."""
        result = await connection_tools.handle_tool_call(
            "manage_connection", {"action": "invalid"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Unknown action: invalid" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_unknown_tool(
        self, connection_tools: ConnectionManagementTools
    ) -> None:
        """Test handling unknown tool call."""
        result = await connection_tools.handle_tool_call("unknown_tool", {})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Unknown tool: unknown_tool" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_exception_in_connection_management(
        self, connection_tools: ConnectionManagementTools, mock_container: Mock
    ) -> None:
        """Test handling exception during connection management."""
        mock_container.test_connection_use_case.execute.side_effect = Exception(
            "Network error"
        )

        result = await connection_tools.handle_tool_call(
            "manage_connection", {"action": "test"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Connection management error" in result[0].text
        assert "Network error" in result[0].text
