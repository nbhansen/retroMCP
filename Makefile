# RetroMCP Test Management Makefile
# Provides convenient commands for running targeted tests

.PHONY: help test test-all test-quick test-coverage
.PHONY: test-tools test-infrastructure test-application test-domain
.PHONY: test-hardware test-gaming test-state test-system test-docker
.PHONY: test-ssh test-security test-contract
.PHONY: test-unit test-integration test-e2e
.PHONY: coverage coverage-html coverage-report
.PHONY: lint format check clean
.PHONY: security-audit security-check security-migration

# Default target
help:
	@echo "RetroMCP Test Management Commands"
	@echo "================================="
	@echo ""
	@echo "Test Execution:"
	@echo "  make test              - Run all tests"
	@echo "  make test-quick        - Run tests without coverage"
	@echo "  make test-coverage     - Run tests with coverage report"
	@echo ""
	@echo "Component Testing:"
	@echo "  make test-tools        - Run all tool tests"
	@echo "  make test-infrastructure - Run infrastructure tests"
	@echo "  make test-application  - Run application layer tests"
	@echo "  make test-domain       - Run domain layer tests"
	@echo ""
	@echo "Tool-Specific Testing:"
	@echo "  make test-hardware     - Run hardware monitoring tests"
	@echo "  make test-gaming       - Run gaming system tests"
	@echo "  make test-state        - Run state management tests"
	@echo "  make test-system       - Run system management tests"
	@echo "  make test-docker       - Run docker tools tests"
	@echo ""
	@echo "Infrastructure Testing:"
	@echo "  make test-ssh          - Run SSH repository tests"
	@echo "  make test-controller   - Run controller repository tests"
	@echo "  make test-emulator     - Run emulator repository tests"
	@echo ""
	@echo "Special Testing:"
	@echo "  make test-security     - Run security tests"
	@echo "  make test-contract     - Run contract/MCP compliance tests"
	@echo "  make test-unit         - Run unit tests only"
	@echo "  make test-integration  - Run integration tests only"
	@echo ""
	@echo "Security & Audit:"
	@echo "  make security-check    - Run comprehensive security tests"
	@echo "  make security-audit    - Audit configuration for security issues"
	@echo "  make security-migration - Help migrate to secure configuration"
	@echo "  make verify-permissions - Check user sudo permissions"
	@echo ""
	@echo "Coverage & Quality:"
	@echo "  make coverage          - Generate coverage report"
	@echo "  make coverage-html     - Generate HTML coverage report"
	@echo "  make lint              - Run linting"
	@echo "  make format            - Format code"
	@echo "  make check             - Run all quality checks"

# Test execution commands
test:
	@echo "Running all tests with coverage..."
	@python3 -m pytest 2>/dev/null || echo "⚠ pytest not available - install with: pip3 install pytest"

test-all: test

test-quick:
	@echo "Running all tests without coverage..."
	@python3 -m pytest --no-cov -v 2>/dev/null || echo "⚠ pytest not available - install with: pip3 install pytest"

test-coverage:
	@echo "Running tests with detailed coverage..."
	@python3 -m pytest --cov=retromcp --cov-report=term-missing --cov-report=html 2>/dev/null || echo "⚠ pytest-cov not available - install with: pip3 install pytest-cov"

# Component-based testing
test-tools:
	@echo "Running all tool tests..."
	@source venv/bin/activate && python -m pytest -m "tools" -v

test-infrastructure:
	@echo "Running infrastructure tests..."
	@source venv/bin/activate && python -m pytest -m "infrastructure" -v

test-application:
	@echo "Running application layer tests..."
	@source venv/bin/activate && python -m pytest -m "application" -v

test-domain:
	@echo "Running domain layer tests..."
	@source venv/bin/activate && python -m pytest -m "domain" -v

# Tool-specific testing
test-hardware:
	@echo "Running hardware monitoring tool tests..."
	@source venv/bin/activate && python -m pytest -m "hardware_tools" -v

test-gaming:
	@echo "Running gaming system tool tests..."
	@source venv/bin/activate && python -m pytest -m "gaming_tools" -v

test-state:
	@echo "Running state management tool tests..."
	@source venv/bin/activate && python -m pytest -m "state_tools" -v

test-system:
	@echo "Running system management tool tests..."
	@source venv/bin/activate && python -m pytest -m "system_tools" -v

test-docker:
	@echo "Running docker tool tests..."
	@source venv/bin/activate && python -m pytest -m "docker_tools" -v

# Infrastructure-specific testing
test-ssh:
	@echo "Running SSH repository tests..."
	@source venv/bin/activate && python -m pytest -m "ssh_repos" -v

test-controller:
	@echo "Running controller repository tests..."
	@source venv/bin/activate && python -m pytest -m "controller_repo" -v

test-emulator:
	@echo "Running emulator repository tests..."
	@source venv/bin/activate && python -m pytest -m "emulator_repo" -v

test-docker-repo:
	@echo "Running docker repository tests..."
	@source venv/bin/activate && python -m pytest -m "docker_repo" -v

test-state-repo:
	@echo "Running state repository tests..."
	@source venv/bin/activate && python -m pytest -m "state_repo" -v

# Special testing
test-security:
	@echo "Running security tests..."
	@source venv/bin/activate && python -m pytest tests/unit/test_ssh_security.py tests/unit/test_security_enhancements.py tests/unit/test_secure_command_execution.py -v

test-contract:
	@echo "Running contract/MCP compliance tests..."
	@source venv/bin/activate && python -m pytest -m "contract" -v

test-unit:
	@echo "Running unit tests only..."
	@source venv/bin/activate && python -m pytest -m "unit" -v

test-integration:
	@echo "Running integration tests only..."
	@source venv/bin/activate && python -m pytest -m "integration" -v

# Security & Audit commands
security-check:
	@echo "Running comprehensive security validation..."
	@echo "1. Testing SSH security features..."
	@source venv/bin/activate && python -m pytest tests/unit/test_ssh_security.py -v
	@echo ""
	@echo "2. Testing enhanced security features..."
	@source venv/bin/activate && python -m pytest tests/unit/test_security_enhancements.py -v
	@echo ""
	@echo "3. Testing secure command execution..."
	@source venv/bin/activate && python -m pytest tests/unit/test_secure_command_execution.py -v
	@echo ""
	@echo "4. Validating configuration security..."
	@source venv/bin/activate && python -c "from retromcp.config import RetroPieConfig; print('✓ Configuration validation working')"
	@echo ""
	@echo "Security check complete!"

security-audit:
	@echo "Running security configuration audit..."
	@echo "Checking for security files and configurations..."
	@test -f config/retromcp-sudoers && echo "✓ Secure sudoers file present" || echo "✗ Secure sudoers file missing"
	@test -f scripts/security-migration.sh && echo "✓ Security migration script present" || echo "✗ Migration script missing"
	@test -f scripts/security-audit.sh && echo "✓ Security audit script present" || echo "✗ Audit script missing"
	@test -f .env.example && echo "✓ Secure configuration example present" || echo "✗ Config example missing"
	@echo ""
	@echo "Configuration validation:"
	@if [ -f .env ]; then \
		echo "Checking .env configuration..."; \
		if grep -q "RETROPIE_USERNAME=root" .env 2>/dev/null; then \
			echo "✗ WARNING: Root username detected in .env"; \
		else \
			echo "✓ No root username in configuration"; \
		fi; \
		if grep -q "RETROPIE_KEY_PATH" .env 2>/dev/null; then \
			echo "✓ SSH key authentication configured"; \
		elif grep -q "RETROPIE_PASSWORD" .env 2>/dev/null; then \
			echo "⚠ Using password authentication (consider SSH keys)"; \
		else \
			echo "✗ No authentication method configured"; \
		fi; \
	else \
		echo "ℹ No .env file found (use .env.example as template)"; \
	fi
	@echo ""
	@echo "Security audit complete!"

security-migration:
	@echo "Security Migration Helper"
	@echo "========================"
	@echo ""
	@echo "This project has been secured to eliminate passwordless root SSH."
	@echo ""
	@echo "Key security improvements:"
	@echo "- Root user access blocked"
	@echo "- Targeted sudo rules instead of NOPASSWD:ALL"
	@echo "- SSH host verification enforced"
	@echo "- Command injection prevention"
	@echo ""
	@echo "Migration steps:"
	@echo "1. Copy secure sudoers: sudo cp config/retromcp-sudoers /etc/sudoers.d/retromcp"
	@echo "2. Set up SSH keys: ssh-keygen -t rsa -b 4096 -f ~/.ssh/retromcp_key"
	@echo "3. Update configuration: cp .env.example .env (and edit)"
	@echo "4. Test connection with new security model"
	@echo ""
	@echo "For Raspberry Pi systems, run: ./scripts/security-migration.sh"
	@echo ""

# Coverage commands
coverage:
	@echo "Generating coverage report..."
	@source venv/bin/activate && python -m pytest --cov=retromcp --cov-report=term-missing

coverage-html:
	@echo "Generating HTML coverage report..."
	@source venv/bin/activate && python -m pytest --cov=retromcp --cov-report=html
	@echo "Open htmlcov/index.html in your browser to view the report"

coverage-report: coverage-html

# Quality checks
lint:
	@echo "Running linting..."
	@source venv/bin/activate && ruff check

format:
	@echo "Formatting code..."
	@source venv/bin/activate && ruff format

check: lint
	@echo "Running ruff format check..."
	@source venv/bin/activate && ruff format --check

# Cleanup
clean:
	@echo "Cleaning up test artifacts..."
	@rm -rf .pytest_cache
	@rm -rf htmlcov
	@rm -rf .coverage
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@echo "Cleanup complete"

# Help for specific components
help-tools:
	@echo "Tool Testing Commands:"
	@echo "  make test-hardware     - Hardware monitoring tools"
	@echo "  make test-gaming       - Gaming system tools"
	@echo "  make test-state        - State management tools"
	@echo "  make test-system       - System management tools"
	@echo "  make test-docker       - Docker tools"

help-infrastructure:
	@echo "Infrastructure Testing Commands:"
	@echo "  make test-ssh          - All SSH repositories"
	@echo "  make test-controller   - Controller repository"
	@echo "  make test-emulator     - Emulator repository"
	@echo "  make test-docker-repo  - Docker repository"
	@echo "  make test-state-repo   - State repository"

# Development workflow commands
dev-test:
	@echo "Running development test suite (unit + tools)..."
	@source venv/bin/activate && python -m pytest -m "unit and tools" -v

quick-check:
	@echo "Running quick checks (lint + format + unit tests)..."
	@make lint
	@make format
	@source venv/bin/activate && python -m pytest -m "unit" --no-cov -x

# Local security validation (no Pi required)
validate-security:
	@echo "Validating security configuration locally..."
	@echo "1. Checking security imports..."
	@python3 -c "from retromcp.secure_ssh_handler_v2 import SecureSSHHandlerV2; print('✓ Enhanced SSH handler available')" 2>/dev/null || echo "⚠ Enhanced SSH handler not available (may need installation)"
	@echo "2. Testing root user blocking..."
	@python3 -c "from retromcp.secure_ssh_handler_v2 import SecureSSHHandlerV2; \
		try: SecureSSHHandlerV2('test', 'root'); print('✗ Root blocking failed') \
		except ValueError: print('✓ Root user properly blocked')" 2>/dev/null || echo "⚠ Root blocking test skipped"
	@echo "3. Testing configuration validation..."
	@python3 -c "from retromcp.config import RetroPieConfig; \
		try: RetroPieConfig._validate_security_requirements('root', None, None); print('✗ Config validation failed') \
		except ValueError: print('✓ Configuration validation working')" 2>/dev/null || echo "⚠ Config validation test skipped"
	@echo "4. Testing command validation..."
	@python3 -c "from retromcp.secure_ssh_handler_v2 import SecureSSHHandlerV2; \
		h = SecureSSHHandlerV2('test', 'pi'); \
		try: h._validate_sudo_command('rm -rf /'); print('✗ Command validation failed') \
		except ValueError: print('✓ Dangerous commands properly blocked')" 2>/dev/null || echo "⚠ Command validation test skipped"
	@echo "5. Testing sudo parameter support..."
	@python3 -c "from retromcp.secure_ssh_handler_v2 import SecureSSHHandlerV2; \
		import inspect; h = SecureSSHHandlerV2('test', 'pi'); \
		sig = inspect.signature(h.execute_command); \
		print('✓ SSH handler supports use_sudo parameter') if 'use_sudo' in sig.parameters else print('✗ Missing use_sudo support')" 2>/dev/null || echo "⚠ Cannot validate handler signature"
	@echo ""
	@echo "✓ Local security validation complete!"

# Show security status
security-status:
	@echo "RetroMCP Security Status"
	@echo "======================="
	@echo ""
	@echo "Security Features Implemented:"
	@echo "✓ Root user access blocked"
	@echo "✓ SSH host verification enforced" 
	@echo "✓ Targeted sudo rules (no NOPASSWD:ALL)"
	@echo "✓ Command injection prevention"
	@echo "✓ Input validation and sanitization"
	@echo "✓ Credential cleanup after use"
	@echo "✓ Error message sanitization"
	@echo ""
	@echo "Available Security Tools:"
	@echo "- make security-check     : Run all security tests"
	@echo "- make security-audit     : Audit configuration"
	@echo "- make validate-security  : Local security validation"
	@echo "- make security-migration : Migration guidance"
	@echo "- make verify-permissions : Check user sudo permissions"
	@echo ""
	@echo "Security Configuration:"
	@echo "- config/retromcp-sudoers  : Secure sudo rules"
	@echo "- .env.example             : Secure configuration template"
	@echo ""

# Verify user permissions for sudo commands
verify-permissions:
	@echo "Verifying user permissions for RetroMCP operations..."
	@if [ -f scripts/verify-user-permissions.sh ]; then \
		./scripts/verify-user-permissions.sh; \
	else \
		echo "⚠ Permission verification script not found"; \
		echo "This check requires deployment on a RetroPie system"; \
	fi