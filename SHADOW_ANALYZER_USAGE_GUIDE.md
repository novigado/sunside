# City Shadow Analyzer - Usage Guide

## Overview

This NVIDIA Omniverse application analyzes sun position and shadow casting for real-world locations using OpenStreetMap building data.

## Features

### ✅ Completed Features

1. **Astronomical Sun Position Calculation**
   - Accurate sun azimuth and elevation for any location and time
   - UTC timezone support
   - Real-time sun position updates

2. **OpenStreetMap Integration**
   - Loads real building data from OpenStreetMap
   - Supports roads and ground plane rendering
   - Automatic 3D building extrusion from height tags
   - 500m radius coverage area

3. **Real Shadow Detection**
   - Möller-Trumbore ray-triangle intersection algorithm
   - Accurate geometric shadow casting
   - Per-building shadow identification

4. **Visual GPS Coordinate Markers**
   - 10-meter radius spheres at query points
   - Color-coded: Cyan (initial) → Yellow (sunlight) / Purple (shadow)
   - Raised 10m above ground for visibility
   - Multiple markers supported

5. **Camera Controls**
   - "Focus Camera on Scene" button positions camera at optimal viewing angle
   - Bird's-eye view from (100m, 80m, 100m) looking at origin

6. **Performance Optimizations**
   - RTX Real Time rendering mode
   - Disabled expensive effects (reflections, AO, path tracing)
   - 4 FPS achieved on Azure NC4as T4 v3

## How to Use

### 1. Launch Application

```powershell
.\repo.bat launch city.shadow_analyzer.kit.kit
```

Wait for "app ready" and "RTX ready" messages.

### 2. Set Observer Location

In the **Observer Location** section:
- **Latitude**: e.g., `40.7128` (NYC)
- **Longitude**: e.g., `-74.0060` (NYC)
- **Date/Time**: Set current date and time (UTC)

Click **"Update Sun Position"** to calculate sun angles.

### 3. Load Buildings

Click **"Load Buildings from OpenStreetMap"** (orange button):
- Status label shows ⏳ while loading
- Automatically loads buildings, roads, and ground within 500m
- Status turns green when complete: "✓ Loaded N buildings, M roads"
- **Note**: OpenStreetMap API may timeout - system retries up to 3 times

### 4. Query GPS Points for Shadow

In the **Query Point GPS Coordinates** section:
- Enter latitude and longitude to query
- Click **"Query Point at GPS Coordinates"** (blue button)
- Results show:
  - ☀️ SUNLIGHT (yellow marker)
  - 🌑 SHADOW (purple marker) - includes which building blocks sun
  - 🌙 NIGHT (sun below horizon)

### 5. Focus Camera

Click **"Focus Camera on Scene"** (purple button):
- Positions camera for optimal view
- Look for large colored spheres (10m radius) at query points

### 6. Multiple Queries

- Query multiple points to build a shadow map
- Each query creates a new marker
- Click **"Clear Query Markers"** to reset

## Marker Color Legend

- **Cyan** (0.3, 0.7, 1.0): Initial placement, before shadow analysis
- **Yellow** (1.0, 0.9, 0.0): Point is in sunlight
- **Purple** (0.8, 0.1, 0.9): Point is in shadow
- **Dark Blue** (0.2, 0.2, 0.6): Nighttime (sun below horizon)

## Coordinate System

- **X axis**: East-West (longitude), 111000m per degree × cos(latitude)
- **Y axis**: Up (height above ground)
- **Z axis**: North-South (latitude), 111000m per degree
- **Origin**: Observer location (reference point for buildings)
- **Scale**: 1 unit = 1 meter

## Example Locations to Try

### New York City
- Latitude: `40.7128`
- Longitude: `-74.0060`
- Query point nearby: `40.7130`, `-74.0062` (~200m away)

### Gothenburg, Sweden
- Latitude: `57.7089`
- Longitude: `11.9746`

### San Francisco
- Latitude: `37.7749`
- Longitude: `-122.4194`

### Tokyo
- Latitude: `35.6762`
- Longitude: `139.6503`

## Troubleshooting

### "No data found in this area"
- Some areas have limited OpenStreetMap building coverage
- Try a major city with good OSM coverage

### "504 Server Error: Gateway Timeout"
- OpenStreetMap Overpass API is overloaded
- System automatically retries 3 times with increasing timeouts (30s, 50s, 70s)
- Wait a few minutes and try again

### Markers not visible
- Click **"Focus Camera on Scene"** to position camera
- Markers may be behind buildings - rotate camera view
- Ensure you've loaded buildings first (gives reference for scale)

### Buildings look wrong
- Cache may have stale data - click "Clear Query Markers" doesn't clear building cache
- Restart application to clear all caches

## Technical Details

### Extensions

1. **city.shadow_analyzer.sun**
   - `sun_calculator.py`: Astronomical calculations
   - Julian date, local sidereal time, ecliptic coordinates
   - Azimuth/elevation output

2. **city.shadow_analyzer.buildings**
   - `building_loader.py`: OpenStreetMap Overpass API queries
   - `geometry_converter.py`: GPS → USD geometry conversion
   - `shadow_analyzer.py`: Ray-triangle intersection for shadows

3. **city.shadow_analyzer.ui**
   - `extension.py`: Main UI and orchestration
   - Controls, status display, marker management

### Shadow Detection Algorithm

1. Get sun direction vector from azimuth/elevation
2. Create ray from query point toward sun (opposite of sun direction)
3. Iterate all buildings at `/World/Buildings`
4. For each building mesh:
   - Extract triangle faces
   - Test ray-triangle intersection (Möller-Trumbore)
   - If intersection found, return shadow + building name
5. No intersection = point in sunlight

### Performance

- **Hardware**: NVIDIA Tesla T4 (16GB VRAM)
- **Resolution**: 1280x720
- **FPS**: ~4 FPS
- **Rendering**: RTX Real Time mode
- **Buildings**: ~100-500 per 500m radius (varies by location)

## Known Limitations

1. **OpenStreetMap Coverage**: Not all areas have building height data
2. **API Rate Limits**: Overpass API may timeout during peak usage
3. **Height Estimation**: Buildings without height tags use defaults (residential=10m, commercial=15m)
4. **Coordinate Accuracy**: GPS to scene conversion assumes flat earth (good for < 10km radius)
5. **Performance**: Large building counts may reduce FPS

## Future Enhancements

### Planned Features

1. **REST API Endpoint** (for smartphone/web queries)
   - POST /query → {lat, lon, time} → {is_shadowed, sun_position}
   - Headless mode support

2. **Grid Shadow Analysis**
   - Analyze 10x10 grid of points
   - Shadow percentage calculation
   - Heatmap visualization

3. **Time-Lapse Animation**
   - Animate sun movement throughout day
   - Record shadow patterns

4. **Export Functionality**
   - Export shadow map as image
   - CSV export of query results

5. **Building Detail Improvements**
   - Better height estimation algorithms
   - Support for complex building shapes
   - Roof geometry

## File Locations

- **Application**: `source/apps/city.shadow_analyzer.kit.kit`
- **Extensions**: `source/extensions/city.shadow_analyzer.*/`
- **Logs**: `C:/Users/peter/.nvidia-omniverse/logs/Kit/city.shadow_analyzer.kit/`
- **Config**: `C:/Users/peter/AppData/Local/ov/data/Kit/city.shadow_analyzer.kit/`

## Credits

- **Building Data**: © OpenStreetMap contributors (ODbL license)
- **Platform**: NVIDIA Omniverse Kit SDK 109.0.2
- **Ray Tracing**: NVIDIA RTX

## License

See LICENSE file in repository root.
