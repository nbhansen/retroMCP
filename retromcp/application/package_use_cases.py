"""Package management use cases for RetroMCP."""

from typing import List

from ..domain.models import CommandResult
from ..domain.ports import SystemRepository


class InstallPackagesUseCase:
    """Use case for installing system packages."""

    def __init__(self, system_repo: SystemRepository) -> None:
        """Initialize with system repository."""
        self._system_repo = system_repo

    def execute(self, packages: List[str]) -> CommandResult:
        """Install the specified packages."""
        if not packages:
            return CommandResult(
                command="",
                exit_code=0,
                stdout="No packages specified",
                stderr="",
                success=True,
                execution_time=0.0,
            )

        # Filter out already installed packages
        installed_packages = self._system_repo.get_packages()
        installed_names = {pkg.name for pkg in installed_packages if pkg.installed}

        packages_to_install = [pkg for pkg in packages if pkg not in installed_names]

        if not packages_to_install:
            return CommandResult(
                command="",
                exit_code=0,
                stdout="All packages are already installed",
                stderr="",
                success=True,
                execution_time=0.0,
            )

        return self._system_repo.install_packages(packages_to_install)

    def _validate_package_name(self, package_name: str) -> None:
        """Validate package name for security."""
        # Only allow alphanumeric characters, hyphens, and underscores
        if not package_name.replace("-", "").replace("_", "").isalnum():
            raise ValueError(f"Invalid package name: {package_name}")
        
        # Prevent empty or overly long names
        if not package_name or len(package_name) > 100:
            raise ValueError(f"Package name must be between 1 and 100 characters: {package_name}")
        
        # Prevent system command injection
        dangerous_chars = [";", "&", "|", "$", "`", "(", ")", "{", "}", "[", "]", "<", ">", "\\", "/"]
        for char in dangerous_chars:
            if char in package_name:
                raise ValueError(f"Package name contains dangerous character '{char}': {package_name}")