#!/usr/bin/env python3
"""Smart test runner for RetroMCP.

This script provides an intelligent interface for running targeted tests
based on component, coverage requirements, and development workflow.
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List
from typing import Optional


class TestRunner:
    """Smart test runner with component-based execution."""

    def __init__(self) -> None:
        self.venv_python = Path("venv/bin/python")
        self.base_cmd = [str(self.venv_python), "-m", "pytest"]

    def run_command(self, cmd: List[str], description: str) -> bool:
        """Run a command and return success status."""
        print(f"🔍 {description}")
        print(f"📋 Running: {' '.join(cmd)}")
        print("─" * 50)

        result = subprocess.run(cmd, capture_output=False)
        success = result.returncode == 0

        print("─" * 50)
        if success:
            print("✅ Command completed successfully")
        else:
            print("❌ Command failed")
        print()

        return success

    def run_tests(
        self,
        markers: Optional[List[str]] = None,
        paths: Optional[List[str]] = None,
        coverage: bool = True,
        verbose: bool = True,
        quick: bool = False,
        extra_args: Optional[List[str]] = None
    ) -> bool:
        """Run tests with specified options."""
        cmd = self.base_cmd.copy()

        # Add markers
        if markers:
            for marker in markers:
                cmd.extend(["-m", marker])

        # Add paths
        if paths:
            cmd.extend(paths)

        # Add coverage
        if coverage and not quick:
            cmd.extend([
                "--cov=retromcp",
                "--cov-report=term-missing",
                "--cov-report=html"
            ])
        elif quick:
            cmd.append("--no-cov")

        # Add verbosity
        if verbose:
            cmd.append("-v")

        # Add extra arguments
        if extra_args:
            cmd.extend(extra_args)

        # Create description
        desc_parts = []
        if markers:
            desc_parts.append(f"markers: {', '.join(markers)}")
        if paths:
            desc_parts.append(f"paths: {', '.join(paths)}")
        if coverage:
            desc_parts.append("with coverage")
        if quick:
            desc_parts.append("quick mode")

        description = f"Running tests ({', '.join(desc_parts)})" if desc_parts else "Running all tests"

        return self.run_command(cmd, description)


def main() -> None:
    """Main entry point for the test runner."""
    parser = argparse.ArgumentParser(
        description="Smart test runner for RetroMCP",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Run all tests
  %(prog)s --tools                  # Run all tool tests
  %(prog)s --hardware               # Run hardware monitoring tests
  %(prog)s --gaming                 # Run gaming system tests
  %(prog)s --ssh                    # Run SSH repository tests
  %(prog)s --quick                  # Run tests without coverage
  %(prog)s --unit --tools           # Run unit tests for tools only
  %(prog)s --security --contract    # Run security and contract tests
  %(prog)s --path tests/unit/test_hardware_monitoring_tools.py  # Run specific file
        """
    )

    # Component markers
    parser.add_argument("--tools", action="store_true", help="Run tool tests")
    parser.add_argument("--infrastructure", action="store_true", help="Run infrastructure tests")
    parser.add_argument("--application", action="store_true", help="Run application tests")
    parser.add_argument("--domain", action="store_true", help="Run domain tests")

    # Tool-specific markers
    parser.add_argument("--hardware", action="store_true", help="Run hardware monitoring tests")
    parser.add_argument("--gaming", action="store_true", help="Run gaming system tests")
    parser.add_argument("--state", action="store_true", help="Run state management tests")
    parser.add_argument("--system", action="store_true", help="Run system management tests")
    parser.add_argument("--docker", action="store_true", help="Run docker tool tests")

    # Infrastructure-specific markers
    parser.add_argument("--ssh", action="store_true", help="Run SSH repository tests")
    parser.add_argument("--controller", action="store_true", help="Run controller repository tests")
    parser.add_argument("--emulator", action="store_true", help="Run emulator repository tests")

    # Special markers
    parser.add_argument("--security", action="store_true", help="Run security tests")
    parser.add_argument("--contract", action="store_true", help="Run contract/MCP compliance tests")
    parser.add_argument("--unit", action="store_true", help="Run unit tests only")
    parser.add_argument("--integration", action="store_true", help="Run integration tests only")

    # Execution options
    parser.add_argument("--no-coverage", action="store_true", help="Skip coverage reporting")
    parser.add_argument("--quick", action="store_true", help="Quick mode (no coverage, fail fast)")
    parser.add_argument("--quiet", action="store_true", help="Reduce output verbosity")
    parser.add_argument("--path", action="append", help="Add specific test path")
    parser.add_argument("--extra", action="append", help="Extra pytest arguments")

    # Predefined test suites
    parser.add_argument("--dev", action="store_true", help="Development suite (unit + tools)")
    parser.add_argument("--ci", action="store_true", help="CI suite (all tests with coverage)")
    parser.add_argument("--smoke", action="store_true", help="Smoke test suite (critical tests only)")

    args = parser.parse_args()

    # Check if virtual environment exists
    runner = TestRunner()
    if not runner.venv_python.exists():
        print("❌ Virtual environment not found. Please run 'python -m venv venv' and install dependencies.")
        sys.exit(1)

    # Build markers list
    markers = []

    # Component markers
    if args.tools:
        markers.append("tools")
    if args.infrastructure:
        markers.append("infrastructure")
    if args.application:
        markers.append("application")
    if args.domain:
        markers.append("domain")

    # Tool-specific markers
    if args.hardware:
        markers.append("hardware_tools")
    if args.gaming:
        markers.append("gaming_tools")
    if args.state:
        markers.append("state_tools")
    if args.system:
        markers.append("system_tools")
    if args.docker:
        markers.append("docker_tools")

    # Infrastructure-specific markers
    if args.ssh:
        markers.append("ssh_repos")
    if args.controller:
        markers.append("controller_repo")
    if args.emulator:
        markers.append("emulator_repo")

    # Special markers
    if args.security:
        markers.append("security")
    if args.contract:
        markers.append("contract")
    if args.unit:
        markers.append("unit")
    if args.integration:
        markers.append("integration")

    # Predefined suites
    if args.dev:
        markers.extend(["unit", "tools"])
    if args.ci:
        # CI runs all tests - no specific markers
        pass
    if args.smoke:
        markers.extend(["unit", "hardware_tools", "gaming_tools", "state_tools"])

    # Execution options
    coverage = not args.no_coverage and not args.quick
    verbose = not args.quiet
    paths = args.path or []
    extra_args = args.extra or []

    if args.quick:
        extra_args.append("-x")  # Fail fast

    # Run tests
    success = runner.run_tests(
        markers=markers if markers else None,
        paths=paths if paths else None,
        coverage=coverage,
        verbose=verbose,
        quick=args.quick,
        extra_args=extra_args
    )

    if not success:
        print("❌ Test execution failed!")
        sys.exit(1)

    print("🎉 All tests completed successfully!")


if __name__ == "__main__":
    main()
