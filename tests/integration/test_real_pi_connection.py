"""Integration tests with real Raspberry Pi at 192.168.1.142."""

import os

import pytest

from retromcp.config import RetroPieConfig
from retromcp.container import Container
from retromcp.discovery import RetroPiePaths
from retromcp.tools.system_management_tools import SystemManagementTools


@pytest.mark.real_pi
class TestRealPiConnection:
    """Integration tests that connect to actual Raspberry Pi hardware."""

    @pytest.fixture
    def real_pi_config(self) -> RetroPieConfig:
        """Create configuration for real Pi at 192.168.1.142."""
        # Set up environment variables for the real Pi
        os.environ["RETROPIE_HOST"] = "192.168.1.142"
        os.environ["RETROPIE_USERNAME"] = "retro"

        # Use SSH key instead of password (Pi only accepts public key auth)
        ssh_key_path = os.path.expanduser("~/.ssh/id_ed25519")
        os.environ["RETROPIE_KEY_PATH"] = ssh_key_path

        # Remove password to force key authentication
        if "RETROPIE_PASSWORD" in os.environ:
            del os.environ["RETROPIE_PASSWORD"]

        # Create config from environment
        config = RetroPieConfig.from_env()

        # Add default paths structure for RetroPie
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

        return config.with_paths(paths)

    @pytest.mark.asyncio
    async def test_real_pi_connection_and_system_info(
        self, real_pi_config: RetroPieConfig
    ) -> None:
        """Test connecting to real Pi and getting system info."""
        # Create container with real Pi configuration
        container = Container(real_pi_config)

        # Create system management tools
        system_tools = SystemManagementTools(container)

        # Test basic connection by getting system info
        result = await system_tools.handle_tool_call("get_system_info", {})

        # Verify successful response
        assert isinstance(result, list), "Should return MCP-compliant list"
        assert len(result) == 1, "Should return single response"

        response = result[0]
        assert hasattr(response, "text"), "Should have text attribute"

        # Should not contain error indicators
        response_text = response.text.lower()
        assert "❌" not in response.text, f"Should not have error: {response.text}"
        assert "error" not in response_text, f"Should not have error: {response.text}"
        assert "failed" not in response_text, f"Should not have failed: {response.text}"

        # Should contain expected system information
        assert any(keyword in response_text for keyword in [
            "hostname", "memory", "cpu", "disk", "uptime"
        ]), f"Should contain system info: {response.text}"

    @pytest.mark.asyncio
    async def test_real_pi_ssh_connectivity(
        self, real_pi_config: RetroPieConfig
    ) -> None:
        """Test SSH connectivity to real Pi."""
        # Create container with real Pi configuration
        container = Container(real_pi_config)

        # Get the actual SSH client
        ssh_client = container.retropie_client

        # Test connection
        connection_info = ssh_client.get_connection_info()

        # Verify connection details
        assert connection_info.host == "192.168.1.142"
        assert connection_info.username == "retro"
        assert connection_info.port == 22

    @pytest.mark.asyncio
    async def test_real_pi_command_execution(
        self, real_pi_config: RetroPieConfig
    ) -> None:
        """Test command execution on real Pi."""
        # Create container with real Pi configuration
        container = Container(real_pi_config)

        # Get the actual SSH client
        ssh_client = container.retropie_client

        # Establish connection first
        connection_established = ssh_client.connect()
        assert connection_established, "Should be able to connect to Pi"

        try:
            # Test simple command execution
            result = ssh_client.execute_command("echo 'Hello from Pi'")

            # Verify command execution
            assert result.success, f"Command should succeed: {result.stderr}"
            assert result.exit_code == 0, f"Should have exit code 0: {result}"
            assert "Hello from Pi" in result.stdout, f"Should contain expected output: {result.stdout}"
        finally:
            # Always disconnect
            ssh_client.disconnect()
