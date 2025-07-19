"""Unit tests for FileManagementTools implementation."""

from unittest.mock import Mock

import pytest
from mcp.types import TextContent

from retromcp.config import RetroPieConfig
from retromcp.discovery import RetroPiePaths
from retromcp.domain.models import CommandResult
from retromcp.tools.file_management_tools import FileManagementTools


@pytest.mark.unit
@pytest.mark.tools
class TestFileManagementTools:
    """Test cases for FileManagementTools class."""

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
    def file_management_tools(self, mock_container: Mock) -> FileManagementTools:
        """Provide FileManagementTools instance with mocked dependencies."""
        return FileManagementTools(mock_container)

    # Schema and Tool Structure Tests

    def test_get_tools_returns_manage_file_tool(
        self, file_management_tools: FileManagementTools
    ) -> None:
        """Test that get_tools returns the manage_file tool."""
        tools = file_management_tools.get_tools()

        assert len(tools) == 1
        tool = tools[0]
        assert tool.name == "manage_file"
        assert "Manage files and directories" in tool.description

    def test_manage_file_tool_has_proper_schema(
        self, file_management_tools: FileManagementTools
    ) -> None:
        """Test that manage_file tool has proper schema."""
        tools = file_management_tools.get_tools()
        tool = tools[0]

        schema = tool.inputSchema
        assert "action" in schema["properties"]
        assert "path" in schema["properties"]
        assert "content" in schema["properties"]
        assert "destination" in schema["properties"]
        assert "mode" in schema["properties"]
        assert "owner" in schema["properties"]
        assert "lines" in schema["properties"]
        assert "create_parents" in schema["properties"]
        assert "type" in schema["properties"]
        assert "url" in schema["properties"]
        assert schema["required"] == ["action", "path"]

        # Check action enum values
        action_enum = schema["properties"]["action"]["enum"]
        expected_actions = [
            "read",
            "write",
            "append",
            "copy",
            "move",
            "delete",
            "create",
            "permissions",
            "download",
        ]
        assert set(action_enum) == set(expected_actions)

    # Tool Routing Tests

    @pytest.mark.asyncio
    async def test_handle_tool_call_routes_to_manage_file(
        self, file_management_tools: FileManagementTools
    ) -> None:
        """Test that handle_tool_call routes manage_file correctly."""
        # Mock successful file read
        file_management_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                command="cat /test/file.txt",
                exit_code=0,
                stdout="test content",
                stderr="",
                success=True,
                execution_time=0.1,
            )
        )

        result = await file_management_tools.handle_tool_call(
            "manage_file", {"action": "read", "path": "/test/file.txt"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "test content" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_tool_call_unknown_tool_error(
        self, file_management_tools: FileManagementTools
    ) -> None:
        """Test error handling for unknown tool."""
        result = await file_management_tools.handle_tool_call(
            "unknown_tool", {"action": "test"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Unknown tool: unknown_tool" in result[0].text
        assert "❌" in result[0].text

    # Parameter Validation Tests

    @pytest.mark.asyncio
    async def test_missing_action_parameter(
        self, file_management_tools: FileManagementTools
    ) -> None:
        """Test error handling for missing action parameter."""
        result = await file_management_tools.handle_tool_call(
            "manage_file", {"path": "/test/file.txt"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Both 'action' and 'path' are required" in result[0].text
        assert "❌" in result[0].text

    @pytest.mark.asyncio
    async def test_missing_path_parameter(
        self, file_management_tools: FileManagementTools
    ) -> None:
        """Test error handling for missing path parameter."""
        result = await file_management_tools.handle_tool_call(
            "manage_file", {"action": "read"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Both 'action' and 'path' are required" in result[0].text
        assert "❌" in result[0].text

    @pytest.mark.asyncio
    async def test_empty_action_parameter(
        self, file_management_tools: FileManagementTools
    ) -> None:
        """Test error handling for empty action parameter."""
        result = await file_management_tools.handle_tool_call(
            "manage_file", {"action": "", "path": "/test/file.txt"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Both 'action' and 'path' are required" in result[0].text
        assert "❌" in result[0].text

    @pytest.mark.asyncio
    async def test_empty_path_parameter(
        self, file_management_tools: FileManagementTools
    ) -> None:
        """Test error handling for empty path parameter."""
        result = await file_management_tools.handle_tool_call(
            "manage_file", {"action": "read", "path": ""}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Both 'action' and 'path' are required" in result[0].text
        assert "❌" in result[0].text

    # File Read Operation Tests

    @pytest.mark.asyncio
    async def test_read_file_success(
        self, file_management_tools: FileManagementTools
    ) -> None:
        """Test successful file read operation."""
        file_management_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                command="cat /test/file.txt",
                exit_code=0,
                stdout="Line 1\nLine 2\nLine 3",
                stderr="",
                success=True,
                execution_time=0.1,
            )
        )

        result = await file_management_tools.handle_tool_call(
            "manage_file", {"action": "read", "path": "/test/file.txt"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "File content:" in result[0].text
        assert "Line 1\nLine 2\nLine 3" in result[0].text
        assert "✅" in result[0].text

        # Verify the correct command was called
        file_management_tools.container.retropie_client.execute_command.assert_called_with(
            "cat /test/file.txt"
        )

    @pytest.mark.asyncio
    async def test_read_file_with_positive_lines(
        self, file_management_tools: FileManagementTools
    ) -> None:
        """Test file read with positive lines parameter (head command)."""
        file_management_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                command="head -n 5 /test/file.txt",
                exit_code=0,
                stdout="Line 1\nLine 2\nLine 3\nLine 4\nLine 5",
                stderr="",
                success=True,
                execution_time=0.1,
            )
        )

        result = await file_management_tools.handle_tool_call(
            "manage_file", {"action": "read", "path": "/test/file.txt", "lines": 5}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "File content:" in result[0].text
        assert "Line 1" in result[0].text

        # Verify the correct head command was called
        file_management_tools.container.retropie_client.execute_command.assert_called_with(
            "head -n 5 /test/file.txt"
        )

    @pytest.mark.asyncio
    async def test_read_file_with_negative_lines(
        self, file_management_tools: FileManagementTools
    ) -> None:
        """Test file read with negative lines parameter (tail command)."""
        file_management_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                command="tail -n 3 /test/file.txt",
                exit_code=0,
                stdout="Line 8\nLine 9\nLine 10",
                stderr="",
                success=True,
                execution_time=0.1,
            )
        )

        result = await file_management_tools.handle_tool_call(
            "manage_file", {"action": "read", "path": "/test/file.txt", "lines": -3}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "File content:" in result[0].text
        assert "Line 8" in result[0].text

        # Verify the correct tail command was called
        file_management_tools.container.retropie_client.execute_command.assert_called_with(
            "tail -n 3 /test/file.txt"
        )

    @pytest.mark.asyncio
    async def test_read_file_failure(
        self, file_management_tools: FileManagementTools
    ) -> None:
        """Test file read failure."""
        file_management_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                command="cat /nonexistent/file.txt",
                exit_code=1,
                stdout="",
                stderr="cat: /nonexistent/file.txt: No such file or directory",
                success=False,
                execution_time=0.1,
            )
        )

        result = await file_management_tools.handle_tool_call(
            "manage_file", {"action": "read", "path": "/nonexistent/file.txt"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Failed to read file:" in result[0].text
        assert "No such file or directory" in result[0].text
        assert "❌" in result[0].text

    # File Write Operation Tests

    @pytest.mark.asyncio
    async def test_write_file_success(
        self, file_management_tools: FileManagementTools
    ) -> None:
        """Test successful file write operation."""
        file_management_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                command="echo 'test content' > /test/file.txt",
                exit_code=0,
                stdout="",
                stderr="",
                success=True,
                execution_time=0.1,
            )
        )

        result = await file_management_tools.handle_tool_call(
            "manage_file",
            {"action": "write", "path": "/test/file.txt", "content": "test content"},
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "File written successfully to /test/file.txt" in result[0].text
        assert "✅" in result[0].text

        # Verify the correct command was called
        file_management_tools.container.retropie_client.execute_command.assert_called_with(
            "echo 'test content' > /test/file.txt"
        )

    @pytest.mark.asyncio
    async def test_write_file_with_create_parents(
        self, file_management_tools: FileManagementTools
    ) -> None:
        """Test file write with parent directory creation."""

        # Mock both parent creation and file write commands
        def mock_execute_command(cmd: str) -> CommandResult:
            return CommandResult(
                command=cmd,
                exit_code=0,
                stdout="",
                stderr="",
                success=True,
                execution_time=0.1,
            )

        file_management_tools.container.retropie_client.execute_command.side_effect = (
            mock_execute_command
        )

        result = await file_management_tools.handle_tool_call(
            "manage_file",
            {
                "action": "write",
                "path": "/test/new/dir/file.txt",
                "content": "test content",
                "create_parents": True,
            },
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "File written successfully to /test/new/dir/file.txt" in result[0].text
        assert "✅" in result[0].text

        # Verify both commands were called
        calls = file_management_tools.container.retropie_client.execute_command.call_args_list
        assert len(calls) == 2
        assert "mkdir -p $(dirname /test/new/dir/file.txt)" in calls[0][0][0]
        assert "echo 'test content' > /test/new/dir/file.txt" in calls[1][0][0]

    @pytest.mark.asyncio
    async def test_write_file_missing_content(
        self, file_management_tools: FileManagementTools
    ) -> None:
        """Test write file error when content is missing."""
        result = await file_management_tools.handle_tool_call(
            "manage_file", {"action": "write", "path": "/test/file.txt"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Content is required for write action" in result[0].text
        assert "❌" in result[0].text

    @pytest.mark.asyncio
    async def test_write_file_empty_content(
        self, file_management_tools: FileManagementTools
    ) -> None:
        """Test write file error when content is empty."""
        result = await file_management_tools.handle_tool_call(
            "manage_file", {"action": "write", "path": "/test/file.txt", "content": ""}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Content is required for write action" in result[0].text
        assert "❌" in result[0].text

    @pytest.mark.asyncio
    async def test_write_file_failure(
        self, file_management_tools: FileManagementTools
    ) -> None:
        """Test file write failure."""
        file_management_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                command="echo 'test content' > /readonly/file.txt",
                exit_code=1,
                stdout="",
                stderr="Permission denied",
                success=False,
                execution_time=0.1,
            )
        )

        result = await file_management_tools.handle_tool_call(
            "manage_file",
            {
                "action": "write",
                "path": "/readonly/file.txt",
                "content": "test content",
            },
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Failed to write file:" in result[0].text
        assert "Permission denied" in result[0].text
        assert "❌" in result[0].text

    # File Append Operation Tests

    @pytest.mark.asyncio
    async def test_append_file_success(
        self, file_management_tools: FileManagementTools
    ) -> None:
        """Test successful file append operation."""
        file_management_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                command="echo 'appended content' >> /test/file.txt",
                exit_code=0,
                stdout="",
                stderr="",
                success=True,
                execution_time=0.1,
            )
        )

        result = await file_management_tools.handle_tool_call(
            "manage_file",
            {
                "action": "append",
                "path": "/test/file.txt",
                "content": "appended content",
            },
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Content appended to /test/file.txt" in result[0].text
        assert "✅" in result[0].text

        file_management_tools.container.retropie_client.execute_command.assert_called_with(
            "echo 'appended content' >> /test/file.txt"
        )

    @pytest.mark.asyncio
    async def test_append_file_missing_content(
        self, file_management_tools: FileManagementTools
    ) -> None:
        """Test append file error when content is missing."""
        result = await file_management_tools.handle_tool_call(
            "manage_file", {"action": "append", "path": "/test/file.txt"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Content is required for append action" in result[0].text
        assert "❌" in result[0].text

    @pytest.mark.asyncio
    async def test_append_file_empty_content(
        self, file_management_tools: FileManagementTools
    ) -> None:
        """Test append file error when content is empty."""
        result = await file_management_tools.handle_tool_call(
            "manage_file", {"action": "append", "path": "/test/file.txt", "content": ""}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Content is required for append action" in result[0].text
        assert "❌" in result[0].text

    @pytest.mark.asyncio
    async def test_append_file_failure(
        self, file_management_tools: FileManagementTools
    ) -> None:
        """Test file append failure."""
        file_management_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                command="echo 'appended content' >> /readonly/file.txt",
                exit_code=1,
                stdout="",
                stderr="Permission denied",
                success=False,
                execution_time=0.1,
            )
        )

        result = await file_management_tools.handle_tool_call(
            "manage_file",
            {
                "action": "append",
                "path": "/readonly/file.txt",
                "content": "appended content",
            },
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Failed to append to file:" in result[0].text
        assert "Permission denied" in result[0].text
        assert "❌" in result[0].text

    # File Copy Operation Tests

    @pytest.mark.asyncio
    async def test_copy_file_success(
        self, file_management_tools: FileManagementTools
    ) -> None:
        """Test successful file copy operation."""
        file_management_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                command="cp /source/file.txt /dest/file.txt",
                exit_code=0,
                stdout="",
                stderr="",
                success=True,
                execution_time=0.1,
            )
        )

        result = await file_management_tools.handle_tool_call(
            "manage_file",
            {
                "action": "copy",
                "path": "/source/file.txt",
                "destination": "/dest/file.txt",
            },
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "File copied to /dest/file.txt" in result[0].text
        assert "✅" in result[0].text

        file_management_tools.container.retropie_client.execute_command.assert_called_with(
            "cp /source/file.txt /dest/file.txt"
        )

    @pytest.mark.asyncio
    async def test_copy_file_missing_destination(
        self, file_management_tools: FileManagementTools
    ) -> None:
        """Test copy file error when destination is missing."""
        result = await file_management_tools.handle_tool_call(
            "manage_file", {"action": "copy", "path": "/source/file.txt"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Destination is required for copy action" in result[0].text
        assert "❌" in result[0].text

    @pytest.mark.asyncio
    async def test_copy_file_empty_destination(
        self, file_management_tools: FileManagementTools
    ) -> None:
        """Test copy file error when destination is empty."""
        result = await file_management_tools.handle_tool_call(
            "manage_file",
            {"action": "copy", "path": "/source/file.txt", "destination": ""},
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Destination is required for copy action" in result[0].text
        assert "❌" in result[0].text

    @pytest.mark.asyncio
    async def test_copy_file_failure(
        self, file_management_tools: FileManagementTools
    ) -> None:
        """Test file copy failure."""
        file_management_tools.container.retropie_client.execute_command.return_value = CommandResult(
            command="cp /nonexistent/file.txt /dest/file.txt",
            exit_code=1,
            stdout="",
            stderr="cp: cannot stat '/nonexistent/file.txt': No such file or directory",
            success=False,
            execution_time=0.1,
        )

        result = await file_management_tools.handle_tool_call(
            "manage_file",
            {
                "action": "copy",
                "path": "/nonexistent/file.txt",
                "destination": "/dest/file.txt",
            },
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Failed to copy file:" in result[0].text
        assert "No such file or directory" in result[0].text
        assert "❌" in result[0].text

    # File Move Operation Tests

    @pytest.mark.asyncio
    async def test_move_file_success(
        self, file_management_tools: FileManagementTools
    ) -> None:
        """Test successful file move operation."""
        file_management_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                command="mv /source/file.txt /dest/file.txt",
                exit_code=0,
                stdout="",
                stderr="",
                success=True,
                execution_time=0.1,
            )
        )

        result = await file_management_tools.handle_tool_call(
            "manage_file",
            {
                "action": "move",
                "path": "/source/file.txt",
                "destination": "/dest/file.txt",
            },
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "File moved to /dest/file.txt" in result[0].text
        assert "✅" in result[0].text

        file_management_tools.container.retropie_client.execute_command.assert_called_with(
            "mv /source/file.txt /dest/file.txt"
        )

    @pytest.mark.asyncio
    async def test_move_file_missing_destination(
        self, file_management_tools: FileManagementTools
    ) -> None:
        """Test move file error when destination is missing."""
        result = await file_management_tools.handle_tool_call(
            "manage_file", {"action": "move", "path": "/source/file.txt"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Destination is required for move action" in result[0].text
        assert "❌" in result[0].text

    @pytest.mark.asyncio
    async def test_move_file_empty_destination(
        self, file_management_tools: FileManagementTools
    ) -> None:
        """Test move file error when destination is empty."""
        result = await file_management_tools.handle_tool_call(
            "manage_file",
            {"action": "move", "path": "/source/file.txt", "destination": ""},
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Destination is required for move action" in result[0].text
        assert "❌" in result[0].text

    @pytest.mark.asyncio
    async def test_move_file_failure(
        self, file_management_tools: FileManagementTools
    ) -> None:
        """Test file move failure."""
        file_management_tools.container.retropie_client.execute_command.return_value = CommandResult(
            command="mv /nonexistent/file.txt /dest/file.txt",
            exit_code=1,
            stdout="",
            stderr="mv: cannot stat '/nonexistent/file.txt': No such file or directory",
            success=False,
            execution_time=0.1,
        )

        result = await file_management_tools.handle_tool_call(
            "manage_file",
            {
                "action": "move",
                "path": "/nonexistent/file.txt",
                "destination": "/dest/file.txt",
            },
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Failed to move file:" in result[0].text
        assert "No such file or directory" in result[0].text
        assert "❌" in result[0].text

    # File Delete Operation Tests

    @pytest.mark.asyncio
    async def test_delete_file_success(
        self, file_management_tools: FileManagementTools
    ) -> None:
        """Test successful file delete operation."""
        file_management_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                command="rm -f /test/file.txt",
                exit_code=0,
                stdout="",
                stderr="",
                success=True,
                execution_time=0.1,
            )
        )

        result = await file_management_tools.handle_tool_call(
            "manage_file", {"action": "delete", "path": "/test/file.txt"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "File deleted: /test/file.txt" in result[0].text
        assert "✅" in result[0].text

        file_management_tools.container.retropie_client.execute_command.assert_called_with(
            "rm -f /test/file.txt"
        )

    @pytest.mark.asyncio
    async def test_delete_file_failure(
        self, file_management_tools: FileManagementTools
    ) -> None:
        """Test file delete failure."""
        file_management_tools.container.retropie_client.execute_command.return_value = CommandResult(
            command="rm -f /protected/file.txt",
            exit_code=1,
            stdout="",
            stderr="rm: cannot remove '/protected/file.txt': Operation not permitted",
            success=False,
            execution_time=0.1,
        )

        result = await file_management_tools.handle_tool_call(
            "manage_file", {"action": "delete", "path": "/protected/file.txt"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Failed to delete file:" in result[0].text
        assert "Operation not permitted" in result[0].text
        assert "❌" in result[0].text

    # File Create Operation Tests

    @pytest.mark.asyncio
    async def test_create_directory_success(
        self, file_management_tools: FileManagementTools
    ) -> None:
        """Test successful directory creation."""
        file_management_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                command="mkdir /test/newdir",
                exit_code=0,
                stdout="",
                stderr="",
                success=True,
                execution_time=0.1,
            )
        )

        result = await file_management_tools.handle_tool_call(
            "manage_file",
            {"action": "create", "path": "/test/newdir", "type": "directory"},
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Directory created: /test/newdir" in result[0].text
        assert "✅" in result[0].text

        file_management_tools.container.retropie_client.execute_command.assert_called_with(
            "mkdir /test/newdir"
        )

    @pytest.mark.asyncio
    async def test_create_directory_with_parents(
        self, file_management_tools: FileManagementTools
    ) -> None:
        """Test directory creation with parent directories."""
        file_management_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                command="mkdir -p /test/new/deep/dir",
                exit_code=0,
                stdout="",
                stderr="",
                success=True,
                execution_time=0.1,
            )
        )

        result = await file_management_tools.handle_tool_call(
            "manage_file",
            {
                "action": "create",
                "path": "/test/new/deep/dir",
                "type": "directory",
                "create_parents": True,
            },
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Directory created: /test/new/deep/dir" in result[0].text
        assert "✅" in result[0].text

        file_management_tools.container.retropie_client.execute_command.assert_called_with(
            "mkdir -p /test/new/deep/dir"
        )

    @pytest.mark.asyncio
    async def test_create_directory_failure(
        self, file_management_tools: FileManagementTools
    ) -> None:
        """Test directory creation failure."""
        file_management_tools.container.retropie_client.execute_command.return_value = CommandResult(
            command="mkdir /readonly/newdir",
            exit_code=1,
            stdout="",
            stderr="mkdir: cannot create directory '/readonly/newdir': Permission denied",
            success=False,
            execution_time=0.1,
        )

        result = await file_management_tools.handle_tool_call(
            "manage_file",
            {"action": "create", "path": "/readonly/newdir", "type": "directory"},
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Failed to create directory:" in result[0].text
        assert "Permission denied" in result[0].text
        assert "❌" in result[0].text

    @pytest.mark.asyncio
    async def test_create_file_success(
        self, file_management_tools: FileManagementTools
    ) -> None:
        """Test successful file creation."""
        file_management_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                command="touch /test/newfile.txt",
                exit_code=0,
                stdout="",
                stderr="",
                success=True,
                execution_time=0.1,
            )
        )

        result = await file_management_tools.handle_tool_call(
            "manage_file",
            {"action": "create", "path": "/test/newfile.txt", "type": "file"},
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "File created: /test/newfile.txt" in result[0].text
        assert "✅" in result[0].text

        file_management_tools.container.retropie_client.execute_command.assert_called_with(
            "touch /test/newfile.txt"
        )

    @pytest.mark.asyncio
    async def test_create_file_with_content(
        self, file_management_tools: FileManagementTools
    ) -> None:
        """Test file creation with content."""
        file_management_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                command="echo 'initial content' > /test/newfile.txt",
                exit_code=0,
                stdout="",
                stderr="",
                success=True,
                execution_time=0.1,
            )
        )

        result = await file_management_tools.handle_tool_call(
            "manage_file",
            {
                "action": "create",
                "path": "/test/newfile.txt",
                "type": "file",
                "content": "initial content",
            },
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "File created: /test/newfile.txt" in result[0].text
        assert "✅" in result[0].text

        file_management_tools.container.retropie_client.execute_command.assert_called_with(
            "echo 'initial content' > /test/newfile.txt"
        )

    @pytest.mark.asyncio
    async def test_create_file_with_parents(
        self, file_management_tools: FileManagementTools
    ) -> None:
        """Test file creation with parent directory creation."""

        def mock_execute_command(cmd: str) -> CommandResult:
            return CommandResult(
                command=cmd,
                exit_code=0,
                stdout="",
                stderr="",
                success=True,
                execution_time=0.1,
            )

        file_management_tools.container.retropie_client.execute_command.side_effect = (
            mock_execute_command
        )

        result = await file_management_tools.handle_tool_call(
            "manage_file",
            {
                "action": "create",
                "path": "/test/new/deep/file.txt",
                "type": "file",
                "create_parents": True,
            },
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "File created: /test/new/deep/file.txt" in result[0].text
        assert "✅" in result[0].text

        calls = file_management_tools.container.retropie_client.execute_command.call_args_list
        assert len(calls) == 2
        assert "mkdir -p $(dirname /test/new/deep/file.txt)" in calls[0][0][0]
        assert "touch /test/new/deep/file.txt" in calls[1][0][0]

    @pytest.mark.asyncio
    async def test_create_file_default_type(
        self, file_management_tools: FileManagementTools
    ) -> None:
        """Test file creation with default type (file)."""
        file_management_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                command="touch /test/defaultfile.txt",
                exit_code=0,
                stdout="",
                stderr="",
                success=True,
                execution_time=0.1,
            )
        )

        result = await file_management_tools.handle_tool_call(
            "manage_file", {"action": "create", "path": "/test/defaultfile.txt"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "File created: /test/defaultfile.txt" in result[0].text
        assert "✅" in result[0].text

        file_management_tools.container.retropie_client.execute_command.assert_called_with(
            "touch /test/defaultfile.txt"
        )

    @pytest.mark.asyncio
    async def test_create_file_failure(
        self, file_management_tools: FileManagementTools
    ) -> None:
        """Test file creation failure."""
        file_management_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                command="touch /readonly/newfile.txt",
                exit_code=1,
                stdout="",
                stderr="touch: cannot touch '/readonly/newfile.txt': Permission denied",
                success=False,
                execution_time=0.1,
            )
        )

        result = await file_management_tools.handle_tool_call(
            "manage_file",
            {"action": "create", "path": "/readonly/newfile.txt", "type": "file"},
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Failed to create file:" in result[0].text
        assert "Permission denied" in result[0].text
        assert "❌" in result[0].text

    # File Permissions Operation Tests

    @pytest.mark.asyncio
    async def test_permissions_mode_only_success(
        self, file_management_tools: FileManagementTools
    ) -> None:
        """Test successful permissions change with mode only."""
        file_management_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                command="chmod 755 /test/file.txt",
                exit_code=0,
                stdout="",
                stderr="",
                success=True,
                execution_time=0.1,
            )
        )

        result = await file_management_tools.handle_tool_call(
            "manage_file",
            {"action": "permissions", "path": "/test/file.txt", "mode": "755"},
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Permissions updated for /test/file.txt" in result[0].text
        assert "✅" in result[0].text

        file_management_tools.container.retropie_client.execute_command.assert_called_with(
            "chmod 755 /test/file.txt"
        )

    @pytest.mark.asyncio
    async def test_permissions_owner_only_success(
        self, file_management_tools: FileManagementTools
    ) -> None:
        """Test successful permissions change with owner only."""
        file_management_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                command="chown user:group /test/file.txt",
                exit_code=0,
                stdout="",
                stderr="",
                success=True,
                execution_time=0.1,
            )
        )

        result = await file_management_tools.handle_tool_call(
            "manage_file",
            {"action": "permissions", "path": "/test/file.txt", "owner": "user:group"},
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Permissions updated for /test/file.txt" in result[0].text
        assert "✅" in result[0].text

        file_management_tools.container.retropie_client.execute_command.assert_called_with(
            "chown user:group /test/file.txt"
        )

    @pytest.mark.asyncio
    async def test_permissions_mode_and_owner_success(
        self, file_management_tools: FileManagementTools
    ) -> None:
        """Test successful permissions change with both mode and owner."""

        def mock_execute_command(cmd: str) -> CommandResult:
            return CommandResult(
                command=cmd,
                exit_code=0,
                stdout="",
                stderr="",
                success=True,
                execution_time=0.1,
            )

        file_management_tools.container.retropie_client.execute_command.side_effect = (
            mock_execute_command
        )

        result = await file_management_tools.handle_tool_call(
            "manage_file",
            {
                "action": "permissions",
                "path": "/test/file.txt",
                "mode": "755",
                "owner": "user:group",
            },
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Permissions updated for /test/file.txt" in result[0].text
        assert "✅" in result[0].text

        calls = file_management_tools.container.retropie_client.execute_command.call_args_list
        assert len(calls) == 2
        assert "chmod 755 /test/file.txt" in calls[0][0][0]
        assert "chown user:group /test/file.txt" in calls[1][0][0]

    @pytest.mark.asyncio
    async def test_permissions_missing_mode_and_owner(
        self, file_management_tools: FileManagementTools
    ) -> None:
        """Test permissions error when both mode and owner are missing."""
        result = await file_management_tools.handle_tool_call(
            "manage_file", {"action": "permissions", "path": "/test/file.txt"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Either mode or owner must be specified" in result[0].text
        assert "❌" in result[0].text

    @pytest.mark.asyncio
    async def test_permissions_empty_mode_and_owner(
        self, file_management_tools: FileManagementTools
    ) -> None:
        """Test permissions error when both mode and owner are empty."""
        result = await file_management_tools.handle_tool_call(
            "manage_file",
            {
                "action": "permissions",
                "path": "/test/file.txt",
                "mode": "",
                "owner": "",
            },
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Either mode or owner must be specified" in result[0].text
        assert "❌" in result[0].text

    @pytest.mark.asyncio
    async def test_permissions_chmod_failure(
        self, file_management_tools: FileManagementTools
    ) -> None:
        """Test permissions failure during chmod."""
        file_management_tools.container.retropie_client.execute_command.return_value = CommandResult(
            command="chmod 755 /protected/file.txt",
            exit_code=1,
            stdout="",
            stderr="chmod: changing permissions of '/protected/file.txt': Operation not permitted",
            success=False,
            execution_time=0.1,
        )

        result = await file_management_tools.handle_tool_call(
            "manage_file",
            {"action": "permissions", "path": "/protected/file.txt", "mode": "755"},
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Failed to set permissions:" in result[0].text
        assert "Operation not permitted" in result[0].text
        assert "❌" in result[0].text

    @pytest.mark.asyncio
    async def test_permissions_chown_failure(
        self, file_management_tools: FileManagementTools
    ) -> None:
        """Test permissions failure during chown."""
        file_management_tools.container.retropie_client.execute_command.return_value = CommandResult(
            command="chown user:group /protected/file.txt",
            exit_code=1,
            stdout="",
            stderr="chown: changing ownership of '/protected/file.txt': Operation not permitted",
            success=False,
            execution_time=0.1,
        )

        result = await file_management_tools.handle_tool_call(
            "manage_file",
            {
                "action": "permissions",
                "path": "/protected/file.txt",
                "owner": "user:group",
            },
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Failed to set permissions:" in result[0].text
        assert "Operation not permitted" in result[0].text
        assert "❌" in result[0].text

    # File Download Operation Tests

    @pytest.mark.asyncio
    async def test_download_file_success(
        self, file_management_tools: FileManagementTools
    ) -> None:
        """Test successful file download operation."""
        file_management_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                command="wget -O /test/downloaded.txt https://example.com/file.txt",
                exit_code=0,
                stdout="",
                stderr="",
                success=True,
                execution_time=2.0,
            )
        )

        result = await file_management_tools.handle_tool_call(
            "manage_file",
            {
                "action": "download",
                "path": "/test/downloaded.txt",
                "url": "https://example.com/file.txt",
            },
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "File downloaded to /test/downloaded.txt" in result[0].text
        assert "✅" in result[0].text

        file_management_tools.container.retropie_client.execute_command.assert_called_with(
            "wget -O /test/downloaded.txt https://example.com/file.txt"
        )

    @pytest.mark.asyncio
    async def test_download_file_missing_url(
        self, file_management_tools: FileManagementTools
    ) -> None:
        """Test download file error when URL is missing."""
        result = await file_management_tools.handle_tool_call(
            "manage_file", {"action": "download", "path": "/test/downloaded.txt"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "URL is required for download action" in result[0].text
        assert "❌" in result[0].text

    @pytest.mark.asyncio
    async def test_download_file_empty_url(
        self, file_management_tools: FileManagementTools
    ) -> None:
        """Test download file error when URL is empty."""
        result = await file_management_tools.handle_tool_call(
            "manage_file",
            {"action": "download", "path": "/test/downloaded.txt", "url": ""},
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "URL is required for download action" in result[0].text
        assert "❌" in result[0].text

    @pytest.mark.asyncio
    async def test_download_file_failure(
        self, file_management_tools: FileManagementTools
    ) -> None:
        """Test file download failure."""
        file_management_tools.container.retropie_client.execute_command.return_value = CommandResult(
            command="wget -O /test/downloaded.txt https://nonexistent.example.com/file.txt",
            exit_code=1,
            stdout="",
            stderr="wget: unable to resolve host address 'nonexistent.example.com'",
            success=False,
            execution_time=5.0,
        )

        result = await file_management_tools.handle_tool_call(
            "manage_file",
            {
                "action": "download",
                "path": "/test/downloaded.txt",
                "url": "https://nonexistent.example.com/file.txt",
            },
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Failed to download file:" in result[0].text
        assert "unable to resolve host address" in result[0].text
        assert "❌" in result[0].text

    # Unknown Action and Exception Handling Tests

    @pytest.mark.asyncio
    async def test_unknown_action_error(
        self, file_management_tools: FileManagementTools
    ) -> None:
        """Test error handling for unknown action."""
        result = await file_management_tools.handle_tool_call(
            "manage_file", {"action": "unknown_action", "path": "/test/file.txt"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Unknown action: unknown_action" in result[0].text
        assert "❌" in result[0].text

    @pytest.mark.asyncio
    async def test_exception_handling(
        self, file_management_tools: FileManagementTools
    ) -> None:
        """Test exception handling in file management operations."""
        # Mock an exception during command execution
        file_management_tools.container.retropie_client.execute_command.side_effect = (
            Exception("Test exception")
        )

        result = await file_management_tools.handle_tool_call(
            "manage_file", {"action": "read", "path": "/test/file.txt"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "File management error: Test exception" in result[0].text
        assert "❌" in result[0].text

    # Test inheritance and tool methods

    def test_inheritance_from_base_tool(
        self, file_management_tools: FileManagementTools
    ) -> None:
        """Test that FileManagementTools inherits from BaseTool."""
        from retromcp.tools.base import BaseTool

        assert isinstance(file_management_tools, BaseTool)
        assert hasattr(file_management_tools, "format_success")
        assert hasattr(file_management_tools, "format_error")
        assert hasattr(file_management_tools, "format_info")
