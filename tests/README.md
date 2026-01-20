# City Shadow Analyzer Tests 

This directory contains test suites for the City Shadow Analyzer application.

---

## Test Files

### `test_api.py`
Tests for the REST API endpoints and service functionality.

**Coverage:**
- Shadow query API endpoints
- Building data loading via API
- Terrain elevation API
- Error handling and validation
- Authentication (if enabled)

**Run:**
```powershell
python tests/test_api.py
```

### `test_nucleus.py`
Tests for Nucleus server integration and caching.

**Coverage:**
- Nucleus connection and authentication
- Building cache save/load operations
- Terrain cache save/load operations
- Metadata handling
- Cache key generation
- USD serialization/deserialization

**Run:**
```powershell
python tests/test_nucleus.py
```

### `test_shadow_api.py`
Tests for shadow analysis algorithms and calculations.

**Coverage:**
- Sun position calculations
- Ray casting operations
- Shadow detection logic
- Coordinate transformations
- Time zone handling

**Run:**
```powershell
python tests/test_shadow_api.py
```

---

## Running Tests

### Run All Tests
```powershell
# Using pytest (recommended)
cd tests
python -m pytest

# Or run individually
python test_api.py
python test_nucleus.py
python test_shadow_api.py
```

### Run Specific Test Suite
```powershell
python -m pytest tests/test_api.py -v
python -m pytest tests/test_nucleus.py -v
python -m pytest tests/test_shadow_api.py -v
```

### Run with Coverage
```powershell
python -m pytest --cov=city.shadow_analyzer --cov-report=html
```

---

## Test Requirements

### Prerequisites
- Python 3.10+
- Omniverse Kit SDK installed
- Required Python packages (see below)

### Install Test Dependencies
```powershell
pip install pytest pytest-asyncio pytest-cov requests
```

### Environment Setup

**For API Tests:**
```powershell
# Start the API service first
.\repo.bat launch -- source/apps/city.shadow_analyzer.api_service.kit

# Then run tests (in another terminal)
python tests/test_api.py
```

**For Nucleus Tests:**
Ensure Nucleus server is accessible and credentials are configured:
```powershell
# Set environment variables (optional)
$env:NUCLEUS_SERVER = "nucleus.swedencentral.cloudapp.azure.com"
$env:NUCLEUS_USERNAME = "omniverse"
$env:NUCLEUS_PASSWORD = "YourPassword"

# Run tests
python tests/test_nucleus.py
```

---

## Test Configuration

### API Service Configuration
- Default host: `localhost`
- Default port: `8000`
- Configure in: `source/apps/city.shadow_analyzer.api_service.kit`

### Nucleus Configuration
- Server: `nucleus.swedencentral.cloudapp.azure.com`
- Cache path: `/Projects/CityData/`
- Configure in: Extension settings

---

## Writing New Tests

### Test Structure
```python
import pytest

class TestFeatureName:
    """Test suite for Feature Name."""

    def setup_method(self):
        """Setup before each test."""
        pass

    def teardown_method(self):
        """Cleanup after each test."""
        pass

    def test_something(self):
        """Test description."""
        # Arrange
        input_data = ...

        # Act
        result = function_to_test(input_data)

        # Assert
        assert result == expected_value
```

### Best Practices
1. **Use descriptive test names**: `test_shadow_query_returns_correct_result`
2. **Test one thing per test**: Keep tests focused
3. **Use fixtures**: Share setup code with pytest fixtures
4. **Mock external services**: Don't rely on live APIs in unit tests
5. **Test edge cases**: Empty inputs, invalid data, boundary conditions
6. **Document test intent**: Clear docstrings explaining what's tested

---

## Continuous Integration

### GitHub Actions (Example)
```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: pip install pytest pytest-cov
      - run: python -m pytest tests/
```

---

## Troubleshooting

### Common Issues

**Import Errors:**
```
ModuleNotFoundError: No module named 'city.shadow_analyzer'
```
**Solution:** Ensure extensions are built and Kit SDK is properly installed.

**API Connection Errors:**
```
ConnectionRefusedError: [Errno 61] Connection refused
```
**Solution:** Start the API service before running API tests.

**Nucleus Authentication Errors:**
```
NucleusManager: Authentication failed
```
**Solution:** Check credentials in extension settings or environment variables.

---

## Test Coverage Goals

| Module | Target Coverage | Current |
|--------|----------------|---------|
| API Endpoints | 90%+ | TBD |
| Nucleus Cache | 85%+ | TBD |
| Shadow Analysis | 95%+ | TBD |
| Building Loader | 80%+ | TBD |
| Terrain Loader | 80%+ | TBD |

---

## Contributing

When adding new features, please include tests:
1. Create test file in `tests/`
2. Follow naming convention: `test_<feature>.py`
3. Aim for 80%+ code coverage
4. Update this README if needed

See [Contributing Guide](../docs/development/CONTRIBUTING.md) for more details.

---

**Last Updated**: January 17, 2026
**Maintainer**: City Shadow Analyzer Team
