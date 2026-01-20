# Nucleus Testing Guide

This guide explains how to test if Nucleus is running and verify the integration works.

## 🔍 Quick Check Methods

### Method 1: Check the Nucleus Status Window (EASIEST)

When you launch the Shadow Analyzer app, a **"Nucleus Status"** window will appear showing:

- ✅ **Connected** = Nucleus is running and accessible
- ⚠️ **Not Connected** = Nucleus is not running or not accessible

The window shows:
- Connection status (green = connected, yellow = not connected)
- Server URL (default: `omniverse://localhost`)
- Project path (default: `/Projects/CityData`)
- A "Test Connection" button to recheck the connection

### Method 2: Check the Console Logs

Look at the console output when the app starts. You'll see:

**If Nucleus IS running:**
```
[city.shadow_analyzer.nucleus] ✅ Successfully connected to Nucleus
[city.shadow_analyzer.nucleus] Server: omniverse://localhost
[city.shadow_analyzer.nucleus] Project Path: /Projects/CityData
```

**If Nucleus is NOT running:**
```
[city.shadow_analyzer.nucleus] ⚠️  No Nucleus connection available - running in local mode
```

### Method 3: Test from Windows

Open PowerShell and run:
```powershell
# Check if Nucleus service is running
Get-Process | Where-Object {$_.ProcessName -like "*nucleus*"}
```

If you see processes, Nucleus is running. If not, it needs to be started.

## 🚀 Starting Nucleus

### Option 1: Omniverse Launcher (Recommended)

1. Open **Omniverse Launcher**
2. Go to the **Nucleus** tab
3. Click **"Start Local Nucleus"** or **"Install"** if not installed
4. Wait for it to show "Running"
5. Default server will be at: `omniverse://localhost`

### Option 2: Manual Start

If you have Nucleus installed but not running:
1. Find Nucleus installation (usually `C:\Users\<username>\AppData\Local\ov\pkg\nucleus-*`)
2. Run the Nucleus executable
3. Check that it starts on port 3009 (default)

## 🧪 Testing the Integration

### Step 1: Launch the App

```bash
# In VS Code, run the "Launch" task, or:
.\repo.bat launch -- source/apps/city.shadow_analyzer.kit.kit
```

### Step 2: Check the Nucleus Status Window

Look for the "Nucleus Status" window that automatically appears.

### Step 3: Test Connection Button

Click the **"Test Connection"** button in the Nucleus Status window to verify:
- If successful: ✅ "Connection successful!" appears
- If failed: ⚠️ "Connection failed. Is Nucleus running?" appears

### Step 4: Test Cache Operations (Manual Test)

Once connected, you can test cache operations by:

1. Load buildings in Shadow Analyzer (select a location)
2. Check console for cache messages:
   ```
   [CityCacheManager] Cache miss for location...
   [CityCacheManager] Saving to Nucleus cache...
   [CityCacheManager] Successfully saved to: omniverse://localhost/Projects/CityData/...
   ```
3. Load the SAME location again - should see:
   ```
   [CityCacheManager] Cache hit! Loading from Nucleus...
   [CityCacheManager] Loaded in X.XX seconds (vs Y.YY seconds from OSM)
   ```

## 📊 Expected Results

### With Nucleus Running:
- Status window shows: ✅ Connected
- Console shows connection success
- Cache operations save to Nucleus
- Subsequent loads are 10x faster (cache hit)

### Without Nucleus:
- Status window shows: ⚠️ Not Connected
- Console shows warning about local mode
- App still works (falls back to OSM every time)
- No performance improvement from caching

## 🔧 Troubleshooting

### "Not Connected" but Nucleus is Running

1. Check the server URL in `city.shadow_analyzer.kit.kit`:
   ```toml
   exts."city.shadow_analyzer.nucleus".nucleus_server = "omniverse://localhost"
   ```

2. Verify Nucleus is on port 3009:
   ```powershell
   netstat -ano | findstr "3009"
   ```

3. Check firewall settings (Windows may block localhost connections)

### Extension Not Loading

1. Check console for errors during startup
2. Verify extension is enabled in the app config:
   ```toml
   "city.shadow_analyzer.nucleus" = {}
   ```
3. Run `.\repo.bat build` to rebuild

### No Nucleus Status Window

1. Check if `omni.ui` dependency is installed
2. Look for errors in console about window creation
3. Try Window > Extensions and manually enable "City Shadow Analyzer - Nucleus Integration"

## 📝 Next Steps

Once Nucleus is confirmed working:
1. ✅ Phase 1 is complete (core integration)
2. 🔄 Ready for Phase 2 (UI integration with building loader)
3. 🎯 Next: Integrate caching into the building loader for automatic caching

## 💡 Pro Tips

- **Keep the Nucleus Status window visible** while testing - it updates when you click "Test Connection"
- **Check the console logs** - they show detailed information about cache hits/misses
- **First load will be slow** (fetching from OSM) - second load of same area should be fast (cache hit)
- **The cache is persistent** - even after restarting the app, cached data remains in Nucleus
