#!/bin/bash
# Convenience script to run MCP Inspector with our server

echo "Starting MCP Inspector for RetroMCP..."
echo "This will open a web browser with the inspector interface."
echo ""

# Check if npm/npx is available
if ! command -v npx &> /dev/null; then
    echo "Error: npx not found. Please install Node.js first."
    exit 1
fi

# Run MCP Inspector with our Python server
npx @modelcontextprotocol/inspector python -m retromcp.server