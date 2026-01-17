# Project Cleanup Plan 🧹

**Branch**: `cleanup/documentation-and-unused-code`  
**Date**: January 17, 2026  
**Goal**: Organize documentation, remove unused code, and create clear project structure

---

## Current State Analysis

### Documentation Files (Root Level - 23 files)
Currently scattered across root directory, needs organization:

**User Guides:**
- `CITY_SHADOW_ANALYZER_GUIDE.md` - Main user guide
- `SHADOW_ANALYZER_USAGE_GUIDE.md` - Usage instructions
- `SHADOW_API_USAGE.md` - API usage guide
- `RAY_CASTING_GUIDE.md` - Ray casting feature
- `TERRAIN_ELEVATION_GUIDE.md` - Terrain feature
- `MAP_LOADING_FEEDBACK_IMPROVEMENTS.md` - UI improvements

**Development/Phase Documentation:**
- `PROJECT_SUMMARY.md` - Project overview
- `PHASE1_SUMMARY.md` - Phase 1 completion
- `PHASE2_PLAN.md` - Phase 2 planning
- `PHASE2_STATUS.md` - Phase 2 progress
- `PHASE2_TASK1_COMPLETE.md` - Building cache
- `PHASE2_TASK1B_COMPLETE.md` - Terrain cache
- `PHASE2_TEST_GUIDE.md` - Testing procedures

**Nucleus Documentation:**
- `NUCLEUS_INTEGRATION_PLAN.md` - Integration planning
- `NUCLEUS_PROJECT_LIBRARY.md` - Project library
- `NUCLEUS_TESTING_GUIDE.md` - Testing guide
- `NUCLEUS_VALIDATION_GUIDE.md` - Validation methods
- `NUCLEUS_PORTS.md` - Port configuration
- `DOCKER_NUCLEUS_SETUP.md` - Docker setup
- `START_NUCLEUS_LOCALLY.md` - Local setup
- `UBUNTU_NUCLEUS_SETUP.md` - Ubuntu setup
- `HOW_TO_TEST_NUCLEUS.md` - Testing instructions

**API Documentation:**
- `API_SERVICE_GUIDE.md` - REST API service

### Unused Kit Applications
In `source/apps/`, several template/example apps that are not part of City Shadow Analyzer:

**Keep (Active):**
- ✅ `city.shadow_analyzer.kit.kit` - Main application
- ✅ `city.shadow_analyzer.api.kit` - API version
- ✅ `city.shadow_analyzer.api_service.kit` - API service
- ✅ `shadow_api_service.kit` - Shadow API

**Consider Removing (Unused Templates):**
- ❌ `my.sdg.app.kit` - Template app
- ❌ `my_company.my_editor.kit` - Template editor

### Test Files (Root Level)
- `test_api.py` - API tests
- `test_nucleus.py` - Nucleus tests
- `test_shadow_api.py` - Shadow API tests

---

## Proposed New Structure

```
kit-app-template/
├── README.md (updated with proper overview)
├── CHANGELOG.md
├── LICENSE
├── SECURITY.md
│
├── docs/
│   ├── README.md (documentation index)
│   │
│   ├── guides/
│   │   ├── USER_GUIDE.md (comprehensive user guide)
│   │   ├── GETTING_STARTED.md (quick start)
│   │   ├── FEATURES.md (feature overview)
│   │   │   ├── shadow-analysis.md
│   │   │   ├── terrain-elevation.md
│   │   │   ├── ray-casting.md
│   │   │   └── nucleus-caching.md
│   │   └── API_GUIDE.md (REST API usage)
│   │
│   ├── development/
│   │   ├── PROJECT_SUMMARY.md
│   │   ├── ARCHITECTURE.md (system architecture)
│   │   ├── PHASE1_SUMMARY.md
│   │   ├── PHASE2_SUMMARY.md (consolidate all Phase 2 docs)
│   │   ├── TESTING.md (consolidate test guides)
│   │   └── CONTRIBUTING.md
│   │
│   └── nucleus/
│       ├── SETUP_GUIDE.md (consolidate all setup docs)
│       ├── INTEGRATION.md (integration details)
│       ├── VALIDATION.md (testing & validation)
│       └── DOCKER_SETUP.md (Docker-specific)
│
├── tests/
│   ├── test_api.py
│   ├── test_nucleus.py
│   └── test_shadow_api.py
│
└── source/
    ├── apps/ (only active apps)
    └── extensions/
```

---

## Cleanup Tasks

### Phase 1: Move Documentation ✅

**User Guides → `docs/guides/`:**
- [ ] Create consolidated `USER_GUIDE.md` from:
  - CITY_SHADOW_ANALYZER_GUIDE.md
  - SHADOW_ANALYZER_USAGE_GUIDE.md
  - SHADOW_API_USAGE.md
- [ ] Create `FEATURES.md` directory with:
  - shadow-analysis.md (from RAY_CASTING_GUIDE.md)
  - terrain-elevation.md (from TERRAIN_ELEVATION_GUIDE.md)
  - nucleus-caching.md (from Phase 2 docs)
- [ ] Move `API_SERVICE_GUIDE.md` → `docs/guides/API_GUIDE.md`

**Development Docs → `docs/development/`:**
- [ ] Keep PROJECT_SUMMARY.md
- [ ] Keep PHASE1_SUMMARY.md
- [ ] Create `PHASE2_SUMMARY.md` consolidating:
  - PHASE2_PLAN.md
  - PHASE2_STATUS.md
  - PHASE2_TASK1_COMPLETE.md
  - PHASE2_TASK1B_COMPLETE.md
  - PHASE2_TEST_GUIDE.md
- [ ] Create `TESTING.md` for all test procedures
- [ ] Create `ARCHITECTURE.md` with system design

**Nucleus Docs → `docs/nucleus/`:**
- [ ] Create `SETUP_GUIDE.md` consolidating:
  - START_NUCLEUS_LOCALLY.md
  - DOCKER_NUCLEUS_SETUP.md
  - UBUNTU_NUCLEUS_SETUP.md
- [ ] Move NUCLEUS_INTEGRATION_PLAN.md → `INTEGRATION.md`
- [ ] Create `VALIDATION.md` consolidating:
  - NUCLEUS_TESTING_GUIDE.md
  - NUCLEUS_VALIDATION_GUIDE.md
  - HOW_TO_TEST_NUCLEUS.md
- [ ] Keep NUCLEUS_PROJECT_LIBRARY.md
- [ ] Keep NUCLEUS_PORTS.md

### Phase 2: Remove Unused Code 🗑️

**Remove Template Apps:**
- [ ] Delete `source/apps/my.sdg.app.kit`
- [ ] Delete `source/apps/my_company.my_editor.kit`
- [ ] Check for any related template extensions

**Move Test Files:**
- [ ] Create `tests/` directory
- [ ] Move `test_api.py` → `tests/`
- [ ] Move `test_nucleus.py` → `tests/`
- [ ] Move `test_shadow_api.py` → `tests/`
- [ ] Create `tests/README.md` with test instructions

### Phase 3: Create Master Documentation 📚

**Root README.md:**
- [ ] Update with project overview
- [ ] Add architecture diagram
- [ ] Link to documentation structure
- [ ] Add quick start section
- [ ] Add features list with screenshots

**docs/README.md:**
- [ ] Create documentation index
- [ ] Link to all major guides
- [ ] Add navigation structure

**CHANGELOG.md:**
- [ ] Update with recent changes
- [ ] Document Phase 2 completion
- [ ] Add caching feature notes

### Phase 4: Template Cleanup 🧩

**Check Templates Directory:**
- [ ] Review `templates/` for unused templates
- [ ] Keep only templates used by City Shadow Analyzer
- [ ] Document what each template is for

### Phase 5: Final Cleanup 🎯

- [ ] Remove deprecated documentation files
- [ ] Update all cross-references in docs
- [ ] Ensure all links work
- [ ] Add `.gitignore` entries for build artifacts
- [ ] Create migration guide for old doc locations

---

## Success Criteria

After cleanup, the project should have:

- ✅ **Clear Documentation Structure**: Easy to navigate docs/ folder
- ✅ **No Duplicate Documentation**: Single source of truth for each topic
- ✅ **No Unused Code**: Only active applications remain
- ✅ **Organized Tests**: All tests in tests/ directory
- ✅ **Updated README**: Professional, comprehensive overview
- ✅ **Easy Onboarding**: New users can find what they need quickly

---

## Migration Notes

For users with bookmarks to old documentation locations:

```
Old Location → New Location
─────────────────────────────────────────────────────────────
CITY_SHADOW_ANALYZER_GUIDE.md → docs/guides/USER_GUIDE.md
PHASE2_*.md → docs/development/PHASE2_SUMMARY.md
NUCLEUS_INTEGRATION_PLAN.md → docs/nucleus/INTEGRATION.md
START_NUCLEUS_LOCALLY.md → docs/nucleus/SETUP_GUIDE.md
test_*.py → tests/test_*.py
```

---

## Timeline

- **Phase 1** (Documentation Move): 1-2 hours
- **Phase 2** (Remove Unused): 30 minutes
- **Phase 3** (Master Docs): 1 hour
- **Phase 4** (Template Cleanup): 30 minutes
- **Phase 5** (Final Cleanup): 30 minutes

**Total Estimated Time**: 3.5-4.5 hours

---

**Status**: 📋 Planning Complete - Ready to Execute
