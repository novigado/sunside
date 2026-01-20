# Nucleus Required Ports

Based on your `nucleus-stack-no-ssl.yml` configuration, here are all the ports used by Nucleus:

## Critical Ports (Must be open)

| Port | Service | Purpose | Status |
|------|---------|---------|--------|
| **3333** | Discovery | Service discovery - **MOST CRITICAL** |  NOT OPEN |
| 3009 | API | Main API endpoint |  Open |
| 3100 | Auth | Authentication service |  Open |
| 3030 | LFT | Large File Transfer |  NOT OPEN |

## Secondary Ports (Recommended)

| Port | Service | Purpose | Status |
|------|---------|---------|--------|
| 3180/80 | Web UI | Navigator web interface |  Open |
| 3400 | Search | Search functionality |  NOT OPEN |
| 3020 | Tagging | Asset tagging |  NOT OPEN |

## Optional Ports

| Port | Service | Purpose | Status |
|------|---------|---------|--------|
| 8080 | Metrics | Prometheus metrics |  NOT OPEN |
| 5000 | Meta Dump | Metadata dump (commented out) | N/A |

## Immediate Action Required

**Open port 3333 in your Azure NSG** - This is the Discovery service port that omni.client is trying to reach!

### Steps to Fix:

1. **Azure Portal** → Your VM → Networking → Add inbound port rule:
   - **Port**: 3333
   - **Protocol**: TCP
   - **Source**: Any (or your IP for security)
   - **Name**: Nucleus-Discovery
   - **Priority**: 310

2. **Also add port 3030** (Large File Transfer - needed for USD files):
   - **Port**: 3030
   - **Protocol**: TCP
   - **Source**: Any
   - **Name**: Nucleus-LFT
   - **Priority**: 320

3. **Test connectivity**:
   ```powershell
   Test-NetConnection -ComputerName 4.165.216.225 -Port 3333
   Test-NetConnection -ComputerName 4.165.216.225 -Port 3030
   ```

## Why This Matters

The omni.client library follows this connection flow:
1. Connect to **Discovery service (port 3333)** to find available services
2. Authenticate via **Auth service (port 3100)**
3. Access data via **API service (port 3009)**
4. Transfer large files via **LFT service (port 3030)**

Without port 3333 open, omni.client can't discover the services and returns `ERROR_CONNECTION`.

## Environment Variable Mapping

In your `.env` file, these correspond to:
```bash
DISCOVERY_PORT=3333    # ← THIS ONE IS CRITICAL
API_PORT=3009
AUTH_PORT=3100
LFT_PORT=3030
WEB_PORT=3180
SEARCH_PORT=3400
TAGGING_PORT=3020
METRICS_PORT=8080
```
