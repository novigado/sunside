# Omniverse Nucleus & Connectors Integration Plan

## Overview
This document outlines the integration of NVIDIA Omniverse Nucleus and Connectors into the City Shadow Analyzer project, transforming it into a comprehensive, collaborative Omniverse solution.

## Architecture Enhancement

### Current State
- Standalone shadow analysis application
- Direct OpenStreetMap data loading
- Local USD scene generation
- REST API for shadow queries

### Enhanced State with Nucleus Integration
- **Nucleus-backed USD storage** for building geometry
- **Collaborative workflows** with shared city models
- **Connector ecosystem** for GIS tool integration
- **Cloud-ready** with remote data access

---

## 1. Nucleus Integration Features

### 1.1 Building Data Cache on Nucleus

**Extension**: `city.shadow_analyzer.nucleus`

**Purpose**: Cache OpenStreetMap building data as USD files on Nucleus server for faster loading and collaboration.

**Key Features**:
- **USD Building Library**: Convert OpenStreetMap buildings to USD and store on Nucleus
  - Path structure: `omniverse://nucleus-server/Projects/CityData/{city_name}/buildings.usd`
  - Metadata: lat/lon bounds, building count, last updated timestamp

- **Intelligent Caching**:
  - Check if building data exists on Nucleus before fetching from OpenStreetMap
  - Version control using USD layers
  - Incremental updates when new buildings are added

- **Collaborative Access**:
  - Multiple users can query the same cached building data
  - Read-only access for analysis, write access for administrators
  - Live updates when building data changes

**API Endpoints** (additions to REST API):
```python
POST /api/v1/nucleus/cache-buildings
{
  "latitude": 40.7589,
  "longitude": -73.9851,
  "radius_km": 1.0,
  "nucleus_path": "omniverse://server/Projects/CityData/manhattan"
}

GET /api/v1/nucleus/building-cache/{city_name}
# Returns metadata about cached building data

POST /api/v1/shadow/query-nucleus
{
  "nucleus_building_path": "omniverse://server/Projects/CityData/manhattan/buildings.usd",
  "query_points": [...],
  "datetime": "2026-01-14T15:00:00Z"
}
```

### 1.2 Results Persistence on Nucleus

**Purpose**: Store shadow analysis results as USD files for visualization and collaboration.

**Features**:
- Save shadow query results as USD with color-coded geometry
- Store time-series analyses (full-day shadow patterns)
- Share results via Nucleus URLs

**Use Cases**:
- Urban planners review shadow impact assessments
- Architects visualize shadow patterns in USD Composer
- Stakeholders collaborate on building placement decisions

---

## 2. Omniverse Connectors

### 2.1 QGIS Connector

**Purpose**: Export GIS data from QGIS to City Shadow Analyzer

**Features**:
- QGIS Plugin: "Omniverse Shadow Analyzer"
- Export building footprints with height data
- Automatic coordinate transformation
- Direct upload to Nucleus or local analysis

**Workflow**:
1. User selects building layer in QGIS
2. Specifies analysis parameters (date/time)
3. Plugin exports to USD and triggers shadow analysis
4. Results visualized back in QGIS or USD Composer

**Technical Stack**:
- Python QGIS plugin
- Uses `omni.client` library for Nucleus uploads
- REST API calls for shadow analysis

### 2.2 Web Connector

**Purpose**: Browser-based interface for Nucleus-stored city models

**Features**:
- **Nucleus Browser**: Navigate and select cached city data
- **Interactive Shadow Queries**: Click map to query shadow at location
- **Visualization**: Embed USD Composer Web Viewer for 3D results
- **Sharing**: Generate shareable links to Nucleus-stored analyses

**Technology**:
- React/Vue.js frontend
- Omniverse Streaming for 3D visualization
- REST API backend (our existing API)

### 2.3 Revit/3ds Max Connector (Future)

**Purpose**: Integrate with architectural design tools

**Features**:
- Export building designs to shadow analyzer
- Analyze shadow impact of proposed buildings
- Import existing city context from Nucleus

---

## 3. Implementation Phases

### Phase 1: Core Nucleus Integration (Week 1-2)
- [x] Create `city.shadow_analyzer.nucleus` extension
- [ ] Implement USD building cache system
- [ ] Add `omni.client` integration for Nucleus I/O
- [ ] Update REST API with Nucleus endpoints
- [ ] Test with local Nucleus server

### Phase 2: Enhanced API (Week 3)
- [ ] Add Nucleus-backed shadow queries
- [ ] Implement result persistence
- [ ] Add authentication/authorization for Nucleus access
- [ ] Performance optimization for remote data

### Phase 3: QGIS Connector (Week 4)
- [ ] Design QGIS plugin architecture
- [ ] Implement data export functionality
- [ ] Create plugin UI
- [ ] Test with real GIS datasets

### Phase 4: Web Connector (Week 5-6)
- [ ] Build web frontend
- [ ] Integrate Omniverse Streaming
- [ ] Implement Nucleus browser
- [ ] Deploy as web service

### Phase 5: Documentation & Examples (Week 7)
- [ ] Complete developer documentation
- [ ] Create tutorial videos
- [ ] Publish sample datasets on Nucleus
- [ ] Write integration guides

---

## 4. Technical Details

### 4.1 Nucleus Connection Setup

```python
import omni.client

# Configure Nucleus connection
nucleus_server = "omniverse://nucleus-server.company.com"
omni.client.set_authentication_message_box_enabled(False)

# Check connection
result = omni.client.stat(f"{nucleus_server}/Projects")
if result[0] == omni.client.Result.OK:
    print("Connected to Nucleus!")
```

### 4.2 USD Building Storage Format

```python
# Building data stored as USD with custom attributes
from pxr import Usd, UsdGeom, Sdf

stage = Usd.Stage.CreateNew("buildings.usd")
xform = UsdGeom.Xform.Define(stage, "/Buildings")

# Add metadata
stage.SetMetadata("city_name", "Manhattan")
stage.SetMetadata("latitude_min", 40.75)
stage.SetMetadata("latitude_max", 40.76)
stage.SetMetadata("longitude_min", -73.99)
stage.SetMetadata("longitude_max", -73.98)
stage.SetMetadata("building_count", 150)
stage.SetMetadata("last_updated", "2026-01-14T12:00:00Z")

# Save to Nucleus
stage.Save()
```

### 4.3 Connector Architecture

```
┌─────────────────┐
│   GIS Tools     │ (QGIS, ArcGIS)
│   (Connectors)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐         ┌─────────────────┐
│  Nucleus Server │◄────────┤   REST API      │
│  (USD Storage)  │         │   (FastAPI)     │
└────────┬────────┘         └────────┬────────┘
         │                           │
         ▼                           ▼
┌─────────────────┐         ┌─────────────────┐
│  USD Composer   │         │  Web Connector  │
│  (Visualization)│         │  (Browser)      │
└─────────────────┘         └─────────────────┘
```

---

## 5. Benefits

### For Urban Planners
- Access shared city models from anywhere
- Collaborate on shadow analysis with stakeholders
- Version control for planning scenarios

### For Architects
- Export designs directly from CAD tools
- Analyze shadow impact in city context
- Share results with clients via Nucleus links

### For Developers
- RESTful API for custom integrations
- Standard USD format for interoperability
- Extensible connector architecture

### For Cities
- Centralized repository of building data
- Automated shadow compliance checking
- Public access to shadow impact data

---

## 6. Learning Resources

### Nucleus Documentation
- [Omniverse Nucleus Setup](https://docs.omniverse.nvidia.com/nucleus/latest/)
- [omni.client API Reference](https://docs.omniverse.nvidia.com/kit/docs/omni.client/latest/)

### Connector Development
- [Creating Connectors](https://docs.omniverse.nvidia.com/connect/latest/index.html)
- [USD Python API](https://openusd.org/release/api/index.html)

### Streaming
- [Kit Streaming Documentation](https://docs.omniverse.nvidia.com/streaming-client/latest/)

---

## 7. Next Steps

Would you like me to start implementing:

1. **Option A**: Nucleus integration extension first (building cache system)
2. **Option B**: Web connector for browser-based access
3. **Option C**: QGIS connector for GIS integration
4. **Option D**: All of the above in phases

Each option provides hands-on experience with different aspects of the Omniverse platform!
