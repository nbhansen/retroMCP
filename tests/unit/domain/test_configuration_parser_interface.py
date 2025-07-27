"""Unit tests for ConfigurationParser interface."""

from abc import ABC

import pytest

from retromcp.domain.models import ESSystemsConfig
from retromcp.domain.models import Result
from retromcp.domain.models import ValidationError
from retromcp.domain.ports import ConfigurationParser


@pytest.mark.unit
@pytest.mark.domain
class TestConfigurationParserInterface:
    """Test cases for ConfigurationParser interface."""

    def test_configuration_parser_is_abstract_base_class(self):
        """Test that ConfigurationParser is an abstract base class."""
        # Assert
        assert issubclass(ConfigurationParser, ABC)
        assert hasattr(ConfigurationParser, '__abstractmethods__')
        assert 'parse_es_systems_config' in ConfigurationParser.__abstractmethods__

    def test_configuration_parser_cannot_be_instantiated(self):
        """Test that ConfigurationParser cannot be instantiated directly."""
        # Act & Assert
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            ConfigurationParser()  # type: ignore

    def test_configuration_parser_has_correct_method_signature(self):
        """Test that parse_es_systems_config method has correct signature."""
        # Arrange - Create a concrete implementation for testing
        class TestParser(ConfigurationParser):
            def parse_es_systems_config(self, content: str) -> Result[ESSystemsConfig, ValidationError]:
                return Result.success(ESSystemsConfig(systems=[]))

        parser = TestParser()

        # Act
        result = parser.parse_es_systems_config("")

        # Assert
        assert result is not None
        assert hasattr(result, 'is_success')
        assert hasattr(result, 'is_error')

    def test_configuration_parser_concrete_implementation_required(self):
        """Test that concrete implementations must implement all abstract methods."""
        # Arrange - Create incomplete implementation
        class IncompleteParser(ConfigurationParser):
            pass  # Missing parse_es_systems_config implementation

        # Act & Assert
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteParser()  # type: ignore

    def test_configuration_parser_method_returns_result_type(self):
        """Test that parse_es_systems_config returns Result type."""
        # Arrange
        class MockParser(ConfigurationParser):
            def parse_es_systems_config(self, content: str) -> Result[ESSystemsConfig, ValidationError]:
                # Return success case
                if content == "valid":
                    config = ESSystemsConfig(systems=[])
                    return Result.success(config)
                # Return failure case
                else:
                    error = ValidationError(
                        code="INVALID_XML",
                        message="Invalid XML content"
                    )
                    return Result.error(error)

        parser = MockParser()

        # Act - Test success case
        success_result = parser.parse_es_systems_config("valid")
        failure_result = parser.parse_es_systems_config("invalid")

        # Assert - Success case
        assert success_result.is_success()
        assert not success_result.is_error()
        config = success_result.success_value
        assert isinstance(config, ESSystemsConfig)
        assert config.systems == []

        # Assert - Failure case
        assert failure_result.is_error()
        assert not failure_result.is_success()
        error = failure_result.error_value
        assert isinstance(error, ValidationError)
        assert error.code == "INVALID_XML"
        assert error.message == "Invalid XML content"
