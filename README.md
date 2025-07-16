# RetroMCP

An MCP server that connects AI assistants to RetroPie systems for configuration and troubleshooting.

RetroMCP enables AI assistants like Claude to help configure and manage RetroPie installations on Raspberry Pi through SSH connections. Ask questions in natural language instead of learning Linux commands.

## Claude Talking to Your RetroPie Setup

<img src="docs/screenshots/hardware-specs.png" alt="Claude analyzing Raspberry Pi hardware specifications" width="800">

*Claude analyzing your Raspberry Pi 5 hardware specifications and system information*

<img src="docs/screenshots/rom-management.png" alt="Claude managing GameCube ROMs" width="800">

*Claude discovering and managing your GameCube ROM collection*

<img src="docs/screenshots/controller-detection.png" alt="Claude detecting and testing PS5 controllers" width="800">

*Claude detecting PS5 controllers and providing configuration guidance*

## How It Works

```mermaid
graph LR
    A[User] --> B[Claude Desktop]
    B --> C[MCP Protocol]
    C --> D[RetroMCP Server]
    D --> E[SSH Connection]
    E --> F[Raspberry Pi]
    F --> G[RetroPie System]
    
    G --> F
    F --> E
    E --> D
    D --> C
    C --> B
    B --> A
```

**Simple Flow:** Natural Language -> AI Understanding -> SSH Commands -> RetroPie Configuration

**Examples:**
- "Set up my Xbox controller" - Installs drivers and configures button mappings
- "My N64 games are slow" - Checks performance and suggests tuning options
- "Find missing BIOS files" - Identifies required files for your emulators
- "Install arcade emulators" - Sets up MAME and configures input

## The Problem This Solves

**Retro gaming on Raspberry Pi is amazing but can be frustrating:**
- Setting up controllers often requires specific drivers and configuration files
- Different emulators need different BIOS files, but which ones?
- Performance tuning requires knowledge of arcane configuration files
- Troubleshooting usually means diving into Linux command line and forums
- Every setup is slightly different, making generic guides unhelpful

**Traditional solutions require you to:**
- SSH into your Pi and run complex commands
- Navigate unfamiliar Linux file systems
- Edit configuration files by hand
- Remember (or re-learn) which packages and settings work for your specific hardware

## The RetroMCP Solution

RetroMCP turns your AI assistant into a knowledgeable helper that:
- **Connects to your Pi** - SSH security with host verification
- **Learns your specific setup** - Remembers your username, paths, and successful configurations
- **Speaks your language** - Ask questions like "Why won't my Xbox controller work?" or "Help me get N64 games running smoothly"
- **Provides contextual guidance** - The AI gets full context about your system and can troubleshoot effectively
- **Adapts automatically** - Works with standard setups and custom configurations alike

## Key Features

### **Dynamic System Discovery**
- Automatically detects username (pi/retro/custom)
- Discovers RetroPie installation paths
- Identifies EmulationStation process type (systemd vs user)
- No hardcoded assumptions about your setup

### **Persistent System Memory**
- Stores system state (hardware, emulators, controllers, ROMs) in `/home/{user}/.retropie-state.json`
- Remembers successful configurations and troubleshooting solutions
- Tracks configuration changes over time
- Enables faster problem-solving across sessions

### **Intelligent State Management**
- **Load state**: Instantly recall your system configuration
- **Save state**: Capture current system state after changes
- **Compare state**: Detect configuration drift and changes
- **Update state**: Modify specific configuration values

### **AI Context Sharing**
- Exposes system state via MCP Resources
- Claude gets context about your specific setup
- Enables more effective troubleshooting conversations
- Remembers past issues and resolutions

## Project Status

**Current Phase**: Functional implementation  
**Security Status**: Security validation implemented  
**Test Coverage**: 84% (434 tests passing)  

## Installation

### 1. Enable SSH on RetroPie

On your Raspberry Pi:
1. Press F4 to exit EmulationStation
2. Run: `sudo raspi-config`
3. Go to "Interface Options" → "SSH" → Enable
4. Note your Pi's IP address: `hostname -I`

### 2. Configure Passwordless Sudo (Required)

**WARNING: This allows any user with SSH access to run any command as root without a password. Only do this on dedicated gaming systems.**

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
- **manage_system** - System operations (connection test, info, packages, updates)
  - `connection` - Test SSH connection to RetroPie
  - `info` - Get system information (CPU, memory, disk, temperature)
  - `package` - Install system packages via apt
  - `update` - Update system packages

### Gaming System
- **manage_gaming** - Gaming operations (retropie, emulationstation, controllers, roms, emulators, audio, video)
  - `retropie` - RetroPie setup and configuration
  - `emulationstation` - EmulationStation configuration and management
  - `controller` - Detect, setup, test, and configure controllers
  - `roms` - Scan, list, and configure ROM files
  - `emulator` - Install, configure, and test emulators
  - `audio` - Configure audio settings
  - `video` - Configure video settings

### Hardware Monitoring
- **manage_hardware** - Hardware operations (temperature, fan, power, gpio)
  - `temperature` - Monitor CPU/GPU temperatures and thermal throttling
  - `fan` - Check fan operation and cooling system
  - `power` - Monitor power health and under-voltage warnings
  - `gpio` - GPIO pin status and configuration

### Docker Management
- **manage_docker** - Docker operations (containers, images, services)
  - `container` - Container lifecycle management
  - `image` - Image management and cleanup
  - `service` - Docker service operations

### State Management
- **manage_state** - Load, save, update, and compare system state
  - `load` - Retrieve cached system configuration
  - `save` - Scan and persist current state
  - `update` - Modify specific configuration field
  - `compare` - Detect configuration drift

## Security Features

### SSH Security
- **Host Key Verification**: Proper known_hosts verification
- **Connection Timeouts**: Prevents hanging connections
- **Credential Cleanup**: Clears passwords from memory after use

### Command Injection Prevention
- **Input Escaping**: All user inputs escaped with `shlex.quote()`
- **Input Validation**: Validation for all parameters
- **Path Traversal Prevention**: Blocks directory traversal attempts

### Error Handling
- **Information Sanitization**: Removes sensitive data from error messages
- **Error Recovery**: Proper error handling and user feedback

## Testing

### MCP Inspector (Recommended)

```bash
# Run the test script
./scripts/test-inspector.sh

# Or manually with npx
npx @modelcontextprotocol/inspector python -m retromcp.server
```

### Quick Setup

```bash
./setup.sh
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

## What is RetroPie?

[RetroPie](https://retropie.org.uk/) is a popular retro gaming platform that turns your Raspberry Pi into a retro-gaming machine. It provides a user-friendly interface to run game emulators for classic consoles like NES, SNES, PlayStation, N64, and dozens more.

## What is MCP?

The [Model Context Protocol](https://modelcontextprotocol.io/) is an open protocol that enables AI assistants like Claude to interact with external systems through standardized server implementations. MCP servers expose tools and resources that AI models can use to perform actions on behalf of users.

## Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Complete technical architecture documentation
- **[CLAUDE.md](CLAUDE.md)** - AI assistant development guidelines

## License

MIT