"""Docker management tools for RetroMCP."""

from typing import Any
from typing import Dict
from typing import List

from mcp.types import EmbeddedResource
from mcp.types import ImageContent
from mcp.types import TextContent
from mcp.types import Tool

from ..domain.models import DockerAction
from ..domain.models import DockerManagementRequest
from ..domain.models import DockerResource
from .base import BaseTool


class DockerTools(BaseTool):
    """Tools for Docker management."""

    def get_tools(self) -> List[Tool]:
        """Return list of available Docker management tools.

        Returns:
            List of Tool objects for Docker management operations.
        """
        return [
            Tool(
                name="manage_docker",
                description="Manage Docker containers, compose services, and volumes for RetroPie and gaming services",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "resource": {
                            "type": "string",
                            "enum": ["container", "compose", "volume"],
                            "description": "Docker resource type to manage",
                        },
                        "action": {
                            "type": "string",
                            "enum": [
                                "pull",
                                "run",
                                "ps",
                                "stop",
                                "start",
                                "restart",
                                "remove",
                                "logs",
                                "inspect",
                                "up",
                                "down",
                                "create",
                                "list",
                            ],
                            "description": "Action to perform on the resource",
                        },
                        "name": {
                            "type": "string",
                            "description": "Container name or volume name (required for container operations except run/ps)",
                        },
                        "image": {
                            "type": "string",
                            "description": "Docker image name (required for pull/run actions)",
                        },
                        "command": {
                            "type": "string",
                            "description": "Command to run in container (optional for run action)",
                        },
                        "ports": {
                            "type": "object",
                            "description": "Port mappings as host:container pairs (e.g., {'8080': '80'})",
                        },
                        "environment": {
                            "type": "object",
                            "description": "Environment variables as key-value pairs",
                        },
                        "volumes": {
                            "type": "object",
                            "description": "Volume mappings as host:container pairs",
                        },
                        "detach": {
                            "type": "boolean",
                            "description": "Run container in detached mode (default: true)",
                            "default": True,
                        },
                        "remove_on_exit": {
                            "type": "boolean",
                            "description": "Remove container when it exits (default: false)",
                            "default": False,
                        },
                        "compose_file": {
                            "type": "string",
                            "description": "Path to docker-compose.yml file (default: docker-compose.yml)",
                        },
                        "service": {
                            "type": "string",
                            "description": "Specific service name for compose operations",
                        },
                        "follow_logs": {
                            "type": "boolean",
                            "description": "Follow log output (default: false)",
                            "default": False,
                        },
                        "tail_lines": {
                            "type": "integer",
                            "description": "Number of lines to tail from logs",
                        },
                    },
                    "required": ["resource", "action"],
                    "additionalProperties": False,
                },
            )
        ]

    async def handle_tool_call(
        self, name: str, arguments: Dict[str, Any]
    ) -> List[TextContent | ImageContent | EmbeddedResource]:
        """Handle tool calls for Docker management operations.

        Args:
            name: Name of the tool to call.
            arguments: Arguments for the tool.

        Returns:
            List of content objects with the tool's response.
        """
        try:
            if name == "manage_docker":
                return await self._manage_docker(arguments)
            else:
                return self.format_error(f"Unknown tool: {name}")
        except Exception as e:
            return self.format_error(f"Error in {name}: {e!s}")

    async def _manage_docker(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle Docker management operations."""
        resource_str = arguments.get("resource")
        action_str = arguments.get("action")

        if not resource_str or not action_str:
            return self.format_error("Resource and action are required")

        # Validate resource and action
        try:
            resource = DockerResource(resource_str)
            action = DockerAction(action_str)
        except ValueError as e:
            return self.format_error(f"Invalid resource or action: {e!s}")

        # Validate action is valid for resource
        if not self._is_valid_action_for_resource(resource, action):
            return self.format_error(
                f"Action '{action.value}' is not valid for resource '{resource.value}'"
            )

        # Build request
        request = DockerManagementRequest(
            resource=resource,
            action=action,
            name=arguments.get("name"),
            image=arguments.get("image"),
            command=arguments.get("command"),
            ports=arguments.get("ports"),
            environment=arguments.get("environment"),
            volumes=arguments.get("volumes"),
            detach=arguments.get("detach", True),
            remove_on_exit=arguments.get("remove_on_exit", False),
            compose_file=arguments.get("compose_file"),
            service=arguments.get("service"),
            follow_logs=arguments.get("follow_logs", False),
            tail_lines=arguments.get("tail_lines"),
        )

        # Execute use case
        result = self.container.manage_docker_use_case.execute(request)

        # Handle Result pattern
        if result.is_error():
            error = result.error_or_none
            return self.format_error(f"Docker operation failed: {error.message}")

        docker_result = result.value
        return self._format_success_response(docker_result)

    def _is_valid_action_for_resource(
        self, resource: DockerResource, action: DockerAction
    ) -> bool:
        """Check if action is valid for resource type."""
        valid_actions = {
            DockerResource.CONTAINER: [
                DockerAction.PULL,
                DockerAction.RUN,
                DockerAction.PS,
                DockerAction.STOP,
                DockerAction.START,
                DockerAction.RESTART,
                DockerAction.REMOVE,
                DockerAction.LOGS,
                DockerAction.INSPECT,
            ],
            DockerResource.COMPOSE: [DockerAction.UP, DockerAction.DOWN],
            DockerResource.VOLUME: [DockerAction.CREATE, DockerAction.LIST],
        }

        return action in valid_actions.get(resource, [])

    def _format_success_response(self, result: Any) -> List[TextContent]:  # noqa: ANN401
        """Format successful Docker management response."""
        response_text = f"✅ {result.message}\n\n"

        if result.action == DockerAction.PS and result.containers:
            # Format container listing
            response_text += "🐳 Docker Containers:\n"
            response_text += "━" * 80 + "\n"

            for container in result.containers:
                status_emoji = "🟢" if "Up" in container.status else "🔴"
                response_text += (
                    f"{status_emoji} {container.name} ({container.container_id[:12]})\n"
                )
                response_text += f"  📦 Image: {container.image}\n"
                response_text += f"  📊 Status: {container.status}\n"
                response_text += f"  📅 Created: {container.created}\n"

                if container.ports:
                    ports_str = ", ".join(
                        [f"{h}→{c}" for h, c in container.ports.items()]
                    )
                    response_text += f"  🔌 Ports: {ports_str}\n"

                if container.command:
                    response_text += f"  ⚙️ Command: {container.command}\n"

                response_text += "\n"

        elif result.action == DockerAction.LIST and result.volumes:
            # Format volume listing
            response_text += "💾 Docker Volumes:\n"
            response_text += "━" * 80 + "\n"

            for volume in result.volumes:
                response_text += f"📁 {volume.name}\n"
                response_text += f"  🚚 Driver: {volume.driver}\n"
                response_text += f"  📍 Mountpoint: {volume.mountpoint}\n"
                response_text += f"  📅 Created: {volume.created}\n"

                if volume.labels:
                    labels_str = ", ".join(
                        [f"{k}={v}" for k, v in volume.labels.items()]
                    )
                    response_text += f"  🏷️ Labels: {labels_str}\n"

                response_text += "\n"

        elif result.action == DockerAction.INSPECT and result.inspect_data:
            # Format inspect data
            response_text += "🔍 Container Inspection:\n"
            response_text += "━" * 80 + "\n"

            if isinstance(result.inspect_data, list) and result.inspect_data:
                data = result.inspect_data[0]

                response_text += (
                    f"📦 Image: {data.get('Config', {}).get('Image', 'Unknown')}\n"
                )
                response_text += (
                    f"📊 State: {data.get('State', {}).get('Status', 'Unknown')}\n"
                )
                response_text += f"📅 Created: {data.get('Created', 'Unknown')}\n"
                response_text += f"🔄 Restart Count: {data.get('RestartCount', 0)}\n"

                # Network info
                networks = data.get("NetworkSettings", {}).get("Networks", {})
                if networks:
                    response_text += "🌐 Networks:\n"
                    for net_name, net_info in networks.items():
                        ip = net_info.get("IPAddress", "None")
                        response_text += f"  • {net_name}: {ip}\n"

                # Port bindings
                port_bindings = data.get("HostConfig", {}).get("PortBindings", {})
                if port_bindings:
                    response_text += "🔌 Port Bindings:\n"
                    for container_port, host_bindings in port_bindings.items():
                        if host_bindings:
                            host_port = host_bindings[0].get("HostPort", "None")
                            response_text += f"  • {container_port} → {host_port}\n"

                # Mounts
                mounts = data.get("Mounts", [])
                if mounts:
                    response_text += "💾 Mounts:\n"
                    for mount in mounts:
                        source = mount.get("Source", "Unknown")
                        destination = mount.get("Destination", "Unknown")
                        mount_type = mount.get("Type", "Unknown")
                        response_text += (
                            f"  • {source} → {destination} ({mount_type})\n"
                        )

        elif result.action in [DockerAction.LOGS] and result.output:
            # Format logs output
            response_text += "📜 Container Logs:\n"
            response_text += "━" * 80 + "\n"
            response_text += result.output

        elif result.action in [DockerAction.RUN, DockerAction.PULL] and result.output:
            # Format command output
            response_text += "📋 Command Output:\n"
            response_text += "━" * 80 + "\n"
            response_text += result.output

        return [TextContent(type="text", text=response_text)]
