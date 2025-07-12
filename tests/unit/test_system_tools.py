"""Unit tests for SystemTools implementation."""

from unittest.mock import Mock

import pytest
from mcp.types import TextContent

from retromcp.config import RetroPieConfig
from retromcp.tools.system_tools import SystemTools


class TestSystemTools:
    """Test cases for SystemTools class."""

    @pytest.fixture
    def mock_ssh_handler(self) -> Mock:
        """Provide mocked SSH handler."""
        mock = Mock()
        mock.execute_command = Mock()
        mock.get_system_info = Mock()
        mock.install_packages = Mock()
        mock.check_bios_files = Mock()
        mock.run_retropie_setup = Mock()
        return mock

    @pytest.fixture
    def test_config(self) -> RetroPieConfig:
        """Provide test configuration."""
        from retromcp.discovery import RetroPiePaths

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
            password="test_password",  # noqa: S106 # Test fixture, not real password
            port=22,
            paths=paths,
        )

    @pytest.fixture
    def system_tools(
        self, mock_ssh_handler: Mock, test_config: RetroPieConfig
    ) -> SystemTools:
        """Provide SystemTools instance with mocked dependencies."""
        return SystemTools(mock_ssh_handler, test_config)

    def test_get_tools(self, system_tools: SystemTools) -> None:
        """Test that all expected tools are returned."""
        tools = system_tools.get_tools()

        assert len(tools) == 5
        tool_names = [tool.name for tool in tools]

        expected_tools = [
            "test_connection",
            "system_info",
            "install_packages",
            "check_bios",
            "update_system",
        ]

        for expected_tool in expected_tools:
            assert expected_tool in tool_names

    def test_tool_schemas(self, system_tools: SystemTools) -> None:
        """Test that tool schemas are properly defined."""
        tools = system_tools.get_tools()
        tool_dict = {tool.name: tool for tool in tools}

        # Test connection tool - no parameters
        test_conn_tool = tool_dict["test_connection"]
        assert test_conn_tool.inputSchema["type"] == "object"
        assert test_conn_tool.inputSchema["required"] == []

        # Install packages tool - requires packages array
        install_tool = tool_dict["install_packages"]
        assert "packages" in install_tool.inputSchema["properties"]
        assert install_tool.inputSchema["required"] == ["packages"]
        assert install_tool.inputSchema["properties"]["packages"]["type"] == "array"

        # Check BIOS tool - requires system enum
        bios_tool = tool_dict["check_bios"]
        assert "system" in bios_tool.inputSchema["properties"]
        assert bios_tool.inputSchema["required"] == ["system"]
        assert "enum" in bios_tool.inputSchema["properties"]["system"]

        # Update system tool - optional update_type
        update_tool = tool_dict["update_system"]
        assert "update_type" in update_tool.inputSchema["properties"]
        assert update_tool.inputSchema["required"] == []

    @pytest.mark.asyncio
    async def test_test_connection_success(self, system_tools: SystemTools) -> None:
        """Test successful connection test."""
        system_tools.ssh.execute_command.return_value = (
            0,
            "Linux retropie 5.10.63-v7l+ #1459 SMP Wed Oct 6 16:41:57 BST 2021 armv7l GNU/Linux",
            "",
        )

        result = await system_tools.handle_tool_call("test_connection", {})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Successfully connected to RetroPie!" in result[0].text
        assert "Linux retropie" in result[0].text
        system_tools.ssh.execute_command.assert_called_once_with("uname -a")

    @pytest.mark.asyncio
    async def test_test_connection_command_failure(
        self, system_tools: SystemTools
    ) -> None:
        """Test connection test when command fails."""
        system_tools.ssh.execute_command.return_value = (1, "", "Permission denied")

        result = await system_tools.handle_tool_call("test_connection", {})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Connected but couldn't get system info" in result[0].text

    @pytest.mark.asyncio
    async def test_test_connection_ssh_exception(
        self, system_tools: SystemTools
    ) -> None:
        """Test connection test when SSH raises exception."""
        system_tools.ssh.execute_command.side_effect = Exception("Connection timeout")

        result = await system_tools.handle_tool_call("test_connection", {})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Connection failed: Connection timeout" in result[0].text
        assert "RETROPIE_HOST" in result[0].text  # Should include config help

    @pytest.mark.asyncio
    async def test_get_system_info_complete(self, system_tools: SystemTools) -> None:
        """Test system info with all data available."""
        system_tools.ssh.get_system_info.return_value = {
            "temperature": 65.5,
            "memory": {"used": 2048, "total": 4096},
            "disk": {"used": "8.5G", "total": "32G", "use_percent": "29%"},
            "emulationstation_running": True,
        }

        result = await system_tools.handle_tool_call("system_info", {})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        text = result[0].text

        assert "🖥️ RetroPie System Information:" in text
        assert "Temperature: ✅ 65.5°C" in text  # Normal temp
        assert "Memory: 🟢 2048MB / 4096MB (50.0%)" in text  # Normal memory
        assert "Disk Usage: 8.5G / 32G (29%)" in text
        assert "EmulationStation: ✅ Running" in text

    @pytest.mark.asyncio
    async def test_get_system_info_high_temperature(
        self, system_tools: SystemTools
    ) -> None:
        """Test system info with high temperature warnings."""
        # Test warning temperature
        system_tools.ssh.get_system_info.return_value = {"temperature": 75.0}
        result = await system_tools.handle_tool_call("system_info", {})
        assert "Temperature: ⚠️ 75.0°C" in result[0].text

        # Test critical temperature
        system_tools.ssh.get_system_info.return_value = {"temperature": 85.0}
        result = await system_tools.handle_tool_call("system_info", {})
        assert "Temperature: 🔥 85.0°C" in result[0].text

    @pytest.mark.asyncio
    async def test_get_system_info_high_memory(self, system_tools: SystemTools) -> None:
        """Test system info with high memory usage warnings."""
        # Test warning memory usage
        system_tools.ssh.get_system_info.return_value = {
            "memory": {"used": 3200, "total": 4096}  # 78%
        }
        result = await system_tools.handle_tool_call("system_info", {})
        assert "Memory: 🟡 3200MB / 4096MB (78.1%)" in result[0].text

        # Test critical memory usage
        system_tools.ssh.get_system_info.return_value = {
            "memory": {"used": 3788, "total": 4096}  # 92.5%
        }
        result = await system_tools.handle_tool_call("system_info", {})
        assert "Memory: 🔴 3788MB / 4096MB (92.5%)" in result[0].text

    @pytest.mark.asyncio
    async def test_get_system_info_es_not_running(
        self, system_tools: SystemTools
    ) -> None:
        """Test system info when EmulationStation is not running."""
        system_tools.ssh.get_system_info.return_value = {
            "emulationstation_running": False
        }

        result = await system_tools.handle_tool_call("system_info", {})

        assert len(result) == 1
        assert "EmulationStation: ❌ Not running" in result[0].text

    @pytest.mark.asyncio
    async def test_get_system_info_partial_data(
        self, system_tools: SystemTools
    ) -> None:
        """Test system info with only partial data available."""
        system_tools.ssh.get_system_info.return_value = {"temperature": 45.0}

        result = await system_tools.handle_tool_call("system_info", {})

        assert len(result) == 1
        text = result[0].text
        assert "Temperature: ✅ 45.0°C" in text
        # Should not contain memory, disk, or ES info
        assert "Memory:" not in text
        assert "Disk Usage:" not in text
        assert "EmulationStation:" not in text

    @pytest.mark.asyncio
    async def test_install_packages_success(self, system_tools: SystemTools) -> None:
        """Test successful package installation."""
        packages = ["htop", "vim", "git"]
        system_tools.ssh.install_packages.return_value = (
            True,
            "Successfully installed: htop vim git",
        )

        result = await system_tools.handle_tool_call(
            "install_packages", {"packages": packages}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Successfully installed: htop vim git" in result[0].text
        system_tools.ssh.install_packages.assert_called_once_with(packages)

    @pytest.mark.asyncio
    async def test_install_packages_failure(self, system_tools: SystemTools) -> None:
        """Test failed package installation."""
        packages = ["nonexistent-package"]
        system_tools.ssh.install_packages.return_value = (
            False,
            "Package 'nonexistent-package' not found",
        )

        result = await system_tools.handle_tool_call(
            "install_packages", {"packages": packages}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Package 'nonexistent-package' not found" in result[0].text

    @pytest.mark.asyncio
    async def test_install_packages_empty_list(self, system_tools: SystemTools) -> None:
        """Test package installation with empty package list."""
        result = await system_tools.handle_tool_call(
            "install_packages", {"packages": []}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "No packages specified" in result[0].text
        system_tools.ssh.install_packages.assert_not_called()

    @pytest.mark.asyncio
    async def test_install_packages_missing_argument(
        self, system_tools: SystemTools
    ) -> None:
        """Test package installation with missing packages argument."""
        result = await system_tools.handle_tool_call("install_packages", {})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "No packages specified" in result[0].text

    @pytest.mark.asyncio
    async def test_check_bios_no_files_required(
        self, system_tools: SystemTools
    ) -> None:
        """Test BIOS check for system that doesn't require BIOS."""
        system_tools.ssh.check_bios_files.return_value = {
            "bios_required": False,
            "files": {},
            "all_present": True,
        }

        result = await system_tools.handle_tool_call("check_bios", {"system": "nes"})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        text = result[0].text
        assert "BIOS Files for NES:" in text
        assert "✅ No BIOS files required for this system" in text

    @pytest.mark.asyncio
    async def test_check_bios_all_present(self, system_tools: SystemTools) -> None:
        """Test BIOS check when all required files are present."""
        system_tools.ssh.check_bios_files.return_value = {
            "bios_required": True,
            "files": {
                "scph1001.bin": True,
                "scph5501.bin": True,
                "scph7001.bin": True,
            },
            "all_present": True,
        }

        result = await system_tools.handle_tool_call("check_bios", {"system": "psx"})

        assert len(result) == 1
        text = result[0].text
        assert "BIOS Files for PSX:" in text
        assert "✅ scph1001.bin" in text
        assert "✅ scph5501.bin" in text
        assert "✅ scph7001.bin" in text
        assert "🎉 All required BIOS files are present!" in text

    @pytest.mark.asyncio
    async def test_check_bios_missing_files(self, system_tools: SystemTools) -> None:
        """Test BIOS check when some files are missing."""
        system_tools.ssh.check_bios_files.return_value = {
            "bios_required": True,
            "files": {
                "dc_boot.bin": True,
                "dc_flash.bin": False,
            },
            "all_present": False,
        }

        result = await system_tools.handle_tool_call(
            "check_bios", {"system": "dreamcast"}
        )

        assert len(result) == 1
        text = result[0].text
        assert "BIOS Files for DREAMCAST:" in text
        assert "✅ dc_boot.bin" in text
        assert "❌ dc_flash.bin" in text
        assert "⚠️ Some BIOS files are missing" in text
        assert "/home/retro/RetroPie/BIOS/" in text

    @pytest.mark.asyncio
    async def test_check_bios_missing_system_argument(
        self, system_tools: SystemTools
    ) -> None:
        """Test BIOS check with missing system argument."""
        result = await system_tools.handle_tool_call("check_bios", {})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "No system specified" in result[0].text

    @pytest.mark.asyncio
    async def test_update_system_basic_success(self, system_tools: SystemTools) -> None:
        """Test successful basic system update."""
        system_tools.ssh.execute_command.return_value = (0, "Update completed", "")

        result = await system_tools.handle_tool_call(
            "update_system", {"update_type": "basic"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "System packages updated successfully" in result[0].text
        system_tools.ssh.execute_command.assert_called_once_with(
            "sudo apt-get update && sudo apt-get upgrade -y"
        )

    @pytest.mark.asyncio
    async def test_update_system_basic_failure(self, system_tools: SystemTools) -> None:
        """Test failed basic system update."""
        system_tools.ssh.execute_command.return_value = (
            1,
            "",
            "E: Could not get lock /var/lib/dpkg/lock",
        )

        result = await system_tools.handle_tool_call(
            "update_system", {"update_type": "basic"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Update failed: E: Could not get lock" in result[0].text

    @pytest.mark.asyncio
    async def test_update_system_retropie_setup_success(
        self, system_tools: SystemTools
    ) -> None:
        """Test successful RetroPie-Setup update."""
        system_tools.ssh.run_retropie_setup.return_value = (
            True,
            "RetroPie-Setup updated successfully",
        )

        result = await system_tools.handle_tool_call(
            "update_system", {"update_type": "retropie-setup"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "RetroPie-Setup updated successfully" in result[0].text
        system_tools.ssh.run_retropie_setup.assert_called_once_with("update")

    @pytest.mark.asyncio
    async def test_update_system_retropie_setup_failure(
        self, system_tools: SystemTools
    ) -> None:
        """Test failed RetroPie-Setup update."""
        system_tools.ssh.run_retropie_setup.return_value = (
            False,
            "RetroPie-Setup update failed",
        )

        result = await system_tools.handle_tool_call(
            "update_system", {"update_type": "retropie-setup"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "RetroPie-Setup update failed" in result[0].text

    @pytest.mark.asyncio
    async def test_update_system_default_type(self, system_tools: SystemTools) -> None:
        """Test system update with default update type."""
        system_tools.ssh.execute_command.return_value = (0, "Update completed", "")

        result = await system_tools.handle_tool_call("update_system", {})

        assert len(result) == 1
        assert "System packages updated successfully" in result[0].text
        # Should default to basic update
        system_tools.ssh.execute_command.assert_called_once_with(
            "sudo apt-get update && sudo apt-get upgrade -y"
        )

    @pytest.mark.asyncio
    async def test_update_system_unknown_type(self, system_tools: SystemTools) -> None:
        """Test system update with unknown update type."""
        result = await system_tools.handle_tool_call(
            "update_system", {"update_type": "invalid"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Unknown update type: invalid" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_unknown_tool(self, system_tools: SystemTools) -> None:
        """Test handling of unknown tool name."""
        result = await system_tools.handle_tool_call("unknown_tool", {})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Unknown tool: unknown_tool" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_tool_exception(self, system_tools: SystemTools) -> None:
        """Test exception handling in tool execution."""
        system_tools.ssh.execute_command.side_effect = Exception("SSH connection lost")

        result = await system_tools.handle_tool_call("test_connection", {})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Connection failed: SSH connection lost" in result[0].text

    @pytest.mark.asyncio
    async def test_bios_check_uses_config_bios_dir(
        self, system_tools: SystemTools
    ) -> None:
        """Test that BIOS check uses configured BIOS directory."""
        system_tools.ssh.check_bios_files.return_value = {
            "bios_required": True,
            "files": {"test.bin": False},
            "all_present": False,
        }

        result = await system_tools.handle_tool_call("check_bios", {"system": "psx"})

        text = result[0].text
        assert "/home/retro/RetroPie/BIOS/" in text

    @pytest.mark.asyncio
    async def test_bios_check_fallback_bios_dir(self, mock_ssh_handler: Mock) -> None:
        """Test BIOS check fallback when bios_dir is None."""
        # Create config without paths (no discovery completed)
        config_no_paths = RetroPieConfig(
            host="test-retropie.local",
            username="retro",
            password="test_password",  # noqa: S106 # Test fixture, not real password
            port=22,
            paths=None,  # No paths discovered
        )

        tools = SystemTools(mock_ssh_handler, config_no_paths)
        tools.ssh.check_bios_files.return_value = {
            "bios_required": True,
            "files": {"test.bin": False},
            "all_present": False,
        }

        result = await tools.handle_tool_call("check_bios", {"system": "psx"})

        text = result[0].text
        # Should fall back to home_dir/RetroPie/BIOS
        assert "/home/retro/RetroPie/BIOS/" in text

    def test_inheritance_from_base_tool(self, system_tools: SystemTools) -> None:
        """Test that SystemTools properly inherits from BaseTool."""
        # Should have access to BaseTool methods
        assert hasattr(system_tools, "format_success")
        assert hasattr(system_tools, "format_error")
        assert hasattr(system_tools, "ssh")
        assert hasattr(system_tools, "config")

        # Test format methods work
        success_result = system_tools.format_success("Test message")
        assert len(success_result) == 1
        assert isinstance(success_result[0], TextContent)
        assert "Test message" in success_result[0].text

        error_result = system_tools.format_error("Error message")
        assert len(error_result) == 1
        assert isinstance(error_result[0], TextContent)
        assert "Error message" in error_result[0].text
