"""Unit tests for ListRomsUseCase - RED phase tests that should FAIL initially.

Following CLAUDE.md TDD: Write tests FIRST that expose the missing ListRomsUseCase.
"""

from unittest.mock import Mock

import pytest

from retromcp.application.use_cases import ListRomsUseCase
from retromcp.domain.models import RomDirectory
from retromcp.domain.ports import EmulatorRepository


class TestListRomsUseCase:
    """Test ListRomsUseCase business logic."""

    @pytest.fixture
    def mock_emulator_repository(self) -> Mock:
        """Mock emulator repository for testing."""
        return Mock(spec=EmulatorRepository)

    @pytest.fixture
    def use_case(self, mock_emulator_repository: Mock) -> ListRomsUseCase:
        """Create ListRomsUseCase with mocked dependencies."""
        return ListRomsUseCase(mock_emulator_repository)

    def test_list_roms_returns_rom_directories(
        self, use_case: ListRomsUseCase, mock_emulator_repository: Mock
    ) -> None:
        """TEST SHOULD FAIL: ListRomsUseCase should return list of ROM directories."""
        # Arrange
        expected_roms = [
            RomDirectory(
                system="nes",
                path="/home/pi/RetroPie/roms/nes",
                rom_count=10,
                total_size=1024000,
                supported_extensions=[".nes", ".zip"],
            ),
            RomDirectory(
                system="snes",
                path="/home/pi/RetroPie/roms/snes",
                rom_count=5,
                total_size=2048000,
                supported_extensions=[".sfc", ".smc", ".zip"],
            ),
        ]
        mock_emulator_repository.get_rom_directories.return_value = expected_roms

        # Act
        result = use_case.execute()

        # Assert
        assert result == expected_roms
        mock_emulator_repository.get_rom_directories.assert_called_once()

    def test_list_roms_handles_empty_directories(
        self, use_case: ListRomsUseCase, mock_emulator_repository: Mock
    ) -> None:
        """TEST SHOULD FAIL: ListRomsUseCase should handle empty ROM directories."""
        # Arrange
        mock_emulator_repository.get_rom_directories.return_value = []

        # Act
        result = use_case.execute()

        # Assert
        assert result == []
        mock_emulator_repository.get_rom_directories.assert_called_once()

    def test_list_roms_filters_by_system_when_specified(
        self, use_case: ListRomsUseCase, mock_emulator_repository: Mock
    ) -> None:
        """TEST SHOULD FAIL: ListRomsUseCase should filter by system when specified."""
        # Arrange
        all_roms = [
            RomDirectory(
                system="nes",
                path="/home/pi/RetroPie/roms/nes",
                rom_count=10,
                total_size=1024000,
                supported_extensions=[".nes", ".zip"],
            ),
            RomDirectory(
                system="snes",
                path="/home/pi/RetroPie/roms/snes",
                rom_count=5,
                total_size=2048000,
                supported_extensions=[".sfc", ".smc", ".zip"],
            ),
        ]
        mock_emulator_repository.get_rom_directories.return_value = all_roms

        # Act
        result = use_case.execute(system_filter="nes")

        # Assert
        expected_filtered = [rom for rom in all_roms if rom.system == "nes"]
        assert result == expected_filtered
        mock_emulator_repository.get_rom_directories.assert_called_once()

    def test_list_roms_filters_by_minimum_count(
        self, use_case: ListRomsUseCase, mock_emulator_repository: Mock
    ) -> None:
        """TEST SHOULD FAIL: ListRomsUseCase should filter by minimum ROM count."""
        # Arrange
        all_roms = [
            RomDirectory(
                system="nes",
                path="/path/nes",
                rom_count=10,
                total_size=1000,
                supported_extensions=[],
            ),
            RomDirectory(
                system="empty",
                path="/path/empty",
                rom_count=0,
                total_size=0,
                supported_extensions=[],
            ),
            RomDirectory(
                system="few",
                path="/path/few",
                rom_count=2,
                total_size=500,
                supported_extensions=[],
            ),
        ]
        mock_emulator_repository.get_rom_directories.return_value = all_roms

        # Act
        result = use_case.execute(min_rom_count=5)

        # Assert
        expected_filtered = [rom for rom in all_roms if rom.rom_count >= 5]
        assert result == expected_filtered
        mock_emulator_repository.get_rom_directories.assert_called_once()

    def test_list_roms_sorts_by_rom_count_descending(
        self, use_case: ListRomsUseCase, mock_emulator_repository: Mock
    ) -> None:
        """TEST SHOULD FAIL: ListRomsUseCase should sort by ROM count descending by default."""
        # Arrange
        unsorted_roms = [
            RomDirectory(
                system="few",
                path="/path/few",
                rom_count=2,
                total_size=500,
                supported_extensions=[],
            ),
            RomDirectory(
                system="many",
                path="/path/many",
                rom_count=20,
                total_size=5000,
                supported_extensions=[],
            ),
            RomDirectory(
                system="medium",
                path="/path/medium",
                rom_count=10,
                total_size=2000,
                supported_extensions=[],
            ),
        ]
        mock_emulator_repository.get_rom_directories.return_value = unsorted_roms

        # Act
        result = use_case.execute()

        # Assert
        expected_sorted = sorted(unsorted_roms, key=lambda r: r.rom_count, reverse=True)
        assert result == expected_sorted
        mock_emulator_repository.get_rom_directories.assert_called_once()
