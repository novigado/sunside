# Installing Nucleus on Ubuntu with Docker

This guide shows how to install and run Nucleus on Ubuntu using the NGC Docker images.

## Prerequisites (Already Done)

✅ Ubuntu VM running
✅ Docker installed
✅ Logged into nvcr.io

## Step 1: Install Docker Compose (if not already installed)

```bash
# Check if docker-compose is installed
docker-compose --version

# If not installed:
sudo apt-get update
sudo apt-get install docker-compose-plugin

# Or use the standalone version:
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

## Step 2: Transfer Nucleus Stack Files to Ubuntu

If you downloaded the Nucleus stack on Windows, transfer it to Ubuntu:

```bash
# On Ubuntu, create directory
mkdir -p ~/nucleus
cd ~/nucleus

# From Windows, use SCP, WinSCP, or copy via shared folder
# Or download directly on Ubuntu from NGC
```

**Or download directly on Ubuntu:**

```bash
# If you have NGC access, you might be able to extract directly
# Check NGC catalog for download instructions specific to your setup
```

## Step 3: Set Up the Environment File

```bash
cd ~/nucleus/base_stack

# Create the .env file with required variables
cat > .env << 'EOF'
# EULA Acceptance (required)
ACCEPT_EULA=1

# Registry and versions
REGISTRY=nvcr.io/nvidia/omniverse
NAV3_VERSION=latest
NUCLEUS_BUILD=latest

# Service passwords (change these!)
SERVICE_PASSWORD=SecurePassword123!
MASTER_PASSWORD=AdminPassword123!

# Admin user
ADMIN_USER=admin
ADMIN_PASSWORD=admin123

# Data storage location
DATA_ROOT=./data

# Network configuration
HOSTNAME=localhost

# Port configuration (defaults)
NUCLEUS_API_PORT=3009
NUCLEUS_WEB_PORT=3180
NUCLEUS_DISCOVERY_PORT=3100

# Optional: if you need specific IPs
# LISTEN_ADDRESS=0.0.0.0
EOF

# Edit the file to set your own secure passwords
nano .env
```

**IMPORTANT:** If you're accessing Nucleus from external machines, change `HOSTNAME=localhost` to your server's IP or hostname:
```bash
# For external access, edit .env and set:
HOSTNAME=4.165.216.225  # Or your server's actual IP/hostname
```

## Step 4: Fix Docker Permissions (IMPORTANT!)

Your user needs permission to access Docker. Choose one option:

**Option A: Add user to docker group (recommended for regular use):**
```bash
# Add your user to the docker group
sudo usermod -aG docker $USER

# Log out and back in for changes to take effect
# Or run this to apply immediately in current session:
newgrp docker

# Verify it works
docker ps
```

**Option B: Use sudo (quick fix):**
```bash
# Just prefix all docker commands with sudo
sudo docker-compose -f nucleus-stack-no-ssl.yml up -d
```

## Step 5: Generate Secret Files (CRITICAL!)

Nucleus requires secret files for authentication and security. Create them all:

```bash
cd ~/nucleus/base_stack

# Create secrets directory
mkdir -p secrets

# Generate the service registration token
echo "$(openssl rand -hex 32)" > secrets/svc_reg_token

# Generate authentication root of trust keys
openssl genrsa -out secrets/auth_root_of_trust.key 2048
openssl rsa -in secrets/auth_root_of_trust.key -pubout -out secrets/auth_root_of_trust.pub

# Generate PEM format variants (also needed)
cp secrets/auth_root_of_trust.pub secrets/auth_root_of_trust.pem
cp secrets/auth_root_of_trust.pub secrets/auth_root_of_trust_lt.pem
cp secrets/auth_root_of_trust.pub secrets/auth_root_of_trust_lt.pub

# Generate password salt (for auth service) - MUST be exactly 16 bytes as hex string
openssl rand -hex 16 | tr -d '\n' > secrets/pwd_salt

# Generate LFT (Large File Transfer) salt
echo "$(openssl rand -hex 32)" > secrets/lft_salt

# Set proper permissions
chmod 600 secrets/*

# Verify all files exist
ls -la secrets/
```

You should see 8 files:
- `svc_reg_token` - Service registration token
- `auth_root_of_trust.key` - Private key
- `auth_root_of_trust.pub` - Public key
- `auth_root_of_trust.pem` - Public key (PEM format)
- `auth_root_of_trust_lt.pem` - Public key (long-term PEM)
- `auth_root_of_trust_lt.pub` - Public key (long-term pub)
- `pwd_salt` - Password hashing salt
- `lft_salt` - Large file transfer salt

## Step 6: Pull Docker Images

```bash
cd ~/nucleus/base_stack

# Pull all required images (use sudo if you didn't do Option A above)
docker-compose -f nucleus-stack-no-ssl.yml pull
# OR
sudo docker-compose -f nucleus-stack-no-ssl.yml pull

# This will take several minutes...
```

## Step 7: Start Nucleus

```bash
# Start in detached mode (add sudo if needed)
docker-compose -f nucleus-stack-no-ssl.yml up -d
# OR
sudo docker-compose -f nucleus-stack-no-ssl.yml up -d

# Check status
docker-compose -f nucleus-stack-no-ssl.yml ps

# View logs (wait for "Nucleus server started successfully")
docker-compose -f nucleus-stack-no-ssl.yml logs -f
```

Press `Ctrl+C` to stop following logs.

## Step 8: Verify Nucleus is Running

```bash
# Check all containers are up
docker-compose -f nucleus-stack-no-ssl.yml ps

# Should see several containers in "Up" state:
# - nucleus-api
# - nucleus-navigator
# - nucleus-auth
# - nucleus-discovery
# - nucleus-search
# - nucleus-tagging
# - etc.

# Check if ports are listening
ss -tlnp | grep 3009  # API port
ss -tlnp | grep 3180  # Web UI port
```

## Step 9: Test Access

### From the Ubuntu VM:

```bash
# Test local access
curl http://localhost:3180
```

### From your Windows machine:

1. **Get Ubuntu VM's IP address**:
   ```bash
   # On Ubuntu VM
   ip addr show | grep inet
   # or
   hostname -I
   ```

2. **Test from Windows browser**:
   - Open: `http://<ubuntu-ip>:3180`
   - You should see Nucleus web interface

3. **Update Shadow Analyzer config** on Windows:
   ```toml
   # In city.shadow_analyzer.kit.kit
   exts."city.shadow_analyzer.nucleus".nucleus_server = "omniverse://<ubuntu-ip>"
   ```

4. **Test connection in Shadow Analyzer**:
   - Launch the app
   - Click "Test Connection" in Nucleus Status window
   - Should show: ✅ Connected

## Step 10: Configure Firewall (if needed)

```bash
# Allow Nucleus ports through firewall
sudo ufw allow 3009/tcp   # Nucleus API
sudo ufw allow 3180/tcp   # Web UI
sudo ufw allow 3100/tcp   # Discovery
sudo ufw status
```

## Step 11: Create API Token for Authentication

Nucleus requires authentication for client connections. Generate an API token:

### Option A: Using Nucleus Web UI

1. Open Nucleus Navigator: `http://<ubuntu-ip>:3180`
2. Log in with your admin credentials (from .env: `ADMIN_USER` / `ADMIN_PASSWORD`)
3. Go to **Settings** → **API Tokens** or **User Settings**
4. Click **"Generate New Token"** or **"Create API Token"**
5. Give it a name (e.g., "Shadow Analyzer")
6. Copy the generated token (it will only be shown once!)

### Option B: Using Nucleus CLI (if available)

```bash
# From Ubuntu VM
cd ~/nucleus/base_stack

# Generate token via API (requires admin credentials)
# This creates a service account token
```

### Option C: Use omniverse:// User Token

If you have Omniverse Launcher installed on Windows:
1. Open Omniverse Launcher
2. Go to **Settings** → **Nucleus**
3. Find your API token or generate one
4. Copy the token

### Configure Shadow Analyzer with Token

On your Windows machine, edit the kit file:

```toml
# In source/apps/city.shadow_analyzer.kit.kit
exts."city.shadow_analyzer.nucleus".nucleus_server = "omniverse://4.165.216.225"
exts."city.shadow_analyzer.nucleus".api_token = "your-api-token-here"
```

**Important:** Keep your API token secret! Don't commit it to version control.

## Managing Nucleus

```bash
cd ~/nucleus/base_stack

# Stop Nucleus
docker-compose -f nucleus-stack-no-ssl.yml down

# Start Nucleus
docker-compose -f nucleus-stack-no-ssl.yml up -d

# Restart Nucleus
docker-compose -f nucleus-stack-no-ssl.yml restart

# View logs
docker-compose -f nucleus-stack-no-ssl.yml logs -f

# View logs for specific service
docker-compose -f nucleus-stack-no-ssl.yml logs nucleus-api

# Check resource usage
docker stats
```

## Troubleshooting

### Missing secret files error:

```bash
# Error: "bind source path does not exist: .../secrets/..."
# Solution: Generate ALL required secret files (see Step 5)

cd ~/nucleus/base_stack
mkdir -p secrets
echo "$(openssl rand -hex 32)" > secrets/svc_reg_token
openssl genrsa -out secrets/auth_root_of_trust.key 2048
openssl rsa -in secrets/auth_root_of_trust.key -pubout -out secrets/auth_root_of_trust.pub
cp secrets/auth_root_of_trust.pub secrets/auth_root_of_trust.pem
cp secrets/auth_root_of_trust.pub secrets/auth_root_of_trust_lt.pem
cp secrets/auth_root_of_trust.pub secrets/auth_root_of_trust_lt.pub
echo "$(openssl rand -hex 32)" > secrets/pwd_salt
echo "$(openssl rand -hex 32)" > secrets/lft_salt
chmod 600 secrets/*
```

### Containers keep restarting:

```bash
# Check logs for errors
docker-compose -f nucleus-stack-no-ssl.yml logs

# Common issues:
# - Missing environment variables in .env
# - Missing secret files in secrets/
# - Insufficient disk space
# - Port conflicts
```

### Can't connect from Windows:

```bash
# On Ubuntu, check if listening on all interfaces
ss -tlnp | grep 3009

# Make sure LISTEN_ADDRESS is set correctly in .env
# or that the services are bound to 0.0.0.0
```

### Authentication errors / "Not connected" status:

**Cause:** Nucleus requires authentication for client connections.

**Solution:** Create and configure an API token (see Step 11):

1. Log into Nucleus Web UI: `http://<ubuntu-ip>:3180`
2. Generate an API token
3. Add token to `city.shadow_analyzer.kit.kit`:
   ```toml
   exts."city.shadow_analyzer.nucleus".api_token = "your-token-here"
   ```
4. Restart Shadow Analyzer

**Alternative:** Enable anonymous access (not recommended for production):
```bash
# On Ubuntu, add to .env
echo "ALLOW_ANONYMOUS_ACCESS=true" >> ~/nucleus/base_stack/.env

# Restart Nucleus
sudo docker-compose -f ~/nucleus/base_stack/nucleus-stack-no-ssl.yml restart
```

### Browser error: "Failed to connect to the discovery service"

**Cause:** The `HOSTNAME` in `.env` is set to `localhost`, causing the browser to try connecting to `localhost` instead of the actual server IP.

**Solution:** Update the HOSTNAME in .env:

```bash
# On Ubuntu VM
cd ~/nucleus/base_stack
nano .env

# Change this line:
HOSTNAME=localhost

# To your server's IP or hostname:
HOSTNAME=4.165.216.225  # Or your actual IP

# Save and restart Nucleus
sudo docker-compose -f nucleus-stack-no-ssl.yml restart

# Wait about 30 seconds for services to fully restart
sudo docker-compose -f nucleus-stack-no-ssl.yml ps
```

After restarting, refresh your browser at `http://4.165.216.225:3180`

**Alternative Cause:** Browser can't authenticate with Discovery service.

**Quick Fix:** Enable anonymous access temporarily to access the web UI:

```bash
# On Ubuntu VM
cd ~/nucleus/base_stack
nano .env

# Add this line (or update if it exists):
ALLOW_ANONYMOUS_ACCESS=true

# Save and restart
sudo docker-compose -f nucleus-stack-no-ssl.yml restart
```

Then refresh your browser. You should be able to log in and generate an API token.

### Permission issues:

```bash
# If running as non-root user
sudo usermod -aG docker $USER
# Log out and back in

# Or run with sudo
sudo docker-compose -f nucleus-stack-no-ssl.yml up -d
```

## Data Persistence

Data is stored in the `DATA_ROOT` location (default: `./data`):

```bash
# Check data directory
ls -la ~/nucleus/base_stack/data

# Backup data
tar -czf nucleus-backup-$(date +%Y%m%d).tar.gz data/

# Restore data
tar -xzf nucleus-backup-YYYYMMDD.tar.gz
```

## Next Steps

Once Nucleus is running on Ubuntu:

1. ✅ Verify connection from Ubuntu: `curl http://localhost:3180`
2. ✅ Get Ubuntu VM IP: `hostname -I`
3. ✅ Test from Windows: Open `http://<ubuntu-ip>:3180` in browser
4. ✅ Update Shadow Analyzer: Change server to `omniverse://<ubuntu-ip>`
5. ✅ Test in app: Click "Test Connection" - should show ✅ Connected

---

## Quick Command Summary

```bash
# First time setup:
cd ~/nucleus/base_stack
nano .env  # Configure passwords
mkdir -p secrets
echo "$(openssl rand -hex 32)" > secrets/svc_reg_token
openssl genrsa -out secrets/auth_root_of_trust.key 2048
openssl rsa -in secrets/auth_root_of_trust.key -pubout -out secrets/auth_root_of_trust.pub
cp secrets/auth_root_of_trust.pub secrets/auth_root_of_trust.pem
cp secrets/auth_root_of_trust.pub secrets/auth_root_of_trust_lt.pem
cp secrets/auth_root_of_trust.pub secrets/auth_root_of_trust_lt.pub
openssl rand -hex 16 | tr -d '\n' > secrets/pwd_salt
echo "$(openssl rand -hex 32)" > secrets/lft_salt
docker-compose -f nucleus-stack-no-ssl.yml pull
docker-compose -f nucleus-stack-no-ssl.yml up -d

# Daily operations:
docker-compose -f nucleus-stack-no-ssl.yml ps      # Check status
docker-compose -f nucleus-stack-no-ssl.yml logs -f # View logs
docker-compose -f nucleus-stack-no-ssl.yml restart # Restart
docker-compose -f nucleus-stack-no-ssl.yml down    # Stop

# Get VM IP for Windows:
hostname -I
```
