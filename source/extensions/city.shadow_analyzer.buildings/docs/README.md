# City Shadow Analyzer - Buildings Extension

This extension loads real building data from OpenStreetMap and converts it to 3D geometry for shadow analysis.

## Features

- Query OpenStreetMap Overpass API for building data
- Convert 2D building footprints to 3D USD geometry
- Support building height data where available
- Efficient caching of building data
- Configurable search radius and detail level

## Usage

```python
from city.shadow_analyzer.buildings import BuildingLoader

loader = BuildingLoader()
buildings = loader.load_buildings(latitude=40.7128, longitude=-74.0060, radius_km=0.5)
```

## Data Source

Building data is sourced from OpenStreetMap via the Overpass API.
- License: ODbL (Open Database License)
- Attribution: © OpenStreetMap contributors
