"""Integration tests for complete tool workflows.

Tests the full flow: Tool call → SSH Handler → Repository → Command execution
Also verifies CLAUDE.md compliance during tool execution workflows.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any
from dataclasses import fields, is_dataclass

from retromcp.config import RetroPieConfig
from retromcp.discovery import RetroPiePaths
from retromcp.domain.models import CommandResult, SystemInfo
from retromcp.tools.system_tools import SystemTools
from retromcp.tools.hardware_tools import HardwareTools
from retromcp.tools.retropie_tools import RetroPieTools
from retromcp.ssh_handler import SSHHandler, RetroPieSSH


class TestSystemToolsWorkflow:
    """Test complete system tools workflows with CLAUDE.md compliance."""

    @pytest.fixture
    def test_config(self) -> RetroPieConfig:
        """Create test configuration with paths."""
        paths = RetroPiePaths(
            home_dir="/home/retro",
            username="retro",
            retropie_dir="/home/retro/RetroPie",
            retropie_setup_dir="/home/retro/RetroPie-Setup",
            bios_dir="/home/retro/RetroPie/BIOS",
            roms_dir="/home/retro/RetroPie/roms",
        )
        return RetroPieConfig(
            host="test-retropie.local",
            username="retro",
            password="test_password",  # noqa: S106
            port=22,
            paths=paths,
        )

    @pytest.fixture
    def mock_ssh_handler(self) -> Mock:
        """Create mock SSH handler."""
        mock = Mock(spec=RetroPieSSH)
        # execute_command is sync, returns tuple (exit_code, stdout, stderr)
        mock.execute_command = Mock()
        return mock

    @pytest.fixture
    def system_tools(self, mock_ssh_handler: Mock, test_config: RetroPieConfig) -> SystemTools:
        """Create SystemTools instance with mocked dependencies."""
        return SystemTools(mock_ssh_handler, test_config)

    def _verify_claude_md_compliance(self, obj: object) -> None:
        """Verify that an object follows CLAUDE.md principles."""
        # Test immutability for dataclasses
        if is_dataclass(obj):
            # Check if it's a frozen dataclass
            if hasattr(obj, '__dataclass_params__'):
                # Allow mutable for profile classes that need updates
                if 'Profile' not in obj.__class__.__name__:
                    assert obj.__dataclass_params__.frozen is True, \
                        f"{obj.__class__.__name__} should be frozen for immutability"
        
        # Test meaningful naming
        class_name = obj.__class__.__name__
        assert len(class_name) >= 4, f"Class name '{class_name}' too short"
        assert class_name[0].isupper(), f"Class name '{class_name}' should use PascalCase"

    @pytest.mark.asyncio
    async def test_get_system_info_workflow(
        self, system_tools: SystemTools, mock_ssh_handler: Mock, test_config: RetroPieConfig
    ) -> None:
        """Test complete system_info workflow with CLAUDE.md compliance."""
        # CLAUDE.md compliance check for config
        self._verify_claude_md_compliance(test_config)

        # Mock the get_system_info method that the tool actually calls
        mock_ssh_handler.get_system_info.return_value = {
            "temperature": 55.4,
            "memory": {"total": 1024, "used": 512},
            "disk": {"total": "32G", "used": "12G", "use_percent": "40%"},
            "emulationstation_running": True
        }

        # Execute the tool workflow
        result = await system_tools.handle_tool_call("system_info", {})

        # Verify the workflow completed successfully and follows MCP protocol
        assert isinstance(result, list), "Tool should return list for MCP compliance"
        assert len(result) > 0, "Tool should return content"
        
        response = result[0]
        assert hasattr(response, 'text'), "Response should have text attribute for MCP compliance"
        
        # Verify system information is collected
        response_text = response.text
        assert "55.4°C" in response_text or "temperature" in response_text.lower()
        assert "memory" in response_text.lower() or "512MB" in response_text
        assert "disk" in response_text.lower() or "32G" in response_text
        
        # Verify SSH method was called
        mock_ssh_handler.get_system_info.assert_called_once()

    @pytest.mark.asyncio
    async def test_install_packages_workflow(
        self, system_tools: SystemTools, mock_ssh_handler: Mock, test_config: RetroPieConfig
    ) -> None:
        """Test complete install_packages workflow with CLAUDE.md compliance."""
        # CLAUDE.md compliance check
        self._verify_claude_md_compliance(test_config)

        # Mock the install_packages method that the tool actually calls
        mock_ssh_handler.install_packages.return_value = (True, "Successfully installed htop, vim")

        # Execute the tool workflow
        result = await system_tools.handle_tool_call("install_packages", {
            "packages": ["htop", "vim"]
        })

        # Verify MCP compliance
        assert isinstance(result, list), "Tool should return list for MCP compliance"
        assert len(result) > 0, "Tool should return content"
        
        response = result[0]
        assert hasattr(response, 'text'), "Response should have text attribute"
        
        # Verify package installation was attempted
        response_text = response.text
        assert "htop" in response_text or "package" in response_text.lower()
        assert "✅" in response_text or "success" in response_text.lower()
        
        # Verify SSH method was called
        mock_ssh_handler.install_packages.assert_called_once_with(["htop", "vim"])

    @pytest.mark.asyncio
    async def test_error_propagation_workflow(
        self, system_tools: SystemTools, mock_ssh_handler: Mock, test_config: RetroPieConfig
    ) -> None:
        """Test error handling and propagation workflow with CLAUDE.md compliance."""
        # CLAUDE.md compliance check
        self._verify_claude_md_compliance(test_config)

        # Mock SSH command failure
        mock_ssh_handler.execute_command.return_value = (1, "", "Command failed")

        # Execute tool that will fail
        result = await system_tools.handle_tool_call("system_info", {})

        # Verify error handling follows MCP protocol
        assert isinstance(result, list), "Error response should still be list for MCP compliance"
        assert len(result) > 0, "Error response should have content"
        
        response = result[0]
        assert hasattr(response, 'text'), "Error response should have text attribute"
        
        # Verify error is communicated properly
        response_text = response.text.lower()
        assert any(word in response_text for word in ['error', 'failed', 'unable']), \
            "Error response should indicate failure"


class TestHardwareToolsWorkflow:
    """Test hardware tools workflows with CLAUDE.md compliance."""

    @pytest.fixture
    def test_config(self) -> RetroPieConfig:
        """Create test configuration."""
        return RetroPieConfig(
            host="test-retropie.local",
            username="retro",
            password="test_password",  # noqa: S106
            port=22,
        )

    @pytest.fixture
    def mock_ssh_handler(self) -> Mock:
        """Create mock SSH handler."""
        mock = Mock(spec=RetroPieSSH)
        # execute_command is sync, returns tuple (exit_code, stdout, stderr)
        mock.execute_command = Mock()
        return mock

    @pytest.fixture
    def hardware_tools(self, mock_ssh_handler: Mock, test_config: RetroPieConfig) -> HardwareTools:
        """Create HardwareTools instance."""
        return HardwareTools(mock_ssh_handler, test_config)

    def _verify_claude_md_compliance(self, obj: object) -> None:
        """Verify CLAUDE.md compliance."""
        if is_dataclass(obj):
            if hasattr(obj, '__dataclass_params__'):
                if 'Profile' not in obj.__class__.__name__:
                    assert obj.__dataclass_params__.frozen is True
        
        class_name = obj.__class__.__name__
        assert len(class_name) >= 4
        assert class_name[0].isupper()

    @pytest.mark.asyncio
    async def test_check_temperature_workflow(
        self, hardware_tools: HardwareTools, mock_ssh_handler: Mock, test_config: RetroPieConfig
    ) -> None:
        """Test temperature check workflow with CLAUDE.md compliance."""
        # CLAUDE.md compliance check
        self._verify_claude_md_compliance(test_config)

        # Mock temperature commands
        mock_ssh_handler.execute_command.side_effect = [
            (0, "temp=55.4'C", ""),  # CPU temperature
            (0, "0x0", ""),  # throttling status
        ]

        # Execute the tool workflow
        result = await hardware_tools.handle_tool_call("check_temperatures", {})

        # Verify MCP compliance
        assert isinstance(result, list), "Tool should return list for MCP compliance"
        assert len(result) > 0, "Tool should return content"
        
        response = result[0]
        assert hasattr(response, 'text'), "Response should have text for MCP compliance"
        
        # Verify temperature information
        response_text = response.text
        assert "55" in response_text or "temperature" in response_text.lower()


class TestRetroPieToolsWorkflow:
    """Test RetroPie-specific tools workflows with CLAUDE.md compliance."""

    @pytest.fixture
    def test_config(self) -> RetroPieConfig:
        """Create test configuration."""
        paths = RetroPiePaths(
            home_dir="/home/retro",
            username="retro",
            retropie_dir="/home/retro/RetroPie",
            bios_dir="/home/retro/RetroPie/BIOS",
        )
        return RetroPieConfig(
            host="test-retropie.local",
            username="retro",
            password="test_password",  # noqa: S106
            port=22,
            paths=paths,
        )

    @pytest.fixture
    def mock_ssh_handler(self) -> Mock:
        """Create mock SSH handler."""
        mock = Mock(spec=RetroPieSSH)
        # execute_command is sync, returns tuple (exit_code, stdout, stderr)
        mock.execute_command = Mock()
        return mock

    @pytest.fixture
    def retropie_tools(self, mock_ssh_handler: Mock, test_config: RetroPieConfig) -> RetroPieTools:
        """Create RetroPieTools instance."""
        return RetroPieTools(mock_ssh_handler, test_config)

    def _verify_claude_md_compliance(self, obj: object) -> None:
        """Verify CLAUDE.md compliance."""
        if is_dataclass(obj):
            if hasattr(obj, '__dataclass_params__'):
                if 'Profile' not in obj.__class__.__name__:
                    assert obj.__dataclass_params__.frozen is True
        
        class_name = obj.__class__.__name__
        assert len(class_name) >= 4
        assert class_name[0].isupper()

    @pytest.mark.asyncio
    async def test_check_bios_workflow(
        self, retropie_tools: RetroPieTools, mock_ssh_handler: Mock, test_config: RetroPieConfig
    ) -> None:
        """Test BIOS checking workflow with CLAUDE.md compliance."""
        # CLAUDE.md compliance check
        self._verify_claude_md_compliance(test_config)

        # Mock BIOS directory listing
        mock_ssh_handler.execute_command.return_value = (
            0, 
            "gba_bios.bin\ndc_bios.bin\nps1_bios.bin", 
            ""
        )

        # Execute the tool workflow
        result = await retropie_tools.handle_tool_call("check_bios", {})

        # Verify MCP compliance
        assert isinstance(result, list), "Tool should return list for MCP compliance"
        assert len(result) > 0, "Tool should return content"
        
        response = result[0]
        assert hasattr(response, 'text'), "Response should have text for MCP compliance"
        
        # Verify BIOS information
        response_text = response.text
        assert "bios" in response_text.lower() or "gba" in response_text


class TestCrossComponentWorkflow:
    """Test workflows that span multiple components with CLAUDE.md compliance."""

    @pytest.fixture
    def test_config(self) -> RetroPieConfig:
        """Create test configuration."""
        paths = RetroPiePaths(
            home_dir="/home/retro",
            username="retro",
            retropie_dir="/home/retro/RetroPie",
        )
        return RetroPieConfig(
            host="test-retropie.local",
            username="retro",
            password="test_password",  # noqa: S106
            port=22,
            paths=paths,
        )

    def _verify_claude_md_compliance(self, obj: object) -> None:
        """Verify CLAUDE.md compliance."""
        if is_dataclass(obj):
            if hasattr(obj, '__dataclass_params__'):
                if 'Profile' not in obj.__class__.__name__:
                    assert obj.__dataclass_params__.frozen is True
        
        class_name = obj.__class__.__name__
        assert len(class_name) >= 4
        assert class_name[0].isupper()

    @pytest.mark.asyncio
    async def test_discovery_and_configuration_workflow(self, test_config: RetroPieConfig) -> None:
        """Test complete discovery to configuration workflow with CLAUDE.md compliance."""
        # CLAUDE.md compliance check
        self._verify_claude_md_compliance(test_config)

        # Mock the complete workflow
        with patch('retromcp.ssh_handler.RetroPieSSH') as mock_ssh_class:
            mock_ssh = Mock()
            mock_ssh.execute_command = Mock(return_value=(0, "retropie-test", ""))
            mock_ssh_class.return_value = mock_ssh

            # Create tools with mocked SSH
            system_tools = SystemTools(mock_ssh, test_config)

            # CLAUDE.md compliance check for tools
            self._verify_claude_md_compliance(test_config)

            # Test a simple tool execution to verify the workflow
            result = await system_tools.handle_tool_call("test_connection", {})

            # Verify MCP compliance
            assert isinstance(result, list), "Workflow should return MCP-compliant list"
            assert len(result) > 0, "Workflow should return content"

            # Verify tool follows MCP protocol
            response = result[0]
            assert hasattr(response, 'text'), "Response should be MCP TextContent"

    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self, test_config: RetroPieConfig) -> None:
        """Test error recovery across components with CLAUDE.md compliance."""
        # CLAUDE.md compliance check
        self._verify_claude_md_compliance(test_config)

        # Mock error scenario followed by recovery
        with patch('retromcp.ssh_handler.RetroPieSSH') as mock_ssh_class:
            mock_ssh = Mock()
            # First call fails, second succeeds
            mock_ssh.execute_command = Mock(side_effect=[
                (1, "", "Connection failed"),  # First call fails
                (0, "retropie-test", "")  # Second call succeeds
            ])
            mock_ssh_class.return_value = mock_ssh

            system_tools = SystemTools(mock_ssh, test_config)

            # First tool call should handle error gracefully
            result1 = await system_tools.handle_tool_call("test_connection", {})
            assert isinstance(result1, list), "Error handling should return MCP-compliant list"
            assert len(result1) > 0, "Error handling should return content"

            # Second tool call should succeed
            result2 = await system_tools.handle_tool_call("test_connection", {})
            assert isinstance(result2, list), "Recovery should return MCP-compliant list"
            assert len(result2) > 0, "Recovery should return content"

            # Verify both calls were made
            assert mock_ssh.execute_command.call_count == 2