"""Integration test demonstrating the file creation bug."""

import pytest
from unittest.mock import Mock, patch
from retromcp.tools.file_management_tools import FileManagementTools
from retromcp.domain.models import CommandResult


@pytest.mark.integration
class TestFileCreationBug:
    """Tests that demonstrate the actual file creation bug reported by users."""

    @pytest.fixture
    def mock_container(self):
        """Provide mocked container."""
        container = Mock()
        container.retropie_client = Mock()
        return container

    @pytest.fixture
    def file_tools(self, mock_container):
        """Provide FileManagementTools instance."""
        return FileManagementTools(mock_container)

    @pytest.mark.asyncio
    async def test_demonstrates_multiline_echo_bug(self, file_tools, mock_container):
        """Demonstrate that echo command fails with multiline content."""
        
        # Simulate what happens when echo command with multiline is executed
        def simulate_real_ssh_execution(command):
            # In real SSH, echo with single quotes and newlines would fail
            if "echo '" in command and "\n" in command:
                # This is what actually happens - command fails or creates empty file
                return CommandResult(
                    command=command,
                    exit_code=0,  # May report success but...
                    stdout="",
                    stderr="",
                    success=True,  # Reports success
                    execution_time=0.1,
                )
            return CommandResult(
                command=command,
                exit_code=0,
                stdout="",
                stderr="",
                success=True,
                execution_time=0.1,
            )
        
        mock_container.retropie_client.execute_command.side_effect = simulate_real_ssh_execution
        
        # Try to write multiline content
        multiline_content = """Line 1
Line 2
Line 3"""
        
        result = await file_tools.handle_tool_call(
            "manage_file",
            {"action": "write", "path": "/test/file.txt", "content": multiline_content}
        )
        
        # Tool reports success
        assert "✅" in result[0].text
        assert "File written successfully" in result[0].text
        
        # But the actual command that was executed is broken
        actual_command = mock_container.retropie_client.execute_command.call_args[0][0]
        assert "echo '" in actual_command
        assert "\n" in actual_command  # This breaks the echo command!
        
        # Demonstrate what the actual file would contain (empty or partial)
        # In reality, the file would be empty or only contain "Line 1"

    @pytest.mark.asyncio
    async def test_demonstrates_quote_injection_bug(self, file_tools, mock_container):
        """Demonstrate that single quotes in content break the command."""
        
        def simulate_real_ssh_execution(command):
            # Single quote in content would break the echo command
            if "echo '" in command and "'" in command[6:]:  # Quote after "echo '"
                # Command would fail with syntax error
                return CommandResult(
                    command=command,
                    exit_code=1,
                    stdout="",
                    stderr="sh: syntax error: unterminated quoted string",
                    success=False,
                    execution_time=0.1,
                )
            return CommandResult(
                command=command,
                exit_code=0,
                stdout="",
                stderr="",
                success=True,
                execution_time=0.1,
            )
        
        mock_container.retropie_client.execute_command.side_effect = simulate_real_ssh_execution
        
        # Try to write content with quotes
        content_with_quotes = "It's a test file"
        
        result = await file_tools.handle_tool_call(
            "manage_file",
            {"action": "write", "path": "/test/file.txt", "content": content_with_quotes}
        )
        
        # This should fail but current implementation doesn't handle it properly
        actual_command = mock_container.retropie_client.execute_command.call_args[0][0]
        
        # The command is: echo 'It's a test file' > /test/file.txt
        # The quote in "It's" terminates the echo string prematurely!
        assert "echo 'It" in actual_command  # String gets cut off here
        
        # In real execution, this would cause a syntax error
        # But the mock shows it would fail
        if not result[0].text.startswith("✅"):
            assert "❌" in result[0].text
            assert "Failed" in result[0].text

    @pytest.mark.asyncio  
    async def test_demonstrates_command_injection_vulnerability(self, file_tools, mock_container):
        """Demonstrate potential command injection vulnerability."""
        
        # Malicious content trying to inject commands
        malicious_content = "'; rm -rf /; echo 'hacked"
        
        mock_container.retropie_client.execute_command.return_value = CommandResult(
            command=f"echo '{malicious_content}' > /test/file.txt",
            exit_code=0,
            stdout="",
            stderr="",
            success=True,
            execution_time=0.1,
        )
        
        result = await file_tools.handle_tool_call(
            "manage_file",
            {"action": "write", "path": "/test/file.txt", "content": malicious_content}
        )
        
        actual_command = mock_container.retropie_client.execute_command.call_args[0][0]
        
        # The dangerous command is included unescaped!
        assert "rm -rf /" in actual_command
        
        # In a real system, this could execute:
        # echo ''; rm -rf /; echo 'hacked' > /test/file.txt
        # Which would run rm -rf / !!!
        
    @pytest.mark.asyncio
    async def test_proper_solution_using_heredoc(self, file_tools, mock_container):
        """Test what the proper solution should look like using heredoc."""
        
        # This is what we SHOULD be doing
        multiline_content = """#!/bin/bash
echo "Test with 'quotes' and $variables"
echo "Multiple lines"
"""
        
        # The fix should use heredoc or printf with proper escaping
        # Expected command should be something like:
        # cat << 'EOF' > /test/file.txt
        # #!/bin/bash
        # echo "Test with 'quotes' and $variables"
        # echo "Multiple lines"
        # EOF
        
        # For now, this test documents what we want to achieve
        result = await file_tools.handle_tool_call(
            "manage_file",
            {"action": "write", "path": "/test/file.txt", "content": multiline_content}
        )
        
        actual_command = mock_container.retropie_client.execute_command.call_args[0][0]
        
        # Current broken implementation uses echo
        assert "echo '" in actual_command
        
        # After fix, it should use cat with heredoc or printf with proper escaping
        # assert "cat <<" in actual_command or "printf" in actual_command