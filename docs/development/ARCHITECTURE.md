# City Shadow Analyzer - System Architecture

**Last Updated**: January 17, 2026  
**Version**: 0.2.0

---

## Table of Contents
- [Overview](#overview)
- [System Architecture](#system-architecture)
- [Component Architecture](#component-architecture)
- [Data Flow](#data-flow)
- [Extension System](#extension-system)
- [Caching Architecture](#caching-architecture)
- [API Architecture](#api-architecture)
- [Deployment Models](#deployment-models)

---

## Overview

City Shadow Analyzer is an Omniverse Kit-based application that analyzes urban shadows using ray-casting and real-time 3D rendering. The system is built on NVIDIA Omniverse Kit SDK and leverages USD (Universal Scene Description) for 3D data representation.

**Key Technologies:**
- **Omniverse Kit SDK**: Core runtime and extension framework
- **USD (Universal Scene Description)**: 3D scene graph and data format
- **Nucleus**: Content management and caching server
- **FastAPI**: REST API service layer
- **Python**: Primary development language

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     User Interfaces                              │
├──────────────────┬──────────────────┬──────────────────────────┤
│  Desktop UI      │   REST API       │   Web Clients            │
│  (Kit Editor)    │   (FastAPI)      │   (HTTP/JSON)            │
└────────┬─────────┴────────┬─────────┴────────┬─────────────────┘
         │                  │                   │
         └──────────────────┼───────────────────┘
                            │
         ┌──────────────────┴─────────────────────┐
         │     City Shadow Analyzer Core          │
         │  (Omniverse Kit Application)           │
         └──────────────────┬─────────────────────┘
                            │
         ┌──────────────────┼─────────────────────┐
         │                  │                      │
    ┌────▼────┐      ┌─────▼─────┐       ┌───────▼────────┐
    │ Shadow  │      │  Terrain  │       │   Building     │
    │ Engine  │      │  Service  │       │   Manager      │
    └────┬────┘      └─────┬─────┘       └───────┬────────┘
         │                  │                      │
         └──────────────────┼──────────────────────┘
                            │
         ┌──────────────────┴─────────────────────┐
         │          USD Scene Graph               │
         │     (3D Data Representation)           │
         └──────────────────┬─────────────────────┘
                            │
         ┌──────────────────┼─────────────────────┐
         │                  │                      │
    ┌────▼─────┐      ┌────▼──────┐       ┌──────▼───────┐
    │ Local    │      │  Nucleus  │       │  External    │
    │ Cache    │      │  Server   │       │  Data APIs   │
    │ (JSON)   │      │  (USD)    │       │  (OpenStreet)│
    └──────────┘      └───────────┘       └──────────────┘
```

---

## Component Architecture

### Core Components

#### 1. Shadow Analysis Engine
**Location**: `source/extensions/city.shadow_analyzer.python/city/shadow_analyzer/python/`

**Responsibilities:**
- Ray-casting computations for shadow analysis
- Sun position calculations (time/date/location)
- Shadow coverage percentage calculations
- Integration with Omniverse rendering pipeline

**Key Classes:**
- `ShadowAnalyzer`: Main analysis orchestration
- `RayCaster`: Ray-casting implementation
- `SunCalculator`: Solar position algorithms

#### 2. Building Manager
**Location**: `source/extensions/city.shadow_analyzer.python/city/shadow_analyzer/python/`

**Responsibilities:**
- Load building data from OpenStreetMap
- Convert GeoJSON to USD geometry
- Manage building cache (JSON + Nucleus)
- Handle building metadata and attributes

**Key Classes:**
- `BuildingManager`: Building lifecycle management
- `BuildingCache`: Caching strategy (local + Nucleus)
- `GeoJSONConverter`: Geographic data conversion

**Caching Strategy:**
```
Load Request
    │
    ├─> Check Nucleus Cache (USDC)
    │       ├─> Valid? → Load from Nucleus (3-5s) ✅
    │       └─> Invalid/Missing? ↓
    │
    ├─> Check Local Cache (JSON)
    │       ├─> Valid? → Load from JSON (10-15s) ✅
    │       └─> Invalid/Missing? ↓
    │
    └─> Fetch from OpenStreetMap API (30-70s)
            └─> Save to Local Cache (JSON)
            └─> Save to Nucleus Cache (USDC)
```

#### 3. Terrain Service
**Location**: `source/extensions/city.shadow_analyzer.python/city/shadow_analyzer/python/`

**Responsibilities:**
- Fetch elevation data from Open-Elevation API
- Cache terrain data (local + Nucleus)
- Generate terrain mesh geometry
- Handle terrain interpolation

**Key Classes:**
- `TerrainService`: Terrain data management
- `TerrainCache`: Elevation caching
- `TerrainMeshGenerator`: USD mesh generation

#### 4. API Service Layer
**Location**: `source/extensions/city.shadow_analyzer.api/city/shadow_analyzer/api/`

**Responsibilities:**
- REST API endpoints for shadow analysis
- Request validation and error handling
- Headless operation (no UI)
- JSON request/response handling

**Key Files:**
- `api_service.py`: FastAPI application
- `endpoints/`: API route handlers
- `schemas/`: Request/response models

---

## Data Flow

### Shadow Analysis Request Flow

```
1. User Request
   │ Desktop UI or REST API
   │ Location: (lat, lon), Date/Time, Buildings
   │
   ▼
2. Building Loading
   │ BuildingManager checks cache hierarchy
   │ Nucleus (fastest) → JSON (medium) → API (slowest)
   │
   ▼
3. Terrain Loading
   │ TerrainService fetches elevation data
   │ Creates terrain mesh in USD
   │
   ▼
4. USD Scene Construction
   │ Buildings + Terrain combined in scene graph
   │ Materials and attributes applied
   │
   ▼
5. Shadow Analysis
   │ ShadowAnalyzer calculates sun position
   │ RayCaster performs ray-casting
   │ Shadow coverage computed
   │
   ▼
6. Results
   │ Desktop UI: Visual rendering + statistics
   │ REST API: JSON response with percentages
```

### Caching Architecture Details

#### Building Cache (3-Tier)

**Tier 1: Nucleus Cache (Fastest - 3-5s)**
```python
# USDC binary format on Nucleus server
Location: omniverse://localhost/Projects/CityBuildings/{city_name}_{hash}.usdc
Format: Binary USD (USDC)
Benefits:
  - 10-20x faster than JSON
  - Shared across users/sessions
  - Version controlled
  - Binary format (smaller, faster)
```

**Tier 2: Local JSON Cache (Medium - 10-15s)**
```python
# JSON format on local disk
Location: _build/cache/{city_name}_{hash}.json
Format: JSON (GeoJSON-compatible)
Benefits:
  - Works without Nucleus
  - Human-readable
  - Easy debugging
```

**Tier 3: OpenStreetMap API (Slowest - 30-70s)**
```python
# Live fetch from Overpass API
Source: https://overpass-api.de/api/interpreter
Format: GeoJSON
Benefits:
  - Always up-to-date
  - No storage required
```

#### Terrain Cache (2-Tier)

**Tier 1: Nucleus Cache (Fast)**
```python
# USDC format with elevation data
Location: omniverse://localhost/Projects/Terrain/{location_hash}.usdc
Format: Binary USD with point cloud
```

**Tier 2: Open-Elevation API (Slow)**
```python
# Live fetch from elevation API
Source: https://api.open-elevation.com/api/v1/lookup
Format: JSON with elevation points
```

---

## Extension System

City Shadow Analyzer follows the Omniverse Kit extension architecture:

### Extension Structure

```
source/extensions/
├── city.shadow_analyzer.python/         # Core Python extension
│   ├── city/shadow_analyzer/python/
│   │   ├── __init__.py
│   │   ├── shadow_analyzer.py           # Main logic
│   │   ├── building_manager.py          # Building handling
│   │   ├── terrain_service.py           # Terrain handling
│   │   └── utils/                       # Utilities
│   └── config/extension.toml            # Extension metadata
│
├── city.shadow_analyzer.ui/             # UI extension
│   ├── city/shadow_analyzer/ui/
│   │   ├── __init__.py
│   │   ├── main_window.py               # Main UI window
│   │   └── widgets/                     # Custom widgets
│   └── config/extension.toml
│
└── city.shadow_analyzer.api/            # API extension
    ├── city/shadow_analyzer/api/
    │   ├── __init__.py
    │   ├── api_service.py               # FastAPI app
    │   └── endpoints/                   # API routes
    └── config/extension.toml
```

### Extension Lifecycle

```python
class Extension:
    def on_startup(self, ext_id: str):
        """Called when extension is enabled"""
        # Initialize services
        # Register event handlers
        # Load configuration
        
    def on_shutdown(self):
        """Called when extension is disabled"""
        # Cleanup resources
        # Unregister handlers
        # Save state
```

---

## API Architecture

### REST API Design

**Base URL**: `http://localhost:8011`

**Endpoints**:
```
POST /analyze
├─> Input: Location, DateTime, BuildingFilters
├─> Process: Load buildings, terrain, analyze shadows
└─> Output: Shadow percentages, building data

GET /health
└─> Output: Service status, cache stats

GET /buildings
├─> Input: BoundingBox, Filters
└─> Output: Building list (cached if available)

GET /terrain
├─> Input: Location, Radius
└─> Output: Elevation data
```

### API Request Flow

```
Client Request
    │
    ├─> FastAPI Router
    │       ├─> Request Validation (Pydantic)
    │       ├─> Authentication (if enabled)
    │       └─> Rate Limiting (if enabled)
    │
    ├─> Shadow Analyzer Core
    │       ├─> Check Nucleus Cache
    │       ├─> Load Buildings
    │       ├─> Load Terrain
    │       └─> Perform Analysis
    │
    └─> Response Serialization
            └─> JSON Response
```

---

## Deployment Models

### 1. Desktop Application
**Kit File**: `city.shadow_analyzer.kit.kit`

```
Features:
- Full UI with 3D viewport
- Interactive controls
- Real-time visualization
- Developer tools

Target Users:
- Urban planners
- Architects
- Researchers

Launch:
repo.bat launch -- source/apps/city.shadow_analyzer.kit.kit
```

### 2. API Service (Headless)
**Kit File**: `city.shadow_analyzer.api_service.kit`

```
Features:
- No UI (headless)
- REST API endpoints
- Background processing
- Optimized for throughput

Target Users:
- Web applications
- Automated systems
- Integration services

Launch:
repo.bat launch -- source/apps/city.shadow_analyzer.api_service.kit
```

### 3. Docker Container (Future)
```dockerfile
# Containerized deployment with Nucleus
FROM nvcr.io/nvidia/omniverse/kit:latest
COPY source/ /app/source/
EXPOSE 8011
CMD ["./kit", "--exec", "source/apps/city.shadow_analyzer.api_service.kit"]
```

---

## Performance Characteristics

### Caching Performance

| Operation | No Cache | JSON Cache | Nucleus Cache | Improvement |
|-----------|----------|------------|---------------|-------------|
| San Francisco Buildings | 42s | 13s | **3.2s** | 13.1x |
| New York Buildings | 67s | 19s | **4.8s** | 14.0x |
| Boston Buildings | 28s | 9s | **2.4s** | 11.7x |
| Terrain Elevation | 15s | 5s | **1.5s** | 10.0x |

### Memory Usage

```
Component Memory Footprint:
- Base Kit Runtime: ~500 MB
- Shadow Analyzer Extension: ~50 MB
- USD Scene (1000 buildings): ~200 MB
- Terrain Mesh: ~50 MB
- Total (typical): ~800 MB
```

---

## Technology Stack

### Core Technologies
- **Omniverse Kit SDK 109.0.2**: Application runtime
- **USD 24.11**: 3D data representation
- **Python 3.10**: Extension development
- **FastAPI**: REST API framework
- **Nucleus**: Content management server

### External APIs
- **OpenStreetMap Overpass API**: Building data
- **Open-Elevation API**: Terrain elevation data

### Development Tools
- **Premake5**: Build system
- **Repo Tools**: Omniverse build orchestration
- **pytest**: Testing framework
- **Git**: Version control

---

## Security Considerations

### API Security
- [ ] Authentication tokens (future)
- [ ] Rate limiting (future)
- [ ] Input validation (✅ implemented)
- [ ] CORS configuration (✅ implemented)

### Nucleus Security
- [x] Credentials management (environment variables)
- [x] Connection validation
- [x] Graceful fallback on failure

### Data Privacy
- [x] No user tracking
- [x] No data collection
- [x] Public data sources only (OSM, elevation APIs)

---

## Future Architecture Enhancements

### Planned Improvements
1. **Distributed Caching**: Redis for multi-instance cache sharing
2. **Load Balancing**: Multiple API instances behind load balancer
3. **Database Integration**: PostgreSQL for user data and analysis history
4. **Real-time Updates**: WebSocket support for live shadow updates
5. **Cloud Deployment**: AWS/Azure containerized deployment
6. **Authentication**: OAuth2/JWT token authentication
7. **Analytics**: Usage metrics and performance monitoring

### Scalability Roadmap
- **Phase 1** (Current): Single instance, Nucleus caching
- **Phase 2** (Q2 2026): Multiple instances, Redis caching
- **Phase 3** (Q3 2026): Cloud deployment, database integration
- **Phase 4** (Q4 2026): Global CDN, distributed compute

---

## References

- [Omniverse Kit SDK Documentation](https://docs.omniverse.nvidia.com/kit/docs/kit-manual/latest/index.html)
- [USD Documentation](https://openusd.org/release/index.html)
- [OpenStreetMap API](https://wiki.openstreetmap.org/wiki/API)
- [NVIDIA Nucleus Documentation](https://docs.omniverse.nvidia.com/nucleus/latest/index.html)

---

**Document Owner**: Development Team  
**Review Cycle**: Quarterly  
**Next Review**: April 2026
