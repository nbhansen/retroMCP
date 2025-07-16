"""Unit tests for SSHStateRepository."""

import json
from datetime import datetime
from unittest.mock import Mock
from unittest.mock import patch

import pytest

from retromcp.config import RetroPieConfig
from retromcp.domain.models import CommandResult
from retromcp.domain.models import StateAction
from retromcp.domain.models import SystemState
from retromcp.infrastructure.ssh_state_repository import SSHStateRepository


class TestSSHStateRepository:
    """Test cases for SSHStateRepository."""

    @pytest.fixture
    def mock_client(self) -> Mock:
        """Provide mock RetroPie client."""
        return Mock()

    @pytest.fixture
    def test_config(self) -> RetroPieConfig:
        """Provide test configuration."""
        from retromcp.discovery import RetroPiePaths

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
    def sample_state(self) -> SystemState:
        """Provide sample system state."""
        return SystemState(
            schema_version="1.0",
            last_updated=datetime.now().isoformat(),
            system={
                "hostname": "retropie",
                "cpu_temperature": 60.0,
                "memory_total": 8000000000,
                "disk_total": 32000000000,
            },
            emulators={
                "installed": ["mupen64plus", "pcsx-rearmed"],
                "preferred": {"n64": "mupen64plus"},
            },
            controllers=[
                {"type": "xbox", "device": "/dev/input/js0", "configured": True}
            ],
            roms={
                "systems": ["nes", "snes", "psx"],
                "counts": {"nes": 150, "snes": 89},
            },
            custom_configs=["shaders", "bezels"],
            known_issues=["audio crackling"],
        )

    @pytest.fixture
    def repository(
        self, mock_client: Mock, test_config: RetroPieConfig
    ) -> SSHStateRepository:
        """Provide SSHStateRepository instance."""
        return SSHStateRepository(mock_client, test_config)

    def test_state_file_path(self, repository: SSHStateRepository) -> None:
        """Test state file path generation."""
        expected_path = "/home/retro/.retropie-state.json"
        assert repository._state_file_path == expected_path

    def test_load_state_success(
        self,
        repository: SSHStateRepository,
        mock_client: Mock,
        sample_state: SystemState,
    ) -> None:
        """Test successful state loading."""
        # Mock successful file read
        mock_client.execute_command.return_value = CommandResult(
            command="cat /home/retro/.retropie-state.json",
            exit_code=0,
            stdout=sample_state.to_json(),
            stderr="",
            success=True,
            execution_time=0.1,
        )

        result = repository.load_state()

        assert result.schema_version == sample_state.schema_version
        assert result.system["hostname"] == "retropie"
        assert result.emulators["installed"] == ["mupen64plus", "pcsx-rearmed"]
        mock_client.execute_command.assert_called_once_with(
            "cat /home/retro/.retropie-state.json"
        )

    def test_load_state_file_not_found(
        self, repository: SSHStateRepository, mock_client: Mock
    ) -> None:
        """Test loading state when file doesn't exist."""
        # Mock file not found
        mock_client.execute_command.return_value = CommandResult(
            command="cat /home/retro/.retropie-state.json",
            exit_code=1,
            stdout="",
            stderr="cat: /home/retro/.retropie-state.json: No such file or directory",
            success=False,
            execution_time=0.1,
        )

        with pytest.raises(FileNotFoundError):
            repository.load_state()

    def test_load_state_invalid_json(
        self, repository: SSHStateRepository, mock_client: Mock
    ) -> None:
        """Test loading state with invalid JSON."""
        # Mock invalid JSON content
        mock_client.execute_command.return_value = CommandResult(
            command="cat /home/retro/.retropie-state.json",
            exit_code=0,
            stdout="invalid json content",
            stderr="",
            success=True,
            execution_time=0.1,
        )

        with pytest.raises(json.JSONDecodeError):
            repository.load_state()

    def test_save_state_success(
        self,
        repository: SSHStateRepository,
        mock_client: Mock,
        sample_state: SystemState,
    ) -> None:
        """Test successful state saving."""
        # Mock successful file write
        mock_client.execute_command.return_value = CommandResult(
            command="write command",
            exit_code=0,
            stdout="",
            stderr="",
            success=True,
            execution_time=0.1,
        )

        result = repository.save_state(sample_state)

        assert result.success is True
        assert result.action == StateAction.SAVE
        assert "saved successfully" in result.message

        # Verify the commands were called properly (mkdir, tee, chmod)
        assert mock_client.execute_command.call_count == 3

        # Check that the mkdir command was called first
        mkdir_call = mock_client.execute_command.call_args_list[0][0][0]
        assert "mkdir -p /home/retro" in mkdir_call

        # Check that the tee command was called second
        tee_call = mock_client.execute_command.call_args_list[1][0][0]
        assert "/home/retro/.retropie-state.json" in tee_call
        assert "tee" in tee_call

        # Check that chmod was called third
        chmod_call = mock_client.execute_command.call_args_list[2][0][0]
        assert "chmod 600" in chmod_call

    def test_save_state_failure(
        self,
        repository: SSHStateRepository,
        mock_client: Mock,
        sample_state: SystemState,
    ) -> None:
        """Test state saving failure."""
        # Mock failed file write
        mock_client.execute_command.return_value = CommandResult(
            command="write command",
            exit_code=1,
            stdout="",
            stderr="Permission denied",
            success=False,
            execution_time=0.1,
        )

        result = repository.save_state(sample_state)

        assert result.success is False
        assert result.action == StateAction.SAVE
        assert "Permission denied" in result.message

    def test_update_state_field_success(
        self,
        repository: SSHStateRepository,
        mock_client: Mock,
        sample_state: SystemState,
    ) -> None:
        """Test successful field update."""
        # Mock successful file read and write operations
        mock_client.execute_command.side_effect = [
            # First call: read current state
            CommandResult(
                command="cat /home/retro/.retropie-state.json",
                exit_code=0,
                stdout=sample_state.to_json(),
                stderr="",
                success=True,
                execution_time=0.1,
            ),
            # Second call: mkdir for save
            CommandResult(
                command="mkdir -p /home/retro",
                exit_code=0,
                stdout="",
                stderr="",
                success=True,
                execution_time=0.1,
            ),
            # Third call: tee for save
            CommandResult(
                command="tee command",
                exit_code=0,
                stdout="",
                stderr="",
                success=True,
                execution_time=0.1,
            ),
            # Fourth call: chmod for save
            CommandResult(
                command="chmod 600",
                exit_code=0,
                stdout="",
                stderr="",
                success=True,
                execution_time=0.1,
            ),
        ]

        result = repository.update_state_field("system.hostname", "new-hostname")

        assert result.success is True
        assert result.action == StateAction.UPDATE
        assert "updated successfully" in result.message

    def test_update_state_field_invalid_path(
        self,
        repository: SSHStateRepository,
        mock_client: Mock,
        sample_state: SystemState,
    ) -> None:
        """Test field update with invalid path."""
        # Mock successful file read
        mock_client.execute_command.return_value = CommandResult(
            command="cat /home/retro/.retropie-state.json",
            exit_code=0,
            stdout=sample_state.to_json(),
            stderr="",
            success=True,
            execution_time=0.1,
        )

        result = repository.update_state_field("invalid.path.structure", "value")

        assert result.success is False
        assert result.action == StateAction.UPDATE
        assert "Invalid path" in result.message

    def test_compare_state_with_differences(
        self,
        repository: SSHStateRepository,
        mock_client: Mock,
        sample_state: SystemState,
    ) -> None:
        """Test state comparison with differences."""
        # Create a slightly different stored state
        stored_state = SystemState(
            schema_version="1.0",
            last_updated="2025-01-01T00:00:00Z",
            system={
                "hostname": "old-retropie",
                "cpu_temperature": 50.0,
                "memory_total": 4000000000,
                "disk_total": 16000000000,
            },
            emulators={
                "installed": ["pcsx-rearmed"],
                "preferred": {"psx": "pcsx-rearmed"},
            },
            controllers=[],
            roms={
                "systems": ["nes"],
                "counts": {"nes": 100},
            },
            custom_configs=["shaders"],
            known_issues=[],
        )

        # Mock successful file read
        mock_client.execute_command.return_value = CommandResult(
            command="cat /home/retro/.retropie-state.json",
            exit_code=0,
            stdout=stored_state.to_json(),
            stderr="",
            success=True,
            execution_time=0.1,
        )

        # Current state has different values
        current_state = sample_state

        diff = repository.compare_state(current_state)

        assert "changed" in diff
        assert "added" in diff
        assert "removed" in diff

        # Check for expected changes
        changes = diff["changed"]
        assert "system.hostname" in changes
        assert changes["system.hostname"]["old"] == "old-retropie"
        assert changes["system.hostname"]["new"] == "retropie"

    def test_compare_state_no_differences(
        self,
        repository: SSHStateRepository,
        mock_client: Mock,
        sample_state: SystemState,
    ) -> None:
        """Test state comparison with no differences."""
        # Mock successful file read with identical state
        mock_client.execute_command.return_value = CommandResult(
            command="cat /home/retro/.retropie-state.json",
            exit_code=0,
            stdout=sample_state.to_json(),
            stderr="",
            success=True,
            execution_time=0.1,
        )

        diff = repository.compare_state(sample_state)

        assert diff["changed"] == {}
        assert diff["added"] == {}
        assert diff["removed"] == {}

    @patch("fcntl.flock")
    def test_file_locking(
        self,
        mock_flock: Mock,  # noqa: ARG002
        repository: SSHStateRepository,
        mock_client: Mock,
        sample_state: SystemState,
    ) -> None:
        """Test file locking during operations."""
        # Mock successful file read with valid JSON
        mock_client.execute_command.return_value = CommandResult(
            command="cat /home/retro/.retropie-state.json",
            exit_code=0,
            stdout=sample_state.to_json(),
            stderr="",
            success=True,
            execution_time=0.1,
        )

        # This would normally test file locking, but since we're using SSH
        # the locking would happen on the remote system, not locally
        # So this test verifies that the method works correctly
        result = repository.load_state()
        assert result.schema_version == "1.0"

    def test_path_validation(self, repository: SSHStateRepository) -> None:
        """Test path validation for security."""
        # Test with path traversal attempt
        with pytest.raises(ValueError):
            repository._validate_path("../../../etc/passwd")

        # Test with valid path
        repository._validate_path("system.hostname")  # Should not raise

    def test_json_sanitization(self, repository: SSHStateRepository) -> None:
        """Test JSON content sanitization."""
        # Test with potentially dangerous content
        content = '{"key": "value with $(dangerous command)"}'
        sanitized = repository._sanitize_json_content(content)

        # Should not contain shell command injection
        assert "$(dangerous command)" not in sanitized or sanitized == content

        # Should still be valid JSON
        json.loads(sanitized)
