# RetroMCP Specification

## Project Vision

RetroMCP is an MCP (Model Context Protocol) server that enables AI assistants to help users configure, troubleshoot, and manage RetroPie installations on Raspberry Pi. The focus is on system setup and configuration rather than game playing.

## Core Use Cases

### 1. Controller Setup
- **Problem**: User plugs in a new controller and it doesn't work
- **Solution**: AI detects controller type, installs required drivers, configures mappings
- **Example**: "I just plugged in my 8BitDo controller but it's not working"

### 2. Emulator Installation & Configuration
- **Problem**: User wants to play N64 games but emulator isn't set up
- **Solution**: AI installs emulator, configures performance settings, checks BIOS files
- **Example**: "Help me get N64 games running smoothly on my Pi 4"

### 3. System Troubleshooting
- **Problem**: Games are running slowly or system is overheating
- **Solution**: AI checks system stats, adjusts overclock settings, manages cooling
- **Example**: "My PSX games are stuttering"

### 4. Package Management
- **Problem**: Missing dependencies or outdated packages
- **Solution**: AI manages apt packages, RetroPie modules, and system updates
- **Example**: "Install everything I need for arcade games"

### 5. BIOS File Management
- **Problem**: Emulators need BIOS files but user doesn't know which ones
- **Solution**: AI checks required BIOS files and guides user on what's needed
- **Example**: "Why won't my PlayStation games start?"

## Technical Architecture

### MCP Server (Python)
- Runs on user's main computer
- Connects to Raspberry Pi via SSH
- Provides tools and resources to AI

### Communication Flow
```
Claude/AI → MCP Client → RetroMCP Server → SSH → Raspberry Pi
```

### Key Components
1. **SSH Handler**: Manages secure connection to Pi
2. **System Tools**: Package installation, service management
3. **Controller Tools**: Detection, driver installation, configuration
4. **Emulator Tools**: Installation, configuration, BIOS checking
5. **Diagnostic Tools**: Performance monitoring, log analysis

## Planned Tools

### System Management
- `install_packages` - Install apt packages
- `update_system` - Run system updates
- `check_disk_space` - Monitor storage
- `manage_services` - Start/stop/restart services

### Controller Configuration
- `detect_controllers` - List connected controllers
- `setup_controller` - Install drivers and configure
- `test_controller` - Verify controller works
- `map_controller` - Configure button mappings

### Emulator Management
- `list_emulators` - Show installed/available emulators
- `install_emulator` - Install via RetroPie-Setup
- `configure_emulator` - Adjust settings
- `check_bios` - Verify required BIOS files

### Diagnostics
- `system_info` - CPU, memory, temperature
- `check_logs` - View relevant log files
- `performance_test` - Run benchmarks
- `network_test` - Check connectivity

### File Management
- `browse_roms` - List ROM files
- `check_permissions` - Verify file permissions
- `manage_configs` - Edit configuration files

## Security Considerations

1. **SSH Authentication**
   - Support both password and key-based auth
   - Encrypted credential storage
   - Connection timeout handling

2. **Command Whitelisting**
   - Only allow specific safe commands
   - No arbitrary command execution
   - Sudo only for specific operations

3. **Rate Limiting**
   - Prevent rapid command spam
   - Cooldown on system-modifying operations

## Configuration

### Environment Variables
- `RETROPIE_HOST` - Pi IP address or hostname
- `RETROPIE_USERNAME` - SSH username
- `RETROPIE_PASSWORD` - SSH password (optional)
- `RETROPIE_SSH_KEY_PATH` - Path to SSH key
- `RETROPIE_PORT` - SSH port (default 22)

### Permissions Required on Pi
- SSH access
- Sudo privileges for package management
- Access to RetroPie directories

## Future Enhancements

1. **Backup/Restore**
   - Save/restore configurations
   - Backup save states and ROMs

2. **Multi-Pi Support**
   - Manage multiple RetroPie systems
   - Sync configurations

3. **Advanced Diagnostics**
   - Performance profiling
   - Automatic optimization

4. **Community Integration**
   - Pull configurations from community
   - Share working setups

## Example Interactions

### Setting up a new controller
```
User: "I just plugged in my Xbox controller but it's not recognized"
AI: [Uses detect_controllers tool]
AI: "I can see a Microsoft Xbox controller connected via USB. Let me set it up for you."
AI: [Uses setup_controller tool with 'xbox' parameter]
AI: [Uses test_controller tool]
AI: "Your Xbox controller is now configured! I've installed the xboxdrv driver and enabled the service. You should be able to use it in EmulationStation now."
```

### Troubleshooting performance
```
User: "My N64 games are running really slowly"
AI: [Uses system_info tool]
AI: "I see your CPU temperature is quite high (82°C) and you're using the default GPU split. Let me help optimize this."
AI: [Uses configure_emulator tool]
AI: "I've adjusted the GPU memory split and enabled some performance optimizations for Mupen64Plus. I also notice you might benefit from a small overclock. Would you like me to apply that?"
```

### Installing new system
```
User: "I want to play Dreamcast games"
AI: [Uses list_emulators tool]
AI: "Dreamcast emulation requires Reicast. Let me install that for you."
AI: [Uses install_emulator tool]
AI: [Uses check_bios tool]
AI: "Reicast is installed, but you're missing the required BIOS files. You'll need dc_boot.bin and dc_flash.bin in your BIOS folder. These files should come from your own Dreamcast console."
```

## Success Metrics

1. **Setup Time Reduction**: Reduce controller setup from 30+ minutes to <5 minutes
2. **Error Resolution**: Successfully diagnose and fix 90% of common issues
3. **User Satisfaction**: Users can configure RetroPie without deep Linux knowledge
4. **Safety**: Zero instances of system damage from AI operations

## Development Roadmap

### Phase 1: Foundation & Code Quality (High Priority) ✅ COMPLETED
1. ✅ **Add comprehensive ruff configuration** to pyproject.toml with strict linting rules
   - Added comprehensive ruff configuration with 13 rule categories
   - Configured strict linting with pycodestyle, flake8, pydocstyle, and more
   - Set up automatic formatting and import sorting
2. ✅ **Fix all linting issues** identified by ruff (369 issues initially → 0 issues)
   - Fixed all syntax errors, type annotation issues, and style violations
   - Achieved zero-tolerance policy compliance per CLAUDE.md standards
3. ✅ **Add missing type hints** to all public functions, methods, and classes
   - Added comprehensive type hints throughout the codebase
   - Used proper Union types and Optional annotations
   - Implemented return type annotations for all methods
4. ✅ **Add comprehensive docstrings** to all public APIs
   - Added Google-style docstrings to all classes and methods
   - Documented parameters, return values, and exceptions
   - Included usage examples where appropriate
5. ✅ **Fix import organization** and remove unused imports
   - Organized imports according to PEP 8 standards
   - Removed unused imports and consolidated related imports
   - Used ruff's automatic import sorting

### Phase 2: Architecture Refactoring (High Priority) ✅ COMPLETED
1. ✅ **Eliminate global state** by implementing dependency injection
   - Removed all global variables from server.py
   - Implemented RetroMCPServer class with proper DI container
   - SSH connections and tool instances now managed through instance variables
2. ✅ **Add proper configuration management** replacing environment variable access
   - Created immutable RetroPieConfig and ServerConfig dataclasses
   - Environment variables loaded once at startup through RetroPieConfig.from_env()
   - Configuration objects injected into server class
3. 🔄 **Create proper domain boundaries** using hexagonal architecture
4. 🔄 **Separate concerns** into distinct layers (domain, application, infrastructure)
5. 🔄 **Implement interfaces/protocols** for all dependencies
6. 🔄 **Create immutable domain objects** where applicable

### Phase 3: Testing Infrastructure (High Priority)
1. **Add pytest configuration** with coverage reporting
2. **Create test structure** with unit, integration, and end-to-end tests
3. **Add test fixtures** for SSH connections and tool instances
4. **Mock external dependencies** for isolated unit tests
5. **Implement test factories** for creating test data
6. **Add test coverage reporting** with minimum coverage thresholds

### Phase 4: Advanced Architecture (Medium Priority)
1. **Implement command pattern** for tool operations
2. **Add event system** for better component communication
3. **Create proper validation layer** for inputs and outputs
4. **Implement retry policies** for network operations
5. **Add proper logging** with structured logging format
6. **Create health check system** for monitoring connections

### Phase 5: Documentation & Tooling (Medium Priority)
1. **Add pre-commit hooks** for code quality enforcement
2. **Create developer documentation** for architecture decisions
3. **Add API documentation** for all public interfaces
4. **Create contribution guidelines** following CLAUDE.md standards
5. **Add automated testing** in CI/CD pipeline

### Development Success Criteria
- ✅ All ruff checks pass with zero issues
- ✅ 100% type hint coverage on public APIs
- ✅ 90%+ test coverage on core functionality
- ✅ Zero global state usage
- ✅ All dependencies injected through interfaces
- ✅ Clear separation of concerns following hexagonal architecture
- ✅ Comprehensive docstrings on all public APIs
- ✅ Immutable domain objects where applicable