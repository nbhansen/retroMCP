# RetroMCP

An MCP server that connects AI assistants to Raspberry Pi systems for comprehensive system administration and RetroPie management.

RetroMCP enables AI assistants like Claude to help configure and manage Raspberry Pi systems through SSH connections. From gaming setup to system administration - ask questions in natural language instead of learning Linux commands.

## Claude Talking to Your RetroPie Setup

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
**Test Coverage**: 89% overall coverage with comprehensive testing infrastructure  

## Installation

### 1. Enable SSH on RetroPie

On your Raspberry Pi:
1. Press F4 to exit EmulationStation
2. Run: `sudo raspi-config`
3. Go to "Interface Options" → "SSH" → Enable
4. Note your Pi's IP address: `hostname -I`

### 2. Configure Secure Sudo Access

**SECURITY IMPROVEMENT**: RetroMCP now uses targeted sudo rules instead of dangerous passwordless root access.

**For standard RetroPie systems using the 'pi' user, this works automatically.**

On your RetroPie system, run the security migration script:

```bash
# Navigate to the RetroMCP directory on your RetroPie
cd /path/to/retroMCP

# Run the automated security setup
./scripts/security-migration.sh
```

This script will:
- Install secure targeted sudo rules
- Remove any dangerous passwordless sudo configurations
- Set up proper user permissions automatically

**Manual Installation (if needed):**

```bash
# Copy the secure sudoers configuration
sudo cp config/retromcp-sudoers /etc/sudoers.d/retromcp
sudo chmod 440 /etc/sudoers.d/retromcp

# Verify the configuration
sudo visudo -c
```

**What this provides:**
- ✅ Specific permissions for RetroMCP operations only
- ✅ Works automatically with standard RetroPie 'pi' user  
- ✅ No blanket root access required
- ✅ Sudo password prompts for security verification

### 3. Set Up SSH Key Authentication (Recommended)

For maximum security, use SSH key-based authentication:

```bash
# Generate SSH key pair
ssh-keygen -t rsa -b 4096 -f ~/.ssh/retromcp_key

# Copy public key to RetroPie
ssh-copy-id -i ~/.ssh/retromcp_key.pub pi@<retropie-ip>

# Set secure permissions
chmod 600 ~/.ssh/retromcp_key
chmod 644 ~/.ssh/retromcp_key.pub
```

### 4. Install RetroMCP

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

### 5. Configure Connection

```bash
# Copy example configuration
cp .env.example .env

# Edit with your Pi's details
nano .env
```

**Secure Configuration Example:**
```bash
# Required
RETROPIE_HOST=192.168.1.100
RETROPIE_USERNAME=pi  # Standard RetroPie user (recommended)

# SSH Key Authentication (Recommended)
RETROPIE_KEY_PATH=~/.ssh/retromcp_key

# OR Password Authentication (Less Secure)
# RETROPIE_PASSWORD=your_ssh_password

# Optional
RETROPIE_PORT=22
```

**Security Notes:**
- **Root user access is blocked** for security reasons
- **Standard 'pi' user works automatically** with the security configuration
- **SSH key authentication is recommended** over passwords
- System will prompt for sudo password when needed for privileged operations
- All commands are validated and restricted to specific allowed operations only

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
- **manage_gaming** - RetroPie configuration, EmulationStation, controllers, ROMs, emulators, audio/video

### Hardware Monitoring
- **manage_hardware** - Temperature monitoring, fan control, power status, GPIO operations

### Docker Management
- **manage_docker** - Container and image management, service operations

### State Management
- **manage_state** - System state persistence, backup/restore, configuration drift detection

## Security Features

RetroMCP implements comprehensive security measures:

- **No Root Access** - Root user connections are blocked entirely
- **Targeted Sudo Rules** - Only specific commands are allowed with sudo (no NOPASSWD:ALL)
- **SSH Security** - Host key verification, connection timeouts, credential cleanup
- **Input Protection** - Command injection prevention, parameter validation, path traversal blocking
- **Error Handling** - Information sanitization and secure error recovery
- **Automatic Setup** - Works with standard RetroPie 'pi' user out of the box

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
- Use the security migration script: `./scripts/security-migration.sh`
- Verify sudo configuration: `sudo visudo -c`
- For standard RetroPie 'pi' user, permissions should work automatically
- Check that `/etc/sudoers.d/retromcp` file exists

### MCP Inspector Issues
- Ensure Node.js is installed: `node --version`
- Update npm if needed: `npm install -g npm`
- Clear npm cache: `npm cache clean --force`

### Security Issues
- Verify SSH host key: `ssh-keyscan <retropie-ip> >> ~/.ssh/known_hosts`
- Check SSH key permissions: `chmod 600 ~/.ssh/retromcp_key`
- Ensure you're not using root user (this is blocked)
- Review error messages for security warnings

## Background

- **[RetroPie](https://retropie.org.uk/)** - Retro gaming platform for Raspberry Pi
- **[MCP](https://modelcontextprotocol.io/)** - Protocol enabling AI assistants to interact with external systems

## Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Complete technical architecture documentation
- **[CLAUDE.md](CLAUDE.md)** - AI assistant development guidelines

## License

MIT