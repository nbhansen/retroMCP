#!/bin/bash
# Quick state management tools test script

echo "🗂️ Testing State Management Tools"
echo "=================================="

source venv/bin/activate && python -m pytest -m "state_tools" -v --cov=retromcp/tools/state_tools --cov-report=term-missing

echo ""
echo "✅ State management tools test completed!"