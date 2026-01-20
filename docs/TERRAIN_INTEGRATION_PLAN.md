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
 GPS coordinate accuracy - markers appear at correct locations
 Buildings and roads properly aligned (share same reference point)
 Shadow analysis works correctly
 Query markers visible with appropriate size (3m radius)

### What's Disabled
 Terrain loading temporarily commented out in `_load_map_with_terrain()`
 Buildings load flat on Y=0 ground plane
 No elevation data visualization

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

**Option 1**: Load Terrain First, Then Buildings at Terrain Elevation

**Rationale**:
- Cleanest approach - buildings created at correct elevation from start
- Terrain and buildings share exact same reference point (critical for alignment)
- Buildings can query terrain elevation during creation for precise placement
- No circular dependency - calculate reference from raw building data first
- Ensures terrain is positioned correctly with buildings and roads

## Implementation Plan

### Phase 1: Add Reference Point Calculation Helper
- [x] Add `calculate_reference_point_from_buildings()` static method
- [x] Returns (lat, lon) without creating any geometry
- [x] Used by both terrain and building creation

### Phase 2: Modify Load Sequence
- [ ] Load building/road data from OpenStreetMap API
- [ ] Calculate reference point from building data
- [ ] Load terrain with this reference point
- [ ] Create terrain mesh (positioned at reference point)
- [ ] Create buildings, querying terrain elevation for each building's base
- [ ] Create roads using terrain elevation

### Phase 3: Add Terrain Elevation Query
- [ ] Add method to `TerrainMeshGenerator` or `BuildingGeometryConverter`
- [ ] Given (X, Z) scene coords, return terrain Y elevation
- [ ] Use during building/road creation

### Phase 4: Modify Building Creation
- [ ] Pass terrain mesh/elevation data to building creation
- [ ] For each building, query terrain elevation at its base position
- [ ] Create base vertices at terrain elevation (not Y=0)
- [ ] Top vertices at terrain elevation + building height

### Phase 5: Update Ground Plane Logic
- [ ] Skip ground plane creation if terrain is loaded
- [ ] Or create ground plane at minimum terrain elevation

## Testing Checklist

- [ ] Load buildings and terrain together
- [ ] Verify buildings sit properly on terrain (not buried/floating)
- [ ] Check shadow analysis accuracy with elevation
- [ ] Test query markers at various elevations
- [ ] Verify camera framing works with elevated scene
- [ ] Test coordinate accuracy still correct with elevation

## Success Criteria

1.  Buildings appear to sit naturally on terrain surface
2.  No visible floating or burial artifacts
3.  Shadow analysis accounts for elevation differences
4.  Query markers appear at correct GPS location AND elevation
5.  Terrain visually enhances the scene (not distracting)

## Notes

- Terrain elevation in Gothenburg area is relatively flat (~0-50m variation)
- High accuracy not critical - visual realism is the goal
- Shadow ray casting works in 3D, so elevation is helpful for accuracy
- Consider making terrain loading optional in UI (checkbox)
