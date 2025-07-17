"""State management tools for RetroMCP."""

from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from mcp.types import EmbeddedResource
from mcp.types import ImageContent
from mcp.types import TextContent
from mcp.types import Tool

from ..domain.models import StateAction
from ..domain.models import StateManagementRequest
from ..domain.models import StateManagementResult
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
                            "enum": [
                                "load",
                                "save",
                                "update",
                                "compare",
                                "export",
                                "import",
                                "diff",
                                "watch",
                            ],
                            "description": "Action to perform: load (retrieve cached state), save (scan and persist current state), update (modify specific field), compare (detect configuration drift), export (backup state to JSON), import (restore state from JSON), diff (compare with another state), watch (monitor specific field)",
                        },
                        "path": {
                            "type": "string",
                            "description": "Field path for update or watch actions (e.g., 'system.hostname')",
                        },
                        "value": {
                            "description": "New value for update action (any type)"
                        },
                        "force_scan": {
                            "type": "boolean",
                            "description": "Force full system scan for save action",
                            "default": False,
                        },
                        "state_data": {
                            "type": "string",
                            "description": "JSON state data for import action",
                        },
                        "other_state_data": {
                            "type": "string",
                            "description": "JSON state data to compare against for diff action",
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
        path = arguments.get("path")  # Store path for later use

        if not action_str:
            return self.format_error("Action is required")

        # Validate action
        try:
            action = StateAction(action_str)
        except ValueError:
            return self.format_error(f"Invalid action: {action_str}")

        # Validate action-specific arguments
        if action == StateAction.UPDATE:
            value = arguments.get("value")

            if not path or value is None:
                return self.format_error(
                    "Path and value are required for update action"
                )
        elif action == StateAction.WATCH:
            if not path:
                return self.format_error("Path is required for watch action")
        elif action == StateAction.IMPORT:
            state_data = arguments.get("state_data")
            if not state_data:
                return self.format_error("state_data is required for import action")
        elif action == StateAction.DIFF:
            other_state_data = arguments.get("other_state_data")
            if not other_state_data:
                return self.format_error("other_state_data is required for diff action")

        # Build request
        request = StateManagementRequest(
            action=action,
            path=path,
            value=arguments.get("value"),
            force_scan=arguments.get("force_scan", False),
            state_data=arguments.get("state_data"),
            other_state_data=arguments.get("other_state_data"),
        )

        # Execute use case
        result = self.container.manage_state_use_case.execute(request)

        if result.success:
            return self._format_success_response(result, path)
        else:
            return self.format_error(result.message)

    def _format_success_response(
        self, result: StateManagementResult, path: Optional[str] = None
    ) -> List[TextContent]:
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

        elif result.action == StateAction.EXPORT and result.exported_data:
            # Format export results
            response_text += "📤 State exported successfully!\n\n"
            response_text += "📄 Exported JSON Data:\n"
            response_text += "```json\n"
            response_text += result.exported_data
            response_text += "\n```\n"

        elif result.action == StateAction.IMPORT:
            # Format import results
            response_text += "📥 State imported successfully!\n"
            response_text += (
                "The system state has been restored from the provided backup.\n"
            )

        elif result.action == StateAction.WATCH and result.watch_value is not None:
            # Format watch results
            response_text += f"👁️ Watching field: {path or 'unknown'}\n"
            response_text += f"📊 Current value: {result.watch_value}\n"
            response_text += "Monitor will track changes to this field.\n"

        elif result.action in [StateAction.DIFF, StateAction.COMPARE] and result.diff:
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
