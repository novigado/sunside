# Shadow Analyzer API Usage Guide

## Overview

The City Shadow Analyzer API provides REST endpoints to check if a GPS location is in shadow or sunlight at any given time. It combines OpenStreetMap building data with astronomical sun calculations and real-time ray casting.

## Starting the Application

Launch the application in the foreground to get both the UI and API:

```powershell
cd c:\Users\peter\omniverse\kit-app-template
.\repo.bat build
cd _build\windows-x86_64\release
.\city.shadow_analyzer.kit.kit.bat
```

The API server will start automatically on `http://localhost:8000`

You'll see this message in the logs:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## API Endpoints

### 1. Health Check

**GET** `/health`

Check if the API is running.

```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2026-01-14T12:30:00+00:00"
}
```

### 2. Sun Position

**POST** `/api/v1/sun/position`

Calculate sun position (azimuth and elevation) for a location and time.

**Request Body:**
```json
{
  "latitude": 57.70716,
  "longitude": 11.96679,
  "timestamp": "2026-01-14T12:00:00Z"  // Optional, defaults to now
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/sun/position \
  -H "Content-Type: application/json" \
  -d '{"latitude": 57.70716, "longitude": 11.96679}'
```

**Response:**
```json
{
  "azimuth": 180.45,
  "elevation": 12.34,
  "distance": 1.0,
  "latitude": 57.70716,
  "longitude": 11.96679,
  "timestamp": "2026-01-14T12:30:00+00:00"
}
```

**Azimuth Reference:**
- 0° = North
- 90° = East
- 180° = South
- 270° = West

**Elevation Reference:**
- 90° = Directly overhead (noon at equator)
- 0° = On the horizon (sunrise/sunset)
- Negative = Below horizon (nighttime)

### 3. Shadow Query 🌟 **Main Feature**

**POST** `/api/v1/shadow/query`

Check if a GPS location is in shadow or sunlight.

**Request Body:**
```json
{
  "latitude": 57.70716,
  "longitude": 11.96679,
  "timestamp": "2026-01-14T12:00:00Z",  // Optional, defaults to now
  "search_radius": 500  // Optional, meters (100-2000), defaults to 500
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/shadow/query \
  -H "Content-Type: application/json" \
  -d '{"latitude": 57.70716, "longitude": 11.96679, "search_radius": 500}'
```

**Response (Sunlight):**
```json
{
  "is_shadowed": false,
  "sun_azimuth": 180.45,
  "sun_elevation": 12.34,
  "blocking_object": null,
  "latitude": 57.70716,
  "longitude": 11.96679,
  "timestamp": "2026-01-14T12:30:00+00:00",
  "message": null
}
```

**Response (Shadow):**
```json
{
  "is_shadowed": true,
  "sun_azimuth": 180.45,
  "sun_elevation": 12.34,
  "blocking_object": "Building_234567",
  "latitude": 57.70716,
  "longitude": 11.96679,
  "timestamp": "2026-01-14T12:30:00+00:00",
  "message": null
}
```

**Response (Nighttime):**
```json
{
  "is_shadowed": true,
  "sun_azimuth": 180.45,
  "sun_elevation": -15.23,
  "blocking_object": null,
  "latitude": 57.70716,
  "longitude": 11.96679,
  "timestamp": "2026-01-14T22:00:00+00:00",
  "message": "Sun is below horizon (nighttime)"
}
```

## How It Works

1. **Load Buildings**: First request loads OpenStreetMap buildings within the search radius
2. **Create 3D Scene**: Buildings are converted to 3D USD geometry in memory
3. **Calculate Sun Position**: Astronomical calculations determine sun angle
4. **Ray Casting**: Cast a ray from the query point toward the sun
5. **Shadow Detection**: If ray hits a building, location is in shadow

## Testing

Use the provided test script:

```powershell
python test_shadow_api.py
```

Or test with PowerShell:

```powershell
# Health check
Invoke-WebRequest http://localhost:8000/health

# Shadow query
$body = @{
    latitude = 57.70716
    longitude = 11.96679
} | ConvertTo-Json

Invoke-WebRequest -Method POST `
    -Uri http://localhost:8000/api/v1/shadow/query `
    -ContentType "application/json" `
    -Body $body
```

## Use Cases

1. **Solar Panel Planning**: Check if location gets sun during specific hours
2. **Outdoor Photography**: Find sunny vs. shadowed spots for photo shoots
3. **Urban Planning**: Analyze shadow patterns in city development
4. **Real Estate**: Assess sunlight exposure for properties
5. **Agriculture**: Optimize urban garden placement
6. **Tourism Apps**: Find sunny spots for outdoor activities

## Performance Notes

- **First Request**: 10-30 seconds (loads OpenStreetMap data)
- **Subsequent Requests**: < 1 second (uses cached building data)
- **Search Radius**: Larger radius = more buildings = slightly slower
- **Building Density**: Dense urban areas may take longer to process

## Default Coordinates

The application defaults to **Gothenburg, Sweden**:
- Latitude: 57.70716°
- Longitude: 11.96679°

You can query any location worldwide using the API.

## Interactive Documentation

Visit `http://localhost:8000/docs` for interactive Swagger UI documentation where you can test endpoints directly in your browser.

## Troubleshooting

**API not responding?**
- Check if application is running (look for the window)
- Check terminal for "Uvicorn running" message
- Try `curl http://localhost:8000/health`

**No buildings loaded?**
- First request may timeout if OpenStreetMap is slow
- Try smaller search_radius (200-300 meters)
- Check logs in `C:/Users/peter/.nvidia-omniverse/logs/Kit/`

**Wrong shadow results?**
- Verify timestamp is in UTC (use 'Z' suffix or explicit timezone)
- Check if sun is above horizon (`sun_elevation > 0`)
- Increase search_radius to find nearby buildings

## Example Workflow

```python
import requests
from datetime import datetime, timezone

# 1. Check if service is healthy
health = requests.get("http://localhost:8000/health").json()
print(f"API Status: {health['status']}")

# 2. Get sun position
sun_data = {
    "latitude": 57.70716,
    "longitude": 11.96679
}
sun = requests.post("http://localhost:8000/api/v1/sun/position", json=sun_data).json()
print(f"Sun: {sun['elevation']:.1f}° elevation, {sun['azimuth']:.1f}° azimuth")

# 3. Check shadow
shadow_data = {
    "latitude": 57.70716,
    "longitude": 11.96679,
    "search_radius": 500
}
result = requests.post("http://localhost:8000/api/v1/shadow/query", json=shadow_data).json()

if result['is_shadowed']:
    print("🌑 Location is in SHADOW")
    if result['blocking_object']:
        print(f"   Blocked by: {result['blocking_object']}")
else:
    print("☀️ Location has SUNLIGHT")
```

## Next Steps

- Integrate with mobile apps
- Create web interface for visualization
- Add historical shadow analysis
- Support batch queries for multiple locations
- Add shadow duration predictions
