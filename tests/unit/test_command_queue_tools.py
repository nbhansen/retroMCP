"""Tests for CommandQueueTools."""

from datetime import datetime
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from retromcp.domain.models import CommandResult
from retromcp.domain.models import CommandQueue
from retromcp.domain.models import CommandStatus
from retromcp.domain.models import QueuedCommand
from retromcp.tools.command_queue import CommandQueueTools


class TestCommandQueueTools:
    """Test CommandQueueTools functionality."""

    @pytest.fixture
    def mock_container(self):
        """Create a mock container."""
        container = MagicMock()
        container.retropie_client = MagicMock()
        container.retropie_client.execute_command = MagicMock()
        return container

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Setup and teardown for each test."""
        import os
        # Clean up persistent storage before each test
        storage_path = os.path.expanduser("~/.retromcp/command_queues.json")
        if os.path.exists(storage_path):
            os.remove(storage_path)
        yield
        # Clean up after each test
        if os.path.exists(storage_path):
            os.remove(storage_path)

    @pytest.fixture
    def queue_tools(self, mock_container):
        """Create CommandQueueTools instance."""
        return CommandQueueTools(mock_container)

    def test_tool_registration(self, queue_tools):
        """Test that tools are properly registered."""
        tools = queue_tools.get_tools()
        assert len(tools) == 1

        tool = tools[0]
        assert tool.name == "manage_command_queue"
        assert "queue" in tool.description.lower()
        assert "action" in tool.inputSchema["properties"]
        assert tool.inputSchema["properties"]["action"]["enum"] == [
            "create",
            "add",
            "execute_next",
            "execute_all",
            "status",
            "cancel",
            "skip",
        ]

    def test_create_queue_empty(self, queue_tools):
        """Test creating an empty queue."""
        result = queue_tools.manage_command_queue(
            {"action": "create", "name": "Test Queue"}
        )

        assert len(result) == 1
        text = result[0].text
        assert "Created command queue: Test Queue" in text
        assert "Total commands: 0" in text
        assert "Auto-execute: False" in text

    def test_create_queue_with_commands(self, queue_tools):
        """Test creating a queue with initial commands."""
        commands = [
            {"command": "echo 'test1'", "description": "First test"},
            {"command": "echo 'test2'", "description": "Second test"},
        ]

        result = queue_tools.manage_command_queue(
            {
                "action": "create",
                "name": "Test Queue",
                "commands": commands,
                "auto_execute": True,
                "pause_between": 3,
            }
        )

        text = result[0].text
        assert "Created command queue: Test Queue" in text
        assert "Total commands: 2" in text
        assert "Auto-execute: True" in text
        assert "First test" in text
        assert "echo 'test1'" in text
        assert "Second test" in text
        assert "echo 'test2'" in text

    def test_execute_next_success(self, queue_tools, mock_container):
        """Test executing the next command successfully."""
        # Create queue
        queue_tools.manage_command_queue(
            {
                "action": "create",
                "name": "Test Queue",
                "commands": [{"command": "echo 'hello'", "description": "Say hello"}],
            }
        )

        # Mock successful execution
        mock_container.retropie_client.execute_command.return_value = CommandResult(
            command="echo 'hello'",
            exit_code=0,
            stdout="hello",
            stderr="",
            success=True,
            execution_time=0.1
        )

        # Execute next
        result = queue_tools.manage_command_queue(
            {"action": "execute_next", "queue_id": "q1"}
        )

        text = result[0].text
        assert "[1/1] Executing: Say hello" in text
        assert "Command: echo 'hello'" in text
        assert "✓ Success" in text
        assert "Output: hello" in text

        # Verify command was called
        mock_container.retropie_client.execute_command.assert_called_once_with(
            "echo 'hello'"
        )

    def test_execute_next_failure(self, queue_tools, mock_container):
        """Test executing a command that fails."""
        # Create queue with two commands
        queue_tools.manage_command_queue(
            {
                "action": "create",
                "name": "Test Queue",
                "commands": [
                    {"command": "false", "description": "Fail command"},
                    {
                        "command": "echo 'should not run'",
                        "description": "Second command",
                    },
                ],
            }
        )

        # Mock failed execution
        mock_container.retropie_client.execute_command.return_value = CommandResult(
            command="false",
            exit_code=1,
            stdout="",
            stderr="Command failed",
            success=False,
            execution_time=0.1
        )

        # Execute next
        result = queue_tools.manage_command_queue(
            {"action": "execute_next", "queue_id": "q1"}
        )

        text = result[0].text
        assert "✗ Failed (exit code: 1)" in text
        assert "Error: Command failed" in text
        assert "Queue execution stopped" in text
        assert "Use 'skip' to skip this command" in text

    def test_skip_failed_command(self, queue_tools, mock_container):
        """Test skipping a failed command."""
        # Create queue and fail first command
        queue_tools.manage_command_queue(
            {
                "action": "create",
                "commands": [
                    {"command": "false", "description": "Fail"},
                    {"command": "echo 'ok'", "description": "Success"},
                ],
            }
        )

        mock_container.retropie_client.execute_command.return_value = CommandResult(
            command="false",
            exit_code=1,
            stdout="",
            stderr="Failed",
            success=False,
            execution_time=0.1
        )
        queue_tools.manage_command_queue({"action": "execute_next", "queue_id": "q1"})

        # Skip the failed command
        result = queue_tools.manage_command_queue({"action": "skip", "queue_id": "q1"})

        assert "Skipped failed command: Fail" in result[0].text

        # Now execute next should work
        mock_container.retropie_client.execute_command.return_value = CommandResult(
            command="echo 'ok'",
            exit_code=0,
            stdout="ok",
            stderr="",
            success=True,
            execution_time=0.1
        )
        result = queue_tools.manage_command_queue(
            {"action": "execute_next", "queue_id": "q1"}
        )

        assert "✓ Success" in result[0].text

    def test_queue_status(self, queue_tools, mock_container):
        """Test getting queue status."""
        # Create queue with multiple commands
        queue_tools.manage_command_queue(
            {
                "action": "create",
                "name": "Status Test",
                "commands": [
                    {"command": "echo '1'", "description": "First"},
                    {"command": "echo '2'", "description": "Second"},
                    {"command": "echo '3'", "description": "Third"},
                ],
            }
        )

        # Execute first command
        mock_container.retropie_client.execute_command.return_value = CommandResult(
            command="echo '1'",
            exit_code=0,
            stdout="1",
            stderr="",
            success=True,
            execution_time=0.1
        )
        queue_tools.manage_command_queue({"action": "execute_next", "queue_id": "q1"})

        # Get status
        result = queue_tools.manage_command_queue(
            {"action": "status", "queue_id": "q1"}
        )

        text = result[0].text
        assert "Queue: Status Test" in text
        assert "Progress: 1/3 commands" in text
        assert "✅ First" in text
        assert "⏳ Second" in text
        assert "⏳ Third" in text

    def test_status_all_queues(self, queue_tools):
        """Test getting status of all queues."""
        # Create multiple queues
        queue_tools.manage_command_queue(
            {
                "action": "create",
                "name": "Queue 1",
                "commands": [{"command": "echo '1'", "description": "Test"}],
            }
        )

        queue_tools.manage_command_queue(
            {
                "action": "create",
                "name": "Queue 2",
                "commands": [
                    {"command": "echo '1'", "description": "Test1"},
                    {"command": "echo '2'", "description": "Test2"},
                ],
            }
        )

        # Get status without queue_id
        result = queue_tools.manage_command_queue({"action": "status"})

        text = result[0].text
        assert "Active command queues:" in text
        assert "Queue 1 (ID: q1): 0/1 completed" in text
        assert "Queue 2 (ID: q2): 0/2 completed" in text

    def test_cancel_queue(self, queue_tools):
        """Test cancelling remaining commands in a queue."""
        # Create queue
        queue_tools.manage_command_queue(
            {
                "action": "create",
                "commands": [
                    {"command": "echo '1'", "description": "First"},
                    {"command": "echo '2'", "description": "Second"},
                    {"command": "echo '3'", "description": "Third"},
                ],
            }
        )

        # Cancel the queue
        result = queue_tools.manage_command_queue(
            {"action": "cancel", "queue_id": "q1"}
        )

        assert "Cancelled 3 pending commands" in result[0].text

    def test_add_commands_to_existing_queue(self, queue_tools):
        """Test adding commands to an existing queue."""
        # Create initial queue
        queue_tools.manage_command_queue(
            {
                "action": "create",
                "name": "Dynamic Queue",
                "commands": [{"command": "echo '1'", "description": "Initial"}],
            }
        )

        # Add more commands
        result = queue_tools.manage_command_queue(
            {
                "action": "add",
                "queue_id": "q1",
                "commands": [
                    {"command": "echo '2'", "description": "Added 1"},
                    {"command": "echo '3'", "description": "Added 2"},
                ],
            }
        )

        text = result[0].text
        assert "Added 2 commands to queue" in text
        assert "Total commands: 3" in text

    def test_execute_all_without_auto_execute(self, queue_tools):
        """Test execute_all requires auto_execute or force."""
        queue_tools.manage_command_queue(
            {
                "action": "create",
                "commands": [{"command": "echo '1'", "description": "Test"}],
            }
        )

        result = queue_tools.manage_command_queue(
            {"action": "execute_all", "queue_id": "q1"}
        )

        assert "was not created with auto_execute=true" in result[0].text
        assert "force=true" in result[0].text

    @patch("time.sleep")
    def test_execute_all_with_force(self, mock_sleep, queue_tools, mock_container):
        """Test execute_all with force flag."""
        queue_tools.manage_command_queue(
            {
                "action": "create",
                "commands": [
                    {"command": "echo '1'", "description": "First"},
                    {"command": "echo '2'", "description": "Second"},
                ],
                "pause_between": 1,
            }
        )

        mock_container.retropie_client.execute_command.return_value = CommandResult(
            command="echo 'test'",
            exit_code=0,
            stdout="output",
            stderr="",
            success=True,
            execution_time=0.1
        )

        result = queue_tools.manage_command_queue(
            {"action": "execute_all", "queue_id": "q1", "force": True}
        )

        text = result[0].text
        assert "All 2 commands executed successfully" in text
        assert mock_container.retropie_client.execute_command.call_count == 2
        mock_sleep.assert_called_once_with(1)

    def test_execute_all_stops_on_failure(self, queue_tools, mock_container):
        """Test execute_all stops when a command fails."""
        queue_tools.manage_command_queue(
            {
                "action": "create",
                "commands": [
                    {"command": "echo '1'", "description": "First"},
                    {"command": "false", "description": "Fail"},
                    {"command": "echo '3'", "description": "Should not run"},
                ],
                "auto_execute": True,
            }
        )

        # First command succeeds, second fails
        mock_container.retropie_client.execute_command.side_effect = [
            CommandResult(
                command="echo '1'",
                exit_code=0,
                stdout="1",
                stderr="",
                success=True,
                execution_time=0.1
            ),
            CommandResult(
                command="false",
                exit_code=1,
                stdout="",
                stderr="Failed",
                success=False,
                execution_time=0.1
            ),
        ]

        result = queue_tools.manage_command_queue(
            {"action": "execute_all", "queue_id": "q1"}
        )

        text = result[0].text
        assert "Execution stopped after 2 commands due to failure" in text
        assert mock_container.retropie_client.execute_command.call_count == 2

    def test_queue_not_found(self, queue_tools):
        """Test operations on non-existent queue."""
        result = queue_tools.manage_command_queue(
            {"action": "execute_next", "queue_id": "invalid"}
        )

        assert "Queue not found: invalid" in result[0].text

    def test_command_exception_handling(self, queue_tools, mock_container):
        """Test handling exceptions during command execution."""
        queue_tools.manage_command_queue(
            {
                "action": "create",
                "commands": [{"command": "bad_command", "description": "Will throw"}],
            }
        )

        mock_container.retropie_client.execute_command.side_effect = Exception(
            "Connection lost"
        )

        result = queue_tools.manage_command_queue(
            {"action": "execute_next", "queue_id": "q1"}
        )

        text = result[0].text
        assert "✗ Exception: Connection lost" in text
        assert "Use 'skip' to skip this command" in text

    def test_empty_queue_execute_next(self, queue_tools):
        """Test executing next on empty queue."""
        queue_tools.manage_command_queue({"action": "create"})

        result = queue_tools.manage_command_queue(
            {"action": "execute_next", "queue_id": "q1"}
        )

        assert "No more commands to execute" in result[0].text


class TestQueuedCommand:
    """Test QueuedCommand model."""

    def test_command_creation(self):
        """Test creating a queued command."""
        cmd = QueuedCommand(
            id="test1", command="echo 'hello'", description="Test command"
        )

        assert cmd.id == "test1"
        assert cmd.command == "echo 'hello'"
        assert cmd.description == "Test command"
        assert cmd.status == CommandStatus.PENDING
        assert cmd.result is None
        assert cmd.error is None

    def test_command_to_dict(self):
        """Test converting command to dictionary."""
        cmd = QueuedCommand(
            id="test1",
            command="echo 'hello'",
            description="Test command",
            status=CommandStatus.COMPLETED,
            result={"exit_code": 0},
            start_time=datetime(2024, 1, 1, 12, 0, 0),
            end_time=datetime(2024, 1, 1, 12, 0, 1),
        )

        data = cmd.to_dict()
        assert data["id"] == "test1"
        assert data["status"] == "completed"
        assert data["result"] == {"exit_code": 0}
        assert data["start_time"] == "2024-01-01T12:00:00"
        assert data["end_time"] == "2024-01-01T12:00:01"


class TestCommandQueue:
    """Test CommandQueue model."""

    def test_queue_creation(self):
        """Test creating a command queue."""
        queue = CommandQueue(id="q1", name="Test Queue")

        assert queue.id == "q1"
        assert queue.name == "Test Queue"
        assert len(queue.commands) == 0
        assert queue.current_index == 0
        assert queue.auto_execute is False
        assert queue.pause_between == 2

    def test_add_command(self):
        """Test adding commands to queue."""
        queue = CommandQueue(id="q1", name="Test")

        cmd1 = queue.add_command("echo '1'", "First")
        assert cmd1.id == "q1_0"
        assert len(queue.commands) == 1

        cmd2 = queue.add_command("echo '2'", "Second")
        assert cmd2.id == "q1_1"
        assert len(queue.commands) == 2

    def test_get_current(self):
        """Test getting current command."""
        queue = CommandQueue(id="q1", name="Test")

        # Empty queue
        assert queue.get_current() is None

        # Add commands
        queue.add_command("echo '1'", "First")
        queue.add_command("echo '2'", "Second")

        # Get current
        current = queue.get_current()
        assert current.description == "First"

        # Move index
        queue.current_index = 1
        current = queue.get_current()
        assert current.description == "Second"

        # Past end
        queue.current_index = 2
        assert queue.get_current() is None

    def test_get_next_pending(self):
        """Test getting next pending command."""
        queue = CommandQueue(id="q1", name="Test")

        cmd1 = queue.add_command("echo '1'", "First")
        cmd2 = queue.add_command("echo '2'", "Second")
        cmd3 = queue.add_command("echo '3'", "Third")

        # All pending
        assert queue.get_next_pending() == cmd1

        # Complete first
        cmd1.status = CommandStatus.COMPLETED
        assert queue.get_next_pending() == cmd2

        # Skip second
        cmd2.status = CommandStatus.SKIPPED
        assert queue.get_next_pending() == cmd3

        # All done
        cmd3.status = CommandStatus.COMPLETED
        assert queue.get_next_pending() is None

    def test_queue_to_dict(self):
        """Test converting queue to dictionary."""
        queue = CommandQueue(
            id="q1", name="Test Queue", auto_execute=True, pause_between=5
        )

        queue.add_command("echo '1'", "First")
        queue.add_command("echo '2'", "Second")
        queue.commands[0].status = CommandStatus.COMPLETED

        data = queue.to_dict()
        assert data["id"] == "q1"
        assert data["name"] == "Test Queue"
        assert data["auto_execute"] is True
        assert data["pause_between"] == 5
        assert data["completed"] == 1
        assert data["total"] == 2
        assert len(data["commands"]) == 2
