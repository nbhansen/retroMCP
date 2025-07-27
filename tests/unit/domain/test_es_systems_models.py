"""Unit tests for es_systems configuration domain models."""

import pytest

from retromcp.domain.models import ESSystemsConfig
from retromcp.domain.models import SystemDefinition


@pytest.mark.unit
@pytest.mark.domain
class TestSystemDefinition:
    """Test cases for SystemDefinition domain model."""

    def test_system_definition_creation_with_required_fields(self):
        """Test SystemDefinition creation with all required fields."""
        # Arrange & Act
        system_def = SystemDefinition(
            name="nes",
            fullname="Nintendo Entertainment System",
            path="/home/pi/RetroPie/roms/nes",
            extensions=[".nes", ".zip", ".NES", ".ZIP"],
            command="/opt/retropie/supplementary/runcommand/runcommand.sh 0 _SYS_ nes %ROM%"
        )

        # Assert
        assert system_def.name == "nes"
        assert system_def.fullname == "Nintendo Entertainment System"
        assert system_def.path == "/home/pi/RetroPie/roms/nes"
        assert system_def.extensions == [".nes", ".zip", ".NES", ".ZIP"]
        assert "/opt/retropie/supplementary/runcommand/runcommand.sh" in system_def.command
        assert system_def.platform is None  # Optional field
        assert system_def.theme is None  # Optional field

    def test_system_definition_creation_with_all_fields(self):
        """Test SystemDefinition creation with all fields including optional ones."""
        # Arrange & Act
        system_def = SystemDefinition(
            name="genesis",
            fullname="Sega Genesis",
            path="/home/pi/RetroPie/roms/genesis",
            extensions=[".gen", ".md", ".bin", ".zip"],
            command="/opt/retropie/supplementary/runcommand/runcommand.sh 0 _SYS_ genesis %ROM%",
            platform="genesis, megadrive",
            theme="genesis"
        )

        # Assert
        assert system_def.name == "genesis"
        assert system_def.fullname == "Sega Genesis"
        assert system_def.path == "/home/pi/RetroPie/roms/genesis"
        assert system_def.extensions == [".gen", ".md", ".bin", ".zip"]
        assert system_def.platform == "genesis, megadrive"
        assert system_def.theme == "genesis"

    def test_system_definition_is_immutable(self):
        """Test that SystemDefinition is immutable (frozen dataclass)."""
        # Arrange
        system_def = SystemDefinition(
            name="nes",
            fullname="Nintendo Entertainment System",
            path="/home/pi/RetroPie/roms/nes",
            extensions=[".nes", ".zip"],
            command="test command"
        )

        # Act & Assert
        with pytest.raises(AttributeError):
            system_def.name = "modified_name"  # type: ignore

    def test_system_definition_extensions_list_immutable(self):
        """Test that extensions list is properly handled for immutability."""
        # Arrange
        extensions = [".nes", ".zip"]
        system_def = SystemDefinition(
            name="nes",
            fullname="Nintendo Entertainment System",
            path="/home/pi/RetroPie/roms/nes",
            extensions=extensions,
            command="test command"
        )

        # Act - modify original list
        extensions.append(".7z")

        # Assert - system definition should not be affected
        assert ".7z" not in system_def.extensions
        assert len(system_def.extensions) == 2


@pytest.mark.unit
@pytest.mark.domain
class TestESSystemsConfig:
    """Test cases for ESSystemsConfig domain model."""

    def test_es_systems_config_creation_empty(self):
        """Test ESSystemsConfig creation with empty systems list."""
        # Arrange & Act
        config = ESSystemsConfig(systems=[])

        # Assert
        assert config.systems == []
        assert len(config.systems) == 0

    def test_es_systems_config_creation_with_systems(self):
        """Test ESSystemsConfig creation with multiple systems."""
        # Arrange
        nes_system = SystemDefinition(
            name="nes",
            fullname="Nintendo Entertainment System",
            path="/home/pi/RetroPie/roms/nes",
            extensions=[".nes", ".zip"],
            command="test command"
        )
        snes_system = SystemDefinition(
            name="snes",
            fullname="Super Nintendo Entertainment System",
            path="/home/pi/RetroPie/roms/snes",
            extensions=[".smc", ".sfc"],
            command="test command"
        )

        # Act
        config = ESSystemsConfig(systems=[nes_system, snes_system])

        # Assert
        assert len(config.systems) == 2
        assert config.systems[0].name == "nes"
        assert config.systems[1].name == "snes"

    def test_es_systems_config_is_immutable(self):
        """Test that ESSystemsConfig is immutable (frozen dataclass)."""
        # Arrange
        system = SystemDefinition(
            name="nes",
            fullname="Nintendo Entertainment System",
            path="/home/pi/RetroPie/roms/nes",
            extensions=[".nes", ".zip"],
            command="test command"
        )
        config = ESSystemsConfig(systems=[system])

        # Act & Assert
        with pytest.raises(AttributeError):
            config.systems = []  # type: ignore

    def test_es_systems_config_find_system_by_name(self):
        """Test finding a system by name in the configuration."""
        # Arrange
        nes_system = SystemDefinition(
            name="nes",
            fullname="Nintendo Entertainment System",
            path="/home/pi/RetroPie/roms/nes",
            extensions=[".nes", ".zip"],
            command="test command"
        )
        genesis_system = SystemDefinition(
            name="genesis",
            fullname="Sega Genesis",
            path="/home/pi/RetroPie/roms/genesis",
            extensions=[".gen", ".md"],
            command="test command"
        )
        config = ESSystemsConfig(systems=[nes_system, genesis_system])

        # Act
        found_system = next((s for s in config.systems if s.name == "nes"), None)
        not_found_system = next((s for s in config.systems if s.name == "nonexistent"), None)

        # Assert
        assert found_system is not None
        assert found_system.name == "nes"
        assert found_system.fullname == "Nintendo Entertainment System"
        assert not_found_system is None
