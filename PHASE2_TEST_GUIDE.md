# Phase 2 Caching - Test Guide 🧪

**Test Date**: January 17, 2025
**Build Status**: ✅ Build Successful
**Server**: nucleus.swedencentral.cloudapp.azure.com
**Connection**: ✅ Connected

---

## Quick Test Plan

### Test 1: Building Cache (San Francisco)

#### First Load - Cache Miss
1. **Launch app** and wait for both windows to appear
2. **Enter coordinates**: `37.7749, -122.4194` (San Francisco)
3. **Click**: "Load Buildings from OpenStreetMap"
4. **Expected**: 30-60 seconds
5. **Watch logs** for:
   ```
   ❌ Cache miss, loading from OpenStreetMap...
   Loading buildings from OpenStreetMap...
   💾 Saving scene to Nucleus cache...
   ✅ Saved to Nucleus: omniverse://nucleus.../buildings_xxxxx.usd
   ```

#### Second Load - Cache Hit
1. **Close app** (important - must close and relaunch)
2. **Relaunch app**
3. **Enter same coordinates**: `37.7749, -122.4194`
4. **Click**: "Load Buildings from OpenStreetMap"
5. **Expected**: 2-5 seconds ← **10-20x FASTER!** 🚀
6. **Watch logs** for:
   ```
   🔍 Checking Nucleus cache for (37.77490, -122.41940)...
   ✅ CACHE HIT! Loading from Nucleus...
   Cache metadata: {building_count: ..., road_count: ...}
   ```

### Test 2: Terrain Cache (San Francisco)

#### First Load - Cache Miss
1. **Click**: "Load Terrain Elevation Data"
2. **Expected**: 10-20 seconds
3. **Watch logs** for:
   ```
   ❌ Terrain cache miss, loading from Open-Elevation API...
   Querying 400 elevation points...
   Creating terrain mesh...
   💾 Saving terrain to Nucleus cache...
   ✅ Saved terrain to Nucleus: omniverse://nucleus.../terrain_xxxxx_20.usd
   ```

#### Second Load - Cache Hit
1. **Close and relaunch app**
2. **Enter coordinates**: `37.7749, -122.4194`
3. **Click**: "Load Terrain Elevation Data"
4. **Expected**: 2-3 seconds ← **5-10x FASTER!** 🚀
5. **Watch logs** for:
   ```
   🔍 Checking Nucleus terrain cache for (37.77490, -122.41940)...
   ✅ TERRAIN CACHE HIT! Loading from Nucleus...
   Terrain cache metadata: {min_elevation: ..., max_elevation: ...}
   ```

### Test 3: Combined Load (Map with Terrain & Buildings)

#### First Load - Both Cache Miss
1. **Enter coordinates**: `40.7128, -74.0060` (New York - fresh location)
2. **Click**: "Load Map with Terrain & Buildings"
3. **Expected**: 40-70 seconds (both queries)
4. **Watch logs** for both cache saves

#### Second Load - Both Cache Hit
1. **Close and relaunch app**
2. **Enter same coordinates**: `40.7128, -74.0060`
3. **Click**: "Load Map with Terrain & Buildings"
4. **Expected**: 5-10 seconds ← **8-10x FASTER!** 🚀
5. **Watch logs** for both cache hits

---

## Verification Checklist

### During Test
- [ ] Both windows show (Nucleus Status + Shadow Analyzer)
- [ ] Nucleus Status shows: "✅ Connected"
- [ ] Coordinates entered correctly
- [ ] Console window visible for logs
- [ ] Timing measured (stopwatch or estimate)

### After First Load
- [ ] Buildings/terrain appear in viewport
- [ ] Status text shows success
- [ ] Console shows "✅ Saved to Nucleus" messages
- [ ] No error messages

### Web Navigator Verification
1. Open: https://nucleus.swedencentral.cloudapp.azure.com/navigator
2. Navigate: `/Projects/CityData/`
3. Look for folders:
   - `city_37N_122W/` (San Francisco)
   - `city_40N_74W/` (New York)
4. Inside each folder:
   - `buildings_xxxxx.usd` + `.meta.json`
   - `terrain_xxxxx_20.usd` + `.meta.json`

### After Second Load
- [ ] Much faster loading time (2-10 seconds)
- [ ] Console shows "✅ CACHE HIT!" messages
- [ ] Console does NOT show OSM/API queries
- [ ] Scene looks identical to first load
- [ ] No errors in console

---

## Expected Console Output Examples

### Building Cache Hit:
```
[Shadow Analyzer] 🔍 Checking Nucleus cache for (37.77490, -122.41940)...
[Shadow Analyzer] ✅ CACHE HIT! Loading from Nucleus...
[Shadow Analyzer] Cache metadata: {'building_count': 1523, 'road_count': 45, ...}
[Shadow Analyzer] Copying cached geometry to scene...
[Shadow Analyzer]   ✓ Copied Buildings
[Shadow Analyzer]   ✓ Copied Roads
[Shadow Analyzer]   ✓ Copied Ground
[Shadow Analyzer] Finished copying cached geometry
```

### Building Cache Miss:
```
[Shadow Analyzer] 🔍 Checking Nucleus cache for (37.77490, -122.41940)...
[Shadow Analyzer] ❌ Cache miss, loading from OpenStreetMap...
[BuildingLoader] Loading buildings from OpenStreetMap...
[BuildingLoader] Found 1523 buildings, 45 roads
[Shadow Analyzer] Creating 1523 buildings...
[Shadow Analyzer] 💾 Saving scene to Nucleus cache...
[Shadow Analyzer] Exporting scene to temporary stage...
[Shadow Analyzer]   ✓ Exported Buildings
[Shadow Analyzer]   ✓ Exported Roads
[Shadow Analyzer]   ✓ Exported Ground
[Shadow Analyzer] ✅ Saved to Nucleus: omniverse://nucleus.../buildings_abc123.usd
```

### Terrain Cache Hit:
```
[Shadow Analyzer] 🔍 Checking Nucleus terrain cache for (37.77490, -122.41940)...
[Shadow Analyzer] ✅ TERRAIN CACHE HIT! Loading from Nucleus...
[Shadow Analyzer] Terrain cache metadata: {'min_elevation': 45.2, 'max_elevation': 89.7, ...}
[Shadow Analyzer] Copying cached terrain to scene...
[Shadow Analyzer]   ✓ Copied Terrain
```

### Terrain Cache Miss:
```
[Shadow Analyzer] 🔍 Checking Nucleus terrain cache for (37.77490, -122.41940)...
[Shadow Analyzer] ❌ Terrain cache miss, loading from Open-Elevation API...
[TerrainLoader] Loading elevation grid at (37.7749, -122.4194)...
[TerrainLoader] Querying 400 elevation points...
[TerrainLoader] Elevation range: 45.2m to 89.7m
[Shadow Analyzer] Creating terrain mesh...
[Shadow Analyzer] 💾 Saving terrain to Nucleus cache...
[Shadow Analyzer] ✅ Saved terrain to Nucleus: omniverse://nucleus.../terrain_def456_20.usd
```

---

## Performance Metrics to Record

| Test | First Load (Cache Miss) | Second Load (Cache Hit) | Speedup |
|------|-------------------------|-------------------------|---------|
| Buildings Only | ___ seconds | ___ seconds | ___x |
| Terrain Only | ___ seconds | ___ seconds | ___x |
| Combined | ___ seconds | ___ seconds | ___x |

**Target Speedups**:
- Buildings: 10-20x faster
- Terrain: 5-10x faster
- Combined: 8-10x faster

---

## Troubleshooting

### If cache hit doesn't work:
1. Check Nucleus Status window shows "✅ Connected"
2. Verify exact same coordinates used (37.7749, -122.4194)
3. Check Web Navigator for cache files
4. Look for errors in console
5. Verify app was closed and relaunched between tests

### If files don't appear in Nucleus:
1. Check console for "✅ Saved to Nucleus" message
2. Look for error messages about authentication
3. Verify network connection to Azure VM
4. Check Nucleus web navigator (may need to refresh)

### If build errors occur:
1. Run: `.\repo.bat build` again
2. Check for Python syntax errors
3. Verify all extensions enabled

---

## Success Criteria ✅

After testing, these should all be true:

- [ ] **First load works** (30-70 seconds depending on test)
- [ ] **Cache files created** in Nucleus (visible in web navigator)
- [ ] **Second load much faster** (2-10 seconds)
- [ ] **Console shows cache hit messages**
- [ ] **No errors** in console
- [ ] **Scene identical** between loads
- [ ] **Metadata correct** (building counts, elevations)
- [ ] **10-20x speedup** for buildings achieved
- [ ] **5-10x speedup** for terrain achieved

---

## Next Steps After Testing

1. **Record actual timings** in performance metrics table
2. **Screenshot** cache files in Web Navigator
3. **Update** PHASE2_TASK1_COMPLETE.md with actual results
4. **Commit** the working implementation
5. **Continue** to Task 2 (Cache Statistics UI)

---

**Test Status**: 🧪 Ready to test

Good luck! The caching should dramatically improve load times on the second attempt. 🚀
