"""State management tools for RetroMCP."""

from typing import Any
from typing import Dict
from typing import List

from mcp.types import EmbeddedResource
from mcp.types import ImageContent
from mcp.types import TextContent
from mcp.types import Tool

from ..domain.models import StateAction
from ..domain.models import StateManagementRequest
from .base import BaseTool


class StateTools(BaseTool):
    """Tools for system state management."""

    def get_tools(self) -> List[Tool]:
        """Return list of available state management tools.

        Returns:
            List of Tool objects for state management operations.
        """
        return [
            Tool(
                name="manage_state",
                description="Manage persistent system state by storing/retrieving structured data about the RetroPie configuration",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "enum": ["load", "save", "update", "compare"],
                            "description": "Action to perform: load (retrieve cached state), save (scan and persist current state), update (modify specific field), compare (detect configuration drift)",
                        },
                        "path": {
                            "type": "string",
                            "description": "Field path for update action (e.g., 'system.hostname')",
                        },
                        "value": {
                            "description": "New value for update action (any type)"
                        },
                        "force_scan": {
                            "type": "boolean",
                            "description": "Force full system scan for save action",
                            "default": False,
                        },
                    },
                    "required": ["action"],
                    "additionalProperties": False,
                },
            )
        ]

    async def handle_tool_call(
        self, name: str, arguments: Dict[str, Any]
    ) -> List[TextContent | ImageContent | EmbeddedResource]:
        """Handle tool calls for state management operations.

        Args:
            name: Name of the tool to call.
            arguments: Arguments for the tool.

        Returns:
            List of content objects with the tool's response.
        """
        try:
            if name == "manage_state":
                return await self._manage_state(arguments)
            else:
                return self.format_error(f"Unknown tool: {name}")
        except Exception as e:
            return self.format_error(f"Error in {name}: {e!s}")

    async def _manage_state(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle state management operations."""
        action_str = arguments.get("action")

        if not action_str:
            return self.format_error("Action is required")

        # Validate action
        try:
            action = StateAction(action_str)
        except ValueError:
            return self.format_error(f"Invalid action: {action_str}")

        # Validate action-specific arguments
        if action == StateAction.UPDATE:
            path = arguments.get("path")
            value = arguments.get("value")

            if not path or value is None:
                return self.format_error(
                    "Path and value are required for update action"
                )

        # Build request
        request = StateManagementRequest(
            action=action,
            path=arguments.get("path"),
            value=arguments.get("value"),
            force_scan=arguments.get("force_scan", False),
        )

        # Execute use case
        result = self.container.manage_state_use_case.execute(request)

        if result.success:
            return self._format_success_response(result)
        else:
            return self.format_error(result.message)

    def _format_success_response(self, result: "StateResult") -> List[TextContent]:
        """Format successful state management response."""
        response_text = f"✅ {result.message}\n\n"

        if result.action == StateAction.LOAD and result.state:
            # Format loaded state
            state = result.state
            response_text += f"🔄 System State (Schema v{state.schema_version})\n"
            response_text += f"📅 Last Updated: {state.last_updated}\n\n"

            # System info
            response_text += "🖥️ System Information:\n"
            if "hostname" in state.system:
                response_text += f"  • Hostname: {state.system['hostname']}\n"
            if "cpu_temperature" in state.system:
                response_text += (
                    f"  • CPU Temperature: {state.system['cpu_temperature']}°C\n"
                )
            if "memory_total" in state.system:
                memory_gb = state.system["memory_total"] / (1024 * 1024 * 1024)
                response_text += f"  • Memory: {memory_gb:.1f}GB\n"

            # Emulators
            response_text += "\n🎮 Emulators:\n"
            installed = state.emulators.get("installed", [])
            if installed:
                response_text += f"  • Installed: {', '.join(installed)}\n"
            else:
                response_text += "  • No emulators installed\n"

            # Controllers
            response_text += "\n🎯 Controllers:\n"
            if state.controllers:
                for controller in state.controllers:
                    status = (
                        "✅ Configured"
                        if controller.get("configured")
                        else "❌ Not configured"
                    )
                    response_text += f"  • {controller['type']} ({controller['device']}) - {status}\n"
            else:
                response_text += "  • No controllers detected\n"

            # ROMs
            response_text += "\n📁 ROMs:\n"
            rom_systems = state.roms.get("systems", [])
            rom_counts = state.roms.get("counts", {})
            if rom_systems:
                for system in rom_systems:
                    count = rom_counts.get(system, 0)
                    response_text += f"  • {system.upper()}: {count} ROMs\n"
            else:
                response_text += "  • No ROM directories found\n"

            # Custom configs
            if state.custom_configs:
                response_text += (
                    f"\n⚙️ Custom Configurations: {', '.join(state.custom_configs)}\n"
                )

            # Known issues
            if state.known_issues:
                response_text += "\n⚠️ Known Issues:\n"
                for issue in state.known_issues:
                    response_text += f"  • {issue}\n"

        elif result.action == StateAction.COMPARE and result.diff:
            # Format comparison results
            diff = result.diff
            has_changes = bool(
                diff.get("added") or diff.get("changed") or diff.get("removed")
            )

            if not has_changes:
                response_text += (
                    "🎉 No differences found - system state is up to date!\n"
                )
            else:
                response_text += "🔍 Configuration drift detected:\n\n"

                # Added fields
                if diff.get("added"):
                    response_text += "+ Added fields:\n"
                    for path, value in diff["added"].items():
                        response_text += f"  • {path}: {value}\n"
                    response_text += "\n"

                # Changed fields
                if diff.get("changed"):
                    response_text += "🔄 Changed fields:\n"
                    for path, change in diff["changed"].items():
                        response_text += (
                            f"  • {path}: {change['old']} → {change['new']}\n"
                        )
                    response_text += "\n"

                # Removed fields
                if diff.get("removed"):
                    response_text += "- Removed fields:\n"
                    for path, value in diff["removed"].items():
                        response_text += f"  • {path}: {value}\n"
                    response_text += "\n"

        return [TextContent(type="text", text=response_text)]
