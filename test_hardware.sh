#!/bin/bash
# Quick hardware monitoring tools test script

echo "🔧 Testing Hardware Monitoring Tools"
echo "===================================="

source venv/bin/activate && python -m pytest -m "hardware_tools" -v --cov=retromcp/tools/hardware_monitoring_tools --cov-report=term-missing

echo ""
echo "✅ Hardware monitoring tools test completed!"