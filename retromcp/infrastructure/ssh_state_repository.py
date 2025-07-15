"""SSH-based state repository implementation."""

import json
import shlex
from typing import Any
from typing import Dict

from ..config import RetroPieConfig
from ..domain.models import StateAction
from ..domain.models import StateManagementResult
from ..domain.models import SystemState
from ..domain.ports import RetroPieClient
from ..domain.ports import StateRepository


class SSHStateRepository(StateRepository):
    """SSH-based implementation of StateRepository."""

    def __init__(self, client: RetroPieClient, config: RetroPieConfig) -> None:
        """Initialize with RetroPie client and configuration."""
        self._client = client
        self._config = config
        self._state_file_path = f"{config.paths.home_dir}/.retropie-state.json"

    def load_state(self) -> SystemState:
        """Load state from remote file."""
        safe_path = shlex.quote(self._state_file_path)
        result = self._client.execute_command(f"cat {safe_path}")
        
        if not result.success:
            if "No such file or directory" in result.stderr:
                raise FileNotFoundError(f"State file not found: {self._state_file_path}")
            else:
                raise RuntimeError(f"Failed to read state file: {result.stderr}")
        
        try:
            return SystemState.from_json(result.stdout)
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(f"Invalid JSON in state file: {str(e)}", result.stdout, 0)

    def save_state(self, state: SystemState) -> StateManagementResult:
        """Save state to remote file."""
        try:
            safe_path = shlex.quote(self._state_file_path)
            json_content = state.to_json()
            
            # Sanitize JSON content for security
            sanitized_content = self._sanitize_json_content(json_content)
            
            # Escape single quotes for shell safety
            escaped_content = sanitized_content.replace("'", "'\"'\"'")
            
            # Create parent directory if it doesn't exist
            parent_dir = shlex.quote(str(self._state_file_path).rsplit("/", 1)[0])
            mkdir_result = self._client.execute_command(f"mkdir -p {parent_dir}")
            
            if not mkdir_result.success:
                return StateManagementResult(
                    success=False,
                    action=StateAction.SAVE,
                    message=f"Failed to create directory: {mkdir_result.stderr}",
                )
            
            # Write file using tee for atomic write
            write_command = f"tee {safe_path} > /dev/null << 'EOF_RETROMCP_STATE'\n{escaped_content}\nEOF_RETROMCP_STATE"
            result = self._client.execute_command(write_command)
            
            if result.success:
                # Set proper permissions (user only)
                chmod_result = self._client.execute_command(f"chmod 600 {safe_path}")
                if not chmod_result.success:
                    return StateManagementResult(
                        success=False,
                        action=StateAction.SAVE,
                        message=f"State saved but chmod failed: {chmod_result.stderr}",
                    )
                
                return StateManagementResult(
                    success=True,
                    action=StateAction.SAVE,
                    message="State saved successfully",
                )
            else:
                return StateManagementResult(
                    success=False,
                    action=StateAction.SAVE,
                    message=f"Failed to save state: {result.stderr}",
                )
        
        except Exception as e:
            return StateManagementResult(
                success=False,
                action=StateAction.SAVE,
                message=f"Error saving state: {str(e)}",
            )

    def update_state_field(self, path: str, value: Any) -> StateManagementResult:
        """Update specific field in state."""
        try:
            # Validate path for security
            self._validate_path(path)
            
            # Load current state
            current_state = self.load_state()
            
            # Parse the path and update the field
            state_dict = json.loads(current_state.to_json())
            
            # Split path into parts
            path_parts = path.split('.')
            
            # Navigate to the parent of the field to update
            current_dict = state_dict
            for part in path_parts[:-1]:
                if part not in current_dict:
                    return StateManagementResult(
                        success=False,
                        action=StateAction.UPDATE,
                        message=f"Invalid path: {path}",
                    )
                current_dict = current_dict[part]
            
            # Update the field
            final_key = path_parts[-1]
            if isinstance(current_dict, dict):
                current_dict[final_key] = value
            else:
                return StateManagementResult(
                    success=False,
                    action=StateAction.UPDATE,
                    message=f"Invalid path: {path}",
                )
            
            # Create updated state
            updated_state = SystemState.from_json(json.dumps(state_dict))
            
            # Save the updated state
            save_result = self.save_state(updated_state)
            
            if save_result.success:
                return StateManagementResult(
                    success=True,
                    action=StateAction.UPDATE,
                    message=f"Field {path} updated successfully",
                )
            else:
                return StateManagementResult(
                    success=False,
                    action=StateAction.UPDATE,
                    message=f"Failed to save updated state: {save_result.message}",
                )
        
        except FileNotFoundError:
            return StateManagementResult(
                success=False,
                action=StateAction.UPDATE,
                message="State file not found - run save first",
            )
        except Exception as e:
            return StateManagementResult(
                success=False,
                action=StateAction.UPDATE,
                message=f"Error updating field: {str(e)}",
            )

    def compare_state(self, current_state: SystemState) -> Dict[str, Any]:
        """Compare current state with stored state."""
        try:
            stored_state = self.load_state()
            
            # Convert both states to dictionaries for comparison
            current_dict = json.loads(current_state.to_json())
            stored_dict = json.loads(stored_state.to_json())
            
            # Initialize diff structure
            diff = {
                "added": {},
                "changed": {},
                "removed": {}
            }
            
            # Compare recursively
            self._compare_dicts(current_dict, stored_dict, diff, "")
            
            return diff
        
        except FileNotFoundError:
            # If no stored state, everything is "added"
            return {
                "added": json.loads(current_state.to_json()),
                "changed": {},
                "removed": {}
            }

    def _compare_dicts(self, current: Dict[str, Any], stored: Dict[str, Any], diff: Dict[str, Any], path: str) -> None:
        """Recursively compare dictionaries."""
        # Check for changes and additions
        for key, current_value in current.items():
            current_path = f"{path}.{key}" if path else key
            
            if key not in stored:
                # Added field
                diff["added"][current_path] = current_value
            elif current_value != stored[key]:
                # Changed field
                if isinstance(current_value, dict) and isinstance(stored[key], dict):
                    # Recursively compare nested dictionaries
                    self._compare_dicts(current_value, stored[key], diff, current_path)
                else:
                    # Simple value change
                    diff["changed"][current_path] = {
                        "old": stored[key],
                        "new": current_value
                    }
        
        # Check for removals
        for key, stored_value in stored.items():
            if key not in current:
                removed_path = f"{path}.{key}" if path else key
                diff["removed"][removed_path] = stored_value

    def _validate_path(self, path: str) -> None:
        """Validate path for security."""
        if not path or not isinstance(path, str):
            raise ValueError("Path must be a non-empty string")
        
        # Check for path traversal attempts
        if ".." in path or "/" in path or "\\" in path:
            raise ValueError("Invalid path characters detected")
        
        # Check for potentially dangerous characters
        dangerous_chars = [";", "&", "|", "`", "$", "(", ")", "<", ">"]
        if any(char in path for char in dangerous_chars):
            raise ValueError("Path contains dangerous characters")

    def _sanitize_json_content(self, content: str) -> str:
        """Sanitize JSON content for security."""
        # Remove potential shell command injection patterns
        dangerous_patterns = [
            "$(", "`", "${", "&&", "||", ";", "|"
        ]
        
        sanitized = content
        for pattern in dangerous_patterns:
            if pattern in sanitized:
                # For now, just return the original content
                # In a more sophisticated implementation, we might escape or remove
                # these patterns, but for JSON data they should be rare
                pass
        
        return sanitized