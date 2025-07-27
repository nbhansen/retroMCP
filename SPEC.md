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

## Command Queue System (Proposed)

### Problem
LLMs using RetroMCP may execute multiple commands rapidly without user ability to interrupt, leading to:
- Cascading failures from early command errors
- Inability to stop problematic command sequences
- No visibility into what's being executed until completion
- Potential system damage from unchecked automation

### Solution: Command Queue with Confirmation

**New Tool**: `manage_command_queue`

**Core Concept**: Commands are added to a queue and executed one at a time with user control between each step.

### API Design
```python
manage_command_queue(
    action="create|add|execute_next|execute_all|status|skip|cancel",
    queue_id="q1",  # Required for all actions except create
    name="System Update",  # For create action
    commands=[  # For create/add actions
        {"command": "sudo apt update", "description": "Update package lists"},
        {"command": "sudo apt upgrade -y", "description": "Upgrade packages"},
        {"command": "sudo systemctl restart docker", "description": "Restart Docker"}
    ],
    auto_execute=False,  # If true, runs all commands without pausing
    pause_between=2  # Seconds between commands (for auto_execute mode)
)
```

### Execution Flow
1. **Create Queue**: LLM creates queue with all planned commands
2. **User Review**: User sees full command list before execution
3. **Step Execution**: User calls `execute_next` to run one command
4. **Result Review**: User sees command output before continuing
5. **Control Options**: User can skip failed commands, cancel queue, or continue

### Example Interaction
```
AI: I'll update your system using a command queue for safety:

Created command queue: System Update (ID: q1)
Commands:
1. Update package lists
   Command: sudo apt update
2. Upgrade packages  
   Command: sudo apt upgrade -y
3. Restart Docker
   Command: sudo systemctl restart docker

Use 'execute_next' to run the first command.

User: execute_next

[1/3] Executing: Update package lists
Command: sudo apt update
✓ Success
Output: Hit:1 http://archive.raspberrypi.org/debian bullseye InRelease...

Next command: Upgrade packages
Use 'execute_next' to continue or 'status' to review.

User: status

Queue: System Update (ID: q1)
Progress: 1/3 commands
1. ✅ Update package lists (Duration: 2.3s)
2. ⏳ Upgrade packages
3. ⏳ Restart Docker
```

### Benefits
- **Transparency**: Users see all commands before execution
- **Interruptibility**: Can stop at any point
- **Error Recovery**: Skip failed commands without stopping entire sequence
- **Debugging**: Clear indication of which command failed
- **Safety**: Prevents runaway automation

### Implementation Notes
- Queue state persists during session
- Failed commands can be skipped with `skip` action
- `cancel` action marks all remaining commands as cancelled
- `status` shows queue progress with success/failure indicators
- Each command tracks execution time and output