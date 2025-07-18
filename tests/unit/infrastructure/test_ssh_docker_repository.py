"""Unit tests for SSH Docker repository."""

import json
from unittest.mock import Mock

import pytest

from retromcp.domain.models import CommandResult
from retromcp.domain.models import DockerAction
from retromcp.domain.models import DockerManagementRequest
from retromcp.domain.models import DockerResource
from retromcp.domain.ports import RetroPieClient
from retromcp.infrastructure.ssh_docker_repository import SSHDockerRepository


@pytest.mark.unit
@pytest.mark.infrastructure
@pytest.mark.ssh_repos
@pytest.mark.docker_repo
class TestSSHDockerRepository:
    """Test cases for SSH Docker repository."""

    @pytest.fixture
    def mock_client(self) -> Mock:
        """Create mock RetroPie client."""
        return Mock(spec=RetroPieClient)

    @pytest.fixture
    def repository(self, mock_client: Mock) -> SSHDockerRepository:
        """Create SSH Docker repository instance."""
        return SSHDockerRepository(mock_client)

    def test_initialization(self, mock_client: Mock) -> None:
        """Test repository initialization."""
        repo = SSHDockerRepository(mock_client)
        assert repo.client == mock_client

    def test_is_docker_available_success(
        self, repository: SSHDockerRepository, mock_client: Mock
    ) -> None:
        """Test successful Docker availability check."""
        mock_client.execute_command.return_value = CommandResult(
            command="docker --version",
            exit_code=0,
            stdout="Docker version 20.10.7, build f0df350",
            stderr="",
            success=True,
            execution_time=0.1,
        )

        result = repository.is_docker_available()

        assert result is True
        mock_client.execute_command.assert_called_once_with("docker --version")

    def test_is_docker_available_command_failure(
        self, repository: SSHDockerRepository, mock_client: Mock
    ) -> None:
        """Test Docker availability check when command fails."""
        mock_client.execute_command.return_value = CommandResult(
            command="docker --version",
            exit_code=1,
            stdout="",
            stderr="docker: command not found",
            success=False,
            execution_time=0.1,
        )

        result = repository.is_docker_available()

        assert result is False

    def test_is_docker_available_no_docker_version_in_output(
        self, repository: SSHDockerRepository, mock_client: Mock
    ) -> None:
        """Test Docker availability check when output doesn't contain 'Docker version'."""
        mock_client.execute_command.return_value = CommandResult(
            command="docker --version",
            exit_code=0,
            stdout="Some other output",
            stderr="",
            success=True,
            execution_time=0.1,
        )

        result = repository.is_docker_available()

        assert result is False

    def test_is_docker_available_exception(
        self, repository: SSHDockerRepository, mock_client: Mock
    ) -> None:
        """Test Docker availability check when exception occurs."""
        mock_client.execute_command.side_effect = Exception("Connection error")

        result = repository.is_docker_available()

        assert result is False

    def test_pull_image_success(
        self, repository: SSHDockerRepository, mock_client: Mock
    ) -> None:
        """Test successful image pull."""
        mock_client.execute_command.return_value = CommandResult(
            command="docker pull nginx:latest",
            exit_code=0,
            stdout="latest: Pulling from library/nginx\nPull complete",
            stderr="",
            success=True,
            execution_time=5.0,
        )

        request = DockerManagementRequest(
            resource=DockerResource.CONTAINER,
            action=DockerAction.PULL,
            image="nginx:latest",
        )

        result = repository.manage_containers(request)

        assert result.success is True
        assert result.resource == DockerResource.CONTAINER
        assert result.action == DockerAction.PULL
        assert "Pull image nginx:latest: Success" in result.message
        assert result.output == "latest: Pulling from library/nginx\nPull complete"
        mock_client.execute_command.assert_called_once_with("docker pull nginx:latest")

    def test_pull_image_failure(
        self, repository: SSHDockerRepository, mock_client: Mock
    ) -> None:
        """Test failed image pull."""
        mock_client.execute_command.return_value = CommandResult(
            command="docker pull nonexistent:latest",
            exit_code=1,
            stdout="",
            stderr="Error response from daemon: pull access denied",
            success=False,
            execution_time=2.0,
        )

        request = DockerManagementRequest(
            resource=DockerResource.CONTAINER,
            action=DockerAction.PULL,
            image="nonexistent:latest",
        )

        result = repository.manage_containers(request)

        assert result.success is False
        assert result.resource == DockerResource.CONTAINER
        assert result.action == DockerAction.PULL
        assert (
            "Pull image nonexistent:latest: Error response from daemon: pull access denied"
            in result.message
        )
        assert result.output == "Error response from daemon: pull access denied"

    def test_pull_image_no_image_name(
        self,
        repository: SSHDockerRepository,
        mock_client: Mock,  # noqa: ARG002  # noqa: ARG002
    ) -> None:
        """Test pull action without image name."""
        request = DockerManagementRequest(
            resource=DockerResource.CONTAINER,
            action=DockerAction.PULL,
        )

        result = repository.manage_containers(request)

        assert result.success is False
        assert result.resource == DockerResource.CONTAINER
        assert result.action == DockerAction.PULL
        assert result.message == "Image name is required for pull action"

    def test_run_container_success(
        self, repository: SSHDockerRepository, mock_client: Mock
    ) -> None:
        """Test successful container run."""
        mock_client.execute_command.return_value = CommandResult(
            command="docker run -d --name test-container nginx:latest",
            exit_code=0,
            stdout="abc123def456",
            stderr="",
            success=True,
            execution_time=2.0,
        )

        request = DockerManagementRequest(
            resource=DockerResource.CONTAINER,
            action=DockerAction.RUN,
            image="nginx:latest",
            name="test-container",
            detach=True,
        )

        result = repository.manage_containers(request)

        assert result.success is True
        assert result.resource == DockerResource.CONTAINER
        assert result.action == DockerAction.RUN
        assert "Run container: Success" in result.message
        assert result.output == "abc123def456"
        mock_client.execute_command.assert_called_once_with(
            "docker run -d --name test-container nginx:latest"
        )

    def test_run_container_with_all_options(
        self, repository: SSHDockerRepository, mock_client: Mock
    ) -> None:
        """Test running container with all options."""
        mock_client.execute_command.return_value = CommandResult(
            command="docker run -d --rm --name app -p 8080:80 -e ENV_VAR=value -v /host:/container nginx:latest /bin/bash -c start",
            exit_code=0,
            stdout="container-id",
            stderr="",
            success=True,
            execution_time=1.0,
        )

        request = DockerManagementRequest(
            resource=DockerResource.CONTAINER,
            action=DockerAction.RUN,
            image="nginx:latest",
            name="app",
            detach=True,
            remove_on_exit=True,
            ports={"8080": "80"},
            environment={"ENV_VAR": "value"},
            volumes={"/host": "/container"},
            command="/bin/bash -c start",
        )

        result = repository.manage_containers(request)

        assert result.success is True
        expected_cmd = "docker run -d --rm --name app -p 8080:80 -e ENV_VAR=value -v /host:/container nginx:latest /bin/bash -c start"
        mock_client.execute_command.assert_called_once_with(expected_cmd)

    def test_run_container_no_image_name(
        self,
        repository: SSHDockerRepository,
        mock_client: Mock,  # noqa: ARG002
    ) -> None:
        """Test run action without image name."""
        request = DockerManagementRequest(
            resource=DockerResource.CONTAINER,
            action=DockerAction.RUN,
        )

        result = repository.manage_containers(request)

        assert result.success is False
        assert result.resource == DockerResource.CONTAINER
        assert result.action == DockerAction.RUN
        assert result.message == "Image name is required for run action"

    def test_run_container_failure(
        self, repository: SSHDockerRepository, mock_client: Mock
    ) -> None:
        """Test failed container run."""
        mock_client.execute_command.return_value = CommandResult(
            command="docker run nginx:latest",
            exit_code=1,
            stdout="",
            stderr="docker: Error running container",
            success=False,
            execution_time=1.0,
        )

        request = DockerManagementRequest(
            resource=DockerResource.CONTAINER,
            action=DockerAction.RUN,
            image="nginx:latest",
        )

        result = repository.manage_containers(request)

        assert result.success is False
        assert result.output == "docker: Error running container"

    def test_list_containers_success(
        self, repository: SSHDockerRepository, mock_client: Mock
    ) -> None:
        """Test successful container listing."""
        mock_output = "abc123\ttest-container\tnginx:latest\tUp 2 hours\t2023-01-01 10:00:00\t0.0.0.0:8080->80/tcp\t/docker-entrypoint.sh\n"
        mock_output += "def456\tapp\tredis:alpine\tExited (0) 1 hour ago\t2023-01-01 09:00:00\t<no value>\tredis-server"

        mock_client.execute_command.return_value = CommandResult(
            command="docker ps -a --format '{{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.CreatedAt}}\t{{.Ports}}\t{{.Command}}'",
            exit_code=0,
            stdout=mock_output,
            stderr="",
            success=True,
            execution_time=1.0,
        )

        request = DockerManagementRequest(
            resource=DockerResource.CONTAINER,
            action=DockerAction.PS,
        )

        result = repository.manage_containers(request)

        assert result.success is True
        assert result.resource == DockerResource.CONTAINER
        assert result.action == DockerAction.PS
        assert result.message == "Found 2 containers"
        assert result.containers is not None
        assert len(result.containers) == 2

        # Check first container
        container1 = result.containers[0]
        assert container1.container_id == "abc123"
        assert container1.name == "test-container"
        assert container1.image == "nginx:latest"
        assert container1.status == "Up 2 hours"
        assert container1.created == "2023-01-01 10:00:00"
        assert container1.ports == {"8080": "80"}
        assert container1.command == "/docker-entrypoint.sh"

        # Check second container
        container2 = result.containers[1]
        assert container2.container_id == "def456"
        assert container2.name == "app"
        assert container2.ports == {}

    def test_list_containers_command_failure(
        self, repository: SSHDockerRepository, mock_client: Mock
    ) -> None:
        """Test container listing when command fails."""
        mock_client.execute_command.return_value = CommandResult(
            command="docker ps -a --format '{{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.CreatedAt}}\t{{.Ports}}\t{{.Command}}'",
            exit_code=1,
            stdout="",
            stderr="Cannot connect to Docker daemon",
            success=False,
            execution_time=0.5,
        )

        request = DockerManagementRequest(
            resource=DockerResource.CONTAINER,
            action=DockerAction.PS,
        )

        result = repository.manage_containers(request)

        assert result.success is False
        assert result.resource == DockerResource.CONTAINER
        assert result.action == DockerAction.PS
        assert (
            "Failed to list containers: Cannot connect to Docker daemon"
            in result.message
        )

    def test_list_containers_malformed_output(
        self, repository: SSHDockerRepository, mock_client: Mock
    ) -> None:
        """Test container listing with malformed output."""
        mock_client.execute_command.return_value = CommandResult(
            command="docker ps -a --format '{{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.CreatedAt}}\t{{.Ports}}\t{{.Command}}'",
            exit_code=0,
            stdout="incomplete\tdata\n\nonly\ttwo\tcolumns",
            stderr="",
            success=True,
            execution_time=1.0,
        )

        request = DockerManagementRequest(
            resource=DockerResource.CONTAINER,
            action=DockerAction.PS,
        )

        result = repository.manage_containers(request)

        assert result.success is True
        assert result.containers is not None
        assert len(result.containers) == 0  # Malformed lines are skipped

    def test_stop_container_success(
        self, repository: SSHDockerRepository, mock_client: Mock
    ) -> None:
        """Test successful container stop."""
        mock_client.execute_command.return_value = CommandResult(
            command="docker stop test-container",
            exit_code=0,
            stdout="test-container",
            stderr="",
            success=True,
            execution_time=1.0,
        )

        request = DockerManagementRequest(
            resource=DockerResource.CONTAINER,
            action=DockerAction.STOP,
            name="test-container",
        )

        result = repository.manage_containers(request)

        assert result.success is True
        assert result.resource == DockerResource.CONTAINER
        assert result.action == DockerAction.STOP
        assert "Stop container test-container: Success" in result.message
        assert result.output == "test-container"
        mock_client.execute_command.assert_called_once_with(
            "docker stop test-container"
        )

    def test_stop_container_no_name(
        self,
        repository: SSHDockerRepository,
        mock_client: Mock,  # noqa: ARG002
    ) -> None:
        """Test stop action without container name."""
        request = DockerManagementRequest(
            resource=DockerResource.CONTAINER,
            action=DockerAction.STOP,
        )

        result = repository.manage_containers(request)

        assert result.success is False
        assert result.resource == DockerResource.CONTAINER
        assert result.action == DockerAction.STOP
        assert result.message == "Container name is required for stop action"

    def test_stop_container_failure(
        self, repository: SSHDockerRepository, mock_client: Mock
    ) -> None:
        """Test failed container stop."""
        mock_client.execute_command.return_value = CommandResult(
            command="docker stop nonexistent",
            exit_code=1,
            stdout="",
            stderr="No such container: nonexistent",
            success=False,
            execution_time=0.5,
        )

        request = DockerManagementRequest(
            resource=DockerResource.CONTAINER,
            action=DockerAction.STOP,
            name="nonexistent",
        )

        result = repository.manage_containers(request)

        assert result.success is False
        assert result.output == "No such container: nonexistent"

    def test_start_container_success(
        self, repository: SSHDockerRepository, mock_client: Mock
    ) -> None:
        """Test successful container start."""
        mock_client.execute_command.return_value = CommandResult(
            command="docker start test-container",
            exit_code=0,
            stdout="test-container",
            stderr="",
            success=True,
            execution_time=1.0,
        )

        request = DockerManagementRequest(
            resource=DockerResource.CONTAINER,
            action=DockerAction.START,
            name="test-container",
        )

        result = repository.manage_containers(request)

        assert result.success is True
        assert result.resource == DockerResource.CONTAINER
        assert result.action == DockerAction.START
        assert "Start container test-container: Success" in result.message
        assert result.output == "test-container"
        mock_client.execute_command.assert_called_once_with(
            "docker start test-container"
        )

    def test_start_container_no_name(
        self,
        repository: SSHDockerRepository,
        mock_client: Mock,  # noqa: ARG002
    ) -> None:
        """Test start action without container name."""
        request = DockerManagementRequest(
            resource=DockerResource.CONTAINER,
            action=DockerAction.START,
        )

        result = repository.manage_containers(request)

        assert result.success is False
        assert result.resource == DockerResource.CONTAINER
        assert result.action == DockerAction.START
        assert result.message == "Container name is required for start action"

    def test_start_container_failure(
        self, repository: SSHDockerRepository, mock_client: Mock
    ) -> None:
        """Test failed container start."""
        mock_client.execute_command.return_value = CommandResult(
            command="docker start nonexistent",
            exit_code=1,
            stdout="",
            stderr="No such container: nonexistent",
            success=False,
            execution_time=0.5,
        )

        request = DockerManagementRequest(
            resource=DockerResource.CONTAINER,
            action=DockerAction.START,
            name="nonexistent",
        )

        result = repository.manage_containers(request)

        assert result.success is False
        assert result.output == "No such container: nonexistent"

    def test_restart_container_success(
        self, repository: SSHDockerRepository, mock_client: Mock
    ) -> None:
        """Test successful container restart."""
        mock_client.execute_command.return_value = CommandResult(
            command="docker restart test-container",
            exit_code=0,
            stdout="test-container",
            stderr="",
            success=True,
            execution_time=2.0,
        )

        request = DockerManagementRequest(
            resource=DockerResource.CONTAINER,
            action=DockerAction.RESTART,
            name="test-container",
        )

        result = repository.manage_containers(request)

        assert result.success is True
        assert result.resource == DockerResource.CONTAINER
        assert result.action == DockerAction.RESTART
        assert "Restart container test-container: Success" in result.message
        assert result.output == "test-container"
        mock_client.execute_command.assert_called_once_with(
            "docker restart test-container"
        )

    def test_restart_container_no_name(
        self,
        repository: SSHDockerRepository,
        mock_client: Mock,  # noqa: ARG002
    ) -> None:
        """Test restart action without container name."""
        request = DockerManagementRequest(
            resource=DockerResource.CONTAINER,
            action=DockerAction.RESTART,
        )

        result = repository.manage_containers(request)

        assert result.success is False
        assert result.resource == DockerResource.CONTAINER
        assert result.action == DockerAction.RESTART
        assert result.message == "Container name is required for restart action"

    def test_restart_container_failure(
        self, repository: SSHDockerRepository, mock_client: Mock
    ) -> None:
        """Test failed container restart."""
        mock_client.execute_command.return_value = CommandResult(
            command="docker restart nonexistent",
            exit_code=1,
            stdout="",
            stderr="No such container: nonexistent",
            success=False,
            execution_time=0.5,
        )

        request = DockerManagementRequest(
            resource=DockerResource.CONTAINER,
            action=DockerAction.RESTART,
            name="nonexistent",
        )

        result = repository.manage_containers(request)

        assert result.success is False
        assert result.output == "No such container: nonexistent"

    def test_remove_container_success(
        self, repository: SSHDockerRepository, mock_client: Mock
    ) -> None:
        """Test successful container removal."""
        mock_client.execute_command.return_value = CommandResult(
            command="docker rm test-container",
            exit_code=0,
            stdout="test-container",
            stderr="",
            success=True,
            execution_time=1.0,
        )

        request = DockerManagementRequest(
            resource=DockerResource.CONTAINER,
            action=DockerAction.REMOVE,
            name="test-container",
        )

        result = repository.manage_containers(request)

        assert result.success is True
        assert result.resource == DockerResource.CONTAINER
        assert result.action == DockerAction.REMOVE
        assert "Remove container test-container: Success" in result.message
        assert result.output == "test-container"
        mock_client.execute_command.assert_called_once_with("docker rm test-container")

    def test_remove_container_no_name(
        self,
        repository: SSHDockerRepository,
        mock_client: Mock,  # noqa: ARG002
    ) -> None:
        """Test remove action without container name."""
        request = DockerManagementRequest(
            resource=DockerResource.CONTAINER,
            action=DockerAction.REMOVE,
        )

        result = repository.manage_containers(request)

        assert result.success is False
        assert result.resource == DockerResource.CONTAINER
        assert result.action == DockerAction.REMOVE
        assert result.message == "Container name is required for remove action"

    def test_remove_container_failure(
        self, repository: SSHDockerRepository, mock_client: Mock
    ) -> None:
        """Test failed container removal."""
        mock_client.execute_command.return_value = CommandResult(
            command="docker rm nonexistent",
            exit_code=1,
            stdout="",
            stderr="No such container: nonexistent",
            success=False,
            execution_time=0.5,
        )

        request = DockerManagementRequest(
            resource=DockerResource.CONTAINER,
            action=DockerAction.REMOVE,
            name="nonexistent",
        )

        result = repository.manage_containers(request)

        assert result.success is False
        assert result.output == "No such container: nonexistent"

    def test_get_container_logs_success(
        self, repository: SSHDockerRepository, mock_client: Mock
    ) -> None:
        """Test successful container logs retrieval."""
        mock_client.execute_command.return_value = CommandResult(
            command="docker logs test-container",
            exit_code=0,
            stdout="Container log line 1\nContainer log line 2",
            stderr="",
            success=True,
            execution_time=1.0,
        )

        request = DockerManagementRequest(
            resource=DockerResource.CONTAINER,
            action=DockerAction.LOGS,
            name="test-container",
        )

        result = repository.manage_containers(request)

        assert result.success is True
        assert result.resource == DockerResource.CONTAINER
        assert result.action == DockerAction.LOGS
        assert "Get logs for test-container: Success" in result.message
        assert result.output == "Container log line 1\nContainer log line 2"
        mock_client.execute_command.assert_called_once_with(
            "docker logs test-container"
        )

    def test_get_container_logs_with_options(
        self, repository: SSHDockerRepository, mock_client: Mock
    ) -> None:
        """Test container logs with follow and tail options."""
        mock_client.execute_command.return_value = CommandResult(
            command="docker logs -f --tail 100 test-container",
            exit_code=0,
            stdout="Recent log lines",
            stderr="",
            success=True,
            execution_time=1.0,
        )

        request = DockerManagementRequest(
            resource=DockerResource.CONTAINER,
            action=DockerAction.LOGS,
            name="test-container",
            follow_logs=True,
            tail_lines=100,
        )

        result = repository.manage_containers(request)

        assert result.success is True
        expected_cmd = "docker logs -f --tail 100 test-container"
        mock_client.execute_command.assert_called_once_with(expected_cmd)

    def test_get_container_logs_no_name(
        self,
        repository: SSHDockerRepository,
        mock_client: Mock,  # noqa: ARG002
    ) -> None:
        """Test logs action without container name."""
        request = DockerManagementRequest(
            resource=DockerResource.CONTAINER,
            action=DockerAction.LOGS,
        )

        result = repository.manage_containers(request)

        assert result.success is False
        assert result.resource == DockerResource.CONTAINER
        assert result.action == DockerAction.LOGS
        assert result.message == "Container name is required for logs action"

    def test_get_container_logs_failure(
        self, repository: SSHDockerRepository, mock_client: Mock
    ) -> None:
        """Test failed container logs retrieval."""
        mock_client.execute_command.return_value = CommandResult(
            command="docker logs nonexistent",
            exit_code=1,
            stdout="",
            stderr="No such container: nonexistent",
            success=False,
            execution_time=0.5,
        )

        request = DockerManagementRequest(
            resource=DockerResource.CONTAINER,
            action=DockerAction.LOGS,
            name="nonexistent",
        )

        result = repository.manage_containers(request)

        assert result.success is False
        assert result.output == "No such container: nonexistent"

    def test_inspect_container_success(
        self, repository: SSHDockerRepository, mock_client: Mock
    ) -> None:
        """Test successful container inspection."""
        inspect_data = {
            "Id": "abc123",
            "Name": "/test-container",
            "State": {"Status": "running"},
            "Config": {"Image": "nginx:latest"},
        }

        mock_client.execute_command.return_value = CommandResult(
            command="docker inspect test-container",
            exit_code=0,
            stdout=json.dumps([inspect_data]),
            stderr="",
            success=True,
            execution_time=1.0,
        )

        request = DockerManagementRequest(
            resource=DockerResource.CONTAINER,
            action=DockerAction.INSPECT,
            name="test-container",
        )

        result = repository.manage_containers(request)

        assert result.success is True
        assert result.resource == DockerResource.CONTAINER
        assert result.action == DockerAction.INSPECT
        assert "Inspect container test-container: Success" in result.message
        assert result.inspect_data == [inspect_data]
        mock_client.execute_command.assert_called_once_with(
            "docker inspect test-container"
        )

    def test_inspect_container_no_name(
        self,
        repository: SSHDockerRepository,
        mock_client: Mock,  # noqa: ARG002
    ) -> None:
        """Test inspect action without container name."""
        request = DockerManagementRequest(
            resource=DockerResource.CONTAINER,
            action=DockerAction.INSPECT,
        )

        result = repository.manage_containers(request)

        assert result.success is False
        assert result.resource == DockerResource.CONTAINER
        assert result.action == DockerAction.INSPECT
        assert result.message == "Container name is required for inspect action"

    def test_inspect_container_command_failure(
        self, repository: SSHDockerRepository, mock_client: Mock
    ) -> None:
        """Test inspect when command fails."""
        mock_client.execute_command.return_value = CommandResult(
            command="docker inspect nonexistent",
            exit_code=1,
            stdout="",
            stderr="No such container: nonexistent",
            success=False,
            execution_time=0.5,
        )

        request = DockerManagementRequest(
            resource=DockerResource.CONTAINER,
            action=DockerAction.INSPECT,
            name="nonexistent",
        )

        result = repository.manage_containers(request)

        assert result.success is False
        assert result.resource == DockerResource.CONTAINER
        assert result.action == DockerAction.INSPECT
        assert (
            "Failed to inspect container nonexistent: No such container: nonexistent"
            in result.message
        )

    def test_inspect_container_invalid_json(
        self, repository: SSHDockerRepository, mock_client: Mock
    ) -> None:
        """Test inspect with invalid JSON response."""
        mock_client.execute_command.return_value = CommandResult(
            command="docker inspect test-container",
            exit_code=0,
            stdout="invalid json response",
            stderr="",
            success=True,
            execution_time=1.0,
        )

        request = DockerManagementRequest(
            resource=DockerResource.CONTAINER,
            action=DockerAction.INSPECT,
            name="test-container",
        )

        result = repository.manage_containers(request)

        assert result.success is False
        assert result.resource == DockerResource.CONTAINER
        assert result.action == DockerAction.INSPECT
        assert "Failed to parse inspect data for test-container" in result.message

    def test_unsupported_container_action(
        self,
        repository: SSHDockerRepository,
        mock_client: Mock,  # noqa: ARG002
    ) -> None:
        """Test unsupported container action."""
        # Use a compose action on containers to test unsupported action
        request = DockerManagementRequest(
            resource=DockerResource.CONTAINER,
            action=DockerAction.UP,  # This is a compose action
        )

        result = repository.manage_containers(request)

        assert result.success is False
        assert result.resource == DockerResource.CONTAINER
        assert result.action == DockerAction.UP
        assert "Unsupported container action: up" in result.message

    def test_container_management_exception(
        self, repository: SSHDockerRepository, mock_client: Mock
    ) -> None:
        """Test exception handling in container management."""
        mock_client.execute_command.side_effect = Exception("Connection error")

        request = DockerManagementRequest(
            resource=DockerResource.CONTAINER,
            action=DockerAction.PULL,
            image="nginx:latest",
        )

        result = repository.manage_containers(request)

        assert result.success is False
        assert result.resource == DockerResource.CONTAINER
        assert result.action == DockerAction.PULL
        assert "Error managing container: Connection error" in result.message

    def test_compose_up_success(
        self, repository: SSHDockerRepository, mock_client: Mock
    ) -> None:
        """Test successful compose up."""
        mock_client.execute_command.return_value = CommandResult(
            command="docker-compose up -d",
            exit_code=0,
            stdout="Starting containers...\nContainers started",
            stderr="",
            success=True,
            execution_time=5.0,
        )

        request = DockerManagementRequest(
            resource=DockerResource.COMPOSE,
            action=DockerAction.UP,
            detach=True,
        )

        result = repository.manage_compose(request)

        assert result.success is True
        assert result.resource == DockerResource.COMPOSE
        assert result.action == DockerAction.UP
        assert "Compose up: Success" in result.message
        assert result.output == "Starting containers...\nContainers started"
        mock_client.execute_command.assert_called_once_with("docker-compose up -d")

    def test_compose_up_with_file_and_service(
        self, repository: SSHDockerRepository, mock_client: Mock
    ) -> None:
        """Test compose up with specific file and service."""
        mock_client.execute_command.return_value = CommandResult(
            command="docker-compose -f custom.yml up -d web",
            exit_code=0,
            stdout="Starting web service",
            stderr="",
            success=True,
            execution_time=3.0,
        )

        request = DockerManagementRequest(
            resource=DockerResource.COMPOSE,
            action=DockerAction.UP,
            compose_file="custom.yml",
            service="web",
            detach=True,
        )

        result = repository.manage_compose(request)

        assert result.success is True
        expected_cmd = "docker-compose -f custom.yml up -d web"
        mock_client.execute_command.assert_called_once_with(expected_cmd)

    def test_compose_up_failure(
        self, repository: SSHDockerRepository, mock_client: Mock
    ) -> None:
        """Test failed compose up."""
        mock_client.execute_command.return_value = CommandResult(
            command="docker-compose up -d",
            exit_code=1,
            stdout="",
            stderr="docker-compose.yml not found",
            success=False,
            execution_time=1.0,
        )

        request = DockerManagementRequest(
            resource=DockerResource.COMPOSE,
            action=DockerAction.UP,
            detach=True,
        )

        result = repository.manage_compose(request)

        assert result.success is False
        assert result.output == "docker-compose.yml not found"

    def test_compose_down_success(
        self, repository: SSHDockerRepository, mock_client: Mock
    ) -> None:
        """Test successful compose down."""
        mock_client.execute_command.return_value = CommandResult(
            command="docker-compose down",
            exit_code=0,
            stdout="Stopping containers...\nRemoving containers...",
            stderr="",
            success=True,
            execution_time=3.0,
        )

        request = DockerManagementRequest(
            resource=DockerResource.COMPOSE,
            action=DockerAction.DOWN,
        )

        result = repository.manage_compose(request)

        assert result.success is True
        assert result.resource == DockerResource.COMPOSE
        assert result.action == DockerAction.DOWN
        assert "Compose down: Success" in result.message
        assert result.output == "Stopping containers...\nRemoving containers..."
        mock_client.execute_command.assert_called_once_with("docker-compose down")

    def test_compose_down_with_file(
        self, repository: SSHDockerRepository, mock_client: Mock
    ) -> None:
        """Test compose down with specific file."""
        mock_client.execute_command.return_value = CommandResult(
            command="docker-compose -f custom.yml down",
            exit_code=0,
            stdout="Stopping services",
            stderr="",
            success=True,
            execution_time=2.0,
        )

        request = DockerManagementRequest(
            resource=DockerResource.COMPOSE,
            action=DockerAction.DOWN,
            compose_file="custom.yml",
        )

        result = repository.manage_compose(request)

        assert result.success is True
        expected_cmd = "docker-compose -f custom.yml down"
        mock_client.execute_command.assert_called_once_with(expected_cmd)

    def test_compose_down_failure(
        self, repository: SSHDockerRepository, mock_client: Mock
    ) -> None:
        """Test failed compose down."""
        mock_client.execute_command.return_value = CommandResult(
            command="docker-compose down",
            exit_code=1,
            stdout="",
            stderr="No such file or directory",
            success=False,
            execution_time=1.0,
        )

        request = DockerManagementRequest(
            resource=DockerResource.COMPOSE,
            action=DockerAction.DOWN,
        )

        result = repository.manage_compose(request)

        assert result.success is False
        assert result.output == "No such file or directory"

    def test_unsupported_compose_action(
        self,
        repository: SSHDockerRepository,
        mock_client: Mock,  # noqa: ARG002
    ) -> None:
        """Test unsupported compose action."""
        request = DockerManagementRequest(
            resource=DockerResource.COMPOSE,
            action=DockerAction.PULL,  # This is a container action
        )

        result = repository.manage_compose(request)

        assert result.success is False
        assert result.resource == DockerResource.COMPOSE
        assert result.action == DockerAction.PULL
        assert "Unsupported compose action: pull" in result.message

    def test_compose_management_exception(
        self, repository: SSHDockerRepository, mock_client: Mock
    ) -> None:
        """Test exception handling in compose management."""
        mock_client.execute_command.side_effect = Exception("Connection error")

        request = DockerManagementRequest(
            resource=DockerResource.COMPOSE,
            action=DockerAction.UP,
        )

        result = repository.manage_compose(request)

        assert result.success is False
        assert result.resource == DockerResource.COMPOSE
        assert result.action == DockerAction.UP
        assert "Error managing compose: Connection error" in result.message

    def test_create_volume_success(
        self, repository: SSHDockerRepository, mock_client: Mock
    ) -> None:
        """Test successful volume creation."""
        mock_client.execute_command.return_value = CommandResult(
            command="docker volume create test-volume",
            exit_code=0,
            stdout="test-volume",
            stderr="",
            success=True,
            execution_time=1.0,
        )

        request = DockerManagementRequest(
            resource=DockerResource.VOLUME,
            action=DockerAction.CREATE,
            name="test-volume",
        )

        result = repository.manage_volumes(request)

        assert result.success is True
        assert result.resource == DockerResource.VOLUME
        assert result.action == DockerAction.CREATE
        assert "Create volume test-volume: Success" in result.message
        assert result.output == "test-volume"
        mock_client.execute_command.assert_called_once_with(
            "docker volume create test-volume"
        )

    def test_create_volume_no_name(
        self,
        repository: SSHDockerRepository,
        mock_client: Mock,  # noqa: ARG002
    ) -> None:
        """Test create volume without name."""
        request = DockerManagementRequest(
            resource=DockerResource.VOLUME,
            action=DockerAction.CREATE,
        )

        result = repository.manage_volumes(request)

        assert result.success is False
        assert result.resource == DockerResource.VOLUME
        assert result.action == DockerAction.CREATE
        assert result.message == "Volume name is required for create action"

    def test_create_volume_failure(
        self, repository: SSHDockerRepository, mock_client: Mock
    ) -> None:
        """Test failed volume creation."""
        mock_client.execute_command.return_value = CommandResult(
            command="docker volume create test-volume",
            exit_code=1,
            stdout="",
            stderr="Volume already exists",
            success=False,
            execution_time=0.5,
        )

        request = DockerManagementRequest(
            resource=DockerResource.VOLUME,
            action=DockerAction.CREATE,
            name="test-volume",
        )

        result = repository.manage_volumes(request)

        assert result.success is False
        assert result.output == "Volume already exists"

    def test_list_volumes_success(
        self, repository: SSHDockerRepository, mock_client: Mock
    ) -> None:
        """Test successful volume listing."""
        mock_output = "vol1\tlocal\t/var/lib/docker/volumes/vol1/_data\t2023-01-01T10:00:00Z\tkey1=value1,key2=value2\n"
        mock_output += "vol2\tlocal\t/var/lib/docker/volumes/vol2/_data\t2023-01-01T11:00:00Z\t<no value>"

        mock_client.execute_command.return_value = CommandResult(
            command="docker volume ls --format '{{.Name}}\t{{.Driver}}\t{{.Mountpoint}}\t{{.CreatedAt}}\t{{.Labels}}'",
            exit_code=0,
            stdout=mock_output,
            stderr="",
            success=True,
            execution_time=1.0,
        )

        request = DockerManagementRequest(
            resource=DockerResource.VOLUME,
            action=DockerAction.LIST,
        )

        result = repository.manage_volumes(request)

        assert result.success is True
        assert result.resource == DockerResource.VOLUME
        assert result.action == DockerAction.LIST
        assert result.message == "Found 2 volumes"
        assert result.volumes is not None
        assert len(result.volumes) == 2

        # Check first volume
        volume1 = result.volumes[0]
        assert volume1.name == "vol1"
        assert volume1.driver == "local"
        assert volume1.mountpoint == "/var/lib/docker/volumes/vol1/_data"
        assert volume1.created == "2023-01-01T10:00:00Z"
        assert volume1.labels == {"key1": "value1", "key2": "value2"}

        # Check second volume
        volume2 = result.volumes[1]
        assert volume2.name == "vol2"
        assert volume2.labels == {}

    def test_list_volumes_command_failure(
        self, repository: SSHDockerRepository, mock_client: Mock
    ) -> None:
        """Test volume listing when command fails."""
        mock_client.execute_command.return_value = CommandResult(
            command="docker volume ls --format '{{.Name}}\t{{.Driver}}\t{{.Mountpoint}}\t{{.CreatedAt}}\t{{.Labels}}'",
            exit_code=1,
            stdout="",
            stderr="Cannot connect to Docker daemon",
            success=False,
            execution_time=0.5,
        )

        request = DockerManagementRequest(
            resource=DockerResource.VOLUME,
            action=DockerAction.LIST,
        )

        result = repository.manage_volumes(request)

        assert result.success is False
        assert result.resource == DockerResource.VOLUME
        assert result.action == DockerAction.LIST
        assert (
            "Failed to list volumes: Cannot connect to Docker daemon" in result.message
        )

    def test_list_volumes_malformed_output(
        self, repository: SSHDockerRepository, mock_client: Mock
    ) -> None:
        """Test volume listing with malformed output."""
        mock_client.execute_command.return_value = CommandResult(
            command="docker volume ls --format '{{.Name}}\t{{.Driver}}\t{{.Mountpoint}}\t{{.CreatedAt}}\t{{.Labels}}'",
            exit_code=0,
            stdout="incomplete\tdata\n\nonly\ttwo\tcolumns",
            stderr="",
            success=True,
            execution_time=1.0,
        )

        request = DockerManagementRequest(
            resource=DockerResource.VOLUME,
            action=DockerAction.LIST,
        )

        result = repository.manage_volumes(request)

        assert result.success is True
        assert result.volumes is not None
        assert len(result.volumes) == 0  # Malformed lines are skipped

    def test_unsupported_volume_action(
        self,
        repository: SSHDockerRepository,
        mock_client: Mock,  # noqa: ARG002
    ) -> None:
        """Test unsupported volume action."""
        request = DockerManagementRequest(
            resource=DockerResource.VOLUME,
            action=DockerAction.PULL,  # This is a container action
        )

        result = repository.manage_volumes(request)

        assert result.success is False
        assert result.resource == DockerResource.VOLUME
        assert result.action == DockerAction.PULL
        assert "Unsupported volume action: pull" in result.message

    def test_volume_management_exception(
        self, repository: SSHDockerRepository, mock_client: Mock
    ) -> None:
        """Test exception handling in volume management."""
        mock_client.execute_command.side_effect = Exception("Connection error")

        request = DockerManagementRequest(
            resource=DockerResource.VOLUME,
            action=DockerAction.CREATE,
            name="test-volume",
        )

        result = repository.manage_volumes(request)

        assert result.success is False
        assert result.resource == DockerResource.VOLUME
        assert result.action == DockerAction.CREATE
        assert "Error managing volume: Connection error" in result.message

    def test_parse_ports_empty_string(self, repository: SSHDockerRepository) -> None:
        """Test parsing empty ports string."""
        result = repository._parse_ports("")
        assert result == {}

    def test_parse_ports_no_value(self, repository: SSHDockerRepository) -> None:
        """Test parsing '<no value>' ports string."""
        result = repository._parse_ports("<no value>")
        assert result == {}

    def test_parse_ports_single_mapping(self, repository: SSHDockerRepository) -> None:
        """Test parsing single port mapping."""
        result = repository._parse_ports("0.0.0.0:8080->80/tcp")
        assert result == {"8080": "80"}

    def test_parse_ports_multiple_mappings(
        self, repository: SSHDockerRepository
    ) -> None:
        """Test parsing multiple port mappings."""
        result = repository._parse_ports("0.0.0.0:8080->80/tcp, 0.0.0.0:8443->443/tcp")
        assert result == {"8080": "80", "8443": "443"}

    def test_parse_ports_no_arrow(self, repository: SSHDockerRepository) -> None:
        """Test parsing ports without arrow mapping."""
        result = repository._parse_ports("80/tcp")
        assert result == {}

    def test_parse_ports_malformed(self, repository: SSHDockerRepository) -> None:
        """Test parsing malformed port mappings."""
        result = repository._parse_ports("malformed->port->mapping")
        assert result == {}

    def test_parse_labels_empty_string(self, repository: SSHDockerRepository) -> None:
        """Test parsing empty labels string."""
        result = repository._parse_labels("")
        assert result == {}

    def test_parse_labels_no_value(self, repository: SSHDockerRepository) -> None:
        """Test parsing '<no value>' labels string."""
        result = repository._parse_labels("<no value>")
        assert result == {}

    def test_parse_labels_single_label(self, repository: SSHDockerRepository) -> None:
        """Test parsing single label."""
        result = repository._parse_labels("key=value")
        assert result == {"key": "value"}

    def test_parse_labels_multiple_labels(
        self, repository: SSHDockerRepository
    ) -> None:
        """Test parsing multiple labels."""
        result = repository._parse_labels("key1=value1,key2=value2")
        assert result == {"key1": "value1", "key2": "value2"}

    def test_parse_labels_no_equals(self, repository: SSHDockerRepository) -> None:
        """Test parsing labels without equals sign."""
        result = repository._parse_labels("key1,key2")
        assert result == {}

    def test_parse_labels_value_with_equals(
        self, repository: SSHDockerRepository
    ) -> None:
        """Test parsing labels with equals in value."""
        result = repository._parse_labels("key=value=with=equals")
        assert result == {"key": "value=with=equals"}

    def test_parse_labels_with_whitespace(
        self, repository: SSHDockerRepository
    ) -> None:
        """Test parsing labels with whitespace."""
        result = repository._parse_labels("key1 = value1 , key2 = value2")
        assert result == {"key1": "value1", "key2": "value2"}
