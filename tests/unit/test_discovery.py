"""Unit tests for RetroPie discovery module."""

from unittest.mock import Mock

import pytest

from retromcp.discovery import RetroPieDiscovery
from retromcp.discovery import RetroPiePaths
from retromcp.domain.models import CommandResult
from retromcp.domain.ports import RetroPieClient


class TestRetroPiePaths:
    """Test cases for RetroPiePaths dataclass."""

    def test_retropie_paths_creation_minimal(self) -> None:
        """Test creating RetroPiePaths with minimal required fields."""
        paths = RetroPiePaths(home_dir="/home/retro", username="retro")

        assert paths.home_dir == "/home/retro"
        assert paths.username == "retro"
        assert paths.retropie_dir is None
        assert paths.retropie_setup_dir is None
        assert paths.bios_dir is None
        assert paths.roms_dir is None
        assert paths.configs_dir == "/opt/retropie/configs"
        assert paths.emulators_dir == "/opt/retropie/emulators"

    def test_retropie_paths_creation_full(self) -> None:
        """Test creating RetroPiePaths with all fields."""
        paths = RetroPiePaths(
            home_dir="/home/retro",
            username="retro",
            retropie_dir="/home/retro/RetroPie",
            retropie_setup_dir="/home/retro/RetroPie-Setup",
            bios_dir="/home/retro/RetroPie/BIOS",
            roms_dir="/home/retro/RetroPie/roms",
            configs_dir="/custom/configs",
            emulators_dir="/custom/emulators",
        )

        assert paths.home_dir == "/home/retro"
        assert paths.username == "retro"
        assert paths.retropie_dir == "/home/retro/RetroPie"
        assert paths.retropie_setup_dir == "/home/retro/RetroPie-Setup"
        assert paths.bios_dir == "/home/retro/RetroPie/BIOS"
        assert paths.roms_dir == "/home/retro/RetroPie/roms"
        assert paths.configs_dir == "/custom/configs"
        assert paths.emulators_dir == "/custom/emulators"

    def test_retropie_paths_frozen(self) -> None:
        """Test that RetroPiePaths is frozen (immutable)."""
        paths = RetroPiePaths(home_dir="/home/retro", username="retro")

        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            paths.home_dir = "/different/path"  # type: ignore


class TestRetroPieDiscovery:
    """Test cases for RetroPie discovery."""

    @pytest.fixture
    def mock_client(self) -> Mock:
        """Create mock RetroPie client."""
        return Mock(spec=RetroPieClient)

    @pytest.fixture
    def discovery(self, mock_client: Mock) -> RetroPieDiscovery:
        """Create RetroPie discovery instance."""
        return RetroPieDiscovery(mock_client)

    def test_discovery_initialization(self, mock_client: Mock) -> None:
        """Test discovery initialization."""
        discovery = RetroPieDiscovery(mock_client)
        assert discovery._client == mock_client

    def test_discover_system_paths_success(
        self, discovery: RetroPieDiscovery, mock_client: Mock
    ) -> None:
        """Test successful system paths discovery."""
        # Mock successful command results
        mock_client.execute_command.side_effect = [
            CommandResult(
                command="pwd",
                exit_code=0,
                stdout="/home/retro",
                stderr="",
                success=True,
                execution_time=0.1,
            ),  # home directory
            CommandResult(
                command="whoami",
                exit_code=0,
                stdout="retro",
                stderr="",
                success=True,
                execution_time=0.1,
            ),  # username
            CommandResult(
                command="test -d /home/retro/RetroPie",
                exit_code=0,
                stdout="",
                stderr="",
                success=True,
                execution_time=0.1,
            ),  # retropie dir exists
            CommandResult(
                command="test -d /home/retro/RetroPie-Setup",
                exit_code=0,
                stdout="",
                stderr="",
                success=True,
                execution_time=0.1,
            ),  # setup dir exists
            CommandResult(
                command="test -d /home/retro/RetroPie/BIOS",
                exit_code=0,
                stdout="",
                stderr="",
                success=True,
                execution_time=0.1,
            ),  # bios dir exists
            CommandResult(
                command="test -d /home/retro/RetroPie/roms",
                exit_code=0,
                stdout="",
                stderr="",
                success=True,
                execution_time=0.1,
            ),  # roms dir exists
        ]

        paths = discovery.discover_system_paths()

        assert paths.home_dir == "/home/retro"
        assert paths.username == "retro"
        assert paths.retropie_dir == "/home/retro/RetroPie"
        assert paths.retropie_setup_dir == "/home/retro/RetroPie-Setup"
        assert paths.bios_dir == "/home/retro/RetroPie/BIOS"
        assert paths.roms_dir == "/home/retro/RetroPie/roms"

    def test_discover_system_paths_partial_installation(
        self, discovery: RetroPieDiscovery, mock_client: Mock
    ) -> None:
        """Test discovery with partial RetroPie installation."""
        # Mock mixed success/failure results
        mock_client.execute_command.side_effect = [
            CommandResult(
                command="pwd",
                exit_code=0,
                stdout="/home/pi",
                stderr="",
                success=True,
                execution_time=0.1,
            ),  # home directory
            CommandResult(
                command="whoami",
                exit_code=0,
                stdout="pi",
                stderr="",
                success=True,
                execution_time=0.1,
            ),  # username
            CommandResult(
                command="test -d /home/pi/RetroPie",
                exit_code=1,
                stdout="",
                stderr="",
                success=False,
                execution_time=0.1,
            ),  # retropie dir missing
            CommandResult(
                command="test -d /home/pi/RetroPie-Setup",
                exit_code=0,
                stdout="",
                stderr="",
                success=True,
                execution_time=0.1,
            ),  # setup dir exists
            CommandResult(
                command="test -d /home/pi/RetroPie/BIOS",
                exit_code=1,
                stdout="",
                stderr="",
                success=False,
                execution_time=0.1,
            ),  # bios dir missing
            CommandResult(
                command="test -d /home/pi/RetroPie/roms",
                exit_code=1,
                stdout="",
                stderr="",
                success=False,
                execution_time=0.1,
            ),  # roms dir missing
        ]

        paths = discovery.discover_system_paths()

        assert paths.home_dir == "/home/pi"
        assert paths.username == "pi"
        assert paths.retropie_dir is None  # Not found
        assert paths.retropie_setup_dir == "/home/pi/RetroPie-Setup"  # Found
        assert paths.bios_dir is None  # Not found
        assert paths.roms_dir is None  # Not found

    def test_discover_system_paths_command_failures(
        self, discovery: RetroPieDiscovery, mock_client: Mock
    ) -> None:
        """Test discovery with command failures."""
        # Mock failed command results
        mock_client.execute_command.side_effect = [
            CommandResult(
                command="pwd",
                exit_code=1,
                stdout="",
                stderr="pwd failed",
                success=False,
                execution_time=0.1,
            ),  # home directory command fails
            CommandResult(
                command="whoami",
                exit_code=1,
                stdout="",
                stderr="whoami failed",
                success=False,
                execution_time=0.1,
            ),  # username command fails
            CommandResult(
                command="test -d unknown/RetroPie",
                exit_code=1,
                stdout="",
                stderr="",
                success=False,
                execution_time=0.1,
            ),  # retropie dir
            CommandResult(
                command="test -d unknown/RetroPie-Setup",
                exit_code=1,
                stdout="",
                stderr="",
                success=False,
                execution_time=0.1,
            ),  # setup dir
            CommandResult(
                command="test -d unknown/RetroPie/BIOS",
                exit_code=1,
                stdout="",
                stderr="",
                success=False,
                execution_time=0.1,
            ),  # bios dir
            CommandResult(
                command="test -d unknown/RetroPie/roms",
                exit_code=1,
                stdout="",
                stderr="",
                success=False,
                execution_time=0.1,
            ),  # roms dir
        ]

        paths = discovery.discover_system_paths()

        assert paths.home_dir == "unknown"  # Fallback value
        assert paths.username == "unknown"  # Fallback value
        assert paths.retropie_dir is None
        assert paths.retropie_setup_dir is None
        assert paths.bios_dir is None
        assert paths.roms_dir is None

    def test_discover_home_directory_success(
        self, discovery: RetroPieDiscovery, mock_client: Mock
    ) -> None:
        """Test successful home directory discovery."""
        mock_client.execute_command.return_value = CommandResult(
            command="pwd",
            exit_code=0,
            stdout="/home/custom_user",
            stderr="",
            success=True,
            execution_time=0.1,
        )

        # Call private method through discovery
        mock_client.execute_command.side_effect = [
            CommandResult(
                command="pwd",
                exit_code=0,
                stdout="/home/custom_user",
                stderr="",
                success=True,
                execution_time=0.1,
            ),  # home directory
            CommandResult(
                command="whoami",
                exit_code=0,
                stdout="custom_user",
                stderr="",
                success=True,
                execution_time=0.1,
            ),  # username
            # All other directory checks fail
            CommandResult(
                command="test -d /home/custom_user/RetroPie",
                exit_code=1,
                stdout="",
                stderr="",
                success=False,
                execution_time=0.1,
            ),
            CommandResult(
                command="test -d /home/custom_user/RetroPie-Setup",
                exit_code=1,
                stdout="",
                stderr="",
                success=False,
                execution_time=0.1,
            ),
            CommandResult(
                command="test -d /home/custom_user/RetroPie/BIOS",
                exit_code=1,
                stdout="",
                stderr="",
                success=False,
                execution_time=0.1,
            ),
            CommandResult(
                command="test -d /home/custom_user/RetroPie/roms",
                exit_code=1,
                stdout="",
                stderr="",
                success=False,
                execution_time=0.1,
            ),
        ]

        paths = discovery.discover_system_paths()
        assert paths.home_dir == "/home/custom_user"

    def test_discover_username_success(
        self, discovery: RetroPieDiscovery, mock_client: Mock
    ) -> None:
        """Test successful username discovery."""
        mock_client.execute_command.side_effect = [
            CommandResult(
                command="pwd",
                exit_code=0,
                stdout="/home/test_user",
                stderr="",
                success=True,
                execution_time=0.1,
            ),  # home directory
            CommandResult(
                command="whoami",
                exit_code=0,
                stdout="test_user",
                stderr="",
                success=True,
                execution_time=0.1,
            ),  # username
            # All directory checks fail for simplicity
            CommandResult(
                command="test -d /home/test_user/RetroPie",
                exit_code=1,
                stdout="",
                stderr="",
                success=False,
                execution_time=0.1,
            ),
            CommandResult(
                command="test -d /home/test_user/RetroPie-Setup",
                exit_code=1,
                stdout="",
                stderr="",
                success=False,
                execution_time=0.1,
            ),
            CommandResult(
                command="test -d /home/test_user/RetroPie/BIOS",
                exit_code=1,
                stdout="",
                stderr="",
                success=False,
                execution_time=0.1,
            ),
            CommandResult(
                command="test -d /home/test_user/RetroPie/roms",
                exit_code=1,
                stdout="",
                stderr="",
                success=False,
                execution_time=0.1,
            ),
        ]

        paths = discovery.discover_system_paths()
        assert paths.username == "test_user"

    def test_discovery_paths_with_alternative_locations(
        self, discovery: RetroPieDiscovery, mock_client: Mock
    ) -> None:
        """Test discovery with alternative RetroPie installation locations."""
        mock_client.execute_command.side_effect = [
            CommandResult(
                command="pwd",
                exit_code=0,
                stdout="/opt/retropie",
                stderr="",
                success=True,
                execution_time=0.1,
            ),  # different home
            CommandResult(
                command="whoami",
                exit_code=0,
                stdout="retropie",
                stderr="",
                success=True,
                execution_time=0.1,
            ),  # system user
            CommandResult(
                command="test -d /opt/retropie/RetroPie",
                exit_code=0,
                stdout="",
                stderr="",
                success=True,
                execution_time=0.1,
            ),  # retropie in opt
            CommandResult(
                command="test -d /opt/retropie/RetroPie-Setup",
                exit_code=1,
                stdout="",
                stderr="",
                success=False,
                execution_time=0.1,
            ),  # no setup dir
            CommandResult(
                command="test -d /opt/retropie/RetroPie/BIOS",
                exit_code=0,
                stdout="",
                stderr="",
                success=True,
                execution_time=0.1,
            ),  # bios exists
            CommandResult(
                command="test -d /opt/retropie/RetroPie/roms",
                exit_code=0,
                stdout="",
                stderr="",
                success=True,
                execution_time=0.1,
            ),  # roms exists
        ]

        paths = discovery.discover_system_paths()

        assert paths.home_dir == "/opt/retropie"
        assert paths.username == "retropie"
        assert paths.retropie_dir == "/opt/retropie/RetroPie"
        assert paths.retropie_setup_dir is None  # Not found
        assert paths.bios_dir == "/opt/retropie/RetroPie/BIOS"
        assert paths.roms_dir == "/opt/retropie/RetroPie/roms"

    def test_discovery_with_whitespace_output(
        self, discovery: RetroPieDiscovery, mock_client: Mock
    ) -> None:
        """Test discovery handles whitespace in command output."""
        mock_client.execute_command.side_effect = [
            CommandResult(
                command="pwd",
                exit_code=0,
                stdout="  /home/retro  \n",  # Extra whitespace
                stderr="",
                success=True,
                execution_time=0.1,
            ),  # home directory
            CommandResult(
                command="whoami",
                exit_code=0,
                stdout="\n  retro  \n",  # Extra whitespace and newlines
                stderr="",
                success=True,
                execution_time=0.1,
            ),  # username
            # Directory checks
            CommandResult(
                command="test -d /home/retro/RetroPie",
                exit_code=0,
                stdout="",
                stderr="",
                success=True,
                execution_time=0.1,
            ),
            CommandResult(
                command="test -d /home/retro/RetroPie-Setup",
                exit_code=1,
                stdout="",
                stderr="",
                success=False,
                execution_time=0.1,
            ),
            CommandResult(
                command="test -d /home/retro/RetroPie/BIOS",
                exit_code=1,
                stdout="",
                stderr="",
                success=False,
                execution_time=0.1,
            ),
            CommandResult(
                command="test -d /home/retro/RetroPie/roms",
                exit_code=1,
                stdout="",
                stderr="",
                success=False,
                execution_time=0.1,
            ),
        ]

        paths = discovery.discover_system_paths()

        # Should properly strip whitespace
        assert paths.home_dir == "/home/retro"
        assert paths.username == "retro"

    def test_discovery_empty_command_output(
        self, discovery: RetroPieDiscovery, mock_client: Mock
    ) -> None:
        """Test discovery with empty command output."""
        mock_client.execute_command.side_effect = [
            CommandResult(
                command="pwd",
                exit_code=0,
                stdout="",  # Empty output
                stderr="",
                success=True,
                execution_time=0.1,
            ),  # home directory
            CommandResult(
                command="whoami",
                exit_code=0,
                stdout="",  # Empty output
                stderr="",
                success=True,
                execution_time=0.1,
            ),  # username
            # Directory checks (will fail due to empty home_dir)
            CommandResult(
                command="test -d /RetroPie",
                exit_code=1,
                stdout="",
                stderr="",
                success=False,
                execution_time=0.1,
            ),
            CommandResult(
                command="test -d /RetroPie-Setup",
                exit_code=1,
                stdout="",
                stderr="",
                success=False,
                execution_time=0.1,
            ),
            CommandResult(
                command="test -d /RetroPie/BIOS",
                exit_code=1,
                stdout="",
                stderr="",
                success=False,
                execution_time=0.1,
            ),
            CommandResult(
                command="test -d /RetroPie/roms",
                exit_code=1,
                stdout="",
                stderr="",
                success=False,
                execution_time=0.1,
            ),
        ]

        paths = discovery.discover_system_paths()

        # Should use fallback values for empty outputs
        assert paths.home_dir == "unknown"  # Fallback value for empty command
        assert paths.username == "unknown"  # Fallback value for empty command
