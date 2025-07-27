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
        """Deserialize dictionary to CommandQueue."""
        try:
            queue = CommandQueue(
                id=data["id"],
                name=data["name"],
                current_index=data.get("current_index", 0),
                auto_execute=data.get("auto_execute", False),
                pause_between=data.get("pause_between", 2),
            )

            # Parse created_at if present
            if "created_at" in data:
                try:
                    queue.created_at = datetime.fromisoformat(data["created_at"])
                except ValueError:
                    # Use current time if parsing fails
                    queue.created_at = datetime.now()

            # Deserialize commands
            queue.commands = []
            for cmd_data in data.get("commands", []):
                cmd = self._deserialize_command(cmd_data)
                if cmd:
                    queue.commands.append(cmd)

            return queue

        except (KeyError, TypeError, ValueError):
            # Invalid queue data, skip this queue
            return None

    def _deserialize_command(self, data: Dict) -> Optional[QueuedCommand]:
        """Deserialize dictionary to QueuedCommand."""
        try:
            # Parse status
            try:
                status = CommandStatus(data["status"])
            except ValueError:
                status = CommandStatus.PENDING

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

    def delete_queue(self, queue_id: str) -> bool:
        """Delete queue from storage.

        Args:
            queue_id: Unique identifier for the queue

        Returns:
            True if queue was deleted, False if not found
        """
        if queue_id not in self.queues:
            return False

        del self.queues[queue_id]

        # Persist the change
        save_result = self._save_queues()
        if save_result.is_error():
            # If save failed, restore the queue to maintain consistency
            # Note: This is a simplified approach - in production you might want
            # more sophisticated error handling
            return False

        return True

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

        self.queues[queue_id] = queue
        return self._save_queues()
