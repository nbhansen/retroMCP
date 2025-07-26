# RetroMCP Specification

## Overview
RetroMCP is an MCP server that enables AI assistants to manage Raspberry Pi systems and RetroPie installations via SSH. Built with hexagonal architecture, comprehensive security controls, and state management.

## Core Architecture
- **Pattern**: Hexagonal Architecture with Domain-Driven Design
- **Security**: Defense-in-depth with input validation (all user inputs sanitized with `shlex.quote()`)
- **Testing**: TDD with 84% coverage, 434 passing tests
- **Protocol**: Full MCP compliance

## State Management v2.0
Persistent system state with caching and change tracking:
- **Storage**: JSON at `/home/{user}/.retropie-state.json`
- **Tool**: `retromcp:manage_state(action, options)`
- **Actions**: `load`, `save`, `update`, `compare`, `export`, `import`, `diff`, `watch`
- **Caching**: TTL-based (system: 30s, hardware: 5min, network: 1min)

## Security Status
- All critical vulnerabilities patched (SSH hardening, command injection prevention)
- Comprehensive input validation framework
- Requires passwordless sudo or stored credentials
- 23 security tests with 100% pass rate

## Tool Structure (Post-Consolidation)
1. **SystemManagementTools** (`manage_system`)
   - Resources: service, package, file, command, connection, info, update
   
2. **HardwareMonitoringTools** (`manage_hardware`)
   - Components: temperature, fan, power, gpio, errors, all
   
3. **GamingSystemTools** (`manage_gaming`)
   - Components: retropie, emulationstation, controller, roms, emulator, audio, video
   
4. **DockerTools** (`manage_docker`)
   - Actions: container (pull/run/ps/stop/start/etc), compose, volume
   
5. **StateTools** (`manage_state`)
   - Actions: load, save, update, compare, export, import, diff, watch

## Environment Variables
- `RETROPIE_HOST`: Pi IP/hostname
- `RETROPIE_USERNAME`: SSH username
- `RETROPIE_PASSWORD`: SSH password (optional)
- `RETROPIE_SSH_KEY_PATH`: SSH key path
- `RETROPIE_PORT`: SSH port (default 22)

## Key Use Cases
1. Controller setup and configuration
2. Emulator installation and optimization
3. System troubleshooting and performance
4. Package and dependency management
5. BIOS file verification

## Implementation Status
- ✅ Production-ready for controlled testing
- ✅ 56% tool reduction through consolidation (9→4 classes)
- ✅ Comprehensive security hardening complete
- 🔄 Batch command execution proposed for user control