"""Tests for cache system integration with dependency injection container.

Following TDD approach - these tests will initially fail until integration is complete.
"""

from retromcp.config import RetroPieConfig
from retromcp.container import Container
from retromcp.infrastructure.cache_system import SystemCache


class TestCacheContainerIntegration:
    """Test cache system integration with dependency injection container."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = RetroPieConfig(
            host="test-host",
            username="test-user",
            password="test-pass",
        )
        self.container = Container(self.config)

    def test_container_provides_system_cache_singleton(self):
        """Test that container provides SystemCache as singleton."""
        # Act
        cache1 = self.container.system_cache
        cache2 = self.container.system_cache

        # Assert
        assert isinstance(cache1, SystemCache)
        assert cache1 is cache2  # Singleton behavior

    def test_system_repository_receives_cache_dependency(self):
        """Test that system repository receives cache as dependency."""
        # Act
        system_repo = self.container.system_repository

        # Assert - Repository should have cache injected
        assert hasattr(system_repo, "_cache")
        assert isinstance(system_repo._cache, SystemCache)

    def test_controller_repository_receives_cache_dependency(self):
        """Test that controller repository receives cache as dependency."""
        # Act
        controller_repo = self.container.controller_repository

        # Assert - Repository should have cache injected
        assert hasattr(controller_repo, "_cache")
        assert isinstance(controller_repo._cache, SystemCache)

    def test_cache_instances_are_shared_across_repositories(self):
        """Test that all repositories share the same cache instance."""
        # Act
        system_repo = self.container.system_repository
        controller_repo = self.container.controller_repository
        cache_instance = self.container.system_cache

        # Assert - All should use the same cache instance
        assert system_repo._cache is cache_instance
        assert controller_repo._cache is cache_instance

    def test_container_cache_integration_doesnt_break_existing_functionality(self):
        """Test that cache integration doesn't break existing repository creation."""
        # Act - These should not raise exceptions
        system_repo = self.container.system_repository
        controller_repo = self.container.controller_repository
        emulator_repo = self.container.emulator_repository

        # Assert - Repositories should be created successfully
        assert system_repo is not None
        assert controller_repo is not None
        assert emulator_repo is not None
