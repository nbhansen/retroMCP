"""Unit tests for config module."""

import os
from unittest.mock import patch

import pytest

from retromcp.config import RetroPieConfig
from retromcp.discovery import RetroPiePaths


class TestRetroPieConfig:
    """Test cases for RetroPie configuration."""

    def test_config_creation_minimal(self) -> None:
        """Test creating config with minimal required fields."""
        config = RetroPieConfig(host="retropie.local", username="retro")

        assert config.host == "retropie.local"
        assert config.username == "retro"
        assert config.password is None
        assert config.key_path is None
        assert config.port == 22
        assert config.paths is None

    def test_config_creation_full(self) -> None:
        """Test creating config with all fields."""
        paths = RetroPiePaths(
            home_dir="/home/retro",
            username="retro",
            retropie_dir="/home/retro/RetroPie",
        )

        config = RetroPieConfig(
            host="192.168.1.100",
            username="pi",
            password="raspberry",  # noqa: S106
            key_path="/home/user/.ssh/id_rsa",
            port=2222,
            paths=paths,
        )

        assert config.host == "192.168.1.100"
        assert config.username == "pi"
        assert config.password == "raspberry"
        assert config.key_path == "/home/user/.ssh/id_rsa"
        assert config.port == 2222
        assert config.paths == paths

    def test_config_frozen(self) -> None:
        """Test that config is frozen (immutable)."""
        config = RetroPieConfig(host="retropie.local", username="retro")

        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            config.host = "different.host"  # type: ignore

    def test_config_from_env_all_vars_set(self) -> None:
        """Test creating config from environment variables when all are set."""
        env_vars = {
            "RETROPIE_HOST": "env-retropie.local",
            "RETROPIE_USERNAME": "env-user",
            "RETROPIE_PASSWORD": "env-pass",
            "RETROPIE_KEY_PATH": "/env/key/path",
            "RETROPIE_PORT": "2222",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            config = RetroPieConfig.from_env()

        assert config.host == "env-retropie.local"
        assert config.username == "env-user"
        assert config.password == "env-pass"
        assert config.key_path == "/env/key/path"
        assert config.port == 2222

    def test_config_from_env_minimal_vars(self) -> None:
        """Test creating config from environment with only required vars."""
        env_vars = {
            "RETROPIE_HOST": "minimal.local",
            "RETROPIE_USERNAME": "minimal-user",
        }

        # Remove any existing env vars that might interfere
        to_remove = ["RETROPIE_PASSWORD", "RETROPIE_KEY_PATH", "RETROPIE_PORT"]
        for var in to_remove:
            if var in os.environ:
                del os.environ[var]

        with patch.dict(os.environ, env_vars, clear=False):
            config = RetroPieConfig.from_env()

        assert config.host == "minimal.local"
        assert config.username == "minimal-user"
        assert config.password is None
        assert config.key_path is None
        assert config.port == 22  # Default value

    def test_config_from_env_missing_required(self) -> None:
        """Test creating config from environment with missing required vars."""
        # Remove all relevant env vars
        to_remove = [
            "RETROPIE_HOST",
            "RETROPIE_USERNAME",
            "RETROPIE_PASSWORD",
            "RETROPIE_KEY_PATH",
            "RETROPIE_PORT",
        ]
        for var in to_remove:
            if var in os.environ:
                del os.environ[var]

        with pytest.raises(ValueError, match="RETROPIE_HOST and RETROPIE_USERNAME"):
            RetroPieConfig.from_env()

    def test_config_from_env_host_missing(self) -> None:
        """Test config creation when only host is missing."""
        # Remove host but keep username
        to_remove = [
            "RETROPIE_HOST",
            "RETROPIE_PASSWORD",
            "RETROPIE_KEY_PATH",
            "RETROPIE_PORT",
        ]
        for var in to_remove:
            if var in os.environ:
                del os.environ[var]

        env_vars = {"RETROPIE_USERNAME": "user"}
        with patch.dict(os.environ, env_vars, clear=False):
            with pytest.raises(ValueError, match="RETROPIE_HOST and RETROPIE_USERNAME"):
                RetroPieConfig.from_env()

    def test_config_from_env_username_missing(self) -> None:
        """Test config creation when only username is missing."""
        # Remove username but keep host
        to_remove = [
            "RETROPIE_USERNAME",
            "RETROPIE_PASSWORD",
            "RETROPIE_KEY_PATH",
            "RETROPIE_PORT",
        ]
        for var in to_remove:
            if var in os.environ:
                del os.environ[var]

        env_vars = {"RETROPIE_HOST": "host.local"}
        with patch.dict(os.environ, env_vars, clear=False):
            with pytest.raises(ValueError, match="RETROPIE_HOST and RETROPIE_USERNAME"):
                RetroPieConfig.from_env()

    def test_config_from_env_port_conversion(self) -> None:
        """Test port conversion from string to int."""
        env_vars = {
            "RETROPIE_HOST": "test.local",
            "RETROPIE_USERNAME": "test",
            "RETROPIE_PORT": "9999",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            config = RetroPieConfig.from_env()

        assert config.port == 9999

    def test_config_from_env_invalid_port(self) -> None:
        """Test config creation with invalid port string."""
        env_vars = {
            "RETROPIE_HOST": "test.local",
            "RETROPIE_USERNAME": "test",
            "RETROPIE_PORT": "not-a-number",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            with pytest.raises(ValueError):
                RetroPieConfig.from_env()

    def test_config_update_paths(self) -> None:
        """Test updating config with paths using replace."""
        original_config = RetroPieConfig(host="retropie.local", username="retro")

        paths = RetroPiePaths(
            home_dir="/home/retro",
            username="retro",
            retropie_dir="/home/retro/RetroPie",
        )

        updated_config = original_config.with_paths(paths)

        # Original config unchanged
        assert original_config.paths is None

        # New config has paths
        assert updated_config.paths == paths
        assert updated_config.host == "retropie.local"
        assert updated_config.username == "retro"

    def test_config_equality(self) -> None:
        """Test config equality comparison."""
        config1 = RetroPieConfig(
            host="retropie.local",
            username="retro",
            password="secret",  # noqa: S106
        )

        config2 = RetroPieConfig(
            host="retropie.local",
            username="retro",
            password="secret",  # noqa: S106
        )

        config3 = RetroPieConfig(
            host="different.local",
            username="retro",
            password="secret",  # noqa: S106
        )

        assert config1 == config2
        assert config1 != config3

    def test_config_repr(self) -> None:
        """Test config string representation."""
        config = RetroPieConfig(host="retropie.local", username="retro", port=2222)

        repr_str = repr(config)

        assert "RetroPieConfig" in repr_str
        assert "retropie.local" in repr_str
        assert "retro" in repr_str
        assert "2222" in repr_str
