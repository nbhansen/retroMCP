"""Docker management use cases for RetroMCP."""

from ..domain.models import DockerManagementRequest
from ..domain.models import DockerManagementResult
from ..domain.models import DockerResource
from ..domain.ports import DockerRepository


class ManageDockerUseCase:
    """Use case for managing Docker containers, compose services, and volumes."""

    def __init__(self, docker_repo: DockerRepository) -> None:
        """Initialize with Docker repository."""
        self._docker_repo = docker_repo

    def execute(self, request: DockerManagementRequest) -> DockerManagementResult:
        """Execute Docker management request."""
        # Check if Docker is available
        if not self._docker_repo.is_docker_available():
            return DockerManagementResult(
                success=False,
                resource=request.resource,
                action=request.action,
                message="Docker is not available on this system. Please install Docker first.",
            )

        # Route to appropriate handler based on resource type
        if request.resource == DockerResource.CONTAINER:
            return self._docker_repo.manage_containers(request)
        elif request.resource == DockerResource.COMPOSE:
            return self._docker_repo.manage_compose(request)
        elif request.resource == DockerResource.VOLUME:
            return self._docker_repo.manage_volumes(request)
        else:
            return DockerManagementResult(
                success=False,
                resource=request.resource,
                action=request.action,
                message=f"Unsupported resource type: {request.resource.value}",
            )
