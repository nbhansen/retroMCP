#!/bin/bash

# RetroMCP User Permissions Verification Script
# This script checks if the current user can run the required sudo commands

set -e

echo "======================================"
echo "RetroMCP User Permissions Verification"
echo "======================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

CURRENT_USER=$(whoami)
echo "Checking permissions for user: $CURRENT_USER"
echo ""

# Test if user is in retromcp group
echo -e "${YELLOW}Checking group membership...${NC}"
if groups $CURRENT_USER | grep -q retromcp; then
    echo -e "${GREEN}✓ User is in retromcp group${NC}"
    GROUP_STATUS="retromcp"
elif [ "$CURRENT_USER" = "pi" ]; then
    echo -e "${GREEN}✓ User is 'pi' (fallback rules available)${NC}"
    GROUP_STATUS="pi"
else
    echo -e "${RED}✗ User is not in retromcp group and is not 'pi' user${NC}"
    echo -e "${YELLOW}To fix this, run: sudo usermod -a -G retromcp $CURRENT_USER${NC}"
    GROUP_STATUS="none"
fi

echo ""

# Test key sudo commands that RetroMCP tools need
echo -e "${YELLOW}Testing sudo command permissions...${NC}"

COMMANDS=(
    "apt update"
    "systemctl status networking"
    "vcgencmd measure_temp"
    "killall -0 emulationstation"  # Test with -0 (just check if process exists)
)

PASSED=0
TOTAL=${#COMMANDS[@]}

for cmd in "${COMMANDS[@]}"; do
    echo -n "Testing: sudo $cmd ... "
    if sudo -l 2>/dev/null | grep -q "$(echo $cmd | cut -d' ' -f1)"; then
        echo -e "${GREEN}✓ Allowed${NC}"
        ((PASSED++))
    else
        echo -e "${RED}✗ Not allowed${NC}"
    fi
done

echo ""
echo -e "${YELLOW}Permission Test Results:${NC}"
echo "Passed: $PASSED/$TOTAL commands"

if [ $PASSED -eq $TOTAL ]; then
    echo -e "${GREEN}✓ All required sudo commands are available${NC}"
    echo -e "${GREEN}✓ RetroMCP should work correctly with current permissions${NC}"
elif [ $PASSED -gt 0 ]; then
    echo -e "${YELLOW}⚠ Some commands may not work correctly${NC}"
    echo "Consider running the security migration script"
else
    echo -e "${RED}✗ Most commands will fail${NC}"
    echo -e "${RED}Please run the security migration script: ./scripts/security-migration.sh${NC}"
fi

echo ""

# Check if sudoers file is installed
echo -e "${YELLOW}Checking sudoers configuration...${NC}"
if [ -f /etc/sudoers.d/retromcp ]; then
    echo -e "${GREEN}✓ RetroMCP sudoers file is installed${NC}"
else
    echo -e "${RED}✗ RetroMCP sudoers file not found${NC}"
    echo "Run: ./scripts/security-migration.sh to install it"
fi

echo ""

# Final recommendations
echo -e "${YELLOW}Recommendations:${NC}"
if [ "$GROUP_STATUS" = "none" ]; then
    echo "1. Add user to retromcp group: sudo usermod -a -G retromcp $CURRENT_USER"
    echo "2. Log out and back in to refresh group membership"
    echo "3. Re-run this verification script"
elif [ "$GROUP_STATUS" = "pi" ]; then
    echo "1. Current setup should work (using pi user fallback rules)"
    echo "2. For better security, consider adding user to retromcp group"
else
    echo "1. ✓ User permissions look good"
    echo "2. ✓ RetroMCP should work correctly"
fi

echo ""
echo "======================================"
echo -e "${GREEN}Verification Complete${NC}"
echo "======================================"
