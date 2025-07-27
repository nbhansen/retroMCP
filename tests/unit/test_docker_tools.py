"""Unit tests for DockerTools implementation."""

from unittest.mock import Mock

import pytest
from mcp.types import TextContent
from mcp.types import Tool

from retromcp.config import RetroPieConfig
from retromcp.domain.models import DockerAction
from retromcp.domain.models import DockerContainer
from retromcp.domain.models import DockerManagementRequest
from retromcp.domain.models import DockerManagementResult
from retromcp.domain.models import DockerResource
from retromcp.domain.models import DockerVolume
from retromcp.domain.models import Result
from retromcp.tools.docker_tools import DockerTools


@pytest.mark.unit
@pytest.mark.tools
@pytest.mark.docker_tools
class TestDockerTools:
    """Test cases for DockerTools class."""

    @pytest.fixture
    def mock_container(self, test_config: RetroPieConfig) -> Mock:
        """Provide mocked container with Docker use case."""
        mock = Mock()
        mock.manage_docker_use_case = Mock()
        mock.config = test_config
        return mock

    @pytest.fixture
    def docker_tools(self, mock_container: Mock) -> DockerTools:
        """Provide DockerTools instance with mocked dependencies."""
        return DockerTools(mock_container)

    def test_get_tools_returns_docker_management_tool(
        self, docker_tools: DockerTools
    ) -> None:
        """Test that get_tools returns the manage_docker tool with correct schema."""
        # Act
        tools = docker_tools.get_tools()

        # Assert
        assert len(tools) == 1
        tool = tools[0]
        assert isinstance(tool, Tool)
        assert tool.name == "manage_docker"
        assert "Docker containers" in tool.description

        # Verify required properties in schema
        schema = tool.inputSchema
        assert schema["type"] == "object"
        assert "resource" in schema["properties"]
        assert "action" in schema["properties"]
        assert schema["required"] == ["resource", "action"]

    def test_get_tools_schema_has_correct_enums(
        self, docker_tools: DockerTools
    ) -> None:
        """Test that the tool schema contains correct enum values."""
        # Act
        tools = docker_tools.get_tools()
        schema = tools[0].inputSchema

        # Assert
        resource_enum = schema["properties"]["resource"]["enum"]
        action_enum = schema["properties"]["action"]["enum"]

        assert "container" in resource_enum
        assert "compose" in resource_enum
        assert "volume" in resource_enum

        assert "pull" in action_enum
        assert "run" in action_enum
        assert "ps" in action_enum
        assert "stop" in action_enum

    @pytest.mark.asyncio
    async def test_handle_tool_call_unknown_tool_returns_error(
        self, docker_tools: DockerTools
    ) -> None:
        """Test that unknown tool names return error response."""
        # Act
        result = await docker_tools.handle_tool_call("unknown_tool", {})

        # Assert
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Unknown tool: unknown_tool" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_tool_call_exception_returns_error(
        self, docker_tools: DockerTools
    ) -> None:
        """Test that exceptions in tool calls return error response."""
        # Arrange
        docker_tools.container.manage_docker_use_case.execute.side_effect = Exception(
            "Test error"
        )

        # Act
        result = await docker_tools.handle_tool_call(
            "manage_docker", {"resource": "container", "action": "ps"}
        )

        # Assert
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Error in manage_docker: Test error" in result[0].text

    @pytest.mark.asyncio
    async def test_manage_docker_missing_resource_returns_error(
        self, docker_tools: DockerTools
    ) -> None:
        """Test that missing resource parameter returns error."""
        # Act
        result = await docker_tools.handle_tool_call("manage_docker", {"action": "ps"})

        # Assert
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Resource and action are required" in result[0].text

    @pytest.mark.asyncio
    async def test_manage_docker_missing_action_returns_error(
        self, docker_tools: DockerTools
    ) -> None:
        """Test that missing action parameter returns error."""
        # Act
        result = await docker_tools.handle_tool_call(
            "manage_docker", {"resource": "container"}
        )

        # Assert
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Resource and action are required" in result[0].text

    @pytest.mark.asyncio
    async def test_manage_docker_invalid_resource_returns_error(
        self, docker_tools: DockerTools
    ) -> None:
        """Test that invalid resource value returns error."""
        # Act
        result = await docker_tools.handle_tool_call(
            "manage_docker", {"resource": "invalid_resource", "action": "ps"}
        )

        # Assert
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Invalid resource or action" in result[0].text

    @pytest.mark.asyncio
    async def test_manage_docker_invalid_action_returns_error(
        self, docker_tools: DockerTools
    ) -> None:
        """Test that invalid action value returns error."""
        # Act
        result = await docker_tools.handle_tool_call(
            "manage_docker", {"resource": "container", "action": "invalid_action"}
        )

        # Assert
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Invalid resource or action" in result[0].text

    @pytest.mark.asyncio
    async def test_manage_docker_invalid_action_for_resource_returns_error(
        self, docker_tools: DockerTools
    ) -> None:
        """Test that invalid action for resource type returns error."""
        # Act
        result = await docker_tools.handle_tool_call(
            "manage_docker",
            {
                "resource": "volume",
                "action": "pull",  # pull is not valid for volumes
            },
        )

        # Assert
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Action 'pull' is not valid for resource 'volume'" in result[0].text


@pytest.mark.unit
@pytest.mark.tools
@pytest.mark.docker_tools
class TestDockerToolsValidation:
    """Test cases for Docker action/resource validation."""

    @pytest.fixture
    def docker_tools(self, test_config: RetroPieConfig) -> DockerTools:
        """Provide DockerTools instance for validation testing."""
        mock_container = Mock()
        mock_container.config = test_config
        return DockerTools(mock_container)

    def test_is_valid_action_for_container_all_valid(
        self, docker_tools: DockerTools
    ) -> None:
        """Test that all container actions are valid."""
        container_actions = [
            DockerAction.PULL,
            DockerAction.RUN,
            DockerAction.PS,
            DockerAction.STOP,
            DockerAction.START,
            DockerAction.RESTART,
            DockerAction.REMOVE,
            DockerAction.LOGS,
            DockerAction.INSPECT,
        ]

        for action in container_actions:
            assert docker_tools._is_valid_action_for_resource(
                DockerResource.CONTAINER, action
            )

    def test_is_valid_action_for_compose_only_up_down(
        self, docker_tools: DockerTools
    ) -> None:
        """Test that only UP and DOWN actions are valid for compose."""
        assert docker_tools._is_valid_action_for_resource(
            DockerResource.COMPOSE, DockerAction.UP
        )
        assert docker_tools._is_valid_action_for_resource(
            DockerResource.COMPOSE, DockerAction.DOWN
        )

        # Test invalid actions for compose
        assert not docker_tools._is_valid_action_for_resource(
            DockerResource.COMPOSE, DockerAction.PULL
        )
        assert not docker_tools._is_valid_action_for_resource(
            DockerResource.COMPOSE, DockerAction.PS
        )

    def test_is_valid_action_for_volume_only_create_list(
        self, docker_tools: DockerTools
    ) -> None:
        """Test that only CREATE and LIST actions are valid for volumes."""
        assert docker_tools._is_valid_action_for_resource(
            DockerResource.VOLUME, DockerAction.CREATE
        )
        assert docker_tools._is_valid_action_for_resource(
            DockerResource.VOLUME, DockerAction.LIST
        )

        # Test invalid actions for volumes
        assert not docker_tools._is_valid_action_for_resource(
            DockerResource.VOLUME, DockerAction.PULL
        )
        assert not docker_tools._is_valid_action_for_resource(
            DockerResource.VOLUME, DockerAction.RUN
        )


@pytest.mark.unit
@pytest.mark.tools
@pytest.mark.docker_tools
class TestDockerToolsExecution:
    """Test cases for Docker tool execution with use case integration."""

    @pytest.fixture
    def mock_container(self, test_config: RetroPieConfig) -> Mock:
        """Provide mocked container with Docker use case."""
        mock = Mock()
        mock.manage_docker_use_case = Mock()
        mock.config = test_config
        return mock

    @pytest.fixture
    def docker_tools(self, mock_container: Mock) -> DockerTools:
        """Provide DockerTools instance with mocked dependencies."""
        return DockerTools(mock_container)

    @pytest.mark.asyncio
    async def test_manage_docker_success_calls_use_case(
        self, docker_tools: DockerTools, mock_container: Mock
    ) -> None:
        """Test successful Docker management calls the use case with correct parameters."""
        # Arrange
        mock_result = DockerManagementResult(
            success=True,
            resource=DockerResource.CONTAINER,
            action=DockerAction.PS,
            message="Success",
            containers=[],
        )
        mock_container.manage_docker_use_case.execute.return_value = Result.success(
            mock_result
        )

        # Act
        result = await docker_tools.handle_tool_call(
            "manage_docker",
            {"resource": "container", "action": "ps", "name": "test-container"},
        )

        # Assert
        mock_container.manage_docker_use_case.execute.assert_called_once()
        call_args = mock_container.manage_docker_use_case.execute.call_args[0][0]
        assert isinstance(call_args, DockerManagementRequest)
        assert call_args.resource == DockerResource.CONTAINER
        assert call_args.action == DockerAction.PS
        assert call_args.name == "test-container"

    @pytest.mark.asyncio
    async def test_manage_docker_use_case_failure_returns_error(
        self, docker_tools: DockerTools, mock_container: Mock
    ) -> None:
        """Test that use case failure returns error response."""
        from retromcp.domain.models import ExecutionError

        # Arrange
        mock_container.manage_docker_use_case.execute.return_value = Result.error(
            ExecutionError(
                code="DOCKER_NOT_AVAILABLE",
                message="Docker not available",
                command="docker ps",
                exit_code=127,
                stderr="docker: command not found",
            )
        )

        # Act
        result = await docker_tools.handle_tool_call(
            "manage_docker", {"resource": "container", "action": "ps"}
        )

        # Assert
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Docker operation failed: Docker not available" in result[0].text

    @pytest.mark.asyncio
    async def test_manage_docker_with_all_parameters(
        self, docker_tools: DockerTools, mock_container: Mock
    ) -> None:
        """Test Docker management with all optional parameters."""
        # Arrange
        mock_result = DockerManagementResult(
            success=True,
            resource=DockerResource.CONTAINER,
            action=DockerAction.RUN,
            message="Container started",
        )
        mock_container.manage_docker_use_case.execute.return_value = Result.success(
            mock_result
        )

        # Act
        await docker_tools.handle_tool_call(
            "manage_docker",
            {
                "resource": "container",
                "action": "run",
                "name": "test-container",
                "image": "nginx:latest",
                "command": "/bin/bash",
                "ports": {"8080": "80"},
                "environment": {"ENV": "test"},
                "volumes": {"/host": "/container"},
                "detach": False,
                "remove_on_exit": True,
                "follow_logs": True,
                "tail_lines": 100,
            },
        )

        # Assert
        call_args = mock_container.manage_docker_use_case.execute.call_args[0][0]
        assert call_args.image == "nginx:latest"
        assert call_args.command == "/bin/bash"
        assert call_args.ports == {"8080": "80"}
        assert call_args.environment == {"ENV": "test"}
        assert call_args.volumes == {"/host": "/container"}
        assert call_args.detach == False
        assert call_args.remove_on_exit == True
        assert call_args.follow_logs == True
        assert call_args.tail_lines == 100


@pytest.mark.unit
@pytest.mark.tools
@pytest.mark.docker_tools
class TestDockerToolsResponseFormatting:
    """Test cases for Docker response formatting methods."""

    @pytest.fixture
    def mock_container(self, test_config: RetroPieConfig) -> Mock:
        """Provide mocked container with Docker use case."""
        mock = Mock()
        mock.manage_docker_use_case = Mock()
        mock.config = test_config
        return mock

    @pytest.fixture
    def docker_tools(self, mock_container: Mock) -> DockerTools:
        """Provide DockerTools instance with mocked dependencies."""
        return DockerTools(mock_container)

    @pytest.mark.asyncio
    async def test_format_ps_response_with_containers(
        self, docker_tools: DockerTools, mock_container: Mock
    ) -> None:
        """Test formatting of container PS response with container data."""
        # Arrange
        sample_containers = [
            DockerContainer(
                container_id="1234567890ab",
                name="test-nginx",
                image="nginx:latest",
                status="Up 2 hours",
                created="2024-01-15 10:30:00",
                ports={"8080": "80", "8443": "443"},
                command="/docker-entrypoint.sh nginx",
            ),
            DockerContainer(
                container_id="abcdef123456",
                name="test-redis",
                image="redis:alpine",
                status="Exited (0) 1 hour ago",
                created="2024-01-15 09:00:00",
                ports={},
                command="redis-server",
            ),
        ]

        mock_result = DockerManagementResult(
            success=True,
            resource=DockerResource.CONTAINER,
            action=DockerAction.PS,
            message="Listed containers",
            containers=sample_containers,
        )
        mock_container.manage_docker_use_case.execute.return_value = Result.success(
            mock_result
        )

        # Act
        result = await docker_tools.handle_tool_call(
            "manage_docker", {"resource": "container", "action": "ps"}
        )

        # Assert
        assert len(result) == 1
        response_text = result[0].text
        assert "✅ Listed containers" in response_text
        assert "🐳 Docker Containers:" in response_text
        assert "🟢 test-nginx (1234567890ab)" in response_text  # Running container
        assert "🔴 test-redis (abcdef123456)" in response_text  # Stopped container
        assert "📦 Image: nginx:latest" in response_text
        assert "📦 Image: redis:alpine" in response_text
        assert "📊 Status: Up 2 hours" in response_text
        assert "📊 Status: Exited (0) 1 hour ago" in response_text
        assert "🔌 Ports: 8080→80, 8443→443" in response_text
        assert "⚙️ Command: /docker-entrypoint.sh nginx" in response_text
        assert "⚙️ Command: redis-server" in response_text

    @pytest.mark.asyncio
    async def test_format_volume_list_response(
        self, docker_tools: DockerTools, mock_container: Mock
    ) -> None:
        """Test formatting of volume LIST response with volume data."""
        # Arrange
        sample_volumes = [
            DockerVolume(
                name="retropie_data",
                driver="local",
                mountpoint="/var/lib/docker/volumes/retropie_data/_data",
                created="2024-01-15T10:30:00Z",
                labels={"app": "retropie", "env": "production"},
            ),
            DockerVolume(
                name="nginx_config",
                driver="local",
                mountpoint="/var/lib/docker/volumes/nginx_config/_data",
                created="2024-01-15T09:00:00Z",
                labels={},
            ),
        ]

        mock_result = DockerManagementResult(
            success=True,
            resource=DockerResource.VOLUME,
            action=DockerAction.LIST,
            message="Listed volumes",
            volumes=sample_volumes,
        )
        mock_container.manage_docker_use_case.execute.return_value = Result.success(
            mock_result
        )

        # Act
        result = await docker_tools.handle_tool_call(
            "manage_docker", {"resource": "volume", "action": "list"}
        )

        # Assert
        assert len(result) == 1
        response_text = result[0].text
        assert "✅ Listed volumes" in response_text
        assert "💾 Docker Volumes:" in response_text
        assert "📁 retropie_data" in response_text
        assert "📁 nginx_config" in response_text
        assert "🚚 Driver: local" in response_text
        assert (
            "📍 Mountpoint: /var/lib/docker/volumes/retropie_data/_data"
            in response_text
        )
        assert (
            "📍 Mountpoint: /var/lib/docker/volumes/nginx_config/_data" in response_text
        )
        assert "🏷️ Labels: app=retropie, env=production" in response_text

    @pytest.mark.asyncio
    async def test_format_inspect_response_with_detailed_data(
        self, docker_tools: DockerTools, mock_container: Mock
    ) -> None:
        """Test formatting of container INSPECT response with detailed inspection data."""
        # Arrange
        inspect_data = [
            {
                "Config": {"Image": "nginx:latest"},
                "State": {"Status": "running"},
                "Created": "2024-01-15T10:30:00.123456Z",
                "RestartCount": 2,
                "NetworkSettings": {
                    "Networks": {
                        "bridge": {"IPAddress": "172.17.0.2"},
                        "custom_network": {"IPAddress": "192.168.1.100"},
                    }
                },
                "HostConfig": {
                    "PortBindings": {
                        "80/tcp": [{"HostPort": "8080"}],
                        "443/tcp": [{"HostPort": "8443"}],
                    }
                },
                "Mounts": [
                    {
                        "Source": "/host/nginx.conf",
                        "Destination": "/etc/nginx/nginx.conf",
                        "Type": "bind",
                    },
                    {
                        "Source": "/var/lib/docker/volumes/nginx_data/_data",
                        "Destination": "/usr/share/nginx/html",
                        "Type": "volume",
                    },
                ],
            }
        ]

        mock_result = DockerManagementResult(
            success=True,
            resource=DockerResource.CONTAINER,
            action=DockerAction.INSPECT,
            message="Container inspected",
            inspect_data=inspect_data,
        )
        mock_container.manage_docker_use_case.execute.return_value = Result.success(
            mock_result
        )

        # Act
        result = await docker_tools.handle_tool_call(
            "manage_docker",
            {"resource": "container", "action": "inspect", "name": "test-nginx"},
        )

        # Assert
        assert len(result) == 1
        response_text = result[0].text
        assert "✅ Container inspected" in response_text
        assert "🔍 Container Inspection:" in response_text
        assert "📦 Image: nginx:latest" in response_text
        assert "📊 State: running" in response_text
        assert "🔄 Restart Count: 2" in response_text
        assert "🌐 Networks:" in response_text
        assert "• bridge: 172.17.0.2" in response_text
        assert "• custom_network: 192.168.1.100" in response_text
        assert "🔌 Port Bindings:" in response_text
        assert "• 80/tcp → 8080" in response_text
        assert "• 443/tcp → 8443" in response_text
        assert "💾 Mounts:" in response_text
        assert "• /host/nginx.conf → /etc/nginx/nginx.conf (bind)" in response_text
        assert (
            "• /var/lib/docker/volumes/nginx_data/_data → /usr/share/nginx/html (volume)"
            in response_text
        )

    @pytest.mark.asyncio
    async def test_format_logs_response(
        self, docker_tools: DockerTools, mock_container: Mock
    ) -> None:
        """Test formatting of container LOGS response."""
        # Arrange
        log_output = """2024-01-15 10:30:01 [INFO] Starting nginx server
2024-01-15 10:30:02 [INFO] Server listening on port 80
2024-01-15 10:30:03 [WARN] Configuration file not found, using defaults
2024-01-15 10:30:04 [INFO] Ready to accept connections"""

        mock_result = DockerManagementResult(
            success=True,
            resource=DockerResource.CONTAINER,
            action=DockerAction.LOGS,
            message="Retrieved logs",
            output=log_output,
        )
        mock_container.manage_docker_use_case.execute.return_value = Result.success(
            mock_result
        )

        # Act
        result = await docker_tools.handle_tool_call(
            "manage_docker",
            {"resource": "container", "action": "logs", "name": "test-nginx"},
        )

        # Assert
        assert len(result) == 1
        response_text = result[0].text
        assert "✅ Retrieved logs" in response_text
        assert "📜 Container Logs:" in response_text
        assert "2024-01-15 10:30:01 [INFO] Starting nginx server" in response_text
        assert "Ready to accept connections" in response_text

    @pytest.mark.asyncio
    async def test_format_run_response_with_output(
        self, docker_tools: DockerTools, mock_container: Mock
    ) -> None:
        """Test formatting of container RUN response with command output."""
        # Arrange
        command_output = """Unable to find image 'nginx:latest' locally
latest: Pulling from library/nginx
7264a8db6415: Pull complete
05b8de3d0acc: Pull complete
Status: Downloaded newer image for nginx:latest
a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6"""

        mock_result = DockerManagementResult(
            success=True,
            resource=DockerResource.CONTAINER,
            action=DockerAction.RUN,
            message="Container started",
            output=command_output,
        )
        mock_container.manage_docker_use_case.execute.return_value = Result.success(
            mock_result
        )

        # Act
        result = await docker_tools.handle_tool_call(
            "manage_docker",
            {"resource": "container", "action": "run", "image": "nginx:latest"},
        )

        # Assert
        assert len(result) == 1
        response_text = result[0].text
        assert "✅ Container started" in response_text
        assert "📋 Command Output:" in response_text
        assert "Unable to find image 'nginx:latest' locally" in response_text
        assert "Status: Downloaded newer image for nginx:latest" in response_text

    @pytest.mark.asyncio
    async def test_format_pull_response_with_output(
        self, docker_tools: DockerTools, mock_container: Mock
    ) -> None:
        """Test formatting of container PULL response with command output."""
        # Arrange
        pull_output = """latest: Pulling from library/nginx
7264a8db6415: Downloading [===========>                                       ]  2.3MB/10.5MB
05b8de3d0acc: Download complete
Status: Image is up to date for nginx:latest
docker.io/library/nginx:latest"""

        mock_result = DockerManagementResult(
            success=True,
            resource=DockerResource.CONTAINER,
            action=DockerAction.PULL,
            message="Image pulled",
            output=pull_output,
        )
        mock_container.manage_docker_use_case.execute.return_value = Result.success(
            mock_result
        )

        # Act
        result = await docker_tools.handle_tool_call(
            "manage_docker",
            {"resource": "container", "action": "pull", "image": "nginx:latest"},
        )

        # Assert
        assert len(result) == 1
        response_text = result[0].text
        assert "✅ Image pulled" in response_text
        assert "📋 Command Output:" in response_text
        assert "latest: Pulling from library/nginx" in response_text
        assert "Status: Image is up to date for nginx:latest" in response_text

    @pytest.mark.asyncio
    async def test_format_simple_success_response(
        self, docker_tools: DockerTools, mock_container: Mock
    ) -> None:
        """Test formatting of simple success response without special data."""
        # Arrange
        mock_result = DockerManagementResult(
            success=True,
            resource=DockerResource.CONTAINER,
            action=DockerAction.START,
            message="Container started successfully",
        )
        mock_container.manage_docker_use_case.execute.return_value = Result.success(
            mock_result
        )

        # Act
        result = await docker_tools.handle_tool_call(
            "manage_docker",
            {"resource": "container", "action": "start", "name": "test-container"},
        )

        # Assert
        assert len(result) == 1
        response_text = result[0].text
        assert response_text == "✅ Container started successfully\n\n"

    @pytest.mark.asyncio
    async def test_format_response_with_empty_containers_list(
        self, docker_tools: DockerTools, mock_container: Mock
    ) -> None:
        """Test formatting of PS response with empty containers list."""
        # Arrange
        mock_result = DockerManagementResult(
            success=True,
            resource=DockerResource.CONTAINER,
            action=DockerAction.PS,
            message="No containers found",
            containers=[],
        )
        mock_container.manage_docker_use_case.execute.return_value = Result.success(
            mock_result
        )

        # Act
        result = await docker_tools.handle_tool_call(
            "manage_docker", {"resource": "container", "action": "ps"}
        )

        # Assert
        assert len(result) == 1
        response_text = result[0].text
        assert "✅ No containers found" in response_text
        # Empty containers list should not show containers section
        assert "🐳 Docker Containers:" not in response_text

    @pytest.mark.asyncio
    async def test_format_response_with_empty_volumes_list(
        self, docker_tools: DockerTools, mock_container: Mock
    ) -> None:
        """Test formatting of LIST response with empty volumes list."""
        # Arrange
        mock_result = DockerManagementResult(
            success=True,
            resource=DockerResource.VOLUME,
            action=DockerAction.LIST,
            message="No volumes found",
            volumes=[],
        )
        mock_container.manage_docker_use_case.execute.return_value = Result.success(
            mock_result
        )

        # Act
        result = await docker_tools.handle_tool_call(
            "manage_docker", {"resource": "volume", "action": "list"}
        )

        # Assert
        assert len(result) == 1
        response_text = result[0].text
        assert "✅ No volumes found" in response_text
        # Empty volumes list should not show volumes section
        assert "💾 Docker Volumes:" not in response_text

    @pytest.mark.asyncio
    async def test_format_inspect_response_with_minimal_data(
        self, docker_tools: DockerTools, mock_container: Mock
    ) -> None:
        """Test formatting of INSPECT response with minimal inspection data."""
        # Arrange
        inspect_data = [
            {
                "Config": {"Image": "nginx:latest"},
                "State": {"Status": "running"},
                "Created": "2024-01-15T10:30:00Z",
                "RestartCount": 0,
            }
        ]

        mock_result = DockerManagementResult(
            success=True,
            resource=DockerResource.CONTAINER,
            action=DockerAction.INSPECT,
            message="Container inspected",
            inspect_data=inspect_data,
        )
        mock_container.manage_docker_use_case.execute.return_value = Result.success(
            mock_result
        )

        # Act
        result = await docker_tools.handle_tool_call(
            "manage_docker",
            {"resource": "container", "action": "inspect", "name": "test-nginx"},
        )

        # Assert
        assert len(result) == 1
        response_text = result[0].text
        assert "✅ Container inspected" in response_text
        assert "📦 Image: nginx:latest" in response_text
        assert "📊 State: running" in response_text
        assert "🔄 Restart Count: 0" in response_text
