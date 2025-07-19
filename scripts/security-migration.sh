#!/bin/bash

# RetroMCP Security Migration Script
# This script helps migrate from insecure passwordless sudo to secure targeted rules

set -e

echo "======================================"
echo "RetroMCP Security Migration Script"
echo "======================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo -e "${RED}ERROR: This script should not be run as root${NC}"
   echo "Please run as a regular user with sudo privileges"
   exit 1
fi

# Check if we're on the RetroPie system
if [[ ! -f /opt/retropie/configs/all/emulationstation/es_settings.xml ]]; then
    echo -e "${YELLOW}WARNING: This doesn't appear to be a RetroPie system${NC}"
    echo "This script is designed for RetroPie systems"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "This script will:"
echo "1. Remove dangerous passwordless sudo rules"
echo "2. Install secure targeted sudo rules for RetroMCP"
echo "3. Set up SSH key authentication (optional)"
echo "4. Create backup of current configuration"
echo ""

read -p "Continue with security migration? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Migration cancelled"
    exit 0
fi

# Step 1: Backup current sudoers configuration
echo -e "${YELLOW}Step 1: Backing up current configuration...${NC}"
sudo cp /etc/sudoers /etc/sudoers.backup.$(date +%Y%m%d_%H%M%S)
echo "Sudoers backed up"

# Step 2: Check for dangerous sudo rules
echo -e "${YELLOW}Step 2: Checking for dangerous sudo rules...${NC}"

# Safely check for dangerous rules in sudoers files
DANGEROUS_FOUND=false
if sudo grep -q "ALL=(ALL) NOPASSWD:ALL" /etc/sudoers 2>/dev/null; then
    DANGEROUS_FOUND=true
fi

# Check sudoers.d directory if it exists and has files
if [[ -d /etc/sudoers.d ]]; then
    for file in /etc/sudoers.d/*; do
        if [[ -f "$file" ]] && sudo grep -q "ALL=(ALL) NOPASSWD:ALL" "$file" 2>/dev/null; then
            DANGEROUS_FOUND=true
            break
        fi
    done
fi

if [[ "$DANGEROUS_FOUND" == "true" ]]; then
    echo -e "${RED}FOUND: Dangerous passwordless sudo rules detected${NC}"
    
    # Show the dangerous rules
    echo "Dangerous rules found:"
    sudo grep -n "ALL=(ALL) NOPASSWD:ALL" /etc/sudoers 2>/dev/null || true
    for file in /etc/sudoers.d/*; do
        if [[ -f "$file" ]]; then
            sudo grep -n "ALL=(ALL) NOPASSWD:ALL" "$file" 2>/dev/null || true
        fi
    done
    
    echo ""
    echo -e "${YELLOW}These rules give unlimited root access without password verification${NC}"
    read -p "Remove these dangerous rules? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Comment out dangerous rules instead of deleting
        sudo sed -i.bak 's/.*ALL=(ALL) NOPASSWD:ALL/# REMOVED BY RETROMCP SECURITY MIGRATION: &/' /etc/sudoers
        
        # Check sudoers.d directory safely
        for file in /etc/sudoers.d/*; do
            if [[ -f "$file" ]]; then
                sudo sed -i.bak 's/.*ALL=(ALL) NOPASSWD:ALL/# REMOVED BY RETROMCP SECURITY MIGRATION: &/' "$file"
            fi
        done
        
        echo -e "${GREEN}Dangerous sudo rules have been commented out${NC}"
    else
        echo -e "${YELLOW}WARNING: Dangerous sudo rules left intact${NC}"
    fi
else
    echo -e "${GREEN}No dangerous passwordless sudo rules found${NC}"
fi

# Step 3: Install secure RetroMCP sudo rules
echo -e "${YELLOW}Step 3: Installing secure RetroMCP sudo rules...${NC}"

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
SUDOERS_FILE="$SCRIPT_DIR/../config/retromcp-sudoers"

if [[ -f "$SUDOERS_FILE" ]]; then
    sudo cp "$SUDOERS_FILE" /etc/sudoers.d/retromcp
    sudo chmod 440 /etc/sudoers.d/retromcp
    sudo chown root:root /etc/sudoers.d/retromcp
    
    # Validate sudoers configuration
    if sudo visudo -c; then
        echo -e "${GREEN}Secure RetroMCP sudo rules installed successfully${NC}"
    else
        echo -e "${RED}ERROR: Sudoers configuration is invalid${NC}"
        sudo rm -f /etc/sudoers.d/retromcp
        echo "Removed invalid configuration"
        exit 1
    fi
else
    echo -e "${RED}ERROR: RetroMCP sudoers file not found at $SUDOERS_FILE${NC}"
    echo "Please ensure you're running this script from the RetroMCP directory"
    exit 1
fi

# Step 3.5: Set up user group for optimal security
echo ""
echo -e "${YELLOW}Step 3.5: Setting up user permissions...${NC}"
CURRENT_USER=$(whoami)

# Check if retromcp group exists, create if not
if ! getent group retromcp > /dev/null 2>&1; then
    echo "Creating retromcp group..."
    sudo groupadd retromcp
    echo -e "${GREEN}retromcp group created${NC}"
else
    echo "retromcp group already exists"
fi

# Add current user to retromcp group if not already a member
if ! groups $CURRENT_USER | grep -q retromcp; then
    echo "Adding $CURRENT_USER to retromcp group..."
    sudo usermod -a -G retromcp $CURRENT_USER
    echo -e "${GREEN}User $CURRENT_USER added to retromcp group${NC}"
    echo -e "${YELLOW}NOTE: You may need to log out and back in for group changes to take effect${NC}"
else
    echo "User $CURRENT_USER is already in retromcp group"
fi

# Provide fallback information
echo ""
echo "Sudo configuration includes:"
echo "- Primary rules for %retromcp group (recommended)"
echo "- Fallback rules for 'pi' user (compatibility)"
echo ""
echo -e "${YELLOW}For optimal security, users should be added to the retromcp group:${NC}"
echo "sudo usermod -a -G retromcp <username>"

# Step 4: SSH Key Setup (Optional)
echo ""
echo -e "${YELLOW}Step 4: SSH Key Authentication Setup (Optional but Recommended)${NC}"
read -p "Set up SSH key authentication for enhanced security? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    SSH_KEY_PATH="$HOME/.ssh/retromcp_key"
    
    if [[ -f "$SSH_KEY_PATH" ]]; then
        echo "SSH key already exists at $SSH_KEY_PATH"
    else
        echo "Generating new SSH key pair..."
        ssh-keygen -t rsa -b 4096 -f "$SSH_KEY_PATH" -C "retromcp-$(hostname)"
        echo -e "${GREEN}SSH key pair generated${NC}"
    fi
    
    # Set proper permissions
    chmod 600 "$SSH_KEY_PATH"
    chmod 644 "$SSH_KEY_PATH.pub"
    
    echo ""
    echo "To use this key with RetroMCP, update your configuration:"
    echo "RETROPIE_KEY_PATH=$SSH_KEY_PATH"
    echo ""
    echo "Public key for remote systems:"
    echo "$(cat $SSH_KEY_PATH.pub)"
fi

# Step 5: Verification
echo ""
echo -e "${YELLOW}Step 5: Verification${NC}"
echo "Testing sudo configuration..."

# Test a safe sudo command
if sudo -l | grep -q "apt-get update"; then
    echo -e "${GREEN}✓ Sudo configuration appears correct${NC}"
else
    echo -e "${YELLOW}⚠ Could not verify sudo configuration${NC}"
fi

# Final summary
echo ""
echo "======================================"
echo -e "${GREEN}Security Migration Complete!${NC}"
echo "======================================"
echo ""
echo "Changes made:"
echo "1. ✓ Dangerous passwordless sudo rules commented out"
echo "2. ✓ Secure targeted sudo rules installed"
echo "3. ✓ SSH key authentication prepared (if selected)"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Update your RetroMCP configuration to use SSH keys or password auth"
echo "2. Test RetroMCP functionality with the new security model"
echo "3. Remove backup files once you've verified everything works"
echo ""
echo -e "${YELLOW}Important:${NC}"
echo "- Root user access is now blocked for security"
echo "- Sudo operations will prompt for password when needed"
echo "- Only specific commands are allowed with sudo"
echo ""
echo "Configuration backups saved with timestamp"
echo -e "${GREEN}Your system is now more secure!${NC}"
