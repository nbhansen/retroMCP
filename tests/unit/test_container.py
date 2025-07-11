"""Unit tests for dependency injection container."""

from unittest.mock import Mock
from unittest.mock import patch

import pytest

from retromcp.config import RetroPieConfig
from retromcp.container import Container
from retromcp.discovery import RetroPiePaths
from retromcp.domain.ports import RetroPieClient
from retromcp.ssh_handler import RetroPieSSH


class TestContainer:
    """Test dependency injection container."""

    @pytest.fixture
    def config(self) -> RetroPieConfig:
        """Provide test configuration."""
        return RetroPieConfig(
            host="test-retropie.local",
            username="retro",
            password="test_password",
            port=22,
        )

    @pytest.fixture
    def container(self, config: RetroPieConfig) -> Container:
        """Provide container instance."""
        return Container(config)

    def test_init(self, config: RetroPieConfig):
        """Test container initialization."""
        container = Container(config)

        assert container._initial_config == config
        assert container.config == config
        assert container._instances == {}
        assert container._discovery_completed is False

    def test_get_or_create_new_instance(self, container: Container):
        """Test _get_or_create creates new instance."""
        # Arrange
        mock_instance = Mock()
        factory = Mock(return_value=mock_instance)

        # Act
        result = container._get_or_create("test_key", factory)

        # Assert
        assert result == mock_instance
        assert container._instances["test_key"] == mock_instance
        factory.assert_called_once()

    def test_get_or_create_existing_instance(self, container: Container):
        """Test _get_or_create returns existing instance."""
        # Arrange
        mock_instance = Mock()
        container._instances["test_key"] = mock_instance
        factory = Mock()

        # Act
        result = container._get_or_create("test_key", factory)

        # Assert
        assert result == mock_instance
        factory.assert_not_called()

    @patch("retromcp.container.RetroPieDiscovery")
    def test_ensure_discovery_success(
        self, mock_discovery_class: Mock, container: Container
    ):
        """Test successful system discovery."""
        # Arrange
        mock_paths = RetroPiePaths(
            home_dir="/home/retro",
            username="retro",
            retropie_dir="/home/retro/RetroPie",
            retropie_setup_dir="/home/retro/RetroPie-Setup",
            bios_dir="/home/retro/RetroPie/BIOS",
            roms_dir="/home/retro/RetroPie/roms",
            configs_dir="/opt/retropie/configs",
            emulators_dir="/opt/retropie/emulators",
        )

        mock_discovery = Mock()
        mock_discovery.discover_system_paths.return_value = mock_paths
        mock_discovery_class.return_value = mock_discovery

        mock_client = Mock(spec=RetroPieClient)
        container._instances["retropie_client"] = mock_client

        # Act
        container._ensure_discovery()

        # Assert
        assert container._discovery_completed is True
        assert container.config.retropie_dir == "/home/retro/RetroPie"
        mock_discovery_class.assert_called_once_with(mock_client)
        mock_discovery.discover_system_paths.assert_called_once()

    @patch("retromcp.container.RetroPieDiscovery")
    def test_ensure_discovery_failure(
        self, mock_discovery_class: Mock, container: Container
    ):
        """Test failed system discovery."""
        # Arrange
        mock_discovery_class.side_effect = Exception("Discovery failed")
        mock_client = Mock(spec=RetroPieClient)
        container._instances["retropie_client"] = mock_client

        # Act
        container._ensure_discovery()

        # Assert
        assert (
            container._discovery_completed is True
        )  # Still marked complete to avoid retry
        assert container.config == container._initial_config  # Config unchanged

    def test_ensure_discovery_already_completed(self, container: Container):
        """Test _ensure_discovery when already completed."""
        # Arrange
        container._discovery_completed = True

        # Act
        with patch("retromcp.container.RetroPieDiscovery") as mock_discovery:
            container._ensure_discovery()

        # Assert
        mock_discovery.assert_not_called()

    def test_ssh_handler_property(self, container: Container):
        """Test ssh_handler property."""
        # Act
        handler = container.ssh_handler

        # Assert
        assert isinstance(handler, RetroPieSSH)
        assert handler.host == "test-retropie.local"
        assert handler.username == "retro"
        assert handler.port == 22

        # Test singleton behavior
        handler2 = container.ssh_handler
        assert handler is handler2

    def test_retropie_client_property(self, container: Container):
        """Test retropie_client property."""
        # Act
        client = container.retropie_client

        # Assert
        assert client is not None

        # Test singleton behavior
        client2 = container.retropie_client
        assert client is client2

    def test_system_repository_property(self, container: Container):
        """Test system_repository property triggers discovery."""
        # Arrange
        with patch.object(container, "_ensure_discovery") as mock_ensure:
            # Act
            repo = container.system_repository

            # Assert
            assert repo is not None
            mock_ensure.assert_called_once()

    def test_controller_repository_property(self, container: Container):
        """Test controller_repository property triggers discovery."""
        # Arrange
        with patch.object(container, "_ensure_discovery") as mock_ensure:
            # Act
            repo = container.controller_repository

            # Assert
            assert repo is not None
            mock_ensure.assert_called_once()

    def test_emulator_repository_property(self, container: Container):
        """Test emulator_repository property triggers discovery."""
        # Arrange
        with patch.object(container, "_ensure_discovery") as mock_ensure:
            # Act
            repo = container.emulator_repository

            # Assert
            assert repo is not None
            mock_ensure.assert_called_once()

    def test_use_case_properties(self, container: Container):
        """Test use case properties return instances."""
        # Test all use case properties exist and return instances
        assert container.test_connection_use_case is not None
        assert container.get_system_info_use_case is not None
        assert container.install_packages_use_case is not None
        assert container.update_system_use_case is not None
        assert container.detect_controllers_use_case is not None
        assert container.setup_controller_use_case is not None
        assert container.install_emulator_use_case is not None

    def test_connect(self, container: Container):
        """Test connect method."""
        # Arrange
        mock_client = Mock(spec=RetroPieClient)
        mock_client.connect.return_value = True
        container._instances["retropie_client"] = mock_client

        # Act
        result = container.connect()

        # Assert
        assert result is True
        mock_client.connect.assert_called_once()

    def test_disconnect_with_client(self, container: Container):
        """Test disconnect when client exists."""
        # Arrange
        mock_client = Mock(spec=RetroPieClient)
        container._instances["retropie_client"] = mock_client

        # Act
        container.disconnect()

        # Assert
        mock_client.disconnect.assert_called_once()

    def test_disconnect_without_client(self, container: Container):
        """Test disconnect when no client exists."""
        # Act (should not raise exception)
        container.disconnect()

        # Assert - no exception raised
