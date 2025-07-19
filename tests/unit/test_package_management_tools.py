"""Unit tests for PackageManagementTools implementation."""

from unittest.mock import Mock

import pytest
from mcp.types import TextContent

from retromcp.config import RetroPieConfig
from retromcp.discovery import RetroPiePaths
from retromcp.domain.models import CommandResult
from retromcp.tools.package_management_tools import PackageManagementTools


@pytest.mark.unit
@pytest.mark.tools
@pytest.mark.system_tools
class TestPackageManagementTools:
    """Test cases for PackageManagementTools class."""

    @pytest.fixture
    def mock_container(self, test_config: RetroPieConfig) -> Mock:
        """Provide mocked container."""
        mock = Mock()
        mock.retropie_client = Mock()
        mock.retropie_client.execute_command = Mock()
        mock.config = test_config

        # Mock use cases
        mock.install_packages_use_case = Mock()
        mock.install_packages_use_case.execute = Mock()
        mock.update_system_use_case = Mock()
        mock.update_system_use_case.execute = Mock()

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
    def package_tools(self, mock_container: Mock) -> PackageManagementTools:
        """Provide PackageManagementTools instance with mocked dependencies."""
        return PackageManagementTools(mock_container)

    # Schema and Tool Structure Tests

    def test_get_tools_returns_package_management_tool(
        self, package_tools: PackageManagementTools
    ) -> None:
        """Test that get_tools returns package management tool."""
        tools = package_tools.get_tools()

        assert len(tools) == 1
        tool = tools[0]
        assert tool.name == "manage_package"
        assert "manage system packages" in tool.description.lower()

    def test_package_tool_has_proper_schema(
        self, package_tools: PackageManagementTools
    ) -> None:
        """Test that package tool has proper schema."""
        tools = package_tools.get_tools()
        tool = tools[0]

        schema = tool.inputSchema
        assert "action" in schema["properties"]
        assert "packages" in schema["properties"]
        assert "query" in schema["properties"]
        assert schema["required"] == ["action"]

        # Check action enum values
        action_enum = schema["properties"]["action"]["enum"]
        expected_actions = ["install", "remove", "update", "list", "search", "check"]
        assert set(action_enum) == set(expected_actions)

    # Package Install Tests

    @pytest.mark.asyncio
    async def test_install_packages_success(
        self, package_tools: PackageManagementTools
    ) -> None:
        """Test successful package installation."""
        # Mock successful installation through use case
        package_tools.container.install_packages_use_case.execute.return_value = (
            CommandResult(
                command="sudo apt-get install -y test-package",
                exit_code=0,
                stdout="Successfully installed test-package",
                stderr="",
                success=True,
                execution_time=30.0,
            )
        )

        # Execute package installation
        result = await package_tools.handle_tool_call(
            "manage_package",
            {
                "action": "install",
                "packages": ["test-package"],
            },
        )

        # Verify result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "✅" in result[0].text
        assert "successfully installed test-package" in result[0].text.lower()

        # Verify use case was called
        package_tools.container.install_packages_use_case.execute.assert_called_once_with(
            ["test-package"]
        )

    @pytest.mark.asyncio
    async def test_install_packages_missing_packages_error(
        self, package_tools: PackageManagementTools
    ) -> None:
        """Test install action without packages parameter."""
        result = await package_tools.handle_tool_call(
            "manage_package",
            {
                "action": "install",
                # Missing packages parameter
            },
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "❌" in result[0].text
        assert "package names are required for install action" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_install_packages_empty_packages_error(
        self, package_tools: PackageManagementTools
    ) -> None:
        """Test install action with empty packages list."""
        result = await package_tools.handle_tool_call(
            "manage_package",
            {
                "action": "install",
                "packages": [],
            },
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "❌" in result[0].text
        assert "package names are required for install action" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_install_packages_use_case_failure(
        self, package_tools: PackageManagementTools
    ) -> None:
        """Test install failure from use case."""
        # Mock failed installation
        package_tools.container.install_packages_use_case.execute.return_value = (
            CommandResult(
                command="sudo apt-get install -y non-existent-package",
                exit_code=1,
                stdout="",
                stderr="E: Unable to locate package non-existent-package",
                success=False,
                execution_time=5.0,
            )
        )

        # Execute package installation
        result = await package_tools.handle_tool_call(
            "manage_package",
            {
                "action": "install",
                "packages": ["non-existent-package"],
            },
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "❌" in result[0].text
        assert "failed to install packages" in result[0].text.lower()
        assert "unable to locate package" in result[0].text.lower()

    # Package Remove Tests

    @pytest.mark.asyncio
    async def test_remove_packages_success(
        self, package_tools: PackageManagementTools
    ) -> None:
        """Test successful package removal."""
        # Mock successful removal
        package_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                command="sudo apt-get remove -y test-package",
                exit_code=0,
                stdout="Successfully removed test-package",
                stderr="",
                success=True,
                execution_time=15.0,
            )
        )

        # Execute package removal
        result = await package_tools.handle_tool_call(
            "manage_package",
            {
                "action": "remove",
                "packages": ["test-package"],
            },
        )

        # Verify result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "✅" in result[0].text
        assert "successfully removed test-package" in result[0].text.lower()

        # Verify command was called
        package_tools.container.retropie_client.execute_command.assert_called_once_with(
            "sudo apt-get remove -y test-package"
        )

    @pytest.mark.asyncio
    async def test_remove_packages_missing_packages_error(
        self, package_tools: PackageManagementTools
    ) -> None:
        """Test remove action without packages parameter."""
        result = await package_tools.handle_tool_call(
            "manage_package",
            {
                "action": "remove",
                # Missing packages parameter
            },
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "❌" in result[0].text
        assert "package names are required for remove action" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_remove_packages_empty_packages_error(
        self, package_tools: PackageManagementTools
    ) -> None:
        """Test remove action with empty packages list."""
        result = await package_tools.handle_tool_call(
            "manage_package",
            {
                "action": "remove",
                "packages": [],
            },
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "❌" in result[0].text
        assert "package names are required for remove action" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_remove_packages_command_failure(
        self, package_tools: PackageManagementTools
    ) -> None:
        """Test remove failure from command execution."""
        # Mock failed removal
        package_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                command="sudo apt-get remove -y non-existent-package",
                exit_code=1,
                stdout="",
                stderr="E: Unable to locate package non-existent-package",
                success=False,
                execution_time=2.0,
            )
        )

        # Execute package removal
        result = await package_tools.handle_tool_call(
            "manage_package",
            {
                "action": "remove",
                "packages": ["non-existent-package"],
            },
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "❌" in result[0].text
        assert "failed to remove packages" in result[0].text.lower()

    # Package Update Tests

    @pytest.mark.asyncio
    async def test_update_all_packages_success(
        self, package_tools: PackageManagementTools
    ) -> None:
        """Test successful system-wide package update."""
        # Mock successful system update
        package_tools.container.update_system_use_case.execute.return_value = (
            CommandResult(
                command="sudo apt-get update && sudo apt-get upgrade -y",
                exit_code=0,
                stdout="System updated successfully",
                stderr="",
                success=True,
                execution_time=120.0,
            )
        )

        # Execute system update (no packages specified)
        result = await package_tools.handle_tool_call(
            "manage_package",
            {
                "action": "update",
            },
        )

        # Verify result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "✅" in result[0].text
        assert "system updated successfully" in result[0].text.lower()

        # Verify use case was called
        package_tools.container.update_system_use_case.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_specific_packages_success(
        self, package_tools: PackageManagementTools
    ) -> None:
        """Test successful specific package update."""
        # Mock successful specific package update
        package_tools.container.retropie_client.execute_command.return_value = CommandResult(
            command="sudo apt-get update && sudo apt-get upgrade -y test-package another-package",
            exit_code=0,
            stdout="Updated test-package and another-package successfully",
            stderr="",
            success=True,
            execution_time=60.0,
        )

        # Execute specific package update
        result = await package_tools.handle_tool_call(
            "manage_package",
            {
                "action": "update",
                "packages": ["test-package", "another-package"],
            },
        )

        # Verify result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "✅" in result[0].text
        assert (
            "updated test-package and another-package successfully"
            in result[0].text.lower()
        )

        # Verify command was called
        package_tools.container.retropie_client.execute_command.assert_called_once_with(
            "sudo apt-get update && sudo apt-get upgrade -y test-package another-package"
        )

    @pytest.mark.asyncio
    async def test_update_system_use_case_failure(
        self, package_tools: PackageManagementTools
    ) -> None:
        """Test update failure from system use case."""
        # Mock failed system update
        package_tools.container.update_system_use_case.execute.return_value = (
            CommandResult(
                command="sudo apt-get update && sudo apt-get upgrade -y",
                exit_code=1,
                stdout="",
                stderr="Failed to fetch package lists",
                success=False,
                execution_time=30.0,
            )
        )

        # Execute system update
        result = await package_tools.handle_tool_call(
            "manage_package",
            {
                "action": "update",
            },
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "❌" in result[0].text
        assert "failed to update packages" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_update_specific_packages_command_failure(
        self, package_tools: PackageManagementTools
    ) -> None:
        """Test update failure for specific packages."""
        # Mock failed specific package update
        package_tools.container.retropie_client.execute_command.return_value = CommandResult(
            command="sudo apt-get update && sudo apt-get upgrade -y non-existent-package",
            exit_code=1,
            stdout="",
            stderr="E: Unable to locate package non-existent-package",
            success=False,
            execution_time=10.0,
        )

        # Execute specific package update
        result = await package_tools.handle_tool_call(
            "manage_package",
            {
                "action": "update",
                "packages": ["non-existent-package"],
            },
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "❌" in result[0].text
        assert "failed to update packages" in result[0].text.lower()

    # Package List Tests

    @pytest.mark.asyncio
    async def test_list_packages_success(
        self, package_tools: PackageManagementTools
    ) -> None:
        """Test successful package listing."""
        # Mock successful package listing
        package_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                command="dpkg --get-selections | grep -v deinstall",
                exit_code=0,
                stdout="test-package\tinstall\nanother-package\tinstall\n",
                stderr="",
                success=True,
                execution_time=2.0,
            )
        )

        # Execute package listing
        result = await package_tools.handle_tool_call(
            "manage_package",
            {
                "action": "list",
            },
        )

        # Verify result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "✅" in result[0].text
        assert "test-package" in result[0].text
        assert "another-package" in result[0].text

        # Verify command was called
        package_tools.container.retropie_client.execute_command.assert_called_once_with(
            "dpkg --get-selections | grep -v deinstall"
        )

    @pytest.mark.asyncio
    async def test_list_packages_command_failure(
        self, package_tools: PackageManagementTools
    ) -> None:
        """Test list failure from command execution."""
        # Mock failed package listing
        package_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                command="dpkg --get-selections | grep -v deinstall",
                exit_code=1,
                stdout="",
                stderr="dpkg: error reading package database",
                success=False,
                execution_time=1.0,
            )
        )

        # Execute package listing
        result = await package_tools.handle_tool_call(
            "manage_package",
            {
                "action": "list",
            },
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "❌" in result[0].text
        assert "failed to list packages" in result[0].text.lower()

    # Package Search Tests

    @pytest.mark.asyncio
    async def test_search_packages_success(
        self, package_tools: PackageManagementTools
    ) -> None:
        """Test successful package search."""
        # Mock successful package search
        package_tools.container.retropie_client.execute_command.return_value = CommandResult(
            command="apt-cache search python",
            exit_code=0,
            stdout="python3 - Interactive high-level object-oriented language\npython3-dev - Header files for Python",
            stderr="",
            success=True,
            execution_time=3.0,
        )

        # Execute package search
        result = await package_tools.handle_tool_call(
            "manage_package",
            {
                "action": "search",
                "query": "python",
            },
        )

        # Verify result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "✅" in result[0].text
        assert "python3" in result[0].text.lower()
        assert "header files" in result[0].text.lower()

        # Verify command was called
        package_tools.container.retropie_client.execute_command.assert_called_once_with(
            "apt-cache search python"
        )

    @pytest.mark.asyncio
    async def test_search_packages_missing_query_error(
        self, package_tools: PackageManagementTools
    ) -> None:
        """Test search action without query parameter."""
        result = await package_tools.handle_tool_call(
            "manage_package",
            {
                "action": "search",
                # Missing query parameter
            },
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "❌" in result[0].text
        assert "search query is required for search action" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_search_packages_empty_query_error(
        self, package_tools: PackageManagementTools
    ) -> None:
        """Test search action with empty query."""
        result = await package_tools.handle_tool_call(
            "manage_package",
            {
                "action": "search",
                "query": "",
            },
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "❌" in result[0].text
        assert "search query is required for search action" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_search_packages_command_failure(
        self, package_tools: PackageManagementTools
    ) -> None:
        """Test search failure from command execution."""
        # Mock failed package search
        package_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                command="apt-cache search nonexistent",
                exit_code=1,
                stdout="",
                stderr="Reading package lists failed",
                success=False,
                execution_time=2.0,
            )
        )

        # Execute package search
        result = await package_tools.handle_tool_call(
            "manage_package",
            {
                "action": "search",
                "query": "nonexistent",
            },
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "❌" in result[0].text
        assert "failed to search packages" in result[0].text.lower()

    # Package Check Tests

    @pytest.mark.asyncio
    async def test_check_packages_installed_success(
        self, package_tools: PackageManagementTools
    ) -> None:
        """Test successful package check for installed packages."""
        # Mock package check output showing installed packages
        package_tools.container.retropie_client.execute_command.return_value = CommandResult(
            command="dpkg -l python3 vim 2>/dev/null | grep '^ii'",
            exit_code=0,
            stdout="ii  python3        3.9.2  amd64  Interactive high-level object-oriented language\nii  vim            8.2.2434  amd64  Vi IMproved - enhanced vi editor",
            stderr="",
            success=True,
            execution_time=1.0,
        )

        # Execute package check
        result = await package_tools.handle_tool_call(
            "manage_package",
            {
                "action": "check",
                "packages": ["python3", "vim"],
            },
        )

        # Verify result
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Package Status Check:" in result[0].text
        assert "✅ python3: Installed" in result[0].text
        assert "✅ vim: Installed" in result[0].text

        # Verify command was called
        package_tools.container.retropie_client.execute_command.assert_called_once_with(
            "dpkg -l python3 vim 2>/dev/null | grep '^ii'"
        )

    @pytest.mark.asyncio
    async def test_check_packages_not_found(
        self, package_tools: PackageManagementTools
    ) -> None:
        """Test package check when no packages are found."""
        # Mock package check output with no installed packages
        package_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                command="dpkg -l non-existent-package 2>/dev/null | grep '^ii'",
                exit_code=0,
                stdout="",  # Empty output means no packages found
                stderr="",
                success=True,
                execution_time=0.5,
            )
        )

        # Execute package check
        result = await package_tools.handle_tool_call(
            "manage_package",
            {
                "action": "check",
                "packages": ["non-existent-package"],
            },
        )

        # Verify error message
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "❌" in result[0].text
        assert "no packages found" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_check_packages_missing_packages_error(
        self, package_tools: PackageManagementTools
    ) -> None:
        """Test check action without packages parameter."""
        result = await package_tools.handle_tool_call(
            "manage_package",
            {
                "action": "check",
                # Missing packages parameter
            },
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "❌" in result[0].text
        assert "package names are required for check action" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_check_packages_empty_packages_error(
        self, package_tools: PackageManagementTools
    ) -> None:
        """Test check action with empty packages list."""
        result = await package_tools.handle_tool_call(
            "manage_package",
            {
                "action": "check",
                "packages": [],
            },
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "❌" in result[0].text
        assert "package names are required for check action" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_check_packages_command_failure(
        self, package_tools: PackageManagementTools
    ) -> None:
        """Test check failure from command execution."""
        # Mock failed package check
        package_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                command="dpkg -l test-package 2>/dev/null | grep '^ii'",
                exit_code=1,
                stdout="",
                stderr="dpkg: error accessing package database",
                success=False,
                execution_time=1.0,
            )
        )

        # Execute package check
        result = await package_tools.handle_tool_call(
            "manage_package",
            {
                "action": "check",
                "packages": ["test-package"],
            },
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "❌" in result[0].text
        assert "failed to check packages" in result[0].text.lower()

    # Error Handling Tests

    @pytest.mark.asyncio
    async def test_unknown_tool_error(
        self, package_tools: PackageManagementTools
    ) -> None:
        """Test error handling for unknown tool."""
        result = await package_tools.handle_tool_call(
            "unknown_tool",
            {
                "action": "test",
            },
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "❌" in result[0].text
        assert "unknown tool" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_unknown_action_error(
        self, package_tools: PackageManagementTools
    ) -> None:
        """Test error handling for unknown action."""
        result = await package_tools.handle_tool_call(
            "manage_package",
            {
                "action": "invalid_action",
            },
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "❌" in result[0].text
        assert "unknown action" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_missing_action_error(
        self, package_tools: PackageManagementTools
    ) -> None:
        """Test error handling for missing action parameter."""
        result = await package_tools.handle_tool_call(
            "manage_package",
            {
                # Missing action parameter
            },
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "❌" in result[0].text
        assert "'action' is required" in result[0].text

    @pytest.mark.asyncio
    async def test_general_exception_handling(
        self, package_tools: PackageManagementTools
    ) -> None:
        """Test general exception handling."""
        # Mock an exception during execution
        package_tools.container.retropie_client.execute_command.side_effect = Exception(
            "Network connection failed"
        )

        # Execute an action that would trigger the exception
        result = await package_tools.handle_tool_call(
            "manage_package",
            {
                "action": "list",
            },
        )

        # Verify error
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "❌" in result[0].text
        assert "package management error" in result[0].text.lower()
        assert "network connection failed" in result[0].text.lower()

    # Architecture Compliance Tests

    def test_inheritance_from_base_tool(
        self, package_tools: PackageManagementTools
    ) -> None:
        """Test that PackageManagementTools inherits from BaseTool."""
        from retromcp.tools.base import BaseTool

        assert isinstance(package_tools, BaseTool)
        assert hasattr(package_tools, "format_success")
        assert hasattr(package_tools, "format_error")
        assert hasattr(package_tools, "format_warning")
        assert hasattr(package_tools, "format_info")

    def test_dependency_injection_compliance(
        self, package_tools: PackageManagementTools
    ) -> None:
        """Test that PackageManagementTools follows dependency injection principles."""
        # Verify container is injected
        assert hasattr(package_tools, "container")
        assert hasattr(package_tools, "config")

        # Verify no direct SSH connections or hardcoded dependencies
        assert not hasattr(package_tools, "_ssh_handler")
        assert not hasattr(package_tools, "_direct_client")
