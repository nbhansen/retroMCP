"""
Tests for cache integration in SSHSystemRepository.

Following TDD approach - these tests will initially fail until cache usage is implemented.
"""
import pytest
from unittest.mock import Mock

from retromcp.config import RetroPieConfig
from retromcp.domain.models import CommandResult, SystemInfo
from retromcp.domain.ports import RetroPieClient
from retromcp.infrastructure.ssh_system_repository import SSHSystemRepository
from retromcp.infrastructure.cache_system import SystemCache


class TestSSHSystemRepositoryCache:
    """Test cache integration in SSHSystemRepository."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = RetroPieConfig(
            host="test-host",
            username="test-user", 
            password="test-pass",
        )
        self.mock_client = Mock(spec=RetroPieClient)
        self.cache = SystemCache()
        self.repository = SSHSystemRepository(self.mock_client, self.config, self.cache)
    
    def test_get_system_info_caches_result_on_first_call(self):
        """Test that get_system_info caches the result on first call."""
        # Arrange
        self.mock_client.execute_command.side_effect = [
            CommandResult(command="hostname", exit_code=0, stdout="test-hostname", stderr="", success=True, execution_time=0.1),
            CommandResult(command="vcgencmd measure_temp", exit_code=0, stdout="temp=45.2'C", stderr="", success=True, execution_time=0.1),
            CommandResult(command="free -b", exit_code=0, stdout="             total       used       free\nMem:     4294967296 2147483648 2147483648", stderr="", success=True, execution_time=0.1),
            CommandResult(command="df -B1 /", exit_code=0, stdout="Filesystem     1B-blocks        Used  Available Use% Mounted on\n/dev/root   100000000000 50000000000 50000000000  50% /", stderr="", success=True, execution_time=0.1),
            CommandResult(command="uptime", exit_code=0, stdout=" 15:30:23 up 1 day,  2:10,  1 user,  load average: 0.15, 0.10, 0.05", stderr="", success=True, execution_time=0.1),
            CommandResult(command="cat /proc/uptime", exit_code=0, stdout="93600.45 86400.32", stderr="", success=True, execution_time=0.1),
        ]
        
        # Act - First call
        result = self.repository.get_system_info()
        
        # Assert - Result returned and cached
        assert isinstance(result, SystemInfo)
        assert result.hostname == "test-hostname"
        assert result.cpu_temperature == 45.2
        assert self.cache.get_system_info() is not None
        
        # Verify client was called for system commands
        assert self.mock_client.execute_command.call_count == 6
    
    def test_get_system_info_returns_cached_result_on_second_call(self):
        """Test that get_system_info returns cached result without SSH calls."""
        # Arrange - Pre-populate cache
        cached_info = SystemInfo(
            hostname="cached-hostname",
            cpu_temperature=42.0,
            memory_total=4000000000,
            memory_used=2000000000,
            memory_free=2000000000,
            disk_total=100000000000,
            disk_used=50000000000,
            disk_free=50000000000,
            load_average=[0.5, 0.3, 0.2],
            uptime=86400
        )
        self.cache.cache_system_info(cached_info)
        
        # Act - Call get_system_info
        result = self.repository.get_system_info()
        
        # Assert - Cached result returned, no SSH calls made
        assert result == cached_info
        assert result.hostname == "cached-hostname"
        assert result.cpu_temperature == 42.0
        self.mock_client.execute_command.assert_not_called()
    
    def test_get_system_info_fetches_fresh_data_when_cache_expired(self):
        """Test that get_system_info fetches fresh data when cache is expired."""
        # Arrange - Cache with expired TTL (0 seconds means immediate expiry)
        old_ttl = self.cache.system_info_ttl
        self.cache.system_info_ttl = 0  # Immediate expiry
        
        cached_info = SystemInfo(
            hostname="old-hostname",
            cpu_temperature=30.0,
            memory_total=3000000000,
            memory_used=1500000000,
            memory_free=1500000000,
            disk_total=80000000000,
            disk_used=40000000000,
            disk_free=40000000000,
            load_average=[0.2, 0.1, 0.1],
            uptime=43200
        )
        self.cache.cache_system_info(cached_info)
        
        # Fresh data from SSH
        self.mock_client.execute_command.side_effect = [
            CommandResult(command="hostname", exit_code=0, stdout="fresh-hostname", stderr="", success=True, execution_time=0.1),
            CommandResult(command="vcgencmd measure_temp", exit_code=0, stdout="temp=50.1'C", stderr="", success=True, execution_time=0.1),
            CommandResult(command="free -b", exit_code=0, stdout="             total       used       free\nMem:     8589934592 4294967296 4294967296", stderr="", success=True, execution_time=0.1),
            CommandResult(command="df -B1 /", exit_code=0, stdout="Filesystem     1B-blocks        Used  Available Use% Mounted on\n/dev/root   200000000000 100000000000 100000000000  50% /", stderr="", success=True, execution_time=0.1),
            CommandResult(command="uptime", exit_code=0, stdout=" 16:30:23 up 2 days,  3:10,  2 users,  load average: 0.25, 0.20, 0.15", stderr="", success=True, execution_time=0.1),
            CommandResult(command="cat /proc/uptime", exit_code=0, stdout="187200.90 172800.65", stderr="", success=True, execution_time=0.1),
        ]
        
        # Act
        result = self.repository.get_system_info()
        
        # Assert - Fresh data returned
        assert result.hostname == "fresh-hostname"
        assert result.cpu_temperature == 50.1
        assert result.memory_total == 8589934592
        assert self.mock_client.execute_command.call_count == 6
        
        # Restore original TTL
        self.cache.system_info_ttl = old_ttl
    
    def test_get_system_info_returns_cached_result_when_ssh_fails(self):
        """Test that get_system_info returns cached result when SSH commands would fail."""
        # Arrange - Pre-populate cache
        cached_info = SystemInfo(
            hostname="cached-hostname",
            cpu_temperature=42.0,
            memory_total=4000000000,
            memory_used=2000000000,
            memory_free=2000000000,
            disk_total=100000000000,
            disk_used=50000000000,
            disk_free=50000000000,
            load_average=[0.5, 0.3, 0.2],
            uptime=86400
        )
        self.cache.cache_system_info(cached_info)
        
        # SSH failure configured (but cache hit should prevent SSH calls)
        self.mock_client.execute_command.side_effect = [
            CommandResult(command="hostname", exit_code=1, stdout="", stderr="Connection failed", success=False, execution_time=0.1),
        ]
        
        # Act - Should return cached result without SSH calls
        result = self.repository.get_system_info()
        
        # Assert - Cached result returned, no SSH calls made due to cache hit
        assert result == cached_info
        assert result.hostname == "cached-hostname"
        self.mock_client.execute_command.assert_not_called()
    
    def test_multiple_repositories_share_same_cache_instance(self):
        """Test that multiple repository instances can share the same cache."""
        # Arrange - Second repository with same cache
        repository2 = SSHSystemRepository(Mock(spec=RetroPieClient), self.config, self.cache)
        
        # Populate cache via first repository
        cached_info = SystemInfo(
            hostname="shared-hostname",
            cpu_temperature=35.0,
            memory_total=2000000000,
            memory_used=1000000000,
            memory_free=1000000000,
            disk_total=60000000000,
            disk_used=30000000000,
            disk_free=30000000000,
            load_average=[0.3, 0.2, 0.1],
            uptime=21600
        )
        self.cache.cache_system_info(cached_info)
        
        # Act - Access via second repository
        result = repository2.get_system_info()
        
        # Assert - Same cached result
        assert result == cached_info
        assert result.hostname == "shared-hostname"