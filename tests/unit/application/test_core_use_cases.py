"""Unit tests for core management use cases."""

from unittest.mock import Mock

import pytest

from retromcp.application.core_use_cases import GetCoreInfoUseCase
from retromcp.application.core_use_cases import GetEmulatorMappingsUseCase
from retromcp.application.core_use_cases import ListCoreOptionsUseCase
from retromcp.application.core_use_cases import ListCoresUseCase
from retromcp.application.core_use_cases import SetDefaultEmulatorUseCase
from retromcp.application.core_use_cases import UpdateCoreOptionUseCase
from retromcp.domain.models import CoreOption
from retromcp.domain.models import DomainError
from retromcp.domain.models import EmulatorMapping
from retromcp.domain.models import Result
from retromcp.domain.models import RetroArchCore
from retromcp.domain.models import ValidationError


@pytest.mark.unit
@pytest.mark.application
class TestListCoresUseCase:
    """Test ListCoresUseCase."""

    @pytest.fixture
    def mock_repository(self) -> Mock:
        """Create mock repository."""
        return Mock()

    @pytest.fixture
    def use_case(self, mock_repository: Mock) -> ListCoresUseCase:
        """Create use case with mock repository."""
        return ListCoresUseCase(mock_repository)

    def test_execute_success(self, use_case: ListCoresUseCase, mock_repository: Mock):
        """Test successful core listing."""
        # Arrange
        cores = [
            RetroArchCore(
                name="lr-mupen64plus-next",
                core_path="/opt/retropie/libretrocores/lr-mupen64plus-next/core.so",
                systems=["n64"],
                version="1.0",
                display_name="Mupen64Plus-Next",
            ),
            RetroArchCore(
                name="lr-snes9x",
                core_path="/opt/retropie/libretrocores/lr-snes9x/snes9x_libretro.so",
                systems=["snes"],
                display_name="Snes9x",
            ),
        ]
        mock_repository.list_cores.return_value = Result.success(cores)

        # Act
        result = use_case.execute()

        # Assert
        assert result.is_success()
        assert len(result.success_value) == 2
        assert result.success_value[0].name == "lr-mupen64plus-next"
        mock_repository.list_cores.assert_called_once()

    def test_execute_error(self, use_case: ListCoresUseCase, mock_repository: Mock):
        """Test error handling."""
        # Arrange
        error = DomainError(code="LIST_FAILED", message="Failed to list cores")
        mock_repository.list_cores.return_value = Result.error(error)

        # Act
        result = use_case.execute()

        # Assert
        assert result.is_error()
        assert result.error_value.code == "LIST_FAILED"


@pytest.mark.unit
@pytest.mark.application
class TestGetCoreInfoUseCase:
    """Test GetCoreInfoUseCase."""

    @pytest.fixture
    def mock_repository(self) -> Mock:
        """Create mock repository."""
        return Mock()

    @pytest.fixture
    def use_case(self, mock_repository: Mock) -> GetCoreInfoUseCase:
        """Create use case with mock repository."""
        return GetCoreInfoUseCase(mock_repository)

    def test_execute_success(
        self, use_case: GetCoreInfoUseCase, mock_repository: Mock
    ):
        """Test successful core info retrieval."""
        # Arrange
        core = RetroArchCore(
            name="lr-mupen64plus-next",
            core_path="/opt/retropie/libretrocores/lr-mupen64plus-next/core.so",
            systems=["n64"],
            version="1.0",
            display_name="Mupen64Plus-Next",
            description="N64 emulator",
        )
        mock_repository.get_core_info.return_value = Result.success(core)

        # Act
        result = use_case.execute("lr-mupen64plus-next")

        # Assert
        assert result.is_success()
        assert result.success_value.name == "lr-mupen64plus-next"
        assert result.success_value.version == "1.0"
        mock_repository.get_core_info.assert_called_once_with("lr-mupen64plus-next")

    def test_execute_empty_core_name(self, use_case: GetCoreInfoUseCase):
        """Test validation of empty core name."""
        # Act
        result = use_case.execute("")

        # Assert
        assert result.is_error()
        assert isinstance(result.error_value, ValidationError)
        assert result.error_value.code == "INVALID_CORE_NAME"

    def test_execute_whitespace_core_name(self, use_case: GetCoreInfoUseCase):
        """Test validation of whitespace core name."""
        # Act
        result = use_case.execute("   ")

        # Assert
        assert result.is_error()
        assert isinstance(result.error_value, ValidationError)

    def test_execute_strips_whitespace(
        self, use_case: GetCoreInfoUseCase, mock_repository: Mock
    ):
        """Test that core name is stripped."""
        # Arrange
        core = RetroArchCore(
            name="lr-snes9x",
            core_path="/opt/retropie/libretrocores/lr-snes9x/snes9x_libretro.so",
            systems=["snes"],
            display_name="Snes9x",
        )
        mock_repository.get_core_info.return_value = Result.success(core)

        # Act
        result = use_case.execute("  lr-snes9x  ")

        # Assert
        assert result.is_success()
        mock_repository.get_core_info.assert_called_once_with("lr-snes9x")


@pytest.mark.unit
@pytest.mark.application
class TestListCoreOptionsUseCase:
    """Test ListCoreOptionsUseCase."""

    @pytest.fixture
    def mock_repository(self) -> Mock:
        """Create mock repository."""
        return Mock()

    @pytest.fixture
    def use_case(self, mock_repository: Mock) -> ListCoreOptionsUseCase:
        """Create use case with mock repository."""
        return ListCoreOptionsUseCase(mock_repository)

    def test_execute_success(
        self, use_case: ListCoreOptionsUseCase, mock_repository: Mock
    ):
        """Test successful core options listing."""
        # Arrange
        options = [
            CoreOption(
                key="mupen64plus-next-cpucore",
                value="dynamic_recompiler",
                core_name="lr-mupen64plus-next",
            ),
            CoreOption(
                key="mupen64plus-next-aspect",
                value="4:3",
                core_name="lr-mupen64plus-next",
            ),
        ]
        mock_repository.get_core_options.return_value = Result.success(options)

        # Act
        result = use_case.execute("lr-mupen64plus-next")

        # Assert
        assert result.is_success()
        assert len(result.success_value) == 2
        assert result.success_value[0].key == "mupen64plus-next-cpucore"
        mock_repository.get_core_options.assert_called_once_with("lr-mupen64plus-next")

    def test_execute_empty_core_name(self, use_case: ListCoreOptionsUseCase):
        """Test validation of empty core name."""
        # Act
        result = use_case.execute("")

        # Assert
        assert result.is_error()
        assert isinstance(result.error_value, ValidationError)
        assert result.error_value.code == "INVALID_CORE_NAME"


@pytest.mark.unit
@pytest.mark.application
class TestUpdateCoreOptionUseCase:
    """Test UpdateCoreOptionUseCase."""

    @pytest.fixture
    def mock_repository(self) -> Mock:
        """Create mock repository."""
        return Mock()

    @pytest.fixture
    def use_case(self, mock_repository: Mock) -> UpdateCoreOptionUseCase:
        """Create use case with mock repository."""
        return UpdateCoreOptionUseCase(mock_repository)

    def test_execute_success(
        self, use_case: UpdateCoreOptionUseCase, mock_repository: Mock
    ):
        """Test successful core option update."""
        # Arrange
        mock_repository.update_core_option.return_value = Result.success(True)

        # Act
        result = use_case.execute(
            "lr-mupen64plus-next", "mupen64plus-next-cpucore", "pure_interpreter"
        )

        # Assert
        assert result.is_success()
        assert result.success_value is True
        mock_repository.update_core_option.assert_called_once()
        call_args = mock_repository.update_core_option.call_args
        assert call_args[0][0] == "lr-mupen64plus-next"
        assert call_args[0][1].key == "mupen64plus-next-cpucore"
        assert call_args[0][1].value == "pure_interpreter"

    def test_execute_empty_core_name(self, use_case: UpdateCoreOptionUseCase):
        """Test validation of empty core name."""
        # Act
        result = use_case.execute("", "key", "value")

        # Assert
        assert result.is_error()
        assert isinstance(result.error_value, ValidationError)
        assert result.error_value.code == "INVALID_CORE_NAME"

    def test_execute_empty_option_key(self, use_case: UpdateCoreOptionUseCase):
        """Test validation of empty option key."""
        # Act
        result = use_case.execute("lr-mupen64plus-next", "", "value")

        # Assert
        assert result.is_error()
        assert isinstance(result.error_value, ValidationError)
        assert result.error_value.code == "INVALID_OPTION_KEY"

    def test_execute_strips_whitespace(
        self, use_case: UpdateCoreOptionUseCase, mock_repository: Mock
    ):
        """Test that inputs are stripped."""
        # Arrange
        mock_repository.update_core_option.return_value = Result.success(True)

        # Act
        result = use_case.execute("  lr-snes9x  ", "  option-key  ", "value")

        # Assert
        assert result.is_success()
        call_args = mock_repository.update_core_option.call_args
        assert call_args[0][0] == "lr-snes9x"
        assert call_args[0][1].key == "option-key"


@pytest.mark.unit
@pytest.mark.application
class TestGetEmulatorMappingsUseCase:
    """Test GetEmulatorMappingsUseCase."""

    @pytest.fixture
    def mock_repository(self) -> Mock:
        """Create mock repository."""
        return Mock()

    @pytest.fixture
    def use_case(self, mock_repository: Mock) -> GetEmulatorMappingsUseCase:
        """Create use case with mock repository."""
        return GetEmulatorMappingsUseCase(mock_repository)

    def test_execute_success(
        self, use_case: GetEmulatorMappingsUseCase, mock_repository: Mock
    ):
        """Test successful emulator mappings retrieval."""
        # Arrange
        mappings = [
            EmulatorMapping(
                system="n64",
                emulator_name="mupen64plus-GLideN64",
                command="/opt/retropie/emulators/mupen64plus/bin/mupen64plus.sh",
                is_default=False,
            ),
            EmulatorMapping(
                system="n64",
                emulator_name="lr-mupen64plus-next",
                command="/opt/retropie/emulators/retroarch/bin/retroarch -L ...",
                is_default=True,
                core_path="/opt/retropie/libretrocores/lr-mupen64plus-next/core.so",
            ),
        ]
        mock_repository.get_emulator_mappings.return_value = Result.success(mappings)

        # Act
        result = use_case.execute("n64")

        # Assert
        assert result.is_success()
        assert len(result.success_value) == 2
        assert result.success_value[1].is_default is True
        mock_repository.get_emulator_mappings.assert_called_once_with("n64")

    def test_execute_empty_system_name(self, use_case: GetEmulatorMappingsUseCase):
        """Test validation of empty system name."""
        # Act
        result = use_case.execute("")

        # Assert
        assert result.is_error()
        assert isinstance(result.error_value, ValidationError)
        assert result.error_value.code == "INVALID_SYSTEM_NAME"


@pytest.mark.unit
@pytest.mark.application
class TestSetDefaultEmulatorUseCase:
    """Test SetDefaultEmulatorUseCase."""

    @pytest.fixture
    def mock_repository(self) -> Mock:
        """Create mock repository."""
        return Mock()

    @pytest.fixture
    def use_case(self, mock_repository: Mock) -> SetDefaultEmulatorUseCase:
        """Create use case with mock repository."""
        return SetDefaultEmulatorUseCase(mock_repository)

    def test_execute_success(
        self, use_case: SetDefaultEmulatorUseCase, mock_repository: Mock
    ):
        """Test successful default emulator setting."""
        # Arrange
        mock_repository.set_default_emulator.return_value = Result.success(True)

        # Act
        result = use_case.execute("n64", "lr-mupen64plus-next")

        # Assert
        assert result.is_success()
        assert result.success_value is True
        mock_repository.set_default_emulator.assert_called_once_with(
            "n64", "lr-mupen64plus-next"
        )

    def test_execute_empty_system_name(self, use_case: SetDefaultEmulatorUseCase):
        """Test validation of empty system name."""
        # Act
        result = use_case.execute("", "lr-mupen64plus-next")

        # Assert
        assert result.is_error()
        assert isinstance(result.error_value, ValidationError)
        assert result.error_value.code == "INVALID_SYSTEM_NAME"

    def test_execute_empty_emulator_name(self, use_case: SetDefaultEmulatorUseCase):
        """Test validation of empty emulator name."""
        # Act
        result = use_case.execute("n64", "")

        # Assert
        assert result.is_error()
        assert isinstance(result.error_value, ValidationError)
        assert result.error_value.code == "INVALID_EMULATOR_NAME"

    def test_execute_strips_whitespace(
        self, use_case: SetDefaultEmulatorUseCase, mock_repository: Mock
    ):
        """Test that inputs are stripped."""
        # Arrange
        mock_repository.set_default_emulator.return_value = Result.success(True)

        # Act
        result = use_case.execute("  n64  ", "  lr-mupen64plus-next  ")

        # Assert
        assert result.is_success()
        mock_repository.set_default_emulator.assert_called_once_with(
            "n64", "lr-mupen64plus-next"
        )
