# Nucleus Cache Validation Guide

This guide shows you how to validate that building and terrain data is being stored in your Nucleus server.

## Current Nucleus Server Configuration

- **Server**: `nucleus.swedencentral.cloudapp.azure.com`
- **Username**: `omniverse`
- **Password**: `Letmeinletmein12`
- **Cache Path**: `/Projects/CityData/`

---

## Method 1: Nucleus Web Navigator (Easiest)

The Nucleus server has a built-in web-based file browser.

### Steps:

1. **Open your browser** and navigate to:
   ```
   https://nucleus.swedencentral.cloudapp.azure.com/navigator
   ```

2. **Login** with:
   - Username: `omniverse`
   - Password: `Letmeinletmein12`

3. **Navigate** to `/Projects/CityData/`

4. **Expected folder structure**:
   ```
   /Projects/CityData/
   ├── city_37N_122W/              (San Francisco area)
   │   ├── buildings_abc123.usd     (Building cache file)
   │   ├── buildings_abc123.meta.json (Metadata with timestamp, count, etc.)
   │   ├── terrain_def456.usd       (Terrain cache file)
   │   └── terrain_def456.meta.json
   ├── city_40N_74W/               (New York area)
   │   ├── buildings_xyz789.usd
   │   └── buildings_xyz789.meta.json
   └── ...
   ```

5. **View metadata**: Click on any `.meta.json` file to see:
   ```json
   {
     "saved_at": "2026-01-16T22:45:00Z",
     "latitude": 37.7749,
     "longitude": -122.4194,
     "radius_km": 0.5,
     "building_count": 1523,
     "bounds": {...},
     "data_source": "OpenStreetMap"
   }
   ```

---

## Method 2: SSH to Azure VM and Check Files

You can SSH to your Azure VM and look at the actual files on disk.

### Steps:

1. **SSH to your Azure VM**:
   ```bash
   ssh azureuser@nucleus.swedencentral.cloudapp.azure.com
   ```

2. **Navigate to Nucleus data directory**:
   ```bash
   cd /var/lib/omni/nucleus-data
   ```

3. **List cache files**:
   ```bash
   # Find the data directory
   sudo find . -name "CityData" -type d

   # List contents
   sudo ls -lh ./path/to/Projects/CityData/
   ```

4. **Check file sizes**:
   ```bash
   # See how much space cached data is using
   sudo du -sh ./path/to/Projects/CityData/

   # List all USD files
   sudo find ./path/to/Projects/CityData/ -name "*.usd" -ls
   ```

5. **View metadata**:
   ```bash
   # Read a metadata file
   sudo cat ./path/to/Projects/CityData/city_37N_122W/buildings_abc123.meta.json
   ```

---

## Method 3: Use omni.client API from Python Script

You can write a Python script to list files using the Omniverse client library.

### Create `list_nucleus_cache.py`:

```python
import omni.client
import json

# Configure connection
nucleus_url = "omniverse://nucleus.swedencentral.cloudapp.azure.com"
base_path = f"{nucleus_url}/Projects/CityData"

# Set up authentication
def auth_callback(url):
    return ("omniverse", "Letmeinletmein12")

omni.client.set_authentication_message_box_callback(auth_callback)

# List directories
result, entries = omni.client.list(base_path)

if result == omni.client.Result.OK:
    print(f"✅ Connected to Nucleus: {nucleus_url}")
    print(f"📁 Cache location: {base_path}\n")

    print(f"Found {len(entries)} cached cities:\n")

    for entry in entries:
        if entry.flags & omni.client.ItemFlags.IS_FOLDER:
            city_name = entry.relative_path
            print(f"  📂 {city_name}")

            # List files in this city folder
            city_path = f"{base_path}/{city_name}"
            result2, files = omni.client.list(city_path)

            if result2 == omni.client.Result.OK:
                usd_files = [f.relative_path for f in files if f.relative_path.endswith('.usd')]
                meta_files = [f.relative_path for f in files if f.relative_path.endswith('.meta.json')]

                print(f"     • {len(usd_files)} USD cache files")
                print(f"     • {len(meta_files)} metadata files")

                # Show first metadata
                if meta_files:
                    meta_path = f"{city_path}/{meta_files[0]}"
                    result3, content = omni.client.read_file(meta_path)
                    if result3 == omni.client.Result.OK:
                        metadata = json.loads(content)
                        print(f"     • Last cached: {metadata.get('saved_at', 'unknown')}")
                        print(f"     • Buildings: {metadata.get('building_count', 0)}")
                print()
else:
    print(f"❌ Failed to connect: {result}")
```

### Run it:
```bash
python list_nucleus_cache.py
```

---

## Method 4: Check Application Logs

The Shadow Analyzer logs every cache operation.

### Steps:

1. **Find the log file**:
   ```
   c:\Users\peter\omniverse\kit-app-template\_build\windows-x86_64\release\logs\Kit\city.shadow_analyzer.kit\0.1\kit_YYYYMMDD_HHMMSS.log
   ```

2. **Search for cache operations**:
   - `"NUCLEUS CACHE HIT"` - Successfully loaded from cache
   - `"Cache miss"` - Data not in cache, querying OSM
   - `"Saved to Nucleus cache"` - Successfully cached data
   - `"Successfully cached to:"` - Shows the Nucleus path

3. **Example log entries**:
   ```
   [BuildingLoader] ✅ NUCLEUS CACHE HIT - Loading from: omniverse://nucleus.../city_37N_122W/buildings_abc123.usd
   [CityCacheManager] Cache HIT for (37.7749, -122.4194)
   [CityCacheManager] Contains 1523 buildings
   [CityCacheManager] Cached data from: 2026-01-16T22:45:00Z
   ```

---

## Method 5: Test Cache Hit/Miss

The best way to validate caching is to test it!

### Test Procedure:

1. **First Load (Cache Miss)**:
   - In Shadow Analyzer, load a new location (e.g., San Francisco)
   - Note the time it takes: **~30-60 seconds**
   - Check logs for: `"Cache miss"` and `"Successfully cached"`

2. **Close and Reopen** the application

3. **Second Load (Cache Hit)**:
   - Load the **SAME** location again
   - Note the time it takes: **~2-5 seconds** ← **10-20x faster!**
   - Check logs for: `"✅ NUCLEUS CACHE HIT"`

4. **Verify in Nucleus Web Navigator**:
   - Browse to `/Projects/CityData/city_37N_122W/`
   - You should see the `.usd` and `.meta.json` files created

---

## Troubleshooting

### No files in Nucleus?

**Current Status**: The caching code is wired up but not yet fully integrated.

The BuildingLoader currently:
- ✅ Checks if cache exists
- ✅ Logs "NUCLEUS CACHE HIT" if found
- ⚠️ But still falls back to OSM query (USD loading not complete)

**What's needed**: Complete Task 1 integration to actually load USD from cache instead of falling back.

### Can't access Web Navigator?

Try the direct API check:
```bash
curl -u "omniverse:Letmeinletmein12" \
  https://nucleus.swedencentral.cloudapp.azure.com/api/repo/v1/list?path=/Projects/CityData
```

### Connection refused?

Check if ports are open on Azure NSG:
- Port 443 (HTTPS) for Web Navigator
- Port 3030 (LFT) for Omniverse client
- Port 3333 (Discovery) for Omniverse client

---

## Summary

**Easiest way right now**: Open the Nucleus Web Navigator in your browser!

**Best validation**: Do a load test (first load = slow, second load = fast)

**Current state**: Infrastructure ready, full integration pending completion of Task 1.
