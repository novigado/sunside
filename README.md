# City Shadow Analyzer

<p align="center">
  <strong>GPU-Accelerated Solar Analysis for Urban Environments</strong><br>
  Built on NVIDIA Omniverse Kit SDK with OpenUSD
</p>

---

## Overview

**City Shadow Analyzer** is a high-performance application for analyzing solar shadows in urban environments. It combines real-time 3D visualization, terrain elevation data, and GPU-accelerated ray casting to determine solar access for any point in a city at any time of day.

### Key Features

- **OpenStreetMap Integration** - Automatic building and road data loading
- **Terrain Elevation** - Real-world elevation data from Open-Elevation API
- **Solar Position Calculation** - Accurate sun position for any location and time
- **Shadow Analysis** - GPU-accelerated ray casting for shadow detection
- **Nucleus Caching** - 10-20x faster loading with Omniverse Nucleus
- **REST API** - Headless service mode for API queries
- **Real-time 3D Visualization** - Interactive scene navigation and queries

### Performance

| Feature | Without Cache | With Nucleus Cache | Speedup |
|---------|--------------|-------------------|---------|
| Building Load | 30-60 seconds | 2-5 seconds | **10-20x** |
| Terrain Load | 10-20 seconds | 2-3 seconds | **5-10x** |
| Combined | 40-70 seconds | 5-10 seconds | **8-10x** |

---

## Quick Start

### Prerequisites

- **Windows 10/11** or **Linux** (Ubuntu 20.04+)
- **NVIDIA RTX GPU** (RTX 2000 series or newer recommended)
- **Visual Studio 2019 or 2022** (Windows only, with C++ workload)
- **Python 3.10+** (included with Kit SDK)
- **Git** for version control

### Installation

1. **Clone the repository:**
   ```powershell
   git clone https://github.com/novigado/sunside.git
   cd sunside
   ```

2. **Build the application:**
   ```powershell
   .\repo.bat build
   ```

3. **Launch City Shadow Analyzer:**
   ```powershell
   .\repo.bat launch -- source/apps/city.shadow_analyzer.kit.kit
   ```

4. **(Optional) Set up Nucleus caching:**
   See [Nucleus Setup Guide](docs/nucleus/SETUP_GUIDE.md) for performance optimization.

---

## Documentation

### For Users
- **[User Guide](docs/guides/USER_GUIDE.md)** - Complete usage documentation
- **[Getting Started](docs/guides/GETTING_STARTED.md)** - Step-by-step tutorial
- **[Features Guide](docs/guides/FEATURES.md)** - Detailed feature documentation
- **[API Guide](docs/guides/API_GUIDE.md)** - REST API reference

### For Developers
- **[Architecture](docs/development/ARCHITECTURE.md)** - System design
- **[Development Guide](docs/development/CONTRIBUTING.md)** - How to contribute
- **[Testing Guide](docs/development/TESTING.md)** - Testing procedures
- **[Phase 2 Summary](docs/development/PHASE2_SUMMARY.md)** - Recent improvements

### Nucleus Integration
- **[Setup Guide](docs/nucleus/SETUP_GUIDE.md)** - Nucleus installation
- **[Integration Details](docs/nucleus/INTEGRATION.md)** - How caching works
- **[Validation Guide](docs/nucleus/VALIDATION.md)** - Testing Nucleus

**[View All Documentation](docs/README.md)**

---

## Usage Example

### Desktop Application

1. **Launch the app** and enter coordinates:
   - San Francisco: `37.7749, -122.4194`
   - New York: `40.7128, -74.0060`
   - London: `51.5074, -0.1278`

2. **Load map data:**
   - Click "Load Map with Terrain & Buildings"
   - First load: 40-70 seconds (queries OpenStreetMap + Open-Elevation)
   - Subsequent loads: 5-10 seconds (loads from Nucleus cache)

3. **Analyze shadows:**
   - Set date and time for solar analysis
   - Click any point in the scene to check if it's in shadow
   - Results show shadow status with sun position and elevation

### REST API

Query shadows without the GUI:

```bash
# Start the main application (API is available automatically)
.\repo.bat launch -- source/apps/city.shadow_analyzer.kit.kit

# Query shadow at location
curl -X POST http://localhost:8000/api/shadow/query \
  -H "Content-Type: application/json" \
  -d '{
    "latitude": 37.7749,
    "longitude": -122.4194,
    "datetime": "2026-06-21T12:00:00Z"
  }'
```

**Response:**
```json
{
  "is_shadowed": false,
  "sun_elevation": 76.4,
  "sun_azimuth": 212.1,
  "query_point": [37.7749, -122.4194, 15.0],
  "timestamp": "2026-06-21T12:00:00Z"
}
```

See [API Guide](docs/guides/API_GUIDE.md) for complete API documentation.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│              City Shadow Analyzer                        │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌───────────────┐  ┌───────────────┐  ┌─────────────┐ │
│  │   UI Layer    │  │  REST API     │  │  CLI Tools  │ │
│  │  (Extension)  │  │  (Service)    │  │             │ │
│  └───────┬───────┘  └───────┬───────┘  └──────┬──────┘ │
│          │                  │                   │        │
│  ┌───────┴──────────────────┴───────────────────┴─────┐ │
│  │          Core Business Logic Layer                  │ │
│  │  • BuildingLoader    • TerrainLoader               │ │
│  │  • ShadowAnalyzer    • SunCalculator               │ │
│  │  • GeometryConverter                                │ │
│  └─────────────────────┬───────────────────────────────┘ │
│                        │                                  │
│  ┌─────────────────────┴───────────────────────────────┐ │
│  │            Data & Caching Layer                      │ │
│  │  • CityCacheManager  • NucleusManager               │ │
│  │  • USD Serialization                                 │ │
│  └─────────────────────┬───────────────────────────────┘ │
│                        │                                  │
│  ┌─────────────────────┴───────────────────────────────┐ │
│  │          External Services & APIs                    │ │
│  │  • OpenStreetMap (Overpass API)                     │ │
│  │  • Open-Elevation API                                │ │
│  │  • Omniverse Nucleus (Caching)                      │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                           │
│  ┌──────────────────────────────────────────────────────┐│
│  │         Foundation: Omniverse Kit SDK + USD          ││
│  │  • GPU Ray Tracing  • Scene Management               ││
│  │  • Python Runtime   • Extension System               ││
│  └──────────────────────────────────────────────────────┘│
└───────────────────────────────────────────────────────────┘
```

See [Architecture Documentation](docs/development/ARCHITECTURE.md) for detailed design.

---

## Testing

```powershell
# Run all tests
cd tests
python -m pytest

# Run specific test suite
python test_api.py
python test_nucleus.py
python test_shadow_api.py
```

See [Testing Guide](docs/development/TESTING.md) for comprehensive testing documentation.

---

## Contributing

We welcome contributions! Please see:

1. **[Contributing Guide](docs/development/CONTRIBUTING.md)** - Development workflow
2. **[Architecture](docs/development/ARCHITECTURE.md)** - System design
3. **[Testing Guide](docs/development/TESTING.md)** - How to test changes

### Development Workflow

```powershell
# Create feature branch
git checkout -b feature/my-new-feature

# Make changes and test
.\repo.bat build
.\repo.bat launch -- source/apps/city.shadow_analyzer.kit.kit

# Run tests
cd tests
python -m pytest

# Commit and push
git add .
git commit -m "feat: Add my new feature"
git push origin feature/my-new-feature
```

---

## Project Structure

```
sunside/
├── docs/                          # Documentation
│   ├── guides/                    # User guides
│   ├── development/               # Developer docs
│   └── nucleus/                   # Nucleus setup
│
├── source/
│   ├── apps/                      # Kit applications
│   │   └── city.shadow_analyzer.kit.kit        # Main application (UI + API)
│   │
│   └── extensions/                # Custom extensions
│       ├── city.shadow_analyzer.api/           # REST API server
│       ├── city.shadow_analyzer.ui/            # UI extension
│       ├── city.shadow_analyzer.buildings/     # Building loader
│       ├── city.shadow_analyzer.sun/           # Sun calculator
│       └── city.shadow_analyzer.nucleus/       # Nucleus caching
│
├── tests/                         # Test suite
│   ├── test_api.py
│   ├── test_nucleus.py
│   └── test_shadow_api.py
│
├── tools/                         # Build tools
├── templates/                     # Project templates
└── README.md                      # This file
```

---

## Learning Resources

### Official Documentation
- **[Omniverse Kit SDK Docs](https://docs.omniverse.nvidia.com/kit/docs/kit-sdk/latest/)**
- **[OpenUSD Documentation](https://openusd.org/)**
- **[Kit App Template Tutorial](https://docs.omniverse.nvidia.com/kit/docs/kit-app-template/latest/)**

### NVIDIA DLI Course
- **[Developing an Omniverse Kit-Based Application](https://learn.nvidia.com/courses/course-detail?course_id=course-v1:DLI+S-OV-11+V1)**

### External APIs
- **[OpenStreetMap Overpass API](https://wiki.openstreetmap.org/wiki/Overpass_API)**
- **[Open-Elevation API](https://open-elevation.com/)**
- **[Omniverse Nucleus](https://docs.omniverse.nvidia.com/nucleus/latest/)**

---

## Performance Benchmarks

Measured on: Windows 11, RTX 4090, 32GB RAM, 1Gbps network to Nucleus

| Operation | First Load | Cached Load | Speedup |
|-----------|-----------|-------------|---------|
| San Francisco Buildings (1,523) | 42s | 3.2s | **13.1x** |
| San Francisco Terrain (400 pts) | 15s | 2.1s | **7.1x** |
| New York Buildings (2,845) | 67s | 4.8s | **14.0x** |
| London Buildings (1,102) | 38s | 2.9s | **13.1x** |

**Average Speedup**: 11.8x faster with Nucleus caching

---

## Known Issues & Limitations

- **OpenStreetMap Rate Limits**: Maximum ~10,000 buildings per query
- **Elevation Data Accuracy**: ±5-10m vertical accuracy from SRTM data
- **Shadow Resolution**: Depends on scene mesh density
- **Nucleus Requirement**: Caching requires Nucleus server access

See [GitHub Issues](https://github.com/novigado/sunside/issues) for current bugs.

---

## License

This project is licensed under the **Apache License 2.0**. See [LICENSE](LICENSE) for details.

Portions of this software are governed by the NVIDIA Omniverse EULA. See [PRODUCT_TERMS_OMNIVERSE](PRODUCT_TERMS_OMNIVERSE) for details.

---

## Acknowledgments

- **NVIDIA Omniverse Team** - Kit SDK and platform
- **OpenStreetMap Contributors** - Building and road data
- **Open-Elevation** - Terrain elevation data
- **OpenUSD Alliance** - Universal Scene Description standard

---

## Contact & Support

- **Issues**: [GitHub Issues](https://github.com/novigado/sunside/issues)
- **Discussions**: [GitHub Discussions](https://github.com/novigado/sunside/discussions)
- **Omniverse Forums**: [NVIDIA Developer Forums](https://forums.developer.nvidia.com/c/omniverse/)

---

## Roadmap

### Phase 3 (Planned)
- [ ] Multi-building analysis (entire city block)
- [ ] Temporal analysis (shadow patterns over time)
- [ ] Solar panel placement optimization
- [ ] 3D heat map visualization
- [ ] WebSocket real-time updates

### Phase 4 (Future)
- [ ] Machine learning shadow prediction
- [ ] Weather data integration
- [ ] Multi-user collaboration via Nucleus
- [ ] Cloud deployment templates

See [GitHub Projects](https://github.com/novigado/sunside/projects) for detailed roadmap.

---

<p align="center">
  Built with NVIDIA Omniverse<br>
  <a href="https://www.nvidia.com/en-us/omniverse/">Learn More About Omniverse</a>
</p>
