"""Unit tests for cache system."""

import time
from datetime import datetime
from datetime import timedelta

import pytest

from retromcp.domain.models import SystemInfo
from retromcp.infrastructure.cache_system import CacheEntry
from retromcp.infrastructure.cache_system import SystemCache
from retromcp.infrastructure.cache_system import TTLCache


class TestCacheEntry:
    """Test cases for CacheEntry."""

    def test_cache_entry_creation(self) -> None:
        """Test cache entry creation with data and timestamp."""
        data = {"test": "value"}
        entry = CacheEntry(data=data, timestamp=datetime.now(), ttl_seconds=300)

        assert entry.data == data
        assert entry.ttl_seconds == 300
        assert isinstance(entry.timestamp, datetime)

    def test_cache_entry_immutability(self) -> None:
        """Test that CacheEntry is immutable."""
        entry = CacheEntry(
            data={"test": "value"}, timestamp=datetime.now(), ttl_seconds=300
        )

        # Test that entry is frozen
        with pytest.raises(AttributeError):
            entry.data = {"new": "value"}  # type: ignore

    def test_is_expired_fresh_entry(self) -> None:
        """Test that fresh entry is not expired."""
        entry = CacheEntry(
            data={"test": "value"}, timestamp=datetime.now(), ttl_seconds=300
        )

        assert not entry.is_expired()

    def test_is_expired_old_entry(self) -> None:
        """Test that old entry is expired."""
        old_timestamp = datetime.now() - timedelta(seconds=400)
        entry = CacheEntry(
            data={"test": "value"}, timestamp=old_timestamp, ttl_seconds=300
        )

        assert entry.is_expired()

    def test_is_expired_zero_ttl(self) -> None:
        """Test that zero TTL always expires immediately."""
        entry = CacheEntry(
            data={"test": "value"}, timestamp=datetime.now(), ttl_seconds=0
        )

        assert entry.is_expired()


class TestTTLCache:
    """Test cases for TTL cache implementation."""

    @pytest.fixture
    def cache(self) -> TTLCache:
        """Provide TTL cache instance."""
        return TTLCache()

    def test_cache_set_and_get(self, cache: TTLCache) -> None:
        """Test basic cache set and get operations."""
        key = "test_key"
        value = {"data": "test_value"}
        ttl = 300

        cache.set(key, value, ttl)
        result = cache.get(key)

        assert result == value

    def test_cache_get_nonexistent_key(self, cache: TTLCache) -> None:
        """Test getting non-existent key returns None."""
        result = cache.get("nonexistent")
        assert result is None

    def test_cache_expiration(self, cache: TTLCache) -> None:
        """Test that expired entries are not returned."""
        key = "test_key"
        value = {"data": "test_value"}

        # Set with very short TTL
        cache.set(key, value, ttl_seconds=0.1)

        # Wait for expiration
        time.sleep(0.2)

        result = cache.get(key)
        assert result is None

    def test_cache_has_key(self, cache: TTLCache) -> None:
        """Test cache key existence check."""
        key = "test_key"
        value = {"data": "test_value"}

        assert not cache.has(key)

        cache.set(key, value, 300)
        assert cache.has(key)

    def test_cache_has_expired_key(self, cache: TTLCache) -> None:
        """Test that expired key is considered as not having the key."""
        key = "test_key"
        value = {"data": "test_value"}

        # Set with very short TTL
        cache.set(key, value, ttl_seconds=0.1)

        # Wait for expiration
        time.sleep(0.2)

        assert not cache.has(key)

    def test_cache_clear(self, cache: TTLCache) -> None:
        """Test cache clearing functionality."""
        cache.set("key1", {"data": "value1"}, 300)
        cache.set("key2", {"data": "value2"}, 300)

        assert cache.has("key1")
        assert cache.has("key2")

        cache.clear()

        assert not cache.has("key1")
        assert not cache.has("key2")

    def test_cache_invalidate(self, cache: TTLCache) -> None:
        """Test cache invalidation for specific key."""
        key = "test_key"
        value = {"data": "test_value"}

        cache.set(key, value, 300)
        assert cache.has(key)

        cache.invalidate(key)
        assert not cache.has(key)

    def test_cache_cleanup_expired_entries(self, cache: TTLCache) -> None:
        """Test that cleanup removes expired entries."""
        # Add fresh entry
        cache.set("fresh", {"data": "fresh_value"}, 300)

        # Add expired entry
        cache.set("expired", {"data": "expired_value"}, 0.1)
        time.sleep(0.2)

        # Trigger cleanup
        cache.cleanup()

        assert cache.has("fresh")
        assert not cache.has("expired")


class TestSystemCache:
    """Test cases for system-specific cache."""

    @pytest.fixture
    def cache(self) -> SystemCache:
        """Provide SystemCache instance."""
        return SystemCache()

    @pytest.fixture
    def sample_system_info(self) -> SystemInfo:
        """Provide sample system info."""
        return SystemInfo(
            hostname="test-host",
            cpu_temperature=65.0,
            memory_total=8000000000,
            memory_used=2000000000,
            memory_free=6000000000,
            disk_total=32000000000,
            disk_used=8000000000,
            disk_free=24000000000,
            load_average=[0.5, 0.3, 0.2],
            uptime=86400,
        )

    def test_cache_system_info(
        self, cache: SystemCache, sample_system_info: SystemInfo
    ) -> None:
        """Test caching system information."""
        cache.cache_system_info(sample_system_info)

        result = cache.get_system_info()
        assert result is not None
        assert result.hostname == sample_system_info.hostname
        assert result.cpu_temperature == sample_system_info.cpu_temperature

    def test_cache_hardware_scan(self, cache: SystemCache) -> None:
        """Test caching hardware scan results."""
        hardware_data = {
            "model": "Raspberry Pi 5",
            "gpio_usage": {"614": "fan_control"},
            "cooling_active": True,
        }

        cache.cache_hardware_scan(hardware_data)

        result = cache.get_hardware_scan()
        assert result is not None
        assert result["model"] == "Raspberry Pi 5"
        assert result["cooling_active"] is True

    def test_cache_network_scan(self, cache: SystemCache) -> None:
        """Test caching network scan results."""
        network_data = [
            {"name": "eth0", "ip": "192.168.1.100", "status": "up", "speed": "1000Mbps"}
        ]

        cache.cache_network_scan(network_data)

        result = cache.get_network_scan()
        assert result is not None
        assert len(result) == 1
        assert result[0]["name"] == "eth0"

    def test_cache_service_status(self, cache: SystemCache) -> None:
        """Test caching service status."""
        services_data = [
            {"name": "docker.service", "status": "running", "enabled": True}
        ]

        cache.cache_service_status(services_data)

        result = cache.get_service_status()
        assert result is not None
        assert len(result) == 1
        assert result[0]["name"] == "docker.service"

    def test_cache_expiration_system_info(
        self, cache: SystemCache, sample_system_info: SystemInfo
    ) -> None:
        """Test that system info cache expires."""
        # Override TTL for testing
        cache.system_info_ttl = 0.1

        cache.cache_system_info(sample_system_info)
        assert cache.get_system_info() is not None

        # Wait for expiration
        time.sleep(0.2)

        assert cache.get_system_info() is None

    def test_cache_invalidation(
        self, cache: SystemCache, sample_system_info: SystemInfo
    ) -> None:
        """Test cache invalidation functionality."""
        hardware_data = {"model": "Pi 5"}

        cache.cache_system_info(sample_system_info)
        cache.cache_hardware_scan(hardware_data)

        assert cache.get_system_info() is not None
        assert cache.get_hardware_scan() is not None

        # Invalidate specific cache
        cache.invalidate_system_info()
        assert cache.get_system_info() is None
        assert cache.get_hardware_scan() is not None

        # Clear all caches
        cache.clear_all()
        assert cache.get_hardware_scan() is None

    def test_cache_performance_tracking(self, cache: SystemCache) -> None:
        """Test cache performance tracking."""
        # Initially no stats
        stats = cache.get_cache_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0

        # Cache miss
        result = cache.get_system_info()
        assert result is None

        stats = cache.get_cache_stats()
        assert stats["misses"] == 1

        # Cache hit
        sample_info = SystemInfo(
            hostname="test",
            cpu_temperature=60.0,
            memory_total=8000000000,
            memory_used=2000000000,
            memory_free=6000000000,
            disk_total=32000000000,
            disk_used=8000000000,
            disk_free=24000000000,
            load_average=[0.1, 0.2, 0.3],
            uptime=3600,
        )
        cache.cache_system_info(sample_info)
        result = cache.get_system_info()
        assert result is not None

        stats = cache.get_cache_stats()
        assert stats["hits"] == 1
