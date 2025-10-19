"""RetroArch core management use cases for RetroMCP."""

from typing import List

from ..domain.models import CoreOption
from ..domain.models import DomainError
from ..domain.models import EmulatorMapping
from ..domain.models import Result
from ..domain.models import RetroArchCore
from ..domain.models import ValidationError
from ..domain.ports import EmulatorRepository


class ListCoresUseCase:
    """Use case for listing all installed RetroArch cores."""

    def __init__(self, repository: EmulatorRepository) -> None:
        """Initialize with emulator repository.

        Args:
            repository: Emulator repository implementation.
        """
        self._repository = repository

    def execute(self) -> Result[List[RetroArchCore], DomainError]:
        """List all installed RetroArch cores.

        Returns:
            Result containing list of RetroArchCore objects or DomainError.
        """
        return self._repository.list_cores()


class GetCoreInfoUseCase:
    """Use case for getting detailed information about a specific core."""

    def __init__(self, repository: EmulatorRepository) -> None:
        """Initialize with emulator repository.

        Args:
            repository: Emulator repository implementation.
        """
        self._repository = repository

    def execute(self, core_name: str) -> Result[RetroArchCore, DomainError]:
        """Get detailed information about a specific core.

        Args:
            core_name: Name of the core (e.g., 'lr-mupen64plus-next').

        Returns:
            Result containing RetroArchCore object or DomainError.
        """
        if not core_name or not core_name.strip():
            return Result.error(
                ValidationError(
                    code="INVALID_CORE_NAME",
                    message="Core name cannot be empty",
                    details={"core_name": core_name},
                )
            )

        return self._repository.get_core_info(core_name.strip())


class ListCoreOptionsUseCase:
    """Use case for listing configurable options for a core."""

    def __init__(self, repository: EmulatorRepository) -> None:
        """Initialize with emulator repository.

        Args:
            repository: Emulator repository implementation.
        """
        self._repository = repository

    def execute(self, core_name: str) -> Result[List[CoreOption], DomainError]:
        """List configurable options for a specific core.

        Args:
            core_name: Name of the core (e.g., 'lr-mupen64plus-next').

        Returns:
            Result containing list of CoreOption objects or DomainError.
        """
        if not core_name or not core_name.strip():
            return Result.error(
                ValidationError(
                    code="INVALID_CORE_NAME",
                    message="Core name cannot be empty",
                    details={"core_name": core_name},
                )
            )

        return self._repository.get_core_options(core_name.strip())


class UpdateCoreOptionUseCase:
    """Use case for updating a core-specific configuration option."""

    def __init__(self, repository: EmulatorRepository) -> None:
        """Initialize with emulator repository.

        Args:
            repository: Emulator repository implementation.
        """
        self._repository = repository

    def execute(
        self, core_name: str, option_key: str, option_value: str
    ) -> Result[bool, DomainError]:
        """Update a core-specific configuration option.

        Args:
            core_name: Name of the core (e.g., 'lr-mupen64plus-next').
            option_key: Option key to update.
            option_value: New value for the option.

        Returns:
            Result containing success boolean or DomainError.
        """
        if not core_name or not core_name.strip():
            return Result.error(
                ValidationError(
                    code="INVALID_CORE_NAME",
                    message="Core name cannot be empty",
                    details={"core_name": core_name},
                )
            )

        if not option_key or not option_key.strip():
            return Result.error(
                ValidationError(
                    code="INVALID_OPTION_KEY",
                    message="Option key cannot be empty",
                    details={"option_key": option_key},
                )
            )

        option = CoreOption(
            key=option_key.strip(),
            value=option_value,
            core_name=core_name.strip(),
        )

        return self._repository.update_core_option(core_name.strip(), option)


class GetEmulatorMappingsUseCase:
    """Use case for getting available emulators/cores for a system."""

    def __init__(self, repository: EmulatorRepository) -> None:
        """Initialize with emulator repository.

        Args:
            repository: Emulator repository implementation.
        """
        self._repository = repository

    def execute(self, system: str) -> Result[List[EmulatorMapping], DomainError]:
        """Get available emulators/cores for a system.

        Args:
            system: System name (e.g., 'n64', 'nes').

        Returns:
            Result containing list of EmulatorMapping objects or DomainError.
        """
        if not system or not system.strip():
            return Result.error(
                ValidationError(
                    code="INVALID_SYSTEM_NAME",
                    message="System name cannot be empty",
                    details={"system": system},
                )
            )

        return self._repository.get_emulator_mappings(system.strip())


class SetDefaultEmulatorUseCase:
    """Use case for setting the default emulator/core for a system."""

    def __init__(self, repository: EmulatorRepository) -> None:
        """Initialize with emulator repository.

        Args:
            repository: Emulator repository implementation.
        """
        self._repository = repository

    def execute(self, system: str, emulator_name: str) -> Result[bool, DomainError]:
        """Set the default emulator/core for a system.

        Args:
            system: System name (e.g., 'n64', 'nes').
            emulator_name: Emulator name (e.g., 'lr-mupen64plus-next').

        Returns:
            Result containing success boolean or DomainError.
        """
        if not system or not system.strip():
            return Result.error(
                ValidationError(
                    code="INVALID_SYSTEM_NAME",
                    message="System name cannot be empty",
                    details={"system": system},
                )
            )

        if not emulator_name or not emulator_name.strip():
            return Result.error(
                ValidationError(
                    code="INVALID_EMULATOR_NAME",
                    message="Emulator name cannot be empty",
                    details={"emulator_name": emulator_name},
                )
            )

        return self._repository.set_default_emulator(
            system.strip(), emulator_name.strip()
        )
