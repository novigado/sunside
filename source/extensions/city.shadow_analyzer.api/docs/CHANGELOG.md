# Changelog

## [1.0.0] - 2026-01-13

### Added
- Initial REST API implementation using FastAPI
- Shadow query endpoint (`POST /api/v1/shadow/query`)
- Sun position endpoint (`POST /api/v1/sun/position`)
- Health check endpoint (`GET /health`)
- CORS middleware for cross-origin requests
- OpenAPI/Swagger documentation
- Configurable host and port via Kit settings
