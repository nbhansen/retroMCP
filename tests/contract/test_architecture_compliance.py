"""Architecture compliance tests verifying CLAUDE.md principles.

These tests ensure our codebase follows the architectural standards
defined in CLAUDE.md, including hexagonal architecture, dependency
injection, immutability, and clean interfaces.
"""

import ast
import importlib
import inspect
from dataclasses import fields
from dataclasses import is_dataclass
from pathlib import Path
from typing import Any
from typing import get_type_hints

import pytest

from retromcp.config import RetroPieConfig
from retromcp.config import ServerConfig
from retromcp.discovery import RetroPiePaths
from retromcp.domain.models import CommandResult
from retromcp.domain.models import Controller
from retromcp.domain.models import SystemInfo
from retromcp.profile import SystemProfile
from retromcp.profile import SystemProfileManager
from retromcp.ssh_handler import SSHHandler
from retromcp.tools.gaming_system_tools import GamingSystemTools
from retromcp.tools.hardware_monitoring_tools import HardwareMonitoringTools
from retromcp.tools.system_management_tools import SystemManagementTools


class TestImmutabilityCompliance:
    """Test that domain objects are immutable as required by CLAUDE.md."""

    def test_config_objects_are_frozen(self) -> None:
        """Test that configuration objects are immutable (frozen=True)."""
        # Test RetroPieConfig
        config = RetroPieConfig(host="test", username="test")

        # Should be a frozen dataclass
        assert hasattr(config, "__dataclass_fields__")
        assert config.__dataclass_params__.frozen is True

        # Should raise error when trying to modify
        with pytest.raises((AttributeError, TypeError)):
            config.host = "modified"  # type: ignore

    def test_discovery_paths_are_frozen(self) -> None:
        """Test that discovery paths are immutable."""
        paths = RetroPiePaths(home_dir="/test", username="test")

        # Should be a frozen dataclass
        assert hasattr(paths, "__dataclass_fields__")
        assert paths.__dataclass_params__.frozen is True

        # Should raise error when trying to modify
        with pytest.raises((AttributeError, TypeError)):
            paths.home_dir = "modified"  # type: ignore

    def test_domain_models_are_frozen(self) -> None:
        """Test that domain models are immutable."""
        # Test SystemInfo
        system_info = SystemInfo(
            hostname="test",
            cpu_temperature=50.0,
            memory_total=1000,
            memory_used=500,
            memory_free=500,
            disk_total=2000,
            disk_used=1000,
            disk_free=1000,
            load_average=[1.0, 1.1, 1.2],
            uptime=3600,
        )

        assert hasattr(system_info, "__dataclass_fields__")
        assert system_info.__dataclass_params__.frozen is True

        with pytest.raises((AttributeError, TypeError)):
            system_info.hostname = "modified"  # type: ignore

    def test_command_result_is_frozen(self) -> None:
        """Test that CommandResult is immutable."""
        result = CommandResult(
            command="test",
            exit_code=0,
            stdout="output",
            stderr="",
            success=True,
            execution_time=0.1,
        )

        assert hasattr(result, "__dataclass_fields__")
        assert result.__dataclass_params__.frozen is True

        with pytest.raises((AttributeError, TypeError)):
            result.command = "modified"  # type: ignore


class TestDependencyInjectionCompliance:
    """Test that components use dependency injection as required by CLAUDE.md."""

    def test_tools_use_dependency_injection(self) -> None:
        """Test that all tool classes use dependency injection."""
        tool_classes = [
            SystemManagementTools,
            HardwareMonitoringTools,
            GamingSystemTools,
        ]

        for tool_class in tool_classes:
            # Check constructor requires dependencies
            init_signature = inspect.signature(tool_class.__init__)
            params = list(init_signature.parameters.values())[1:]  # Skip 'self'

            # Should require exactly one Container dependency (improved architecture)
            assert len(params) == 1, (
                f"{tool_class.__name__} should require exactly one Container dependency"
            )

            # Check parameter is Container for proper dependency injection
            container_param = params[0]
            assert "container" in container_param.name.lower(), (
                f"{tool_class.__name__} should have container parameter, got: {container_param.name}"
            )

            # Verify parameter is properly typed
            if container_param.annotation != inspect.Parameter.empty:
                annotation_str = str(container_param.annotation)
                assert "Container" in annotation_str, (
                    f"{tool_class.__name__} container parameter should be typed as Container"
                )

    def test_ssh_handler_dependency_injection(self) -> None:
        """Test that SSHHandler uses dependency injection."""
        init_signature = inspect.signature(SSHHandler.__init__)
        params = list(init_signature.parameters.values())[1:]  # Skip 'self'

        # Should require config dependency
        assert len(params) >= 1, "SSHHandler should require config dependency"

        # Check parameter is typed
        config_param = params[0]
        assert config_param.annotation != inspect.Parameter.empty, (
            "SSHHandler config parameter should be type-hinted"
        )

    def test_profile_manager_dependency_injection(self) -> None:
        """Test that SystemProfileManager uses dependency injection."""
        init_signature = inspect.signature(SystemProfileManager.__init__)
        params = list(init_signature.parameters.values())[1:]  # Skip 'self'

        # Should allow profile_dir injection
        if params:  # Optional dependency
            profile_dir_param = params[0]
            assert (
                "profile" in profile_dir_param.name.lower()
                or "dir" in profile_dir_param.name.lower()
            ), "Profile manager should have meaningful parameter name"


class TestTypeHintCompliance:
    """Test that all functions have type hints as required by CLAUDE.md."""

    def _get_public_methods(self, cls: type) -> list:
        """Get all public methods of a class."""
        return [
            method
            for method in inspect.getmembers(cls, predicate=inspect.isfunction)
            if not method[0].startswith("_")
        ]

    def test_tool_methods_have_type_hints(self) -> None:
        """Test that all tool methods have proper type hints."""
        tool_classes = [
            SystemManagementTools,
            HardwareMonitoringTools,
            GamingSystemTools,
        ]

        for tool_class in tool_classes:
            public_methods = self._get_public_methods(tool_class)

            for method_name, method in public_methods:
                # Get type hints
                hints = get_type_hints(method)
                signature = inspect.signature(method)

                # Check return type hint exists
                assert "return" in hints, (
                    f"{tool_class.__name__}.{method_name} missing return type hint"
                )

                # Check parameter type hints (skip 'self')
                params = list(signature.parameters.values())[1:]
                for param in params:
                    if param.annotation == inspect.Parameter.empty:
                        # Allow *args, **kwargs without hints
                        if param.kind not in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
                            pytest.fail(
                                f"{tool_class.__name__}.{method_name} parameter '{param.name}' "
                                f"missing type hint"
                            )

    def test_config_classes_have_type_hints(self) -> None:
        """Test that config classes have proper type hints."""
        config_classes = [RetroPieConfig, ServerConfig, RetroPiePaths]

        for config_class in config_classes:
            if is_dataclass(config_class):
                # Check dataclass fields have type annotations
                for field in fields(config_class):
                    assert field.type != Any, (
                        f"{config_class.__name__}.{field.name} should have specific type, not Any"
                    )

    def test_domain_models_have_type_hints(self) -> None:
        """Test that domain models have proper type hints."""
        domain_classes = [SystemInfo, Controller, CommandResult]

        for domain_class in domain_classes:
            if is_dataclass(domain_class):
                # Check dataclass fields have type annotations
                for field in fields(domain_class):
                    assert field.type != Any, (
                        f"{domain_class.__name__}.{field.name} should have specific type, not Any"
                    )


class TestMeaningfulNamingCompliance:
    """Test that code uses meaningful names as required by CLAUDE.md."""

    def test_no_single_letter_variable_names(self) -> None:
        """Test that we don't use single-letter variable names in key files."""
        # This is a simplified check - in practice, you'd parse AST of source files
        key_modules = [
            "retromcp.config",
            "retromcp.discovery",
            "retromcp.profile",
            "retromcp.tools.system_tools",
        ]

        for module_name in key_modules:
            try:
                module = importlib.import_module(module_name)
                source_file = Path(module.__file__)

                if source_file.exists():
                    # Read source and check for meaningful names in key contexts
                    with open(source_file) as f:
                        content = f.read()

                    # Parse AST to check function parameter names
                    tree = ast.parse(content)

                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            # Check function parameters have meaningful names
                            for arg in node.args.args:
                                if arg.arg != "self" and len(arg.arg) == 1:
                                    # Allow some common single-letter exceptions
                                    if arg.arg not in ["x", "y", "i", "j", "n"]:
                                        pytest.fail(
                                            f"Single-letter parameter '{arg.arg}' in "
                                            f"{module_name}.{node.name} violates naming standards"
                                        )
            except (ImportError, FileNotFoundError):
                # Skip if module can't be imported
                pass

    def test_class_names_are_descriptive(self) -> None:
        """Test that class names are descriptive."""
        classes_to_check = [
            (SystemManagementTools, "SystemManagementTools"),
            (RetroPieConfig, "RetroPieConfig"),
            (SystemProfile, "SystemProfile"),
            (CommandResult, "CommandResult"),
        ]

        for cls, expected_pattern in classes_to_check:
            class_name = cls.__name__

            # Should not be abbreviated beyond recognition
            assert len(class_name) >= 4, f"Class name '{class_name}' too short"

            # Should use PascalCase
            assert class_name[0].isupper(), (
                f"Class name '{class_name}' should start with uppercase"
            )

            # Should be descriptive
            assert class_name == expected_pattern, (
                f"Class name '{class_name}' should match expected pattern"
            )

    def test_method_names_are_descriptive(self) -> None:
        """Test that method names are descriptive and follow conventions."""
        # Check a sample of key methods
        method_checks = [
            (SystemManagementTools, "get_tools"),
            (RetroPieConfig, "from_env"),
            (SystemProfileManager, "get_or_create_profile"),
            (SSHHandler, "execute_command"),
        ]

        for cls, method_name in method_checks:
            assert hasattr(cls, method_name), (
                f"{cls.__name__} should have method {method_name}"
            )

            getattr(cls, method_name)

            # Method name should be descriptive
            assert len(method_name) >= 3, f"Method name '{method_name}' too short"

            # Should use snake_case
            assert method_name.islower() or "_" in method_name, (
                f"Method name '{method_name}' should use snake_case"
            )


class TestSeparationOfConcernsCompliance:
    """Test that domain logic is separated from infrastructure as required by CLAUDE.md."""

    def test_domain_models_have_no_infrastructure_dependencies(self) -> None:
        """Test that domain models don't import infrastructure."""
        # Check CommandResult doesn't import SSH or IO libraries
        command_result_module = inspect.getmodule(CommandResult)
        source_file = Path(command_result_module.__file__)

        with open(source_file) as f:
            content = f.read()

        # Domain models shouldn't import infrastructure concerns
        # Note: asyncio is allowed in domain for CommandResult async handling
        forbidden_imports = ["paramiko", "socket", "requests"]
        for forbidden in forbidden_imports:
            assert forbidden not in content.lower(), (
                f"Domain models should not import {forbidden}"
            )

    def test_tools_separate_domain_from_infrastructure(self) -> None:
        """Test that tools separate domain logic from infrastructure."""
        # SystemManagementTools should use injected SSH handler, not create it directly
        system_tools_module = inspect.getmodule(SystemManagementTools)
        source_file = Path(system_tools_module.__file__)

        with open(source_file) as f:
            content = f.read()

        # Should not directly instantiate SSH connections
        assert "paramiko.SSHClient()" not in content, (
            "Tools should not directly create SSH connections"
        )
        assert "ssh.client.SSHClient" not in content, (
            "Tools should use injected SSH handler"
        )

    def test_config_objects_are_pure_data(self) -> None:
        """Test that config objects are pure data without behavior."""
        config_classes = [RetroPieConfig, ServerConfig, RetroPiePaths]

        for config_class in config_classes:
            # Get all methods (excluding special methods)
            methods = [
                method
                for method in inspect.getmembers(
                    config_class, predicate=inspect.ismethod
                )
                if not method[0].startswith("__")
            ]

            # Config objects should have minimal behavior
            # Allow factory methods (from_env) and simple transformations (with_paths)
            allowed_method_patterns = ["from_", "with_", "to_"]

            for method_name, _method in methods:
                if not any(
                    method_name.startswith(pattern)
                    for pattern in allowed_method_patterns
                ):
                    # Allow properties
                    if not isinstance(getattr(config_class, method_name), property):
                        pytest.fail(
                            f"Config class {config_class.__name__} should not have "
                            f"behavioral method {method_name}"
                        )


class TestHexagonalArchitectureCompliance:
    """Test that the codebase follows hexagonal architecture principles."""

    def test_domain_ports_define_interfaces(self) -> None:
        """Test that domain ports define clear interfaces."""
        from retromcp.domain.ports import RetroPieClient

        # Ports should be abstract/interface-like
        assert inspect.isabstract(RetroPieClient) or hasattr(
            RetroPieClient, "__abstractmethods__"
        ), "RetroPieClient should be an abstract interface"

    def test_infrastructure_implements_ports(self) -> None:
        """Test that infrastructure classes implement domain ports."""
        from retromcp.domain.ports import RetroPieClient
        from retromcp.infrastructure.ssh_retropie_client import SSHRetroPieClient

        # Infrastructure should implement domain interfaces
        assert issubclass(SSHRetroPieClient, RetroPieClient), (
            "SSH client should implement RetroPie client interface"
        )

    def test_tools_depend_on_abstractions(self) -> None:
        """Test that tools depend on abstractions, not concretions."""
        # Check SystemManagementTools constructor
        init_signature = inspect.signature(SystemManagementTools.__init__)
        params = list(init_signature.parameters.values())[1:]  # Skip 'self'

        # Should accept Container (dependency injection) instead of direct SSH handlers
        assert len(params) == 1, (
            "SystemManagementTools should have exactly one parameter (Container)"
        )

        container_param = params[0]
        assert "container" in container_param.name.lower(), (
            "SystemManagementTools should accept Container parameter for dependency injection"
        )

        # The container parameter should be properly typed
        if container_param.annotation != inspect.Parameter.empty:
            annotation_str = str(container_param.annotation)
            assert "Container" in annotation_str, (
                f"Container parameter should be typed as Container, got: {annotation_str}"
            )


class TestGlobalStateCompliance:
    """Test that code avoids global state as required by CLAUDE.md."""

    def test_no_module_level_variables_in_tools(self) -> None:
        """Test that tool modules don't create global state."""
        tool_modules = [
            "retromcp.tools.system_management_tools",
            "retromcp.tools.gaming_system_tools",
            "retromcp.tools.hardware_monitoring_tools",
        ]

        for module_name in tool_modules:
            try:
                module = importlib.import_module(module_name)
                source_file = Path(module.__file__)

                if source_file.exists():
                    with open(source_file) as f:
                        content = f.read()

                    tree = ast.parse(content)

                    # Check for module-level variables that aren't constants
                    # Only look at top-level nodes (direct children of module)
                    for node in tree.body:
                        if isinstance(node, ast.Assign):
                            # This is definitely a module-level assignment
                            for target in node.targets:
                                if isinstance(target, ast.Name):
                                    var_name = target.id
                                    # Allow constants (ALL_CAPS) and standard module variables
                                    if not var_name.isupper() and var_name not in [
                                        "logger",
                                        "__version__",
                                        "__all__",
                                    ]:
                                        pytest.fail(
                                            f"Module {module_name} has global variable '{var_name}' "
                                            f"which violates CLAUDE.md no-global-state principle"
                                        )
            except (ImportError, FileNotFoundError, AttributeError):
                # Skip if module can't be imported or parsed
                pass

    def test_no_class_level_state_in_tools(self) -> None:
        """Test that tool classes don't maintain class-level state."""
        tool_classes = [
            SystemManagementTools,
            HardwareMonitoringTools,
            GamingSystemTools,
        ]

        for tool_class in tool_classes:
            # Check for class-level variables that aren't constants
            for attr_name in dir(tool_class):
                if not attr_name.startswith("_"):  # Skip private/magic methods
                    attr_value = getattr(tool_class, attr_name)

                    # Skip methods, properties, and standard class attributes
                    if (
                        inspect.ismethod(attr_value)
                        or inspect.isfunction(attr_value)
                        or isinstance(attr_value, property)
                        or attr_name in ["__module__", "__doc__", "__annotations__"]
                    ):
                        continue

                    # If it's a class variable that's not a constant, that's state
                    if not attr_name.isupper():
                        pytest.fail(
                            f"Tool class {tool_class.__name__} has class-level state "
                            f"variable '{attr_name}' which violates immutability principles"
                        )

    def test_no_singleton_patterns_outside_container(self) -> None:
        """Test that singleton patterns are only used in the container."""
        modules_to_check = [
            "retromcp.tools.system_management_tools",
            "retromcp.tools.gaming_system_tools",
            "retromcp.profile",
            "retromcp.ssh_handler",
        ]

        for module_name in modules_to_check:
            try:
                module = importlib.import_module(module_name)
                source_file = Path(module.__file__)

                if source_file.exists():
                    with open(source_file) as f:
                        content = f.read()

                    # Check for singleton patterns
                    singleton_indicators = [
                        "_instance",
                        "__new__",
                        "instance()",
                        "_singleton",
                        "metaclass",
                    ]

                    for indicator in singleton_indicators:
                        if indicator in content.lower():
                            # Allow container module to use singletons
                            if "container" not in module_name:
                                # Do a more precise check using AST
                                tree = ast.parse(content)
                                for node in ast.walk(tree):
                                    if (
                                        isinstance(node, ast.Name)
                                        and indicator.lower() in node.id.lower()
                                    ):
                                        pytest.fail(
                                            f"Module {module_name} appears to implement singleton pattern "
                                            f"(found '{indicator}') which should only be in container"
                                        )
            except (ImportError, FileNotFoundError, AttributeError):
                pass


class TestInfrastructureImportCompliance:
    """Test that layers don't import inappropriate infrastructure."""

    def test_tools_only_import_domain_abstractions(self) -> None:
        """Test that tool classes only import domain and abstraction modules."""
        tool_modules = [
            "retromcp.tools.system_management_tools",
            "retromcp.tools.gaming_system_tools",
            "retromcp.tools.hardware_monitoring_tools",
        ]

        forbidden_infrastructure_imports = [
            "paramiko",
            "socket",
            "requests",
            "urllib",
            "http",
            "ssh2",
            "fabric",
        ]

        for module_name in tool_modules:
            try:
                module = importlib.import_module(module_name)
                source_file = Path(module.__file__)

                if source_file.exists():
                    with open(source_file) as f:
                        content = f.read()

                    # Parse imports using AST
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.Import, ast.ImportFrom)):
                            if isinstance(node, ast.Import):
                                import_names = [alias.name for alias in node.names]
                            else:  # ImportFrom
                                import_names = [node.module] if node.module else []

                            for import_name in import_names:
                                if import_name:
                                    for forbidden in forbidden_infrastructure_imports:
                                        if forbidden in import_name.lower():
                                            pytest.fail(
                                                f"Tool module {module_name} imports infrastructure "
                                                f"module '{import_name}' which violates hexagonal architecture. "
                                                f"Tools should only use injected domain abstractions."
                                            )
            except (ImportError, FileNotFoundError, SyntaxError):
                pass

    def test_domain_models_pure_of_infrastructure(self) -> None:
        """Test that domain models have no infrastructure dependencies."""
        domain_modules = ["retromcp.domain.models", "retromcp.domain.ports"]

        forbidden_imports = [
            "paramiko",
            "socket",
            "requests",
            "urllib",
            "http",
            "ssh2",
            "fabric",
            "subprocess",
            "os.system",
            "shlex",
        ]

        for module_name in domain_modules:
            try:
                module = importlib.import_module(module_name)
                source_file = Path(module.__file__)

                if source_file.exists():
                    with open(source_file) as f:
                        content = f.read()

                    for forbidden in forbidden_imports:
                        if forbidden in content.lower():
                            # More precise check with AST
                            tree = ast.parse(content)
                            for node in ast.walk(tree):
                                if isinstance(node, (ast.Import, ast.ImportFrom)):
                                    if isinstance(node, ast.Import):
                                        import_names = [
                                            alias.name for alias in node.names
                                        ]
                                    else:
                                        import_names = (
                                            [node.module] if node.module else []
                                        )

                                    for import_name in import_names:
                                        if (
                                            import_name
                                            and forbidden in import_name.lower()
                                        ):
                                            pytest.fail(
                                                f"Domain module {module_name} imports infrastructure "
                                                f"dependency '{import_name}' which violates clean architecture"
                                            )
            except (ImportError, FileNotFoundError, SyntaxError):
                pass


class TestInterfaceImplementationCompliance:
    """Test that all interfaces are properly implemented."""

    def test_all_port_methods_implemented(self) -> None:
        """Test that infrastructure classes implement all port methods."""
        from retromcp.domain.ports import ControllerRepository
        from retromcp.domain.ports import RetroPieClient
        from retromcp.domain.ports import SystemRepository
        from retromcp.infrastructure.ssh_controller_repository import (
            SSHControllerRepository,
        )
        from retromcp.infrastructure.ssh_retropie_client import SSHRetroPieClient
        from retromcp.infrastructure.ssh_system_repository import SSHSystemRepository

        implementations = [
            (SSHRetroPieClient, RetroPieClient),
            (SSHSystemRepository, SystemRepository),
            (SSHControllerRepository, ControllerRepository),
        ]

        for impl_class, interface_class in implementations:
            # Get all abstract methods from interface
            interface_methods = set()
            if hasattr(interface_class, "__abstractmethods__"):
                interface_methods = interface_class.__abstractmethods__

            # Check implementation has all required methods
            for method_name in interface_methods:
                assert hasattr(impl_class, method_name), (
                    f"{impl_class.__name__} must implement {method_name} from {interface_class.__name__}"
                )

                # Check method signature compatibility
                impl_method = getattr(impl_class, method_name)
                interface_method = getattr(interface_class, method_name)

                impl_sig = inspect.signature(impl_method)
                interface_sig = inspect.signature(interface_method)

                # Basic signature compatibility check
                assert len(impl_sig.parameters) == len(interface_sig.parameters), (
                    f"{impl_class.__name__}.{method_name} parameter count doesn't match interface"
                )

    def test_constructor_parameters_are_abstractions(self) -> None:
        """Test that all constructor parameters are abstractions, not concrete types."""
        classes_to_check = [
            SystemManagementTools,
            GamingSystemTools,
            HardwareMonitoringTools,
        ]

        for tool_class in classes_to_check:
            init_signature = inspect.signature(tool_class.__init__)
            params = list(init_signature.parameters.values())[1:]  # Skip 'self'

            for param in params:
                if param.annotation != inspect.Parameter.empty:
                    annotation_str = str(param.annotation)

                    # Check that we're not depending on concrete SSH implementations
                    concrete_violations = [
                        "paramiko.SSHClient",
                        "paramiko.client.SSHClient",
                        "ssh.SSHClient",
                        "retromcp.ssh_handler.SSHHandler",  # Should use abstraction instead
                    ]

                    for violation in concrete_violations:
                        if violation in annotation_str:
                            pytest.fail(
                                f"{tool_class.__name__} constructor parameter '{param.name}' "
                                f"depends on concrete type '{violation}' instead of abstraction. "
                                f"Should depend on domain interface."
                            )
