"""Unit tests for Docker use cases with Result pattern."""

from unittest.mock import Mock

import pytest

from retromcp.application.docker_use_cases import ManageDockerUseCase
from retromcp.domain.models import ConnectionError
from retromcp.domain.models import DockerAction
from retromcp.domain.models import DockerContainer
from retromcp.domain.models import DockerManagementRequest
from retromcp.domain.models import DockerManagementResult
from retromcp.domain.models import DockerResource
from retromcp.domain.models import DockerVolume
from retromcp.domain.models import ExecutionError
from retromcp.domain.models import Result
from retromcp.domain.models import ValidationError
from retromcp.domain.ports import DockerRepository


class TestManageDockerUseCaseResult:
    """Test ManageDockerUseCase with Result pattern."""

    @pytest.fixture
    def mock_docker_repo(self):
        """Create mock Docker repository."""
        return Mock(spec=DockerRepository)

    @pytest.fixture
    def use_case(self, mock_docker_repo):
        """Create ManageDockerUseCase instance."""
        return ManageDockerUseCase(mock_docker_repo)

    # Success cases
    def test_execute_returns_result_success_when_docker_available_and_container_operation_succeeds(
        self, use_case, mock_docker_repo
    ):
        """Test that execute returns Result.success when Docker is available and container operation succeeds."""
        # Arrange
        request = DockerManagementRequest(
            resource=DockerResource.CONTAINER,
            action=DockerAction.PS,
            name=None,
        )

        # Mock Docker available
        mock_docker_repo.is_docker_available.return_value = True

        # Mock successful container listing
        containers = [
            DockerContainer(
                container_id="abc123def456",
                name="retropie-emulator",
                image="retropie/emulator:latest",
                status="Up 2 hours",
                created="2024-01-15 10:00:00",
                ports={"8080": "80"},
                command="/bin/bash",
            ),
            DockerContainer(
                container_id="789ghi012jkl",
                name="retropie-frontend",
                image="retropie/frontend:latest",
                status="Up 1 hour",
                created="2024-01-15 11:00:00",
                ports={"3000": "3000"},
                command="npm start",
            ),
        ]

        expected_result = DockerManagementResult(
            success=True,
            resource=DockerResource.CONTAINER,
            action=DockerAction.PS,
            message="Listed 2 containers",
            containers=containers,
        )
        mock_docker_repo.manage_containers.return_value = expected_result

        # Act
        result = use_case.execute(request)

        # Assert
        assert isinstance(result, Result)
        assert result.is_success()
        assert not result.is_error()
        assert result.value == expected_result
        assert result.value.success is True
        assert result.value.containers == containers
        assert len(result.value.containers) == 2

    def test_execute_returns_result_success_when_compose_operation_succeeds(
        self, use_case, mock_docker_repo
    ):
        """Test that execute returns Result.success when compose operation succeeds."""
        # Arrange
        request = DockerManagementRequest(
            resource=DockerResource.COMPOSE,
            action=DockerAction.UP,
            name="retropie-stack",
            compose_file="/home/pi/docker-compose.yml",
        )

        # Mock Docker available
        mock_docker_repo.is_docker_available.return_value = True

        # Mock successful compose up
        expected_result = DockerManagementResult(
            success=True,
            resource=DockerResource.COMPOSE,
            action=DockerAction.UP,
            message="Compose stack 'retropie-stack' started successfully",
            output="Creating network retropie_default\nCreating retropie_db_1\nCreating retropie_app_1",
        )
        mock_docker_repo.manage_compose.return_value = expected_result

        # Act
        result = use_case.execute(request)

        # Assert
        assert isinstance(result, Result)
        assert result.is_success()
        assert result.value == expected_result
        assert (
            result.value.message
            == "Compose stack 'retropie-stack' started successfully"
        )

    def test_execute_returns_result_success_when_volume_operation_succeeds(
        self, use_case, mock_docker_repo
    ):
        """Test that execute returns Result.success when volume operation succeeds."""
        # Arrange
        request = DockerManagementRequest(
            resource=DockerResource.VOLUME,
            action=DockerAction.LIST,
        )

        # Mock Docker available
        mock_docker_repo.is_docker_available.return_value = True

        # Mock successful volume listing
        volumes = [
            DockerVolume(
                name="retropie_roms",
                driver="local",
                mountpoint="/var/lib/docker/volumes/retropie_roms/_data",
                created="2024-01-15T10:00:00Z",
                labels={"type": "roms", "size": "1.5GB"},
            ),
            DockerVolume(
                name="retropie_saves",
                driver="local",
                mountpoint="/var/lib/docker/volumes/retropie_saves/_data",
                created="2024-01-14T09:00:00Z",
                labels={"type": "saves", "size": "256MB"},
            ),
        ]

        expected_result = DockerManagementResult(
            success=True,
            resource=DockerResource.VOLUME,
            action=DockerAction.LIST,
            message="Listed 2 volumes",
            volumes=volumes,
        )
        mock_docker_repo.manage_volumes.return_value = expected_result

        # Act
        result = use_case.execute(request)

        # Assert
        assert isinstance(result, Result)
        assert result.is_success()
        assert result.value == expected_result
        assert len(result.value.volumes) == 2

    # Error cases
    def test_execute_returns_result_error_when_docker_not_available(
        self, use_case, mock_docker_repo
    ):
        """Test that execute returns Result.error when Docker is not available."""
        # Arrange
        request = DockerManagementRequest(
            resource=DockerResource.CONTAINER,
            action=DockerAction.PS,
        )

        # Mock Docker not available
        mock_docker_repo.is_docker_available.return_value = False

        # Act
        result = use_case.execute(request)

        # Assert
        assert isinstance(result, Result)
        assert not result.is_success()
        assert result.is_error()
        assert isinstance(result.error_or_none, ValidationError)
        assert result.error_or_none.code == "DOCKER_NOT_AVAILABLE"
        assert "Docker is not available" in result.error_or_none.message

    def test_execute_returns_result_error_when_invalid_resource_type(
        self, use_case, mock_docker_repo
    ):
        """Test that execute returns Result.error for invalid resource type."""
        # Arrange
        # Create a request with invalid resource type (mocking an edge case)
        request = Mock(spec=DockerManagementRequest)
        request.resource = "invalid_resource"  # Not a valid DockerResource
        request.action = DockerAction.PS

        # Mock Docker available
        mock_docker_repo.is_docker_available.return_value = True

        # Act
        result = use_case.execute(request)

        # Assert
        assert isinstance(result, Result)
        assert result.is_error()
        assert isinstance(result.error_or_none, ValidationError)
        assert result.error_or_none.code == "UNSUPPORTED_RESOURCE_TYPE"
        assert "Unsupported resource type" in result.error_or_none.message

    def test_execute_returns_result_error_when_container_operation_fails(
        self, use_case, mock_docker_repo
    ):
        """Test that execute returns Result.error when container operation fails."""
        # Arrange
        request = DockerManagementRequest(
            resource=DockerResource.CONTAINER,
            action=DockerAction.STOP,
            name="non-existent-container",
        )

        # Mock Docker available
        mock_docker_repo.is_docker_available.return_value = True

        # Mock container operation failure
        mock_docker_repo.manage_containers.side_effect = RuntimeError(
            "Error response from daemon: No such container: non-existent-container"
        )

        # Act
        result = use_case.execute(request)

        # Assert
        assert isinstance(result, Result)
        assert result.is_error()
        assert isinstance(result.error_or_none, ExecutionError)
        assert result.error_or_none.code == "DOCKER_OPERATION_FAILED"
        assert "Failed to execute Docker operation" in result.error_or_none.message

    def test_execute_returns_result_error_when_docker_check_fails(
        self, use_case, mock_docker_repo
    ):
        """Test that execute returns Result.error when Docker availability check fails."""
        # Arrange
        request = DockerManagementRequest(
            resource=DockerResource.CONTAINER,
            action=DockerAction.PS,
        )

        # Mock Docker availability check failure
        mock_docker_repo.is_docker_available.side_effect = OSError(
            "Cannot connect to Docker daemon"
        )

        # Act
        result = use_case.execute(request)

        # Assert
        assert isinstance(result, Result)
        assert result.is_error()
        assert isinstance(result.error_or_none, ConnectionError)
        assert result.error_or_none.code == "DOCKER_CONNECTION_FAILED"
        assert "Failed to connect to Docker" in result.error_or_none.message

    def test_execute_returns_result_error_when_compose_operation_fails(
        self, use_case, mock_docker_repo
    ):
        """Test that execute returns Result.error when compose operation fails."""
        # Arrange
        request = DockerManagementRequest(
            resource=DockerResource.COMPOSE,
            action=DockerAction.DOWN,
            name="failing-stack",
        )

        # Mock Docker available
        mock_docker_repo.is_docker_available.return_value = True

        # Mock compose operation failure
        mock_docker_repo.manage_compose.side_effect = Exception(
            "docker-compose.yml not found"
        )

        # Act
        result = use_case.execute(request)

        # Assert
        assert isinstance(result, Result)
        assert result.is_error()
        assert isinstance(result.error_or_none, ExecutionError)
        assert result.error_or_none.code == "DOCKER_OPERATION_FAILED"

    def test_execute_returns_result_error_when_volume_operation_fails(
        self, use_case, mock_docker_repo
    ):
        """Test that execute returns Result.error when volume operation fails."""
        # Arrange
        request = DockerManagementRequest(
            resource=DockerResource.VOLUME,
            action=DockerAction.CREATE,
            name="invalid/volume/name",
        )

        # Mock Docker available
        mock_docker_repo.is_docker_available.return_value = True

        # Mock volume operation failure
        mock_docker_repo.manage_volumes.side_effect = ValueError("Invalid volume name")

        # Act
        result = use_case.execute(request)

        # Assert
        assert isinstance(result, Result)
        assert result.is_error()
        assert isinstance(result.error_or_none, ExecutionError)
        assert result.error_or_none.code == "DOCKER_OPERATION_FAILED"

    # Edge cases
    def test_execute_handles_empty_container_list(self, use_case, mock_docker_repo):
        """Test that execute handles empty container list correctly."""
        # Arrange
        request = DockerManagementRequest(
            resource=DockerResource.CONTAINER,
            action=DockerAction.PS,
        )

        # Mock Docker available
        mock_docker_repo.is_docker_available.return_value = True

        # Mock empty container list
        expected_result = DockerManagementResult(
            success=True,
            resource=DockerResource.CONTAINER,
            action=DockerAction.PS,
            message="No containers found",
            containers=[],
        )
        mock_docker_repo.manage_containers.return_value = expected_result

        # Act
        result = use_case.execute(request)

        # Assert
        assert isinstance(result, Result)
        assert result.is_success()
        assert result.value.containers == []
        assert result.value.message == "No containers found"
