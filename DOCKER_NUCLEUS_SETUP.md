# Running Nucleus Locally

This guide will help you run Omniverse Nucleus locally. Since the public nucleus-stack is not available, we'll use **Omniverse Navigator** (the official modern method).

## Method 1: Omniverse Navigator (RECOMMENDED)

Omniverse Navigator is the official replacement for the deprecated Launcher and includes Nucleus management.

### Step 1: Download and Install Navigator

1. **Go to the official download page**:
   - Visit: https://www.nvidia.com/en-us/omniverse/download/
   - Or direct link: https://install.launcher.omniverse.nvidia.com/installers/omniverse-launcher-win.exe

2. **Install Omniverse Navigator**:
   - Run the installer
   - Follow the installation prompts
   - Launch Omniverse Navigator when installation completes

3. **Sign in** (free NVIDIA account required):
   - Create an account if you don't have one
   - Sign in to Navigator

### Step 2: Install Nucleus through Navigator

1. **Open Omniverse Navigator**

2. **Go to the Nucleus section**:
   - Look for "Nucleus" in the left sidebar or main menu
   - Or go to Settings/Services

3. **Install Local Nucleus Server**:
   - Click "Install" or "Add Local Nucleus"
   - Choose installation location
   - Wait for installation to complete

4. **Start Nucleus**:
   - Click "Start" button
   - Wait for status to show "Running"
   - Default URL will be: `omniverse://localhost`

### Step 3: Verify Nucleus is Running

```powershell
# Check if Nucleus processes are running
Get-Process | Where-Object {$_.ProcessName -like "*nucleus*" -or $_.ProcessName -like "*omni*"}
```

You should see several Nucleus-related processes.

### Step 4: Test from Shadow Analyzer

1. **Launch the Shadow Analyzer app**

2. **Check the Nucleus Status window**:
   - Should now show: ✅ **Connected**
   - Server: `omniverse://localhost`

3. **Click "Test Connection"** to verify

---

## Method 2: Docker with NGC (If you have NGC access)

If you have an NVIDIA NGC account, you can use Docker with the official Nucleus stacks.

### What You'll Find in NGC Catalog

There are **two Nucleus stacks** available in NGC:

1. **Nucleus Compose Stack** - Full Nucleus server with all services (recommended)
   - NGC URL: https://catalog.ngc.nvidia.com/orgs/nvidia/teams/omniverse/resources/nucleus-stack

2. **Nucleus Cache Compose Stack** - Lightweight caching server only
   - NGC URL: https://catalog.ngc.nvidia.com/orgs/nvidia/teams/omniverse/resources/nucleus-cache-stack

For Shadow Analyzer, we want the **full Nucleus Compose Stack**.

### Prerequisites

1. **Docker Desktop** installed and running
   - Download from: https://www.docker.com/products/docker-desktop/
   - Make sure it's running (check system tray)
   - Ensure Docker Compose is installed (included in Docker Desktop)

2. **NVIDIA NGC Account**
   - Sign up at: https://ngc.nvidia.com/
   - Generate an API key: https://ngc.nvidia.com/setup/api-key

### Step-by-Step Setup

#### Step 1: Login to NGC

```powershell
# Login to NGC registry
docker login nvcr.io
# Username: $oauthtoken
# Password: <paste your NGC API key>
```

#### Step 2: Pull the Nucleus Stack

The Nucleus Compose Stack is a resource in NGC that contains the docker-compose configuration.

```powershell
# Create a directory for Nucleus
mkdir C:\nucleus-stack -Force
cd C:\nucleus-stack

# Pull the nucleus-stack resource
# This pulls a container that contains the compose files
docker pull nvcr.io/nvidia/omniverse/nucleus-stack:latest

# Extract the compose files from the container
docker run --rm -v ${PWD}:/output nvcr.io/nvidia/omniverse/nucleus-stack:latest cp -r /compose /output/
```

**Alternative: If the above doesn't work**, pull the compose files this way:

```powershell
# Run the container to get the files
docker create --name nucleus-temp nvcr.io/nvidia/omniverse/nucleus-stack:latest
docker cp nucleus-temp:/compose ./
docker rm nucleus-temp
```

#### Step 3: Review and Configure (Optional)

```powershell
# Check what files were extracted
ls

# Edit .env or docker-compose.yml if needed
# Default ports:
# - 3009: Nucleus API
# - 3180: Web interface
# - 3100: Navigator service
```

#### Step 4: Start Nucleus

```powershell
# Make sure you're in the nucleus-stack directory
cd C:\nucleus-stack\compose  # or wherever the compose file ended up

# Pull all required images
docker-compose pull

# Start the stack in detached mode
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

#### Step 5: Verify Running
  nvcr.io/nvidia/omniverse/nucleus-server:latest

# Check if container is running
docker ps | findstr nucleus

# View logs
docker logs nucleus-local
```

### Test Connection

Open your browser: http://localhost:3180 (Nucleus web interface)

---

## Recommendation

**Use Omniverse Navigator (Method 1)** because:
- ✅ Official supported method
- ✅ Easy installation and management
- ✅ Automatic updates
- ✅ Better integrated with Omniverse ecosystem
- ✅ No Docker complexity

Docker is good for:
- CI/CD pipelines
- Containerized deployments
- If you already have NGC access
- Development environments where you need isolation

---

```powershell
# Check if container is running
docker ps | findstr nucleus

# Check Nucleus logs
docker logs nucleus-local

# You should see something like:
# "Nucleus server started successfully"
# "Listening on port 3009"
```

## Step 4: Test Connection from Browser

Open your browser and go to:
```
http://localhost:3180
```

You should see the Nucleus web interface.

## Step 5: Test from Shadow Analyzer

1. **Make sure Nucleus container is running**:
   ```powershell
   docker ps
   ```

2. **Launch the Shadow Analyzer app**

3. **Look at the Nucleus Status window**:
   - Should now show: ✅ **Connected**
   - Server: `omniverse://localhost`

4. **Or click "Test Connection"** button to verify

## Common Issues & Solutions

### Issue: "Cannot connect to Docker daemon"
**Solution**: Make sure Docker Desktop is running
```powershell
# Start Docker Desktop, then verify
docker version
```

### Issue: "Port already in use"
**Solution**: Another service is using the port
```powershell
# Check what's using port 3009
netstat -ano | findstr "3009"

# Stop the conflicting service or use different ports:
docker run -d `
  --name nucleus-local `
  -p 13009:3009 `
  nvcr.io/nvidia/omniverse/nucleus-server:latest

# Then update your app config to use: omniverse://localhost:13009
```

### Issue: "No NGC access / authentication failed"
**Solution**: Use the public nucleus-stack instead (Option B above)

### Issue: Container starts but can't connect
**Solution**: Wait a minute - Nucleus takes time to initialize
```powershell
# Watch the logs
docker logs -f nucleus-local

# Wait for "Nucleus server started successfully"
```

## Managing the Nucleus Container

```powershell
# Stop Nucleus
docker stop nucleus-local

# Start Nucleus (after stopping)
docker start nucleus-local

# Restart Nucleus
docker restart nucleus-local

# View logs
docker logs nucleus-local

# Remove container (keeps data if you used -v)
docker rm nucleus-local

# Remove container AND data
docker rm nucleus-local
Remove-Item -Recurse -Force C:\nucleus-data
```

## Default Credentials

When you first access Nucleus web interface (http://localhost:3180):
- **Username**: `admin` or `omniverse`
- **Password**: `admin` or check docker logs for generated password

You can create additional users through the web interface.

## Updating the Shadow Analyzer Config (if needed)

If you used custom ports, update `city.shadow_analyzer.kit.kit`:

```toml
# If you used port 13009 instead of 3009:
exts."city.shadow_analyzer.nucleus".nucleus_server = "omniverse://localhost:13009"
```

## Next Steps

Once Nucleus is running and connected:

1. **✅ Verify connection** in the Nucleus Status window
2. **Test caching** by loading buildings (future Phase 2)
3. **View cached data** in Nucleus web interface at http://localhost:3180

## Performance Note

Docker Nucleus on Windows/WSL2 might be slightly slower than native, but it's:
- ✅ Easy to set up
- ✅ Easy to reset/clean
- ✅ Consistent across machines
- ✅ Good for development

For production, consider native Nucleus installation or Omniverse Navigator.

---

## Quick Start Command (Copy-Paste)

If you have NGC access:
```powershell
docker run -d --name nucleus-local -p 3009:3009 -p 3180:3180 nvcr.io/nvidia/omniverse/nucleus-server:latest
```

Then open Shadow Analyzer and check the Nucleus Status window!
