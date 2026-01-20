# City Shadow Analyzer - Quick Start Guide

## Overview

The City Shadow Analyzer is an NVIDIA Omniverse Kit-based application that determines if a location in a city has sunshine or is shadowed by surrounding buildings. It uses accurate astronomical calculations for sun positioning and RTX ray tracing for realistic shadow rendering.

## Current Features

###  Implemented
- **Sun Position Calculation**: Accurate astronomical algorithms based on date, time, and GPS coordinates
- **Visual Representation**: Real-time 3D visualization with RTX-rendered shadows
- **Interactive UI**: Controls for location, time, and sun position updates
- **Test Scene Generation**: Create simple city blocks for testing
- **Time Control**: Use current time or set custom date/time

###  Coming Soon
- Point query system (click to check if location is in sun/shadow)
- Real city data loading (OpenStreetMap integration)
- REST API for remote queries
- Caching system for performance
- More sophisticated building geometry

## Usage

### 1. Launch the Application

```powershell
.\repo.bat launch
```

Or use the VS Code task: **Launch**

### 2. Using the Interface

The **Shadow Analyzer** window will appear on the right side with the following controls:

#### Location Settings
- **Latitude**: Enter latitude in degrees (-90 to 90, positive = North)
- **Longitude**: Enter longitude in degrees (-180 to 180, positive = East)

Example locations:
- New York City: `40.7128, -74.0060`
- London: `51.5074, -0.1278`
- Tokyo: `35.6762, 139.6503`
- Sydney: `-33.8688, 151.2093`

#### Time Settings
- Shows current UTC time
- Click **"Use Current Time"** to update to now

#### Sun Position Display
- **Azimuth**: Direction (0°=North, 90°=East, 180°=South, 270°=West)
- **Elevation**: Angle above horizon (90°=overhead, 0°=horizon, negative=below)
- **Status**: Indicates if sun is above or below horizon

### 3. Create a Test Scene

1. Click **"Create Test Scene"** to generate simple buildings
2. The scene will create:
   - A ground plane
   - 5 buildings of varying heights
   - A directional sun light

### 4. Update Sun Position

1. Set your desired location (latitude/longitude)
2. Set the time (or use current)
3. Click **"Update Sun Position"**
4. Watch the sun light direction change in the 3D viewport
5. Observe how shadows fall on buildings and ground

### 5. Visual Validation

- Use the viewport camera controls to navigate:
  - **Middle mouse**: Pan
  - **Right mouse**: Rotate
  - **Scroll wheel**: Zoom
- Watch shadows change as you update sun position
- Try different times of day to see sun angle changes
- Try different locations to see how latitude affects shadows

## Understanding the Results

### Azimuth Interpretation
- **0°**: Sun in the North (unusual except near poles)
- **90°**: Sun in the East (morning)
- **180°**: Sun in the South (midday in Northern Hemisphere)
- **270°**: Sun in the West (evening)

### Elevation Interpretation
- **90°**: Sun directly overhead (only in tropics)
- **45°**: Sun at mid-height angle
- **0°**: Sun at horizon (sunrise/sunset)
- **Negative**: Sun below horizon (nighttime)

### Shadow Behavior
- **Low elevation angle**: Long shadows
- **High elevation angle**: Short shadows
- **Sun below horizon**: Complete darkness/shadows everywhere

## Example Scenarios

### Scenario 1: New York at Noon
```
Latitude: 40.7128
Longitude: -74.0060
Time: 12:00 PM local time (17:00 UTC in winter)
Expected: Sun in the south, elevation ~30° in winter, ~70° in summer
```

### Scenario 2: London Morning
```
Latitude: 51.5074
Longitude: -0.1278
Time: 8:00 AM local time (08:00 UTC)
Expected: Sun in the east-southeast, low elevation angle
```

### Scenario 3: Equator at Noon
```
Latitude: 0.0
Longitude: 0.0
Time: 12:00 PM local time (12:00 UTC)
Expected: Sun nearly overhead (elevation close to 90°)
```

## Architecture

### Extensions

1. **city.shadow_analyzer.sun**
   - Sun position calculation using astronomical algorithms
   - Converts position to direction vectors for lighting

2. **city.shadow_analyzer.ui**
   - User interface controls
   - Scene management
   - Integration of sun calculation with visualization

### Technical Details

- **Coordinate System**: Uses standard astronomical conventions
- **Rendering**: NVIDIA RTX for accurate shadow computation
- **USD/Omniverse**: Scene representation using Universal Scene Description
- **Python**: Extensions written in Python for flexibility

## Next Steps for Development

### Phase 1: Enhanced Visualization  (Current)
- Basic sun positioning
- Simple test scenes
- Visual shadow validation

### Phase 2: Query System (Next)
- Click points in scene to query sun/shadow status
- Ray casting from point toward sun
- Display results in UI

### Phase 3: Real City Data
- Load OpenStreetMap building footprints
- Convert to 3D USD geometry
- Handle large city datasets

### Phase 4: Service API
- REST API endpoint for queries
- Headless operation mode
- Caching and optimization
- Mobile client integration

## Troubleshooting

### Issue: Sun light not visible
- **Solution**: Check elevation angle - if negative, sun is below horizon
- **Solution**: Click "Update Sun Position" to ensure light is created

### Issue: No shadows visible
- **Solution**: Ensure RTX rendering is enabled (should be default)
- **Solution**: Check that buildings have been created ("Create Test Scene")
- **Solution**: Try a different time with sun above horizon (elevation > 0)

### Issue: Wrong sun position
- **Solution**: Verify latitude/longitude are correct
- **Solution**: Check that time is in UTC (not local time)
- **Solution**: Remember: positive latitude = North, negative = South

## Performance Notes

- Current implementation is optimized for real-time visualization
- Test scenes are simple for fast rendering
- Real city data will require additional optimization
- Ray tracing performance depends on GPU (your NC4as T4 v3 VM has Tesla T4)

## API Reference (Coming Soon)

Future REST API will support queries like:

```
GET /api/shadow/query?lat=40.7128&lon=-74.0060&time=2026-01-13T12:00:00Z
Response: {"is_sunny": true, "sun_elevation": 32.5, "sun_azimuth": 175.2}
```

## Resources

- [Omniverse Kit SDK Documentation](https://docs.omniverse.nvidia.com/kit)
- [USD Documentation](https://openusd.org/release/index.html)
- [Astronomical Algorithms](https://en.wikipedia.org/wiki/Position_of_the_Sun)
