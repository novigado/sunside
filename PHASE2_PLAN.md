# Phase 2 Implementation Plan - Building Loader Nucleus Caching

## Status: 🚀 IN PROGRESS

## Objectives

Integrate Nucleus caching into the BuildingLoader and terrain system to automatically cache and retrieve:
- **Building data** (from OpenStreetMap)
- **Terrain elevation data** (from Open-Elevation API)

Providing 10-20x performance improvement for repeated queries.

## What We're Building

Transform both BuildingLoader and terrain system from always querying external APIs to intelligently using Nucleus cache:

**Before (Current)**:
```python
# Buildings: Every time query OSM (30-60s)
buildings = osm_service.get_buildings(bounds)
geometry = create_usd_geometry(buildings)

# Terrain: Every time query Open-Elevation (10-20s)
elevation_data = elevation_service.get_elevation(bounds, resolution)
terrain_mesh = create_terrain_mesh(elevation_data)
```

**After (Phase 2)**:
```python
# Buildings: First time (30-60s + 2s), subsequent (2-5s) ← 10-20x faster!
if nucleus_cache.has_buildings(bounds):
    geometry = nucleus_cache.load_buildings(bounds)
else:
    buildings = osm_service.get_buildings(bounds)
    geometry = create_usd_geometry(buildings)
    nucleus_cache.save_buildings(bounds, geometry)

# Terrain: First time (10-20s + 2s), subsequent (2-5s) ← 5-10x faster!
if nucleus_cache.has_terrain(bounds):
    terrain_mesh = nucleus_cache.load_terrain(bounds)
else:
    elevation_data = elevation_service.get_elevation(bounds, resolution)
    terrain_mesh = create_terrain_mesh(elevation_data)
    nucleus_cache.save_terrain(bounds, terrain_mesh)
```

## Implementation Tasks

### Task 1: Update BuildingLoader

**File**: `source/extensions/city.shadow_analyzer.buildings/city/shadow_analyzer/buildings/building_loader.py`

**Changes**:
1. Import CityCacheManager and get NucleusManager singleton
2. Add cache checking before OSM query
3. Load from Nucleus if cache hit
4. Save to Nucleus after OSM fetch (cache miss)
5. Add logging for cache hits/misses

**Methods to modify**:
- `__init__()` - Initialize cache manager
- `load_buildings_for_area()` - Add cache logic
- New helper: `_generate_cache_key()` - Create bounds hash
- New helper: `_load_from_nucleus()` - Load cached USD
- New helper: `_save_to_nucleus()` - Save USD to cache

### Task 1b: Update Terrain System

**File**: `source/extensions/city.shadow_analyzer.buildings/city/shadow_analyzer/buildings/building_loader.py`

**Changes**:
1. Add terrain cache checking before elevation API query
2. Load terrain from Nucleus if cache hit
3. Save terrain to Nucleus after elevation fetch (cache miss)
4. Use separate cache keys for terrain vs buildings
5. Add logging for terrain cache hits/misses

**Methods to modify**:
- `load_terrain()` or terrain loading method - Add cache logic
- New helper: `_generate_terrain_cache_key()` - Create bounds + resolution hash
- New helper: `_load_terrain_from_nucleus()` - Load cached terrain mesh
- New helper: `_save_terrain_to_nucleus()` - Save terrain mesh to cache

**Cache key for terrain**:
```python
# Include resolution in terrain cache key
terrain_key = f"{north:.6f},{south:.6f},{east:.6f},{west:.6f},res{resolution}"
terrain_hash = hashlib.md5(terrain_key.encode()).hexdigest()[:16]
```

### Task 2: Add Cache Statistics UI

**File**: `source/extensions/city.shadow_analyzer.nucleus/city/shadow_analyzer/nucleus/extension.py`

**Changes**:
1. Add cache statistics section to Nucleus Status window
2. Show cache hit/miss ratio
3. Show number of cached cities
4. Add "Clear Cache" button
5. Add "Refresh Stats" button

**New UI elements**:
- Cache Hit Rate: X% (Y hits / Z total)
- Cached Cities: N cities
- Last Cache Hit: timestamp
- Buttons: [Clear Cache] [Refresh Stats]

### Task 3: Add Global Nucleus Manager Singleton

**File**: `source/extensions/city.shadow_analyzer.nucleus/city/shadow_analyzer/nucleus/__init__.py`

**Changes**:
1. Create global NucleusManager instance
2. Add `get_nucleus_manager()` function
3. Ensure thread-safe singleton pattern
4. Handle extension lifecycle

**API**:
```python
from city.shadow_analyzer.nucleus import get_nucleus_manager

nucleus_mgr = get_nucleus_manager()
cache = CityCacheManager(nucleus_mgr)
```

### Task 4: Handle USD Stage Export/Import

**File**: `source/extensions/city.shadow_analyzer.nucleus/city/shadow_analyzer/nucleus/city_cache.py`

**Changes**:
1. Implement USD stage serialization
2. Handle temporary file creation for export
3. Implement USD stage deserialization
4. Error handling for corrupt cache

**Methods to complete**:
- `save_to_cache()` - Export stage to USD string
- `load_from_cache()` - Import USD string to stage
- Helper: `_serialize_stage()` - Convert stage to string
- Helper: `_deserialize_stage()` - Convert string to stage

### Task 5: Add Cache Key Generation

**File**: `source/extensions/city.shadow_analyzer.buildings/city/shadow_analyzer/buildings/building_loader.py`

**Changes**:
1. Generate consistent hash from bounds
2. Include radius/area in hash
3. Optionally include city name
4. Handle floating point precision

**Hash input**:
```python
bounds_str = f"{north:.6f},{south:.6f},{east:.6f},{west:.6f},{radius:.3f}"
bounds_hash = hashlib.md5(bounds_str.encode()).hexdigest()[:16]
```

### Task 6: Update Documentation

**Files to update**:
- `PHASE2_SUMMARY.md` - Create completion summary
- `README.md` - Update with caching info
- Code comments - Add docstrings

## Success Criteria

### Performance
- ✅ First load: ~30-60 seconds (OSM fetch + cache save)
- ✅ Second load: ~2-5 seconds (Nucleus cache hit)
- ✅ Performance improvement: 10-20x faster

### Functionality
- ✅ Cache automatically checks before OSM query
- ✅ Cache saves automatically after OSM query
- ✅ Cache hit/miss logged to console
- ✅ Works without Nucleus (graceful fallback to OSM)
- ✅ Multiple cities cached independently

### User Experience
- ✅ No UI changes required (automatic behind the scenes)
- ✅ Cache statistics visible in Nucleus Status window
- ✅ Clear indication of cache hits in logs
- ✅ First load shows "Caching..." message
- ✅ Subsequent loads show "Loading from cache..."

## Testing Plan

### Manual Tests

1. **First Load (Cache Miss)**:
   - Launch Shadow Analyzer
   - Load Manhattan area
   - Check logs: "Cache miss for manhattan"
   - Check logs: "Saved to Nucleus cache"
   - Time: ~30-60 seconds

2. **Second Load (Cache Hit)**:
   - Restart Shadow Analyzer
   - Load SAME Manhattan area
   - Check logs: "Cache hit! Loading from Nucleus"
   - Time: ~2-5 seconds ✅

3. **Different Area (Cache Miss)**:
   - Load Brooklyn area (different bounds)
   - Check logs: "Cache miss for brooklyn"
   - Check logs: "Saved to Nucleus cache"

4. **Without Nucleus (Fallback)**:
   - Stop Nucleus server
   - Launch Shadow Analyzer
   - Load area - should work (direct OSM query)
   - Check logs: "Nucleus not available, querying OSM"

5. **Cache Statistics**:
   - Open Nucleus Status window
   - Check cache hit rate displayed
   - Click "Refresh Stats" - numbers update
   - Load multiple areas - watch stats increase

### Automated Tests (Future)

```python
def test_cache_miss_then_hit():
    # First load
    loader.load_buildings_for_area(lat, lon, radius)
    assert cache_stats['misses'] == 1

    # Second load
    loader.load_buildings_for_area(lat, lon, radius)
    assert cache_stats['hits'] == 1

def test_fallback_without_nucleus():
    nucleus_manager.disconnect()
    buildings = loader.load_buildings_for_area(lat, lon, radius)
    assert buildings is not None
```

## Implementation Order

1. ✅ **Task 3** - Global singleton (enables all other tasks)
2. ✅ **Task 4** - USD export/import (enables caching)
3. ✅ **Task 5** - Cache key generation (enables lookups)
4. ✅ **Task 1** - BuildingLoader integration (core feature)
5. ✅ **Task 2** - Statistics UI (visibility)
6. ✅ **Task 6** - Documentation (completion)

## Timeline Estimate

- Task 3: 30 minutes (singleton pattern)
- Task 4: 1 hour (USD serialization)
- Task 5: 30 minutes (hash generation)
- Task 1: 2 hours (BuildingLoader logic)
- Task 2: 1 hour (UI updates)
- Task 6: 30 minutes (docs)

**Total: ~5-6 hours**

## Risks & Mitigations

### Risk: USD serialization complexity
**Mitigation**: Use temporary files, not in-memory strings

### Risk: Cache key collisions
**Mitigation**: Include sufficient precision in hash (6 decimal places for lat/lon)

### Risk: Stale cache data
**Mitigation**: Store timestamp in metadata, add "Refresh Cache" button

### Risk: Nucleus unavailable
**Mitigation**: Graceful fallback to OSM (already implemented in Phase 1)

## Phase 2 Deliverables

- ✅ Automatic caching in BuildingLoader
- ✅ 10-20x performance improvement for cached queries
- ✅ Cache statistics in UI
- ✅ Comprehensive logging
- ✅ Graceful fallback without Nucleus
- ✅ Documentation and tests

## Next Phase (Phase 3 - Future)

- Project-based organization
- Scenario comparison
- Team collaboration features
- Advanced cache management (TTL, refresh, etc.)

---

**Started**: January 16, 2026
**Branch**: `feature/nucleus-building-cache`
**Status**: Ready to implement! 🚀
