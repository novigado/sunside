# How to Test the Nucleus Status Window

## Quick Summary
The Nucleus extension is **configured and built**, but you need to **launch the app** to see it in action.

## Current Status
✅ Nucleus extension registered and configured
✅ Build successful
⚠️ App not currently running (last log from 18:30:34, build phase)

## How to Launch & Test

### Step 1: Launch the Shadow Analyzer UI App

**Option A: Use VS Code Task**
1. Press `Ctrl+Shift+P` (Command Palette)
2. Type "Run Task"
3. Select **"Launch"** (NOT "Launch (Developer Mode)")
4. Wait for the app to start

**Option B: Use Terminal** (in a NEW terminal, not the one running the app)
```powershell
.\repo.bat launch -- source/apps/city.shadow_analyzer.kit.kit
```

### Step 2: Look for the Nucleus Status Window

Once the app launches, you should see:
- A new window titled **"Nucleus Status"**
- Connection status: ✅ Connected OR ⚠️ Not Connected
- Server URL: `omniverse://localhost`
- Project path: `/Projects/CityData`
- A blue "Test Connection" button

### Step 3: Check the Console Output

In the terminal where the app is running, search for these messages:

**If Nucleus IS running:**
```
[city.shadow_analyzer.nucleus] ✅ Successfully connected to Nucleus
[city.shadow_analyzer.nucleus] Server: omniverse://localhost
[city.shadow_analyzer.nucleus] Project Path: /Projects/CityData
```

**If Nucleus is NOT running:**
```
[city.shadow_analyzer.nucleus] ⚠️ No Nucleus connection available - running in local mode
```

## Troubleshooting

### "I don't see the Nucleus Status window"

1. **Check Window menu**: Go to `Window` menu → look for "Nucleus Status"
2. **Check console for errors**: Look for errors containing `city.shadow_analyzer.nucleus`
3. **Verify extension loaded**: Search console for `[ext: city.shadow_analyzer.nucleus-0.1.0] startup`

### "Window says Not Connected"

1. **Install Nucleus**: Open Omniverse Launcher → Nucleus tab → Install/Start Local Nucleus
2. **Check if Nucleus is running**:
   ```powershell
   # In a NEW PowerShell window:
   Get-Process | Where-Object {$_.ProcessName -like "*nucleus*"}
   ```
3. **Test connection**: Click the "Test Connection" button in the Nucleus Status window

### "Extension not loading at all"

1. **Rebuild**: Stop the app, run `.\repo.bat build`
2. **Check the app config**: Verify `city.shadow_analyzer.kit.kit` includes:
   ```toml
   "city.shadow_analyzer.nucleus" = {}
   ```
3. **Check logs**: Look in `_build/windows-x86_64/release/logs/Kit/city.shadow_analyzer.kit/0.1/` for the latest log file

## What You Should See

### With Nucleus Running:
```
┌─────────────────────────────────────┐
│     Nucleus Integration Status      │
├─────────────────────────────────────┤
│ Connection:     ✅ Connected         │
│ Server:         omniverse://localhost│
│ Project Path:   /Projects/CityData   │
│                                      │
│  [      Test Connection      ]       │
│                                      │
│ ✅ Connection successful!            │
└─────────────────────────────────────┘
```

### Without Nucleus:
```
┌─────────────────────────────────────┐
│     Nucleus Integration Status      │
├─────────────────────────────────────┤
│ Connection:     ⚠️ Not Connected     │
│ Server:         omniverse://localhost│
│ Project Path:   /Projects/CityData   │
│                                      │
│  [      Test Connection      ]       │
│                                      │
│ ⚠️ Connection failed. Is Nucleus     │
│    running?                          │
└─────────────────────────────────────┘
```

## Next Steps After Confirming

Once you see the window and verify connection status:
1. If connected → Phase 1 is complete! ✅
2. If not connected → Follow NUCLEUS_TESTING_GUIDE.md to start Nucleus
3. Ready for Phase 2 → Integrate caching into building loader

## Key Files Modified

- `source/extensions/city.shadow_analyzer.nucleus/city/shadow_analyzer/nucleus/extension.py` - Added UI window
- `source/extensions/city.shadow_analyzer.nucleus/extension.toml` - Added omni.ui dependency
- `source/apps/city.shadow_analyzer.kit.kit` - Already configured (no changes needed)
