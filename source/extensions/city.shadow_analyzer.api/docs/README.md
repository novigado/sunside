# City Shadow Analyzer REST API

REST API extension for the City Shadow Analyzer, providing HTTP endpoints for shadow analysis queries from smartphones and web applications.

## Features

- **Shadow Query Endpoint**: Check if a GPS location is in shadow at a specific time
- **Sun Position Endpoint**: Get sun azimuth and elevation for any location and time
- **Health Check Endpoint**: Monitor API availability
- **CORS Enabled**: Access from web browsers and mobile apps
- **OpenAPI Documentation**: Interactive API docs at `/docs`

## API Endpoints

### POST /api/v1/shadow/query

Query whether a GPS location is in shadow.

**Request Body:**
```json
{
  "latitude": 40.7128,
  "longitude": -74.0060,
  "timestamp": "2026-01-13T12:00:00Z",
  "search_radius": 500
}
```

**Response:**
```json
{
  "is_shadowed": true,
  "sun_azimuth": 180.5,
  "sun_elevation": 35.2,
  "blocking_object": "/World/Buildings/building_123",
  "latitude": 40.7128,
  "longitude": -74.0060,
  "timestamp": "2026-01-13T12:00:00Z",
  "message": null
}
```

### POST /api/v1/sun/position

Get sun position for a location and time.

**Request Body:**
```json
{
  "latitude": 40.7128,
  "longitude": -74.0060,
  "timestamp": "2026-01-13T12:00:00Z"
}
```

**Response:**
```json
{
  "azimuth": 180.5,
  "elevation": 35.2,
  "distance": 1.0,
  "latitude": 40.7128,
  "longitude": -74.0060,
  "timestamp": "2026-01-13T12:00:00Z"
}
```

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2026-01-13T12:00:00Z"
}
```

## Configuration

The API server can be configured via Kit settings:

```toml
[settings]
exts."city.shadow_analyzer.api".host = "0.0.0.0"
exts."city.shadow_analyzer.api".port = 8000
```

## Usage from Smartphone

### JavaScript Example
```javascript
async function checkShadow(lat, lon) {
  const response = await fetch('http://your-server:8000/api/v1/shadow/query', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      latitude: lat,
      longitude: lon,
      timestamp: new Date().toISOString(),
      search_radius: 500
    })
  });

  const data = await response.json();
  console.log(`Location is ${data.is_shadowed ? 'in shadow' : 'in sunlight'}`);
  return data;
}
```

### Python Example
```python
import requests

def check_shadow(lat, lon):
    response = requests.post(
        'http://your-server:8000/api/v1/shadow/query',
        json={
            'latitude': lat,
            'longitude': lon,
            'search_radius': 500
        }
    )
    data = response.json()
    return data['is_shadowed']
```

## Interactive Documentation

Once the extension is running, visit `http://localhost:8000/docs` for interactive API documentation powered by Swagger UI.

## Notes

- All timestamps are in UTC using ISO 8601 format
- If no timestamp is provided, current time is used
- Search radius is in meters (default: 500m, max: 2000m)
- CORS is enabled for all origins (configure appropriately for production)
