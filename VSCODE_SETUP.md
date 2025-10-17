# VS Code MCP Server Setup Guide

## Quick Start

Your RetroMCP server is now configured for VS Code! Here's what was set up:

### 1. VS Code Configuration Created

The `.vscode/settings.json` file has been configured with your MCP server:

```json
{
  "mcp.servers": {
    "retromcp": {
      "command": "python",
      "args": ["-m", "retromcp.server"],
      "cwd": "${workspaceFolder}",
      "env": {
        "PYTHONPATH": "${workspaceFolder}"
      }
    }
  }
}
```

### 2. Required Setup Steps

Before using the MCP server, complete these steps:

#### A. Create Your `.env` File

```bash
# Copy the example file
cp .env.example .env

# Edit with your RetroPie details
nano .env
```

Configure the following required variables in `.env`:

```bash
RETROPIE_HOST=192.168.1.100        # Your Pi's IP address
RETROPIE_USERNAME=retro             # SSH username
RETROPIE_PASSWORD=your_password     # SSH password
# OR use SSH key instead:
# RETROPIE_SSH_KEY_PATH=~/.ssh/id_rsa

# Optional: Set log level
RETROMCP_LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

#### B. Install Python Dependencies

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Linux/Mac

# Install in development mode
pip install -e .

# Or install with dev dependencies for testing
pip install -e ".[dev]"
```

#### C. Configure Passwordless Sudo (Required)

On your RetroPie system, run:

```bash
sudo visudo

# Add this line (replace 'retro' with your username):
retro ALL=(ALL) NOPASSWD:ALL

# Save and exit
```

⚠️ **Security Note**: This allows passwordless sudo for the specified user. Only do this if you understand the security implications.

### 3. Using the MCP Server in VS Code

#### With GitHub Copilot Chat

Once configured, you can interact with your RetroPie through GitHub Copilot Chat:

1. Open Copilot Chat (Ctrl+Alt+I or Cmd+Alt+I)
2. The MCP server will be available as a tool provider
3. Ask questions like:
   - "Test connection to my RetroPie"
   - "What's the CPU temperature?"
   - "Detect my game controllers"
   - "List all ROMs for Nintendo 64"
   - "Install the GameCube emulator"

#### Available Tool Categories

🔧 **System Management**
- Connection testing and system info
- Package installation and updates
- File management
- Service management

🎮 **Gaming System**
- Controller detection and setup
- ROM management
- Emulator installation
- EmulationStation configuration

🔬 **Hardware Monitoring**
- Temperature monitoring
- CPU/Memory/Disk usage
- Fan control
- Power supply status

🐳 **Docker Management**
- Container management
- Image operations

💾 **State Management**
- System state backup/restore
- Configuration tracking

### 4. Testing Your Setup

Test the MCP server from the command line:

```bash
# Activate your virtual environment first
source venv/bin/activate

# Run the server
python -m retromcp.server

# Or use the installed command
retromcp
```

Press Ctrl+C to stop.

### 5. Troubleshooting

#### Connection Issues
```bash
# Test SSH manually
ssh retro@192.168.1.100

# Check if SSH is enabled on Pi
# On the Pi: sudo raspi-config -> Interface Options -> SSH
```

#### MCP Server Not Appearing in VS Code
1. Reload VS Code window: Ctrl+Shift+P -> "Developer: Reload Window"
2. Check VS Code output: View -> Output -> Select "MCP" from dropdown
3. Verify `.vscode/settings.json` syntax is valid

#### Python Environment Issues
```bash
# Verify Python version (requires 3.8+)
python --version

# Reinstall dependencies
pip install --force-reinstall -e .
```

#### Permission Errors
- Ensure your user has passwordless sudo configured
- Check file permissions: `ls -la ~/.retromcp/`
- Verify SSH key permissions: `chmod 600 ~/.ssh/id_rsa`

### 6. Development and Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run specific test categories
pytest -m unit
pytest -m integration
pytest -m hardware_tools

# With coverage
pytest --cov=retromcp --cov-report=html
```

### 7. Advanced Configuration

#### Custom Python Environment

If you're using a specific Python interpreter:

```json
{
  "mcp.servers": {
    "retromcp": {
      "command": "/path/to/your/venv/bin/python",
      "args": ["-m", "retromcp.server"],
      "cwd": "${workspaceFolder}"
    }
  }
}
```

#### Debug Mode

Enable debug logging in your `.env`:

```bash
RETROMCP_LOG_LEVEL=DEBUG
```

Debug logs will be written to `~/.retromcp/debug.log`

### 8. Resources

- **Architecture Documentation**: See `ARCHITECTURE.md`
- **Full README**: See `README.md`
- **MCP Protocol**: https://modelcontextprotocol.io/
- **Issue Tracker**: Report issues on GitHub

## Next Steps

1. ✅ VS Code settings configured
2. ⏳ Create and configure `.env` file
3. ⏳ Install Python dependencies
4. ⏳ Configure passwordless sudo on RetroPie
5. ⏳ Test the connection
6. ⏳ Start using in Copilot Chat!

Happy coding! 🎮
