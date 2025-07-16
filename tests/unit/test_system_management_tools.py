"""Unit tests for SystemManagementTools implementation."""

from unittest.mock import Mock

import pytest
from mcp.types import TextContent

from retromcp.config import RetroPieConfig
from retromcp.discovery import RetroPiePaths
from retromcp.domain.models import CommandResult
from retromcp.tools.system_management_tools import SystemManagementTools


class TestSystemManagementTools:
    """Test cases for SystemManagementTools class."""

    @pytest.fixture
    def mock_container(self, test_config: RetroPieConfig) -> Mock:
        """Provide mocked container."""
        mock = Mock()
        mock.retropie_client = Mock()
        mock.retropie_client.execute_command = Mock()
        mock.config = test_config

        # Mock use cases
        mock.execute_command_use_case = Mock()
        mock.write_file_use_case = Mock()
        mock.test_connection_use_case = Mock()
        mock.get_system_info_use_case = Mock()
        mock.update_system_use_case = Mock()
        mock.system_repository = Mock()

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
    def system_management_tools(self, mock_container: Mock) -> SystemManagementTools:
        """Provide SystemManagementTools instance with mocked dependencies."""
        return SystemManagementTools(mock_container)

    # Schema and Tool Structure Tests

    def test_get_tools_returns_single_manage_system_tool(
        self, system_management_tools: SystemManagementTools
    ) -> None:
        """Test that get_tools returns exactly one manage_system tool."""
        tools = system_management_tools.get_tools()

        assert len(tools) == 1
        assert tools[0].name == "manage_system"
        assert "system administration" in tools[0].description.lower()

    def test_manage_system_tool_schema_validation(
        self, system_management_tools: SystemManagementTools
    ) -> None:
        """Test that manage_system tool has proper schema with all resources and actions."""
        tools = system_management_tools.get_tools()
        tool = tools[0]

        # Check required properties
        assert "resource" in tool.inputSchema["properties"]
        assert "action" in tool.inputSchema["properties"]
        assert tool.inputSchema["required"] == ["resource", "action"]

        # Check resource enum
        resource_enum = tool.inputSchema["properties"]["resource"]["enum"]
        expected_resources = [
            "service",
            "package",
            "file",
            "command",
            "connection",
            "info",
            "update",
        ]
        assert set(resource_enum) == set(expected_resources)

    # Service Resource Tests

    @pytest.mark.asyncio
    async def test_manage_system_service_start_success(
        self, system_management_tools: SystemManagementTools
    ) -> None:
        """Test successful service start operation."""
        # Mock successful command execution
        system_management_tools.container.retropie_client.execute_command.return_value = CommandResult(
            command="sudo systemctl start test-service",
            exit_code=0,
            stdout="Started test-service successfully",
            stderr="",
            success=True,
            execution_time=1.5,
        )

        # Execute service start
        result = await system_management_tools.handle_tool_call(
            "manage_system",
            {
                "resource": "service",
                "action": "start",
                "name": "test-service",
            },
        )

        # Verify result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "started successfully" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_manage_system_service_status(
        self, system_management_tools: SystemManagementTools
    ) -> None:
        """Test service status check operation."""
        # Mock service status output
        system_management_tools.container.retropie_client.execute_command.return_value = CommandResult(
            command="systemctl status test-service --no-pager",
            exit_code=0,
            stdout="● test-service - Test Service\n   Loaded: loaded\n   Active: active (running) since...",
            stderr="",
            success=True,
            execution_time=0.5,
        )

        # Execute service status check
        result = await system_management_tools.handle_tool_call(
            "manage_system",
            {
                "resource": "service",
                "action": "status",
                "name": "test-service",
            },
        )

        # Verify result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "active (running)" in result[0].text.lower()

    # Package Resource Tests

    @pytest.mark.asyncio
    async def test_manage_system_package_install_success(
        self, system_management_tools: SystemManagementTools
    ) -> None:
        """Test successful package installation."""
        # Mock successful package installation
        system_management_tools.container.retropie_client.execute_command.return_value = CommandResult(
            command="sudo apt-get install -y test-package",
            exit_code=0,
            stdout="Successfully installed test-package",
            stderr="",
            success=True,
            execution_time=30.0,
        )

        # Execute package installation
        result = await system_management_tools.handle_tool_call(
            "manage_system",
            {
                "resource": "package",
                "action": "install",
                "packages": ["test-package"],
            },
        )

        # Verify result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "successfully installed" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_manage_system_package_check_verification(
        self, system_management_tools: SystemManagementTools
    ) -> None:
        """Test package verification functionality."""
        # Mock package check output
        system_management_tools.container.retropie_client.execute_command.return_value = CommandResult(
            command="dpkg -l test-package 2>/dev/null | grep '^ii'",
            exit_code=0,
            stdout="ii  test-package  1.0  amd64  Test package",
            stderr="",
            success=True,
            execution_time=0.2,
        )

        # Execute package check
        result = await system_management_tools.handle_tool_call(
            "manage_system",
            {
                "resource": "package",
                "action": "check",
                "packages": ["test-package"],
            },
        )

        # Verify result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "✅ test-package: Installed" in result[0].text

    # File Resource Tests

    @pytest.mark.asyncio
    async def test_manage_system_file_read_success(
        self, system_management_tools: SystemManagementTools
    ) -> None:
        """Test successful file read operation."""
        # Mock successful file read
        system_management_tools.container.retropie_client.execute_command.return_value = CommandResult(
            command="cat /test/file.txt",
            exit_code=0,
            stdout="Test file content\nLine 2\nLine 3",
            stderr="",
            success=True,
            execution_time=0.1,
        )

        # Execute file read
        result = await system_management_tools.handle_tool_call(
            "manage_system",
            {
                "resource": "file",
                "action": "read",
                "path": "/test/file.txt",
            },
        )

        # Verify result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Test file content" in result[0].text

    @pytest.mark.asyncio
    async def test_manage_system_file_write_with_parents(
        self, system_management_tools: SystemManagementTools
    ) -> None:
        """Test file write with parent directory creation."""
        # Mock successful file write
        system_management_tools.container.retropie_client.execute_command.return_value = CommandResult(
            command="echo 'Test content' | sudo tee /test/new/file.txt > /dev/null",
            exit_code=0,
            stdout="",
            stderr="",
            success=True,
            execution_time=0.2,
        )

        # Execute file write with parent creation
        result = await system_management_tools.handle_tool_call(
            "manage_system",
            {
                "resource": "file",
                "action": "write",
                "path": "/test/new/file.txt",
                "content": "Test content",
                "create_parents": True,
            },
        )

        # Verify result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "written" in result[0].text.lower()

    # Command Resource Tests

    @pytest.mark.asyncio
    async def test_manage_system_command_execute_success(
        self, system_management_tools: SystemManagementTools
    ) -> None:
        """Test successful command execution."""
        # Mock successful command execution
        mock_result = CommandResult(
            command="ls -la /home",
            exit_code=0,
            stdout="total 12\ndrwxr-xr-x  3 root root 4096 Jan  1 00:00 .\n",
            stderr="",
            success=True,
            execution_time=0.1,
        )
        system_management_tools.container.execute_command_use_case.execute.return_value = mock_result

        # Execute command
        result = await system_management_tools.handle_tool_call(
            "manage_system",
            {
                "resource": "command",
                "action": "execute",
                "command": "ls -la /home",
            },
        )

        # Verify result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Command Executed Successfully" in result[0].text

    @pytest.mark.asyncio
    async def test_manage_system_command_security_validation(
        self, system_management_tools: SystemManagementTools
    ) -> None:
        """Test command security validation."""
        # Mock security validation failure
        system_management_tools.container.execute_command_use_case.execute.side_effect = ValueError(
            "Command contains dangerous pattern"
        )

        # Execute dangerous command
        result = await system_management_tools.handle_tool_call(
            "manage_system",
            {
                "resource": "command",
                "action": "execute",
                "command": "rm -rf /",
            },
        )

        # Verify security error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "security validation failed" in result[0].text.lower()

    # Connection Resource Tests

    @pytest.mark.asyncio
    async def test_manage_system_connection_test_success(
        self, system_management_tools: SystemManagementTools
    ) -> None:
        """Test successful connection test."""
        # Mock successful connection
        mock_connection_info = Mock()
        mock_connection_info.connected = True
        mock_connection_info.host = "test-retropie.local"
        mock_connection_info.port = 22
        mock_connection_info.username = "retro"
        mock_connection_info.connection_method = "password"
        mock_connection_info.last_connected = "2024-01-01 12:00:00"

        system_management_tools.container.test_connection_use_case.execute.return_value = mock_connection_info

        # Execute connection test
        result = await system_management_tools.handle_tool_call(
            "manage_system",
            {
                "resource": "connection",
                "action": "test",
            },
        )

        # Verify result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "successfully connected" in result[0].text.lower()

    # Info Resource Tests

    @pytest.mark.asyncio
    async def test_manage_system_info_get_with_ports(
        self, system_management_tools: SystemManagementTools
    ) -> None:
        """Test system info retrieval with port monitoring."""
        # Mock system info
        mock_system_info = Mock()
        mock_system_info.cpu_temperature = 65.5
        mock_system_info.memory_total = 8589934592
        mock_system_info.memory_used = 4294967296
        mock_system_info.disk_total = 32000000000
        mock_system_info.disk_used = 16000000000
        mock_system_info.load_average = [0.5, 0.3, 0.2]
        mock_system_info.uptime = 3600
        mock_system_info.hostname = "retropie"

        system_management_tools.container.get_system_info_use_case.execute.return_value = mock_system_info

        # Mock port check
        system_management_tools.container.retropie_client.execute_command.return_value = CommandResult(
            command="netstat -tuln | grep ':22 '",
            exit_code=0,
            stdout="tcp   0   0 0.0.0.0:22   0.0.0.0:*   LISTEN",
            stderr="",
            success=True,
            execution_time=0.1,
        )

        # Execute info retrieval
        result = await system_management_tools.handle_tool_call(
            "manage_system",
            {
                "resource": "info",
                "action": "get",
                "check_ports": [22, 80],
            },
        )

        # Verify result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "65.5°C" in result[0].text
        assert "Port Status" in result[0].text

    # Update Resource Tests

    @pytest.mark.asyncio
    async def test_manage_system_update_run_success(
        self, system_management_tools: SystemManagementTools
    ) -> None:
        """Test successful system update."""
        # Mock successful update
        mock_result = CommandResult(
            command="sudo apt-get update && sudo apt-get upgrade -y",
            exit_code=0,
            stdout="System updated successfully",
            stderr="",
            success=True,
            execution_time=120.0,
        )
        system_management_tools.container.update_system_use_case.execute.return_value = mock_result

        # Execute update
        result = await system_management_tools.handle_tool_call(
            "manage_system",
            {
                "resource": "update",
                "action": "run",
                "update_type": "basic",
            },
        )

        # Verify result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "updated successfully" in result[0].text.lower()

    # Error Handling Tests

    @pytest.mark.asyncio
    async def test_invalid_resource_error(
        self, system_management_tools: SystemManagementTools
    ) -> None:
        """Test error handling for invalid resource."""
        result = await system_management_tools.handle_tool_call(
            "manage_system",
            {
                "resource": "invalid_resource",
                "action": "test",
            },
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "invalid resource" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_invalid_action_error(
        self, system_management_tools: SystemManagementTools
    ) -> None:
        """Test error handling for invalid action."""
        result = await system_management_tools.handle_tool_call(
            "manage_system",
            {
                "resource": "service",
                "action": "invalid_action",
            },
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "invalid action" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_missing_required_parameters(
        self, system_management_tools: SystemManagementTools
    ) -> None:
        """Test error handling for missing required parameters."""
        result = await system_management_tools.handle_tool_call(
            "manage_system",
            {
                "resource": "service",
                "action": "start",
                # Missing 'name' parameter
            },
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "required" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_handle_unknown_tool(
        self, system_management_tools: SystemManagementTools
    ) -> None:
        """Test handling of unknown tool calls."""
        result = await system_management_tools.handle_tool_call(
            "unknown_tool",
            {"test": "value"},
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "unknown tool" in result[0].text.lower()

    def test_inheritance_from_base_tool(
        self, system_management_tools: SystemManagementTools
    ) -> None:
        """Test that SystemManagementTools inherits from BaseTool."""
        from retromcp.tools.base import BaseTool

        assert isinstance(system_management_tools, BaseTool)
        assert hasattr(system_management_tools, "format_success")
        assert hasattr(system_management_tools, "format_error")
        assert hasattr(system_management_tools, "format_info")
