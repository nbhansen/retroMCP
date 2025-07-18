# RetroMCP Test Management Makefile
# Provides convenient commands for running targeted tests

.PHONY: help test test-all test-quick test-coverage
.PHONY: test-tools test-infrastructure test-application test-domain
.PHONY: test-hardware test-gaming test-state test-system test-docker
.PHONY: test-ssh test-security test-contract
.PHONY: test-unit test-integration test-e2e
.PHONY: coverage coverage-html coverage-report
.PHONY: lint format check clean

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
	@echo "Coverage & Quality:"
	@echo "  make coverage          - Generate coverage report"
	@echo "  make coverage-html     - Generate HTML coverage report"
	@echo "  make lint              - Run linting"
	@echo "  make format            - Format code"
	@echo "  make check             - Run all quality checks"

# Test execution commands
test:
	@echo "Running all tests with coverage..."
	@source venv/bin/activate && python -m pytest

test-all: test

test-quick:
	@echo "Running all tests without coverage..."
	@source venv/bin/activate && python -m pytest --no-cov -v

test-coverage:
	@echo "Running tests with detailed coverage..."
	@source venv/bin/activate && python -m pytest --cov=retromcp --cov-report=term-missing --cov-report=html

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
	@source venv/bin/activate && python -m pytest -m "security" -v

test-contract:
	@echo "Running contract/MCP compliance tests..."
	@source venv/bin/activate && python -m pytest -m "contract" -v

test-unit:
	@echo "Running unit tests only..."
	@source venv/bin/activate && python -m pytest -m "unit" -v

test-integration:
	@echo "Running integration tests only..."
	@source venv/bin/activate && python -m pytest -m "integration" -v

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