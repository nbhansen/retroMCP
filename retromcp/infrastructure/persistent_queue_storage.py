"""Persistent storage for command queues to survive MCP instance recreation."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import fcntl
import tempfile

from ..domain.models import (
    Result,
    ValidationError,
    CommandQueue,
    CommandStatus,
    QueuedCommand,
)


class PersistentQueueStorage:
    """Manages persistent storage of command queues using JSON files."""

    def __init__(self, storage_path: str) -> None:
        """Initialize persistent storage with file path.

        Args:
            storage_path: Path to JSON file for storing queues
        """
        self.storage_path = storage_path
        self.queues: Dict[str, CommandQueue] = {}
        self._ensure_storage_directory()
        self._load_queues()

    def _ensure_storage_directory(self) -> None:
        """Ensure storage directory exists."""
        try:
            storage_dir = Path(self.storage_path).parent
            storage_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            # If we can't create the directory, we'll handle it gracefully later
            pass

    def _load_queues(self) -> None:
        """Load queues from persistent storage."""
        try:
            if not os.path.exists(self.storage_path):
                # File doesn't exist yet, start with empty storage
                self.queues = {}
                return

            with open(self.storage_path, "r") as f:
                # Use file locking for thread safety
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                try:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self.queues = {}
                        for queue_id, queue_data in data.items():
                            queue = self._deserialize_queue(queue_data)
                            if queue:
                                self.queues[queue_id] = queue
                    else:
                        # Invalid format, start fresh
                        self.queues = {}
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except (json.JSONDecodeError, OSError, PermissionError):
            # Corrupted file or permission issues - start with empty storage
            self.queues = {}

    def _save_queues(self) -> Result[None, ValidationError]:
        """Save queues to persistent storage.

        Returns:
            Result indicating success or failure
        """
        try:
            # Create temp file first, then atomic rename for safety
            temp_fd, temp_path = tempfile.mkstemp(
                dir=Path(self.storage_path).parent, prefix=".queues_", suffix=".tmp"
            )

            try:
                with os.fdopen(temp_fd, "w") as f:
                    # Use file locking for thread safety
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                    try:
                        serialized_queues = {}
                        for queue_id, queue in self.queues.items():
                            serialized_queues[queue_id] = self._serialize_queue(queue)

                        json.dump(serialized_queues, f, indent=2, default=str)
                        f.flush()
                        os.fsync(f.fileno())
                    finally:
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)

                # Atomic rename to final location
                os.rename(temp_path, self.storage_path)
                return Result.success(None)

            except Exception:
                # Clean up temp file on error
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
                raise

        except (OSError, PermissionError) as e:
            return Result.error(
                ValidationError(
                    code="STORAGE_SAVE_FAILED",
                    message=f"Failed to save queues to storage: {str(e)}",
                )
            )

    def _serialize_queue(self, queue: CommandQueue) -> Dict:
        """Serialize a CommandQueue to dictionary."""
        return {
            "id": queue.id,
            "name": queue.name,
            "commands": [self._serialize_command(cmd) for cmd in queue.commands],
            "current_index": queue.current_index,
            "created_at": queue.created_at.isoformat(),
            "auto_execute": queue.auto_execute,
            "pause_between": queue.pause_between,
        }

    def _serialize_command(self, command: QueuedCommand) -> Dict:
        """Serialize a QueuedCommand to dictionary."""
        return {
            "id": command.id,
            "command": command.command,
            "description": command.description,
            "status": command.status.value,
            "result": command.result,
            "error": command.error,
            "start_time": command.start_time.isoformat()
            if command.start_time
            else None,
            "end_time": command.end_time.isoformat() if command.end_time else None,
        }

    def _deserialize_queue(self, data: Dict) -> Optional[CommandQueue]:
        """Deserialize dictionary to CommandQueue with strict type validation."""
        try:
            # Validate required fields exist and are correct types
            queue_id = data["id"]
            name = data["name"]

            if not isinstance(queue_id, str) or not isinstance(name, str):
                return None

            # Validate and convert numeric types with strict checking
            try:
                current_index = int(data.get("current_index", 0))
            except (ValueError, TypeError):
                return None

            try:
                pause_between = int(data.get("pause_between", 2))
            except (ValueError, TypeError):
                return None

            # Validate boolean type
            auto_execute_val = data.get("auto_execute", False)
            if not isinstance(auto_execute_val, bool):
                return None

            # Validate commands is a list
            commands_data = data.get("commands", [])
            if not isinstance(commands_data, list):
                return None

            queue = CommandQueue(
                id=queue_id,
                name=name,
                current_index=current_index,
                auto_execute=auto_execute_val,
                pause_between=pause_between,
            )

            # Parse created_at if present
            if "created_at" in data:
                try:
                    queue.created_at = datetime.fromisoformat(data["created_at"])
                except (ValueError, TypeError):
                    # Use current time if parsing fails
                    queue.created_at = datetime.now()

            # Deserialize commands
            queue.commands = []
            for cmd_data in commands_data:
                cmd = self._deserialize_command(cmd_data)
                if cmd:
                    queue.commands.append(cmd)

            return queue

        except (KeyError, TypeError, ValueError):
            # Invalid queue data, skip this queue
            return None

    def _deserialize_command(self, data: Dict) -> Optional[QueuedCommand]:
        """Deserialize dictionary to QueuedCommand with strict validation."""
        try:
            # Parse status - return None if invalid (strict validation)
            try:
                status = CommandStatus(data["status"])
            except (ValueError, KeyError):
                # Invalid status - reject the command entirely
                return None

            # Parse timestamps
            start_time = None
            if data.get("start_time"):
                try:
                    start_time = datetime.fromisoformat(data["start_time"])
                except ValueError:
                    pass

            end_time = None
            if data.get("end_time"):
                try:
                    end_time = datetime.fromisoformat(data["end_time"])
                except ValueError:
                    pass

            return QueuedCommand(
                id=data["id"],
                command=data["command"],
                description=data["description"],
                status=status,
                result=data.get("result"),
                error=data.get("error"),
                start_time=start_time,
                end_time=end_time,
            )

        except (KeyError, TypeError):
            # Invalid command data, skip this command
            return None

    def create_queue(
        self, queue_id: str, queue: CommandQueue
    ) -> Result[None, ValidationError]:
        """Create and persist a new queue.

        Args:
            queue_id: Unique identifier for the queue
            queue: CommandQueue instance to store

        Returns:
            Result indicating success or failure
        """
        if not queue_id or not queue_id.strip():
            return Result.error(
                ValidationError(
                    code="INVALID_QUEUE_ID", message="Queue ID cannot be empty"
                )
            )

        # Store queue in memory
        self.queues[queue_id] = queue

        # Persist to storage
        return self._save_queues()

    def get_queue(self, queue_id: str) -> Optional[CommandQueue]:
        """Retrieve queue from storage.

        Args:
            queue_id: Unique identifier for the queue

        Returns:
            CommandQueue instance or None if not found
        """
        return self.queues.get(queue_id)

    def list_queues(self) -> List[str]:
        """List all persisted queue IDs.

        Returns:
            List of queue IDs
        """
        return list(self.queues.keys())

    def delete_queue(self, queue_id: str) -> Result[None, ValidationError]:
        """Delete queue from storage.

        Args:
            queue_id: Unique identifier for the queue

        Returns:
            Result indicating success or failure
        """
        if queue_id not in self.queues:
            return Result.error(
                ValidationError(
                    code="QUEUE_NOT_FOUND",
                    message=f"Queue with ID '{queue_id}' not found",
                )
            )

        # Store original queue for rollback
        deleted_queue = self.queues[queue_id]
        del self.queues[queue_id]

        try:
            # Persist the change
            save_result = self._save_queues()
            if save_result.is_error():
                # Rollback on save failure
                self.queues[queue_id] = deleted_queue
                return Result.error(
                    ValidationError(
                        code="DELETE_QUEUE_SAVE_FAILED",
                        message="Failed to save after deleting queue",
                    )
                )

            return Result.success(None)

        except Exception as e:
            # Rollback on exception
            self.queues[queue_id] = deleted_queue
            return Result.error(
                ValidationError(
                    code="DELETE_QUEUE_SAVE_FAILED",
                    message="Failed to save after deleting queue",
                )
            )

    def update_queue(
        self, queue_id: str, queue: CommandQueue
    ) -> Result[None, ValidationError]:
        """Update an existing queue in storage.

        Args:
            queue_id: Unique identifier for the queue
            queue: Updated CommandQueue instance

        Returns:
            Result indicating success or failure
        """
        if queue_id not in self.queues:
            return Result.error(
                ValidationError(
                    code="QUEUE_NOT_FOUND",
                    message=f"Queue with ID '{queue_id}' not found",
                )
            )

        # Store original queue for potential rollback
        original_queue = self.queues[queue_id]
        self.queues[queue_id] = queue

        try:
            save_result = self._save_queues()

            if save_result.is_error():
                # Rollback on save failure
                self.queues[queue_id] = original_queue
                return save_result

            return Result.success(None)

        except Exception as e:
            # Rollback on exception and return error
            self.queues[queue_id] = original_queue
            return Result.error(
                ValidationError(
                    code="UPDATE_QUEUE_FAILED",
                    message=f"Failed to update queue: {str(e)}",
                )
            )
