"""Command queue system for interruptible batch execution."""

import os
import time
from datetime import datetime
from typing import Any
from typing import Dict
from typing import List

from mcp.types import TextContent
from mcp.types import Tool

from ..container import Container
from ..domain.models import CommandQueue
from ..domain.models import CommandStatus
from ..infrastructure.persistent_queue_storage import PersistentQueueStorage
from .base import BaseTool


class CommandQueueTools(BaseTool):
    """Tools for managing command queues."""

    def __init__(self, container: Container) -> None:
        """Initialize with container and persistent storage."""
        super().__init__(container)

        # Initialize persistent storage
        storage_path = os.path.expanduser("~/.retromcp/command_queues.json")
        self._storage = PersistentQueueStorage(storage_path)
        self._queue_counter = len(self._storage.list_queues())

    def get_tools(self) -> List[Tool]:
        """Get tool definitions."""
        return [
            Tool(
                name="manage_command_queue",
                description=(
                    "Create and manage command queues for controlled batch execution. "
                    "Allows graceful interruption and step-by-step execution."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": [
                                "create",
                                "add",
                                "execute_next",
                                "execute_all",
                                "status",
                                "cancel",
                                "skip",
                            ],
                            "description": "Action to perform",
                        },
                        "queue_id": {
                            "type": "string",
                            "description": "Queue ID (required for all actions except create)",
                        },
                        "name": {
                            "type": "string",
                            "description": "Queue name (for create action)",
                        },
                        "commands": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "command": {"type": "string"},
                                    "description": {"type": "string"},
                                },
                                "required": ["command", "description"],
                            },
                            "description": "Commands to add (for create or add actions)",
                        },
                        "auto_execute": {
                            "type": "boolean",
                            "description": "Automatically execute all commands without pausing",
                        },
                        "pause_between": {
                            "type": "integer",
                            "description": "Seconds to pause between commands (default: 2)",
                        },
                    },
                    "required": ["action"],
                },
            )
        ]

    async def handle_tool_call(
        self, name: str, arguments: Dict[str, Any]
    ) -> List[TextContent]:
        """Handle tool calls for command queue management."""
        if name == "manage_command_queue":
            return self.manage_command_queue(arguments)
        else:
            return self.format_error(f"Unknown tool: {name}")

    def manage_command_queue(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Manage command queues."""
        action = arguments.get("action")
        queue_id = arguments.get("queue_id")

        if action == "create":
            return self._create_queue(arguments)
        elif action == "add":
            return self._add_to_queue(queue_id, arguments)
        elif action == "execute_next":
            return self._execute_next(queue_id)
        elif action == "execute_all":
            return self._execute_all(queue_id, arguments)
        elif action == "status":
            return self._get_status(queue_id)
        elif action == "cancel":
            return self._cancel_queue(queue_id)
        elif action == "skip":
            return self._skip_current(queue_id)
        else:
            return self.format_error(f"Unknown action: {action}")

    def _create_queue(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Create a new command queue."""
        name = arguments.get("name", f"Queue_{self._queue_counter}")
        commands = arguments.get("commands", [])
        auto_execute = arguments.get("auto_execute", False)
        pause_between = arguments.get("pause_between", 2)

        self._queue_counter += 1
        queue_id = f"q{self._queue_counter}"

        queue = CommandQueue(
            id=queue_id,
            name=name,
            auto_execute=auto_execute,
            pause_between=pause_between,
        )

        # Add initial commands
        for cmd_data in commands:
            queue.add_command(
                command=cmd_data["command"], description=cmd_data["description"]
            )

        # Persist queue to storage
        result = self._storage.create_queue(queue_id, queue)
        if result.is_error():
            return self.format_error(
                f"Failed to create queue: {result.error_value.message}"
            )

        output = [
            f"Created command queue: {name} (ID: {queue_id})",
            f"Total commands: {len(queue.commands)}",
            f"Auto-execute: {auto_execute}",
            "",
        ]

        if queue.commands:
            output.append("Commands in queue:")
            for i, cmd in enumerate(queue.commands):
                output.append(f"{i + 1}. {cmd.description}")
                output.append(f"   Command: {cmd.command}")

            output.append("")
            output.append(
                "Use 'execute_next' to run the first command, or 'execute_all' to run all."
            )

        return [TextContent(type="text", text="\n".join(output))]

    def _add_to_queue(
        self, queue_id: str, arguments: Dict[str, Any]
    ) -> List[TextContent]:
        """Add commands to an existing queue."""
        queue = self._storage.get_queue(queue_id)
        if queue is None:
            return self.format_error(f"Queue not found: {queue_id}")

        commands = arguments.get("commands", [])

        if not commands:
            return self.format_error("No commands provided to add")

        # Add commands
        added = 0
        for cmd_data in commands:
            queue.add_command(
                command=cmd_data["command"], description=cmd_data["description"]
            )
            added += 1

        # Update queue in storage
        result = self._storage.update_queue(queue_id, queue)
        if result.is_error():
            return self.format_error(
                f"Failed to update queue: {result.error_value.message}"
            )

        return [
            TextContent(
                type="text",
                text=f"Added {added} commands to queue: {queue.name}\nTotal commands: {len(queue.commands)}",
            )
        ]

    def _execute_next(self, queue_id: str) -> List[TextContent]:
        """Execute the next command in the queue."""
        queue = self._storage.get_queue(queue_id)
        if queue is None:
            return self.format_error(f"Queue not found: {queue_id}")
        cmd = queue.get_next_pending()

        if not cmd:
            return [
                TextContent(
                    type="text", text="No more commands to execute in this queue."
                )
            ]

        # Update status
        cmd.status = CommandStatus.RUNNING
        cmd.start_time = datetime.now()

        output = [
            f"[{queue.current_index + 1}/{len(queue.commands)}] Executing: {cmd.description}",
            f"Command: {cmd.command}",
            "",
        ]

        try:
            # Execute the command using the proper RetroPieClient abstraction
            result = self.container.retropie_client.execute_command(cmd.command)

            cmd.end_time = datetime.now()
            cmd.result = {
                "exit_code": result.exit_code,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }

            if result.success:
                cmd.status = CommandStatus.COMPLETED
                output.append("✓ Success")
                if result.stdout:
                    output.append(f"Output: {result.stdout}")
            else:
                cmd.status = CommandStatus.FAILED
                output.append(f"✗ Failed (exit code: {result.exit_code})")
                if result.stderr:
                    output.append(f"Error: {result.stderr}")
                output.append("")
                output.append(
                    "Queue execution stopped. Use 'skip' to skip this command and continue."
                )

        except Exception as e:
            cmd.status = CommandStatus.FAILED
            cmd.error = str(e)
            cmd.end_time = datetime.now()
            output.append(f"✗ Exception: {e}")
            output.append("")
            output.append(
                "Queue execution stopped. Use 'skip' to skip this command and continue."
            )

        # Move to next command if successful
        if cmd.status == CommandStatus.COMPLETED:
            queue.current_index += 1

            # Show next command preview
            next_cmd = queue.get_next_pending()
            if next_cmd:
                output.append("")
                output.append(f"Next command: {next_cmd.description}")
                output.append("Use 'execute_next' to continue or 'status' to review.")

        # Update queue in storage
        result = self._storage.update_queue(queue_id, queue)
        if result.is_error():
            output.append(
                f"Warning: Failed to save queue state: {result.error_value.message}"
            )

        return [TextContent(type="text", text="\n".join(output))]

    def _execute_all(
        self, queue_id: str, arguments: Dict[str, Any]
    ) -> List[TextContent]:
        """Execute all remaining commands in the queue."""
        queue = self._storage.get_queue(queue_id)
        if queue is None:
            return self.format_error(f"Queue not found: {queue_id}")
        force = arguments.get("force", False)

        if not force and not queue.auto_execute:
            return [
                TextContent(
                    type="text",
                    text="This queue was not created with auto_execute=true. "
                    "Use force=true to execute all commands anyway, or use 'execute_next' for controlled execution.",
                )
            ]

        output = []
        executed = 0
        last_cmd = None

        while True:
            cmd = queue.get_next_pending()
            if not cmd:
                break

            # Execute command
            result = self._execute_next(queue_id)
            output.extend(result[0].text.split("\n"))
            executed += 1
            last_cmd = cmd

            # Check if execution failed
            if cmd.status == CommandStatus.FAILED:
                output.append("")
                output.append(
                    f"Execution stopped after {executed} commands due to failure."
                )
                break

            # Pause between commands if configured
            if queue.pause_between > 0 and queue.get_next_pending():
                time.sleep(queue.pause_between)

        if last_cmd is None or last_cmd.status != CommandStatus.FAILED:
            output.append("")
            output.append(f"All {executed} commands executed successfully.")

        return [TextContent(type="text", text="\n".join(output))]

    def _get_status(self, queue_id: str) -> List[TextContent]:
        """Get the status of a command queue."""
        if queue_id is None:
            # Show all queues
            queue_ids = self._storage.list_queues()
            if not queue_ids:
                return [TextContent(type="text", text="No command queues exist.")]

            output = ["Active command queues:"]
            for qid in queue_ids:
                queue = self._storage.get_queue(qid)
                if queue:
                    completed = sum(
                        1
                        for cmd in queue.commands
                        if cmd.status == CommandStatus.COMPLETED
                    )
                    total = len(queue.commands)
                    output.append(
                        f"- {queue.name} (ID: {qid}): {completed}/{total} completed"
                    )

            return [TextContent(type="text", text="\n".join(output))]

        queue = self._storage.get_queue(queue_id)
        if queue is None:
            return self.format_error(f"Queue not found: {queue_id}")
        output = [
            f"Queue: {queue.name} (ID: {queue.id})",
            f"Created: {queue.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Progress: {queue.current_index}/{len(queue.commands)} commands",
            "",
        ]

        for i, cmd in enumerate(queue.commands):
            status_icon = {
                CommandStatus.PENDING: "⏳",
                CommandStatus.RUNNING: "🔄",
                CommandStatus.COMPLETED: "✅",
                CommandStatus.FAILED: "❌",
                CommandStatus.SKIPPED: "⏭️",
                CommandStatus.CANCELLED: "🚫",
            }.get(cmd.status, "❓")

            output.append(f"{i + 1}. {status_icon} {cmd.description}")
            if cmd.status == CommandStatus.FAILED and cmd.error:
                output.append(f"   Error: {cmd.error}")
            elif cmd.status == CommandStatus.COMPLETED and cmd.result:
                duration = (
                    (cmd.end_time - cmd.start_time).total_seconds()
                    if cmd.end_time and cmd.start_time
                    else 0
                )
                output.append(f"   Duration: {duration:.1f}s")

        return [TextContent(type="text", text="\n".join(output))]

    def _skip_current(self, queue_id: str) -> List[TextContent]:
        """Skip the current failed command and move to the next."""
        queue = self._storage.get_queue(queue_id)
        if queue is None:
            return self.format_error(f"Queue not found: {queue_id}")
        current = (
            queue.commands[queue.current_index]
            if queue.current_index < len(queue.commands)
            else None
        )

        if not current:
            return [TextContent(type="text", text="No command to skip.")]

        if current.status == CommandStatus.FAILED:
            current.status = CommandStatus.SKIPPED
            queue.current_index += 1

            # Update queue in storage
            result = self._storage.update_queue(queue_id, queue)
            if result.is_error():
                return self.format_error(
                    f"Failed to update queue: {result.error_value.message}"
                )

            return [
                TextContent(
                    type="text", text=f"Skipped failed command: {current.description}"
                )
            ]
        else:
            return [
                TextContent(
                    type="text",
                    text=f"Current command is not failed: {current.status.value}",
                )
            ]

    def _cancel_queue(self, queue_id: str) -> List[TextContent]:
        """Cancel all remaining commands in a queue."""
        queue = self._storage.get_queue(queue_id)
        if queue is None:
            return self.format_error(f"Queue not found: {queue_id}")

        cancelled = 0

        for cmd in queue.commands[queue.current_index :]:
            if cmd.status == CommandStatus.PENDING:
                cmd.status = CommandStatus.CANCELLED
                cancelled += 1

        # Update queue in storage
        result = self._storage.update_queue(queue_id, queue)
        if result.is_error():
            return self.format_error(
                f"Failed to update queue: {result.error_value.message}"
            )

        return [
            TextContent(
                type="text",
                text=f"Cancelled {cancelled} pending commands in queue: {queue.name}",
            )
        ]
