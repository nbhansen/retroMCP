"""Unit tests for FileManagementTools edge cases and bug reproduction."""

import shlex
from unittest.mock import Mock

import pytest
from mcp.types import TextContent

from retromcp.config import RetroPieConfig
from retromcp.discovery import RetroPiePaths
from retromcp.domain.models import CommandResult
from retromcp.tools.file_management_tools import FileManagementTools


@pytest.mark.unit
@pytest.mark.tools
class TestFileManagementEdgeCases:
    """Test cases for FileManagementTools edge cases that reproduce real-world bugs."""

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
            password="test_password",  # noqa: S106
            port=22,
            paths=paths,
        )

    @pytest.fixture
    def file_management_tools(self, mock_container: Mock) -> FileManagementTools:
        """Provide FileManagementTools instance with mocked dependencies."""
        return FileManagementTools(mock_container)

    # Bug Reproduction Tests

    @pytest.mark.asyncio
    async def test_write_file_with_multiline_content(
        self, file_management_tools: FileManagementTools
    ) -> None:
        """Test that multiline content is handled correctly."""
        multiline_content = """#!/bin/bash
# Cron job script
echo "Starting backup at $(date)"
rsync -av /source/ /destination/
echo "Backup completed at $(date)"
"""
        
        # This test exposes the bug: echo with single quotes doesn't handle multiline
        file_management_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                command=f"echo '{multiline_content}' > /test/script.sh",
                exit_code=0,
                stdout="",
                stderr="",
                success=True,
                execution_time=0.1,
            )
        )

        result = await file_management_tools.handle_tool_call(
            "manage_file",
            {"action": "write", "path": "/test/script.sh", "content": multiline_content},
        )

        # Check the command that was called
        called_command = file_management_tools.container.retropie_client.execute_command.call_args[0][0]
        
        # The bug: echo with single quotes will fail with multiline content
        # This assertion documents the current broken behavior
        assert "echo '" in called_command
        # This command will actually FAIL in real SSH because newlines break echo
        assert "\n" in called_command  # Newlines in the middle of echo command!

    @pytest.mark.asyncio
    async def test_write_file_with_special_characters(
        self, file_management_tools: FileManagementTools
    ) -> None:
        """Test that special characters are handled correctly."""
        content_with_specials = "Path: /home/user's files & \"configs\"\n$HOME=$(pwd)\nTest `command`"
        
        file_management_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                command=f"echo '{content_with_specials}' > /test/special.txt",
                exit_code=0,
                stdout="",
                stderr="",
                success=True,
                execution_time=0.1,
            )
        )

        result = await file_management_tools.handle_tool_call(
            "manage_file",
            {"action": "write", "path": "/test/special.txt", "content": content_with_specials},
        )

        called_command = file_management_tools.container.retropie_client.execute_command.call_args[0][0]
        
        # The bug: single quotes in content will break the echo command
        # Also, backticks and dollar signs can cause command substitution
        assert "echo '" in called_command
        assert "user's" in called_command  # This will break the quoting

    @pytest.mark.asyncio
    async def test_write_file_with_escape_sequences(
        self, file_management_tools: FileManagementTools
    ) -> None:
        """Test that escape sequences are handled correctly."""
        content_with_escapes = "Line 1\\nLine 2\\tTabbed\\rReturn\\\\Backslash"
        
        file_management_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                command=f"echo '{content_with_escapes}' > /test/escapes.txt",
                exit_code=0,
                stdout="",
                stderr="",
                success=True,
                execution_time=0.1,
            )
        )

        result = await file_management_tools.handle_tool_call(
            "manage_file",
            {"action": "write", "path": "/test/escapes.txt", "content": content_with_escapes},
        )

        called_command = file_management_tools.container.retropie_client.execute_command.call_args[0][0]
        
        # The bug: echo without -e won't interpret escape sequences correctly
        assert "echo '" in called_command
        assert "\\n" in called_command  # Will be written literally, not as newline

    @pytest.mark.asyncio
    async def test_write_empty_file_should_create_empty_file(
        self, file_management_tools: FileManagementTools
    ) -> None:
        """Test that writing empty content still creates a file."""
        # Current implementation rejects empty content, but this might be a valid use case
        result = await file_management_tools.handle_tool_call(
            "manage_file",
            {"action": "write", "path": "/test/empty.txt", "content": ""},
        )

        # Current behavior: rejects empty content
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Content is required for write action" in result[0].text
        assert "❌" in result[0].text

    @pytest.mark.asyncio
    async def test_write_file_with_shell_redirection_in_content(
        self, file_management_tools: FileManagementTools
    ) -> None:
        """Test that shell redirection operators in content don't cause issues."""
        content_with_redirects = "echo 'test' > output.txt && cat < input.txt | grep pattern >> results.txt"
        
        file_management_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                command=f"echo '{content_with_redirects}' > /test/commands.sh",
                exit_code=0,
                stdout="",
                stderr="",
                success=True,
                execution_time=0.1,
            )
        )

        result = await file_management_tools.handle_tool_call(
            "manage_file",
            {"action": "write", "path": "/test/commands.sh", "content": content_with_redirects},
        )

        called_command = file_management_tools.container.retropie_client.execute_command.call_args[0][0]
        
        # The bug: nested redirections might confuse the shell parser
        assert "echo '" in called_command
        assert "> output.txt" in called_command  # Nested redirection in content

    @pytest.mark.asyncio
    async def test_write_large_file_content(
        self, file_management_tools: FileManagementTools
    ) -> None:
        """Test that large file content is handled correctly."""
        # Create content that might exceed command line limits
        large_content = "x" * 100000  # 100KB of content
        
        file_management_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                command=f"echo '{large_content[:50]}...' > /test/large.txt",  # Truncated for display
                exit_code=0,
                stdout="",
                stderr="",
                success=True,
                execution_time=0.5,
            )
        )

        result = await file_management_tools.handle_tool_call(
            "manage_file",
            {"action": "write", "path": "/test/large.txt", "content": large_content},
        )

        called_command = file_management_tools.container.retropie_client.execute_command.call_args[0][0]
        
        # The bug: echo command might exceed shell command line limits (typically 128KB)
        assert "echo '" in called_command
        assert len(called_command) > 100000  # Command is huge

    @pytest.mark.asyncio
    async def test_write_file_with_binary_like_content(
        self, file_management_tools: FileManagementTools
    ) -> None:
        """Test that binary-like content (base64, etc.) is handled correctly."""
        binary_like_content = "SGVsbG8gV29ybGQhIFRoaXMgaXMgYSBiYXNlNjQgZW5jb2RlZCBzdHJpbmcu"
        
        file_management_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                command=f"echo '{binary_like_content}' > /test/binary.b64",
                exit_code=0,
                stdout="",
                stderr="",
                success=True,
                execution_time=0.1,
            )
        )

        result = await file_management_tools.handle_tool_call(
            "manage_file",
            {"action": "write", "path": "/test/binary.b64", "content": binary_like_content},
        )

        # This should work but might have issues with very long base64 strings
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "✅" in result[0].text

    @pytest.mark.asyncio
    async def test_create_file_with_content_containing_quotes(
        self, file_management_tools: FileManagementTools
    ) -> None:
        """Test file creation with content containing various quote types."""
        content_with_quotes = '''He said "Hello" and she replied 'Hi there!'. It's complicated.'''
        
        file_management_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                command=f"echo '{content_with_quotes}' > /test/quotes.txt",
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
                "path": "/test/quotes.txt",
                "type": "file",
                "content": content_with_quotes,
            },
        )

        called_command = file_management_tools.container.retropie_client.execute_command.call_args[0][0]
        
        # The bug: mixing quotes will break the echo command
        assert "echo '" in called_command
        # The single quote in "It's" will terminate the echo string prematurely
        assert "'Hi there!'" in called_command  # Nested single quotes will break

    @pytest.mark.asyncio
    async def test_append_file_with_special_content(
        self, file_management_tools: FileManagementTools
    ) -> None:
        """Test that append operation has same issues as write."""
        problematic_content = "New line with 'quotes' and $variables"
        
        file_management_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                command=f"echo '{problematic_content}' >> /test/append.txt",
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
                "path": "/test/append.txt",
                "content": problematic_content,
            },
        )

        called_command = file_management_tools.container.retropie_client.execute_command.call_args[0][0]
        
        # The bug affects append too since it uses the same echo approach
        assert "echo '" in called_command
        assert ">>" in called_command  # Append operator
        assert "'quotes'" in called_command  # Nested quotes will break

    # Test for proper escaping (what the fix should do)

    @pytest.mark.asyncio
    async def test_proper_content_escaping(
        self, file_management_tools: FileManagementTools
    ) -> None:
        """Test what proper escaping should look like."""
        dangerous_content = "'; rm -rf /; echo 'hacked"
        
        file_management_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                command="echo '...' > /test/file.txt",  # Should be escaped
                exit_code=0,
                stdout="",
                stderr="",
                success=True,
                execution_time=0.1,
            )
        )

        result = await file_management_tools.handle_tool_call(
            "manage_file",
            {"action": "write", "path": "/test/file.txt", "content": dangerous_content},
        )

        called_command = file_management_tools.container.retropie_client.execute_command.call_args[0][0]
        
        # Current bug: this dangerous content could cause command injection
        # The fix should properly escape this content
        assert "rm -rf /" in called_command  # This is dangerous!

    @pytest.mark.asyncio
    async def test_monitoring_mode_false_positive(
        self, file_management_tools: FileManagementTools
    ) -> None:
        """Test that file operations don't trigger monitoring mode."""
        # Commands with 'watch' or 'tail' in the path shouldn't trigger monitoring
        file_management_tools.container.retropie_client.execute_command.return_value = (
            CommandResult(
                command="echo 'content' > /var/log/watch_folder/tail_log.txt",
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
                "action": "write",
                "path": "/var/log/watch_folder/tail_log.txt",
                "content": "content",
            },
        )

        # Should complete normally, not enter monitoring mode
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "✅" in result[0].text
        assert "monitoring" not in result[0].text.lower()