"""Unit tests for state management domain models."""

import json
from datetime import datetime

import pytest

from retromcp.domain.models import StateAction
from retromcp.domain.models import StateManagementRequest
from retromcp.domain.models import StateManagementResult
from retromcp.domain.models import SystemState


class TestStateModels:
    """Test cases for state management domain models."""

    def test_state_action_enum(self) -> None:
        """Test StateAction enum has expected values."""
        assert StateAction.LOAD.value == "load"
        assert StateAction.SAVE.value == "save"
        assert StateAction.UPDATE.value == "update"
        assert StateAction.COMPARE.value == "compare"

    def test_system_state_immutability(self) -> None:
        """Test that SystemState is immutable."""
        state = SystemState(
            schema_version="1.0",
            last_updated=datetime.now().isoformat(),
            system={
                "hardware": "Pi 4B",
                "overclocking": "medium",
                "temperatures": {"normal_range": "45-65°C"}
            },
            emulators={
                "installed": ["mupen64plus"],
                "preferred": {"n64": "mupen64plus"}
            },
            controllers=[],
            roms={"systems": ["nes"], "counts": {"nes": 10}},
            custom_configs=["shaders"],
            known_issues=[]
        )
        
        # Test that state is frozen
        with pytest.raises(AttributeError):
            state.schema_version = "2.0"  # type: ignore

    def test_system_state_to_json(self) -> None:
        """Test SystemState can be serialized to JSON."""
        state = SystemState(
            schema_version="1.0",
            last_updated="2025-07-15T12:00:00Z",
            system={
                "hardware": "Pi 4B",
                "overclocking": "medium",
                "temperatures": {"normal_range": "45-65°C"}
            },
            emulators={
                "installed": ["mupen64plus", "pcsx-rearmed"],
                "preferred": {"n64": "mupen64plus-gliden64"}
            },
            controllers=[
                {"type": "xbox", "device": "/dev/input/js0", "configured": True}
            ],
            roms={
                "systems": ["nes", "snes"],
                "counts": {"nes": 150, "snes": 89}
            },
            custom_configs=["shaders", "bezels"],
            known_issues=["audio crackling"]
        )
        
        # Convert to JSON and back
        json_str = state.to_json()
        data = json.loads(json_str)
        
        assert data["schema_version"] == "1.0"
        assert data["last_updated"] == "2025-07-15T12:00:00Z"
        assert data["system"]["hardware"] == "Pi 4B"
        assert len(data["emulators"]["installed"]) == 2
        assert data["controllers"][0]["type"] == "xbox"
        assert data["roms"]["counts"]["nes"] == 150

    def test_system_state_from_json(self) -> None:
        """Test SystemState can be deserialized from JSON."""
        json_data = {
            "schema_version": "1.0",
            "last_updated": "2025-07-15T12:00:00Z",
            "system": {
                "hardware": "Pi 4B",
                "overclocking": "medium",
                "temperatures": {"normal_range": "45-65°C"}
            },
            "emulators": {
                "installed": ["mupen64plus"],
                "preferred": {"n64": "mupen64plus"}
            },
            "controllers": [],
            "roms": {"systems": ["nes"], "counts": {"nes": 10}},
            "custom_configs": ["shaders"],
            "known_issues": []
        }
        
        state = SystemState.from_json(json.dumps(json_data))
        
        assert state.schema_version == "1.0"
        assert state.system["hardware"] == "Pi 4B"
        assert len(state.emulators["installed"]) == 1
        assert state.roms["counts"]["nes"] == 10

    def test_state_management_request_immutability(self) -> None:
        """Test StateManagementRequest is immutable."""
        request = StateManagementRequest(
            action=StateAction.UPDATE,
            path="system.hardware",
            value="Pi 5"
        )
        
        with pytest.raises(AttributeError):
            request.action = StateAction.LOAD  # type: ignore

    def test_state_management_request_optional_fields(self) -> None:
        """Test StateManagementRequest with optional fields."""
        # Load action doesn't need path or value
        load_request = StateManagementRequest(action=StateAction.LOAD)
        assert load_request.path is None
        assert load_request.value is None
        assert load_request.force_scan is False
        
        # Update action needs path and value
        update_request = StateManagementRequest(
            action=StateAction.UPDATE,
            path="system.hardware",
            value="Pi 5",
            force_scan=True
        )
        assert update_request.path == "system.hardware"
        assert update_request.value == "Pi 5"
        assert update_request.force_scan is True

    def test_state_management_result_immutability(self) -> None:
        """Test StateManagementResult is immutable."""
        result = StateManagementResult(
            success=True,
            action=StateAction.SAVE,
            message="State saved successfully",
            state=None
        )
        
        with pytest.raises(AttributeError):
            result.success = False  # type: ignore

    def test_state_management_result_with_state(self) -> None:
        """Test StateManagementResult can include state data."""
        state = SystemState(
            schema_version="1.0",
            last_updated="2025-07-15T12:00:00Z",
            system={"hardware": "Pi 4B"},
            emulators={"installed": [], "preferred": {}},
            controllers=[],
            roms={"systems": [], "counts": {}},
            custom_configs=[],
            known_issues=[]
        )
        
        result = StateManagementResult(
            success=True,
            action=StateAction.LOAD,
            message="State loaded successfully",
            state=state
        )
        
        assert result.state is not None
        assert result.state.schema_version == "1.0"

    def test_state_management_result_with_diff(self) -> None:
        """Test StateManagementResult can include diff data."""
        diff = {
            "added": {"system.new_field": "value"},
            "changed": {"system.hardware": {"old": "Pi 4B", "new": "Pi 5"}},
            "removed": {"system.old_field": "old_value"}
        }
        
        result = StateManagementResult(
            success=True,
            action=StateAction.COMPARE,
            message="Comparison complete",
            diff=diff
        )
        
        assert result.diff is not None
        assert "added" in result.diff
        assert result.diff["changed"]["system.hardware"]["new"] == "Pi 5"