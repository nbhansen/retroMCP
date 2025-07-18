#!/usr/bin/env python3
"""Quick test script to verify MCP server functionality."""

import asyncio
import sys

from retromcp.config import RetroPieConfig
from retromcp.config import ServerConfig
from retromcp.server import RetroMCPServer


async def test_mcp_server():
    """Test basic MCP server functionality."""
    print("🧪 Testing MCP server functionality...")

    # Create server with minimal config
    config = RetroPieConfig(host='192.168.1.100', username='test')
    server_config = ServerConfig()
    server = RetroMCPServer(config, server_config)

    print("✅ Server created successfully")

    # Test tool listing
    tools = await server.list_tools()
    print(f"✅ Found {len(tools)} tools:")
    for tool in tools:
        print(f"   - {tool.name}: {tool.description[:50]}...")

    # Test tool call (should fail gracefully)
    print("\n🔧 Testing tool call...")
    try:
        result = await server.call_tool('manage_system', {'resource': 'connection', 'action': 'test'})
        print(f"✅ Tool call completed: {result[0].text[:80]}...")
    except Exception as e:
        print(f"❌ Tool call failed: {e}")

    print("\n🎉 MCP server test completed!")
    return True

if __name__ == "__main__":
    success = asyncio.run(test_mcp_server())
    sys.exit(0 if success else 1)
