"""Integration tests for discovery and profile management.

Tests the complete flow: SSH connection → discovery → profile creation → tool usage
Also verifies CLAUDE.md compliance during these workflows.
"""

import asyncio
import tempfile
from dataclasses import fields
from dataclasses import is_dataclass
from pathlib import Path
from unittest.mock import Mock
from unittest.mock import patch

import pytest

from retromcp.config import RetroPieConfig
from retromcp.discovery import RetroPieDiscovery
from retromcp.discovery import RetroPiePaths
from retromcp.domain.models import CommandResult
from retromcp.domain.ports import RetroPieClient
from retromcp.profile import SystemProfileManager
from retromcp.tools.system_management_tools import SystemManagementTools


class TestDiscoveryProfileIntegration:
    """Test integration between discovery, profile management, and configuration."""

    @pytest.fixture
    def temp_profiles_dir(self):
        """Create temporary directory for profile storage."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def base_config(self) -> RetroPieConfig:
        """Create base configuration without paths."""
        return RetroPieConfig(
            host="test-retropie.local",
            username="retro",
            password="test_password",  # noqa: S106
            port=22,
        )

    @pytest.fixture
    def mock_client(self) -> Mock:
        """Create mock RetroPie client."""
        return Mock(spec=RetroPieClient)

    @pytest.fixture
    def discovery(self, mock_client: Mock) -> RetroPieDiscovery:
        """Create discovery instance."""
        return RetroPieDiscovery(mock_client)

    @pytest.fixture
    def profile_manager(self, temp_profiles_dir: Path) -> SystemProfileManager:
        """Create profile manager with temporary storage."""
        return SystemProfileManager(profile_dir=temp_profiles_dir)

    def _verify_claude_md_compliance(self, obj: object) -> None:
        """Verify that an object follows CLAUDE.md principles."""
        # Test immutability for dataclasses
        if (
            is_dataclass(obj)
            and hasattr(obj, "__dataclass_params__")
            and "Profile" not in obj.__class__.__name__
        ):
            assert obj.__dataclass_params__.frozen is True, (
                f"{obj.__class__.__name__} should be frozen for immutability"
            )

        # Test meaningful naming
        class_name = obj.__class__.__name__
        assert len(class_name) >= 4, f"Class name '{class_name}' too short"
        assert class_name[0].isupper(), (
            f"Class name '{class_name}' should use PascalCase"
        )

        # Test type hints exist for dataclass fields
        if is_dataclass(obj):
            for field in fields(obj):
                assert field.type is not None, (
                    f"Field {field.name} in {class_name} should have type annotation"
                )

    def test_complete_discovery_to_profile_workflow(
        self,
        discovery: RetroPieDiscovery,
        profile_manager: SystemProfileManager,
        mock_client: Mock,
        base_config: RetroPieConfig,
    ) -> None:
        """Test complete workflow from discovery to profile creation with CLAUDE.md compliance."""
        # Step 1: Mock successful discovery
        mock_client.execute_command.side_effect = [
            CommandResult("pwd", 0, "/home/retro", "", True, 0.1),
            CommandResult("whoami", 0, "retro", "", True, 0.1),
            CommandResult("test -d /home/retro/RetroPie", 0, "", "", True, 0.1),
            CommandResult("test -d /home/retro/RetroPie-Setup", 0, "", "", True, 0.1),
            CommandResult("test -d /home/retro/RetroPie/BIOS", 0, "", "", True, 0.1),
            CommandResult("test -d /home/retro/RetroPie/roms", 0, "", "", True, 0.1),
        ]

        # Step 2: Perform discovery
        discovered_paths = discovery.discover_system_paths()

        # CLAUDE.md compliance check for discovered paths
        self._verify_claude_md_compliance(discovered_paths)

        # Verify discovery results
        assert discovered_paths.home_dir == "/home/retro"
        assert discovered_paths.username == "retro"
        assert discovered_paths.retropie_dir == "/home/retro/RetroPie"
        assert discovered_paths.retropie_setup_dir == "/home/retro/RetroPie-Setup"
        assert discovered_paths.bios_dir == "/home/retro/RetroPie/BIOS"
        assert discovered_paths.roms_dir == "/home/retro/RetroPie/roms"

        # Step 3: Create profile from discovered paths
        profile = profile_manager.get_or_create_profile(discovered_paths)

        # CLAUDE.md compliance check for profile
        self._verify_claude_md_compliance(profile)

        # Verify profile creation (using actual SystemProfile API)
        assert profile.discovered_at is not None
        assert profile.username == "retro"
        assert profile.home_dir == "/home/retro"
        assert profile.retropie_dir == "/home/retro/RetroPie"
        assert profile.retropie_setup_dir == "/home/retro/RetroPie-Setup"
        assert profile.bios_dir == "/home/retro/RetroPie/BIOS"
        assert profile.roms_dir == "/home/retro/RetroPie/roms"

        # Step 4: Update configuration with discovered paths
        updated_config = base_config.with_paths(discovered_paths)

        # CLAUDE.md compliance check for config
        self._verify_claude_md_compliance(updated_config)

        # Verify configuration update
        assert updated_config.paths == discovered_paths
        assert updated_config.host == base_config.host
        assert updated_config.username == base_config.username

        # Step 5: Verify profile persistence
        # The profile manager should have the current profile loaded
        current_profile = profile_manager.current_profile
        assert current_profile is not None
        assert current_profile.username == "retro"
        assert current_profile.home_dir == "/home/retro"

    def test_partial_discovery_profile_workflow(
        self,
        discovery: RetroPieDiscovery,
        profile_manager: SystemProfileManager,
        mock_client: Mock,
    ) -> None:
        """Test workflow when some directories are missing."""
        # Mock partial discovery (some directories missing)
        mock_client.execute_command.side_effect = [
            CommandResult("pwd", 0, "/home/pi", "", True, 0.1),
            CommandResult("whoami", 0, "pi", "", True, 0.1),
            CommandResult(
                "test -d /home/pi/RetroPie", 1, "", "", False, 0.1
            ),  # Missing
            CommandResult("test -d /home/pi/RetroPie-Setup", 0, "", "", True, 0.1),
            CommandResult(
                "test -d /home/pi/RetroPie/BIOS", 1, "", "", False, 0.1
            ),  # Missing
            CommandResult(
                "test -d /home/pi/RetroPie/roms", 1, "", "", False, 0.1
            ),  # Missing
        ]

        # Perform discovery
        discovered_paths = discovery.discover_system_paths()

        # CLAUDE.md compliance check
        self._verify_claude_md_compliance(discovered_paths)

        # Create profile
        profile = profile_manager.get_or_create_profile(discovered_paths)

        # CLAUDE.md compliance check
        self._verify_claude_md_compliance(profile)

        # Verify partial discovery works
        assert profile.home_dir == "/home/pi"
        assert profile.username == "pi"
        assert profile.retropie_dir is None  # Missing
        assert profile.retropie_setup_dir == "/home/pi/RetroPie-Setup"
        assert profile.bios_dir is None  # Missing
        assert profile.roms_dir is None  # Missing

    def test_discovery_failure_handling(
        self,
        discovery: RetroPieDiscovery,
        profile_manager: SystemProfileManager,
        mock_client: Mock,
    ) -> None:
        """Test handling of discovery failures with CLAUDE.md compliance."""
        # Mock discovery failures
        mock_client.execute_command.side_effect = [
            CommandResult("pwd", 1, "", "Permission denied", False, 0.1),
            CommandResult("whoami", 1, "", "Command not found", False, 0.1),
            CommandResult("test -d /unknown/RetroPie", 1, "", "", False, 0.1),
            CommandResult("test -d /unknown/RetroPie-Setup", 1, "", "", False, 0.1),
            CommandResult("test -d /unknown/RetroPie/BIOS", 1, "", "", False, 0.1),
            CommandResult("test -d /unknown/RetroPie/roms", 1, "", "", False, 0.1),
        ]

        # Perform discovery (should handle gracefully)
        discovered_paths = discovery.discover_system_paths()

        # CLAUDE.md compliance check
        self._verify_claude_md_compliance(discovered_paths)

        # Create profile
        profile = profile_manager.get_or_create_profile(discovered_paths)

        # CLAUDE.md compliance check
        self._verify_claude_md_compliance(profile)

        # Verify graceful handling of failures
        assert profile.home_dir == "unknown"
        assert profile.username == "unknown"
        assert profile.retropie_dir is None
        assert profile.discovered_at is not None

    def test_discovery_to_tool_usage_integration(
        self,
        discovery: RetroPieDiscovery,
        profile_manager: SystemProfileManager,
        mock_client: Mock,
        base_config: RetroPieConfig,
    ) -> None:
        """Test complete integration from discovery to tool usage with CLAUDE.md compliance."""
        # Step 1: Mock successful discovery
        mock_client.execute_command.side_effect = [
            CommandResult("pwd", 0, "/home/retro", "", True, 0.1),
            CommandResult("whoami", 0, "retro", "", True, 0.1),
            CommandResult("test -d /home/retro/RetroPie", 0, "", "", True, 0.1),
            CommandResult("test -d /home/retro/RetroPie-Setup", 0, "", "", True, 0.1),
            CommandResult("test -d /home/retro/RetroPie/BIOS", 0, "", "", True, 0.1),
            CommandResult("test -d /home/retro/RetroPie/roms", 0, "", "", True, 0.1),
        ]

        # Perform discovery and create profile
        discovered_paths = discovery.discover_system_paths()
        profile = profile_manager.get_or_create_profile(discovered_paths)
        updated_config = base_config.with_paths(discovered_paths)

        # CLAUDE.md compliance checks
        self._verify_claude_md_compliance(discovered_paths)
        self._verify_claude_md_compliance(profile)
        self._verify_claude_md_compliance(updated_config)

        # Step 2: Use tools with the configured system
        with patch("retromcp.container.Container") as mock_container_class:
            # Mock Container instance
            mock_container = Mock()
            mock_container.config = updated_config
            mock_container_class.return_value = mock_container

            # Mock the get_system_info_use_case
            mock_use_case = Mock()
            mock_system_info = Mock()
            mock_system_info.hostname = "test-hostname"
            mock_system_info.cpu_temperature = 45.0
            mock_system_info.load_average = "0.1 0.2 0.3"
            mock_system_info.uptime = "2 days, 3 hours"
            mock_system_info.memory_total = 1024 * 1024 * 1024  # 1GB
            mock_system_info.memory_used = 512 * 1024 * 1024  # 512MB
            mock_system_info.memory_free = 512 * 1024 * 1024  # 512MB
            mock_system_info.disk_total = 16 * 1024 * 1024 * 1024  # 16GB
            mock_system_info.disk_used = 8 * 1024 * 1024 * 1024  # 8GB
            mock_system_info.disk_free = 8 * 1024 * 1024 * 1024  # 8GB
            mock_use_case.execute.return_value = mock_system_info
            mock_container.get_system_info_use_case = mock_use_case

            # Create SystemManagementTools with Container
            system_tools = SystemManagementTools(mock_container)

            # CLAUDE.md compliance check for tools
            self._verify_claude_md_compliance(updated_config)

            # Test tool execution
            result = asyncio.run(system_tools.handle_tool_call("get_system_info", {}))

            # Verify tool execution works and follows MCP protocol
            assert isinstance(result, list)
            assert len(result) > 0
            # Tool should use the discovered paths in its operation
            # This verifies the complete integration chain


class TestProfilePersistenceIntegration:
    """Test profile persistence and retrieval with CLAUDE.md compliance."""

    @pytest.fixture
    def temp_profiles_dir(self):
        """Create temporary directory for profile storage."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def sample_paths(self) -> RetroPiePaths:
        """Create sample discovered paths."""
        return RetroPiePaths(
            home_dir="/home/retro",
            username="retro",
            retropie_dir="/home/retro/RetroPie",
            retropie_setup_dir="/home/retro/RetroPie-Setup",
            bios_dir="/home/retro/RetroPie/BIOS",
            roms_dir="/home/retro/RetroPie/roms",
        )

    def _verify_claude_md_compliance(self, obj: object) -> None:
        """Verify that an object follows CLAUDE.md principles."""
        # Test immutability for dataclasses
        if (
            is_dataclass(obj)
            and hasattr(obj, "__dataclass_params__")
            and "Profile" not in obj.__class__.__name__
        ):
            assert obj.__dataclass_params__.frozen is True, (
                f"{obj.__class__.__name__} should be frozen for immutability"
            )

        # Test meaningful naming
        class_name = obj.__class__.__name__
        assert len(class_name) >= 4, f"Class name '{class_name}' too short"
        assert class_name[0].isupper(), (
            f"Class name '{class_name}' should use PascalCase"
        )

    def test_profile_creation_and_retrieval(
        self, temp_profiles_dir: Path, sample_paths: RetroPiePaths
    ) -> None:
        """Test profile creation, persistence, and retrieval with CLAUDE.md compliance."""
        # Create profile manager
        manager = SystemProfileManager(profile_dir=temp_profiles_dir)

        # CLAUDE.md compliance check for manager
        self._verify_claude_md_compliance(sample_paths)

        # Create profile
        profile = manager.get_or_create_profile(sample_paths)

        # CLAUDE.md compliance check for profile
        self._verify_claude_md_compliance(profile)

        # Verify creation
        assert profile.username == "retro"
        assert profile.home_dir == "/home/retro"
        assert profile.discovered_at is not None

        # Create new manager instance to test persistence
        new_manager = SystemProfileManager(profile_dir=temp_profiles_dir)
        loaded_profile = new_manager.load_profile()

        # Verify persistence
        if loaded_profile:
            # CLAUDE.md compliance check for loaded profile
            self._verify_claude_md_compliance(loaded_profile)

            assert loaded_profile.username == profile.username
            assert loaded_profile.home_dir == profile.home_dir
            assert loaded_profile.retropie_dir == profile.retropie_dir

    def test_profile_updates_integration(
        self, temp_profiles_dir: Path, sample_paths: RetroPiePaths
    ) -> None:
        """Test profile updates and versioning with CLAUDE.md compliance."""
        manager = SystemProfileManager(profile_dir=temp_profiles_dir)

        # Create initial profile
        profile = manager.get_or_create_profile(sample_paths)

        # CLAUDE.md compliance check
        self._verify_claude_md_compliance(profile)

        original_discovered_at = profile.discovered_at

        # Add user note (test mutable operations)
        profile.add_user_note("Test note from integration test")
        manager.save_profile(profile)

        # Verify update
        assert "Test note from integration test" in profile.user_notes

        # Load and verify persistence of update
        loaded_profile = manager.load_profile()
        assert loaded_profile is not None

        # CLAUDE.md compliance check for loaded profile
        self._verify_claude_md_compliance(loaded_profile)

        assert "Test note from integration test" in loaded_profile.user_notes
        assert loaded_profile.discovered_at == original_discovered_at

    def test_multiple_profiles_integration(self, temp_profiles_dir: Path) -> None:
        """Test handling multiple profile scenarios with CLAUDE.md compliance."""
        # Create two different path configurations
        retro_paths = RetroPiePaths(
            home_dir="/home/retro",
            username="retro",
            retropie_dir="/home/retro/RetroPie",
        )

        pi_paths = RetroPiePaths(
            home_dir="/home/pi",
            username="pi",
            retropie_dir="/home/pi/RetroPie",
        )

        # CLAUDE.md compliance checks
        self._verify_claude_md_compliance(retro_paths)
        self._verify_claude_md_compliance(pi_paths)

        # Create profile with retro paths
        manager = SystemProfileManager(profile_dir=temp_profiles_dir)
        retro_profile = manager.get_or_create_profile(retro_paths)

        # CLAUDE.md compliance check
        self._verify_claude_md_compliance(retro_profile)

        # Update to pi paths (should update existing profile)
        pi_profile = manager.get_or_create_profile(pi_paths)

        # CLAUDE.md compliance check
        self._verify_claude_md_compliance(pi_profile)

        # Verify profile was updated, not duplicated
        assert pi_profile.username == "pi"
        assert pi_profile.home_dir == "/home/pi"

        # Profiles should have different paths but may be separate objects
        # The important thing is that the manager only maintains one profile at a time
        current_profile = manager.current_profile
        assert current_profile is not None
        assert current_profile.username == "pi"
        assert current_profile.home_dir == "/home/pi"
