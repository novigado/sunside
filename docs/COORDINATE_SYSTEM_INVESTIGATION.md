# Coordinate System Reference Point Investigation

## Issue Description

After fixing the map orientation (Z-axis negation for north-south correction), the map displays correctly. However, when placing query markers at GPS coordinates, they appear in incorrect positions and shadow calculations don't work as expected.

**Symptoms:**
- Map terrain and buildings display with correct geographic orientation
- Query markers placed at GPS coordinates don't appear where expected
- Shadow calculations at marker positions are incorrect
- Markers that should be clearly visible on the map don't appear in the expected location

## Current Date
January 18, 2026

## Investigation History

### Previous Fixes (Completed)
1. **Button Restoration Issue** - Fixed in commit `54226d0`
   - "Load Map with Terrain & Buildings" button stuck in loading state
   - Solution: Added `from_combined_button` parameter to prevent individual button restoration

2. **Map Orientation Issue** - Fixed in commits `ff4666d`, `1e24007`, `a28eb2f`
   - Initial: Map appeared mirrored/flipped
   - First attempt: Negated both X and Z coordinates (180° rotation)
   - User feedback: Map looked mirrored again
   - Final solution: Only negate Z-axis (latitude/north-south), keep X-axis (longitude/east-west) normal
   - Result: Map now displays with correct geographic orientation

### Current Issue (In Progress)
**Problem**: Query marker placement and shadow calculations incorrect

**Observed Behavior:**
- User enters GPS coordinates in query fields
- System converts GPS → scene coordinates using geometry converter
- Marker is created at calculated scene position
- Marker doesn't appear in expected location relative to buildings
- Shadow calculation fails or gives wrong results

## Technical Context

### Coordinate Conversion System

The system uses three coordinate systems:

1. **GPS Coordinates** (Lat/Lon)
   - Latitude: -90° to 90° (negative = South, positive = North)
   - Longitude: -180° to 180° (negative = West, positive = East)
   - From OpenStreetMap data

2. **Scene Coordinates** (USD/Omniverse)
   - X-axis: East-West (increasing = East)
   - Y-axis: Elevation (up)
   - Z-axis: North-South (increasing = North, BUT negated in current implementation)
   - Origin: Set by reference point

3. **Reference Point**
   - The GPS coordinate that maps to scene origin (0, 0)
   - Set when buildings are loaded
   - Used for all subsequent GPS → scene coordinate conversions

### Current Coordinate Conversion Formula

In `geometry_converter.py` and `extension.py`:
```python
# Calculate offset from reference point
lat_diff = query_lat - reference_lat
lon_diff = query_lon - reference_lon

# Convert to meters
meters_per_lat_degree = 111000.0
meters_per_lon_degree = 111000.0 * math.cos(math.radians(lat))

# Convert to scene coordinates
x = lon_diff * meters_per_lon_degree       # X = East/West (normal)
z = -(lat_diff * meters_per_lat_degree)    # Z = North/South (negated)
y = elevation_value                         # Y = height
```

### Reference Point Management

**Building Loader** (`building_loader.py`):
- Calculates center of bounding box from all building coordinates
- Sets this as reference point: `geometry_converter.set_reference_point(center_lat, center_lon)`
- All buildings placed relative to this center

**Terrain Generator** (`terrain_generator.py`):
- Uses same reference point as buildings
- Generates terrain mesh with same coordinate conversion

**Query System** (`extension.py`):
- Uses map center coordinates (`self._latitude`, `self._longitude`) as reference
- These are set from UI input fields
- Converts query GPS to scene coordinates using these as reference

## Hypothesis: Reference Point Mismatch

**The Problem:**
The query system may be using a **different reference point** than the one used to place buildings.

**Why This Matters:**
- Buildings are centered at the **center of their bounding box** (calculated from OSM data)
- Query system uses **UI input coordinates** (`self._latitude`, `self._longitude`) as reference
- If these don't match, all coordinate conversions will be offset

**Example Scenario:**
```
OSM data for Gothenburg:
  - Buildings span from 57.70° to 57.75° N, 11.95° to 11.98° E
  - Center of bounding box: 57.725° N, 11.965° E
  - geometry_converter.reference_point = (57.725, 11.965)

UI coordinates:
  - User entered: 57.749254° N, 12.263287° E
  - extension.py uses: (57.749254, 12.263287) as reference

Query at 57.720° N, 11.960° E:
  - Building system: offset from (57.725, 11.965) = (-0.005°, -0.005°)
  - Query system: offset from (57.749254, 12.263287) = (-0.029254°, -0.303287°)
  - Result: Marker appears ~3 km south and ~26 km west of correct position!
```

## Possible Solutions

### Option 1: Share Reference Point (Recommended)
Make query system use the **same reference point** as buildings:
- After loading buildings, read `geometry_converter.reference_lat/lon`
- Use these values in query coordinate conversion
- Ensures perfect alignment

### Option 2: Update UI Reference
When buildings load, update UI fields to match building center:
- After loading, set `self._latitude` and `self._longitude` to building center
- User sees "actual" map center coordinates
- May confuse users if coordinates change automatically

### Option 3: Store Building Reference
Keep building reference point separate from UI coordinates:
- Add `self._building_reference_lat/lon` fields
- Set these when buildings load
- Use for all query conversions
- Keep UI fields for sun calculation only

## Next Steps

###  Solution Implemented (Commit 35c708d)

**Approach**: Option 3 - Store Building Reference (Modified)

The fix ensures the query system uses the **same reference point** as the buildings:

1. **Added geometry converter instance** to UI extension
   - Created `self._geometry_converter` field
   - Initialized when stage is available

2. **Load building reference point** before each query
   - Calls `load_reference_point_from_scene()` to read from building metadata
   - Falls back to UI coordinates if no buildings loaded
   - Logs which reference point is being used

3. **Use geometry converter** for coordinate conversion
   - Replaces manual calculation with `gps_to_scene_coords()`
   - Ensures consistency with building placement
   - Provides better error handling

**Code Changes**:
```python
# Initialize geometry converter if needed
if self._geometry_converter is None:
    self._geometry_converter = BuildingGeometryConverter(stage)

# Load reference point from buildings in scene
if not self._geometry_converter.load_reference_point_from_scene():
    # Fall back to UI coordinates if no buildings loaded
    self._geometry_converter.set_reference_point(self._latitude, self._longitude)

# Convert using same reference as buildings
x, z = self._geometry_converter.gps_to_scene_coords(
    self._query_latitude, self._query_longitude
)
```

**Benefits**:
-  Query markers align perfectly with buildings
-  Shadow calculations use correct positions
-  Works even if no buildings loaded (uses UI coordinates)
-  Clear logging shows which reference point is used
-  Reuses existing, tested coordinate conversion code

### Testing Required

1. **Load buildings** and place markers at known GPS coordinates
   - Verify markers appear at correct positions relative to buildings
   - Test multiple locations across the map

2. **Verify shadow calculations** work correctly
   - Place markers in sunlit areas
   - Place markers in shadowed areas
   - Verify results match visual rendering

3. **Test edge cases**
   - Query before loading buildings (should use UI coordinates)
   - Query after loading buildings (should use building center)
   - Load different map locations

## Files Involved

- `source/extensions/city.shadow_analyzer.buildings/city/shadow_analyzer/buildings/geometry_converter.py`
  - `set_reference_point()` - Sets reference lat/lon
  - `gps_to_scene_coords()` - Converts GPS to scene coordinates

- `source/extensions/city.shadow_analyzer.buildings/city/shadow_analyzer/buildings/building_loader.py`
  - Calculates building bounding box center
  - Sets reference point in geometry converter

- `source/extensions/city.shadow_analyzer.ui/city/shadow_analyzer/ui/extension.py`
  - `_on_viewport_click()` - Converts query GPS to scene coordinates
  - Uses `self._latitude` and `self._longitude` as reference
  - Needs to use building reference point instead

- `source/extensions/city.shadow_analyzer.buildings/city/shadow_analyzer/buildings/terrain_generator.py`
  - Also uses reference point for terrain mesh generation
  - Should already be consistent with buildings

## Notes

- Sun position calculation is **correct** - it only uses GPS coordinates directly
- Visual marker creation is **correct** - it places sphere at given scene coordinates
- The issue is in the **GPS → scene coordinate conversion** for queries
- Buildings display correctly because they use consistent reference point
- Terrain displays correctly for the same reason
- Only query markers use wrong reference point
