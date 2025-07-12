"""Unit tests for RetroPieTools implementation."""

from unittest.mock import Mock

import pytest
from mcp.types import TextContent

from retromcp.config import RetroPieConfig
from retromcp.discovery import RetroPiePaths
from retromcp.tools.retropie_tools import RetroPieTools


class TestRetroPieTools:
    """Test cases for RetroPieTools class."""

    @pytest.fixture
    def mock_ssh_handler(self) -> Mock:
        """Provide mocked SSH handler."""
        mock = Mock()
        mock.execute_command = Mock()
        mock.run_retropie_setup = Mock()
        mock.setup_emulator = Mock()
        return mock

    @pytest.fixture
    def test_config(self) -> RetroPieConfig:
        """Provide test configuration."""
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
    def retropie_tools(
        self, mock_ssh_handler: Mock, test_config: RetroPieConfig
    ) -> RetroPieTools:
        """Provide RetroPieTools instance with mocked dependencies."""
        return RetroPieTools(mock_ssh_handler, test_config)

    def test_get_tools(self, retropie_tools: RetroPieTools) -> None:
        """Test that all expected tools are returned."""
        tools = retropie_tools.get_tools()

        assert len(tools) == 5
        tool_names = [tool.name for tool in tools]

        expected_tools = [
            "run_retropie_setup",
            "install_emulator",
            "manage_roms",
            "configure_overclock",
            "configure_audio",
        ]

        for expected_tool in expected_tools:
            assert expected_tool in tool_names

    def test_tool_schemas(self, retropie_tools: RetroPieTools) -> None:
        """Test that tool schemas are properly defined."""
        tools = retropie_tools.get_tools()
        tool_dict = {tool.name: tool for tool in tools}

        # RetroPie setup tool
        setup_tool = tool_dict["run_retropie_setup"]
        assert setup_tool.inputSchema["type"] == "object"
        assert "action" in setup_tool.inputSchema["properties"]
        assert "update" in setup_tool.inputSchema["properties"]["action"]["enum"]
        assert "install" in setup_tool.inputSchema["properties"]["action"]["enum"]
        assert "package" in setup_tool.inputSchema["properties"]
        assert setup_tool.inputSchema["required"] == ["action"]

        # Install emulator tool
        emulator_tool = tool_dict["install_emulator"]
        assert "emulator" in emulator_tool.inputSchema["properties"]
        assert "install_type" in emulator_tool.inputSchema["properties"]
        assert (
            "binary" in emulator_tool.inputSchema["properties"]["install_type"]["enum"]
        )
        assert (
            "source" in emulator_tool.inputSchema["properties"]["install_type"]["enum"]
        )
        assert emulator_tool.inputSchema["required"] == ["emulator"]

        # ROM management tool
        roms_tool = tool_dict["manage_roms"]
        assert "action" in roms_tool.inputSchema["properties"]
        assert "list" in roms_tool.inputSchema["properties"]["action"]["enum"]
        assert "scan" in roms_tool.inputSchema["properties"]["action"]["enum"]
        assert "permissions" in roms_tool.inputSchema["properties"]["action"]["enum"]
        assert "system" in roms_tool.inputSchema["properties"]

        # Overclock tool
        overclock_tool = tool_dict["configure_overclock"]
        assert "preset" in overclock_tool.inputSchema["properties"]
        assert "none" in overclock_tool.inputSchema["properties"]["preset"]["enum"]
        assert "custom" in overclock_tool.inputSchema["properties"]["preset"]["enum"]
        assert "arm_freq" in overclock_tool.inputSchema["properties"]
        assert "gpu_freq" in overclock_tool.inputSchema["properties"]

        # Audio tool
        audio_tool = tool_dict["configure_audio"]
        assert "output" in audio_tool.inputSchema["properties"]
        assert "auto" in audio_tool.inputSchema["properties"]["output"]["enum"]
        assert "hdmi" in audio_tool.inputSchema["properties"]["output"]["enum"]
        assert "volume" in audio_tool.inputSchema["properties"]
        assert audio_tool.inputSchema["properties"]["volume"]["minimum"] == 0
        assert audio_tool.inputSchema["properties"]["volume"]["maximum"] == 100

    @pytest.mark.asyncio
    async def test_run_retropie_setup_update(
        self, retropie_tools: RetroPieTools
    ) -> None:
        """Test RetroPie setup update action."""
        retropie_tools.ssh.run_retropie_setup.return_value = (
            True,
            "✅ RetroPie-Setup updated successfully",
        )

        result = await retropie_tools.handle_tool_call(
            "run_retropie_setup", {"action": "update"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "✅ RetroPie-Setup updated successfully" in result[0].text
        retropie_tools.ssh.run_retropie_setup.assert_called_once_with()

    @pytest.mark.asyncio
    async def test_run_retropie_setup_install_package(
        self, retropie_tools: RetroPieTools
    ) -> None:
        """Test RetroPie setup package installation."""
        retropie_tools.ssh.run_retropie_setup.return_value = (
            True,
            "Package installed successfully",
        )

        result = await retropie_tools.handle_tool_call(
            "run_retropie_setup", {"action": "install", "package": "lr-mupen64plus"}
        )

        assert len(result) == 1
        assert "Installed lr-mupen64plus successfully" in result[0].text
        retropie_tools.ssh.run_retropie_setup.assert_called_once_with(
            "install lr-mupen64plus"
        )

    @pytest.mark.asyncio
    async def test_run_retropie_setup_remove_package(
        self, retropie_tools: RetroPieTools
    ) -> None:
        """Test RetroPie setup package removal."""
        retropie_tools.ssh.run_retropie_setup.return_value = (
            True,
            "Package removed successfully",
        )

        result = await retropie_tools.handle_tool_call(
            "run_retropie_setup", {"action": "remove", "package": "lr-genesis-plus-gx"}
        )

        assert len(result) == 1
        assert "Removeed lr-genesis-plus-gx successfully" in result[0].text
        retropie_tools.ssh.run_retropie_setup.assert_called_once_with(
            "remove lr-genesis-plus-gx"
        )

    @pytest.mark.asyncio
    async def test_run_retropie_setup_configure_package(
        self, retropie_tools: RetroPieTools
    ) -> None:
        """Test RetroPie setup package configuration."""
        retropie_tools.ssh.run_retropie_setup.return_value = (
            True,
            "Package configured successfully",
        )

        result = await retropie_tools.handle_tool_call(
            "run_retropie_setup", {"action": "configure", "package": "emulationstation"}
        )

        assert len(result) == 1
        assert "Configureed emulationstation successfully" in result[0].text
        retropie_tools.ssh.run_retropie_setup.assert_called_once_with(
            "configure emulationstation"
        )

    @pytest.mark.asyncio
    async def test_run_retropie_setup_missing_package(
        self, retropie_tools: RetroPieTools
    ) -> None:
        """Test RetroPie setup with missing package for install action."""
        result = await retropie_tools.handle_tool_call(
            "run_retropie_setup", {"action": "install"}
        )

        assert len(result) == 1
        assert "Package name required for install action" in result[0].text

    @pytest.mark.asyncio
    async def test_run_retropie_setup_failure(
        self, retropie_tools: RetroPieTools
    ) -> None:
        """Test RetroPie setup action failure."""
        retropie_tools.ssh.run_retropie_setup.return_value = (
            False,
            "❌ Failed to update: Network error",
        )

        result = await retropie_tools.handle_tool_call(
            "run_retropie_setup", {"action": "update"}
        )

        assert len(result) == 1
        assert "❌ Failed to update: Network error" in result[0].text

    @pytest.mark.asyncio
    async def test_run_retropie_setup_unknown_action(
        self, retropie_tools: RetroPieTools
    ) -> None:
        """Test RetroPie setup with unknown action."""
        result = await retropie_tools.handle_tool_call(
            "run_retropie_setup", {"action": "invalid_action"}
        )

        assert len(result) == 1
        assert "Unknown action: invalid_action" in result[0].text

    @pytest.mark.asyncio
    async def test_install_emulator_direct_name(
        self, retropie_tools: RetroPieTools
    ) -> None:
        """Test emulator installation with direct name."""
        retropie_tools.ssh.setup_emulator.return_value = (
            True,
            "✅ Emulator installed successfully",
        )

        result = await retropie_tools.handle_tool_call(
            "install_emulator", {"emulator": "mupen64plus"}
        )

        assert len(result) == 1
        assert "Successfully installed mupen64plus emulator" in result[0].text
        retropie_tools.ssh.setup_emulator.assert_called_once_with(
            "retropie", "mupen64plus"
        )

    @pytest.mark.asyncio
    async def test_install_emulator_mapped_name(
        self, retropie_tools: RetroPieTools
    ) -> None:
        """Test emulator installation with mapped name."""
        retropie_tools.ssh.setup_emulator.return_value = (
            True,
            "✅ Emulator installed successfully",
        )

        result = await retropie_tools.handle_tool_call(
            "install_emulator", {"emulator": "n64", "install_type": "binary"}
        )

        assert len(result) == 1
        assert "Successfully installed n64 emulator" in result[0].text
        # Should map "n64" to "mupen64plus"
        retropie_tools.ssh.setup_emulator.assert_called_once_with(
            "retropie", "mupen64plus"
        )

    @pytest.mark.asyncio
    async def test_install_emulator_case_insensitive_mapping(
        self, retropie_tools: RetroPieTools
    ) -> None:
        """Test emulator installation with case insensitive mapping."""
        retropie_tools.ssh.setup_emulator.return_value = (
            True,
            "✅ Emulator installed successfully",
        )

        test_cases = [
            ("PSX", "pcsx-rearmed"),
            ("PlayStation", "pcsx-rearmed"),
            ("GameCube", "dolphin"),
            ("PSP", "ppsspp"),
        ]

        for input_name, expected_package in test_cases:
            result = await retropie_tools.handle_tool_call(
                "install_emulator", {"emulator": input_name}
            )

            assert len(result) == 1
            assert f"Successfully installed {input_name} emulator" in result[0].text
            retropie_tools.ssh.setup_emulator.assert_called_with(
                "retropie", expected_package
            )

    @pytest.mark.asyncio
    async def test_install_emulator_missing_name(
        self, retropie_tools: RetroPieTools
    ) -> None:
        """Test emulator installation with missing emulator name."""
        result = await retropie_tools.handle_tool_call("install_emulator", {})

        assert len(result) == 1
        assert "No emulator specified" in result[0].text

    @pytest.mark.asyncio
    async def test_install_emulator_failure(
        self, retropie_tools: RetroPieTools
    ) -> None:
        """Test emulator installation failure."""
        retropie_tools.ssh.setup_emulator.return_value = (
            False,
            "❌ Installation failed: Dependency missing",
        )

        result = await retropie_tools.handle_tool_call(
            "install_emulator", {"emulator": "dolphin"}
        )

        assert len(result) == 1
        assert (
            "Failed to install dolphin: ❌ Installation failed: Dependency missing"
            in result[0].text
        )

    @pytest.mark.asyncio
    async def test_manage_roms_list_all(self, retropie_tools: RetroPieTools) -> None:
        """Test ROM listing for all systems."""
        retropie_tools.ssh.execute_command.return_value = (
            0,
            "/home/retro/RetroPie/roms/nes/game1.zip\n/home/retro/RetroPie/roms/snes/game2.rom\n/home/retro/RetroPie/roms/psx/game3.bin",
            "",
        )

        result = await retropie_tools.handle_tool_call(
            "manage_roms", {"action": "list"}
        )

        assert len(result) == 1
        assert "📁 ROM Files:" in result[0].text
        assert "game1.zip" in result[0].text
        assert "game2.rom" in result[0].text
        assert "game3.bin" in result[0].text

    @pytest.mark.asyncio
    async def test_manage_roms_list_specific_system(
        self, retropie_tools: RetroPieTools
    ) -> None:
        """Test ROM listing for specific system."""
        retropie_tools.ssh.execute_command.return_value = (
            0,
            "/home/retro/RetroPie/roms/nes/mario.zip\n/home/retro/RetroPie/roms/nes/zelda.zip",
            "",
        )

        result = await retropie_tools.handle_tool_call(
            "manage_roms", {"action": "list", "system": "nes"}
        )

        assert len(result) == 1
        assert "📁 ROM Files:" in result[0].text
        assert "mario.zip" in result[0].text
        assert "zelda.zip" in result[0].text

    @pytest.mark.asyncio
    async def test_manage_roms_list_no_roms_found(
        self, retropie_tools: RetroPieTools
    ) -> None:
        """Test ROM listing when no ROMs are found."""
        retropie_tools.ssh.execute_command.return_value = (0, "", "")

        result = await retropie_tools.handle_tool_call(
            "manage_roms", {"action": "list"}
        )

        assert len(result) == 1
        assert "No ROM files found" in result[0].text

    @pytest.mark.asyncio
    async def test_manage_roms_list_command_failure(
        self, retropie_tools: RetroPieTools
    ) -> None:
        """Test ROM listing when command fails."""
        retropie_tools.ssh.execute_command.return_value = (1, "", "Permission denied")

        result = await retropie_tools.handle_tool_call(
            "manage_roms", {"action": "list"}
        )

        assert len(result) == 1
        assert "Failed to list ROM files" in result[0].text

    @pytest.mark.asyncio
    async def test_manage_roms_scan_service_active(
        self, retropie_tools: RetroPieTools
    ) -> None:
        """Test ROM scanning when EmulationStation service is active."""
        retropie_tools.ssh.execute_command.side_effect = [
            (0, "active", ""),  # Service check
            (0, "", ""),  # Restart command
        ]

        result = await retropie_tools.handle_tool_call(
            "manage_roms", {"action": "scan"}
        )

        assert len(result) == 1
        assert "EmulationStation restarted to scan for new ROMs" in result[0].text

    @pytest.mark.asyncio
    async def test_manage_roms_scan_user_process(
        self, retropie_tools: RetroPieTools
    ) -> None:
        """Test ROM scanning when EmulationStation runs as user process."""
        retropie_tools.ssh.execute_command.side_effect = [
            (1, "", ""),  # Service not active
            (0, "", ""),  # pkill
            (0, "", ""),  # sleep
            (0, "", ""),  # restart as user
        ]

        result = await retropie_tools.handle_tool_call(
            "manage_roms", {"action": "scan"}
        )

        assert len(result) == 1
        assert "EmulationStation restarted to scan for new ROMs" in result[0].text

    @pytest.mark.asyncio
    async def test_manage_roms_scan_failure(
        self, retropie_tools: RetroPieTools
    ) -> None:
        """Test ROM scanning failure."""
        retropie_tools.ssh.execute_command.side_effect = [
            (0, "active", ""),  # Service check
            (1, "", "Failed to restart"),  # Restart fails
        ]

        result = await retropie_tools.handle_tool_call(
            "manage_roms", {"action": "scan"}
        )

        assert len(result) == 1
        assert "Failed to restart EmulationStation" in result[0].text

    @pytest.mark.asyncio
    async def test_manage_roms_fix_permissions_success(
        self, retropie_tools: RetroPieTools
    ) -> None:
        """Test ROM permissions fix success."""
        retropie_tools.ssh.execute_command.return_value = (0, "", "")

        result = await retropie_tools.handle_tool_call(
            "manage_roms", {"action": "permissions"}
        )

        assert len(result) == 1
        assert "ROM file permissions fixed" in result[0].text

    @pytest.mark.asyncio
    async def test_manage_roms_fix_permissions_failure(
        self, retropie_tools: RetroPieTools
    ) -> None:
        """Test ROM permissions fix failure."""
        retropie_tools.ssh.execute_command.return_value = (1, "", "Permission denied")

        result = await retropie_tools.handle_tool_call(
            "manage_roms", {"action": "permissions"}
        )

        assert len(result) == 1
        assert "Failed to fix permissions: Permission denied" in result[0].text

    @pytest.mark.asyncio
    async def test_manage_roms_unknown_action(
        self, retropie_tools: RetroPieTools
    ) -> None:
        """Test ROM management with unknown action."""
        result = await retropie_tools.handle_tool_call(
            "manage_roms", {"action": "invalid"}
        )

        assert len(result) == 1
        assert "Unknown ROM action: invalid" in result[0].text

    @pytest.mark.asyncio
    async def test_configure_overclock_preset_none(
        self, retropie_tools: RetroPieTools
    ) -> None:
        """Test overclocking configuration with 'none' preset."""
        retropie_tools.ssh.execute_command.side_effect = [
            (0, "", ""),  # arm_freq command
            (0, "", ""),  # gpu_freq command
        ]

        result = await retropie_tools.handle_tool_call(
            "configure_overclock", {"preset": "none"}
        )

        assert len(result) == 1
        assert "Overclocking configured to none preset" in result[0].text
        assert "Reboot required" in result[0].text

    @pytest.mark.asyncio
    async def test_configure_overclock_preset_turbo(
        self, retropie_tools: RetroPieTools
    ) -> None:
        """Test overclocking configuration with 'turbo' preset."""
        retropie_tools.ssh.execute_command.side_effect = [
            (0, "", ""),  # arm_freq command
            (0, "", ""),  # gpu_freq command
        ]

        result = await retropie_tools.handle_tool_call(
            "configure_overclock", {"preset": "turbo"}
        )

        assert len(result) == 1
        assert "Overclocking configured to turbo preset" in result[0].text

    @pytest.mark.asyncio
    async def test_configure_overclock_custom_preset(
        self, retropie_tools: RetroPieTools
    ) -> None:
        """Test overclocking configuration with custom preset."""
        retropie_tools.ssh.execute_command.side_effect = [
            (0, "", ""),  # arm_freq command
            (0, "", ""),  # gpu_freq command
        ]

        result = await retropie_tools.handle_tool_call(
            "configure_overclock",
            {"preset": "custom", "arm_freq": 1200, "gpu_freq": 400},
        )

        assert len(result) == 1
        assert "Overclocking configured to custom preset" in result[0].text

    @pytest.mark.asyncio
    async def test_configure_overclock_custom_missing_params(
        self, retropie_tools: RetroPieTools
    ) -> None:
        """Test overclocking configuration with custom preset missing parameters."""
        result = await retropie_tools.handle_tool_call(
            "configure_overclock", {"preset": "custom", "arm_freq": 1200}
        )

        assert len(result) == 1
        assert "Custom preset requires arm_freq and gpu_freq" in result[0].text

    @pytest.mark.asyncio
    async def test_configure_overclock_unknown_preset(
        self, retropie_tools: RetroPieTools
    ) -> None:
        """Test overclocking configuration with unknown preset."""
        result = await retropie_tools.handle_tool_call(
            "configure_overclock", {"preset": "invalid"}
        )

        assert len(result) == 1
        assert "Unknown preset: invalid" in result[0].text

    @pytest.mark.asyncio
    async def test_configure_overclock_command_failure(
        self, retropie_tools: RetroPieTools
    ) -> None:
        """Test overclocking configuration command failure."""
        retropie_tools.ssh.execute_command.return_value = (1, "", "Permission denied")

        result = await retropie_tools.handle_tool_call(
            "configure_overclock", {"preset": "modest"}
        )

        assert len(result) == 1
        assert "Failed to update config: Permission denied" in result[0].text

    @pytest.mark.asyncio
    async def test_configure_audio_output_hdmi(
        self, retropie_tools: RetroPieTools
    ) -> None:
        """Test audio configuration with HDMI output."""
        retropie_tools.ssh.execute_command.return_value = (0, "amixer set", "")

        result = await retropie_tools.handle_tool_call(
            "configure_audio", {"output": "hdmi"}
        )

        assert len(result) == 1
        assert "Audio configured successfully" in result[0].text

    @pytest.mark.asyncio
    async def test_configure_audio_volume_only(
        self, retropie_tools: RetroPieTools
    ) -> None:
        """Test audio configuration with volume only."""
        retropie_tools.ssh.execute_command.return_value = (0, "volume set", "")

        result = await retropie_tools.handle_tool_call(
            "configure_audio", {"volume": 75}
        )

        assert len(result) == 1
        assert "Audio configured successfully" in result[0].text

    @pytest.mark.asyncio
    async def test_configure_audio_output_and_volume(
        self, retropie_tools: RetroPieTools
    ) -> None:
        """Test audio configuration with both output and volume."""
        retropie_tools.ssh.execute_command.side_effect = [
            (0, "output set", ""),  # Output command
            (0, "volume set", ""),  # Volume command
        ]

        result = await retropie_tools.handle_tool_call(
            "configure_audio", {"output": "headphone", "volume": 50}
        )

        assert len(result) == 1
        assert "Audio configured successfully" in result[0].text

    @pytest.mark.asyncio
    async def test_configure_audio_unknown_output(
        self, retropie_tools: RetroPieTools
    ) -> None:
        """Test audio configuration with unknown output."""
        result = await retropie_tools.handle_tool_call(
            "configure_audio", {"output": "invalid"}
        )

        assert len(result) == 1
        assert "Unknown audio output: invalid" in result[0].text

    @pytest.mark.asyncio
    async def test_configure_audio_command_failure(
        self, retropie_tools: RetroPieTools
    ) -> None:
        """Test audio configuration command failure."""
        retropie_tools.ssh.execute_command.return_value = (1, "", "Device not found")

        result = await retropie_tools.handle_tool_call(
            "configure_audio", {"output": "hdmi"}
        )

        assert len(result) == 1
        assert "Audio configuration failed: Device not found" in result[0].text

    @pytest.mark.asyncio
    async def test_configure_audio_no_parameters(
        self, retropie_tools: RetroPieTools
    ) -> None:
        """Test audio configuration with no parameters."""
        result = await retropie_tools.handle_tool_call("configure_audio", {})

        assert len(result) == 1
        assert "Audio configured successfully" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_unknown_tool(self, retropie_tools: RetroPieTools) -> None:
        """Test handling of unknown tool name."""
        result = await retropie_tools.handle_tool_call("unknown_tool", {})

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Unknown tool: unknown_tool" in result[0].text

    @pytest.mark.asyncio
    async def test_handle_tool_exception(self, retropie_tools: RetroPieTools) -> None:
        """Test exception handling in tool execution."""
        retropie_tools.ssh.run_retropie_setup.side_effect = Exception(
            "SSH connection lost"
        )

        result = await retropie_tools.handle_tool_call(
            "run_retropie_setup", {"action": "update"}
        )

        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Error in run_retropie_setup: SSH connection lost" in result[0].text

    def test_inheritance_from_base_tool(self, retropie_tools: RetroPieTools) -> None:
        """Test that RetroPieTools properly inherits from BaseTool."""
        # Should have access to BaseTool methods
        assert hasattr(retropie_tools, "format_success")
        assert hasattr(retropie_tools, "format_error")
        assert hasattr(retropie_tools, "ssh")
        assert hasattr(retropie_tools, "config")

        # Test format methods work
        success_result = retropie_tools.format_success("Test message")
        assert len(success_result) == 1
        assert isinstance(success_result[0], TextContent)
        assert "Test message" in success_result[0].text

        error_result = retropie_tools.format_error("Error message")
        assert len(error_result) == 1
        assert isinstance(error_result[0], TextContent)
        assert "Error message" in error_result[0].text

    @pytest.mark.asyncio
    async def test_overclock_all_presets(self, retropie_tools: RetroPieTools) -> None:
        """Test all overclocking presets work correctly."""
        presets = ["none", "modest", "medium", "high", "turbo"]

        for preset in presets:
            retropie_tools.ssh.execute_command.side_effect = [
                (0, "", ""),  # arm_freq command
                (0, "", ""),  # gpu_freq command
            ]

            result = await retropie_tools.handle_tool_call(
                "configure_overclock", {"preset": preset}
            )

            assert len(result) == 1
            assert f"Overclocking configured to {preset} preset" in result[0].text

    @pytest.mark.asyncio
    async def test_audio_all_outputs(self, retropie_tools: RetroPieTools) -> None:
        """Test all audio output types work correctly."""
        outputs = ["auto", "headphone", "hdmi", "both"]

        for output in outputs:
            retropie_tools.ssh.execute_command.return_value = (0, "configured", "")

            result = await retropie_tools.handle_tool_call(
                "configure_audio", {"output": output}
            )

            assert len(result) == 1
            assert "Audio configured successfully" in result[0].text

    @pytest.mark.asyncio
    async def test_roms_use_config_paths(self, retropie_tools: RetroPieTools) -> None:
        """Test ROM management uses configuration paths correctly."""
        retropie_tools.ssh.execute_command.return_value = (0, "roms found", "")

        result = await retropie_tools.handle_tool_call(
            "manage_roms", {"action": "list"}
        )

        # Should use config roms_dir path in find command
        call_args = retropie_tools.ssh.execute_command.call_args[0][0]
        assert (
            "/home/retro/RetroPie/roms" in call_args
            or retropie_tools.config.paths.roms_dir in call_args
        )

    @pytest.mark.asyncio
    async def test_roms_permissions_uses_config(
        self, retropie_tools: RetroPieTools
    ) -> None:
        """Test ROM permissions uses config paths and username."""
        retropie_tools.ssh.execute_command.return_value = (0, "", "")

        result = await retropie_tools.handle_tool_call(
            "manage_roms", {"action": "permissions"}
        )

        # Should use config username and roms path
        call_args = retropie_tools.ssh.execute_command.call_args[0][0]
        assert "retro:retro" in call_args  # Username from config
        assert "/home/retro/RetroPie/roms" in call_args  # Path from config

    @pytest.mark.asyncio
    async def test_emulator_mapping_coverage(
        self, retropie_tools: RetroPieTools
    ) -> None:
        """Test emulator name mapping covers all documented aliases."""
        retropie_tools.ssh.setup_emulator.return_value = (True, "installed")

        mappings = {
            "mupen64plus": "mupen64plus",
            "n64": "mupen64plus",
            "psx": "pcsx-rearmed",
            "playstation": "pcsx-rearmed",
            "dreamcast": "reicast",
            "psp": "ppsspp",
            "gamecube": "dolphin",
            "wii": "dolphin",
        }

        for input_name, expected_package in mappings.items():
            result = await retropie_tools.handle_tool_call(
                "install_emulator", {"emulator": input_name}
            )

            assert len(result) == 1
            retropie_tools.ssh.setup_emulator.assert_called_with(
                "retropie", expected_package
            )

    @pytest.mark.asyncio
    async def test_config_file_paths_used_correctly(
        self, retropie_tools: RetroPieTools
    ) -> None:
        """Test that config file paths are used correctly in operations."""
        retropie_tools.ssh.execute_command.return_value = (0, "", "")

        # Test overclocking uses /boot/config.txt
        result = await retropie_tools.handle_tool_call(
            "configure_overclock", {"preset": "modest"}
        )

        call_args = retropie_tools.ssh.execute_command.call_args_list[0][0][0]
        assert "/boot/config.txt" in call_args

    @pytest.mark.asyncio
    async def test_volume_boundary_values(self, retropie_tools: RetroPieTools) -> None:
        """Test audio volume configuration with boundary values."""
        retropie_tools.ssh.execute_command.return_value = (0, "volume set", "")

        # Test minimum volume
        result = await retropie_tools.handle_tool_call("configure_audio", {"volume": 0})
        assert "Audio configured successfully" in result[0].text

        # Test maximum volume
        result = await retropie_tools.handle_tool_call(
            "configure_audio", {"volume": 100}
        )
        assert "Audio configured successfully" in result[0].text
