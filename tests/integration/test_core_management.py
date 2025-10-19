"""Integration tests for core management with real Raspberry Pi.

These tests connect to an actual Raspberry Pi and test the core management
functionality end-to-end. Requires .env with RETROPIE_HOST, RETROPIE_USERNAME,
and RETROPIE_PASSWORD or RETROPIE_SSH_KEY_PATH.
"""

import os

import pytest
from dotenv import load_dotenv

from retromcp.config import RetroPieConfig
from retromcp.container import Container
from retromcp.domain.models import CoreOption

# Load environment variables from .env file
load_dotenv()


@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("RETROPIE_HOST"),
    reason="RETROPIE_HOST not set - skipping real Pi tests",
)
class TestCoreManagementIntegration:
    """Test core management with real Raspberry Pi."""

    @pytest.fixture(scope="class")
    def container(self) -> Container:
        """Create container with real SSH connection."""
        config = RetroPieConfig.from_env()
        container = Container(config)
        container.ssh_handler.connect()
        yield container
        container.ssh_handler.disconnect()

    def test_list_cores(self, container: Container):
        """Test listing all installed cores."""
        # Act
        use_case = container.list_cores_use_case
        result = use_case.execute()

        # Assert
        assert result.is_success(), f"Failed: {result.error_value if result.is_error() else ''}"
        cores = result.success_value
        assert len(cores) > 0, "Expected at least one core to be installed"

        # Verify core structure
        first_core = cores[0]
        assert first_core.name
        assert first_core.core_path
        assert first_core.display_name
        assert isinstance(first_core.systems, list)

    def test_get_core_info(self, container: Container):
        """Test getting detailed info about a specific core."""
        # First get a core name
        list_result = container.list_cores_use_case.execute()
        assert list_result.is_success()
        cores = list_result.success_value
        assert len(cores) > 0

        core_name = cores[0].name

        # Act
        use_case = container.get_core_info_use_case
        result = use_case.execute(core_name)

        # Assert
        assert result.is_success()
        core = result.success_value
        assert core.name == core_name
        assert core.core_path
        assert core.display_name

    def test_get_core_info_nonexistent(self, container: Container):
        """Test getting info for a core that doesn't exist."""
        # Act
        use_case = container.get_core_info_use_case
        result = use_case.execute("lr-nonexistent-core-12345")

        # Assert
        assert result.is_error()
        assert result.error_value.code == "CORE_NOT_FOUND"

    def test_get_core_info_invalid_name(self, container: Container):
        """Test security validation of core name."""
        # Act
        use_case = container.get_core_info_use_case
        result = use_case.execute("../../../etc/passwd")

        # Assert
        assert result.is_error()

    def test_list_core_options(self, container: Container):
        """Test listing options for a core."""
        # Use lr-mupen64plus-next as it has many options
        core_name = "lr-mupen64plus-next"

        # Skip if core not installed
        list_result = container.list_cores_use_case.execute()
        if list_result.is_success():
            core_names = [c.name for c in list_result.success_value]
            if core_name not in core_names:
                pytest.skip(f"{core_name} not installed on this Pi")

        # Act
        use_case = container.list_core_options_use_case
        result = use_case.execute(core_name)

        # Assert
        assert result.is_success()
        options = result.success_value
        # mupen64plus-next typically has many options
        assert len(options) > 0, f"Expected {core_name} to have configuration options"

        # Verify option structure
        first_option = options[0]
        assert first_option.key
        assert first_option.value is not None

    def test_list_core_options_invalid_name(self, container: Container):
        """Test security validation of core name in options."""
        # Act
        use_case = container.list_core_options_use_case
        result = use_case.execute("; rm -rf /")

        # Assert
        assert result.is_error()

    def test_get_emulator_mappings(self, container: Container):
        """Test getting emulator mappings for a system."""
        # Act - use n64 as it typically has multiple emulators
        use_case = container.get_emulator_mappings_use_case
        result = use_case.execute("n64")

        # Assert
        assert result.is_success()
        mappings = result.success_value
        assert len(mappings) > 0, "Expected at least one emulator for n64"

        # Verify one is marked as default
        defaults = [m for m in mappings if m.is_default]
        assert len(defaults) == 1, "Expected exactly one default emulator"

        # Verify mapping structure
        first_mapping = mappings[0]
        assert first_mapping.system == "n64"
        assert first_mapping.emulator_name
        assert first_mapping.command

    def test_get_emulator_mappings_invalid_system(self, container: Container):
        """Test security validation of system name."""
        # Act
        use_case = container.get_emulator_mappings_use_case
        result = use_case.execute("../../etc")

        # Assert
        assert result.is_error()

    def test_update_core_option_and_restore(self, container: Container):
        """Test updating a core option and restoring it."""
        core_name = "lr-mupen64plus-next"
        option_key = "mupen64plus-next-aspect"

        # Skip if core not installed
        list_result = container.list_cores_use_case.execute()
        if list_result.is_success():
            core_names = [c.name for c in list_result.success_value]
            if core_name not in core_names:
                pytest.skip(f"{core_name} not installed on this Pi")

        # Get current value
        options_result = container.list_core_options_use_case.execute(core_name)
        if options_result.is_error():
            pytest.skip(f"Could not list options for {core_name}")

        current_options = {opt.key: opt.value for opt in options_result.success_value}
        if option_key not in current_options:
            pytest.skip(f"Option {option_key} not found in {core_name}")

        original_value = current_options[option_key]

        try:
            # Change to a different value
            new_value = "16:9" if original_value != "16:9" else "4:3"

            # Act - Update option
            update_use_case = container.update_core_option_use_case
            option = CoreOption(key=option_key, value=new_value, core_name=core_name)
            update_result = update_use_case.execute(core_name, option_key, new_value)

            # Assert update worked
            assert update_result.is_success(), f"Update failed: {update_result.error_value if update_result.is_error() else ''}"

            # Verify the change
            verify_result = container.list_core_options_use_case.execute(core_name)
            assert verify_result.is_success()
            updated_options = {opt.key: opt.value for opt in verify_result.success_value}
            assert updated_options[option_key] == new_value, "Option value was not updated"

        finally:
            # Restore original value
            restore_option = CoreOption(key=option_key, value=original_value, core_name=core_name)
            restore_result = update_use_case.execute(core_name, option_key, original_value)
            assert restore_result.is_success(), "Failed to restore original value"

    def test_set_default_emulator_and_restore(self, container: Container):
        """Test setting default emulator and restoring it."""
        system = "n64"

        # Get current mappings
        mappings_result = container.get_emulator_mappings_use_case.execute(system)
        assert mappings_result.is_success()
        mappings = mappings_result.success_value

        if len(mappings) < 2:
            pytest.skip(f"Need at least 2 emulators for {system} to test switching")

        # Find current default and an alternative
        current_default = next(m.emulator_name for m in mappings if m.is_default)
        alternative = next(m.emulator_name for m in mappings if not m.is_default)

        try:
            # Act - Switch to alternative
            set_use_case = container.set_default_emulator_use_case
            switch_result = set_use_case.execute(system, alternative)

            # Assert switch worked
            assert switch_result.is_success(), f"Switch failed: {switch_result.error_value if switch_result.is_error() else ''}"

            # Verify the change
            verify_result = container.get_emulator_mappings_use_case.execute(system)
            assert verify_result.is_success()
            updated_mappings = verify_result.success_value
            new_default = next(m.emulator_name for m in updated_mappings if m.is_default)
            assert new_default == alternative, "Default emulator was not changed"

        finally:
            # Restore original default
            restore_result = set_use_case.execute(system, current_default)
            assert restore_result.is_success(), "Failed to restore original default"

    def test_set_default_emulator_invalid_system(self, container: Container):
        """Test security validation of system name."""
        # Act
        use_case = container.set_default_emulator_use_case
        result = use_case.execute("; rm -rf /", "emulator")

        # Assert
        assert result.is_error()

    def test_set_default_emulator_invalid_emulator(self, container: Container):
        """Test security validation of emulator name."""
        # Act
        use_case = container.set_default_emulator_use_case
        result = use_case.execute("n64", "../../../etc/passwd")

        # Assert
        assert result.is_error()
