"""
Tests for cache integration in SSHControllerRepository.

Following TDD approach - these tests will initially fail until cache usage is implemented.
"""
import pytest
from unittest.mock import Mock
from typing import List

from retromcp.domain.models import CommandResult, Controller, ControllerType
from retromcp.domain.ports import RetroPieClient
from retromcp.infrastructure.ssh_controller_repository import SSHControllerRepository
from retromcp.infrastructure.cache_system import SystemCache


class TestSSHControllerRepositoryCache:
    """Test cache integration in SSHControllerRepository."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_client = Mock(spec=RetroPieClient)
        self.cache = SystemCache()
        self.repository = SSHControllerRepository(self.mock_client, self.cache)
    
    def test_detect_controllers_caches_result_on_first_call(self):
        """Test that detect_controllers caches the result on first call."""
        # Arrange
        self.mock_client.execute_command.side_effect = [
            CommandResult(command="ls -la /dev/input/js* 2>/dev/null", exit_code=0, stdout="crw-rw---- 1 root input 13, 0 Jul 19 17:00 /dev/input/js0", stderr="", success=True, execution_time=0.1),
            CommandResult(command="lsusb", exit_code=0, stdout="Bus 001 Device 002: ID 045e:028e Microsoft Corp. Xbox360 Controller", stderr="", success=True, execution_time=0.1),
            CommandResult(command="cat /proc/bus/input/devices | grep -B 5 js0 | grep Name | head -1", exit_code=0, stdout='N: Name="Microsoft Xbox 360 pad"', stderr="", success=True, execution_time=0.1),
            CommandResult(command="grep -q 'input_device.*Microsoft Xbox 360 pad' /opt/retropie/configs/all/retroarch.cfg", exit_code=0, stdout="", stderr="", success=True, execution_time=0.1),
            CommandResult(command="lsmod | grep -q xpad", exit_code=0, stdout="", stderr="", success=True, execution_time=0.1),
        ]
        
        # Act - First call
        result = self.repository.detect_controllers()
        
        # Assert - Result returned and cached
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].name == "Microsoft Xbox 360 pad"
        assert result[0].controller_type == ControllerType.XBOX
        assert self.cache.get_hardware_scan() is not None
        
        # Verify client was called for controller detection commands
        assert self.mock_client.execute_command.call_count == 5
    
    def test_detect_controllers_returns_cached_result_on_second_call(self):
        """Test that detect_controllers returns cached result without SSH calls."""
        # Arrange - Pre-populate cache with controller data
        cached_controllers = [
            Controller(
                name="Cached Controller",
                device_path="/dev/input/js0",
                controller_type=ControllerType.PS4,
                connected=True,
                vendor_id="054c",
                product_id="05c4",
                is_configured=True,
                driver_required=None
            )
        ]
        self.cache.cache_hardware_scan({"controllers": cached_controllers})
        
        # Act - Call detect_controllers
        result = self.repository.detect_controllers()
        
        # Assert - Cached result returned, no SSH calls made
        assert result == cached_controllers
        assert len(result) == 1
        assert result[0].name == "Cached Controller"
        assert result[0].controller_type == ControllerType.PS4
        self.mock_client.execute_command.assert_not_called()
    
    def test_detect_controllers_fetches_fresh_data_when_cache_expired(self):
        """Test that detect_controllers fetches fresh data when cache is expired."""
        # Arrange - Cache with expired TTL (0 seconds means immediate expiry)
        old_ttl = self.cache.hardware_scan_ttl
        self.cache.hardware_scan_ttl = 0  # Immediate expiry
        
        cached_controllers = [
            Controller(
                name="Old Controller",
                device_path="/dev/input/js1",
                controller_type=ControllerType.UNKNOWN,
                connected=True,
                vendor_id="0000",
                product_id="0000",
                is_configured=False,
                driver_required=None
            )
        ]
        self.cache.cache_hardware_scan({"controllers": cached_controllers})
        
        # Fresh data from SSH
        self.mock_client.execute_command.side_effect = [
            CommandResult(command="ls -la /dev/input/js* 2>/dev/null", exit_code=0, stdout="crw-rw---- 1 root input 13, 0 Jul 19 17:00 /dev/input/js0", stderr="", success=True, execution_time=0.1),
            CommandResult(command="lsusb", exit_code=0, stdout="Bus 001 Device 003: ID 054c:09cc Sony Corp. DualShock 4 Wireless Controller", stderr="", success=True, execution_time=0.1),
            CommandResult(command="cat /proc/bus/input/devices | grep -B 5 js0 | grep Name | head -1", exit_code=0, stdout='N: Name="Sony PLAYSTATION(R)4 Wireless Controller"', stderr="", success=True, execution_time=0.1),
            CommandResult(command="grep -q 'input_device.*Sony PLAYSTATION(R)4 Wireless Controller' /opt/retropie/configs/all/retroarch.cfg", exit_code=1, stdout="", stderr="", success=False, execution_time=0.1),
            CommandResult(command="which ds4drv", exit_code=1, stdout="", stderr="", success=False, execution_time=0.1),
        ]
        
        # Act
        result = self.repository.detect_controllers()
        
        # Assert - Fresh data returned
        assert len(result) == 1
        assert result[0].name == "Sony PLAYSTATION(R)4 Wireless Controller"
        assert result[0].controller_type == ControllerType.PS4
        assert result[0].driver_required == "ds4drv"
        assert self.mock_client.execute_command.call_count == 5
        
        # Restore original TTL
        self.cache.hardware_scan_ttl = old_ttl
    
    def test_detect_controllers_returns_cached_result_when_ssh_fails(self):
        """Test that detect_controllers returns cached result when SSH commands would fail."""
        # Arrange - Pre-populate cache
        cached_controllers = [
            Controller(
                name="Cached Controller",
                device_path="/dev/input/js0",
                controller_type=ControllerType.NINTENDO_PRO,
                connected=True,
                vendor_id="057e",
                product_id="2009",
                is_configured=True,
                driver_required=None
            )
        ]
        self.cache.cache_hardware_scan({"controllers": cached_controllers})
        
        # SSH failure configured (but cache hit should prevent SSH calls)
        self.mock_client.execute_command.side_effect = [
            CommandResult(command="ls -la /dev/input/js* 2>/dev/null", exit_code=1, stdout="", stderr="No such file or directory", success=False, execution_time=0.1),
        ]
        
        # Act - Should return cached result without SSH calls
        result = self.repository.detect_controllers()
        
        # Assert - Cached result returned, no SSH calls made due to cache hit
        assert result == cached_controllers
        assert len(result) == 1
        assert result[0].name == "Cached Controller"
        assert result[0].controller_type == ControllerType.NINTENDO_PRO
        self.mock_client.execute_command.assert_not_called()
    
    def test_multiple_repositories_share_same_cache_instance(self):
        """Test that multiple repository instances can share the same cache."""
        # Arrange - Second repository with same cache
        repository2 = SSHControllerRepository(Mock(spec=RetroPieClient), self.cache)
        
        # Populate cache via first repository
        cached_controllers = [
            Controller(
                name="Shared Controller",
                device_path="/dev/input/js0",
                controller_type=ControllerType.EIGHT_BIT_DO,
                connected=True,
                vendor_id="2dc8",
                product_id="ab20",
                is_configured=False,
                driver_required=None
            )
        ]
        self.cache.cache_hardware_scan({"controllers": cached_controllers})
        
        # Act - Access via second repository
        result = repository2.detect_controllers()
        
        # Assert - Same cached result
        assert result == cached_controllers
        assert len(result) == 1
        assert result[0].name == "Shared Controller"
        assert result[0].controller_type == ControllerType.EIGHT_BIT_DO