# Map Orientation Investigation

## Issue Report

**Reported**: Map appears to not be oriented in a north-south direction. It almost looks like a mirrored image.

## Current Coordinate System

### Theoretical Implementation

```python
# From geometry_converter.py
z = lat_diff * meters_per_lat_degree  # Latitude -> Z (north-south)
x = lon_diff * meters_per_lon_degree  # Longitude -> X (east-west)
```

**Expected behavior:**
- Increasing latitude (going North) → Positive Z direction
- Increasing longitude (going East) → Positive X direction
- In viewport with default camera: North should be "forward/up" on screen

### Possible Issues

1. **Camera Orientation**: The viewport camera might not be oriented with Z-axis pointing north
2. **Coordinate Swap**: OpenStreetMap might be returning coordinates in unexpected order
3. **Sign Flip**: One or both axes might need to be negated for correct orientation
4. **Building Coordinate Order**: OSM polygon coordinates might be in unexpected order (clockwise vs counter-clockwise)

## Diagnostic Steps

### Test Location: Gothenburg, Sweden
- **Center**: 57.749254°N, 12.263287°E
- **Expected prominent features**:
  - Göta älv river (runs roughly N-S through city)
  - Avenyn street (runs N-S)
  - Harbor on west side

### Things to Check

1. **Verify coordinate conversion is consistent**:
   ```python
   # Building at 57.75°N, 12.26°E should be at:
   lat_diff = 57.75 - 57.749254 = +0.000746° (slightly north)
   lon_diff = 12.26 - 12.263287 = -0.003287° (slightly west)

   # Should give:
   z = +0.000746 * 111000 = +82.8m (positive Z = north) ✓
   x = -0.003287 * 111000 * cos(57.749°) = -193.6m (negative X = west) ✓
   ```

2. **Check OSM polygon order**:
   - OSM buildings return coordinates as list of (lat, lon) pairs
   - Are they in correct order?
   - Are they lat,lon or lon,lat?

3. **Check viewport orientation**:
   - Which direction is "up" on screen?
   - Which direction is +Z in viewport?

## Testing Recommendations

### Add Debug Markers

Add visible markers at cardinal directions to verify orientation:

```python
# North marker (positive Z)
create_marker("/World/Debug/North", position=(0, 10, 100), color="blue")

# South marker (negative Z)
create_marker("/World/Debug/South", position=(0, 10, -100), color="yellow")

# East marker (positive X)
create_marker("/World/Debug/East", position=(100, 10, 0), color="red")

# West marker (negative X)
create_marker("/World/Debug/West", position=(-100, 10, 0), color="green")
```

### Compare with Known Geography

1. Load Gothenburg map
2. Identify known geographic features (river, major streets)
3. Compare with actual map orientation
4. Determine if flip/rotation needed

## Potential Fixes

### If Map is Mirrored (Flipped Left-Right)

```python
# Flip X coordinate
x = -(lon_diff * meters_per_lon_degree)  # Note the negative sign
```

### If Map is Mirrored (Flipped Front-Back)

```python
# Flip Z coordinate
z = -(lat_diff * meters_per_lat_degree)  # Note the negative sign
```

### If Map Needs 180° Rotation

```python
# Flip both
x = -(lon_diff * meters_per_lon_degree)
z = -(lat_diff * meters_per_lat_degree)
```

### If Map Needs 90° Rotation

```python
# Swap and possibly flip
x = lat_diff * meters_per_lat_degree  # lat → x
z = lon_diff * meters_per_lon_degree  # lon → z
```

## Action Items

1. ✅ Document the issue
2. ✅ Launch application with Gothenburg coordinates
3. ✅ Visually inspect map orientation
4. ✅ Identify problem: Map is flipped left-right (mirrored)
5. ✅ Apply fix: Negate X coordinate
6. ⬜ Test in application to verify fix
7. ⬜ Test with multiple locations to verify

## Solution Applied

**Problem Identified**: Map was mirrored (flipped left-right)

**Root Cause**: The X coordinate (longitude/East-West) was not negated, causing a left-right flip

**Fix Applied** (Commit: ff4666d):

```python
# BEFORE (incorrect - caused left-right flip):
x = lon_diff * meters_per_lon_degree  # X = East/West

# AFTER (correct):
x = -(lon_diff * meters_per_lon_degree)  # X = East/West, negated to fix left-right flip
```

**Files Modified**:
1. `geometry_converter.py` - Building coordinate conversion
2. `terrain_generator.py` - Terrain coordinate conversion
3. `extension.py` - GPS query coordinate conversion

**Testing**: Ready to test in application. The map should now display with correct orientation:
- East → Right (+X direction)
- West → Left (-X direction)
- North → Forward (+Z direction)
- South → Backward (-Z direction)

## References

- OpenStreetMap coordinate order: https://wiki.openstreetmap.org/wiki/Node
- USD Coordinate Systems: https://graphics.pixar.com/usd/docs/api/group___usd_geom_up_axis__group.html
- Omniverse Coordinate System: Y-up, right-handed

## Notes

- This is a VERY common issue when working with geographic data
- The "mirrored" appearance suggests a sign flip on one axis
- Need to test with real application to determine exact nature of problem
