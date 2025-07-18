"""SSH-based Docker repository implementation."""

import json
import re
from typing import Dict

from ..domain.models import DockerAction
from ..domain.models import DockerContainer
from ..domain.models import DockerManagementRequest
from ..domain.models import DockerManagementResult
from ..domain.models import DockerResource
from ..domain.models import DockerVolume
from ..domain.ports import DockerRepository
from ..domain.ports import RetroPieClient


class SSHDockerRepository(DockerRepository):
    """SSH-based implementation of Docker repository."""

    def __init__(self, client: RetroPieClient) -> None:
        """Initialize Docker repository.

        Args:
            client: RetroPie client for SSH operations.
        """
        self.client = client

    def manage_containers(
        self, request: DockerManagementRequest
    ) -> DockerManagementResult:
        """Manage Docker containers."""
        try:
            if request.action == DockerAction.PULL:
                return self._pull_image(request)
            elif request.action == DockerAction.RUN:
                return self._run_container(request)
            elif request.action == DockerAction.PS:
                return self._list_containers(request)
            elif request.action == DockerAction.STOP:
                return self._stop_container(request)
            elif request.action == DockerAction.START:
                return self._start_container(request)
            elif request.action == DockerAction.RESTART:
                return self._restart_container(request)
            elif request.action == DockerAction.REMOVE:
                return self._remove_container(request)
            elif request.action == DockerAction.LOGS:
                return self._get_container_logs(request)
            elif request.action == DockerAction.INSPECT:
                return self._inspect_container(request)
            else:
                return DockerManagementResult(
                    success=False,
                    resource=DockerResource.CONTAINER,
                    action=request.action,
                    message=f"Unsupported container action: {request.action.value}",
                )
        except Exception as e:
            return DockerManagementResult(
                success=False,
                resource=DockerResource.CONTAINER,
                action=request.action,
                message=f"Error managing container: {e!s}",
            )

    def manage_compose(
        self, request: DockerManagementRequest
    ) -> DockerManagementResult:
        """Manage Docker Compose services."""
        try:
            if request.action == DockerAction.UP:
                return self._compose_up(request)
            elif request.action == DockerAction.DOWN:
                return self._compose_down(request)
            else:
                return DockerManagementResult(
                    success=False,
                    resource=DockerResource.COMPOSE,
                    action=request.action,
                    message=f"Unsupported compose action: {request.action.value}",
                )
        except Exception as e:
            return DockerManagementResult(
                success=False,
                resource=DockerResource.COMPOSE,
                action=request.action,
                message=f"Error managing compose: {e!s}",
            )

    def manage_volumes(
        self, request: DockerManagementRequest
    ) -> DockerManagementResult:
        """Manage Docker volumes."""
        try:
            if request.action == DockerAction.CREATE:
                return self._create_volume(request)
            elif request.action == DockerAction.LIST:
                return self._list_volumes(request)
            else:
                return DockerManagementResult(
                    success=False,
                    resource=DockerResource.VOLUME,
                    action=request.action,
                    message=f"Unsupported volume action: {request.action.value}",
                )
        except Exception as e:
            return DockerManagementResult(
                success=False,
                resource=DockerResource.VOLUME,
                action=request.action,
                message=f"Error managing volume: {e!s}",
            )

    def is_docker_available(self) -> bool:
        """Check if Docker is available on the system."""
        try:
            result = self.client.execute_command("docker --version")
            return result.success and "Docker version" in result.stdout
        except Exception:
            return False

    def _pull_image(self, request: DockerManagementRequest) -> DockerManagementResult:
        """Pull Docker image."""
        if not request.image:
            return DockerManagementResult(
                success=False,
                resource=DockerResource.CONTAINER,
                action=DockerAction.PULL,
                message="Image name is required for pull action",
            )

        result = self.client.execute_command(f"docker pull {request.image}")
        return DockerManagementResult(
            success=result.success,
            resource=DockerResource.CONTAINER,
            action=DockerAction.PULL,
            message=f"Pull image {request.image}: {'Success' if result.success else result.stderr}",
            output=result.stdout if result.success else result.stderr,
        )

    def _run_container(
        self, request: DockerManagementRequest
    ) -> DockerManagementResult:
        """Run Docker container."""
        if not request.image:
            return DockerManagementResult(
                success=False,
                resource=DockerResource.CONTAINER,
                action=DockerAction.RUN,
                message="Image name is required for run action",
            )

        cmd_parts = ["docker", "run"]

        if request.detach:
            cmd_parts.append("-d")

        if request.remove_on_exit:
            cmd_parts.append("--rm")

        if request.name:
            cmd_parts.extend(["--name", request.name])

        if request.ports:
            for host_port, container_port in request.ports.items():
                cmd_parts.extend(["-p", f"{host_port}:{container_port}"])

        if request.environment:
            for key, value in request.environment.items():
                cmd_parts.extend(["-e", f"{key}={value}"])

        if request.volumes:
            for host_path, container_path in request.volumes.items():
                cmd_parts.extend(["-v", f"{host_path}:{container_path}"])

        cmd_parts.append(request.image)

        if request.command:
            cmd_parts.extend(request.command.split())

        result = self.client.execute_command(" ".join(cmd_parts))
        return DockerManagementResult(
            success=result.success,
            resource=DockerResource.CONTAINER,
            action=DockerAction.RUN,
            message=f"Run container: {'Success' if result.success else result.stderr}",
            output=result.stdout if result.success else result.stderr,
        )

    def _list_containers(
        self,
        request: DockerManagementRequest,  # noqa: ARG002
    ) -> DockerManagementResult:
        """List Docker containers."""
        cmd = "docker ps -a --format '{{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.CreatedAt}}\t{{.Ports}}\t{{.Command}}'"
        result = self.client.execute_command(cmd)

        if not result.success:
            return DockerManagementResult(
                success=False,
                resource=DockerResource.CONTAINER,
                action=DockerAction.PS,
                message=f"Failed to list containers: {result.stderr}",
            )

        containers = []
        for line in result.stdout.strip().split("\n"):
            if line.strip():
                parts = line.split("\t")
                if len(parts) >= 7:
                    containers.append(
                        DockerContainer(
                            container_id=parts[0],
                            name=parts[1],
                            image=parts[2],
                            status=parts[3],
                            created=parts[4],
                            ports=self._parse_ports(parts[5]),
                            command=parts[6],
                        )
                    )

        return DockerManagementResult(
            success=True,
            resource=DockerResource.CONTAINER,
            action=DockerAction.PS,
            message=f"Found {len(containers)} containers",
            containers=containers,
        )

    def _stop_container(
        self, request: DockerManagementRequest
    ) -> DockerManagementResult:
        """Stop Docker container."""
        if not request.name:
            return DockerManagementResult(
                success=False,
                resource=DockerResource.CONTAINER,
                action=DockerAction.STOP,
                message="Container name is required for stop action",
            )

        result = self.client.execute_command(f"docker stop {request.name}")
        return DockerManagementResult(
            success=result.success,
            resource=DockerResource.CONTAINER,
            action=DockerAction.STOP,
            message=f"Stop container {request.name}: {'Success' if result.success else result.stderr}",
            output=result.stdout if result.success else result.stderr,
        )

    def _start_container(
        self, request: DockerManagementRequest
    ) -> DockerManagementResult:
        """Start Docker container."""
        if not request.name:
            return DockerManagementResult(
                success=False,
                resource=DockerResource.CONTAINER,
                action=DockerAction.START,
                message="Container name is required for start action",
            )

        result = self.client.execute_command(f"docker start {request.name}")
        return DockerManagementResult(
            success=result.success,
            resource=DockerResource.CONTAINER,
            action=DockerAction.START,
            message=f"Start container {request.name}: {'Success' if result.success else result.stderr}",
            output=result.stdout if result.success else result.stderr,
        )

    def _restart_container(
        self, request: DockerManagementRequest
    ) -> DockerManagementResult:
        """Restart Docker container."""
        if not request.name:
            return DockerManagementResult(
                success=False,
                resource=DockerResource.CONTAINER,
                action=DockerAction.RESTART,
                message="Container name is required for restart action",
            )

        result = self.client.execute_command(f"docker restart {request.name}")
        return DockerManagementResult(
            success=result.success,
            resource=DockerResource.CONTAINER,
            action=DockerAction.RESTART,
            message=f"Restart container {request.name}: {'Success' if result.success else result.stderr}",
            output=result.stdout if result.success else result.stderr,
        )

    def _remove_container(
        self, request: DockerManagementRequest
    ) -> DockerManagementResult:
        """Remove Docker container."""
        if not request.name:
            return DockerManagementResult(
                success=False,
                resource=DockerResource.CONTAINER,
                action=DockerAction.REMOVE,
                message="Container name is required for remove action",
            )

        result = self.client.execute_command(f"docker rm {request.name}")
        return DockerManagementResult(
            success=result.success,
            resource=DockerResource.CONTAINER,
            action=DockerAction.REMOVE,
            message=f"Remove container {request.name}: {'Success' if result.success else result.stderr}",
            output=result.stdout if result.success else result.stderr,
        )

    def _get_container_logs(
        self, request: DockerManagementRequest
    ) -> DockerManagementResult:
        """Get Docker container logs."""
        if not request.name:
            return DockerManagementResult(
                success=False,
                resource=DockerResource.CONTAINER,
                action=DockerAction.LOGS,
                message="Container name is required for logs action",
            )

        cmd_parts = ["docker", "logs"]

        if request.follow_logs:
            cmd_parts.append("-f")

        if request.tail_lines:
            cmd_parts.extend(["--tail", str(request.tail_lines)])

        cmd_parts.append(request.name)

        result = self.client.execute_command(" ".join(cmd_parts))
        return DockerManagementResult(
            success=result.success,
            resource=DockerResource.CONTAINER,
            action=DockerAction.LOGS,
            message=f"Get logs for {request.name}: {'Success' if result.success else result.stderr}",
            output=result.stdout if result.success else result.stderr,
        )

    def _inspect_container(
        self, request: DockerManagementRequest
    ) -> DockerManagementResult:
        """Inspect Docker container."""
        if not request.name:
            return DockerManagementResult(
                success=False,
                resource=DockerResource.CONTAINER,
                action=DockerAction.INSPECT,
                message="Container name is required for inspect action",
            )

        result = self.client.execute_command(f"docker inspect {request.name}")

        if not result.success:
            return DockerManagementResult(
                success=False,
                resource=DockerResource.CONTAINER,
                action=DockerAction.INSPECT,
                message=f"Failed to inspect container {request.name}: {result.stderr}",
            )

        try:
            inspect_data = json.loads(result.stdout)
            return DockerManagementResult(
                success=True,
                resource=DockerResource.CONTAINER,
                action=DockerAction.INSPECT,
                message=f"Inspect container {request.name}: Success",
                inspect_data=inspect_data,
            )
        except json.JSONDecodeError:
            return DockerManagementResult(
                success=False,
                resource=DockerResource.CONTAINER,
                action=DockerAction.INSPECT,
                message=f"Failed to parse inspect data for {request.name}",
            )

    def _compose_up(self, request: DockerManagementRequest) -> DockerManagementResult:
        """Start Docker Compose services."""
        cmd_parts = ["docker-compose"]

        if request.compose_file:
            cmd_parts.extend(["-f", request.compose_file])

        cmd_parts.append("up")

        if request.detach:
            cmd_parts.append("-d")

        if request.service:
            cmd_parts.append(request.service)

        result = self.client.execute_command(" ".join(cmd_parts))
        return DockerManagementResult(
            success=result.success,
            resource=DockerResource.COMPOSE,
            action=DockerAction.UP,
            message=f"Compose up: {'Success' if result.success else result.stderr}",
            output=result.stdout if result.success else result.stderr,
        )

    def _compose_down(self, request: DockerManagementRequest) -> DockerManagementResult:
        """Stop Docker Compose services."""
        cmd_parts = ["docker-compose"]

        if request.compose_file:
            cmd_parts.extend(["-f", request.compose_file])

        cmd_parts.append("down")

        result = self.client.execute_command(" ".join(cmd_parts))
        return DockerManagementResult(
            success=result.success,
            resource=DockerResource.COMPOSE,
            action=DockerAction.DOWN,
            message=f"Compose down: {'Success' if result.success else result.stderr}",
            output=result.stdout if result.success else result.stderr,
        )

    def _create_volume(
        self, request: DockerManagementRequest
    ) -> DockerManagementResult:
        """Create Docker volume."""
        if not request.name:
            return DockerManagementResult(
                success=False,
                resource=DockerResource.VOLUME,
                action=DockerAction.CREATE,
                message="Volume name is required for create action",
            )

        result = self.client.execute_command(f"docker volume create {request.name}")
        return DockerManagementResult(
            success=result.success,
            resource=DockerResource.VOLUME,
            action=DockerAction.CREATE,
            message=f"Create volume {request.name}: {'Success' if result.success else result.stderr}",
            output=result.stdout if result.success else result.stderr,
        )

    def _list_volumes(self, request: DockerManagementRequest) -> DockerManagementResult:  # noqa: ARG002
        """List Docker volumes."""
        cmd = "docker volume ls --format '{{.Name}}\t{{.Driver}}\t{{.Mountpoint}}\t{{.CreatedAt}}\t{{.Labels}}'"
        result = self.client.execute_command(cmd)

        if not result.success:
            return DockerManagementResult(
                success=False,
                resource=DockerResource.VOLUME,
                action=DockerAction.LIST,
                message=f"Failed to list volumes: {result.stderr}",
            )

        volumes = []
        for line in result.stdout.strip().split("\n"):
            if line.strip():
                parts = line.split("\t")
                if len(parts) >= 5:
                    volumes.append(
                        DockerVolume(
                            name=parts[0],
                            driver=parts[1],
                            mountpoint=parts[2],
                            created=parts[3],
                            labels=self._parse_labels(parts[4]),
                        )
                    )

        return DockerManagementResult(
            success=True,
            resource=DockerResource.VOLUME,
            action=DockerAction.LIST,
            message=f"Found {len(volumes)} volumes",
            volumes=volumes,
        )

    def _parse_ports(self, ports_str: str) -> Dict[str, str]:
        """Parse Docker ports string into dictionary."""
        if not ports_str or ports_str == "<no value>":
            return {}

        ports = {}
        port_mappings = ports_str.split(", ")
        for mapping in port_mappings:
            if "->" in mapping:
                parts = mapping.split("->")
                if len(parts) == 2:
                    host_part, container_part = parts
                    host_port = re.search(r":(\d+)", host_part)
                    container_port = re.search(r"(\d+)", container_part)
                    if host_port and container_port:
                        ports[host_port.group(1)] = container_port.group(1)
        return ports

    def _parse_labels(self, labels_str: str) -> Dict[str, str]:
        """Parse Docker labels string into dictionary."""
        if not labels_str or labels_str == "<no value>":
            return {}

        labels = {}
        label_pairs = labels_str.split(",")
        for pair in label_pairs:
            if "=" in pair:
                key, value = pair.split("=", 1)
                labels[key.strip()] = value.strip()
        return labels
