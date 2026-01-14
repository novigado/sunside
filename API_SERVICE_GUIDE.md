# City Shadow Analyzer REST API

REST API service for real-time shadow analysis using OpenStreetMap building data and astronomical sun calculations.

## Features

- 🌞 **Real-time shadow detection** at any GPS coordinate
- 🏢 **OpenStreetMap integration** - automatically loads building data
- 🔆 **Astronomical sun calculations** - accurate azimuth and elevation
- 📱 **Mobile-friendly API** - CORS-enabled for smartphone apps
- 📊 **Interactive documentation** - Swagger UI at `/docs`
- ⚡ **Optimized performance** - headless mode for production

## Quick Start

### 1. Build the Application

```bash
.\repo.bat build
```

### 2. Launch the API Service

```bash
.\repo.bat launch city.shadow_analyzer.api.kit
```

The API server will start on `http://0.0.0.0:8000`

### 3. Access API Documentation

Open your browser to:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### Check if Location is in Shadow

**Endpoint**: `POST /api/v1/shadow/query`

**Request**:
```bash
curl -X POST "http://localhost:8000/api/v1/shadow/query" \
  -H "Content-Type: application/json" \
  -d '{
    "latitude": 40.7128,
    "longitude": -74.0060,
    "timestamp": "2026-01-13T15:00:00Z",
    "search_radius": 500
  }'
```

**Response**:
```json
{
  "is_shadowed": true,
  "sun_azimuth": 220.5,
  "sun_elevation": 25.3,
  "blocking_object": "/World/Buildings/way_123456789",
  "latitude": 40.7128,
  "longitude": -74.0060,
  "timestamp": "2026-01-13T15:00:00Z",
  "message": null
}
```

### Get Sun Position

**Endpoint**: `POST /api/v1/sun/position`

**Request**:
```bash
curl -X POST "http://localhost:8000/api/v1/sun/position" \
  -H "Content-Type: application/json" \
  -d '{
    "latitude": 40.7128,
    "longitude": -74.0060,
    "timestamp": "2026-01-13T15:00:00Z"
  }'
```

**Response**:
```json
{
  "azimuth": 220.5,
  "elevation": 25.3,
  "distance": 1.0,
  "latitude": 40.7128,
  "longitude": -74.0060,
  "timestamp": "2026-01-13T15:00:00Z"
}
```

### Health Check

**Endpoint**: `GET /health`

**Request**:
```bash
curl "http://localhost:8000/health"
```

**Response**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2026-01-13T15:30:00.123456Z"
}
```

## Configuration

Edit `source/apps/city.shadow_analyzer.api.kit` to configure:

```toml
[settings]
# Change the server host/port
exts."city.shadow_analyzer.api".host = "0.0.0.0"
exts."city.shadow_analyzer.api".port = 8000
```

## Usage Examples

### JavaScript (Browser/Node.js)

```javascript
async function checkShadow(lat, lon) {
  const response = await fetch('http://localhost:8000/api/v1/shadow/query', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      latitude: lat,
      longitude: lon,
      search_radius: 500
    })
  });

  const data = await response.json();

  if (data.is_shadowed) {
    console.log('🌙 Location is in shadow');
    if (data.sun_elevation < 0) {
      console.log('☀️ Sun is below horizon (nighttime)');
    } else if (data.blocking_object) {
      console.log(`🏢 Blocked by: ${data.blocking_object}`);
    }
  } else {
    console.log('☀️ Location is in sunlight');
  }

  return data;
}

// Example: Check Times Square
checkShadow(40.7580, -73.9855);
```

### Python

```python
import requests
from datetime import datetime, timezone

def check_shadow(lat, lon, dt=None):
    """Check if a location is in shadow."""
    if dt is None:
        dt = datetime.now(timezone.utc)

    response = requests.post(
        'http://localhost:8000/api/v1/shadow/query',
        json={
            'latitude': lat,
            'longitude': lon,
            'timestamp': dt.isoformat(),
            'search_radius': 500
        }
    )

    data = response.json()
    return data

# Example: Check Central Park
result = check_shadow(40.7829, -73.9654)
print(f"In shadow: {result['is_shadowed']}")
print(f"Sun elevation: {result['sun_elevation']:.1f}°")
```

### Swift (iOS)

```swift
struct ShadowQuery: Codable {
    let latitude: Double
    let longitude: Double
    let searchRadius: Int = 500

    enum CodingKeys: String, CodingKey {
        case latitude, longitude
        case searchRadius = "search_radius"
    }
}

struct ShadowResponse: Codable {
    let isShadowed: Bool
    let sunAzimuth: Double
    let sunElevation: Double
    let latitude: Double
    let longitude: Double

    enum CodingKeys: String, CodingKey {
        case isShadowed = "is_shadowed"
        case sunAzimuth = "sun_azimuth"
        case sunElevation = "sun_elevation"
        case latitude, longitude
    }
}

func checkShadow(lat: Double, lon: Double) async throws -> ShadowResponse {
    let url = URL(string: "http://your-server:8000/api/v1/shadow/query")!
    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    request.setValue("application/json", forHTTPHeaderField: "Content-Type")

    let query = ShadowQuery(latitude: lat, longitude: lon)
    request.httpBody = try JSONEncoder().encode(query)

    let (data, _) = try await URLSession.shared.data(for: request)
    let response = try JSONDecoder().decode(ShadowResponse.self, from: data)

    return response
}
```

## Deployment

### Local Network
```bash
# Edit city.shadow_analyzer.api.kit
exts."city.shadow_analyzer.api".host = "0.0.0.0"  # Listen on all interfaces
exts."city.shadow_analyzer.api".port = 8000

# Launch
.\repo.bat launch city.shadow_analyzer.api.kit

# Access from phone on same network
http://192.168.1.100:8000/api/v1/shadow/query
```

### Cloud Deployment (Azure/AWS/GCP)

1. Deploy on cloud VM with GPU (e.g., Azure NC4as T4 v3)
2. Open port 8000 in firewall
3. Set up reverse proxy (nginx) with SSL
4. Configure domain name
5. Update CORS settings for production

### Docker (Future)

```dockerfile
FROM nvcr.io/nvidia/omniverse-kit:latest
COPY source /app/source
WORKDIR /app
CMD ["./repo.sh", "launch", "city.shadow_analyzer.api.kit"]
```

## Performance Notes

- First query for a location loads buildings from OpenStreetMap (1-5 seconds)
- Subsequent queries for same location are cached (< 100ms)
- Ray-casting shadow detection: ~10-50ms depending on building count
- Recommended: 500m search radius for balance of accuracy and performance
- Maximum: 2000m search radius

## Troubleshooting

### API Server Won't Start

Check if port is already in use:
```bash
netstat -ano | findstr :8000
```

Change port in config:
```toml
exts."city.shadow_analyzer.api".port = 8001
```

### OpenStreetMap Timeouts

Increase timeout in `building_loader.py` or reduce search radius:
```json
{
  "search_radius": 300
}
```

### CORS Errors

For production, update `api_server.py`:
```python
allow_origins=["https://your-app.com"]
```

## Architecture

```
┌─────────────────┐
│  Smartphone/Web │
└────────┬────────┘
         │ HTTP POST
         ▼
┌─────────────────┐
│   FastAPI REST  │
│   API Server    │
│  (Port 8000)    │
└────────┬────────┘
         │
    ┌────┼────┐
    │    │    │
    ▼    ▼    ▼
┌────┐┌────┐┌─────┐
│Sun ││OSM ││Ray  │
│Calc││Load││Cast │
└────┘└────┘└─────┘
```

## License

See [LICENSE](../../LICENSE)

## Support

For issues and questions, see [SHADOW_ANALYZER_USAGE_GUIDE.md](../../SHADOW_ANALYZER_USAGE_GUIDE.md)
