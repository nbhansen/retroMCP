#!/usr/bin/env python3
"""Quick test script to verify MCP server setup."""

import os
import sys
from pathlib import Path


def check_env_file():
    """Check if .env file exists and has required variables."""
    env_path = Path(".env")
    if not env_path.exists():
        return False, "❌ .env file not found"
    
    # Read and check for required variables
    with open(env_path) as f:
        content = f.read()
    
    required = ["RETROPIE_HOST", "RETROPIE_USERNAME"]
    missing = [var for var in required if var not in content]
    
    if missing:
        return False, f"❌ Missing required variables: {', '.join(missing)}"
    
    # Check if credentials are set
    has_password = "RETROPIE_PASSWORD=" in content and not content.split("RETROPIE_PASSWORD=")[1].split("\n")[0].strip() == ""
    has_key = "RETROPIE_SSH_KEY_PATH=" in content and not content.split("RETROPIE_SSH_KEY_PATH=")[1].split("\n")[0].strip().startswith("~")
    
    if not (has_password or has_key):
        return True, "⚠️  .env exists but credentials may need updating"
    
    return True, "✅ .env file configured"


def check_vscode_settings():
    """Check if VS Code settings are configured."""
    settings_path = Path(".vscode/settings.json")
    if not settings_path.exists():
        return False, "❌ VS Code settings not found"
    
    with open(settings_path) as f:
        content = f.read()
    
    if "mcp.servers" in content and "retromcp" in content:
        return True, "✅ VS Code MCP settings configured"
    
    return False, "❌ VS Code settings missing MCP configuration"


def check_dependencies():
    """Check if required packages are installed."""
    try:
        import mcp
        import paramiko
        import dotenv
        return True, "✅ All dependencies installed"
    except ImportError as e:
        return False, f"❌ Missing dependency: {e.name}"


def check_virtual_env():
    """Check if running in virtual environment."""
    if sys.prefix != sys.base_prefix:
        return True, f"✅ Virtual environment active: {sys.prefix}"
    return False, "❌ Not running in virtual environment"


def main():
    """Run all checks and display status."""
    print("🔍 RetroMCP Setup Status Check\n")
    print("=" * 60)
    
    checks = [
        ("Virtual Environment", check_virtual_env()),
        ("Dependencies", check_dependencies()),
        (".env Configuration", check_env_file()),
        ("VS Code Settings", check_vscode_settings()),
    ]
    
    all_good = True
    for name, (status, message) in checks:
        print(f"\n{name:.<40} {message}")
        if not status:
            all_good = False
    
    print("\n" + "=" * 60)
    
    if all_good:
        print("\n🎉 Setup Complete! Your MCP server is ready to use.")
        print("\n📝 Next Steps:")
        print("   1. Update .env with your RetroPie credentials (if needed)")
        print("   2. Reload VS Code window (Ctrl+Shift+P -> Reload Window)")
        print("   3. Open GitHub Copilot Chat (Ctrl+Alt+I)")
        print("   4. Try: 'Test connection to my RetroPie'")
    else:
        print("\n⚠️  Some setup steps need attention (see above)")
        print("\n📚 See VSCODE_SETUP.md for detailed instructions")
    
    print()


if __name__ == "__main__":
    main()
