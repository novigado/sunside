# City Shadow Analyzer - Comprehensive Architecture Guide

**Last Updated**: January 19, 2026
**Version**: 0.2.0
**Audience**: New developers joining the project
**Branch**: main (with bugfix/nucleus-connection-not-initialized pending)

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [What This Application Does](#what-this-application-does)
3. [System Architecture](#system-architecture)
4. [Extension-Based Design](#extension-based-design)
5. [Core Components Deep Dive](#core-components-deep-dive)
6. [Data Flow & Processing Pipeline](#data-flow--processing-pipeline)
7. [Coordinate Systems & Transformations](#coordinate-systems--transformations)
8. [Caching Architecture (Critical!)](#caching-architecture-critical)
9. [Shadow Analysis Engine](#shadow-analysis-engine)
10. [API Server Architecture](#api-server-architecture)
11. [Known Limitations & Shortcuts](#known-limitations--shortcuts)
12. [Performance Optimizations](#performance-optimizations)
13. [Current Issues & Future Work](#current-issues--future-work)
14. [Development Setup](#development-setup)

---

## Project Overview

**City Shadow Analyzer** is a GPU-accelerated 3D application built on NVIDIA Omniverse Kit that analyzes urban shadows using real-time ray-casting and RTX rendering. It answers the question: "Is this GPS location in shadow at this time?"

### Key Use Cases

- **Urban planning**: Analyze sunlight access for buildings/parks
- **Solar panel optimization**: Determine best installation locations
- **Real estate**: Calculate shadow coverage for properties
- **API integration**: Headless shadow queries via REST API

### Technology Stack

- **Omniverse Kit SDK 109.0.2**: Application runtime and extension framework
- **USD (Universal Scene Description)**: 3D scene graph and data format
- **NVIDIA RTX**: Real-time ray-tracing for shadow rendering
- **OpenStreetMap API**: Building and road data source
- **Open-Elevation API**: Terrain elevation data
- **Nucleus Server**: High-performance content caching (10-20x speedup)
- **FastAPI**: REST API service layer
- **Python 3.10+**: Primary development language

---

## What This Application Does

### Primary Functions

1. **Sun Position Calculation**
   - Inputs: GPS coordinates (lat, lon), date/time (UTC)
   - Outputs: Sun azimuth (0-360°), elevation (-90 to +90°)
   - Uses astronomical algorithms (Julian date, sidereal time)

2. **Building Data Loading**
   - Fetches real building footprints from OpenStreetMap
   - Converts 2D GeoJSON polygons to 3D USD geometry
   - Estimates building heights from OSM tags or defaults
   - Loads roads for context visualization

3. **Terrain Integration**
   - Fetches elevation data from Open-Elevation API
   - Creates 3D terrain mesh with realistic topography
   - Positions buildings on terrain (not flat ground)
   - Accounts for elevation in shadow calculations

4. **Shadow Analysis**
   - CPU-based ray-casting from query point toward sun
   - Checks for occlusion by buildings or terrain
   - Returns shadow status + blocking object
   - Works in 3D with elevation data

5. **Interactive UI**
   - Visual 3D viewport with RTX-rendered shadows
   - Time controls (current time or custom datetime)
   - Location input (lat/lon or click on map)
   - Query mode: click to check shadow status
   - Building/terrain loading controls

6. **REST API**
   - Headless shadow queries via HTTP
   - JSON request/response format
   - Smartphone/web client support
   - Runs alongside desktop UI or standalone

---

## System Architecture

### High-Level Component Diagram

```
┌────────────────────────────────────────────────────────────────┐
│                    User Interfaces                             │
├─────────────────┬──────────────────┬──────────────────────────┤
│  Desktop UI     │   REST API       │   Web/Mobile Clients     │
│  (Kit Editor)   │   (FastAPI)      │   (HTTP/JSON)            │
└────────┬────────┴────────┬─────────┴────────┬─────────────────┘
         │                 │                   │
         └─────────────────┼───────────────────┘
                           │
         ┌─────────────────▼──────────────────────┐
         │  City Shadow Analyzer Core             │
         │  (Omniverse Kit Application)           │
         │  city.shadow_analyzer.kit.kit          │
         └─────────────────┬──────────────────────┘
                           │
         ┌─────────────────┼────────────────────┐
         │                 │                     │
    ┌────▼─────┐    ┌─────▼──────┐    ┌────────▼────────┐
    │   UI     │    │  Buildings │    │      Sun        │
    │Extension │    │  Extension │    │   Extension     │
    └────┬─────┘    └─────┬──────┘    └────────┬────────┘
         │                │                      │
         └────────────────┼──────────────────────┘
                          │
         ┌────────────────┴─────────────────────┐
         │                │                      │
    ┌────▼─────┐    ┌────▼──────┐       ┌──────▼────────┐
    │ Nucleus  │    │    API    │       │   External    │
    │ Cache    │    │  Server   │       │   Data APIs   │
    │ (USDC)   │    │ (FastAPI) │       │ (OSM/Elev)    │
    └──────────┘    └───────────┘       └───────────────┘
```

### Application Entry Point

**File**: `source/apps/city.shadow_analyzer.kit.kit`

This TOML configuration file defines:
- Extension dependencies (which extensions to load)
- Rendering settings (RTX, performance optimizations)
- Nucleus server configuration
- API server settings

**Key Configuration**:

```toml
[package]
title = "City Sun Analyzer"
version = "0.1.0"

# Extensions loaded in dependency order
[dependencies]
"city.shadow_analyzer.sun" = {}        # Sun calculations
"city.shadow_analyzer.buildings" = {}  # OSM building loader
"city.shadow_analyzer.nucleus" = {}    # Nucleus caching
"city.shadow_analyzer.ui" = {}         # Main UI
"city.shadow_analyzer.api" = {}        # REST API

# Nucleus configuration
[settings]
exts."city.shadow_analyzer.nucleus".nucleus_server = "omniverse://nucleus.swedencentral.cloudapp.azure.com"
exts."city.shadow_analyzer.nucleus".project_path = "/Projects/CityData"
exts."city.shadow_analyzer.nucleus".username = "omniverse"
exts."city.shadow_analyzer.nucleus".password = "Letmeinletmein12"

# API configuration
exts."city.shadow_analyzer.api".host = "0.0.0.0"
exts."city.shadow_analyzer.api".port = 8000

# Performance: Fast rendering (not path-traced)
rtx.rendermode = "RaytracedLighting"  # Real-time mode
rtx.pathtracing.enabled = false
rtx.shadows.enabled = true  # Keep shadows for analysis
```

---

## Extension-Based Design

Omniverse Kit uses an **extension-based architecture** where functionality is modularized into reusable components. Each extension is a self-contained Python package.

### Why Extensions?

- **Modularity**: Features can be enabled/disabled independently
- **Dependency Management**: Extensions declare dependencies explicitly
- **Hot-reloading**: Extensions can be reloaded without restarting the app
- **Reusability**: Extensions can be shared across projects

### Our Extensions

#### 1. `city.shadow_analyzer.sun`

**Purpose**: Sun position calculation engine
**Location**: `source/extensions/city.shadow_analyzer.sun/`

**Key Class**: `SunCalculator`

```python
class SunCalculator:
    """Calculate sun position using astronomical algorithms."""

    def calculate_sun_position(
        latitude: float,
        longitude: float,
        dt: datetime
    ) -> Tuple[float, float, float]:
        """
        Returns: (azimuth, elevation, distance)
        - azimuth: 0°=North, 90°=East, 180°=South, 270°=West
        - elevation: 90°=Overhead, 0°=Horizon, negative=Below
        - distance: ~1.0 AU (astronomical units)
        """
```

**Algorithm**: Simplified astronomical calculation
- Calculates Julian date from datetime
- Computes sun's ecliptic longitude
- Converts to equatorial coordinates (RA, declination)
- Calculates local sidereal time
- Converts to horizontal coordinates (azimuth, elevation)

**Accuracy**: ±0.5° for most locations/times (sufficient for shadow analysis)

**Shortcuts Taken**:
- Simplified algorithm (not NOAA's full algorithm)
- No atmospheric refraction correction
- No nutation/aberration corrections
- Good enough for visual shadow analysis!

---

#### 2. `city.shadow_analyzer.buildings`

**Purpose**: OpenStreetMap building/road data loader and geometry converter
**Location**: `source/extensions/city.shadow_analyzer.buildings/`

**Key Classes**:

##### `BuildingLoader`
- Fetches building data from Overpass API (OpenStreetMap)
- Queries buildings AND roads within radius
- Parses OSM JSON to extract geometry and metadata
- Handles building height extraction/estimation
- In-memory caching to avoid redundant API calls

```python
class BuildingLoader:
    def load_buildings(
        latitude: float,
        longitude: float,
        radius_km: float = 0.5
    ) -> List[Dict]:
        """
        Returns list of building dicts with:
        - id: OSM way ID
        - coordinates: [(lat, lon), ...]
        - height: Estimated height in meters
        - type: Building type from OSM tags
        """
```

**Height Estimation Logic**:
1. Use `height` tag if available (e.g., "15m")
2. Use `building:levels` × 3m per level
3. Default to 10m if no information

**Timeout Issue**: Overpass API can be slow (30-70 seconds). This is a known limitation of the free public API.

##### `BuildingGeometryConverter`
- Converts GPS coordinates to USD scene coordinates
- Creates 3D extruded building meshes
- Handles coordinate system transformations
- Positions buildings on terrain (elevation support)
- Color-codes buildings by type

**Critical Method**: `gps_to_scene_coords()`

```python
def gps_to_scene_coords(self, lat: float, lon: float) -> Tuple[float, float]:
    """
    Convert GPS to scene XZ coordinates.

    Coordinate system:
    - Y is UP (elevation)
    - X is East-West (longitude)
    - Z is North-South (latitude, NEGATED to fix flip)

    Uses reference point for consistent meter-per-degree calculation.
    """
    lat_diff = lat - self.reference_lat
    lon_diff = lon - self.reference_lon

    meters_per_lat_degree = 111000.0
    meters_per_lon_degree = 111000.0 * math.cos(math.radians(self.reference_lat))

    z = -(lat_diff * meters_per_lat_degree)  # Note: NEGATED
    x = lon_diff * meters_per_lon_degree

    return (x, z)
```

**Why the negation?** USD coordinate system convention required flipping Z to match north pointing in +Z direction.

##### `ShadowAnalyzer`
- CPU-based ray-casting for shadow detection
- Möller-Trumbore algorithm for ray-triangle intersection
- Checks occlusion by buildings AND terrain
- Returns shadow status + blocking object path

**Important**: This is NOT using RTX ray-tracing. It's CPU-based mesh intersection for API queries.

##### `TerrainLoader` & `TerrainMeshGenerator`
- Fetches elevation data from Open-Elevation API
- Creates grid of elevation samples
- Generates 3D mesh with realistic topography
- Provides elevation queries for building placement

---

#### 3. `city.shadow_analyzer.nucleus`

**Purpose**: Nucleus server integration for high-performance caching
**Location**: `source/extensions/city.shadow_analyzer.nucleus/`

**Why This Matters**: This is the **biggest performance optimization** in the system!

**Key Classes**:

##### `NucleusManager`
- Manages connection to Nucleus server
- Handles USD file read/write operations
- Directory creation and management
- Authentication (username/password)

```python
class NucleusManager:
    def save_buildings_to_nucleus(
        city_name: str,
        bounds_hash: str,
        usd_content,
        metadata: Dict
    ) -> Tuple[bool, Optional[str]]:
        """
        Saves building USD + metadata to Nucleus.
        Path: omniverse://server/Projects/CityData/{city_name}/buildings_{hash}.usdc
        """
```

##### `CityCacheManager`
- High-level caching API
- Cache key generation from GPS + radius
- Cache hit/miss detection
- USD stage export/import
- Metadata management

**Cache Key Generation**:
```python
def generate_cache_key(lat: float, lon: float, radius: float) -> Tuple[str, str]:
    """
    city_name: "city_37N_122W" (truncated lat/lon)
    bounds_hash: SHA256 of (lat, lon, radius)
    """
```

**3-Tier Caching Strategy**:

```
Query for buildings at (lat, lon)
    │
    ├─> 1. Check Nucleus Cache (FASTEST - 3-5s)
    │       ├─> USDC binary format on Nucleus server
    │       ├─> Cache HIT? → Load from Nucleus ✅
    │       └─> Cache MISS? ↓
    │
    ├─> 2. Fetch from OpenStreetMap API (SLOW - 30-70s)
    │       └─> Parse JSON, create geometry
    │
    └─> 3. Save to Nucleus for future use
            └─> Export USD stage to Nucleus
            └─> Save metadata (building count, bounds, timestamp)
```

**Performance Impact**: **10-20x faster** loading!
- First load: 30-70 seconds (OSM fetch + save to Nucleus)
- Subsequent loads: 3-5 seconds (Nucleus read)

**Nucleus File Structure**:
```
omniverse://nucleus.swedencentral.cloudapp.azure.com/Projects/CityData/
├── city_57N_11E/                    # Gothenburg area
│   ├── buildings_a1b2c3d4.usdc     # Cached buildings (binary USD)
│   ├── buildings_a1b2c3d4.usdc.meta.json  # Metadata
│   ├── terrain_x1y2z3.usdc         # Cached terrain
│   └── terrain_x1y2z3.usdc.meta.json
└── city_40N_74W/                    # Manhattan
    └── buildings_f6e5d4.usdc
```

**Metadata Example**:
```json
{
    "city_name": "city_57N_11E",
    "bounds_hash": "a1b2c3d4e5f6...",
    "latitude": 57.7089,
    "longitude": 11.9746,
    "radius_km": 1.0,
    "building_count": 1247,
    "min_elevation": 2.5,
    "max_elevation": 45.8,
    "timestamp": "2026-01-17T14:30:00Z",
    "data_source": "OpenStreetMap"
}
```

---

#### 4. `city.shadow_analyzer.ui`

**Purpose**: Main interactive user interface
**Location**: `source/extensions/city.shadow_analyzer.ui/`

**Size**: 2043 lines (the biggest extension!)

**Key Class**: `CityAnalyzerUIExtension`

**Responsibilities**:
- Creates main UI window with controls
- Manages USD scene (buildings, terrain, sun light)
- Handles user interactions (clicks, time changes)
- Coordinates between all other extensions
- Query mode for shadow testing
- Camera framing and viewport management

**UI Layout**:

```
┌─────────────────────────────────────────┐
│ City Shadow Analyzer                    │
├─────────────────────────────────────────┤
│ [Location]                              │
│   Latitude:  [57.7089    ]              │
│   Longitude: [11.9746    ]              │
│                                         │
│ [Time & Date]                           │
│   ○ Current Time  ● Custom Time         │
│   Date: [2026-01-19]  Time: [14:30:00] │
│                                         │
│ [Sun Position]                          │
│   Azimuth:    185.4° (S)                │
│   Elevation:  12.3° (Above horizon)     │
│                                         │
│ [Map Controls]                          │
│   Radius: [1.0] km                      │
│   [Load Buildings & Terrain]            │
│   Buildings: 1247 loaded                │
│   Terrain: Loaded (2.5m - 45.8m)        │
│                                         │
│ [Query Mode]                            │
│   [Enable Query Mode]                   │
│   Status: Click in viewport to query   │
│   Last Result: SHADOW (Building_123)    │
└─────────────────────────────────────────┘
```

**Critical Methods**:

##### `_load_buildings_sync()`
Implements the 3-tier caching strategy:

```python
def _load_buildings_sync(self, latitude, longitude, radius_km):
    """
    Load buildings with Nucleus caching.

    Flow:
    1. Check Nucleus cache → fast load if hit
    2. On miss: fetch from OSM API
    3. Create USD geometry
    4. Save to Nucleus for next time
    """
```

##### `_update_sun_position()`
Updates sun light direction based on time/location:

```python
def _update_sun_position(self):
    """
    1. Calculate sun position (azimuth, elevation)
    2. Convert to 3D direction vector
    3. Position/orient USD DistantLight
    4. Update UI display
    """
```

##### Query Mode Implementation
When query mode is enabled:
1. User clicks in viewport
2. Convert 2D screen click → 3D ray
3. Find intersection point with scene
4. Convert scene coords → GPS coords
5. Create query marker (visible sphere)
6. Perform shadow analysis
7. Display result

**Tricky Part**: Multi-threading coordination
- USD operations MUST happen on main thread
- FastAPI runs on separate thread
- Query requests are queued for main thread processing

---

#### 5. `city.shadow_analyzer.api`

**Purpose**: REST API service for headless shadow queries
**Location**: `source/extensions/city.shadow_analyzer.api/`

**Key Class**: `ShadowAnalyzerAPI`

**Framework**: FastAPI (modern Python web framework)

**Endpoints**:

##### `POST /shadow/query`
Check if location is in shadow.

**Request**:
```json
{
    "latitude": 57.7089,
    "longitude": 11.9746,
    "timestamp": "2026-01-19T14:30:00Z",  // Optional, defaults to now
    "search_radius": 500  // meters, default 100
}
```

**Response**:
```json
{
    "is_shadowed": true,
    "sun_azimuth": 185.4,
    "sun_elevation": 12.3,
    "blocking_object": "/World/Buildings/Building_123456",
    "latitude": 57.7089,
    "longitude": 11.9746,
    "timestamp": "2026-01-19T14:30:00Z",
    "message": "Location is in shadow cast by building"
}
```

##### `POST /sun/position`
Get sun position for location/time.

**Request**:
```json
{
    "latitude": 57.7089,
    "longitude": 11.9746,
    "timestamp": "2026-01-19T14:30:00Z"
}
```

**Response**:
```json
{
    "azimuth": 185.4,
    "elevation": 12.3,
    "distance": 1.0,
    "latitude": 57.7089,
    "longitude": 11.9746,
    "timestamp": "2026-01-19T14:30:00Z"
}
```

##### `GET /health`
Health check endpoint.

**Threading Architecture** (CRITICAL!):

```
FastAPI Thread                   Main Thread (USD/Kit)
     │                                  │
     │  Receives HTTP request           │
     │  /shadow/query                   │
     │  ↓                                │
     │  Validate input                  │
     │  Calculate sun position          │
     │  ↓                                │
     │  Queue shadow analysis ────────→ Queue
     │  request_id = 123                │
     │  ↓                                │
     │  Wait for result (async)         │
     │                                  │
     │                                  ← Process queue
     │                                  ↓
     │                                  Load USD stage
     │                                  Create geometry
     │                                  Cast ray
     │                                  Check shadow
     │                                  ↓
     │                                  Store result[123]
     │  ← Check result[123]             │
     │  ↓                                │
     │  Return JSON response            │
```

**Why This Complexity?**: USD operations are NOT thread-safe. All USD/scene operations must happen on the main Kit thread. FastAPI runs on a separate thread, so we use a queue to coordinate.

---

## Data Flow & Processing Pipeline

### Complete Shadow Query Flow

```
1. USER INPUT
   │
   ├─ UI: User clicks "Load Buildings & Terrain"
   │  └─ latitude, longitude, radius_km
   │
   └─ API: POST /shadow/query
      └─ latitude, longitude, timestamp

2. NUCLEUS CACHE CHECK
   │
   ├─ Generate cache key: city_name + bounds_hash
   ├─ Check if USDC file exists on Nucleus
   │
   ├─ CACHE HIT (3-5 seconds)
   │  └─ Load buildings from Nucleus USDC
   │  └─ Load terrain from Nucleus USDC
   │  └─ Copy to main USD stage
   │  └─ DONE ✅
   │
   └─ CACHE MISS → Continue to step 3

3. EXTERNAL DATA FETCH (30-70 seconds)
   │
   ├─ OpenStreetMap Overpass API
   │  └─ Query buildings within radius
   │  └─ Query roads within radius
   │  └─ Parse GeoJSON response
   │  └─ Extract building heights/types
   │
   └─ Open-Elevation API
      └─ Query elevation grid
      └─ Grid resolution: 50x50 points
      └─ Parse JSON response

4. COORDINATE TRANSFORMATION
   │
   ├─ Calculate reference point
   │  └─ Center of building bounding box
   │  └─ Used for consistent coordinate system
   │
   ├─ Convert GPS → Scene Coordinates
   │  └─ For each building vertex:
   │     └─ (lat, lon) → (x, z) in meters
   │     └─ Query terrain elevation → y
   │
   └─ Create terrain mesh
      └─ Grid of elevation samples
      └─ Generate triangulated mesh

5. USD GEOMETRY CREATION
   │
   ├─ Create /World/Buildings xform
   │  └─ For each building:
   │     └─ Create UsdGeom.Mesh
   │     └─ Set vertices (following terrain)
   │     └─ Set faces (extruded polygon)
   │     └─ Set color (by building type)
   │
   ├─ Create /World/Terrain mesh
   │  └─ Triangulated elevation grid
   │  └─ Textured or colored
   │
   └─ Create /World/Roads
      └─ Line geometry for roads

6. NUCLEUS CACHE SAVE
   │
   ├─ Export buildings to temp USD stage
   ├─ Export terrain to temp USD stage
   ├─ Save USDC files to Nucleus
   └─ Save metadata JSON
      └─ For future cache validation

7. SUN POSITION CALCULATION
   │
   ├─ Input: latitude, longitude, datetime
   ├─ Calculate Julian date
   ├─ Astronomical algorithms
   └─ Output: azimuth, elevation, direction vector

8. LIGHT POSITIONING
   │
   ├─ Create/update /World/SunLight (UsdLux.DistantLight)
   ├─ Set direction from sun direction vector
   ├─ Set intensity (5000-10000)
   └─ Set color (yellowish white)

9. SHADOW ANALYSIS (if query)
   │
   ├─ Ray casting from query point toward sun
   │  └─ Ray direction = OPPOSITE of sun direction
   │  └─ Origin = query point + 0.1m up
   │
   ├─ Check intersection with buildings
   │  └─ For each building mesh:
   │     └─ For each triangle:
   │        └─ Möller-Trumbore ray-triangle test
   │
   ├─ Check intersection with terrain
   │  └─ (same ray-triangle algorithm)
   │
   └─ Determine closest hit
      ├─ Hit? → SHADOW (return blocking object)
      └─ No hit? → SUNLIGHT

10. RESULT DISPLAY
    │
    ├─ UI Mode:
    │  └─ Create query marker sphere (red/green)
    │  └─ Update UI label with shadow status
    │  └─ Show blocking object path
    │
    └─ API Mode:
       └─ Return JSON response
          └─ is_shadowed, blocking_object, sun_position
```

---

## Coordinate Systems & Transformations

### GPS Coordinate System
- **Latitude**: -90° to +90° (negative = South, positive = North)
- **Longitude**: -180° to +180° (negative = West, positive = East)
- **Elevation**: Meters above sea level

### USD Scene Coordinate System
- **Y-Up**: Y axis points UP (elevation)
- **X-Axis**: East-West (longitude increases → X increases)
- **Z-Axis**: North-South (latitude increases → Z DECREASES due to negation)
- **Units**: Meters
- **Origin**: Reference point (typically building center)

### Transformation Formula

```python
# GPS → Scene Coordinates
def gps_to_scene_coords(lat, lon):
    lat_diff = lat - reference_lat
    lon_diff = lon - reference_lon

    # Approximation: degrees to meters
    meters_per_lat_degree = 111000.0  # ~111km per degree of latitude
    meters_per_lon_degree = 111000.0 * cos(reference_lat)  # Varies by latitude

    x = lon_diff * meters_per_lon_degree  # East-West
    z = -(lat_diff * meters_per_lat_degree)  # North-South (NEGATED!)

    return (x, z)

# Scene → GPS Coordinates
def scene_coords_to_gps(x, z):
    lat_diff = -z / meters_per_lat_degree  # Invert negation
    lon_diff = x / meters_per_lon_degree

    lat = reference_lat + lat_diff
    lon = reference_lon + lon_diff

    return (lat, lon)
```

### Why the Z Negation?

**Problem**: OpenStreetMap uses geographic north (latitude increases northward), but USD's default coordinate system had north pointing in -Z direction.

**Solution**: Negate Z coordinate during conversion so north = +Z in scene.

**Impact**: All coordinate conversions must account for this!

---

## Caching Architecture (Critical!)

### Why Caching Matters

**Without caching**: Every query requires 30-70 seconds to fetch buildings from OpenStreetMap API.

**With Nucleus caching**: Subsequent queries take 3-5 seconds (10-20x faster!).

### Cache Invalidation Strategy

**Current**: No automatic invalidation
- Cache lives forever until manually deleted
- Building data from OSM is relatively static

**Future**: Add cache expiry
- 30-day TTL (time-to-live)
- Check metadata timestamp on cache load
- Invalidate if too old

### Cache Key Generation

```python
def generate_cache_key(lat, lon, radius):
    # City name: truncated GPS coordinates
    city_name = f"city_{int(lat)}N_{abs(int(lon))}E"

    # Bounds hash: unique identifier for exact bounds
    bounds_str = f"{lat:.6f},{lon:.6f},{radius:.3f}"
    bounds_hash = hashlib.sha256(bounds_str.encode()).hexdigest()[:12]

    return (city_name, bounds_hash)

# Example: (57.7089, 11.9746, 1.0)
# → city_name = "city_57N_11E"
# → bounds_hash = "a1b2c3d4e5f6"
# → file = "omniverse://.../city_57N_11E/buildings_a1b2c3d4e5f6.usdc"
```

### Metadata Schema

Stored alongside USD files as `.meta.json`:

```json
{
    // Cache identification
    "city_name": "city_57N_11E",
    "bounds_hash": "a1b2c3d4e5f6",

    // Query parameters (for validation)
    "latitude": 57.7089,
    "longitude": 11.9746,
    "radius_km": 1.0,

    // Content statistics
    "building_count": 1247,
    "min_elevation": 2.5,
    "max_elevation": 45.8,
    "grid_resolution": 50,

    // Cache metadata
    "timestamp": "2026-01-17T14:30:00Z",
    "data_source": "OpenStreetMap",
    "elevation_source": "Open-Elevation",

    // Optional: cache validation
    "expires_at": "2026-02-16T14:30:00Z"  // Future feature
}
```

---

## Shadow Analysis Engine

### Ray Casting Algorithm

**Purpose**: Determine if a point is in shadow by casting a ray toward the sun.

**Algorithm**: Möller-Trumbore ray-triangle intersection test

```python
def is_point_in_shadow(point, sun_direction):
    """
    Args:
        point: 3D location to test (x, y, z)
        sun_direction: Direction FROM sun TO ground (normalized)

    Returns:
        (is_shadowed: bool, blocking_object: Optional[str])
    """

    # Ray direction: FROM point TOWARD sun (opposite of sun_direction)
    ray_direction = -sun_direction
    ray_origin = point + Vec3(0, 0.1, 0)  # Slightly above point

    closest_hit = None
    closest_distance = float('inf')

    # Check all building meshes
    for building in buildings:
        for triangle in building.triangles:
            hit = ray_triangle_intersection(
                ray_origin, ray_direction, triangle
            )
            if hit and hit.distance < closest_distance:
                closest_hit = (building, hit.distance)
                closest_distance = hit.distance

    # Check terrain mesh
    for triangle in terrain.triangles:
        hit = ray_triangle_intersection(
            ray_origin, ray_direction, triangle
        )
        if hit and hit.distance < closest_distance:
            # Ignore close terrain hits (< 5m) - likely local terrain
            if hit.distance >= 5.0:
                closest_hit = (terrain, hit.distance)
                closest_distance = hit.distance

    if closest_hit:
        return (True, closest_hit[0].path)
    else:
        return (False, None)
```

### Möller-Trumbore Algorithm

Fast ray-triangle intersection test (used in graphics engines):

```python
def ray_triangle_intersection(ray_origin, ray_direction, triangle):
    """
    Returns: distance to hit point, or None if no intersection
    """
    v0, v1, v2 = triangle.vertices

    # Edge vectors
    edge1 = v1 - v0
    edge2 = v2 - v0

    # Calculate determinant
    h = cross(ray_direction, edge2)
    a = dot(edge1, h)

    if abs(a) < EPSILON:
        return None  # Ray parallel to triangle

    f = 1.0 / a
    s = ray_origin - v0
    u = f * dot(s, h)

    if u < 0.0 or u > 1.0:
        return None  # Outside triangle

    q = cross(s, edge1)
    v = f * dot(ray_direction, q)

    if v < 0.0 or u + v > 1.0:
        return None  # Outside triangle

    # Calculate intersection distance
    t = f * dot(edge2, q)

    if t > EPSILON:
        return t  # Ray intersects triangle
    else:
        return None  # Behind ray origin
```

### CPU vs GPU Ray Casting

**Current Implementation**: CPU-based ray casting
- Iterates through all triangles manually
- Slow for large scenes (1000+ buildings)
- Good enough for API queries

**Future Optimization**: Use RTX ray-tracing
- Hardware-accelerated ray casting
- 100-1000x faster
- Requires PhysX scene query API integration

---

## API Server Architecture

### FastAPI + Omniverse Kit Integration

**Challenge**: FastAPI runs on a separate thread, but USD operations must happen on the main thread.

**Solution**: Queue-based coordination

```python
class ShadowAnalyzerAPI:
    def __init__(self):
        self.request_queue = queue.Queue()
        self.result_map = {}  # request_id → result
        self.next_request_id = 0

    async def handle_shadow_query(self, request: ShadowQueryRequest):
        """FastAPI endpoint (runs on FastAPI thread)"""

        # 1. Calculate sun position (thread-safe)
        azimuth, elevation = calculate_sun_position(
            request.latitude, request.longitude, request.timestamp
        )

        # 2. Queue shadow check for main thread
        request_id = self.next_request_id
        self.next_request_id += 1

        self.request_queue.put((
            request_id,
            request.latitude,
            request.longitude,
            azimuth,
            elevation
        ))

        # 3. Wait for result (async polling)
        while request_id not in self.result_map:
            await asyncio.sleep(0.1)  # Poll every 100ms

        # 4. Get result and return
        is_shadowed, blocking_object = self.result_map.pop(request_id)

        return ShadowQueryResponse(
            is_shadowed=is_shadowed,
            blocking_object=blocking_object,
            sun_azimuth=azimuth,
            sun_elevation=elevation,
            ...
        )

    def process_main_thread_queue(self):
        """Called from extension update loop (main thread)"""

        while not self.request_queue.empty():
            request_id, lat, lon, azimuth, elevation = self.request_queue.get()

            # Perform shadow check on main thread (USD operations)
            is_shadowed, blocking_object = self._perform_shadow_check(
                lat, lon, azimuth, elevation
            )

            # Store result for FastAPI thread to retrieve
            self.result_map[request_id] = (is_shadowed, blocking_object)
```

### Extension Update Loop Integration

The API extension hooks into Kit's update loop:

```python
class CityAnalyzerAPIExtension(omni.ext.IExt):
    def on_startup(self, ext_id):
        self.api_server = ShadowAnalyzerAPI()
        self.api_server.start()  # Start FastAPI in background thread

        # Register update callback
        self._update_stream = omni.kit.app.get_app().get_update_event_stream()
        self._update_sub = self._update_stream.create_subscription_to_pop(
            self._on_update, name="shadow_api_update"
        )

    def _on_update(self, event):
        """Called every frame (~60 FPS)"""
        self.api_server.process_main_thread_queue()
```

---

## Known Limitations & Shortcuts

### 1. Sun Position Accuracy

**Current**: Simplified astronomical algorithm
**Accuracy**: ±0.5° (sufficient for shadows)
**Missing**:
- Atmospheric refraction
- Nutation (Earth's wobble)
- Aberration (observer motion)

**Impact**: Minimal - visual shadow analysis doesn't need sub-degree accuracy.

### 2. Building Height Estimation

**Current**: Estimate from OSM tags or default to 10m
**Accuracy**: ±50% in many cases
**Missing**:
- Actual surveyed building heights
- Roof shape information
- Multi-part buildings

**Impact**: Moderate - shadows are approximate. Good for general analysis, not precise.

### 3. OpenStreetMap API Performance

**Current**: 30-70 second queries (free public API)
**Limitation**: Rate limiting, server congestion
**Missing**:
- Local OSM database (would be 1-2 seconds)
- Paid OSM provider (faster)

**Mitigation**: Nucleus caching makes this a one-time cost per location.

### 4. Terrain Elevation Resolution

**Current**: 50x50 grid (~20m spacing for 1km radius)
**Accuracy**: ±5m elevation
**Missing**:
- High-resolution terrain (1m DEM)
- Lidar data integration

**Impact**: Low - elevation is mostly for visual realism. Shadow analysis works with coarse terrain.

### 5. Shadow Analysis Performance

**Current**: CPU-based ray casting (slow for large scenes)
**Performance**: 100-500ms per query for 1000 buildings
**Missing**:
- RTX hardware ray-tracing (would be <1ms)

**Impact**: Acceptable for interactive UI, but limits API throughput.

### 6. Terrain Integration Issue (CURRENT BUG!)

**Status**: ~~Terrain loading temporarily disabled~~ FIXED on feature/terrain-elevation-integration
**Problem**: ~~Buildings appear buried/floating when terrain elevation != 0~~ RESOLVED
**Current Status**: Merged to main, terrain integration working correctly

### 7. Nucleus Caching Disabled (FIXED!)

**Status**: FIXED on bugfix/nucleus-connection-not-initialized
**Problem**: NucleusManager never called `check_connection()` during initialization
**Impact**: `self._connected` remained False, all cache operations silently failed
**Symptoms**:
- All building loads took 30-70s (no cache hits)
- Nothing saved to Nucleus server
- Logs showed "Not connected to Nucleus" warnings
**Root Cause**: Constructor set `self._connected = False` but never called `check_connection()` to actually test and establish the connection
**Fix**: Added `self.check_connection()` call at end of `__init__()` method

---

## Performance Optimizations

### Rendering Optimizations

**Goal**: Fast real-time rendering (not photorealistic)

Settings in `.kit` file:

```toml
[settings]
# Use real-time ray tracing (not path tracing)
rtx.rendermode = "RaytracedLighting"
rtx.pathtracing.enabled = false

# Disable expensive features
rtx.newDenoiser.enabled = false
rtx.post.aa.op = 0  # No anti-aliasing
rtx.reflections.enabled = false
rtx.translucency.enabled = false
rtx.ambientOcclusion.enabled = false

# Keep shadows (essential!)
rtx.shadows.enabled = true

# Lower resolution
app.renderer.resolution.width = 1280
app.renderer.resolution.height = 720
```

**Impact**: 5-10x faster rendering, still looks good enough for shadow analysis.

### Nucleus Caching (10-20x)

Already covered above - this is the BIGGEST optimization!

### In-Memory Building Cache

`BuildingLoader` caches OSM responses in memory:

```python
self._cache = {}  # GPS coords → building list
cache_key = f"{latitude:.5f},{longitude:.5f},{radius_km}"
```

**Impact**: Avoid redundant OSM queries within same session.

### Async Operations

UI operations are async to prevent blocking:

```python
async def _load_buildings_async(self, latitude, longitude, radius_km):
    """Non-blocking building load"""
    # Run sync load in thread pool
    await asyncio.get_event_loop().run_in_executor(
        None,
        self._load_buildings_sync,
        latitude, longitude, radius_km
    )
```

**Impact**: UI remains responsive during slow OSM queries.

---

## Current Issues & Future Work

### Active Issues

1. **Terrain Integration Bug**
   - Buildings not properly positioned on terrain
   - Fix in progress on `feature/terrain-elevation-integration` branch

2. **OSM API Timeouts**
   - Overpass API frequently slow/unresponsive
   - Consider self-hosted OSM database

3. **Shadow Query Performance**
   - CPU ray casting slow for large scenes
   - Consider RTX hardware ray-tracing

### Planned Features

1. **Cache Expiry**
   - Add 30-day TTL to cached data
   - Automatic re-fetch when expired

2. **Query Result Persistence**
   - Store shadow query results in Nucleus
   - Time-series shadow analysis

3. **Mobile UI**
   - Smartphone-optimized web interface
   - GPS-based location input

4. **Batch Analysis**
   - Analyze entire grid of points
   - Generate shadow coverage heatmaps

5. **Terrain Improvements**
   - Higher resolution elevation data
   - Texture mapping for realism

6. **Building Details**
   - Window/door geometry
   - Roof shapes (pitched, flat, etc.)
   - Facade textures

---

## Development Setup

### Prerequisites

- **NVIDIA Omniverse Launcher**: Install from nvidia.com/omniverse
- **Omniverse Kit SDK 109.0.2**: Included with launcher
- **Nucleus Server**: Install Nucleus Workstation OR use cloud Nucleus
- **Python 3.10+**: Included with Kit
- **Git**: For version control
- **VS Code**: Recommended IDE (with Python extension)

### Building the Application

```powershell
# Clone repository
git clone <repo_url>
cd kit-app-template

# Checkout current development branch
git checkout feature/terrain-elevation-integration

# Build application (fetches dependencies)
.\repo.bat build

# Launch desktop UI
.\repo.bat launch -- source/apps/city.shadow_analyzer.kit.kit

# Launch in developer mode (with debug console)
.\repo.bat launch -d -- source/apps/city.shadow_analyzer.kit.kit
```

### Running Tests

```powershell
# Run unit tests
.\repo.bat test
```

### Nucleus Server Setup

**Option 1: Local Nucleus (Development)**

1. Install Nucleus Workstation from Omniverse Launcher
2. Configure in `.kit` file:
   ```toml
   exts."city.shadow_analyzer.nucleus".nucleus_server = "omniverse://localhost"
   ```

**Option 2: Cloud Nucleus (Production)**

1. Use Azure-hosted Nucleus server
2. Configure in `.kit` file:
   ```toml
   exts."city.shadow_analyzer.nucleus".nucleus_server = "omniverse://nucleus.swedencentral.cloudapp.azure.com"
   exts."city.shadow_analyzer.nucleus".username = "omniverse"
   exts."city.shadow_analyzer.nucleus".password = "Letmeinletmein12"
   ```

### Extension Development

To modify an extension:

1. Edit files in `source/extensions/<extension_name>/`
2. Reload extension: In Kit console, run `omni.ext.reload("<extension_name>")`
3. OR restart application to load changes

### Debugging

**Enable logging**:
```python
import carb
carb.log_info("[YourExtension] Debug message")
carb.log_warn("[YourExtension] Warning message")
carb.log_error("[YourExtension] Error message")
```

**View logs**:
- Desktop UI: Console window (Window → Console)
- Log file: `_build/logs/kit.log`

**Python debugging**:
- Add VS Code launch configuration
- Attach debugger to Kit process
- Set breakpoints in extension code

---

## Summary: Key Takeaways

### What Works Well

✅ **Sun position calculation** - Accurate astronomical algorithms
✅ **Building data loading** - Real OSM data with height estimation
✅ **Nucleus caching** - 10-20x performance improvement
✅ **Shadow analysis** - CPU ray-casting gives correct results
✅ **API integration** - REST API works for headless queries
✅ **Coordinate system** - GPS ↔ scene transformations accurate

### What Needs Work

⚠️ **~~Nucleus caching broken~~** - FIXED! Was not connecting during init
⚠️ **OSM API speed** - Slow public API (30-70s queries)
⚠️ **Shadow query performance** - CPU ray casting bottleneck
⚠️ **Cache invalidation** - No automatic expiry yet

### Architectural Highlights

🏆 **Extension modularity** - Clean separation of concerns
🏆 **3-tier caching** - Excellent performance optimization
🏆 **Thread coordination** - Elegant queue-based API integration
🏆 **USD scene graph** - Leverages industry-standard format

### Most Important Files to Understand

1. **`city.shadow_analyzer.kit.kit`** - Application entry point and configuration
2. **`city/shadow_analyzer/ui/extension.py`** - Main UI logic and coordination (2043 lines!)
3. **`city/shadow_analyzer/buildings/building_loader.py`** - OSM data fetching
4. **`city/shadow_analyzer/buildings/geometry_converter.py`** - GPS → USD conversion
5. **`city/shadow_analyzer/nucleus/city_cache.py`** - Caching strategy
6. **`city/shadow_analyzer/sun/sun_calculator.py`** - Sun position algorithms
7. **`city/shadow_analyzer/api/api_server.py`** - REST API implementation

---

**Welcome to the team! This guide should give you a comprehensive understanding of how everything works. Don't hesitate to dig into the code - the architecture is modular and well-commented.**

**Happy coding! 🌞🏙️**
