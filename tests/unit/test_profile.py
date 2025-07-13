"""Unit tests for system profile management."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from retromcp.discovery import RetroPiePaths
from retromcp.profile import ControllerProfile
from retromcp.profile import EmulatorProfile
from retromcp.profile import SystemProfile
from retromcp.profile import SystemProfileManager


class TestControllerProfile:
    """Test cases for ControllerProfile dataclass."""

    def test_controller_profile_creation(self) -> None:
        """Test basic controller profile creation."""
        controller = ControllerProfile(
            name="Xbox Controller",
            controller_type="xbox",
            device_path="/dev/input/js0",
            configured=True,
        )

        assert controller.name == "Xbox Controller"
        assert controller.controller_type == "xbox"
        assert controller.device_path == "/dev/input/js0"
        assert controller.configured is True
        assert controller.driver_required is None
        assert controller.known_issues == []
        assert controller.last_tested is None

    def test_controller_profile_with_all_fields(self) -> None:
        """Test controller profile with all optional fields."""
        controller = ControllerProfile(
            name="DualShock 4",
            controller_type="ps4",
            device_path="/dev/input/js1",
            configured=False,
            driver_required="ds4drv",
            known_issues=["Bluetooth pairing issues"],
            last_tested="2024-01-15T10:30:00",
        )

        assert controller.driver_required == "ds4drv"
        assert controller.known_issues == ["Bluetooth pairing issues"]
        assert controller.last_tested == "2024-01-15T10:30:00"

    def test_controller_profile_post_init(self) -> None:
        """Test that post_init properly initializes mutable fields."""
        controller = ControllerProfile(
            name="Test",
            controller_type="test",
            device_path="/dev/test",
            configured=True,
            known_issues=None,
        )

        assert controller.known_issues == []


class TestEmulatorProfile:
    """Test cases for EmulatorProfile dataclass."""

    def test_emulator_profile_creation(self) -> None:
        """Test basic emulator profile creation."""
        emulator = EmulatorProfile(
            name="lr-mupen64plus",
            system="n64",
            status="installed",
        )

        assert emulator.name == "lr-mupen64plus"
        assert emulator.system == "n64"
        assert emulator.status == "installed"
        assert emulator.version is None
        assert emulator.config_path is None
        assert emulator.bios_required == []
        assert emulator.controller_issues == []
        assert emulator.performance_notes == []
        assert emulator.last_used is None

    def test_emulator_profile_with_all_fields(self) -> None:
        """Test emulator profile with all optional fields."""
        emulator = EmulatorProfile(
            name="pcsx-rearmed",
            system="psx",
            status="configured",
            version="1.9.93",
            config_path="/opt/retropie/configs/psx/pcsx.cfg",
            bios_required=["scph1001.bin", "scph5501.bin"],
            controller_issues=["Analog sticks need calibration"],
            performance_notes=["Enable frameskip for smooth gameplay"],
            last_used="2024-01-14T20:00:00",
        )

        assert emulator.version == "1.9.93"
        assert emulator.config_path == "/opt/retropie/configs/psx/pcsx.cfg"
        assert emulator.bios_required == ["scph1001.bin", "scph5501.bin"]
        assert emulator.controller_issues == ["Analog sticks need calibration"]
        assert emulator.performance_notes == ["Enable frameskip for smooth gameplay"]
        assert emulator.last_used == "2024-01-14T20:00:00"

    def test_emulator_profile_post_init(self) -> None:
        """Test that post_init properly initializes mutable fields."""
        emulator = EmulatorProfile(
            name="test",
            system="test",
            status="test",
            bios_required=None,
            controller_issues=None,
            performance_notes=None,
        )

        assert emulator.bios_required == []
        assert emulator.controller_issues == []
        assert emulator.performance_notes == []


class TestSystemProfile:
    """Test cases for SystemProfile dataclass."""

    @pytest.fixture
    def test_paths(self) -> RetroPiePaths:
        """Provide test RetroPiePaths instance."""
        return RetroPiePaths(
            home_dir="/home/retro",
            username="retro",
            retropie_dir="/home/retro/RetroPie",
            retropie_setup_dir="/home/retro/RetroPie-Setup",
            bios_dir="/home/retro/RetroPie/BIOS",
            roms_dir="/home/retro/RetroPie/roms",
            configs_dir="/opt/retropie/configs",
            emulators_dir="/opt/retropie/emulators",
        )

    def test_system_profile_creation(self) -> None:
        """Test basic system profile creation."""
        profile = SystemProfile(
            discovered_at="2024-01-15T10:00:00",
            username="retro",
            home_dir="/home/retro",
        )

        assert profile.discovered_at == "2024-01-15T10:00:00"
        assert profile.username == "retro"
        assert profile.home_dir == "/home/retro"
        assert profile.controllers == []
        assert profile.emulators == []
        assert profile.known_issues == []
        assert profile.resolved_issues == []
        assert profile.user_notes == []
        assert profile.preferred_install_method == "binary"

    def test_system_profile_from_discovery(self, test_paths: RetroPiePaths) -> None:
        """Test creating system profile from discovery results."""
        with patch("retromcp.profile.datetime") as mock_datetime:
            mock_datetime.now.return_value.isoformat.return_value = (
                "2024-01-15T10:00:00"
            )
            profile = SystemProfile.from_discovery(test_paths)

        assert profile.discovered_at == "2024-01-15T10:00:00"
        assert profile.username == "retro"
        assert profile.home_dir == "/home/retro"
        assert profile.retropie_dir == "/home/retro/RetroPie"
        assert profile.retropie_setup_dir == "/home/retro/RetroPie-Setup"
        assert profile.bios_dir == "/home/retro/RetroPie/BIOS"
        assert profile.roms_dir == "/home/retro/RetroPie/roms"

    def test_update_controller_new(self) -> None:
        """Test adding a new controller profile."""
        profile = SystemProfile(
            discovered_at="2024-01-15T10:00:00",
            username="retro",
            home_dir="/home/retro",
        )

        controller = ControllerProfile(
            name="Xbox Controller",
            controller_type="xbox",
            device_path="/dev/input/js0",
            configured=True,
        )

        profile.update_controller(controller)

        assert len(profile.controllers) == 1
        assert profile.controllers[0] == controller

    def test_update_controller_existing(self) -> None:
        """Test updating an existing controller profile."""
        profile = SystemProfile(
            discovered_at="2024-01-15T10:00:00",
            username="retro",
            home_dir="/home/retro",
        )

        # Add initial controller
        old_controller = ControllerProfile(
            name="Xbox Controller",
            controller_type="xbox",
            device_path="/dev/input/js0",
            configured=False,
        )
        profile.update_controller(old_controller)

        # Update with same device path
        new_controller = ControllerProfile(
            name="Xbox Controller",
            controller_type="xbox",
            device_path="/dev/input/js0",
            configured=True,
        )
        profile.update_controller(new_controller)

        assert len(profile.controllers) == 1
        assert profile.controllers[0].configured is True

    def test_update_emulator_new(self) -> None:
        """Test adding a new emulator profile."""
        profile = SystemProfile(
            discovered_at="2024-01-15T10:00:00",
            username="retro",
            home_dir="/home/retro",
        )

        emulator = EmulatorProfile(
            name="lr-mupen64plus",
            system="n64",
            status="installed",
        )

        profile.update_emulator(emulator)

        assert len(profile.emulators) == 1
        assert profile.emulators[0] == emulator

    def test_update_emulator_existing(self) -> None:
        """Test updating an existing emulator profile."""
        profile = SystemProfile(
            discovered_at="2024-01-15T10:00:00",
            username="retro",
            home_dir="/home/retro",
        )

        # Add initial emulator
        old_emulator = EmulatorProfile(
            name="lr-mupen64plus",
            system="n64",
            status="installed",
        )
        profile.update_emulator(old_emulator)

        # Update with same name and system
        new_emulator = EmulatorProfile(
            name="lr-mupen64plus",
            system="n64",
            status="configured",
            version="2.5.9",
        )
        profile.update_emulator(new_emulator)

        assert len(profile.emulators) == 1
        assert profile.emulators[0].status == "configured"
        assert profile.emulators[0].version == "2.5.9"

    def test_add_known_issue(self) -> None:
        """Test adding known issues."""
        profile = SystemProfile(
            discovered_at="2024-01-15T10:00:00",
            username="retro",
            home_dir="/home/retro",
        )

        profile.add_known_issue("Audio crackling in SNES emulator")
        assert len(profile.known_issues) == 1
        assert "Audio crackling in SNES emulator" in profile.known_issues

        # Adding same issue again should not duplicate
        profile.add_known_issue("Audio crackling in SNES emulator")
        assert len(profile.known_issues) == 1

    def test_resolve_issue(self) -> None:
        """Test resolving issues."""
        profile = SystemProfile(
            discovered_at="2024-01-15T10:00:00",
            username="retro",
            home_dir="/home/retro",
        )

        # Add an issue
        profile.add_known_issue("Audio crackling in SNES emulator")

        # Resolve it
        profile.resolve_issue(
            "Audio crackling in SNES emulator", "Changed audio driver to ALSA"
        )

        assert len(profile.known_issues) == 0
        assert len(profile.resolved_issues) == 1
        assert (
            "Audio crackling in SNES emulator -> Changed audio driver to ALSA"
            in profile.resolved_issues
        )

    def test_add_user_note(self) -> None:
        """Test adding user notes."""
        profile = SystemProfile(
            discovered_at="2024-01-15T10:00:00",
            username="retro",
            home_dir="/home/retro",
        )

        profile.add_user_note("Remember to backup saves before updating")
        assert len(profile.user_notes) == 1
        assert "Remember to backup saves before updating" in profile.user_notes

        # Adding same note again should not duplicate
        profile.add_user_note("Remember to backup saves before updating")
        assert len(profile.user_notes) == 1

    def test_to_context_summary_minimal(self) -> None:
        """Test context summary generation with minimal data."""
        profile = SystemProfile(
            discovered_at="2024-01-15T10:00:00",
            username="retro",
            home_dir="/home/retro",
        )

        summary = profile.to_context_summary()

        assert "RetroPie System Profile (User: retro)" in summary
        assert "Home: /home/retro" in summary

    def test_to_context_summary_full(self) -> None:
        """Test context summary generation with full data."""
        profile = SystemProfile(
            discovered_at="2024-01-15T10:00:00",
            username="retro",
            home_dir="/home/retro",
            retropie_dir="/home/retro/RetroPie",
            hostname="retropie.local",
        )

        # Add controller
        controller = ControllerProfile(
            name="Xbox Controller",
            controller_type="xbox",
            device_path="/dev/input/js0",
            configured=True,
            known_issues=["Wireless disconnects randomly"],
        )
        profile.update_controller(controller)

        # Add emulator
        emulator = EmulatorProfile(
            name="lr-mupen64plus",
            system="n64",
            status="installed",
            controller_issues=["C-buttons need remapping"],
        )
        profile.update_emulator(emulator)

        # Add issues
        profile.add_known_issue("Audio crackling")
        profile.resolve_issue("Old issue", "Fixed it")

        summary = profile.to_context_summary()

        assert "RetroPie System Profile (User: retro)" in summary
        assert "Home: /home/retro" in summary
        assert "RetroPie: /home/retro/RetroPie" in summary
        assert "Host: retropie.local" in summary
        assert "Controllers:" in summary
        assert "Xbox Controller (xbox) ✓ Configured" in summary
        assert "Issue: Wireless disconnects randomly" in summary
        assert "Emulators:" in summary
        assert "lr-mupen64plus (n64) - installed" in summary
        assert "Controller issue: C-buttons need remapping" in summary
        assert "Known Issues:" in summary
        assert "Audio crackling" in summary
        assert "Previously Resolved:" in summary
        assert "Old issue -> Fixed it" in summary


class TestSystemProfileManager:
    """Test cases for SystemProfileManager class."""

    @pytest.fixture
    def temp_profile_dir(self, tmp_path: Path) -> Path:
        """Create temporary profile directory."""
        profile_dir = tmp_path / ".retromcp"
        profile_dir.mkdir()
        return profile_dir

    @pytest.fixture
    def test_paths(self) -> RetroPiePaths:
        """Provide test RetroPiePaths instance."""
        return RetroPiePaths(
            home_dir="/home/retro",
            username="retro",
            retropie_dir="/home/retro/RetroPie",
            retropie_setup_dir="/home/retro/RetroPie-Setup",
            bios_dir="/home/retro/RetroPie/BIOS",
            roms_dir="/home/retro/RetroPie/roms",
            configs_dir="/opt/retropie/configs",
            emulators_dir="/opt/retropie/emulators",
        )

    def test_manager_initialization(self, temp_profile_dir: Path) -> None:
        """Test profile manager initialization."""
        manager = SystemProfileManager(profile_dir=temp_profile_dir)

        assert manager.profile_dir == temp_profile_dir
        assert manager.profile_path == temp_profile_dir / "system-profile.json"
        assert manager._profile is None

    def test_manager_default_directory(self) -> None:
        """Test profile manager with default directory."""
        with patch("pathlib.Path.home") as mock_home:
            mock_home.return_value = Path("/home/test")
            manager = SystemProfileManager()

        assert manager.profile_dir == Path("/home/test/.retromcp")

    def test_ensure_profile_dir(self, tmp_path: Path) -> None:
        """Test ensuring profile directory exists."""
        profile_dir = tmp_path / "new_dir"
        manager = SystemProfileManager(profile_dir=profile_dir)

        assert not profile_dir.exists()
        manager.ensure_profile_dir()
        assert profile_dir.exists()

        # Should not fail if directory already exists
        manager.ensure_profile_dir()
        assert profile_dir.exists()

    def test_load_profile_not_exists(self, temp_profile_dir: Path) -> None:
        """Test loading profile when file doesn't exist."""
        manager = SystemProfileManager(profile_dir=temp_profile_dir)
        profile = manager.load_profile()

        assert profile is None

    def test_save_and_load_profile(self, temp_profile_dir: Path) -> None:
        """Test saving and loading a profile."""
        manager = SystemProfileManager(profile_dir=temp_profile_dir)

        # Create profile with data
        profile = SystemProfile(
            discovered_at="2024-01-15T10:00:00",
            username="retro",
            home_dir="/home/retro",
            hostname="retropie.local",
        )

        # Add controller
        controller = ControllerProfile(
            name="Xbox Controller",
            controller_type="xbox",
            device_path="/dev/input/js0",
            configured=True,
        )
        profile.update_controller(controller)

        # Add emulator
        emulator = EmulatorProfile(
            name="lr-mupen64plus",
            system="n64",
            status="installed",
        )
        profile.update_emulator(emulator)

        # Save profile
        manager.save_profile(profile)

        # Load profile
        loaded_profile = manager.load_profile()

        assert loaded_profile is not None
        assert loaded_profile.username == "retro"
        assert loaded_profile.hostname == "retropie.local"
        assert len(loaded_profile.controllers) == 1
        assert loaded_profile.controllers[0].name == "Xbox Controller"
        assert len(loaded_profile.emulators) == 1
        assert loaded_profile.emulators[0].name == "lr-mupen64plus"

    def test_load_profile_corrupted(self, temp_profile_dir: Path) -> None:
        """Test loading corrupted profile file."""
        manager = SystemProfileManager(profile_dir=temp_profile_dir)

        # Write corrupted JSON
        profile_path = temp_profile_dir / "system-profile.json"
        profile_path.write_text("{ invalid json")

        profile = manager.load_profile()
        assert profile is None

    def test_save_profile_error(self, temp_profile_dir: Path) -> None:
        """Test handling save errors."""
        manager = SystemProfileManager(profile_dir=temp_profile_dir)

        profile = SystemProfile(
            discovered_at="2024-01-15T10:00:00",
            username="retro",
            home_dir="/home/retro",
        )

        # Make directory read-only to cause error
        temp_profile_dir.chmod(0o444)

        # Should not raise exception
        manager.save_profile(profile)

        # Restore permissions
        temp_profile_dir.chmod(0o755)

    def test_get_or_create_profile_new(
        self, temp_profile_dir: Path, test_paths: RetroPiePaths
    ) -> None:
        """Test getting or creating profile when none exists."""
        manager = SystemProfileManager(profile_dir=temp_profile_dir)

        with patch("retromcp.profile.datetime") as mock_datetime:
            mock_datetime.now.return_value.isoformat.return_value = (
                "2024-01-15T10:00:00"
            )
            profile = manager.get_or_create_profile(test_paths)

        assert profile.username == "retro"
        assert profile.home_dir == "/home/retro"
        assert profile.discovered_at == "2024-01-15T10:00:00"

        # Verify it was saved
        assert (temp_profile_dir / "system-profile.json").exists()

    def test_get_or_create_profile_existing_same_paths(
        self, temp_profile_dir: Path, test_paths: RetroPiePaths
    ) -> None:
        """Test getting existing profile with same paths."""
        manager = SystemProfileManager(profile_dir=temp_profile_dir)

        # Create initial profile
        initial_profile = SystemProfile.from_discovery(test_paths)
        initial_profile.add_known_issue("Test issue")
        manager.save_profile(initial_profile)

        # Get profile again
        profile = manager.get_or_create_profile(test_paths)

        # Should have preserved data
        assert "Test issue" in profile.known_issues

    def test_get_or_create_profile_existing_different_paths(
        self, temp_profile_dir: Path, test_paths: RetroPiePaths
    ) -> None:
        """Test getting existing profile with different paths."""
        manager = SystemProfileManager(profile_dir=temp_profile_dir)

        # Create initial profile with different paths
        old_paths = RetroPiePaths(
            home_dir="/home/olduser",
            username="olduser",
            retropie_dir="/home/olduser/RetroPie",
            retropie_setup_dir="/home/olduser/RetroPie-Setup",
            bios_dir="/home/olduser/RetroPie/BIOS",
            roms_dir="/home/olduser/RetroPie/roms",
            configs_dir="/opt/retropie/configs",
            emulators_dir="/opt/retropie/emulators",
        )
        initial_profile = SystemProfile.from_discovery(old_paths)
        manager.save_profile(initial_profile)

        # Get profile with new paths
        with patch("retromcp.profile.datetime") as mock_datetime:
            mock_datetime.now.return_value.isoformat.return_value = (
                "2024-01-16T10:00:00"
            )
            profile = manager.get_or_create_profile(test_paths)

        # Should have updated paths
        assert profile.username == "retro"
        assert profile.home_dir == "/home/retro"
        assert profile.discovered_at == "2024-01-16T10:00:00"

    def test_update_profile(
        self, temp_profile_dir: Path, test_paths: RetroPiePaths
    ) -> None:
        """Test updating profile with callback function."""
        manager = SystemProfileManager(profile_dir=temp_profile_dir)

        # Create initial profile
        manager.get_or_create_profile(test_paths)

        # Update profile
        def add_controller(p: SystemProfile) -> None:
            controller = ControllerProfile(
                name="Test Controller",
                controller_type="test",
                device_path="/dev/test",
                configured=True,
            )
            p.update_controller(controller)

        manager.update_profile(add_controller)

        # Verify update was saved
        loaded_profile = manager.load_profile()
        assert loaded_profile is not None
        assert len(loaded_profile.controllers) == 1
        assert loaded_profile.controllers[0].name == "Test Controller"

    def test_update_profile_no_current(self, temp_profile_dir: Path) -> None:
        """Test updating profile when no current profile exists."""
        manager = SystemProfileManager(profile_dir=temp_profile_dir)

        # Should not fail
        manager.update_profile(lambda p: p.add_known_issue("Test"))

    def test_current_profile_property(
        self, temp_profile_dir: Path, test_paths: RetroPiePaths
    ) -> None:
        """Test current profile property."""
        manager = SystemProfileManager(profile_dir=temp_profile_dir)

        # Initially None
        assert manager.current_profile is None

        # After get_or_create
        profile = manager.get_or_create_profile(test_paths)
        assert manager.current_profile == profile

    def test_profile_persistence_across_managers(
        self, temp_profile_dir: Path, test_paths: RetroPiePaths
    ) -> None:
        """Test that profiles persist across different manager instances."""
        # First manager creates profile
        manager1 = SystemProfileManager(profile_dir=temp_profile_dir)
        profile1 = manager1.get_or_create_profile(test_paths)
        profile1.add_known_issue("Persistent issue")
        manager1.save_profile(profile1)

        # Second manager loads same profile
        manager2 = SystemProfileManager(profile_dir=temp_profile_dir)
        profile2 = manager2.load_profile()

        assert profile2 is not None
        assert "Persistent issue" in profile2.known_issues

    def test_profile_json_format(self, temp_profile_dir: Path) -> None:
        """Test that saved profile has correct JSON format."""
        manager = SystemProfileManager(profile_dir=temp_profile_dir)

        profile = SystemProfile(
            discovered_at="2024-01-15T10:00:00",
            username="retro",
            home_dir="/home/retro",
        )

        controller = ControllerProfile(
            name="Xbox Controller",
            controller_type="xbox",
            device_path="/dev/input/js0",
            configured=True,
        )
        profile.update_controller(controller)

        manager.save_profile(profile)

        # Read JSON directly
        with open(temp_profile_dir / "system-profile.json") as f:
            data = json.load(f)

        assert data["username"] == "retro"
        assert data["home_dir"] == "/home/retro"
        assert len(data["controllers"]) == 1
        assert data["controllers"][0]["name"] == "Xbox Controller"

    def test_complex_profile_serialization(self, temp_profile_dir: Path) -> None:
        """Test serialization of complex profile with all fields."""
        manager = SystemProfileManager(profile_dir=temp_profile_dir)

        profile = SystemProfile(
            discovered_at="2024-01-15T10:00:00",
            username="retro",
            home_dir="/home/retro",
            retropie_dir="/home/retro/RetroPie",
            hostname="retropie.local",
            cpu_temp_normal=55.5,
            memory_total=1024,
            raspberry_pi_model="Raspberry Pi 4B",
        )

        # Add complex data
        controller = ControllerProfile(
            name="DualShock 4",
            controller_type="ps4",
            device_path="/dev/input/js0",
            configured=True,
            driver_required="ds4drv",
            known_issues=["Bluetooth issues", "Battery drain"],
            last_tested="2024-01-15T09:00:00",
        )
        profile.update_controller(controller)

        emulator = EmulatorProfile(
            name="pcsx-rearmed",
            system="psx",
            status="configured",
            version="1.9.93",
            config_path="/opt/retropie/configs/psx/pcsx.cfg",
            bios_required=["scph1001.bin"],
            controller_issues=["Analog calibration needed"],
            performance_notes=["Enable frameskip"],
            last_used="2024-01-14T20:00:00",
        )
        profile.update_emulator(emulator)

        profile.add_known_issue("Audio issues")
        profile.resolve_issue("Old problem", "Fixed somehow")
        profile.add_user_note("Remember to backup")

        # Save and load
        manager.save_profile(profile)
        loaded = manager.load_profile()

        assert loaded is not None
        assert loaded.cpu_temp_normal == 55.5
        assert loaded.memory_total == 1024
        assert loaded.raspberry_pi_model == "Raspberry Pi 4B"
        assert len(loaded.controllers) == 1
        assert loaded.controllers[0].driver_required == "ds4drv"
        assert len(loaded.controllers[0].known_issues) == 2
        assert len(loaded.emulators) == 1
        assert loaded.emulators[0].version == "1.9.93"
        assert len(loaded.emulators[0].bios_required) == 1
