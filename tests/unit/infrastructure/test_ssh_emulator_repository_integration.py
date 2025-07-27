"""Integration tests for SSHEmulatorRepository with ESSystemsConfigParser."""

from unittest.mock import Mock

import pytest

from retromcp.config import RetroPieConfig
from retromcp.discovery import RetroPiePaths
from retromcp.domain.models import CommandResult
from retromcp.domain.models import ESSystemsConfig
from retromcp.domain.models import Result
from retromcp.domain.models import SystemDefinition
from retromcp.domain.models import ValidationError
from retromcp.domain.ports import ConfigurationParser
from retromcp.domain.ports import RetroPieClient
from retromcp.infrastructure.ssh_emulator_repository import SSHEmulatorRepository


@pytest.mark.unit
@pytest.mark.infrastructure
@pytest.mark.integration
class TestSSHEmulatorRepositoryParserIntegration:
    """Test integration of SSHEmulatorRepository with configuration parser."""

    @pytest.fixture
    def mock_client(self) -> Mock:
        """Create mock RetroPie client."""
        return Mock(spec=RetroPieClient)

    @pytest.fixture
    def mock_parser(self) -> Mock:
        """Create mock configuration parser."""
        return Mock(spec=ConfigurationParser)

    @pytest.fixture
    def test_config(self) -> RetroPieConfig:
        """Create test configuration."""
        paths = RetroPiePaths(
            home_dir="/home/retro",
            username="retro",
            retropie_dir="/home/retro/RetroPie",
            retropie_setup_dir="/home/retro/RetroPie-Setup",
            bios_dir="/home/retro/RetroPie/BIOS",
            roms_dir="/home/retro/RetroPie/roms",
            configs_dir="/opt/retropie/configs",
            emulators_dir="/opt/retropie/emulators",
        )
        return RetroPieConfig(
            host="test-retropie.local",
            username="retro",
            password="test_password",  # noqa: S106
            port=22,
            paths=paths,
        )

    @pytest.fixture
    def repository_with_parser(self, mock_client: Mock, test_config: RetroPieConfig, mock_parser: Mock) -> SSHEmulatorRepository:
        """Create repository instance with injected parser."""
        return SSHEmulatorRepository(mock_client, test_config, config_parser=mock_parser)

    @pytest.fixture
    def sample_es_systems_xml(self) -> str:
        """Sample es_systems.cfg XML content."""
        return """<?xml version="1.0"?>
<systemList>
    <system>
        <name>nes</name>
        <fullname>Nintendo Entertainment System</fullname>
        <path>/home/pi/RetroPie/roms/nes</path>
        <extension>.nes .zip .NES .ZIP</extension>
        <command>/opt/retropie/supplementary/runcommand/runcommand.sh 0 _SYS_ nes %ROM%</command>
        <platform>nes</platform>
        <theme>nes</theme>
    </system>
    <system>
        <name>snes</name>
        <fullname>Super Nintendo Entertainment System</fullname>
        <path>/home/pi/RetroPie/roms/snes</path>
        <extension>.smc .sfc .SMC .SFC</extension>
        <command>/opt/retropie/supplementary/runcommand/runcommand.sh 0 _SYS_ snes %ROM%</command>
        <platform>snes</platform>
        <theme>snes</theme>
    </system>
</systemList>"""

    def test_repository_accepts_parser_via_constructor(self, mock_client: Mock, test_config: RetroPieConfig, mock_parser: Mock):
        """Test that repository accepts parser via constructor injection."""
        # Act
        repository = SSHEmulatorRepository(mock_client, test_config, config_parser=mock_parser)

        # Assert
        assert repository is not None
        assert hasattr(repository, '_config_parser')
        assert repository._config_parser == mock_parser

    def test_repository_has_default_parser_when_none_provided(self, mock_client: Mock, test_config: RetroPieConfig):
        """Test that repository creates default parser when none provided."""
        # Act
        repository = SSHEmulatorRepository(mock_client, test_config)

        # Assert
        assert repository is not None
        assert hasattr(repository, '_config_parser')
        assert repository._config_parser is not None

    def test_get_supported_extensions_uses_parser_when_available(
        self, repository_with_parser: SSHEmulatorRepository, mock_client: Mock, mock_parser: Mock, sample_es_systems_xml: str
    ):
        """Test that get_supported_extensions uses parser to get extensions from es_systems.cfg."""
        # Arrange
        # Mock successful file read
        mock_client.execute_command.return_value = CommandResult(
            command="cat /etc/emulationstation/es_systems.cfg",
            exit_code=0,
            stdout=sample_es_systems_xml,
            stderr="",
            success=True,
            execution_time=0.1,
        )

        # Mock successful parsing
        expected_config = ESSystemsConfig(systems=[
            SystemDefinition(
                name="nes",
                fullname="Nintendo Entertainment System",
                path="/home/pi/RetroPie/roms/nes",
                extensions=[".nes", ".zip", ".NES", ".ZIP"],
                command="test command",
                platform="nes",
                theme="nes"
            ),
            SystemDefinition(
                name="snes",
                fullname="Super Nintendo Entertainment System",
                path="/home/pi/RetroPie/roms/snes",
                extensions=[".smc", ".sfc", ".SMC", ".SFC"],
                command="test command",
                platform="snes",
                theme="snes"
            )
        ])
        mock_parser.parse_es_systems_config.return_value = Result.success(expected_config)

        # Act
        extensions = repository_with_parser._get_supported_extensions("nes")

        # Assert
        assert extensions == [".nes", ".zip", ".NES", ".ZIP"]
        mock_client.execute_command.assert_called_once()
        mock_parser.parse_es_systems_config.assert_called_once_with(sample_es_systems_xml)

    def test_get_supported_extensions_falls_back_to_hardcoded_when_file_not_found(
        self, repository_with_parser: SSHEmulatorRepository, mock_client: Mock, mock_parser: Mock
    ):
        """Test fallback to hard-coded extensions when es_systems.cfg file not found."""
        # Arrange
        # Mock file not found
        mock_client.execute_command.return_value = CommandResult(
            command="cat /etc/emulationstation/es_systems.cfg",
            exit_code=1,
            stdout="",
            stderr="No such file or directory",
            success=False,
            execution_time=0.1,
        )

        # Act
        extensions = repository_with_parser._get_supported_extensions("nes")

        # Assert
        # Should fall back to hard-coded extensions for NES
        assert ".nes" in extensions
        assert ".zip" in extensions
        # Should try multiple file locations when files don't exist
        assert mock_client.execute_command.call_count >= 1
        # Parser should not be called when file read fails
        mock_parser.parse_es_systems_config.assert_not_called()

    def test_get_supported_extensions_falls_back_to_hardcoded_when_parsing_fails(
        self, repository_with_parser: SSHEmulatorRepository, mock_client: Mock, mock_parser: Mock
    ):
        """Test fallback to hard-coded extensions when XML parsing fails."""
        # Arrange
        # Mock successful file read but malformed content for all paths
        mock_client.execute_command.return_value = CommandResult(
            command="cat /etc/emulationstation/es_systems.cfg",
            exit_code=0,
            stdout="<invalid xml content>",
            stderr="",
            success=True,
            execution_time=0.1,
        )

        # Mock parsing failure
        mock_parser.parse_es_systems_config.return_value = Result.error(
            ValidationError(code="XML_PARSE_ERROR", message="Invalid XML")
        )

        # Act
        extensions = repository_with_parser._get_supported_extensions("snes")

        # Assert
        # Should fall back to hard-coded extensions for SNES
        assert ".smc" in extensions or ".sfc" in extensions  # One of the SNES extensions
        # Should try multiple paths when parsing fails
        assert mock_client.execute_command.call_count >= 1
        # Parser should be called at least once with the invalid content
        assert mock_parser.parse_es_systems_config.call_count >= 1

    def test_get_supported_extensions_caches_parsed_config(
        self, repository_with_parser: SSHEmulatorRepository, mock_client: Mock, mock_parser: Mock, sample_es_systems_xml: str
    ):
        """Test that parsed config is cached to avoid repeated SSH calls."""
        # Arrange
        mock_client.execute_command.return_value = CommandResult(
            command="cat /etc/emulationstation/es_systems.cfg",
            exit_code=0,
            stdout=sample_es_systems_xml,
            stderr="",
            success=True,
            execution_time=0.1,
        )

        expected_config = ESSystemsConfig(systems=[
            SystemDefinition(
                name="nes",
                fullname="Nintendo Entertainment System",
                path="/home/pi/RetroPie/roms/nes",
                extensions=[".nes", ".zip", ".NES", ".ZIP"],
                command="test command"
            )
        ])
        mock_parser.parse_es_systems_config.return_value = Result.success(expected_config)

        # Act - Call twice for different systems
        extensions1 = repository_with_parser._get_supported_extensions("nes")
        extensions2 = repository_with_parser._get_supported_extensions("nes")

        # Assert
        assert extensions1 == [".nes", ".zip", ".NES", ".ZIP"]
        assert extensions2 == [".nes", ".zip", ".NES", ".ZIP"]
        # SSH command should only be called once (cached)
        mock_client.execute_command.assert_called_once()
        mock_parser.parse_es_systems_config.assert_called_once()

    def test_get_supported_extensions_returns_empty_for_unknown_system_from_config(
        self, repository_with_parser: SSHEmulatorRepository, mock_client: Mock, mock_parser: Mock, sample_es_systems_xml: str
    ):
        """Test that unknown system returns fallback extensions when not in parsed config."""
        # Arrange
        mock_client.execute_command.return_value = CommandResult(
            command="cat /etc/emulationstation/es_systems.cfg",
            exit_code=0,
            stdout=sample_es_systems_xml,
            stderr="",
            success=True,
            execution_time=0.1,
        )

        # Config only has NES and SNES
        expected_config = ESSystemsConfig(systems=[
            SystemDefinition(
                name="nes",
                fullname="Nintendo Entertainment System",
                path="/test",
                extensions=[".nes", ".zip"],
                command="test"
            )
        ])
        mock_parser.parse_es_systems_config.return_value = Result.success(expected_config)

        # Act - Request unknown system
        extensions = repository_with_parser._get_supported_extensions("unknown_system")

        # Assert
        # Should fall back to default extensions for unknown systems
        assert isinstance(extensions, list)
        # Default fallback should include common extensions
        assert ".zip" in extensions or ".7z" in extensions

    def test_get_supported_extensions_handles_ssh_timeout_gracefully(
        self, repository_with_parser: SSHEmulatorRepository, mock_client: Mock, mock_parser: Mock
    ):
        """Test graceful handling of SSH timeout when reading es_systems.cfg."""
        # Arrange
        # Mock SSH timeout
        mock_client.execute_command.side_effect = Exception("SSH timeout")

        # Act
        extensions = repository_with_parser._get_supported_extensions("nes")

        # Assert
        # Should fall back to hard-coded extensions
        assert isinstance(extensions, list)
        assert len(extensions) > 0
        assert mock_client.execute_command.call_count >= 1
        # Parser should not be called when SSH fails
        mock_parser.parse_es_systems_config.assert_not_called()

    def test_repository_uses_different_es_systems_file_paths(
        self, repository_with_parser: SSHEmulatorRepository, mock_client: Mock, mock_parser: Mock
    ):
        """Test that repository tries different es_systems.cfg file locations."""
        # Arrange
        # Mock first location fails, second succeeds
        mock_client.execute_command.side_effect = [
            # First attempt: /etc/emulationstation/es_systems.cfg fails
            CommandResult(
                command="cat /etc/emulationstation/es_systems.cfg",
                exit_code=1,
                stdout="",
                stderr="No such file",
                success=False,
                execution_time=0.1,
            ),
            # Second attempt: ~/.emulationstation/es_systems.cfg succeeds
            CommandResult(
                command="cat ~/.emulationstation/es_systems.cfg",
                exit_code=0,
                stdout="<?xml version='1.0'?><systemList></systemList>",
                stderr="",
                success=True,
                execution_time=0.1,
            )
        ]

        mock_parser.parse_es_systems_config.return_value = Result.success(
            ESSystemsConfig(systems=[])
        )

        # Act
        extensions = repository_with_parser._get_supported_extensions("nes")

        # Assert
        assert isinstance(extensions, list)
        # Should have tried multiple file locations
        assert mock_client.execute_command.call_count >= 1
        mock_parser.parse_es_systems_config.assert_called_once()
