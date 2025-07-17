#!/bin/bash
# Convenience script to run MCP Inspector with our server

echo "Starting MCP Inspector for RetroMCP..."
echo "This will open a web browser with the inspector interface."
echo ""

# Get the project root directory (parent of scripts directory)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Check if npm/npx is available
if ! command -v npx &> /dev/null; then
    echo "Error: npx not found. Please install Node.js first."
    echo "Install Node.js from https://nodejs.org/ or use your package manager."
    exit 1
fi

# Check if virtual environment exists
if [ ! -f "$PROJECT_ROOT/venv/bin/activate" ]; then
    echo "Error: Virtual environment not found at $PROJECT_ROOT/venv/"
    echo "Please create a virtual environment and install the package:"
    echo "  python -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install -e ."
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
source "$PROJECT_ROOT/venv/bin/activate"

# Check if Python module can be imported (now using venv Python)
if ! python -c "import retromcp.server" 2>/dev/null; then
    echo "Error: RetroMCP module not found in virtual environment."
    echo "Please install the package in the virtual environment:"
    echo "  source venv/bin/activate"
    echo "  pip install -e ."
    exit 1
fi

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

# Enable debug logging for inspector testing
export RETROMCP_LOG_LEVEL=DEBUG

echo "Debug logging enabled (RETROMCP_LOG_LEVEL=DEBUG)"
echo "Debug logs will be written to ~/.retromcp/debug.log"
echo ""

npx @modelcontextprotocol/inspector python -m retromcp.server