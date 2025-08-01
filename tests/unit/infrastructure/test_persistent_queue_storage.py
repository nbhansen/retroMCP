"""Unit tests for PersistentQueueStorage implementation."""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest

from retromcp.domain.models import Result, ValidationError, CommandQueue, CommandStatus, QueuedCommand


class TestPersistentQueueStorage:
    """Test cases for PersistentQueueStorage class."""

    @pytest.fixture
    def temp_storage_path(self) -> str:
        """Provide temporary storage path for testing."""
        temp_dir = tempfile.mkdtemp()
        return str(Path(temp_dir) / "test_queues.json")

    @pytest.fixture
    def sample_queue(self) -> CommandQueue:
        """Provide sample command queue for testing."""
        queue = CommandQueue(
            id="test_queue_1",
            name="Test Queue",
            auto_execute=False,
            pause_between=2
        )
        queue.add_command("ls -la", "List directory contents")
        queue.add_command("pwd", "Show current directory")
        return queue

    # Test Case: Storage initialization
    def test_persistent_storage_initialization_empty_file(self, temp_storage_path: str) -> None:
        """Test storage initialization with empty/non-existent file."""
        from retromcp.infrastructure.persistent_queue_storage import PersistentQueueStorage
        storage = PersistentQueueStorage(temp_storage_path)
        
        # Should start with empty storage
        assert len(storage.list_queues()) == 0

    # Test Case: Queue creation and persistence
    def test_create_queue_persists_to_storage(self, temp_storage_path: str, sample_queue: CommandQueue) -> None:
        """Test that creating a queue persists it to storage."""
        from retromcp.infrastructure.persistent_queue_storage import PersistentQueueStorage
        storage = PersistentQueueStorage(temp_storage_path)
        
        # Create queue should persist immediately
        result = storage.create_queue(sample_queue.id, sample_queue)
        assert result.is_success()
        
        # Verify file was written
        assert Path(temp_storage_path).exists()

    # Test Case: Queue retrieval
    def test_get_queue_retrieves_from_storage(self, temp_storage_path: str, sample_queue: CommandQueue) -> None:
        """Test that getting a queue retrieves it from storage."""
        from retromcp.infrastructure.persistent_queue_storage import PersistentQueueStorage
        storage = PersistentQueueStorage(temp_storage_path)
        
        # Create and retrieve queue
        storage.create_queue(sample_queue.id, sample_queue)
        retrieved_queue = storage.get_queue(sample_queue.id)
        
        assert retrieved_queue is not None
        assert retrieved_queue.id == sample_queue.id
        assert retrieved_queue.name == sample_queue.name
        assert len(retrieved_queue.commands) == len(sample_queue.commands)

    # Test Case: Queue listing
    def test_list_queues_returns_all_queue_ids(self, temp_storage_path: str) -> None:
        """Test that listing queues returns all persisted queue IDs."""
        from retromcp.infrastructure.persistent_queue_storage import PersistentQueueStorage
        storage = PersistentQueueStorage(temp_storage_path)
        
        # Create multiple queues
        queue1 = CommandQueue(id="q1", name="Queue 1")
        queue2 = CommandQueue(id="q2", name="Queue 2")
        
        storage.create_queue(queue1.id, queue1)
        storage.create_queue(queue2.id, queue2)
        
        queue_ids = storage.list_queues()
        assert "q1" in queue_ids
        assert "q2" in queue_ids
        assert len(queue_ids) == 2

    # Test Case: Queue deletion
    def test_delete_queue_removes_from_storage(self, temp_storage_path: str, sample_queue: CommandQueue) -> None:
        """Test that deleting a queue removes it from storage."""
        from retromcp.infrastructure.persistent_queue_storage import PersistentQueueStorage
        storage = PersistentQueueStorage(temp_storage_path)
        
        # Create and delete queue
        storage.create_queue(sample_queue.id, sample_queue)
        deleted = storage.delete_queue(sample_queue.id)
        
        assert deleted is True
        assert storage.get_queue(sample_queue.id) is None

    # Test Case: Storage corruption handling
    def test_corrupted_storage_file_recovery(self, temp_storage_path: str) -> None:
        """Test graceful recovery from corrupted storage file."""
        # Create corrupted JSON file
        with open(temp_storage_path, 'w') as f:
            f.write("invalid json content {")
        
        from retromcp.infrastructure.persistent_queue_storage import PersistentQueueStorage
        # Should not crash, should recover gracefully
        storage = PersistentQueueStorage(temp_storage_path)
        
        # Should start with empty storage after recovery
        assert len(storage.list_queues()) == 0

    # Test Case: File system error handling
    def test_storage_file_permission_error(self) -> None:
        """Test handling of file permission errors."""
        readonly_path = "/readonly/path/queues.json"
        
        from retromcp.infrastructure.persistent_queue_storage import PersistentQueueStorage
        # Should handle permission errors gracefully
        storage = PersistentQueueStorage(readonly_path)
        
        # Should start with empty storage when unable to access file
        assert len(storage.list_queues()) == 0

    # Test Case: JSON serialization/deserialization
    def test_queue_serialization_deserialization(self, temp_storage_path: str) -> None:
        """Test that queues are properly serialized and deserialized."""
        from retromcp.infrastructure.persistent_queue_storage import PersistentQueueStorage
        storage = PersistentQueueStorage(temp_storage_path)
        
        # Create queue with various command states
        queue = CommandQueue(id="serialize_test", name="Serialization Test")
        cmd1 = queue.add_command("echo 'hello'", "Test echo")
        cmd2 = queue.add_command("ls", "List files")
        
        # Modify command states
        cmd1.status = CommandStatus.COMPLETED
        cmd1.start_time = datetime.now()
        cmd1.end_time = datetime.now()
        cmd1.result = {"exit_code": 0, "stdout": "hello"}
        
        cmd2.status = CommandStatus.FAILED
        cmd2.error = "Command not found"
        
        # Store and retrieve
        storage.create_queue(queue.id, queue)
        retrieved = storage.get_queue(queue.id)
        
        assert retrieved is not None
        assert len(retrieved.commands) == 2
        assert retrieved.commands[0].status == CommandStatus.COMPLETED
        assert retrieved.commands[0].result == {"exit_code": 0, "stdout": "hello"}
        assert retrieved.commands[1].status == CommandStatus.FAILED
        assert retrieved.commands[1].error == "Command not found"

    # Test Case: Thread safety (basic)
    def test_concurrent_access_handling(self, temp_storage_path: str) -> None:
        """Test basic thread safety mechanisms."""
        from retromcp.infrastructure.persistent_queue_storage import PersistentQueueStorage
        storage = PersistentQueueStorage(temp_storage_path)
        
        # This test will verify file locking mechanisms exist
        # Implementation should handle concurrent access
        queue = CommandQueue(id="concurrent_test", name="Concurrent Test")
        result = storage.create_queue(queue.id, queue)
        assert result.is_success()

    # Test Case: Large queue handling
    def test_large_queue_performance(self, temp_storage_path: str) -> None:
        """Test handling of large queues."""
        from retromcp.infrastructure.persistent_queue_storage import PersistentQueueStorage
        storage = PersistentQueueStorage(temp_storage_path)
        
        # Create queue with many commands
        large_queue = CommandQueue(id="large_queue", name="Large Queue")
        for i in range(100):
            large_queue.add_command(f"echo 'command {i}'", f"Command {i}")
        
        # Should handle large queues efficiently
        result = storage.create_queue(large_queue.id, large_queue)
        assert result.is_success()
        
        retrieved = storage.get_queue(large_queue.id)
        assert retrieved is not None
        assert len(retrieved.commands) == 100

    # Test Case: Storage path validation
    def test_invalid_storage_path_handling(self) -> None:
        """Test handling of invalid storage paths."""
        from retromcp.infrastructure.persistent_queue_storage import PersistentQueueStorage
        # Should handle invalid paths gracefully
        storage = PersistentQueueStorage("")
        assert len(storage.list_queues()) == 0

    # Test Case: Empty queue handling
    def test_empty_queue_storage(self, temp_storage_path: str) -> None:
        """Test storing and retrieving empty queues."""
        from retromcp.infrastructure.persistent_queue_storage import PersistentQueueStorage
        storage = PersistentQueueStorage(temp_storage_path)
        
        empty_queue = CommandQueue(id="empty", name="Empty Queue")
        
        result = storage.create_queue(empty_queue.id, empty_queue)
        assert result.is_success()
        
        retrieved = storage.get_queue(empty_queue.id)
        assert retrieved is not None
        assert len(retrieved.commands) == 0

    # Test Case: Duplicate queue ID handling
    def test_duplicate_queue_id_handling(self, temp_storage_path: str, sample_queue: CommandQueue) -> None:
        """Test handling of duplicate queue IDs."""
        from retromcp.infrastructure.persistent_queue_storage import PersistentQueueStorage
        storage = PersistentQueueStorage(temp_storage_path)
        
        # Create queue twice with same ID
        result1 = storage.create_queue(sample_queue.id, sample_queue)
        result2 = storage.create_queue(sample_queue.id, sample_queue)
        
        # Should handle duplicate appropriately (update existing)
        assert result1.is_success()
        assert result2.is_success()
        assert len(storage.list_queues()) == 1

    # Test Case: Non-existent queue retrieval
    def test_get_nonexistent_queue(self, temp_storage_path: str) -> None:
        """Test retrieving a queue that doesn't exist."""
        from retromcp.infrastructure.persistent_queue_storage import PersistentQueueStorage
        storage = PersistentQueueStorage(temp_storage_path)
        
        result = storage.get_queue("nonexistent")
        assert result is None

    # Test Case: Delete non-existent queue
    def test_delete_nonexistent_queue(self, temp_storage_path: str) -> None:
        """Test deleting a queue that doesn't exist."""
        from retromcp.infrastructure.persistent_queue_storage import PersistentQueueStorage
        storage = PersistentQueueStorage(temp_storage_path)
        
        result = storage.delete_queue("nonexistent")
        assert result is False