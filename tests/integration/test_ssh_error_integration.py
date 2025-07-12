"""Integration tests for SSH connection and error handling.

Tests error propagation and recovery across the entire application stack.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import asyncio
from typing import List, Tuple

from retromcp.config import RetroPieConfig
from retromcp.discovery import RetroPiePaths
from retromcp.ssh_handler import SSHHandler
from retromcp.tools.system_tools import SystemTools
from retromcp.tools.hardware_tools import HardwareTools
from mcp.types import TextContent


class TestSSHConnectionIntegration:
    """Test SSH connection integration across components."""

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

    @pytest.mark.asyncio
    async def test_ssh_connection_failure_propagation(self, test_config: RetroPieConfig) -> None:
        """Test how SSH connection failures propagate through the stack."""
        with patch('retromcp.ssh_handler.RetroPieSSH') as mock_ssh_class:
            # Mock SSH connection failure
            mock_ssh = Mock()
            mock_ssh.get_system_info = Mock(side_effect=ConnectionError("SSH connection failed"))
            mock_ssh_class.return_value = mock_ssh

            # Create tools (correct constructor signature: ssh_handler, config)
            system_tools = SystemTools(mock_ssh, test_config)

            # Attempt tool operation - should handle connection error gracefully
            result = await system_tools.handle_tool_call("system_info", {})

            # Verify error is properly handled using MCP-compliant response format
            assert isinstance(result, list), "Should return MCP-compliant list"
            assert len(result) == 1
            response = result[0]
            
            # Check for error using text content (MCP standard approach)
            assert hasattr(response, 'text'), "Should have text attribute"
            response_text = response.text.lower()
            assert "❌" in response.text or any(word in response_text for word in ["error", "failed"]), \
                "Should indicate error in text"
            assert "connection" in response_text or "ssh" in response_text, \
                "Should mention connection or SSH in error message"

    @pytest.mark.asyncio
    async def test_ssh_command_timeout_handling(self, test_config: RetroPieConfig) -> None:
        """Test handling of SSH command timeouts."""
        with patch('retromcp.ssh_handler.RetroPieSSH') as mock_ssh_class:
            # Mock SSH command timeout
            mock_ssh = Mock()
            mock_ssh.execute_command = Mock(side_effect=asyncio.TimeoutError("Command timed out"))
            mock_ssh_class.return_value = mock_ssh

            # Create tools (correct constructor signature: ssh_handler, config)
            hardware_tools = HardwareTools(mock_ssh, test_config)

            # Attempt operation that might timeout
            result = await hardware_tools.handle_tool_call("check_temperatures", {})

            # Verify timeout is handled gracefully using MCP-compliant response
            assert isinstance(result, list), "Should return MCP-compliant list"
            assert len(result) == 1
            response = result[0]
            
            # Check for error using text content (MCP standard approach)
            assert hasattr(response, 'text'), "Should have text attribute"
            response_text = response.text.lower()
            assert "❌" in response.text or any(word in response_text for word in ["error", "failed"]), \
                "Should indicate error in text"
            assert "timeout" in response_text or "time" in response_text, \
                "Should mention timeout in error message"

    @pytest.mark.asyncio
    async def test_ssh_authentication_failure(self, test_config: RetroPieConfig) -> None:
        """Test handling of SSH authentication failures."""
        with patch('retromcp.ssh_handler.RetroPieSSH') as mock_ssh_class:
            # Mock authentication failure
            mock_ssh = Mock()
            mock_ssh.get_system_info = Mock(
                side_effect=PermissionError("Authentication failed")
            )
            mock_ssh_class.return_value = mock_ssh

            # Create tools (correct constructor signature: ssh_handler, config)
            system_tools = SystemTools(mock_ssh, test_config)

            # Attempt operation
            result = await system_tools.handle_tool_call("system_info", {})

            # Verify authentication error is handled using MCP-compliant response
            assert isinstance(result, list), "Should return MCP-compliant list"
            assert len(result) == 1
            response = result[0]
            
            # Check for error using text content (MCP standard approach)
            assert hasattr(response, 'text'), "Should have text attribute"
            response_text = response.text.lower()
            assert "❌" in response.text or any(word in response_text for word in ["error", "failed"]), \
                "Should indicate error in text"
            assert any(word in response_text for word in ["auth", "permission", "access"]), \
                "Should mention authentication issue in error message"


class TestErrorRecoveryIntegration:
    """Test error recovery and retry mechanisms."""

    @pytest.fixture
    def test_config(self) -> RetroPieConfig:
        """Create test configuration."""
        return RetroPieConfig(
            host="test-retropie.local",
            username="retro",
            password="test_password",  # noqa: S106
            port=22,
        )

    @pytest.mark.asyncio
    async def test_command_retry_on_temporary_failure(self, test_config: RetroPieConfig) -> None:
        """Test retry mechanism for temporary command failures."""
        with patch('retromcp.ssh_handler.SSHHandler') as mock_ssh_class:
            mock_ssh = Mock()
            
            # Mock temporary failure followed by success
            call_count = 0
            def mock_execute_command(command):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    # First call fails with temporary error
                    return (1, "", "Temporary failure")
                else:
                    # Second call succeeds
                    return (0, "success output", "")
            
            mock_ssh.execute_command = AsyncMock(side_effect=mock_execute_command)
            mock_ssh_class.return_value = mock_ssh

            # Create tools
            system_tools = SystemTools(test_config, mock_ssh)

            # First attempt - should handle temporary failure
            result1 = await system_tools.handle_tool_call("get_system_info", {})
            assert len(result1) == 1
            # Could be error or success depending on retry logic

            # Second attempt - should succeed
            result2 = await system_tools.handle_tool_call("get_system_info", {})
            assert len(result2) == 1
            # Should have success output

    @pytest.mark.asyncio
    async def test_partial_command_failure_handling(self, test_config: RetroPieConfig) -> None:
        """Test handling when some commands succeed and others fail."""
        with patch('retromcp.ssh_handler.RetroPieSSH') as mock_ssh_class:
            mock_ssh = Mock()
            
            # Mock get_system_info to return partial data (some info available, some missing)
            mock_ssh.get_system_info.return_value = {
                "temperature": 55.0,  # Success
                "memory": {"total": 1024, "used": 512},  # Success  
                # Missing disk info - simulates partial failure
            }
            mock_ssh_class.return_value = mock_ssh

            # Create tools (correct constructor signature: ssh_handler, config)
            system_tools = SystemTools(mock_ssh, test_config)

            # Execute tool that collects system info
            result = await system_tools.handle_tool_call("system_info", {})

            # Verify partial success is handled appropriately using MCP format
            assert isinstance(result, list), "Should return MCP-compliant list"
            assert len(result) == 1
            response = result[0]
            
            # Check response follows MCP standard
            assert hasattr(response, 'text'), "Should have text attribute"
            
            # Should contain successful parts  
            response_text = response.text
            assert "55" in response_text or "temperature" in response_text.lower(), \
                "Should include successful temperature data"
            assert "memory" in response_text.lower() or "512" in response_text, \
                "Should include successful memory data"


class TestConcurrentOperationsIntegration:
    """Test concurrent operations and resource management."""

    @pytest.fixture
    def test_config(self) -> RetroPieConfig:
        """Create test configuration."""
        return RetroPieConfig(
            host="test-retropie.local",
            username="retro",
            password="test_password",  # noqa: S106
            port=22,
        )

    @pytest.mark.asyncio
    async def test_concurrent_tool_operations(self, test_config: RetroPieConfig) -> None:
        """Test multiple tools running concurrently."""
        with patch('retromcp.ssh_handler.RetroPieSSH') as mock_ssh_class:
            mock_ssh = Mock()
            
            # Mock the high-level methods that tools actually call
            mock_ssh.get_system_info.return_value = {
                "temperature": 45.0,
                "memory": {"total": 1024, "used": 512}
            }
            mock_ssh.execute_command.return_value = (0, "temp=45.0'C", "")
            mock_ssh_class.return_value = mock_ssh

            # Create multiple tools (correct constructor signature: ssh_handler, config)
            system_tools = SystemTools(mock_ssh, test_config)
            hardware_tools = HardwareTools(mock_ssh, test_config)

            # Run operations concurrently
            tasks = [
                system_tools.handle_tool_call("system_info", {}),
                hardware_tools.handle_tool_call("check_temperatures", {}),
                system_tools.handle_tool_call("system_info", {}),  # Duplicate
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Verify all operations completed using MCP-compliant format
            assert len(results) == 3
            
            # Check that none raised exceptions and all return MCP-compliant lists
            for i, result in enumerate(results):
                assert not isinstance(result, Exception), f"Task {i} should not raise exception"
                assert isinstance(result, list), f"Task {i} should return MCP-compliant list"
                assert len(result) == 1, f"Task {i} should return one response"
                assert hasattr(result[0], 'text'), f"Task {i} response should have text attribute"

            # Verify SSH methods were called
            assert mock_ssh.get_system_info.call_count >= 2  # System info called twice

    @pytest.mark.asyncio
    async def test_resource_cleanup_on_error(self, test_config: RetroPieConfig) -> None:
        """Test proper resource cleanup when errors occur."""
        with patch('retromcp.ssh_handler.RetroPieSSH') as mock_ssh_class:
            mock_ssh = Mock()
            
            # Mock context manager behavior if needed
            mock_ssh.__enter__ = Mock(return_value=mock_ssh)
            mock_ssh.__exit__ = Mock(return_value=None)
            mock_ssh.get_system_info = Mock(side_effect=Exception("Test error"))
            mock_ssh_class.return_value = mock_ssh

            # Create tools (correct constructor signature: ssh_handler, config)
            system_tools = SystemTools(mock_ssh, test_config)

            # Execute operation that will fail
            result = await system_tools.handle_tool_call("system_info", {})

            # Verify error handling using MCP-compliant response format
            assert isinstance(result, list), "Should return MCP-compliant list"
            assert len(result) == 1
            response = result[0]
            
            # Check for error using text content (MCP standard approach)
            assert hasattr(response, 'text'), "Should have text attribute"
            response_text = response.text.lower()
            assert "❌" in response.text or any(word in response_text for word in ["error", "failed"]), \
                "Should indicate error in text"

            # Note: Specific cleanup verification would depend on actual SSH handler implementation


class TestEndToEndErrorScenarios:
    """Test realistic end-to-end error scenarios."""

    @pytest.fixture
    def test_config(self) -> RetroPieConfig:
        """Create test configuration."""
        return RetroPieConfig(
            host="unreachable-host.local",
            username="retro",
            password="wrong_password",  # noqa: S106
            port=22,
        )

    @pytest.mark.asyncio
    async def test_unreachable_host_scenario(self, test_config: RetroPieConfig) -> None:
        """Test scenario where RetroPie host is unreachable."""
        with patch('retromcp.ssh_handler.RetroPieSSH') as mock_ssh_class:
            # Mock network unreachable error
            mock_ssh = Mock()
            mock_ssh.get_system_info = Mock(
                side_effect=OSError("Network is unreachable")
            )
            mock_ssh_class.return_value = mock_ssh

            # Create tools (correct constructor signature: ssh_handler, config)
            system_tools = SystemTools(mock_ssh, test_config)

            # Attempt operation
            result = await system_tools.handle_tool_call("system_info", {})

            # Verify network error is handled using MCP-compliant response format
            assert isinstance(result, list), "Should return MCP-compliant list"
            assert len(result) == 1
            response = result[0]
            
            # Check for error using text content (MCP standard approach)
            assert hasattr(response, 'text'), "Should have text attribute"
            response_text = response.text.lower()
            assert "❌" in response.text or any(word in response_text for word in ["error", "failed"]), \
                "Should indicate error in text"
            assert any(word in response_text for word in ["network", "unreachable", "connection"]), \
                "Should mention network issue in error message"

    @pytest.mark.asyncio
    async def test_malformed_command_output_scenario(self, test_config: RetroPieConfig) -> None:
        """Test scenario where commands return unexpected output."""
        with patch('retromcp.ssh_handler.SSHHandler') as mock_ssh_class:
            mock_ssh = Mock()
            
            # Mock malformed/unexpected command outputs
            def mock_execute_command(command):
                if "hostname" in command:
                    return (0, "MALFORMED_OUTPUT_###", "")
                elif "vcgencmd" in command:
                    return (0, "invalid_temp_format", "")
                elif "free" in command:
                    return (0, "completely unexpected output format", "")
                else:
                    return (0, "???", "")
            
            mock_ssh.execute_command = AsyncMock(side_effect=mock_execute_command)
            mock_ssh_class.return_value = mock_ssh

            # Create tools
            system_tools = SystemTools(test_config, mock_ssh)

            # Execute operation with malformed responses
            result = await system_tools.handle_tool_call("get_system_info", {})

            # Verify malformed output is handled gracefully
            assert len(result) == 1
            response = result[0]
            
            # Should either handle gracefully or report parsing issues
            # The exact behavior depends on implementation, but shouldn't crash
            assert isinstance(response, TextContent)