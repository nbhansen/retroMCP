#!/usr/bin/env python3
"""Simple test client for the RetroMCP server."""

import asyncio
import json

from mcp import ClientSession
from mcp import StdioServerParameters
from mcp.client.stdio import stdio_client


async def test_server() -> None:
    """Test the MCP server with basic requests."""
    # Create server parameters for stdio connection
    server_params = StdioServerParameters(
        command="python", args=["-m", "retromcp.server"], env=None
    )

    # Connect to the server
    async with stdio_client(server_params) as (read, write), ClientSession(
        read, write
    ) as session:
        # Initialize the connection
        await session.initialize()

        print("Connected to RetroMCP server!")
        print(f"Server: {session.server_info.name} v{session.server_info.version}")
        print()

        # List available tools
        tools = await session.list_tools()
        print("Available tools:")
        for tool in tools:
            print(f"  - {tool.name}: {tool.description}")
        print()

        # Test the hello tool
        print("Testing 'hello' tool...")
        result = await session.call_tool("hello", {"name": "RetroPie User"})
        print(f"Response: {result.content[0].text}")
        print()

        # Test the get_retropie_info tool
        print("Testing 'get_retropie_info' tool...")
        result = await session.call_tool("get_retropie_info", {})
        info = json.loads(result.content[0].text)
        print("RetroMCP Info:")
        print(json.dumps(info, indent=2))


if __name__ == "__main__":
    asyncio.run(test_server())
