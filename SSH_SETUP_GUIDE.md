# SSH Passwordless Access Setup Guide

## Problem
Your Raspberry Pi is configured to only accept public key authentication (`publickey` only), which means password authentication is disabled. You need to set up SSH key-based authentication.

## Solution: Set Up SSH Key Authentication

### Step 1: Generate SSH Key Pair (On Your Fedora Machine)

```bash
# Generate a new SSH key pair
ssh-keygen -t ed25519 -C "nbhansen@fedora"

# When prompted:
# - File location: Press Enter (use default: ~/.ssh/id_ed25519)
# - Passphrase: Press Enter twice for no passphrase (or set one for extra security)
```

This creates two files:
- `~/.ssh/id_ed25519` - Your private key (keep this secret!)
- `~/.ssh/id_ed25519.pub` - Your public key (safe to share)

### Step 2: Copy Your Public Key to the Raspberry Pi

Since password authentication is disabled, you'll need physical or alternate access to your Pi to add your key.

#### Option A: Physical Access to Raspberry Pi (Recommended)

1. **On the Raspberry Pi** (keyboard/monitor or via another method):

```bash
# Login to your Pi directly
# Then run these commands:

# Create .ssh directory if it doesn't exist
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# Create or edit the authorized_keys file
nano ~/.ssh/authorized_keys
```

2. **On your Fedora machine**, copy your public key:

```bash
# Display your public key
cat ~/.ssh/id_ed25519.pub
```

3. **Copy the output** and paste it into the `authorized_keys` file on the Pi

4. **On the Pi**, set correct permissions:

```bash
chmod 600 ~/.ssh/authorized_keys
```

#### Option B: If You Have SD Card Access

1. Remove SD card from Pi and insert into your Fedora machine
2. Mount the SD card
3. Navigate to the home directory: `/home/nbhansen/.ssh/` on the SD card
4. Add your public key to `authorized_keys` file
5. Ensure permissions: `chmod 700 .ssh && chmod 600 .ssh/authorized_keys`
6. Unmount and return SD card to Pi

#### Option C: Enable Password Authentication Temporarily

If you have physical access to the Pi:

1. **On the Raspberry Pi**, edit SSH config:
```bash
sudo nano /etc/ssh/sshd_config
```

2. Find and modify these lines:
```bash
# Change from:
PasswordAuthentication no

# To:
PasswordAuthentication yes
```

3. Restart SSH:
```bash
sudo systemctl restart sshd
```

4. **From your Fedora machine**, now you can use `ssh-copy-id`:
```bash
ssh-copy-id nbhansen@192.168.1.142
```

5. **Back on the Pi**, disable password authentication again:
```bash
sudo nano /etc/ssh/sshd_config
# Set: PasswordAuthentication no
sudo systemctl restart sshd
```

### Step 3: Test SSH Connection

```bash
# From your Fedora machine
ssh nbhansen@192.168.1.142

# Should connect without asking for password!
```

### Step 4: Update Your .env File

Once SSH key authentication is working, update your `.env` file:

```bash
RETROPIE_HOST=192.168.1.142
RETROPIE_USERNAME=nbhansen
# Leave password empty since using key auth
RETROPIE_PASSWORD=
RETROPIE_SSH_KEY_PATH=/home/nbhansen/.ssh/id_ed25519
RETROPIE_PORT=22
```

## Alternative: Use Password Authentication in RetroMCP

If you prefer to enable password authentication on your Pi permanently:

### On the Raspberry Pi:

1. Edit SSH config:
```bash
sudo nano /etc/ssh/sshd_config
```

2. Ensure these settings:
```bash
PasswordAuthentication yes
PermitRootLogin no
PubkeyAuthentication yes  # Keep key auth enabled too
```

3. Restart SSH:
```bash
sudo systemctl restart sshd
```

4. Set/change your password if needed:
```bash
passwd
```

### In Your .env File:

```bash
RETROPIE_HOST=192.168.1.142
RETROPIE_USERNAME=nbhansen
RETROPIE_PASSWORD=your_actual_password
RETROPIE_SSH_KEY_PATH=
RETROPIE_PORT=22
```

## Troubleshooting

### "Permission denied (publickey)"
- Your public key is not in `~/.ssh/authorized_keys` on the Pi
- Wrong permissions on `.ssh/` or `authorized_keys` file
- Wrong username (use the actual Pi username)

### Check SSH Configuration on Pi:
```bash
# On the Pi, check what auth methods are enabled
sudo cat /etc/ssh/sshd_config | grep -E "PasswordAuthentication|PubkeyAuthentication"
```

### Debug SSH Connection:
```bash
# Verbose SSH output to see what's happening
ssh -v nbhansen@192.168.1.142
```

### Verify Key Permissions:
```bash
# On Fedora (should be 600 for private key)
ls -la ~/.ssh/id_ed25519

# On Pi (should be 700 for .ssh, 600 for authorized_keys)
ls -la ~/.ssh/
```

## Security Best Practices

1. **Never share your private key** (`~/.ssh/id_ed25519`)
2. **Use key-based auth** (more secure than passwords)
3. **Consider using a passphrase** on your private key for extra security
4. **Keep password authentication disabled** if possible (use keys only)
5. **Regular Pi username** should not have passwordless sudo in production

## Quick Command Reference

```bash
# Generate SSH key
ssh-keygen -t ed25519 -C "your_email@example.com"

# Copy key to server (if password auth enabled)
ssh-copy-id username@hostname

# Test connection
ssh username@hostname

# Check SSH logs on Pi (if issues)
sudo journalctl -u ssh -f
```
