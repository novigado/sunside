# City Shadow Analyzer - Sun Position Extension

This extension provides sun position calculation capabilities for the City Shadow Analyzer application.

## Features

- Calculate sun position (azimuth and elevation) based on:
  - Geographic location (latitude, longitude)
  - Date and time (UTC)
- Convert sun position to direction vectors for 3D scene lighting
- Astronomical algorithms for accurate solar positioning

## Usage

```python
from city.shadow_analyzer.sun import SunCalculator
from datetime import datetime

calc = SunCalculator()

# Calculate current sun position for a location
latitude = 40.7128  # New York City
longitude = -74.0060
azimuth, elevation, distance = calc.calculate_sun_position(latitude, longitude)

# Get direction vector for lighting
direction = SunCalculator.get_sun_direction_vector(azimuth, elevation)
```

## Coordinate System

- **Azimuth**: 0° = North, 90° = East, 180° = South, 270° = West
- **Elevation**: 90° = directly overhead, 0° = horizon, negative = below horizon
- **Direction Vector**: Returns (x, y, z) in USD/Omniverse coordinates (+Y up)
