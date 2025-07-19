"""Unit tests for SystemUpdateTools implementation."""

from unittest.mock import Mock

import pytest
from mcp.types import TextContent

from retromcp.config import RetroPieConfig
from retromcp.discovery import RetroPiePaths
from retromcp.domain.models import CommandResult
from retromcp.tools.system_update_tools import SystemUpdateTools


@pytest.mark.unit
@pytest.mark.tools
@pytest.mark.system_tools
class TestSystemUpdateTools:
    """Test cases for SystemUpdateTools class."""

    @pytest.fixture
    def mock_container(self, test_config: RetroPieConfig) -> Mock:
        """Provide mocked container."""
        mock = Mock()
        mock.retropie_client = Mock()
        mock.retropie_client.execute_command = Mock()
        mock.config = test_config
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
    def system_update_tools(self, mock_container: Mock) -> SystemUpdateTools:
        """Provide SystemUpdateTools instance with mocked dependencies."""
        return SystemUpdateTools(mock_container)

    # Schema and Tool Structure Tests

    def test_get_tools_returns_update_system_tool(
        self, system_update_tools: SystemUpdateTools
    ) -> None:
        """Test that get_tools returns the update_system tool."""
        tools = system_update_tools.get_tools()

        assert len(tools) == 1
        tool = tools[0]
        assert tool.name == "update_system"
        assert tool.description == "Perform system updates and maintenance"

    def test_tool_has_proper_schema(
        self, system_update_tools: SystemUpdateTools
    ) -> None:
        """Test that the tool has proper input schema."""
        tools = system_update_tools.get_tools()
        tool = tools[0]

        # Check required properties
        assert "action" in tool.inputSchema["properties"]
        assert "force" in tool.inputSchema["properties"]
        assert tool.inputSchema["required"] == ["action"]

        # Check action enum values
        action_enum = tool.inputSchema["properties"]["action"]["enum"]
        expected_actions = ["update", "upgrade", "check", "cleanup"]
        assert set(action_enum) == set(expected_actions)

        # Check force property
        force_prop = tool.inputSchema["properties"]["force"]
        assert force_prop["type"] == "boolean"
        assert force_prop["default"] is False

    # Action Tests - Success Cases

    @pytest.mark.asyncio
    async def test_handle_system_update_action_success(
        self, system_update_tools: SystemUpdateTools
    ) -> None:
        """Test successful system update action."""
        # Mock successful command execution
        system_update_tools.container.retropie_client.execute_command.return_value = CommandResult(
            command="sudo apt update",
            exit_code=0,
            stdout="Reading package lists... Done\nBuilding dependency tree... Done",
            stderr="",
            success=True,
            execution_time=2.5,
        )

        # Execute update action
        result = await system_update_tools.handle_tool_call(
            "update_system",
            {"action": "update"},
        )

        # Verify result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "✅" in result[0].text
        assert "System update completed" in result[0].text
        assert "Reading package lists... Done" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_system_upgrade_action_success_without_force(
        self, system_update_tools: SystemUpdateTools
    ) -> None:
        """Test successful system upgrade action without force flag."""
        # Mock successful command execution
        system_update_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                command="sudo apt upgrade",
                exit_code=0,
                stdout="Reading package lists... Done\n0 upgraded, 0 newly installed",
                stderr="",
                success=True,
                execution_time=5.2,
            )
        )

        # Execute upgrade action
        result = await system_update_tools.handle_tool_call(
            "update_system",
            {"action": "upgrade"},
        )

        # Verify result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "✅" in result[0].text
        assert "System upgrade completed" in result[0].text
        assert "0 upgraded, 0 newly installed" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_system_upgrade_action_success_with_force(
        self, system_update_tools: SystemUpdateTools
    ) -> None:
        """Test successful system upgrade action with force flag."""
        # Mock successful command execution
        system_update_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                command="sudo apt upgrade -y",
                exit_code=0,
                stdout="Reading package lists... Done\n5 upgraded, 0 newly installed",
                stderr="",
                success=True,
                execution_time=30.1,
            )
        )

        # Execute upgrade action with force
        result = await system_update_tools.handle_tool_call(
            "update_system",
            {"action": "upgrade", "force": True},
        )

        # Verify result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "✅" in result[0].text
        assert "System upgrade completed" in result[0].text
        assert "5 upgraded, 0 newly installed" in result[0].text

        # Verify the command was called with -y flag
        system_update_tools.container.retropie_client.execute_command.assert_called_with(
            "sudo apt upgrade -y", use_sudo=False
        )

    @pytest.mark.asyncio
    async def test_handle_system_check_action_success(
        self, system_update_tools: SystemUpdateTools
    ) -> None:
        """Test successful system check action."""
        # Mock successful command execution
        system_update_tools.container.retropie_client.execute_command.return_value = CommandResult(
            command="sudo apt list --upgradable",
            exit_code=0,
            stdout="Listing... Done\nvim/stable 8.2.0716-3 amd64 [upgradable from: 8.2.0716-2]",
            stderr="",
            success=True,
            execution_time=1.8,
        )

        # Execute check action
        result = await system_update_tools.handle_tool_call(
            "update_system",
            {"action": "check"},
        )

        # Verify result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "i" in result[0].text  # Info icon
        assert "Update check completed" in result[0].text
        assert "vim/stable" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_system_cleanup_action_success(
        self, system_update_tools: SystemUpdateTools
    ) -> None:
        """Test successful system cleanup action."""
        # Mock successful command execution
        system_update_tools.container.retropie_client.execute_command.return_value = CommandResult(
            command="sudo apt autoremove -y",
            exit_code=0,
            stdout="Reading package lists... Done\nRemoving old packages...\n0 to remove",
            stderr="",
            success=True,
            execution_time=3.4,
        )

        # Execute cleanup action
        result = await system_update_tools.handle_tool_call(
            "update_system",
            {"action": "cleanup"},
        )

        # Verify result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "✅" in result[0].text
        assert "System cleanup completed" in result[0].text
        assert "0 to remove" in result[0].text

    # Action Tests - Failure Cases

    @pytest.mark.asyncio
    async def test_handle_system_update_action_failure(
        self, system_update_tools: SystemUpdateTools
    ) -> None:
        """Test failed system update action."""
        # Mock failed command execution
        system_update_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                command="sudo apt update",
                exit_code=1,
                stdout="",
                stderr="E: Could not get lock /var/lib/apt/lists/lock",
                success=False,
                execution_time=0.5,
            )
        )

        # Execute update action
        result = await system_update_tools.handle_tool_call(
            "update_system",
            {"action": "update"},
        )

        # Verify error result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "❌" in result[0].text
        assert "System update failed" in result[0].text
        assert "Could not get lock" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_system_upgrade_action_failure(
        self, system_update_tools: SystemUpdateTools
    ) -> None:
        """Test failed system upgrade action."""
        # Mock failed command execution
        system_update_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                command="sudo apt upgrade -y",
                exit_code=1,
                stdout="",
                stderr="E: Unable to correct problems, you have held broken packages.",
                success=False,
                execution_time=2.1,
            )
        )

        # Execute upgrade action
        result = await system_update_tools.handle_tool_call(
            "update_system",
            {"action": "upgrade", "force": True},
        )

        # Verify error result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "❌" in result[0].text
        assert "System upgrade failed" in result[0].text
        assert "broken packages" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_system_check_action_failure(
        self, system_update_tools: SystemUpdateTools
    ) -> None:
        """Test failed system check action."""
        # Mock failed command execution
        system_update_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                command="sudo apt list --upgradable",
                exit_code=1,
                stdout="",
                stderr="E: The package lists or status file could not be parsed",
                success=False,
                execution_time=0.3,
            )
        )

        # Execute check action
        result = await system_update_tools.handle_tool_call(
            "update_system",
            {"action": "check"},
        )

        # Verify error result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "❌" in result[0].text
        assert "Update check failed" in result[0].text
        assert "could not be parsed" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_system_cleanup_action_failure(
        self, system_update_tools: SystemUpdateTools
    ) -> None:
        """Test failed system cleanup action."""
        # Mock failed command execution
        system_update_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                command="sudo apt autoremove -y",
                exit_code=1,
                stdout="",
                stderr="E: Could not perform immediate configuration",
                success=False,
                execution_time=1.2,
            )
        )

        # Execute cleanup action
        result = await system_update_tools.handle_tool_call(
            "update_system",
            {"action": "cleanup"},
        )

        # Verify error result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "❌" in result[0].text
        assert "System cleanup failed" in result[0].text
        assert "immediate configuration" in result[0].text

    # Parameter Validation Tests

    @pytest.mark.asyncio
    async def test_handle_system_update_missing_action(
        self, system_update_tools: SystemUpdateTools
    ) -> None:
        """Test error handling for missing action parameter."""
        result = await system_update_tools.handle_tool_call(
            "update_system",
            {},
        )

        # Verify error result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "❌" in result[0].text
        assert "Action is required" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_system_update_invalid_action(
        self, system_update_tools: SystemUpdateTools
    ) -> None:
        """Test error handling for invalid action parameter."""
        result = await system_update_tools.handle_tool_call(
            "update_system",
            {"action": "invalid_action"},
        )

        # Verify error result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "❌" in result[0].text
        assert "Unknown action: invalid_action" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_unknown_tool(
        self, system_update_tools: SystemUpdateTools
    ) -> None:
        """Test error handling for unknown tool."""
        result = await system_update_tools.handle_tool_call(
            "unknown_tool",
            {"action": "update"},
        )

        # Verify error result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "❌" in result[0].text
        assert "Unknown tool: unknown_tool" in result[0].text

    # Exception Handling Tests

    @pytest.mark.asyncio
    async def test_handle_system_update_exception_handling(
        self, system_update_tools: SystemUpdateTools
    ) -> None:
        """Test exception handling in system update operations."""
        # Mock exception during command execution
        system_update_tools.container.retropie_client.execute_command.side_effect = (
            Exception("Connection timeout")
        )

        # Execute update action
        result = await system_update_tools.handle_tool_call(
            "update_system",
            {"action": "update"},
        )

        # Verify error result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "❌" in result[0].text
        assert "System update error: Connection timeout" in result[0].text

    # Command Verification Tests

    @pytest.mark.asyncio
    async def test_correct_commands_are_executed(
        self, system_update_tools: SystemUpdateTools
    ) -> None:
        """Test that correct commands are executed for each action."""
        # Mock successful command execution
        mock_result = CommandResult(
            command="test_command",
            exit_code=0,
            stdout="success",
            stderr="",
            success=True,
            execution_time=1.0,
        )
        system_update_tools.container.retropie_client.execute_command.return_value = (
            mock_result
        )

        # Test update command
        await system_update_tools.handle_tool_call(
            "update_system", {"action": "update"}
        )
        system_update_tools.container.retropie_client.execute_command.assert_called_with(
            "sudo apt update", use_sudo=False
        )

        # Test upgrade command without force
        await system_update_tools.handle_tool_call(
            "update_system", {"action": "upgrade"}
        )
        system_update_tools.container.retropie_client.execute_command.assert_called_with(
            "sudo apt upgrade", use_sudo=False
        )

        # Test upgrade command with force
        await system_update_tools.handle_tool_call(
            "update_system", {"action": "upgrade", "force": True}
        )
        system_update_tools.container.retropie_client.execute_command.assert_called_with(
            "sudo apt upgrade -y", use_sudo=False
        )

        # Test check command
        await system_update_tools.handle_tool_call("update_system", {"action": "check"})
        system_update_tools.container.retropie_client.execute_command.assert_called_with(
            "sudo apt list --upgradable", use_sudo=False
        )

        # Test cleanup command
        await system_update_tools.handle_tool_call(
            "update_system", {"action": "cleanup"}
        )
        system_update_tools.container.retropie_client.execute_command.assert_called_with(
            "sudo apt autoremove -y", use_sudo=False
        )

    # Integration with Base Tool Tests

    def test_inheritance_from_base_tool(
        self, system_update_tools: SystemUpdateTools
    ) -> None:
        """Test that SystemUpdateTools inherits from BaseTool."""
        from retromcp.tools.base import BaseTool

        assert isinstance(system_update_tools, BaseTool)
        assert hasattr(system_update_tools, "format_success")
        assert hasattr(system_update_tools, "format_error")
        assert hasattr(system_update_tools, "format_info")

    def test_format_methods_work_correctly(
        self, system_update_tools: SystemUpdateTools
    ) -> None:
        """Test that formatting methods work correctly."""
        # Test format_success
        success_result = system_update_tools.format_success("Test success")
        assert len(success_result) == 1
        assert isinstance(success_result[0], TextContent)
        assert success_result[0].text == "✅ Test success"

        # Test format_error
        error_result = system_update_tools.format_error("Test error")
        assert len(error_result) == 1
        assert isinstance(error_result[0], TextContent)
        assert error_result[0].text == "❌ Test error"

        # Test format_info
        info_result = system_update_tools.format_info("Test info")
        assert len(info_result) == 1
        assert isinstance(info_result[0], TextContent)
        assert info_result[0].text == "i Test info"

    # Force Parameter Edge Cases

    @pytest.mark.asyncio
    async def test_force_parameter_default_false(
        self, system_update_tools: SystemUpdateTools
    ) -> None:
        """Test that force parameter defaults to False."""
        # Mock successful command execution
        system_update_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                command="sudo apt upgrade",
                exit_code=0,
                stdout="success",
                stderr="",
                success=True,
                execution_time=1.0,
            )
        )

        # Execute upgrade without specifying force
        await system_update_tools.handle_tool_call(
            "update_system", {"action": "upgrade"}
        )

        # Verify command was called without -y flag
        system_update_tools.container.retropie_client.execute_command.assert_called_with(
            "sudo apt upgrade", use_sudo=False
        )

    @pytest.mark.asyncio
    async def test_force_parameter_explicit_false(
        self, system_update_tools: SystemUpdateTools
    ) -> None:
        """Test force parameter set explicitly to False."""
        # Mock successful command execution
        system_update_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                command="sudo apt upgrade",
                exit_code=0,
                stdout="success",
                stderr="",
                success=True,
                execution_time=1.0,
            )
        )

        # Execute upgrade with force explicitly set to False
        await system_update_tools.handle_tool_call(
            "update_system", {"action": "upgrade", "force": False}
        )

        # Verify command was called without -y flag
        system_update_tools.container.retropie_client.execute_command.assert_called_with(
            "sudo apt upgrade", use_sudo=False
        )

    @pytest.mark.asyncio
    async def test_force_parameter_only_affects_upgrade(
        self, system_update_tools: SystemUpdateTools
    ) -> None:
        """Test that force parameter only affects upgrade action."""
        # Mock successful command execution
        system_update_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                command="test_command",
                exit_code=0,
                stdout="success",
                stderr="",
                success=True,
                execution_time=1.0,
            )
        )

        # Test that force doesn't affect update action
        await system_update_tools.handle_tool_call(
            "update_system", {"action": "update", "force": True}
        )
        system_update_tools.container.retropie_client.execute_command.assert_called_with(
            "sudo apt update", use_sudo=False
        )

        # Test that force doesn't affect check action
        await system_update_tools.handle_tool_call(
            "update_system", {"action": "check", "force": True}
        )
        system_update_tools.container.retropie_client.execute_command.assert_called_with(
            "sudo apt list --upgradable", use_sudo=False
        )

        # Test that force doesn't affect cleanup action (cleanup already has -y)
        await system_update_tools.handle_tool_call(
            "update_system", {"action": "cleanup", "force": True}
        )
        system_update_tools.container.retropie_client.execute_command.assert_called_with(
            "sudo apt autoremove -y", use_sudo=False
        )
