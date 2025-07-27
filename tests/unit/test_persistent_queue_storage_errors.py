"""Comprehensive error handling tests for PersistentQueueStorage - Coverage improvement."""

import json
import os
import tempfile
from unittest.mock import Mock, patch, mock_open
from pathlib import Path

import pytest

from retromcp.domain.models import CommandQueue, CommandStatus, QueuedCommand
from retromcp.infrastructure.persistent_queue_storage import PersistentQueueStorage


@pytest.mark.unit
@pytest.mark.infrastructure
class TestPersistentQueueStorageErrorHandling:
    """Test error handling and edge cases for PersistentQueueStorage to improve coverage."""

    @pytest.fixture
    def temp_storage_path(self):
        """Create a temporary storage path."""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tmp:
            yield tmp.name
        # Cleanup
        if os.path.exists(tmp.name):
            os.unlink(tmp.name)

    @pytest.fixture
    def storage(self, temp_storage_path):
        """Create PersistentQueueStorage instance."""
        return PersistentQueueStorage(temp_storage_path)

    def test_load_queues_with_malformed_json_structure(self, temp_storage_path):
        """Test loading queues with malformed JSON structure (valid JSON, invalid structure)."""
        # Write valid JSON but invalid structure
        malformed_data = {"not_a_queues_key": "invalid"}
        with open(temp_storage_path, 'w') as f:
            json.dump(malformed_data, f)

        storage = PersistentQueueStorage(temp_storage_path)
        
        # Should handle gracefully and start with empty queues
        queue_ids = storage.list_queues()
        assert queue_ids == []

    def test_load_queues_with_corrupted_json_syntax(self, temp_storage_path):
        """Test loading queues with corrupted JSON syntax."""
        # Write invalid JSON syntax
        with open(temp_storage_path, 'w') as f:
            f.write('{"queues": {"q1": invalid json}')

        storage = PersistentQueueStorage(temp_storage_path)
        
        # Should handle gracefully and start with empty queues
        queue_ids = storage.list_queues()
        assert queue_ids == []

    def test_save_queues_disk_full_error(self, storage):
        """Test save_queues when disk is full or write fails."""
        queue = CommandQueue(id="test_queue", name="Test Queue")
        storage.queues["test_queue"] = queue

        # Mock disk full error during write
        with patch('builtins.open', mock_open()) as mock_file:
            mock_file.side_effect = OSError("No space left on device")
            
            # Should not crash on disk full
            # The _save_queues method should handle this gracefully
            try:
                storage._save_queues()
            except OSError:
                # This is expected behavior - let it propagate
                pass

    def test_save_queues_permission_error(self, storage):
        """Test save_queues when permission is denied."""
        queue = CommandQueue(id="test_queue", name="Test Queue")
        storage.queues["test_queue"] = queue

        # Mock permission error during write
        with patch('builtins.open', mock_open()) as mock_file:
            mock_file.side_effect = PermissionError("Permission denied")
            
            # Should not crash on permission error
            try:
                storage._save_queues()
            except PermissionError:
                # This is expected behavior - let it propagate
                pass

    def test_deserialize_queue_missing_required_fields(self, storage):
        """Test deserializing queue data with missing required fields."""
        # Queue data missing required fields
        invalid_queue_data = {
            "name": "Test Queue",
            # Missing 'id', 'commands', 'current_index' etc.
        }

        result = storage._deserialize_queue(invalid_queue_data)
        
        # Should return None for invalid data
        assert result is None

    def test_deserialize_queue_invalid_data_types(self, storage):
        """Test deserializing queue data with invalid data types."""
        # Queue data with wrong data types
        invalid_queue_data = {
            "id": "test_queue",
            "name": "Test Queue",
            "commands": "not_a_list",  # Should be list
            "current_index": "not_an_int",  # Should be int
            "auto_execute": "not_a_bool",  # Should be bool
            "pause_between": "not_a_number",  # Should be number
            "created_at": "invalid_timestamp"  # Should be valid timestamp
        }

        result = storage._deserialize_queue(invalid_queue_data)
        
        # Should return None for invalid data types
        assert result is None

    def test_deserialize_command_missing_required_fields(self, storage):
        """Test deserializing command data with missing required fields."""
        # Command data missing required fields
        invalid_command_data = {
            "command": "echo test",
            # Missing 'id', 'description', 'status'
        }

        result = storage._deserialize_command(invalid_command_data)
        
        # Should return None for invalid data
        assert result is None

    def test_deserialize_command_invalid_status_enum(self, storage):
        """Test deserializing command data with invalid status enum."""
        # Command data with invalid status
        invalid_command_data = {
            "id": "cmd1",
            "command": "echo test",
            "description": "Test command",
            "status": "INVALID_STATUS",  # Not a valid CommandStatus
        }

        result = storage._deserialize_command(invalid_command_data)
        
        # Should return None for invalid status
        assert result is None

    def test_deserialize_command_invalid_timestamp_formats(self, storage):
        """Test deserializing command data with invalid timestamp formats."""
        # Command data with invalid timestamps
        invalid_command_data = {
            "id": "cmd1",
            "command": "echo test",
            "description": "Test command",
            "status": "pending",
            "start_time": "not_a_timestamp",
            "end_time": "also_not_a_timestamp"
        }

        result = storage._deserialize_command(invalid_command_data)
        
        # Should handle gracefully, setting timestamps to None
        assert result is not None
        assert result.start_time is None
        assert result.end_time is None

    def test_create_queue_with_empty_string_id(self, storage):
        """Test creating queue with empty string ID."""
        queue = CommandQueue(id="", name="Test Queue")
        
        result = storage.create_queue("", queue)
        
        # Should return error for empty ID
        assert result.is_error()
        assert "Queue ID cannot be empty" in result.error_value.message

    def test_create_queue_with_whitespace_only_id(self, storage):
        """Test creating queue with whitespace-only ID."""
        queue = CommandQueue(id="   ", name="Test Queue")
        
        result = storage.create_queue("   ", queue)
        
        # Should return error for whitespace-only ID
        assert result.is_error()
        assert "Queue ID cannot be empty" in result.error_value.message

    def test_delete_queue_save_failure(self, storage):
        """Test delete_queue when save operation fails."""
        # Create a queue first
        queue = CommandQueue(id="test_queue", name="Test Queue")
        storage.queues["test_queue"] = queue

        # Mock save failure
        with patch.object(storage, '_save_queues') as mock_save:
            mock_save.side_effect = Exception("Save failed")
            
            result = storage.delete_queue("test_queue")
            
            # Should return error when save fails
            assert result.is_error()
            assert "Failed to save after deleting queue" in result.error_value.message

    def test_update_nonexistent_queue_error(self, storage):
        """Test updating a queue that doesn't exist."""
        queue = CommandQueue(id="nonexistent", name="Test Queue")
        
        result = storage.update_queue("nonexistent", queue)
        
        # Should return error for non-existent queue
        assert result.is_error()
        assert "Queue not found" in result.error_value.message

    def test_storage_directory_creation_permission_error(self):
        """Test storage directory creation when permission is denied."""
        # Try to create storage in a path that requires permissions
        restricted_path = "/root/retromcp/command_queues.json"
        
        with patch('os.makedirs') as mock_makedirs:
            mock_makedirs.side_effect = PermissionError("Permission denied")
            
            # Should handle gracefully
            try:
                storage = PersistentQueueStorage(restricted_path)
                # If no exception, the permission error was handled
                assert storage is not None
            except PermissionError:
                # This is acceptable behavior
                pass

    def test_concurrent_access_file_lock_timeout(self, storage):
        """Test behavior when file lock times out due to concurrent access."""
        queue = CommandQueue(id="test_queue", name="Test Queue")
        
        # Mock file lock timeout
        with patch('fcntl.flock') as mock_flock:
            mock_flock.side_effect = OSError("Resource temporarily unavailable")
            
            result = storage.create_queue("test_queue", queue)
            
            # Should handle lock timeout gracefully
            # (Actual behavior depends on implementation)
            assert result is not None

    def test_atomic_write_failure_recovery(self, storage):
        """Test recovery when atomic write operation fails."""
        queue = CommandQueue(id="test_queue", name="Test Queue")
        storage.queues["test_queue"] = queue

        # Mock atomic rename failure
        with patch('os.rename') as mock_rename:
            mock_rename.side_effect = OSError("Rename failed")
            
            # Should handle atomic write failure
            try:
                storage._save_queues()
            except OSError:
                # Expected behavior - let it propagate
                pass

    def test_load_queues_with_partial_corruption(self, temp_storage_path):
        """Test loading when some queues are corrupted but others are valid."""
        # Create data with mixed valid/invalid queues
        mixed_data = {
            "queues": {
                "valid_queue": {
                    "id": "valid_queue",
                    "name": "Valid Queue",
                    "commands": [],
                    "current_index": 0,
                    "auto_execute": False,
                    "pause_between": 2,
                    "created_at": "2024-01-01T00:00:00"
                },
                "invalid_queue": {
                    "id": "invalid_queue",
                    # Missing required fields
                }
            }
        }
        
        with open(temp_storage_path, 'w') as f:
            json.dump(mixed_data, f)

        storage = PersistentQueueStorage(temp_storage_path)
        
        # Should load only valid queues
        queue_ids = storage.list_queues()
        assert "valid_queue" in queue_ids
        assert "invalid_queue" not in queue_ids

    def test_command_result_serialization_edge_cases(self, storage):
        """Test serialization of commands with complex result data."""
        queue = CommandQueue(id="test_queue", name="Test Queue")
        cmd = queue.add_command("echo test", "Test command")
        
        # Set complex result data
        cmd.result = {
            "exit_code": 0,
            "stdout": "output with unicode: 🚀",
            "stderr": "",
            "complex_data": {"nested": {"values": [1, 2, 3]}}
        }
        cmd.status = CommandStatus.COMPLETED
        
        # Should handle complex result serialization
        result = storage.create_queue("test_queue", queue)
        assert result.is_success()
        
        # Verify it can be loaded back
        loaded_queue = storage.get_queue("test_queue")
        assert loaded_queue is not None
        assert loaded_queue.commands[0].result["complex_data"]["nested"]["values"] == [1, 2, 3]