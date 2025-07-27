"""Package management use cases for RetroMCP."""

from typing import List

from ..domain.models import CommandResult
from ..domain.models import ExecutionError
from ..domain.models import Result
from ..domain.models import ValidationError
from ..domain.ports import SystemRepository


class InstallPackagesUseCase:
    """Use case for installing system packages."""

    def __init__(self, system_repo: SystemRepository) -> None:
        """Initialize with system repository."""
        self._system_repo = system_repo

    def execute(
        self, packages: List[str]
    ) -> Result[CommandResult, ValidationError | ExecutionError]:
        """Install the specified packages."""
        if not packages:
            no_packages_result = CommandResult(
                command="",
                exit_code=0,
                stdout="No packages specified",
                stderr="",
                success=True,
                execution_time=0.0,
            )
            return Result.success(no_packages_result)

        # Validate all package names for security
        try:
            for package in packages:
                self._validate_package_name(package)
        except ValueError as e:
            return Result.error(ValidationError(str(e)))

        # Get installed packages - handle Result pattern
        installed_packages_result = self._system_repo.get_packages()
        if installed_packages_result.is_error():
            return Result.error(installed_packages_result.error_or_none)

        # Filter out already installed packages
        installed_packages = installed_packages_result.value
        installed_names = {pkg.name for pkg in installed_packages if pkg.installed}

        packages_to_install = [pkg for pkg in packages if pkg not in installed_names]

        if not packages_to_install:
            all_installed_result = CommandResult(
                command="",
                exit_code=0,
                stdout="All packages are already installed",
                stderr="",
                success=True,
                execution_time=0.0,
            )
            return Result.success(all_installed_result)

        # Install packages - handle Result pattern
        result = self._system_repo.install_packages(packages_to_install)

        # If installation failed, try to enhance error details
        if result.is_error():
            error = result.error_value
            # If we have stderr information, parse it for better details
            if hasattr(error, "stderr") and error.stderr:
                # Try to identify which specific packages failed
                stderr_lines = error.stderr.split("\n")
                failed_packages = []

                for line in stderr_lines:
                    if "Unable to locate package" in line:
                        # Extract package name
                        parts = line.split("Unable to locate package")
                        if len(parts) > 1:
                            pkg_name = parts[1].strip()
                            if pkg_name in packages_to_install:
                                failed_packages.append(pkg_name)

                # If we found specific failures, enhance the error
                if failed_packages:
                    # Update error details
                    if not hasattr(error, "details") or error.details is None:
                        error.details = {}

                    error.details["failed_packages"] = failed_packages
                    if len(failed_packages) < len(packages_to_install):
                        # Some succeeded
                        succeeded = [
                            p for p in packages_to_install if p not in failed_packages
                        ]
                        error.details["succeeded"] = succeeded
                        error.details["failed"] = failed_packages
                        error.details["total"] = len(packages_to_install)

        return result

    def _validate_package_name(self, package_name: str) -> None:
        """Validate package name for security."""
        # Prevent empty or overly long names
        if not package_name or len(package_name) > 100:
            raise ValueError(
                f"Package name must be between 1 and 100 characters: {package_name}"
            )

        # Prevent system command injection - check dangerous chars first
        dangerous_chars = [
            ";",
            "&",
            "|",
            "$",
            "`",
            "(",
            ")",
            "{",
            "}",
            "[",
            "]",
            "<",
            ">",
            "\\",
            "/",
        ]
        for char in dangerous_chars:
            if char in package_name:
                raise ValueError(
                    f"Package name contains dangerous character '{char}': {package_name}"
                )

        # Only allow alphanumeric characters, hyphens, and underscores
        if not package_name.replace("-", "").replace("_", "").isalnum():
            raise ValueError(f"Invalid package name: {package_name}")
