"""
FastAPI server for shadow analysis queries.

Provides REST endpoints for:
- Shadow detection at GPS coordinates
- Sun position calculations
- Health checks
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import uvicorn
import carb
import threading

# Import shadow analyzer components
from city.shadow_analyzer.sun.sun_calculator import SunCalculator
from city.shadow_analyzer.buildings.building_loader import BuildingLoader
from city.shadow_analyzer.buildings.shadow_analyzer import ShadowAnalyzer
from city.shadow_analyzer.buildings.geometry_converter import BuildingGeometryConverter


# Request/Response Models
class ShadowQueryRequest(BaseModel):
    """Request model for shadow query."""
    latitude: float = Field(..., ge=-90, le=90, description="Latitude in degrees")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude in degrees")
    timestamp: Optional[str] = Field(None, description="ISO 8601 timestamp (UTC). If not provided, uses current time.")
    search_radius: Optional[int] = Field(500, ge=100, le=2000, description="Radius in meters to search for buildings")


class ShadowQueryResponse(BaseModel):
    """Response model for shadow query."""
    is_shadowed: bool = Field(..., description="Whether the location is in shadow")
    sun_azimuth: float = Field(..., description="Sun azimuth angle in degrees (0=North, 90=East, 180=South, 270=West)")
    sun_elevation: float = Field(..., description="Sun elevation angle in degrees (90=overhead, negative=below horizon)")
    blocking_object: Optional[str] = Field(None, description="Path to the object casting the shadow, if any")
    latitude: float = Field(..., description="Query latitude")
    longitude: float = Field(..., description="Query longitude")
    timestamp: str = Field(..., description="Query timestamp (ISO 8601 UTC)")
    message: Optional[str] = Field(None, description="Additional information or warnings")


class SunPositionRequest(BaseModel):
    """Request model for sun position."""
    latitude: float = Field(..., ge=-90, le=90, description="Latitude in degrees")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude in degrees")
    timestamp: Optional[str] = Field(None, description="ISO 8601 timestamp (UTC). If not provided, uses current time.")


class SunPositionResponse(BaseModel):
    """Response model for sun position."""
    azimuth: float = Field(..., description="Sun azimuth angle in degrees")
    elevation: float = Field(..., description="Sun elevation angle in degrees")
    distance: float = Field(..., description="Distance to sun in AU")
    latitude: float = Field(..., description="Query latitude")
    longitude: float = Field(..., description="Query longitude")
    timestamp: str = Field(..., description="Query timestamp (ISO 8601 UTC)")


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    timestamp: str = Field(..., description="Current server time (ISO 8601 UTC)")


class ShadowAnalyzerAPI:
    """FastAPI server for shadow analysis."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8000):
        """Initialize the API server."""
        self.host = host
        self.port = port
        self.app = FastAPI(
            title="City Shadow Analyzer API",
            description="REST API for real-time shadow analysis using OpenStreetMap data",
            version="1.0.0",
            docs_url="/docs",
            redoc_url="/redoc"
        )
        
        # Add CORS middleware for smartphone/web access
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # In production, specify exact origins
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Initialize components
        self.building_loader = BuildingLoader()
        self.geometry_converter = BuildingGeometryConverter()
        self.shadow_analyzer = None  # Will be initialized per-request with scene data
        
        # Setup routes
        self._setup_routes()
        
        # Server control
        self._server = None
        self._shutdown_event = threading.Event()

    def _setup_routes(self):
        """Setup API routes."""
        
        @self.app.get("/", response_model=Dict[str, str])
        async def root():
            """Root endpoint with API information."""
            return {
                "service": "City Shadow Analyzer API",
                "version": "1.0.0",
                "docs": f"http://{self.host}:{self.port}/docs",
                "status": "running"
            }
        
        @self.app.get("/health", response_model=HealthResponse)
        async def health_check():
            """Health check endpoint."""
            return HealthResponse(
                status="healthy",
                version="1.0.0",
                timestamp=datetime.now(timezone.utc).isoformat()
            )
        
        @self.app.post("/api/v1/sun/position", response_model=SunPositionResponse)
        async def get_sun_position(request: SunPositionRequest):
            """
            Calculate sun position for given location and time.
            
            Returns azimuth and elevation angles of the sun.
            """
            try:
                # Parse timestamp
                if request.timestamp:
                    dt = datetime.fromisoformat(request.timestamp.replace('Z', '+00:00'))
                else:
                    dt = datetime.now(timezone.utc)
                
                # Calculate sun position
                azimuth, elevation, distance = SunCalculator.calculate_sun_position(
                    request.latitude,
                    request.longitude,
                    dt
                )
                
                return SunPositionResponse(
                    azimuth=azimuth,
                    elevation=elevation,
                    distance=distance,
                    latitude=request.latitude,
                    longitude=request.longitude,
                    timestamp=dt.isoformat()
                )
            except Exception as e:
                carb.log_error(f"[ShadowAnalyzerAPI] Error calculating sun position: {e}")
                raise HTTPException(status_code=500, detail=f"Error calculating sun position: {str(e)}")
        
        @self.app.post("/api/v1/shadow/query", response_model=ShadowQueryResponse)
        async def query_shadow(request: ShadowQueryRequest):
            """
            Query whether a GPS location is in shadow at a given time.
            
            This endpoint:
            1. Loads building data from OpenStreetMap around the location
            2. Calculates sun position for the given time
            3. Performs ray-casting to detect shadows
            4. Returns shadow status and sun position
            """
            try:
                # Parse timestamp
                if request.timestamp:
                    dt = datetime.fromisoformat(request.timestamp.replace('Z', '+00:00'))
                else:
                    dt = datetime.now(timezone.utc)
                
                carb.log_info(f"[ShadowAnalyzerAPI] Shadow query: lat={request.latitude}, lon={request.longitude}, time={dt}")
                
                # Calculate sun position
                azimuth, elevation, distance = SunCalculator.calculate_sun_position(
                    request.latitude,
                    request.longitude,
                    dt
                )
                
                # Check if sun is below horizon
                if elevation < 0:
                    return ShadowQueryResponse(
                        is_shadowed=True,
                        sun_azimuth=azimuth,
                        sun_elevation=elevation,
                        blocking_object=None,
                        latitude=request.latitude,
                        longitude=request.longitude,
                        timestamp=dt.isoformat(),
                        message="Sun is below horizon (nighttime)"
                    )
                
                # Load building data from OpenStreetMap
                try:
                    scene_data = self.building_loader.load_scene_data(
                        request.latitude,
                        request.longitude,
                        request.search_radius
                    )
                    buildings = scene_data.get('buildings', [])
                    
                    if not buildings:
                        return ShadowQueryResponse(
                            is_shadowed=False,
                            sun_azimuth=azimuth,
                            sun_elevation=elevation,
                            blocking_object=None,
                            latitude=request.latitude,
                            longitude=request.longitude,
                            timestamp=dt.isoformat(),
                            message="No buildings found in area"
                        )
                    
                    carb.log_info(f"[ShadowAnalyzerAPI] Loaded {len(buildings)} buildings")
                    
                except Exception as e:
                    carb.log_error(f"[ShadowAnalyzerAPI] Error loading buildings: {e}")
                    return ShadowQueryResponse(
                        is_shadowed=False,
                        sun_azimuth=azimuth,
                        sun_elevation=elevation,
                        blocking_object=None,
                        latitude=request.latitude,
                        longitude=request.longitude,
                        timestamp=dt.isoformat(),
                        message=f"Could not load building data: {str(e)}"
                    )
                
                # Convert GPS to scene coordinates
                query_x, query_z = self.geometry_converter.gps_to_scene_coords(
                    request.latitude,
                    request.longitude
                )
                query_point = (query_x, 1.5, query_z)  # 1.5m height (person height)
                
                # Get sun direction vector
                sun_direction = SunCalculator.get_sun_direction_vector(azimuth, elevation)
                
                # Create shadow analyzer with building data
                shadow_analyzer = ShadowAnalyzer(buildings, self.geometry_converter)
                
                # Perform shadow detection
                is_shadowed, blocking_object = shadow_analyzer.is_point_in_shadow(
                    query_point,
                    sun_direction
                )
                
                return ShadowQueryResponse(
                    is_shadowed=is_shadowed,
                    sun_azimuth=azimuth,
                    sun_elevation=elevation,
                    blocking_object=blocking_object,
                    latitude=request.latitude,
                    longitude=request.longitude,
                    timestamp=dt.isoformat(),
                    message=None
                )
                
            except Exception as e:
                carb.log_error(f"[ShadowAnalyzerAPI] Error processing shadow query: {e}")
                raise HTTPException(status_code=500, detail=f"Error processing shadow query: {str(e)}")

    def run(self):
        """Run the API server."""
        carb.log_info(f"[ShadowAnalyzerAPI] Starting server on {self.host}:{self.port}")
        
        config = uvicorn.Config(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info",
            access_log=True
        )
        self._server = uvicorn.Server(config)
        self._server.run()

    def shutdown(self):
        """Shutdown the API server."""
        if self._server:
            carb.log_info("[ShadowAnalyzerAPI] Shutting down server")
            self._server.should_exit = True
