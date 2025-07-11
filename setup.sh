#!/bin/bash
# Quick setup script for RetroMCP

echo "🎮 RetroMCP Setup"
echo "=================="
echo ""

# Check Python version
python_version=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
if [ -z "$python_version" ]; then
    echo "❌ Python 3 not found. Please install Python 3.8 or later."
    exit 1
fi
echo "✅ Python $python_version found"

# Create virtual environment if not exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install package
echo "📥 Installing RetroMCP..."
pip install -e . --quiet

# Create .env from example if not exists
if [ ! -f ".env" ]; then
    echo "📋 Creating .env configuration file..."
    cp .env.example .env
    echo ""
    echo "⚠️  Please edit .env with your RetroPie connection details:"
    echo "   - RETROPIE_HOST: Your Pi's IP address"
    echo "   - RETROPIE_USERNAME: SSH username (usually 'pi')"
    echo "   - RETROPIE_PASSWORD: Your Pi's password"
    echo ""
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env with your RetroPie details"
echo "2. Run: ./scripts/test-inspector.sh"
echo "3. Test the connection to your Pi"
echo ""