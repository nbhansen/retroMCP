"""Test ServiceManagementTools following TDD methodology and Result pattern."""

from unittest.mock import Mock
from typing import List

import pytest
from mcp.types import TextContent, ImageContent, EmbeddedResource

from retromcp.domain.models import CommandResult, Result, DomainError
from retromcp.tools.service_management_tools import ServiceManagementTools


@pytest.mark.unit
@pytest.mark.tools
@pytest.mark.service_tools
class TestServiceManagementTools:
    """Test ServiceManagementTools with comprehensive coverage."""

    @pytest.fixture
    def mock_container(self) -> Mock:
        """Provide mocked container."""
        mock = Mock()
        mock.retropie_client = Mock()
        mock.retropie_client.execute_command = Mock()
        return mock

    @pytest.fixture
    def service_tools(self, mock_container: Mock) -> ServiceManagementTools:
        """Provide ServiceManagementTools instance with mocked dependencies."""
        return ServiceManagementTools(mock_container)

    # Tool Schema Tests

    def test_get_tools_returns_correct_schema(self, service_tools: ServiceManagementTools) -> None:
        """Test get_tools returns correct tool schema."""
        tools = service_tools.get_tools()
        
        assert len(tools) == 1
        tool = tools[0]
        
        assert tool.name == "manage_service"
        assert "Manage system services" in tool.description
        
        # Verify schema structure
        schema = tool.inputSchema
        assert schema["type"] == "object"
        assert "action" in schema["properties"]
        assert "name" in schema["properties"]
        assert schema["required"] == ["action", "name"]
        
        # Verify action enum
        action_enum = schema["properties"]["action"]["enum"]
        expected_actions = ["start", "stop", "restart", "enable", "disable", "status"]
        assert action_enum == expected_actions

    # Service Start Operation Tests

    @pytest.mark.asyncio
    async def test_start_service_success(self, service_tools: ServiceManagementTools) -> None:
        """Test successful service start operation."""
        # Mock successful command execution
        mock_result = CommandResult(
            command="sudo systemctl start nginx",
            exit_code=0,
            stdout="Started nginx successfully",
            stderr="",
            success=True,
            execution_time=2.5,
        )
        service_tools.container.retropie_client.execute_command.return_value = mock_result

        # Execute service start
        result = await service_tools.handle_tool_call(
            "manage_service",
            {"action": "start", "name": "nginx"},
        )

        # Verify result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "nginx start: Started nginx successfully" in result[0].text
        service_tools.container.retropie_client.execute_command.assert_called_once_with(
            "sudo systemctl start nginx"
        )

    @pytest.mark.asyncio
    async def test_start_service_failure(self, service_tools: ServiceManagementTools) -> None:
        """Test failed service start operation."""
        # Mock failed command execution
        mock_result = CommandResult(
            command="sudo systemctl start nginx",
            exit_code=1,
            stdout="",
            stderr="Failed to start nginx.service",
            success=False,
            execution_time=1.0,
        )
        service_tools.container.retropie_client.execute_command.return_value = mock_result

        # Execute service start
        result = await service_tools.handle_tool_call(
            "manage_service",
            {"action": "start", "name": "nginx"},
        )

        # Verify error result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Failed to start service nginx: Failed to start nginx.service" in result[0].text

    # Service Stop Operation Tests

    @pytest.mark.asyncio
    async def test_stop_service_success(self, service_tools: ServiceManagementTools) -> None:
        """Test successful service stop operation."""
        mock_result = CommandResult(
            command="sudo systemctl stop apache2",
            exit_code=0,
            stdout="Stopped apache2 successfully",
            stderr="",
            success=True,
            execution_time=1.5,
        )
        service_tools.container.retropie_client.execute_command.return_value = mock_result

        result = await service_tools.handle_tool_call(
            "manage_service",
            {"action": "stop", "name": "apache2"},
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "apache2 stop: Stopped apache2 successfully" in result[0].text
        service_tools.container.retropie_client.execute_command.assert_called_once_with(
            "sudo systemctl stop apache2"
        )

    # Service Restart Operation Tests

    @pytest.mark.asyncio
    async def test_restart_service_success(self, service_tools: ServiceManagementTools) -> None:
        """Test successful service restart operation."""
        mock_result = CommandResult(
            command="sudo systemctl restart ssh",
            exit_code=0,
            stdout="Restarted ssh successfully",
            stderr="",
            success=True,
            execution_time=3.0,
        )
        service_tools.container.retropie_client.execute_command.return_value = mock_result

        result = await service_tools.handle_tool_call(
            "manage_service",
            {"action": "restart", "name": "ssh"},
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "ssh restart: Restarted ssh successfully" in result[0].text
        service_tools.container.retropie_client.execute_command.assert_called_once_with(
            "sudo systemctl restart ssh"
        )

    # Service Enable Operation Tests

    @pytest.mark.asyncio
    async def test_enable_service_success(self, service_tools: ServiceManagementTools) -> None:
        """Test successful service enable operation."""
        mock_result = CommandResult(
            command="sudo systemctl enable docker",
            exit_code=0,
            stdout="Created symlink /etc/systemd/system/multi-user.target.wants/docker.service",
            stderr="",
            success=True,
            execution_time=1.0,
        )
        service_tools.container.retropie_client.execute_command.return_value = mock_result

        result = await service_tools.handle_tool_call(
            "manage_service",
            {"action": "enable", "name": "docker"},
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "docker enable:" in result[0].text
        assert "Created symlink" in result[0].text
        service_tools.container.retropie_client.execute_command.assert_called_once_with(
            "sudo systemctl enable docker"
        )

    # Service Disable Operation Tests

    @pytest.mark.asyncio
    async def test_disable_service_success(self, service_tools: ServiceManagementTools) -> None:
        """Test successful service disable operation."""
        mock_result = CommandResult(
            command="sudo systemctl disable bluetooth",
            exit_code=0,
            stdout="Removed /etc/systemd/system/multi-user.target.wants/bluetooth.service",
            stderr="",
            success=True,
            execution_time=0.8,
        )
        service_tools.container.retropie_client.execute_command.return_value = mock_result

        result = await service_tools.handle_tool_call(
            "manage_service",
            {"action": "disable", "name": "bluetooth"},
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "bluetooth disable:" in result[0].text
        assert "Removed" in result[0].text
        service_tools.container.retropie_client.execute_command.assert_called_once_with(
            "sudo systemctl disable bluetooth"
        )

    # Service Status Operation Tests

    @pytest.mark.asyncio
    async def test_status_service_success(self, service_tools: ServiceManagementTools) -> None:
        """Test successful service status operation."""
        mock_result = CommandResult(
            command="systemctl status nginx --no-pager",
            exit_code=0,
            stdout="● nginx.service - A high performance web server\nActive: active (running) since Mon 2023-01-01",
            stderr="",
            success=True,
            execution_time=0.5,
        )
        service_tools.container.retropie_client.execute_command.return_value = mock_result

        result = await service_tools.handle_tool_call(
            "manage_service",
            {"action": "status", "name": "nginx"},
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "nginx status:" in result[0].text
        assert "Active: active (running)" in result[0].text
        service_tools.container.retropie_client.execute_command.assert_called_once_with(
            "systemctl status nginx --no-pager"
        )

    # Error Handling Tests

    @pytest.mark.asyncio
    async def test_unknown_tool_name(self, service_tools: ServiceManagementTools) -> None:
        """Test handling of unknown tool name."""
        result = await service_tools.handle_tool_call(
            "unknown_tool",
            {"action": "start", "name": "nginx"},
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Unknown tool: unknown_tool" in result[0].text

    @pytest.mark.asyncio
    async def test_missing_action_parameter(self, service_tools: ServiceManagementTools) -> None:
        """Test handling of missing action parameter."""
        result = await service_tools.handle_tool_call(
            "manage_service",
            {"name": "nginx"},
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Both 'action' and 'name' are required" in result[0].text

    @pytest.mark.asyncio
    async def test_missing_name_parameter(self, service_tools: ServiceManagementTools) -> None:
        """Test handling of missing name parameter."""
        result = await service_tools.handle_tool_call(
            "manage_service",
            {"action": "start"},
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Both 'action' and 'name' are required" in result[0].text

    @pytest.mark.asyncio
    async def test_empty_action_parameter(self, service_tools: ServiceManagementTools) -> None:
        """Test handling of empty action parameter."""
        result = await service_tools.handle_tool_call(
            "manage_service",
            {"action": "", "name": "nginx"},
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Both 'action' and 'name' are required" in result[0].text

    @pytest.mark.asyncio
    async def test_empty_name_parameter(self, service_tools: ServiceManagementTools) -> None:
        """Test handling of empty name parameter."""
        result = await service_tools.handle_tool_call(
            "manage_service",
            {"action": "start", "name": ""},
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Both 'action' and 'name' are required" in result[0].text

    @pytest.mark.asyncio
    async def test_unknown_action(self, service_tools: ServiceManagementTools) -> None:
        """Test handling of unknown action."""
        result = await service_tools.handle_tool_call(
            "manage_service",
            {"action": "unknown", "name": "nginx"},
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Unknown action: unknown" in result[0].text

    @pytest.mark.asyncio
    async def test_exception_handling(self, service_tools: ServiceManagementTools) -> None:
        """Test handling of exceptions during execution."""
        # Mock exception during command execution
        service_tools.container.retropie_client.execute_command.side_effect = Exception("Connection failed")

        result = await service_tools.handle_tool_call(
            "manage_service",
            {"action": "start", "name": "nginx"},
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Service management error: Connection failed" in result[0].text

    # Edge Cases and Additional Coverage

    @pytest.mark.asyncio
    async def test_service_with_special_characters(self, service_tools: ServiceManagementTools) -> None:
        """Test service management with special characters in service name."""
        mock_result = CommandResult(
            command="sudo systemctl start my-custom.service",
            exit_code=0,
            stdout="Started my-custom.service",
            stderr="",
            success=True,
            execution_time=1.0,
        )
        service_tools.container.retropie_client.execute_command.return_value = mock_result

        result = await service_tools.handle_tool_call(
            "manage_service",
            {"action": "start", "name": "my-custom.service"},
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "my-custom.service start: Started my-custom.service" in result[0].text

    @pytest.mark.asyncio
    async def test_service_command_with_stderr_output(self, service_tools: ServiceManagementTools) -> None:
        """Test service command that succeeds but has stderr output."""
        mock_result = CommandResult(
            command="systemctl status unknown-service --no-pager",
            exit_code=0,
            stdout="● unknown-service.service - Unknown Service\nActive: inactive (dead)",
            stderr="Warning: Service not found",
            success=True,
            execution_time=0.3,
        )
        service_tools.container.retropie_client.execute_command.return_value = mock_result

        result = await service_tools.handle_tool_call(
            "manage_service",
            {"action": "status", "name": "unknown-service"},
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "unknown-service status:" in result[0].text
        assert "Active: inactive (dead)" in result[0].text