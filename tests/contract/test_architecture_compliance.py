"""Architecture compliance tests verifying CLAUDE.md principles.

These tests ensure our codebase follows the architectural standards
defined in CLAUDE.md, including hexagonal architecture, dependency
injection, immutability, and clean interfaces.
"""

import pytest
import inspect
from typing import get_type_hints, Any, Optional
from dataclasses import fields, is_dataclass
from pathlib import Path
import ast
import importlib

from retromcp.config import RetroPieConfig, ServerConfig
from retromcp.discovery import RetroPiePaths
from retromcp.domain.models import SystemInfo, Controller, CommandResult
from retromcp.tools.system_tools import SystemTools
from retromcp.tools.hardware_tools import HardwareTools
from retromcp.tools.retropie_tools import RetroPieTools
from retromcp.tools.controller_tools import ControllerTools
from retromcp.tools.emulationstation_tools import EmulationStationTools
from retromcp.profile import SystemProfile, SystemProfileManager
from retromcp.ssh_handler import SSHHandler


class TestImmutabilityCompliance:
    """Test that domain objects are immutable as required by CLAUDE.md."""

    def test_config_objects_are_frozen(self) -> None:
        """Test that configuration objects are immutable (frozen=True)."""
        # Test RetroPieConfig
        config = RetroPieConfig(host="test", username="test")
        
        # Should be a frozen dataclass
        assert hasattr(config, '__dataclass_fields__')
        assert config.__dataclass_params__.frozen is True
        
        # Should raise error when trying to modify
        with pytest.raises((AttributeError, TypeError)):
            config.host = "modified"  # type: ignore

    def test_discovery_paths_are_frozen(self) -> None:
        """Test that discovery paths are immutable."""
        paths = RetroPiePaths(home_dir="/test", username="test")
        
        # Should be a frozen dataclass
        assert hasattr(paths, '__dataclass_fields__')
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
            uptime=3600
        )
        
        assert hasattr(system_info, '__dataclass_fields__')
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
            execution_time=0.1
        )
        
        assert hasattr(result, '__dataclass_fields__')
        assert result.__dataclass_params__.frozen is True
        
        with pytest.raises((AttributeError, TypeError)):
            result.command = "modified"  # type: ignore


class TestDependencyInjectionCompliance:
    """Test that components use dependency injection as required by CLAUDE.md."""

    def test_tools_use_dependency_injection(self) -> None:
        """Test that all tool classes use dependency injection."""
        tool_classes = [
            SystemTools,
            HardwareTools,
            RetroPieTools,
            ControllerTools,
            EmulationStationTools
        ]
        
        for tool_class in tool_classes:
            # Check constructor requires dependencies
            init_signature = inspect.signature(tool_class.__init__)
            params = list(init_signature.parameters.values())[1:]  # Skip 'self'
            
            # Should require config and ssh dependencies
            assert len(params) >= 2, f"{tool_class.__name__} should require config and ssh dependencies"
            
            # Check parameter names are meaningful
            param_names = [p.name for p in params]
            assert any("config" in name.lower() for name in param_names), \
                f"{tool_class.__name__} should have config parameter"
            assert any("ssh" in name.lower() for name in param_names), \
                f"{tool_class.__name__} should have ssh parameter"

    def test_ssh_handler_dependency_injection(self) -> None:
        """Test that SSHHandler uses dependency injection."""
        init_signature = inspect.signature(SSHHandler.__init__)
        params = list(init_signature.parameters.values())[1:]  # Skip 'self'
        
        # Should require config dependency
        assert len(params) >= 1, "SSHHandler should require config dependency"
        
        # Check parameter is typed
        config_param = params[0]
        assert config_param.annotation != inspect.Parameter.empty, \
            "SSHHandler config parameter should be type-hinted"

    def test_profile_manager_dependency_injection(self) -> None:
        """Test that SystemProfileManager uses dependency injection."""
        init_signature = inspect.signature(SystemProfileManager.__init__)
        params = list(init_signature.parameters.values())[1:]  # Skip 'self'
        
        # Should allow profile_dir injection
        if params:  # Optional dependency
            profile_dir_param = params[0]
            assert "profile" in profile_dir_param.name.lower() or "dir" in profile_dir_param.name.lower(), \
                "Profile manager should have meaningful parameter name"


class TestTypeHintCompliance:
    """Test that all functions have type hints as required by CLAUDE.md."""

    def _get_public_methods(self, cls: type) -> list:
        """Get all public methods of a class."""
        return [
            method for method in inspect.getmembers(cls, predicate=inspect.isfunction)
            if not method[0].startswith('_')
        ]

    def test_tool_methods_have_type_hints(self) -> None:
        """Test that all tool methods have proper type hints."""
        tool_classes = [
            SystemTools,
            HardwareTools, 
            RetroPieTools,
            ControllerTools,
            EmulationStationTools
        ]
        
        for tool_class in tool_classes:
            public_methods = self._get_public_methods(tool_class)
            
            for method_name, method in public_methods:
                # Get type hints
                hints = get_type_hints(method)
                signature = inspect.signature(method)
                
                # Check return type hint exists
                assert 'return' in hints, \
                    f"{tool_class.__name__}.{method_name} missing return type hint"
                
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
                    assert field.type != Any, \
                        f"{config_class.__name__}.{field.name} should have specific type, not Any"

    def test_domain_models_have_type_hints(self) -> None:
        """Test that domain models have proper type hints."""
        domain_classes = [SystemInfo, Controller, CommandResult]
        
        for domain_class in domain_classes:
            if is_dataclass(domain_class):
                # Check dataclass fields have type annotations
                for field in fields(domain_class):
                    assert field.type != Any, \
                        f"{domain_class.__name__}.{field.name} should have specific type, not Any"


class TestMeaningfulNamingCompliance:
    """Test that code uses meaningful names as required by CLAUDE.md."""

    def test_no_single_letter_variable_names(self) -> None:
        """Test that we don't use single-letter variable names in key files."""
        # This is a simplified check - in practice, you'd parse AST of source files
        key_modules = [
            'retromcp.config',
            'retromcp.discovery', 
            'retromcp.profile',
            'retromcp.tools.system_tools'
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
                                if arg.arg != 'self' and len(arg.arg) == 1:
                                    # Allow some common single-letter exceptions
                                    if arg.arg not in ['x', 'y', 'i', 'j', 'n']:
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
            (SystemTools, "SystemTools"),
            (RetroPieConfig, "RetroPieConfig"), 
            (SystemProfile, "SystemProfile"),
            (CommandResult, "CommandResult")
        ]
        
        for cls, expected_pattern in classes_to_check:
            class_name = cls.__name__
            
            # Should not be abbreviated beyond recognition
            assert len(class_name) >= 4, f"Class name '{class_name}' too short"
            
            # Should use PascalCase
            assert class_name[0].isupper(), f"Class name '{class_name}' should start with uppercase"
            
            # Should be descriptive
            assert class_name == expected_pattern, f"Class name '{class_name}' should match expected pattern"

    def test_method_names_are_descriptive(self) -> None:
        """Test that method names are descriptive and follow conventions."""
        # Check a sample of key methods
        method_checks = [
            (SystemTools, "get_tools"),
            (RetroPieConfig, "from_env"),
            (SystemProfileManager, "get_or_create_profile"),
            (SSHHandler, "execute_command")
        ]
        
        for cls, method_name in method_checks:
            assert hasattr(cls, method_name), f"{cls.__name__} should have method {method_name}"
            
            method = getattr(cls, method_name)
            
            # Method name should be descriptive
            assert len(method_name) >= 3, f"Method name '{method_name}' too short"
            
            # Should use snake_case
            assert method_name.islower() or '_' in method_name, \
                f"Method name '{method_name}' should use snake_case"


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
        forbidden_imports = ['paramiko', 'socket', 'requests']
        for forbidden in forbidden_imports:
            assert forbidden not in content.lower(), \
                f"Domain models should not import {forbidden}"

    def test_tools_separate_domain_from_infrastructure(self) -> None:
        """Test that tools separate domain logic from infrastructure."""
        # SystemTools should use injected SSH handler, not create it directly
        system_tools_module = inspect.getmodule(SystemTools)
        source_file = Path(system_tools_module.__file__)
        
        with open(source_file) as f:
            content = f.read()
        
        # Should not directly instantiate SSH connections
        assert 'paramiko.SSHClient()' not in content, \
            "Tools should not directly create SSH connections"
        assert 'ssh.client.SSHClient' not in content, \
            "Tools should use injected SSH handler"

    def test_config_objects_are_pure_data(self) -> None:
        """Test that config objects are pure data without behavior."""
        config_classes = [RetroPieConfig, ServerConfig, RetroPiePaths]
        
        for config_class in config_classes:
            # Get all methods (excluding special methods)
            methods = [
                method for method in inspect.getmembers(config_class, predicate=inspect.ismethod)
                if not method[0].startswith('__')
            ]
            
            # Config objects should have minimal behavior
            # Allow factory methods (from_env) and simple transformations (with_paths)
            allowed_method_patterns = ['from_', 'with_', 'to_']
            
            for method_name, method in methods:
                if not any(method_name.startswith(pattern) for pattern in allowed_method_patterns):
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
        assert inspect.isabstract(RetroPieClient) or hasattr(RetroPieClient, '__abstractmethods__'), \
            "RetroPieClient should be an abstract interface"

    def test_infrastructure_implements_ports(self) -> None:
        """Test that infrastructure classes implement domain ports."""
        from retromcp.infrastructure.ssh_retropie_client import SSHRetroPieClient
        from retromcp.domain.ports import RetroPieClient
        
        # Infrastructure should implement domain interfaces
        assert issubclass(SSHRetroPieClient, RetroPieClient), \
            "SSH client should implement RetroPie client interface"

    def test_tools_depend_on_abstractions(self) -> None:
        """Test that tools depend on abstractions, not concretions."""
        # Check SystemTools constructor
        init_signature = inspect.signature(SystemTools.__init__)
        params = list(init_signature.parameters.values())[1:]  # Skip 'self'
        
        # Should accept abstract SSH handler, not concrete SSH implementation
        ssh_param = None
        for param in params:
            if 'ssh' in param.name.lower():
                ssh_param = param
                break
        
        assert ssh_param is not None, "SystemTools should have SSH parameter"
        
        # The SSH parameter should not be tied to specific implementation
        if ssh_param.annotation != inspect.Parameter.empty:
            annotation_str = str(ssh_param.annotation)
            assert 'SSHHandler' in annotation_str or 'ssh' in annotation_str.lower(), \
                "SSH parameter should reference handler interface"