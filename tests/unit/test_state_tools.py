"""Unit tests for StateTools implementation."""

from unittest.mock import Mock

import pytest
from mcp.types import TextContent

from retromcp.config import RetroPieConfig
from retromcp.domain.models import StateAction
from retromcp.domain.models import StateManagementResult
from retromcp.domain.models import SystemState
from retromcp.tools.state_tools import StateTools


class TestStateTools:
    """Test cases for StateTools class."""

    @pytest.fixture
    def mock_container(self, test_config: RetroPieConfig) -> Mock:
        """Provide mocked container with use cases."""
        mock = Mock()
        mock.manage_state_use_case = Mock()
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
    def state_tools(self, mock_container: Mock) -> StateTools:
        """Provide StateTools instance with mocked dependencies."""
        return StateTools(mock_container)

    def test_get_tools(self, state_tools: StateTools) -> None:
        """Test that manage_state tool is returned."""
        tools = state_tools.get_tools()

        assert len(tools) == 1
        tool = tools[0]
        assert tool.name == "manage_state"
        assert "persistent system state" in tool.description

        # Check input schema
        assert tool.inputSchema["type"] == "object"
        assert "action" in tool.inputSchema["properties"]
        assert tool.inputSchema["required"] == ["action"]

        # Check action enum
        action_enum = tool.inputSchema["properties"]["action"]["enum"]
        assert "load" in action_enum
        assert "save" in action_enum
        assert "update" in action_enum
        assert "compare" in action_enum

    @pytest.mark.asyncio
    async def test_handle_load_action(
        self, state_tools: StateTools, mock_container: Mock
    ) -> None:
        """Test handling load action."""
        sample_state = SystemState(
            schema_version="1.0",
            last_updated="2025-07-15T12:00:00Z",
            system={"hostname": "retropie"},
            emulators={"installed": ["mupen64plus"], "preferred": {}},
            controllers=[],
            roms={"systems": [], "counts": {}},
            custom_configs=[],
            known_issues=[],
        )

        mock_container.manage_state_use_case.execute.return_value = (
            StateManagementResult(
                success=True,
                action=StateAction.LOAD,
                message="State loaded successfully",
                state=sample_state,
            )
        )

        result = await state_tools.handle_tool_call("manage_state", {"action": "load"})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "State loaded successfully" in result[0].text
        assert "retropie" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_save_action(
        self, state_tools: StateTools, mock_container: Mock
    ) -> None:
        """Test handling save action."""
        mock_container.manage_state_use_case.execute.return_value = (
            StateManagementResult(
                success=True,
                action=StateAction.SAVE,
                message="State saved successfully",
            )
        )

        result = await state_tools.handle_tool_call("manage_state", {"action": "save"})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "State saved successfully" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_save_action_with_force_scan(
        self, state_tools: StateTools, mock_container: Mock
    ) -> None:
        """Test handling save action with force_scan."""
        mock_container.manage_state_use_case.execute.return_value = (
            StateManagementResult(
                success=True,
                action=StateAction.SAVE,
                message="State saved successfully",
            )
        )

        result = await state_tools.handle_tool_call(
            "manage_state", {"action": "save", "force_scan": True}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "State saved successfully" in result[0].text

        # Verify force_scan was passed to the use case
        call_args = mock_container.manage_state_use_case.execute.call_args[0][0]
        assert call_args.force_scan is True

    @pytest.mark.asyncio
    async def test_handle_update_action(
        self, state_tools: StateTools, mock_container: Mock
    ) -> None:
        """Test handling update action."""
        mock_container.manage_state_use_case.execute.return_value = (
            StateManagementResult(
                success=True,
                action=StateAction.UPDATE,
                message="Field updated successfully",
            )
        )

        result = await state_tools.handle_tool_call(
            "manage_state",
            {"action": "update", "path": "system.hostname", "value": "new-hostname"},
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Field updated successfully" in result[0].text

        # Verify path and value were passed to the use case
        call_args = mock_container.manage_state_use_case.execute.call_args[0][0]
        assert call_args.path == "system.hostname"
        assert call_args.value == "new-hostname"

    @pytest.mark.asyncio
    async def test_handle_compare_action(
        self, state_tools: StateTools, mock_container: Mock
    ) -> None:
        """Test handling compare action."""
        diff = {
            "added": {"system.new_field": "value"},
            "changed": {"system.hostname": {"old": "old-name", "new": "new-name"}},
            "removed": {},
        }

        mock_container.manage_state_use_case.execute.return_value = (
            StateManagementResult(
                success=True,
                action=StateAction.COMPARE,
                message="Comparison complete",
                diff=diff,
            )
        )

        result = await state_tools.handle_tool_call(
            "manage_state", {"action": "compare"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Comparison complete" in result[0].text
        assert "Added fields:" in result[0].text
        assert "Changed fields:" in result[0].text
        assert "system.new_field" in result[0].text
        assert "system.hostname" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_compare_action_no_differences(
        self, state_tools: StateTools, mock_container: Mock
    ) -> None:
        """Test handling compare action with no differences."""
        diff = {"added": {}, "changed": {}, "removed": {}}

        mock_container.manage_state_use_case.execute.return_value = (
            StateManagementResult(
                success=True,
                action=StateAction.COMPARE,
                message="Comparison complete",
                diff=diff,
            )
        )

        result = await state_tools.handle_tool_call(
            "manage_state", {"action": "compare"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "No differences found" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_invalid_action(self, state_tools: StateTools) -> None:
        """Test handling invalid action."""
        result = await state_tools.handle_tool_call(
            "manage_state", {"action": "invalid"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Invalid action" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_missing_action(self, state_tools: StateTools) -> None:
        """Test handling missing action."""
        result = await state_tools.handle_tool_call("manage_state", {})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Action is required" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_update_missing_path(self, state_tools: StateTools) -> None:
        """Test handling update action with missing path."""
        result = await state_tools.handle_tool_call(
            "manage_state", {"action": "update"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Path and value are required" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_update_missing_value(self, state_tools: StateTools) -> None:
        """Test handling update action with missing value."""
        result = await state_tools.handle_tool_call(
            "manage_state", {"action": "update", "path": "system.hostname"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Path and value are required" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_error_from_use_case(
        self, state_tools: StateTools, mock_container: Mock
    ) -> None:
        """Test handling error from use case."""
        mock_container.manage_state_use_case.execute.return_value = (
            StateManagementResult(
                success=False, action=StateAction.LOAD, message="File not found"
            )
        )

        result = await state_tools.handle_tool_call("manage_state", {"action": "load"})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "File not found" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_exception(
        self, state_tools: StateTools, mock_container: Mock
    ) -> None:
        """Test handling exception from use case."""
        mock_container.manage_state_use_case.execute.side_effect = Exception(
            "Database error"
        )

        result = await state_tools.handle_tool_call("manage_state", {"action": "load"})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Error" in result[0].text
        assert "Database error" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_unknown_tool(self, state_tools: StateTools) -> None:
        """Test handling unknown tool call."""
        result = await state_tools.handle_tool_call("unknown_tool", {})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Unknown tool" in result[0].text
