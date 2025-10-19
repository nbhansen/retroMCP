# RetroMCP

An MCP server that connects AI assistants to Raspberry Pi systems for comprehensive system administration and RetroPie management.

RetroMCP enables AI assistants like Claude to help configure and manage Raspberry Pi systems through SSH connections. From gaming setup to system administration - ask questions in natural language instead of learning Linux commands. Also work with other LLMs, even local ones (as long as they support tool calling which is generally required for MCP so)

## Claude Talking to Your Raspberry Pi Setup

<img src="docs/screenshots/hardware-specs.png" alt="Claude analyzing Raspberry Pi hardware specifications" width="800">

*Claude analyzing your Raspberry Pi 5 hardware specifications and system information*

<img src="docs/screenshots/rom-management.png" alt="Claude managing GameCube ROMs" width="800">

*Claude discovering and managing your GameCube ROM collection*

<img src="docs/screenshots/controller-detection.png" alt="Claude detecting and testing PS5 controllers" width="800">

*Claude detecting PS5 controllers and providing configuration guidance*

## How It Works

Natural language requests are translated through Claude Desktop via MCP protocol to SSH commands executed on your Raspberry Pi.

**Examples:**
- "Set up my Xbox controller" - Installs drivers and configures button mappings
- "My N64 games are slow" - Checks performance and suggests tuning options
- "Find missing BIOS files" - Identifies required files for your emulators
- "Monitor CPU temperature" - Tracks system health and cooling performance

## Problem Solved

Raspberry Pi and RetroPie administration typically requires Linux command line expertise, manual configuration file editing, and hardware-specific knowledge. RetroMCP eliminates this by providing AI assistants with secure SSH connectivity, automatic system discovery, and comprehensive context about your specific setup.

## Key Features

- **Dynamic System Discovery** - Automatic detection of usernames, paths, and configurations
- **State Management** - Persistent system tracking with backup/restore capabilities  
- **Performance Optimization** - TTL-based caching for expensive operations
- **AI Context Sharing** - System state exposed via MCP Resources for effective troubleshooting

## Project Status

**Current Phase**: v2.0 production implementation  
**Security Status**: Comprehensive security validation  
**Test Coverage**: 93% overall coverage with comprehensive testing infrastructure  

## Installation

### 1. Enable SSH on RetroPie

On your Raspberry Pi:
1. Press F4 to exit EmulationStation
2. Run: `sudo raspi-config`
3. Go to "Interface Options" → "SSH" → Enable
4. Note your Pi's IP address: `hostname -I`

### 2. Configure Passwordless Sudo (Required)

**WARNING: This allows any user with SSH access to run any command as root without a password. Only do this if you know what that means - its probably not dangerous unless you are in the habit of handing out SSH access to your system like candy and allow people from outside your local LAN to SSH in but... be wary**

RetroMCP requires passwordless sudo for package installation, service management, and system configuration. On your RetroPie system:

```bash
# Edit sudoers file
sudo visudo

# Add this line at the end (replace 'pi' with your username):
pi ALL=(ALL) NOPASSWD:ALL

# Or for the retro user:
retro ALL=(ALL) NOPASSWD:ALL

# Save and exit (Ctrl+X, then Y, then Enter in nano)
```

### 3. Install RetroMCP

```bash
# Clone repository
git clone <repository-url>
cd retroMCP

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .
```

### 4. Configure Connection

```bash
# Copy example configuration
cp .env.example .env

# Edit with your Pi's details
nano .env
```

Required settings in `.env`:
```
RETROPIE_HOST=192.168.1.100  # Your Pi's IP address
RETROPIE_USERNAME=retro       # SSH username (auto-detected after first connection)
RETROPIE_PASSWORD=password    # SSH password
# OR
RETROPIE_SSH_KEY_PATH=~/.ssh/id_rsa  # Path to SSH key
```

## Claude Desktop Integration

### Configuration

**Config file location:**
- Mac: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

**Configuration:**
```json
{
  "mcpServers": {
    "retromcp": {
      "command": "python",
      "args": ["-m", "retromcp.server"],
      "cwd": "/absolute/path/to/retroMCP"
    }
  }
}
```

Restart Claude Desktop to load the server.

## Available Tools

### System Management
- **manage_system** - Connection testing, system info, package management, updates

### Gaming System
- **manage_gaming** - RetroPie configuration, EmulationStation, controllers, ROMs, emulators, RetroArch cores, audio/video

**RetroArch Core Management:**
- List installed RetroArch cores and their supported systems
- Get detailed core information (version, path, display name)
- View and update core-specific configuration options
- Manage emulator mappings and set default emulators per system
- Change RetroArch settings like aspect ratio, CPU core type, graphics options

**Examples:**
```
"List all installed RetroArch cores"
"Show me the configuration options for lr-mupen64plus-next"
"Change the N64 aspect ratio to 16:9"
"Set mupen64plus-GLideN64 as the default N64 emulator"
"What emulators are available for SNES?"
```

### Hardware Monitoring
- **manage_hardware** - Temperature monitoring, fan control, power status, GPIO operations

### Docker Management
- **manage_docker** - Container and image management, service operations

### State Management
- **manage_state** - System state persistence, backup/restore, configuration drift detection

## Security Features

- **SSH Security** - Host key verification, connection timeouts, credential cleanup
- **Input Protection** - Command injection prevention, parameter validation, path traversal blocking
- **Error Handling** - Information sanitization and secure error recovery

## Testing

### Test Strategy

RetroMCP uses comprehensive test-driven development with 89% code coverage:

- **Unit Tests**: Domain logic and tool functionality testing
- **Integration Tests**: End-to-end SSH and MCP protocol validation  
- **Contract Tests**: Architecture compliance and hexagonal pattern verification
- **Infrastructure Tests**: SSH repositories and external service mocking

### Running Tests

```bash
# Run all tests
make test

# Component-specific testing
make test-hardware    # Hardware monitoring tools
make test-gaming      # Gaming system tools  
make test-state       # State management tools
make test-ssh         # SSH infrastructure

# Using smart test runner
python run_tests.py --hardware --coverage
python run_tests.py --quick --gaming

# Convenience scripts
./test_hardware.sh
./test_gaming.sh
```

### MCP Inspector

```bash
# Test MCP protocol compliance
./scripts/test-inspector.sh
npx @modelcontextprotocol/inspector python -m retromcp.server
```

## Troubleshooting

### Connection Issues
- Verify SSH is enabled on the Pi
- Check firewall settings
- Ensure credentials in `.env` are correct
- Test SSH manually: `ssh pi@<your-pi-ip>`

### Permission Issues
- RetroMCP requires passwordless sudo for system operations
- Ensure your user has NOPASSWD:ALL configured in sudoers
- Check RetroPie directory ownership if file operations fail

### MCP Inspector Issues
- Ensure Node.js is installed: `node --version`
- Update npm if needed: `npm install -g npm`
- Clear npm cache: `npm cache clean --force`

### Security Issues
- Verify known_hosts file exists: `~/.ssh/known_hosts`
- Check SSH key permissions: `chmod 600 ~/.ssh/id_rsa`
- Review error messages for security warnings

## Background

- **[MCP](https://modelcontextprotocol.io/)** - Protocol enabling AI assistants to interact with external systems

## Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Complete technical architecture documentation

## License

MIT