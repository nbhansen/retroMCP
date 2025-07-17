"""Cache system for expensive system operations."""

from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from typing import Any
from typing import Dict
from typing import Generic
from typing import List
from typing import Optional
from typing import TypeVar

from ..domain.models import SystemInfo

T = TypeVar("T")


@dataclass(frozen=True)
class CacheEntry:
    """Cache entry with TTL support."""

    data: Any
    timestamp: datetime
    ttl_seconds: int

    def is_expired(self) -> bool:
        """Check if entry is expired."""
        if self.ttl_seconds == 0:
            return True

        expiry_time = self.timestamp + timedelta(seconds=self.ttl_seconds)
        return datetime.now() > expiry_time


class TTLCache(Generic[T]):
    """Generic TTL-based cache implementation."""

    def __init__(self) -> None:
        """Initialize empty cache."""
        self._cache: Dict[str, CacheEntry] = {}
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[T]:
        """Get value from cache if not expired."""
        if key not in self._cache:
            self._misses += 1
            return None

        entry = self._cache[key]
        if entry.is_expired():
            del self._cache[key]
            self._misses += 1
            return None

        self._hits += 1
        return entry.data

    def set(self, key: str, value: T, ttl_seconds: int = 300) -> None:
        """Set value in cache with TTL."""
        entry = CacheEntry(
            data=value, timestamp=datetime.now(), ttl_seconds=ttl_seconds
        )
        self._cache[key] = entry

    def has(self, key: str) -> bool:
        """Check if key exists and is not expired."""
        if key not in self._cache:
            return False

        entry = self._cache[key]
        if entry.is_expired():
            del self._cache[key]
            return False

        return True

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0

    def invalidate(self, key: str) -> None:
        """Remove specific key from cache."""
        if key in self._cache:
            del self._cache[key]

    def cleanup(self) -> None:
        """Remove expired entries from cache."""
        expired_keys = []
        for key, entry in self._cache.items():
            if entry.is_expired():
                expired_keys.append(key)

        for key in expired_keys:
            del self._cache[key]

    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return {"hits": self._hits, "misses": self._misses, "entries": len(self._cache)}


class SystemCache:
    """System-specific cache for expensive operations."""

    def __init__(self) -> None:
        """Initialize system cache."""
        self._cache = TTLCache[Any]()
        # Default TTL values for different types of data
        self.system_info_ttl = 30  # 30 seconds
        self.hardware_scan_ttl = 300  # 5 minutes
        self.network_scan_ttl = 60  # 1 minute
        self.service_status_ttl = 30  # 30 seconds

    def cache_system_info(self, info: SystemInfo) -> None:
        """Cache system information."""
        self._cache.set("system_info", info, self.system_info_ttl)

    def get_system_info(self) -> Optional[SystemInfo]:
        """Get cached system information."""
        return self._cache.get("system_info")

    def cache_hardware_scan(self, data: Dict[str, Any]) -> None:
        """Cache hardware scan results."""
        self._cache.set("hardware_scan", data, self.hardware_scan_ttl)

    def get_hardware_scan(self) -> Optional[Dict[str, Any]]:
        """Get cached hardware scan results."""
        return self._cache.get("hardware_scan")

    def cache_network_scan(self, data: List[Dict[str, Any]]) -> None:
        """Cache network scan results."""
        self._cache.set("network_scan", data, self.network_scan_ttl)

    def get_network_scan(self) -> Optional[List[Dict[str, Any]]]:
        """Get cached network scan results."""
        return self._cache.get("network_scan")

    def cache_service_status(self, data: List[Dict[str, Any]]) -> None:
        """Cache service status results."""
        self._cache.set("service_status", data, self.service_status_ttl)

    def get_service_status(self) -> Optional[List[Dict[str, Any]]]:
        """Get cached service status results."""
        return self._cache.get("service_status")

    def invalidate_system_info(self) -> None:
        """Invalidate system info cache."""
        self._cache.invalidate("system_info")

    def invalidate_hardware_scan(self) -> None:
        """Invalidate hardware scan cache."""
        self._cache.invalidate("hardware_scan")

    def invalidate_network_scan(self) -> None:
        """Invalidate network scan cache."""
        self._cache.invalidate("network_scan")

    def invalidate_service_status(self) -> None:
        """Invalidate service status cache."""
        self._cache.invalidate("service_status")

    def clear_all(self) -> None:
        """Clear all cached data."""
        self._cache.clear()

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache performance statistics."""
        return self._cache.get_stats()
