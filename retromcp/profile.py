"""RetroPie system profile management and caching."""

import json
import logging
from dataclasses import asdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable
from typing import List
from typing import Optional

from .discovery import RetroPiePaths

logger = logging.getLogger(__name__)


@dataclass
class ControllerProfile:
    """Profile information for a controller."""

    name: str
    controller_type: str
    device_path: str
    configured: bool
    driver_required: Optional[str] = None
    known_issues: List[str] = None
    last_tested: Optional[str] = None

    def __post_init__(self) -> None:
        """Initialize mutable fields."""
        if self.known_issues is None:
            self.known_issues = []


@dataclass
class EmulatorProfile:
    """Profile information for an emulator."""

    name: str
    system: str
    status: str
    version: Optional[str] = None
    config_path: Optional[str] = None
    bios_required: List[str] = None
    controller_issues: List[str] = None
    performance_notes: List[str] = None
    last_used: Optional[str] = None

    def __post_init__(self) -> None:
        """Initialize mutable fields."""
        if self.bios_required is None:
            self.bios_required = []
        if self.controller_issues is None:
            self.controller_issues = []
        if self.performance_notes is None:
            self.performance_notes = []


@dataclass
class SystemProfile:
    """Complete RetroPie system profile."""

    # Discovery info
    discovered_at: str
    username: str
    home_dir: str
    retropie_dir: Optional[str] = None
    retropie_setup_dir: Optional[str] = None
    bios_dir: Optional[str] = None
    roms_dir: Optional[str] = None

    # System specs
    hostname: Optional[str] = None
    cpu_temp_normal: Optional[float] = None
    memory_total: Optional[int] = None
    raspberry_pi_model: Optional[str] = None

    # Installed components
    controllers: List[ControllerProfile] = None
    emulators: List[EmulatorProfile] = None

    # User preferences and known issues
    preferred_install_method: str = "binary"
    known_issues: List[str] = None
    resolved_issues: List[str] = None
    user_notes: List[str] = None

    def __post_init__(self) -> None:
        """Initialize mutable fields."""
        if self.controllers is None:
            self.controllers = []
        if self.emulators is None:
            self.emulators = []
        if self.known_issues is None:
            self.known_issues = []
        if self.resolved_issues is None:
            self.resolved_issues = []
        if self.user_notes is None:
            self.user_notes = []

    @classmethod
    def from_discovery(cls, paths: RetroPiePaths) -> "SystemProfile":
        """Create profile from discovery results."""
        return cls(
            discovered_at=datetime.now().isoformat(),
            username=paths.username,
            home_dir=paths.home_dir,
            retropie_dir=paths.retropie_dir,
            retropie_setup_dir=paths.retropie_setup_dir,
            bios_dir=paths.bios_dir,
            roms_dir=paths.roms_dir,
        )

    def update_controller(self, controller_profile: ControllerProfile) -> None:
        """Update or add controller profile."""
        # Remove existing controller with same device path
        self.controllers = [c for c in self.controllers if c.device_path != controller_profile.device_path]
        self.controllers.append(controller_profile)

    def update_emulator(self, emulator_profile: EmulatorProfile) -> None:
        """Update or add emulator profile."""
        # Remove existing emulator with same name and system
        self.emulators = [
            e for e in self.emulators
            if not (e.name == emulator_profile.name and e.system == emulator_profile.system)
        ]
        self.emulators.append(emulator_profile)

    def add_known_issue(self, issue: str) -> None:
        """Add a known issue."""
        if issue not in self.known_issues:
            self.known_issues.append(issue)

    def resolve_issue(self, issue: str, solution: str) -> None:
        """Mark an issue as resolved and record the solution."""
        if issue in self.known_issues:
            self.known_issues.remove(issue)

        resolution = f"{issue} -> {solution}"
        if resolution not in self.resolved_issues:
            self.resolved_issues.append(resolution)

    def add_user_note(self, note: str) -> None:
        """Add a user note."""
        if note not in self.user_notes:
            self.user_notes.append(note)

    def to_context_summary(self) -> str:
        """Generate a context summary for AI conversations."""
        lines = [
            f"RetroPie System Profile (User: {self.username})",
            f"Home: {self.home_dir}",
        ]

        if self.retropie_dir:
            lines.append(f"RetroPie: {self.retropie_dir}")

        if self.hostname:
            lines.append(f"Host: {self.hostname}")

        if self.controllers:
            lines.append("\nControllers:")
            for controller in self.controllers:
                status = "✓ Configured" if controller.configured else "⚠ Not configured"
                lines.append(f"  - {controller.name} ({controller.controller_type}) {status}")
                if controller.known_issues:
                    for issue in controller.known_issues:
                        lines.append(f"    Issue: {issue}")

        if self.emulators:
            lines.append("\nEmulators:")
            for emulator in self.emulators:
                lines.append(f"  - {emulator.name} ({emulator.system}) - {emulator.status}")
                if emulator.controller_issues:
                    for issue in emulator.controller_issues:
                        lines.append(f"    Controller issue: {issue}")

        if self.known_issues:
            lines.append("\nKnown Issues:")
            for issue in self.known_issues:
                lines.append(f"  - {issue}")

        if self.resolved_issues:
            lines.append("\nPreviously Resolved:")
            for resolution in self.resolved_issues[-3:]:  # Show last 3
                lines.append(f"  - {resolution}")

        return "\n".join(lines)


class SystemProfileManager:
    """Manages RetroPie system profile persistence."""

    def __init__(self, profile_dir: Optional[Path] = None) -> None:
        """Initialize profile manager."""
        self.profile_dir = profile_dir or Path.home() / ".retromcp"
        self.profile_path = self.profile_dir / "system-profile.json"
        self._profile: Optional[SystemProfile] = None

    def ensure_profile_dir(self) -> None:
        """Ensure profile directory exists."""
        self.profile_dir.mkdir(exist_ok=True)

    def load_profile(self) -> Optional[SystemProfile]:
        """Load system profile from disk."""
        if not self.profile_path.exists():
            logger.info("No existing system profile found")
            return None

        try:
            with open(self.profile_path) as f:
                data = json.load(f)

            # Convert controller and emulator dicts back to dataclasses
            controllers = [ControllerProfile(**c) for c in data.get('controllers', [])]
            emulators = [EmulatorProfile(**e) for e in data.get('emulators', [])]

            data['controllers'] = controllers
            data['emulators'] = emulators

            profile = SystemProfile(**data)
            logger.info(f"Loaded system profile for {profile.username}")
            return profile

        except Exception as e:
            logger.error(f"Failed to load system profile: {e}")
            return None

    def save_profile(self, profile: SystemProfile) -> None:
        """Save system profile to disk."""
        try:
            self.ensure_profile_dir()

            # Convert to dict with dataclass serialization
            data = asdict(profile)

            with open(self.profile_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)

            logger.info(f"Saved system profile for {profile.username}")

        except Exception as e:
            logger.error(f"Failed to save system profile: {e}")

    def get_or_create_profile(self, paths: RetroPiePaths) -> SystemProfile:
        """Get existing profile or create new one from discovery."""
        # Try to load existing profile
        profile = self.load_profile()

        if profile is None:
            # Create new profile from discovery
            logger.info("Creating new system profile from discovery")
            profile = SystemProfile.from_discovery(paths)
            self.save_profile(profile)
        else:
            # Update discovery info if paths have changed
            if (profile.home_dir != paths.home_dir or
                profile.retropie_dir != paths.retropie_dir):
                logger.info("Updating profile with new discovery info")
                profile.home_dir = paths.home_dir
                profile.username = paths.username
                profile.retropie_dir = paths.retropie_dir
                profile.retropie_setup_dir = paths.retropie_setup_dir
                profile.bios_dir = paths.bios_dir
                profile.roms_dir = paths.roms_dir
                profile.discovered_at = datetime.now().isoformat()
                self.save_profile(profile)

        self._profile = profile
        return profile

    def update_profile(self, updater: Callable[[SystemProfile], None]) -> None:
        """Update profile using a function and save."""
        if self._profile:
            updater(self._profile)
            self.save_profile(self._profile)

    @property
    def current_profile(self) -> Optional[SystemProfile]:
        """Get current profile."""
        return self._profile

