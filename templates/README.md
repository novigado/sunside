# Templates Directory 📋

This directory contains NVIDIA Omniverse Kit templates used for creating new applications and extensions.

---

## Purpose

These templates are used by the `repo template new` command to scaffold new projects:

```powershell
# Create a new application from template
.\repo.bat template new

# This will prompt you to choose from available templates
```

---

## Available Templates

### Application Templates (`apps/`)

| Template | Description | Use Case |
|----------|-------------|----------|
| **kit_base_editor** | Basic Kit editor with UI | General-purpose 3D applications |
| **usd_composer** | USD authoring application | 3D content creation |
| **usd_explorer** | USD viewing/review application | 3D content review |
| **usd_viewer** | Lightweight USD viewer | Simple 3D visualization |
| **kit_service** | Headless service application | Background services, APIs |
| **streaming_configs** | Streaming application configs | Cloud/remote rendering |

### Extension Templates (`extensions/`)

| Template | Description | Language |
|----------|-------------|----------|
| **basic_python** | Simple Python extension | Python |
| **python_ui** | Python extension with UI | Python + UI |
| **basic_cpp** | C++ extension | C++ |
| **basic_python_binding** | C++ with Python bindings | C++ + Python |
| **service.setup** | Service setup extension | Python |
| **usd_composer.setup** | USD Composer setup | Python |
| **usd_explorer.setup** | USD Explorer setup | Python |
| **usd_viewer.setup** | USD Viewer setup | Python |
| **usd_viewer.messaging** | USD Viewer messaging | Python |

---

## City Shadow Analyzer Usage

City Shadow Analyzer currently uses **custom-built extensions** (not generated from these templates):

**Custom Extensions:**
- `city.shadow_analyzer.api` - REST API service
- `city.shadow_analyzer.buildings` - Building management
- `city.shadow_analyzer.nucleus` - Nucleus integration
- `city.shadow_analyzer.sun` - Solar calculations
- `city.shadow_analyzer.ui` - User interface

**Why Keep Templates?**
- Useful for adding new features/extensions
- Standard Omniverse development workflow
- No impact on runtime application
- Part of Kit App Template infrastructure

---

## Creating New Extensions

If you want to add a new extension to City Shadow Analyzer:

### 1. Generate from Template
```powershell
# Run template wizard
.\repo.bat template new

# Choose "Basic Python Extension" or "Python UI Extension"
# Name it: city.shadow_analyzer.{feature_name}
```

### 2. Customize the Extension
```
source/extensions/city.shadow_analyzer.{feature_name}/
├── city/shadow_analyzer/{feature_name}/
│   ├── __init__.py
│   └── {your_code}.py
└── config/
    └── extension.toml
```

### 3. Register in Kit File
Add to `source/apps/city.shadow_analyzer.kit.kit`:
```toml
[dependencies]
"city.shadow_analyzer.{feature_name}" = {}
```

---

## Template Configuration

Templates are configured in `templates.toml`. Each template specifies:
- **name**: Human-readable template name
- **subpath**: Location of template files
- **variables**: Customizable parameters (name, version, etc.)
- **type**: Template type (application, extension, setup, etc.)

---

## Maintenance

**DO NOT DELETE** these templates unless:
- You're certain you'll never add new extensions/apps
- You want to break the standard Omniverse workflow
- You're removing the entire Kit App Template infrastructure

**Why?**
- These are part of the standard Omniverse Kit SDK
- Other developers may use them
- They enable rapid development of new features

---

## References

- [Kit App Template Documentation](https://docs.omniverse.nvidia.com/kit/docs/kit-app-template/latest/index.html)
- [Creating Extensions](https://docs.omniverse.nvidia.com/kit/docs/kit-manual/latest/guide/extensions_basic.html)
- [Extension Templates Guide](https://docs.omniverse.nvidia.com/kit/docs/kit-app-template/latest/docs/intro.html)

---

**Last Updated**: January 17, 2026
**Cleanup Branch**: Phase 4 Complete
