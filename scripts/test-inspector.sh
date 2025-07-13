#!/bin/bash
# Convenience script to run MCP Inspector with our server

echo "Starting MCP Inspector for RetroMCP..."
echo "This will open a web browser with the inspector interface."
echo ""

# Check if npm/npx is available
if ! command -v npx &> /dev/null; then
    echo "Error: npx not found. Please install Node.js first."
    echo "Install Node.js from https://nodejs.org/ or use your package manager."
    exit 1
fi

# Check if Python module can be imported
if ! python -c "import retromcp.server" 2>/dev/null; then
    echo "Error: RetroMCP module not found."
    echo "Please run 'pip install -e .' from the project root first."
    exit 1
fi

# Get the project root directory (parent of scripts directory)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Check if .env file exists in project root
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    echo "Warning: .env file not found in project root. Inspector may fail to connect to RetroPie."
    echo "Create a .env file in $PROJECT_ROOT with your RetroPie connection details."
    echo ""
fi

echo "Launching MCP Inspector..."
echo "Press Ctrl+C to stop the inspector."
echo ""

# Change to project root and run MCP Inspector with our Python server
cd "$PROJECT_ROOT"
npx @modelcontextprotocol/inspector python -m retromcp.server