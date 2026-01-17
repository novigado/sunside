# Nucleus Setup Guide

**Last Updated**: January 17, 2026
**Purpose**: Install and configure NVIDIA Omniverse Nucleus for City Shadow Analyzer caching

---

## Table of Contents
- [Overview](#overview)
- [Which Setup Method?](#which-setup-method)
- [Method 1: Omniverse Navigator (Recommended)](#method-1-omniverse-navigator-recommended)
- [Method 2: Docker on Windows](#method-2-docker-on-windows)
- [Method 3: Docker on Ubuntu/Linux](#method-3-docker-on-ubuntulinux)
- [Method 4: Omniverse Cloud](#method-4-omniverse-cloud)
- [Testing Your Setup](#testing-your-setup)
- [Troubleshooting](#troubleshooting)

---

## Overview

Nucleus is NVIDIA's content management server that provides:
- **10-20x faster loading** for City Shadow Analyzer (via caching)
- **Persistent storage** for building and terrain data
- **Version control** for USD assets
- **Team collaboration** (optional)

**Do I need Nucleus?**
- ❌ **Not required** - City Shadow Analyzer works without it (uses JSON cache)
- ✅ **Recommended** - Dramatically improves performance (3-5s vs 30-70s loading)
- ✅ **Optional** - Can add it later when you need performance

---

## Which Setup Method?

| Method | Best For | Difficulty | Setup Time |
|--------|----------|------------|------------|
| **[Omniverse Navigator](#method-1-omniverse-navigator-recommended)** | Windows users, beginners | ⭐ Easy | 10 minutes |
| **[Docker (Windows)](#method-2-docker-on-windows)** | Development, CI/CD | ⭐⭐ Medium | 15 minutes |
| **[Docker (Ubuntu)](#method-3-docker-on-ubuntulinux)** | Linux servers, production | ⭐⭐⭐ Advanced | 30 minutes |
| **[Cloud Nucleus](#method-4-omniverse-cloud)** | Teams, enterprise | ⭐ Easy | 5 minutes |

**Recommendation**: Start with **Omniverse Navigator** (easiest, officially supported).

---

## Method 1: Omniverse Navigator (Recommended)

**Best for**: Windows users, beginners, most users
**Time**: ~10 minutes

### Step 1: Download Omniverse Navigator

1. **Visit**: https://www.nvidia.com/en-us/omniverse/download/
2. **Download**: Omniverse Navigator (replaces the deprecated Launcher)
3. **Install**: Run the installer and follow prompts
4. **Sign in**: Create/use your NVIDIA account (free)

### Step 2: Install Nucleus

1. **Open Omniverse Navigator**
2. **Go to Nucleus section** (left sidebar or Settings)
3. **Click "Install Local Nucleus"**
4. **Choose installation location**
5. **Wait for installation** (5-10 minutes)

### Step 3: Start Nucleus

1. **In Navigator, click "Start"** (in Nucleus section)
2. **Wait for status**: Should show "Running"
3. **Note the URL**: Usually `omniverse://localhost`

### Step 4: Verify in City Shadow Analyzer

1. **Launch City Shadow Analyzer**:
   ```powershell
   .\repo.bat launch -- source/apps/city.shadow_analyzer.kit.kit
   ```

2. **Check Nucleus Status window**:
   - Should show: ✅ **Connected**
   - Server: `omniverse://localhost`

3. **Click "Test Connection"** to verify

### Step 5: Test Caching

1. **Load a map with buildings** (e.g., San Francisco)
   - First load: 30-60 seconds (cache miss, saves to Nucleus)
2. **Clear the scene**
3. **Load same location again**
   - Second load: 3-5 seconds (cache hit!) ✅

**Success!** You're now getting 10-20x performance improvements.

---

## Method 2: Docker on Windows

**Best for**: Development, containerized environments, CI/CD
**Time**: ~15 minutes

### Prerequisites

1. **Docker Desktop**: https://www.docker.com/products/docker-desktop/
   - Install and ensure it's running (check system tray)
2. **NVIDIA NGC Account** (optional, for official images):
   - Sign up: https://ngc.nvidia.com/
   - Generate API key: https://ngc.nvidia.com/setup/api-key

### Option A: Simple Nucleus Server (No NGC Required)

```powershell
# Run a basic Nucleus server
docker run -d `
  --name nucleus-local `
  -p 3009:3009 `
  -p 3180:3180 `
  -v c:\nucleus-data:/data `
  nvcr.io/nvidia/omniverse/nucleus-server:latest
```

**If you get authentication errors**, try the public nucleus-stack image (check NGC catalog).

### Option B: Full Nucleus Stack (NGC Required)

#### Step 1: Login to NGC

```powershell
docker login nvcr.io
# Username: $oauthtoken
# Password: <paste your NGC API key>
```

#### Step 2: Pull Nucleus Stack

```powershell
# Create directory
mkdir C:\nucleus-stack -Force
cd C:\nucleus-stack

# Pull the nucleus-stack resource
docker pull nvcr.io/nvidia/omniverse/nucleus-stack:latest

# Extract compose files
docker run --rm -v ${PWD}:/output nvcr.io/nvidia/omniverse/nucleus-stack:latest cp -r /compose /output/
```

#### Step 3: Start Nucleus

```powershell
cd C:\nucleus-stack\compose

# Pull all images
docker-compose pull

# Start the stack
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

### Verify Installation

1. **Check containers are running**:
   ```powershell
   docker ps | findstr nucleus
   ```

2. **Access web interface**: http://localhost:3180

3. **Test in City Shadow Analyzer**:
   - Server URL: `omniverse://localhost`
   - Click "Test Connection"

### Managing Docker Nucleus

```powershell
# Stop Nucleus
docker stop nucleus-local

# Start Nucleus
docker start nucleus-local

# View logs
docker logs nucleus-local

# Remove container (keeps data with -v)
docker rm nucleus-local
```

---

## Method 3: Docker on Ubuntu/Linux

**Best for**: Linux servers, production deployments, remote access
**Time**: ~30 minutes

### Prerequisites

```bash
# Ubuntu VM with Docker installed
docker --version

# Docker Compose
docker-compose --version

# NGC login (if using official images)
docker login nvcr.io
```

### Step 1: Install Docker Compose (if needed)

```bash
# Check version
docker-compose --version

# Install if missing
sudo apt-get update
sudo apt-get install docker-compose-plugin
```

### Step 2: Create Nucleus Directory

```bash
mkdir -p ~/nucleus/base_stack
cd ~/nucleus/base_stack
```

### Step 3: Create Environment File

```bash
cat > .env << 'EOF'
# EULA Acceptance (required)
ACCEPT_EULA=1

# Registry and versions
REGISTRY=nvcr.io/nvidia/omniverse
NAV3_VERSION=latest
NUCLEUS_BUILD=latest

# Service passwords (CHANGE THESE!)
SERVICE_PASSWORD=YourSecurePassword123!
MASTER_PASSWORD=YourAdminPassword123!

# Admin user
ADMIN_USER=admin
ADMIN_PASSWORD=admin123

# Data storage
DATA_ROOT=./data

# Network configuration
# Use your server's IP if accessing from other machines
HOSTNAME=localhost

# Ports
NUCLEUS_API_PORT=3009
NUCLEUS_WEB_PORT=3180
NUCLEUS_DISCOVERY_PORT=3100
EOF

# Edit to set secure passwords
nano .env
```

**Important**: If accessing from other machines, change `HOSTNAME=localhost` to your server's IP address!

### Step 4: Fix Docker Permissions

```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Log out and back in, or run:
newgrp docker

# Verify
docker ps
```

### Step 5: Generate Secret Files (CRITICAL!)

```bash
cd ~/nucleus/base_stack
mkdir -p secrets

# Generate service registration token
echo "$(openssl rand -hex 32)" > secrets/svc_reg_token

# Generate authentication keys
openssl genrsa -out secrets/auth_root_of_trust.key 2048
openssl rsa -in secrets/auth_root_of_trust.key -pubout -out secrets/auth_root_of_trust.pub

# Generate PEM variants
cp secrets/auth_root_of_trust.pub secrets/auth_root_of_trust.pem
cp secrets/auth_root_of_trust.pub secrets/auth_root_of_trust_lt.pem
cp secrets/auth_root_of_trust.pub secrets/auth_root_of_trust_lt.pub

# Generate salts (MUST be exactly 16 bytes as hex)
openssl rand -hex 16 | tr -d '\n' > secrets/pwd_salt
echo "$(openssl rand -hex 32)" > secrets/lft_salt

# Set permissions
chmod 600 secrets/*

# Verify all 8 files exist
ls -la secrets/
```

### Step 6: Get Docker Compose File

You'll need the `nucleus-stack-no-ssl.yml` file from NGC or your Nucleus distribution. Place it in `~/nucleus/base_stack/`.

### Step 7: Start Nucleus

```bash
cd ~/nucleus/base_stack

# Pull images
docker-compose -f nucleus-stack-no-ssl.yml pull

# Start Nucleus
docker-compose -f nucleus-stack-no-ssl.yml up -d

# Check status
docker-compose -f nucleus-stack-no-ssl.yml ps

# View logs
docker-compose -f nucleus-stack-no-ssl.yml logs -f
```

### Step 8: Verify Nucleus is Running

```bash
# Check containers
docker-compose -f nucleus-stack-no-ssl.yml ps

# Check ports are listening
ss -tlnp | grep 3009  # API
ss -tlnp | grep 3180  # Web UI
```

### Step 9: Configure Firewall (if needed)

```bash
# Allow Nucleus ports
sudo ufw allow 3009/tcp   # API
sudo ufw allow 3180/tcp   # Web UI
sudo ufw allow 3100/tcp   # Discovery
sudo ufw status
```

### Step 10: Test Access

**From Ubuntu VM**:
```bash
curl http://localhost:3180
```

**From Windows (get Ubuntu IP first)**:
```bash
# On Ubuntu, get IP
hostname -I
```

Then on Windows:
- Browser: `http://<ubuntu-ip>:3180`
- Update City Shadow Analyzer config:
  ```toml
  exts."city.shadow_analyzer.nucleus".nucleus_server = "omniverse://<ubuntu-ip>"
  ```

### Step 11: Create API Token (for client authentication)

1. **Open web interface**: `http://<ubuntu-ip>:3180`
2. **Log in** with credentials from `.env`
3. **Go to Settings → API Tokens**
4. **Generate new token** (name it "Shadow Analyzer")
5. **Copy the token** (shown only once!)
6. **Add to kit file**:
   ```toml
   exts."city.shadow_analyzer.nucleus".api_token = "your-token-here"
   ```

### Managing Nucleus

```bash
cd ~/nucleus/base_stack

# Stop
docker-compose -f nucleus-stack-no-ssl.yml down

# Start
docker-compose -f nucleus-stack-no-ssl.yml up -d

# Restart
docker-compose -f nucleus-stack-no-ssl.yml restart

# View logs
docker-compose -f nucleus-stack-no-ssl.yml logs -f

# Check resource usage
docker stats
```

---

## Method 4: Omniverse Cloud

**Best for**: Teams, enterprise, cloud deployments
**Time**: ~5 minutes

### Step 1: Sign Up

1. **Visit**: https://www.nvidia.com/en-us/omniverse/cloud/
2. **Sign up** for Omniverse Cloud (may require enterprise account)
3. **Get your Nucleus URL**: Usually `omniverse://your-org.ov.nvidia.com`

### Step 2: Configure City Shadow Analyzer

Edit `source/apps/city.shadow_analyzer.kit.kit`:

```toml
exts."city.shadow_analyzer.nucleus".nucleus_server = "omniverse://your-org.ov.nvidia.com"
exts."city.shadow_analyzer.nucleus".api_token = "your-cloud-api-token"
```

### Step 3: Test Connection

1. Launch City Shadow Analyzer
2. Check Nucleus Status window
3. Should show: ✅ Connected to cloud Nucleus

---

## Testing Your Setup

### Test 1: Connection Test

1. **Launch City Shadow Analyzer**
2. **Open Nucleus Status window** (Window → Nucleus Status)
3. **Click "Test Connection"**
4. **Expected**: ✅ Connected, server info displayed

### Test 2: Cache Performance Test

1. **Load a city** (e.g., San Francisco, 37.7749, -122.4194)
   - First load: 30-60 seconds (downloads from OpenStreetMap, saves to Nucleus)
   - Check logs for: "💾 Saving buildings to Nucleus cache..."
2. **Clear the scene** (Scene → Clear All)
3. **Load same city again**
   - Second load: 3-5 seconds (loads from Nucleus cache)
   - Check logs for: "✅ BUILDING CACHE HIT! Loading from Nucleus..."

**Success if**: Second load is 10-20x faster!

### Test 3: Verify Cache Files

**Omniverse Navigator**:
- Open Navigator → Nucleus tab
- Browse to `/Projects/CityBuildings/`
- Should see `.usdc` files

**Web Interface**:
- Open `http://localhost:3180` (or your server IP)
- Browse to `/Projects/CityBuildings/`
- Should see cached building files

**Command Line**:
```python
from city.shadow_analyzer.nucleus import get_nucleus_manager

nucleus = get_nucleus_manager()
files = nucleus.list_files("/Projects/CityBuildings")
print(files)  # Should show cached .usdc files
```

---

## Troubleshooting

### Issue: "Cannot connect to Nucleus"

**Causes**:
- Nucleus not running
- Wrong URL
- Firewall blocking

**Solutions**:
```powershell
# Check if Nucleus is running
# Windows (Navigator):
Get-Process | Where-Object {$_.ProcessName -like "*nucleus*"}

# Docker:
docker ps | findstr nucleus

# Linux:
ss -tlnp | grep 3009

# Test connectivity
curl http://localhost:3009
# or
Test-NetConnection localhost -Port 3009
```

### Issue: "Authentication failed"

**Causes**:
- Missing API token
- Incorrect credentials

**Solutions**:
1. **Generate API token** (see Method 3, Step 11)
2. **Add to kit file**:
   ```toml
   exts."city.shadow_analyzer.nucleus".api_token = "your-token"
   ```
3. **Or enable anonymous access** (development only):
   ```bash
   # Add to .env
   ALLOW_ANONYMOUS_ACCESS=true
   # Restart Nucleus
   ```

### Issue: "Port already in use"

**Cause**: Another service using port 3009

**Solutions**:
```powershell
# Check what's using the port
netstat -ano | findstr "3009"

# Use different port
docker run -d -p 13009:3009 nvcr.io/nvidia/omniverse/nucleus-server:latest

# Update app config
exts."city.shadow_analyzer.nucleus".nucleus_server = "omniverse://localhost:13009"
```

### Issue: Docker permission denied (Linux)

**Solution**:
```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Log out and back in, or:
newgrp docker

# Verify
docker ps
```

### Issue: Missing secret files (Linux)

**Cause**: Secret files not generated

**Solution**: Re-run Step 5 secret generation commands

### Issue: "Failed to connect to discovery service" (Linux)

**Causes**:
- HOSTNAME set to localhost but accessing remotely
- Anonymous access disabled

**Solutions**:
```bash
# Fix HOSTNAME
nano ~/nucleus/base_stack/.env
# Change: HOSTNAME=<your-server-ip>

# Or enable anonymous access
echo "ALLOW_ANONYMOUS_ACCESS=true" >> .env

# Restart
docker-compose -f nucleus-stack-no-ssl.yml restart
```

### Issue: Cache not working / Always cache miss

**Causes**:
- Nucleus connected but cache writes failing
- Insufficient permissions

**Solutions**:
1. **Check Nucleus logs** for errors
2. **Verify write permissions**: Try creating a file in web interface
3. **Check disk space**: `df -h` (Linux) or Properties (Windows)
4. **Enable detailed logging**:
   ```toml
   # In kit file
   exts."city.shadow_analyzer.nucleus".log_level = "debug"
   ```

---

## Default Credentials

**Local Nucleus** (Navigator or Docker):
- Username: `admin` or `omniverse`
- Password: `admin` (or check docker logs for generated password)

**Cloud Nucleus**:
- Use your NVIDIA account credentials

---

## Performance Notes

### Expected Performance

| Cache Type | First Load | Cached Load | Improvement |
|------------|-----------|-------------|-------------|
| Buildings | 30-70s | 3-5s | **10-20x** |
| Terrain | 10-20s | 1-2s | **5-10x** |

### Docker on Windows/WSL2

- Slightly slower than native (~10-15% overhead)
- Still provides significant benefits
- Good for development

### Production Recommendations

- Use native Nucleus installation or Omniverse Navigator
- Or use dedicated Linux server (Method 3)
- Or use Omniverse Cloud for enterprise

---

## Next Steps

1. ✅ **Nucleus installed and running**
2. ✅ **Connection verified** in City Shadow Analyzer
3. ✅ **Cache performance tested** (10-20x faster!)
4. **Optional**: Set up [validation testing](VALIDATION.md)
5. **Optional**: Review [integration details](INTEGRATION.md)

---

## References

- [Nucleus Documentation](https://docs.omniverse.nvidia.com/nucleus/latest/)
- [Omniverse Navigator](https://www.nvidia.com/en-us/omniverse/download/)
- [NGC Nucleus Stack](https://catalog.ngc.nvidia.com/orgs/nvidia/teams/omniverse/resources/nucleus-stack)
- [Docker Documentation](https://docs.docker.com/)
- [City Shadow Analyzer - ARCHITECTURE.md](../development/ARCHITECTURE.md)

---

**Document Owner**: Development Team
**Last Updated**: January 17, 2026
**Phase**: Phase 5 (Documentation Consolidation)
