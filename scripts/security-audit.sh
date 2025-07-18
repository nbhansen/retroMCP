#!/bin/bash

# RetroMCP Security Audit Script
# This script checks for security vulnerabilities and compliance

set -e

echo "======================================"
echo "RetroMCP Security Audit"
echo "======================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

AUDIT_SCORE=0
TOTAL_CHECKS=0
ISSUES_FOUND=0

# Function to perform a security check
security_check() {
    local test_name="$1"
    local command="$2"
    local expected_result="$3"
    local issue_description="$4"
    local recommendation="$5"
    
    ((TOTAL_CHECKS++))
    echo -n "[$TOTAL_CHECKS] Checking $test_name... "
    
    if eval "$command"; then
        if [[ "$expected_result" == "pass" ]]; then
            echo -e "${GREEN}PASS${NC}"
            ((AUDIT_SCORE++))
        else
            echo -e "${RED}FAIL${NC}"
            ((ISSUES_FOUND++))
            echo -e "    ${RED}Issue:${NC} $issue_description"
            echo -e "    ${BLUE}Fix:${NC} $recommendation"
            echo ""
        fi
    else
        if [[ "$expected_result" == "fail" ]]; then
            echo -e "${GREEN}PASS${NC}"
            ((AUDIT_SCORE++))
        else
            echo -e "${RED}FAIL${NC}"
            ((ISSUES_FOUND++))
            echo -e "    ${RED}Issue:${NC} $issue_description"
            echo -e "    ${BLUE}Fix:${NC} $recommendation"
            echo ""
        fi
    fi
}

echo "Running security audit checks..."
echo ""

# Check 1: Passwordless sudo rules
security_check \
    "for dangerous passwordless sudo rules" \
    "! sudo grep -q 'ALL=(ALL) NOPASSWD:ALL' /etc/sudoers /etc/sudoers.d/* 2>/dev/null" \
    "pass" \
    "Dangerous passwordless sudo rules found" \
    "Run ./scripts/security-migration.sh to fix"

# Check 2: Root SSH access
security_check \
    "that root SSH login is disabled" \
    "! sudo sshd -T | grep -q 'permitrootlogin yes'" \
    "pass" \
    "Root SSH login may be enabled" \
    "Edit /etc/ssh/sshd_config: PermitRootLogin no"

# Check 3: SSH key permissions
if [[ -f ~/.ssh/id_rsa ]]; then
    security_check \
        "SSH private key permissions" \
        "[[ \$(stat -c '%a' ~/.ssh/id_rsa) == '600' ]]" \
        "pass" \
        "SSH private key has insecure permissions" \
        "chmod 600 ~/.ssh/id_rsa"
fi

# Check 4: RetroMCP sudoers file exists
security_check \
    "for RetroMCP sudoers configuration" \
    "[[ -f /etc/sudoers.d/retromcp ]]" \
    "pass" \
    "RetroMCP sudoers file not found" \
    "Install with: sudo cp config/retromcp-sudoers /etc/sudoers.d/retromcp"

# Check 5: Sudoers file permissions
if [[ -f /etc/sudoers.d/retromcp ]]; then
    security_check \
        "RetroMCP sudoers file permissions" \
        "[[ \$(stat -c '%a' /etc/sudoers.d/retromcp) == '440' ]]" \
        "pass" \
        "Sudoers file has incorrect permissions" \
        "sudo chmod 440 /etc/sudoers.d/retromcp"
fi

# Check 6: Configuration file security
if [[ -f .env ]]; then
    security_check \
        "that .env file doesn't contain root username" \
        "! grep -iq 'RETROPIE_USERNAME=root' .env" \
        "pass" \
        "Configuration uses root username" \
        "Change RETROPIE_USERNAME to a non-privileged user (e.g., pi)"
        
    security_check \
        "for SSH key authentication preference" \
        "grep -q 'RETROPIE_KEY_PATH' .env && ! grep -q '^RETROPIE_PASSWORD=' .env" \
        "pass" \
        "Using password authentication instead of SSH keys" \
        "Set up SSH key authentication for better security"
fi

# Check 7: Known hosts file
security_check \
    "for SSH known_hosts file" \
    "[[ -f ~/.ssh/known_hosts ]]" \
    "pass" \
    "SSH known_hosts file not found" \
    "Create known_hosts file to prevent MITM attacks"

# Check 8: SSH agent forwarding
security_check \
    "that SSH agent forwarding is disabled in config" \
    "! grep -q 'ForwardAgent yes' ~/.ssh/config 2>/dev/null" \
    "pass" \
    "SSH agent forwarding is enabled" \
    "Disable ForwardAgent in ~/.ssh/config"

# Check 9: Password authentication in SSH config
security_check \
    "SSH password authentication settings" \
    "sudo sshd -T | grep -q 'passwordauthentication no' || echo 'warning'" \
    "fail" \
    "Password authentication should be disabled when using keys" \
    "Set PasswordAuthentication no in /etc/ssh/sshd_config"

# Check 10: File system permissions
security_check \
    "that /tmp has proper mount options" \
    "mount | grep -q '/tmp.*noexec'" \
    "pass" \
    "/tmp filesystem allows execution" \
    "Mount /tmp with noexec option"

echo ""
echo "======================================"
echo "Security Audit Results"
echo "======================================"
echo ""

# Calculate score percentage
SCORE_PERCENTAGE=$((AUDIT_SCORE * 100 / TOTAL_CHECKS))

echo "Checks passed: $AUDIT_SCORE/$TOTAL_CHECKS ($SCORE_PERCENTAGE%)"
echo "Issues found: $ISSUES_FOUND"
echo ""

# Provide overall assessment
if [[ $SCORE_PERCENTAGE -ge 90 ]]; then
    echo -e "${GREEN}✓ Excellent security posture${NC}"
elif [[ $SCORE_PERCENTAGE -ge 80 ]]; then
    echo -e "${YELLOW}⚠ Good security with minor issues${NC}"
elif [[ $SCORE_PERCENTAGE -ge 60 ]]; then
    echo -e "${YELLOW}⚠ Moderate security - improvements needed${NC}"
else
    echo -e "${RED}✗ Poor security - immediate action required${NC}"
fi

echo ""
echo "Security recommendations:"
echo "1. Use SSH key authentication instead of passwords"
echo "2. Disable root login and use non-privileged users"
echo "3. Implement targeted sudo rules instead of NOPASSWD:ALL"
echo "4. Enable SSH host key verification"
echo "5. Regularly update the system and review configurations"
echo ""

if [[ $ISSUES_FOUND -gt 0 ]]; then
    echo -e "${YELLOW}Run the security migration script to fix common issues:${NC}"
    echo "./scripts/security-migration.sh"
    echo ""
fi

echo "Audit completed at $(date)"
exit $ISSUES_FOUND
