# City Shadow Analyzer - Nucleus Integration

This extension integrates the City Shadow Analyzer with NVIDIA Omniverse Nucleus, enabling:

- **USD Building Cache**: Store OpenStreetMap building data as USD files on Nucleus
- **Collaborative Access**: Multiple users can query the same cached city data
- **Results Persistence**: Save shadow analysis results for visualization and sharing
- **Version Control**: Track changes to city data over time

## Features

### 1. Building Data Caching

Instead of fetching building data from OpenStreetMap every time, cache it as USD on Nucleus:

```python
from city.shadow_analyzer.nucleus.nucleus_manager import NucleusManager

manager = NucleusManager()

# Check if buildings are cached
city_name = "manhattan"
bounds_hash = "40.75_-73.99_1.0"  # lat_lon_radius

exists, path = manager.check_buildings_cache(city_name, bounds_hash)
if exists:
    # Load from Nucleus
    success, usd_content = manager.load_buildings_from_nucleus(city_name, bounds_hash)
else:
    # Fetch from OpenStreetMap and cache
    # ... fetch buildings ...
    success, path = manager.save_buildings_to_nucleus(
        city_name, bounds_hash, usd_content, metadata
    )
```

### 2. Collaborative Workflows

Multiple users can access the same cached building data:
- **Urban planners** query shadow impact from their office
- **Architects** analyze building designs remotely
- **Stakeholders** review shadow assessments collaboratively

### 3. Results Persistence

Save shadow analysis results for later visualization:

```python
results = {
    "query_time": "2026-01-14T15:00:00Z",
    "location": {"lat": 40.7589, "lon": -73.9851},
    "shadow_detected": True,
    "buildings": [...]
}

success, path = manager.save_shadow_results(
    "manhattan", "analysis_20260114", results
)
# Results saved to: omniverse://server/Projects/CityData/manhattan/results/...
```

## Configuration

Configure Nucleus settings in your kit file or via settings:

```toml
[settings]
exts."city.shadow_analyzer.nucleus".nucleus_server = "omniverse://nucleus-server.company.com"
exts."city.shadow_analyzer.nucleus".project_path = "/Projects/CityData"
```

Or programmatically:

```python
import carb

settings = carb.settings.get_settings()
settings.set("exts/city.shadow_analyzer.nucleus/nucleus_server", "omniverse://localhost")
settings.set("exts/city.shadow_analyzer.nucleus/project_path", "/Projects/CityData")
```

## Nucleus Server Setup

### Local Nucleus (for development)

1. Install Omniverse Launcher
2. Install Nucleus (from Launcher > Library)
3. Start Nucleus service
4. Default URL: `omniverse://localhost`

### Enterprise Nucleus

1. Connect to your company's Nucleus server
2. Configure authentication
3. Set server URL in extension settings

## USD Storage Structure

```
omniverse://server/Projects/CityData/
├── manhattan/
│   ├── buildings_40.75_-73.99_1.0.usd
│   ├── buildings_40.75_-73.99_1.0.usd.meta.json
│   └── results/
│       ├── shadow_analysis_20260114.json
│       └── shadow_analysis_20260115.json
├── brooklyn/
│   ├── buildings_40.65_-73.95_2.0.usd
│   └── ...
└── ...
```

## API Integration

This extension enhances the REST API with Nucleus-backed endpoints:

```bash
# Cache buildings to Nucleus
curl -X POST http://localhost:8000/api/v1/nucleus/cache-buildings \
  -H "Content-Type: application/json" \
  -d '{
    "latitude": 40.7589,
    "longitude": -73.9851,
    "radius_km": 1.0,
    "city_name": "manhattan"
  }'

# Query shadow using Nucleus-cached buildings
curl -X POST http://localhost:8000/api/v1/shadow/query-nucleus \
  -H "Content-Type: application/json" \
  -d '{
    "nucleus_building_path": "omniverse://server/Projects/CityData/manhattan/buildings.usd",
    "query_point": {"latitude": 40.7589, "longitude": -73.9851},
    "datetime": "2026-01-14T15:00:00Z"
  }'
```

## Benefits

### Performance
- Faster queries (no OpenStreetMap API calls)
- Reduced network bandwidth
- Cached USD loads instantly

### Collaboration
- Shared city models across team
- Consistent data for all users
- Version control and history

### Scalability
- Store city-scale building data
- Handle multiple concurrent users
- Cloud-ready architecture

## Troubleshooting

### Cannot Connect to Nucleus

```
[NucleusManager] Cannot connect to omniverse://localhost: ERROR_CONNECTION
```

**Solution**:
- Check Nucleus service is running
- Verify server URL in settings
- Check network/firewall settings

### Permission Denied

```
[NucleusManager] Failed to write USD file: ERROR_ACCESS_DENIED
```

**Solution**:
- Check Nucleus user permissions
- Ensure write access to project folder
- Contact Nucleus administrator

## Learning Resources

- [Omniverse Nucleus Documentation](https://docs.omniverse.nvidia.com/nucleus/latest/)
- [omni.client API Reference](https://docs.omniverse.nvidia.com/kit/docs/omni.client/latest/)
- [USD File Format](https://openusd.org/release/api/index.html)

## Next Steps

1. **Install Nucleus** locally for testing
2. **Configure settings** in your kit file
3. **Cache building data** via REST API
4. **Query shadows** using Nucleus paths
5. **Share results** with collaborators

For connector development (QGIS, Web, etc.), see `NUCLEUS_INTEGRATION_PLAN.md`.
