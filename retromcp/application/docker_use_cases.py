"""Docker management use cases for RetroMCP."""

from ..domain.models import ConnectionError
from ..domain.models import DockerManagementRequest
from ..domain.models import DockerManagementResult
from ..domain.models import DockerResource
from ..domain.models import ExecutionError
from ..domain.models import Result
from ..domain.models import ValidationError
from ..domain.ports import DockerRepository


class ManageDockerUseCase:
    """Use case for managing Docker containers, compose services, and volumes."""

    def __init__(self, docker_repo: DockerRepository) -> None:
        """Initialize with Docker repository."""
        self._docker_repo = docker_repo

    def execute(
        self, request: DockerManagementRequest
    ) -> Result[
        DockerManagementResult, ValidationError | ConnectionError | ExecutionError
    ]:
        """Execute Docker management request."""
        try:
            # Check if Docker is available
            if not self._docker_repo.is_docker_available():
                return Result.error(
                    ValidationError(
                        code="DOCKER_NOT_AVAILABLE",
                        message="Docker is not available on this system. Please install Docker first.",
                        details={
                            "resource": request.resource.value,
                            "action": request.action.value,
                        },
                    )
                )

            # Route to appropriate handler based on resource type
            if request.resource == DockerResource.CONTAINER:
                result = self._docker_repo.manage_containers(request)
                return Result.success(result)
            elif request.resource == DockerResource.COMPOSE:
                result = self._docker_repo.manage_compose(request)
                return Result.success(result)
            elif request.resource == DockerResource.VOLUME:
                result = self._docker_repo.manage_volumes(request)
                return Result.success(result)
            else:
                return Result.error(
                    ValidationError(
                        code="UNSUPPORTED_RESOURCE_TYPE",
                        message=f"Unsupported resource type: {request.resource if isinstance(request.resource, str) else request.resource.value}",
                        details={"resource": str(request.resource)},
                    )
                )

        except OSError as e:
            return Result.error(
                ConnectionError(
                    code="DOCKER_CONNECTION_FAILED",
                    message=f"Failed to connect to Docker: {e}",
                    details={"error": str(e)},
                )
            )
        except Exception as e:
            return Result.error(
                ExecutionError(
                    code="DOCKER_OPERATION_FAILED",
                    message="Failed to execute Docker operation",
                    command=f"docker {request.action.value if hasattr(request.action, 'value') else request.action}",
                    exit_code=1,
                    stderr=str(e),
                )
            )
