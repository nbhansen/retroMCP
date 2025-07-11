#!/usr/bin/env python3
"""Manual testing script that sends JSON-RPC messages to the MCP server."""

import json
import subprocess
import sys
from typing import Any
from typing import Dict


def send_message(
    proc: subprocess.Popen[str], message: Dict[str, Any]
) -> Dict[str, Any]:
    """Send a JSON-RPC message to the server."""
    json_str = json.dumps(message)
    proc.stdin.write(json_str + "\n")
    proc.stdin.flush()

    # Read response
    response = proc.stdout.readline()
    return json.loads(response)


def main() -> None:
    """Run the manual test client."""
    # Start the MCP server
    proc = subprocess.Popen(
        [sys.executable, "-m", "retromcp.server"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    try:
        # Send initialize request
        print("Sending initialize request...")
        init_request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "0.1.0",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"},
            },
            "id": 1,
        }
        response = send_message(proc, init_request)
        print(f"Initialize response: {json.dumps(response, indent=2)}\n")

        # Send initialized notification
        init_notification = {"jsonrpc": "2.0", "method": "initialized"}
        proc.stdin.write(json.dumps(init_notification) + "\n")
        proc.stdin.flush()

        # List tools
        print("Listing tools...")
        list_tools = {"jsonrpc": "2.0", "method": "tools/list", "params": {}, "id": 2}
        response = send_message(proc, list_tools)
        print(f"Tools: {json.dumps(response, indent=2)}\n")

        # Call hello tool
        print("Calling hello tool...")
        call_hello = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "hello", "arguments": {"name": "Test User"}},
            "id": 3,
        }
        response = send_message(proc, call_hello)
        print(f"Hello response: {json.dumps(response, indent=2)}\n")

        # Call get_retropie_info tool
        print("Calling get_retropie_info tool...")
        call_info = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "get_retropie_info", "arguments": {}},
            "id": 4,
        }
        response = send_message(proc, call_info)
        print(f"Info response: {json.dumps(response, indent=2)}\n")

    finally:
        proc.terminate()
        proc.wait()


if __name__ == "__main__":
    main()
