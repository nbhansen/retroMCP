#!/bin/bash
# Quick gaming system tools test script

echo "🎮 Testing Gaming System Tools"
echo "==============================="

source venv/bin/activate && python -m pytest -m "gaming_tools" -v --cov=retromcp/tools/gaming_system_tools --cov-report=term-missing

echo ""
echo "✅ Gaming system tools test completed!"