# RetroMCP

A Model Context Protocol (MCP) server for configuring and managing RetroPie on Raspberry Pi.

## What is MCP?

The [Model Context Protocol](https://modelcontextprotocol.io/) is an open protocol that enables AI assistants like Claude to interact with external systems through standardized server implementations. MCP servers expose tools and resources that AI models can use to perform actions on behalf of users.

## What is RetroPie?

[RetroPie](https://retropie.org.uk/) is a popular retro gaming platform that turns your Raspberry Pi into a retro-gaming machine. It provides a user-friendly interface to run game emulators and manage ROM collections.

## Overview

RetroMCP bridges the gap between AI assistants and RetroPie by providing MCP tools that enable:
- Remote configuration of RetroPie systems via SSH
- Automated setup of controllers and emulators
- System diagnostics and troubleshooting
- Package management and updates

Instead of manually SSH-ing into your Pi and running complex commands, you can ask an AI assistant to help configure your RetroPie system using natural language.

## Architecture

RetroMCP follows hexagonal architecture principles:

- **Domain Layer**: Core business models and interfaces (ports)
- **Application Layer**: Use cases that orchestrate business logic
- **Infrastructure Layer**: SSH implementations of domain interfaces
- **MCP Adapter**: Exposes functionality through the Model Context Protocol

## Requirements

- Python 3.8 or higher
- SSH access to a Raspberry Pi running RetroPie
- Node.js (optional, for MCP Inspector testing)

## Installation

### 1. Enable SSH on RetroPie

On your Raspberry Pi:
1. Press F4 to exit EmulationStation
2. Run: `sudo raspi-config`
3. Go to "Interface Options" → "SSH" → Enable
4. Note your Pi's IP address: `hostname -I`

### 2. Install RetroMCP

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

### 3. Configure Connection

```bash
# Copy example configuration
cp .env.example .env

# Edit with your Pi's details
nano .env
```

Required settings in `.env`:
```
RETROPIE_HOST=192.168.1.100  # Your Pi's IP address
RETROPIE_USERNAME=pi          # SSH username
RETROPIE_PASSWORD=raspberry   # SSH password
# OR
RETROPIE_SSH_KEY_PATH=~/.ssh/id_rsa  # Path to SSH key
```

## Available Tools

### System Tools
- **test_connection** - Test SSH connection to RetroPie
- **system_info** - Get system information (CPU, memory, disk, temperature)
- **install_packages** - Install system packages via apt
- **update_system** - Update system packages
- **check_bios** - Check for required BIOS files

### Controller Tools
- **detect_controllers** - Detect connected game controllers
- **setup_controller** - Install drivers and configure controller
- **test_controller** - Test controller functionality
- **configure_controller_mapping** - Configure button mappings

### RetroPie Tools
- **run_retropie_setup** - Launch RetroPie-Setup
- **install_emulator** - Install emulators
- **manage_roms** - Browse and manage ROM files
- **configure_overclock** - Adjust performance settings
- **configure_audio** - Configure audio settings

### EmulationStation Tools
- **restart_emulationstation** - Restart EmulationStation
- **configure_themes** - Manage themes
- **manage_gamelists** - Manage game lists
- **configure_es_settings** - Configure EmulationStation settings

## Testing

### MCP Inspector (Recommended)

```bash
# Run the test script
./scripts/test-inspector.sh

# Or manually with npx
npx @modelcontextprotocol/inspector python -m retromcp.server
```

In the Inspector:
1. Tools are listed on the left
2. Click a tool to see its parameters
3. Fill in parameters and click "Run"
4. View results in the response panel

### Python Test Client

```bash
python test_client.py
```

### Manual Testing

```bash
python manual_test.py
```

## Claude Desktop Integration

### Official Support
Claude Desktop officially supports macOS and Windows.

### Linux Support
For Linux users (including Fedora), community solutions are available:
- [Fedora-specific build](https://github.com/bsneed/claude-desktop-fedora) - Recommended for Fedora users
- [Universal Linux installer](https://github.com/AstroSteveo/claude-desktop-linux-installer) - Supports RHEL/Debian/Arch

### Configuration
Once Claude Desktop is installed, configure MCP support:

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

## Development

### Project Structure

```
retromcp/
├── domain/           # Business models and interfaces
│   ├── models.py     # Domain entities
│   └── ports.py      # Interface definitions
├── application/      # Use cases and business logic
│   └── use_cases.py  # Application services
├── infrastructure/   # External system implementations
│   ├── ssh_*.py      # SSH-based repositories
│   └── ...
├── tools/           # MCP tool adapters (legacy)
├── server.py        # MCP server entry point
├── container.py     # Dependency injection
└── config.py        # Configuration objects
```

### Code Quality

The project uses strict linting and formatting:

```bash
# Run linting
ruff check

# Auto-fix issues
ruff check --fix

# Format code
ruff format
```

All code must pass linting with zero errors before committing.

### Adding New Features

1. Define domain models in `domain/models.py`
2. Create interface in `domain/ports.py`
3. Implement infrastructure in `infrastructure/`
4. Add use case in `application/use_cases.py`
5. Wire up dependencies in `container.py`
6. Expose via MCP tools in `tools/`

## Troubleshooting

### Connection Issues
- Verify SSH is enabled on the Pi
- Check firewall settings
- Ensure credentials in `.env` are correct
- Test SSH manually: `ssh pi@<your-pi-ip>`

### Permission Issues
- Some operations require sudo access
- Ensure the Pi user has appropriate permissions
- Check RetroPie directory ownership

### MCP Inspector Issues
- Ensure Node.js is installed: `node --version`
- Update npm if needed: `npm install -g npm`
- Clear npm cache: `npm cache clean --force`

## License

MIT