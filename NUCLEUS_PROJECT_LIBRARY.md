# Nucleus Project Library Feature

## Executive Summary

Transform the City Shadow Analyzer into a **collaborative urban planning tool** by integrating NVIDIA Omniverse Nucleus for persistent storage, shared city models, and team collaboration.

## The Problem

### Current Limitations:
1. **Redundant Data Fetching**: Every user must fetch building data from OpenStreetMap APIs, causing:
   - Slow initial load times (10-30 seconds per city area)
   - Rate limit issues with repeated queries
   - Network dependency for every session
   
2. **No Persistence**: Analysis results disappear when app closes:
   - Cannot review previous analyses
   - Cannot compare multiple scenarios
   - Lost institutional knowledge
   
3. **No Collaboration**: Isolated work environment:
   - Teams can't share city models
   - No way to review colleague's shadow studies
   - Duplicate effort across organization
   
4. **No Version Control**: Cannot track design iterations:
   - "What did the shadow look like last week?"
   - "Which design alternative cast less shadow?"
   - No audit trail for regulatory compliance

## The Solution: Nucleus-Backed Project Library

### Core Features:

#### 1. **Shared City Model Cache**
Store OpenStreetMap building geometry on Nucleus server:
- **Path Structure**: `omniverse://nucleus-server/CityLibrary/{region}/{city}/buildings.usd`
- **Metadata**: Bounds, building count, terrain data, last updated
- **Smart Loading**: Check Nucleus before fetching from OSM
- **Benefits**: 
  - ✅ 10x faster loading (local read vs API call)
  - ✅ Works offline (once cached)
  - ✅ No API rate limits
  - ✅ Shared across team

#### 2. **Project-Based Analysis Storage**
Organize work into projects with persistent results:
- **Path Structure**: `omniverse://nucleus-server/Projects/{project_name}/`
  - `city_model.usd` - The base city geometry
  - `scenarios/current.usd` - Current state analysis
  - `scenarios/proposed_tower.usd` - With new building
  - `scenarios/alternative_design.usd` - Different design
  - `results/shadow_analysis_2026-01-14.usd` - Timestamped results
- **Benefits**:
  - ✅ Compare multiple design scenarios
  - ✅ Review analysis history
  - ✅ Share with stakeholders via Nucleus URL

#### 3. **Collaborative Workflows**
Enable team collaboration on urban planning:
- **Live Updates**: See when colleagues update analyses
- **Comments**: Annotate USD with notes and concerns
- **Version History**: Track who changed what and when
- **Access Control**: Read-only for reviewers, edit for planners
- **Benefits**:
  - ✅ Real-time collaboration
  - ✅ Institutional knowledge preservation
  - ✅ Regulatory compliance (audit trail)

#### 4. **Project Browser UI**
New UI panel for managing Nucleus projects:
- Browse existing projects on Nucleus
- Create new projects with metadata
- Load city models from library
- Compare scenario results side-by-side
- Export reports/visualizations

## Technical Architecture

### New Extension: `city.shadow_analyzer.nucleus`

```
city.shadow_analyzer.nucleus/
├── city/
│   └── shadow_analyzer/
│       └── nucleus/
│           ├── __init__.py
│           ├── nucleus_client.py       # Omni.client wrapper
│           ├── city_cache.py          # City model caching
│           ├── project_manager.py     # Project CRUD operations
│           ├── scenario_manager.py    # Scenario comparisons
│           └── result_persistence.py  # Save/load analysis results
└── extension.toml
```

### Key Classes:

#### `NucleusClient`
Wrapper around `omni.client` for Shadow Analyzer:
```python
class NucleusClient:
    def connect(self, server_url: str) -> bool
    def list_projects(self) -> List[ProjectMetadata]
    def create_project(self, name: str, description: str) -> str
    def save_usd(self, path: str, stage: Usd.Stage) -> bool
    def load_usd(self, path: str) -> Usd.Stage
    def check_exists(self, path: str) -> bool
```

#### `CityCacheManager`
Manages shared city model library:
```python
class CityCacheManager:
    def get_cached_city(self, lat: float, lon: float, radius: float) -> Optional[Usd.Stage]
    def cache_city_model(self, lat: float, lon: float, buildings: List[Dict], terrain: np.array) -> str
    def is_city_cached(self, lat: float, lon: float, radius: float) -> bool
    def get_cache_metadata(self, cache_path: str) -> Dict
```

#### `ProjectManager`
Organizes shadow analysis projects:
```python
class ProjectManager:
    def create_project(self, name: str, city_model_path: str) -> str
    def list_scenarios(self, project_path: str) -> List[str]
    def create_scenario(self, project_path: str, name: str, description: str) -> str
    def save_analysis_result(self, scenario_path: str, result: ShadowAnalysisResult) -> str
    def load_scenario(self, scenario_path: str) -> Usd.Stage
```

### Updated UI Extension

New "Projects" panel in `city.shadow_analyzer.ui`:
- **Connect to Nucleus**: Server URL input and connection status
- **Project Browser**: TreeView of projects and scenarios
- **Create Project**: Dialog for new project metadata
- **Load from Cache**: Button to load cached city models
- **Save Scenario**: Save current analysis as named scenario
- **Compare**: Side-by-side scenario comparison

## Implementation Plan

### Phase 1: Core Nucleus Integration (Priority: HIGH)
**Goal**: Basic read/write to Nucleus

**Tasks**:
1. ✅ Create feature branch
2. ⬜ Create `city.shadow_analyzer.nucleus` extension skeleton
3. ⬜ Implement `NucleusClient` wrapper around `omni.client`
4. ⬜ Add Nucleus connection UI (server URL input)
5. ⬜ Test basic USD save/load to Nucleus
6. ⬜ Add error handling and connection status

**Deliverable**: Can connect to Nucleus and save/load USD files

**Estimated Time**: 2-3 days

### Phase 2: City Model Caching (Priority: HIGH)
**Goal**: Cache OpenStreetMap data on Nucleus

**Tasks**:
1. ⬜ Implement `CityCacheManager`
2. ⬜ Add cache key generation (lat/lon/radius → unique path)
3. ⬜ Modify building loader to check cache first
4. ⬜ Add "Save to Nucleus Library" button
5. ⬜ Add cache metadata (bounds, timestamp, stats)
6. ⬜ Test with multiple city areas

**Deliverable**: First load fetches OSM, subsequent loads use Nucleus cache

**Estimated Time**: 3-4 days

### Phase 3: Project Management (Priority: MEDIUM)
**Goal**: Organize analyses into projects

**Tasks**:
1. ⬜ Implement `ProjectManager`
2. ⬜ Add project browser UI panel
3. ⬜ Create project wizard (name, description, city selection)
4. ⬜ Implement scenario creation
5. ⬜ Save analysis results to project
6. ⬜ Test multi-scenario workflows

**Deliverable**: Can create projects and save multiple scenarios

**Estimated Time**: 4-5 days

### Phase 4: Analysis Result Persistence (Priority: MEDIUM)
**Goal**: Save shadow query results persistently

**Tasks**:
1. ⬜ Design result USD schema (shadow points, colors, timestamps)
2. ⬜ Implement result serialization
3. ⬜ Add "Save Analysis" button
4. ⬜ Add result viewer (load previous analyses)
5. ⬜ Add time-series analysis support (full day pattern)
6. ⬜ Test with large datasets

**Deliverable**: Can save and reload shadow analysis results

**Estimated Time**: 3-4 days

### Phase 5: Scenario Comparison (Priority: LOW)
**Goal**: Compare multiple design scenarios

**Tasks**:
1. ⬜ Add scenario comparison UI
2. ⬜ Implement side-by-side viewport
3. ⬜ Add difference visualization (more/less shadow)
4. ⬜ Generate comparison reports
5. ⬜ Test with real urban planning use case

**Deliverable**: Can compare shadow impact of different designs

**Estimated Time**: 3-4 days

### Phase 6: Collaboration Features (Priority: LOW)
**Goal**: Enable team workflows

**Tasks**:
1. ⬜ Add live update notifications
2. ⬜ Implement comment system
3. ⬜ Add user attribution (who created what)
4. ⬜ Test multi-user scenarios
5. ⬜ Add access control (if needed)

**Deliverable**: Teams can collaborate on shared projects

**Estimated Time**: 4-5 days

## User Stories

### Story 1: Urban Planner - Faster Workflow
**As an** urban planner  
**I want** to quickly load building data for cities I frequently analyze  
**So that** I don't waste time waiting for API calls

**Acceptance Criteria**:
- First load: Fetches from OSM and caches to Nucleus (30 seconds)
- Subsequent loads: Reads from Nucleus cache (3 seconds)
- Cache invalidation option available

### Story 2: Architecture Team - Scenario Comparison
**As an** architecture team lead  
**I want** to compare shadow impact of 3 different building designs  
**So that** we can choose the design with minimal shadow impact

**Acceptance Criteria**:
- Can create 3 scenarios in same project
- Can load each scenario and run shadow analysis
- Can view side-by-side comparison
- Can export comparison report

### Story 3: Developer - Regulatory Compliance
**As a** real estate developer  
**I want** to save shadow analysis results with timestamps  
**So that** I can prove compliance with city regulations

**Acceptance Criteria**:
- Each analysis has timestamp and metadata
- Results are stored permanently on Nucleus
- Can export analysis with audit trail
- Version history shows who made changes

### Story 4: Consultant - Knowledge Sharing
**As a** shadow analysis consultant  
**I want** to share my analysis results with clients  
**So that** they can review findings in USD Composer

**Acceptance Criteria**:
- Can generate shareable Nucleus URL
- Client can open URL in USD Composer
- Client sees annotated 3D model with shadow patterns
- Comments are visible in USD

## Benefits Summary

### Performance Benefits:
- **10x faster loading** for cached cities (3s vs 30s)
- **Zero API rate limits** once data is cached
- **Offline capability** when using cached data

### Collaboration Benefits:
- **Shared city models** across team
- **Project organization** with scenarios
- **Version history** and audit trails
- **Stakeholder reviews** via Nucleus URLs

### Business Benefits:
- **Institutional knowledge** preserved
- **Regulatory compliance** documentation
- **Client deliverables** (shareable 3D results)
- **Competitive advantage** (collaborative workflow)

## Technical Requirements

### Dependencies:
- `omni.client` - Nucleus client library (already in Kit)
- `omni.usd` - USD manipulation (already available)
- Nucleus server - Local or cloud instance

### Nucleus Server Setup:
For development:
```bash
# Option 1: Use Omniverse Nucleus Local (recommended for dev)
- Download from Omniverse Launcher
- Default: localhost:3009

# Option 2: Use Omniverse Cloud Nucleus
- Requires Omniverse account
- URL: omniverse://ov-prod.us-west-2.aws.net/
```

### File Structure on Nucleus:
```
omniverse://nucleus-server/
├── CityLibrary/                    # Shared city model cache
│   ├── north_america/
│   │   ├── new_york/
│   │   │   ├── manhattan_midtown.usd
│   │   │   └── manhattan_midtown.meta.json
│   │   └── san_francisco/
│   │       ├── downtown.usd
│   │       └── downtown.meta.json
│   └── europe/
│       └── london/
│           └── city_center.usd
│
└── Projects/                       # User projects
    ├── hudson_yards_study/
    │   ├── project.meta.json
    │   ├── city_model.usd
    │   └── scenarios/
    │       ├── current_state.usd
    │       ├── proposed_tower.usd
    │       └── alternative_design.usd
    │
    └── embarcadero_development/
        ├── project.meta.json
        └── scenarios/
            └── baseline.usd
```

## Testing Strategy

### Unit Tests:
- `NucleusClient` connection and CRUD operations
- `CityCacheManager` cache key generation and retrieval
- `ProjectManager` project/scenario creation
- USD serialization/deserialization

### Integration Tests:
- End-to-end city caching workflow
- Multi-scenario project workflow
- Concurrent access (multiple users)

### Performance Tests:
- Cache hit vs miss performance
- Large dataset handling (10,000+ buildings)
- Nucleus bandwidth usage

### User Acceptance Tests:
- Urban planner workflow (cache usage)
- Architecture team workflow (scenario comparison)
- Developer workflow (compliance documentation)

## Future Enhancements

### Phase 7+:
1. **Web Interface**: Browse and query projects via web browser
2. **Mobile App**: Field shadow queries from mobile devices
3. **AI Integration**: ML-based shadow optimization suggestions
4. **GIS Integration**: QGIS/ArcGIS connector plugins
5. **Real-time Collaboration**: Multiple users editing simultaneously
6. **Cloud Rendering**: Omniverse Farm for batch analysis
7. **Analytics Dashboard**: Usage metrics and insights

## Risk Assessment

### Technical Risks:
- **Nucleus availability**: Mitigation: Fallback to local storage
- **Network latency**: Mitigation: Aggressive local caching
- **USD versioning**: Mitigation: Schema versioning system

### User Adoption Risks:
- **Learning curve**: Mitigation: Tutorial videos and docs
- **Migration effort**: Mitigation: Import existing work
- **Server setup**: Mitigation: Simplified setup guide

## Success Metrics

### Key Performance Indicators:
1. **Load Time**: Average city load time < 5 seconds (cached)
2. **Cache Hit Rate**: > 70% of loads use cache
3. **User Adoption**: > 50% of users create projects
4. **Collaboration**: > 30% of projects shared with team
5. **Storage Usage**: Average project size < 500 MB

### Measurement Plan:
- Add telemetry for cache hits/misses
- Track project creation frequency
- Monitor Nucleus storage usage
- User surveys for satisfaction

---

**Document Version**: 1.0  
**Created**: January 14, 2026  
**Author**: GitHub Copilot  
**Status**: 🔨 In Development
