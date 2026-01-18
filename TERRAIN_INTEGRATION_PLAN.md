# Terrain Elevation Integration Plan

**Branch**: `feature/terrain-elevation-integration`  
**Created**: 2026-01-18  
**Status**: Planning

## Objective

Re-enable terrain loading and fix the building/terrain elevation coordination issue where:
- Buildings appear partially buried when terrain elevation is above Y=0
- Buildings appear floating when terrain elevation is below Y=0
- Semi-transparent terrain made buildings hard to see

## Current State

### What Works
✅ GPS coordinate accuracy - markers appear at correct locations  
✅ Buildings and roads properly aligned (share same reference point)  
✅ Shadow analysis works correctly  
✅ Query markers visible with appropriate size (3m radius)  

### What's Disabled
❌ Terrain loading temporarily commented out in `_load_map_with_terrain()`  
❌ Buildings load flat on Y=0 ground plane  
❌ No elevation data visualization  

## Problem Analysis

### Root Cause
Buildings are created with base vertices at Y=0 (flat ground), but terrain mesh has actual elevation data that can be above or below Y=0. The adjustment function `_adjust_buildings_for_terrain()` tries to lift buildings after the fact, but this has issues.

### Current Approach (Problematic)
1. Load buildings at Y=0
2. Load terrain with elevation data
3. Try to adjust building vertices to match terrain elevation
4. Issues: timing, vertex detection, base elevation calculation

## Proposed Solutions

### Option 1: Load Terrain First, Then Buildings at Terrain Elevation
**Pros**: Clean - buildings created at correct elevation from the start  
**Cons**: Terrain loader needs building reference point (circular dependency)

**Steps**:
1. Calculate reference point from building data WITHOUT creating buildings
2. Load terrain with this reference point
3. Create buildings, querying terrain elevation for base vertices

### Option 2: Create Buildings with Elevation Offset
**Pros**: Simple - just add elevation offset during building creation  
**Cons**: Need to query terrain elevation API during building creation

**Steps**:
1. Load buildings and terrain data from APIs
2. Calculate average terrain elevation for the area
3. Create ground plane at this average elevation
4. Create buildings with base at average elevation
5. Load terrain mesh (may have hills/valleys around base)

### Option 3: Improve Current Adjustment Approach
**Pros**: Minimal code changes  
**Cons**: Still doing adjustment after creation (complexity)

**Steps**:
1. Fix vertex detection in `_adjust_buildings_for_terrain()`
2. Ensure terrain is loaded before adjustment runs
3. Improve base elevation calculation
4. Test with various terrain profiles

### Option 4: Flat Ground Only (No Terrain)
**Pros**: Simplest - everything works now  
**Cons**: No realistic elevation visualization

**Steps**:
1. Keep terrain loading disabled
2. Document as limitation
3. Focus on other features

## Recommended Approach

**Option 2**: Create buildings with elevation offset

**Rationale**:
- Avoids vertex manipulation after creation
- Buildings created correctly from the start
- Terrain is decorative - doesn't need perfect vertex-level accuracy
- Average elevation good enough for shadow analysis

## Implementation Plan

### Phase 1: Calculate Average Terrain Elevation
- [ ] Add function to get average elevation from terrain data
- [ ] Store as scene metadata alongside reference point

### Phase 2: Modify Building Creation
- [ ] Pass elevation offset to `create_building_mesh()`
- [ ] Adjust base vertices during creation (Y = 0 + elevation_offset)
- [ ] Top vertices (Y = height + elevation_offset)

### Phase 3: Modify Ground Plane
- [ ] Create ground plane at average elevation instead of Y=0
- [ ] Or skip ground plane entirely if terrain is loaded

### Phase 4: Re-enable Terrain Loading
- [ ] Uncomment terrain loading in `_load_map_with_terrain()`
- [ ] Test with buildings at elevated base

### Phase 5: Marker Elevation
- [ ] Update marker creation to use terrain elevation at query point
- [ ] Query terrain at marker X,Z position, use that Y value

## Testing Checklist

- [ ] Load buildings and terrain together
- [ ] Verify buildings sit properly on terrain (not buried/floating)
- [ ] Check shadow analysis accuracy with elevation
- [ ] Test query markers at various elevations
- [ ] Verify camera framing works with elevated scene
- [ ] Test coordinate accuracy still correct with elevation

## Success Criteria

1. ✅ Buildings appear to sit naturally on terrain surface
2. ✅ No visible floating or burial artifacts
3. ✅ Shadow analysis accounts for elevation differences
4. ✅ Query markers appear at correct GPS location AND elevation
5. ✅ Terrain visually enhances the scene (not distracting)

## Notes

- Terrain elevation in Gothenburg area is relatively flat (~0-50m variation)
- High accuracy not critical - visual realism is the goal
- Shadow ray casting works in 3D, so elevation is helpful for accuracy
- Consider making terrain loading optional in UI (checkbox)
