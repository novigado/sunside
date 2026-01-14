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
import queue
import time
import asyncio
import omni.usd
from pxr import Gf
import omni.usd
import omni.kit.app
from pxr import Gf

# Import shadow analyzer components
from city.shadow_analyzer.sun.sun_calculator import SunCalculator
from city.shadow_analyzer.buildings.shadow_analyzer import ShadowAnalyzer
from city.shadow_analyzer.buildings.geometry_converter import BuildingGeometryConverter


# Request/Response Models
class ShadowQueryRequest(BaseModel):
    """Request model for shadow query."""
    latitude: float = Field(..., ge=-90, le=90, description="Latitude in degrees")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude in degrees")
    timestamp: Optional[str] = Field(None, description="ISO 8601 timestamp (UTC). If not provided, uses current time.")
    search_radius: Optional[int] = Field(100, ge=100, le=2000, description="Radius in meters to search for buildings")


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
        self.sun_calculator = SunCalculator()
        self.geometry_converter = None  # Initialized on first use
        self.shadow_analyzer = None  # Initialized on first use

        # Queue for main-thread USD operations
        self.request_queue = queue.Queue()
        self.result_map = {}  # Maps request_id -> (is_shadowed, blocking_object, error_msg)
        self.next_request_id = 0
        self.request_lock = threading.Lock()

        # Setup routes
        self._setup_routes()

        # Server control
        self._server = None
        self._shutdown_event = threading.Event()

    def process_main_thread_queue(self):
        """
        Process queued shadow detection requests on the main thread.
        This is called from the extension's update loop.
        """
        try:
            # Check if there are items in queue
            queue_size = self.request_queue.qsize()
            if queue_size > 0:
                print(f"[ShadowAnalyzerAPI] Processing {queue_size} items from queue on main thread")
                carb.log_info(f"[ShadowAnalyzerAPI] Processing {queue_size} items from queue on main thread")

            while not self.request_queue.empty():
                try:
                    task = self.request_queue.get_nowait()
                    request_id, latitude, longitude, azimuth, elevation = task
                    print(f"[ShadowAnalyzerAPI] Processing request {request_id} on main thread")
                    carb.log_info(f"[ShadowAnalyzerAPI] Processing request {request_id} on main thread")

                    carb.log_info(f"[ShadowAnalyzerAPI] Processing request {request_id} on main thread")

                    # Perform shadow check on main thread
                    self._perform_shadow_check(request_id, latitude, longitude, azimuth, elevation)

                except queue.Empty:
                    break
                except Exception as e:
                    carb.log_error(f"[ShadowAnalyzerAPI] Error processing queue item: {e}")
                    import traceback
                    carb.log_error(f"[ShadowAnalyzerAPI] Traceback: {traceback.format_exc()}")
        except Exception as e:
            carb.log_error(f"[ShadowAnalyzerAPI] Error in process_main_thread_queue: {e}")

    def _perform_shadow_check(self, request_id: int, latitude: float, longitude: float,
                              azimuth: float, elevation: float):
        """
        Perform shadow check using USD ray casting. Runs on main thread.
        """
        try:
            # Get stage (safe on main thread)
            stage = omni.usd.get_context().get_stage()
            if not stage:
                self.result_map[request_id] = (False, None, "USD stage not available")
                return

            # Initialize geometry converter if needed
            if self.geometry_converter is None:
                self.geometry_converter = BuildingGeometryConverter(stage)
                print("[ShadowAnalyzerAPI] Initialized BuildingGeometryConverter")
                carb.log_info("[ShadowAnalyzerAPI] Initialized BuildingGeometryConverter")

            # Try to load reference point from existing buildings
            print("[ShadowAnalyzerAPI] Attempting to load reference point from scene...")
            if not self.geometry_converter.load_reference_point_from_scene():
                print("[ShadowAnalyzerAPI] load_reference_point_from_scene returned False")
                self.result_map[request_id] = (False, None, "No buildings loaded. Use the 'Import Map' button in the UI to load buildings first.")
                return

            print("[ShadowAnalyzerAPI] Reference point loaded successfully!")

            # Convert GPS to scene coordinates
            query_x, query_z = self.geometry_converter.gps_to_scene_coords(latitude, longitude)
            query_point = Gf.Vec3f(query_x, 1.5, query_z)  # 1.5m height (person standing)

            # Get sun direction vector
            sun_dir_tuple = self.sun_calculator.get_sun_direction_vector(azimuth, elevation)
            sun_direction = Gf.Vec3f(sun_dir_tuple[0], sun_dir_tuple[1], sun_dir_tuple[2])

            # Initialize shadow analyzer if needed
            if self.shadow_analyzer is None:
                self.shadow_analyzer = ShadowAnalyzer(stage)
                carb.log_info("[ShadowAnalyzerAPI] Initialized ShadowAnalyzer")

            # Perform ray casting
            is_shadowed, blocking_object = self.shadow_analyzer.is_point_in_shadow(
                query_point,
                sun_direction,
                max_distance=10000.0
            )

            # Store result
            self.result_map[request_id] = (is_shadowed, blocking_object, None)
            carb.log_info(f"[ShadowAnalyzerAPI] Shadow check {request_id} complete: shadowed={is_shadowed}")

        except Exception as e:
            carb.log_error(f"[ShadowAnalyzerAPI] Error in shadow check {request_id}: {e}")
            import traceback
            carb.log_error(f"[ShadowAnalyzerAPI] Traceback: {traceback.format_exc()}")
            self.result_map[request_id] = (False, None, str(e))

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
                azimuth, elevation, distance = self.sun_calculator.calculate_sun_position(
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

            Performs ray-cast shadow detection using building geometry.
            Buildings must be loaded via UI first using "Import Map" button.
            """
            try:
                # Parse timestamp
                if request.timestamp:
                    dt = datetime.fromisoformat(request.timestamp.replace('Z', '+00:00'))
                else:
                    dt = datetime.now(timezone.utc)

                carb.log_info(f"[ShadowAnalyzerAPI] Shadow query: lat={request.latitude}, lon={request.longitude}, time={dt}")

                # Calculate sun position
                azimuth, elevation, distance = self.sun_calculator.calculate_sun_position(
                    request.latitude,
                    request.longitude,
                    dt
                )

                carb.log_info(f"[ShadowAnalyzerAPI] Sun position: az={azimuth:.2f}°, el={elevation:.1f}°")

                # Check if sun is below horizon (nighttime)
                if elevation <= 0:
                    return ShadowQueryResponse(
                        is_shadowed=True,
                        sun_azimuth=azimuth,
                        sun_elevation=elevation,
                        blocking_object=None,
                        latitude=request.latitude,
                        longitude=request.longitude,
                        timestamp=dt.isoformat(),
                        message=f"Sun is below horizon (nighttime). Elevation: {elevation:.1f}°"
                    )

                # Queue the shadow check to be processed on main thread
                # Store request data in a simple dict
                with self.request_lock:
                    request_id = self.next_request_id
                    self.next_request_id += 1

                print(f"[ShadowAnalyzerAPI] Queuing shadow check request {request_id}")
                carb.log_info(f"[ShadowAnalyzerAPI] Queuing shadow check request {request_id}")

                # Queue: (request_id, lat, lon, sun_azimuth, sun_elevation)
                self.request_queue.put((
                    request_id,
                    request.latitude,
                    request.longitude,
                    azimuth,
                    elevation
                ))

                # Wait for result (with timeout)
                timeout = 10.0  # 10 second timeout
                start_time = time.time()
                while time.time() - start_time < timeout:
                    if request_id in self.result_map:
                        # Got result!
                        is_shadowed, blocking_object, error_msg = self.result_map.pop(request_id)

                        if error_msg:
                            return ShadowQueryResponse(
                                is_shadowed=False,
                                sun_azimuth=azimuth,
                                sun_elevation=elevation,
                                blocking_object=None,
                                latitude=request.latitude,
                                longitude=request.longitude,
                                timestamp=dt.isoformat(),
                                message=f"Error during shadow detection: {error_msg}"
                            )

                        # Extract building name if available
                        building_name = None
                        if blocking_object:
                            parts = blocking_object.split("/")
                            if len(parts) > 0:
                                building_name = parts[-1]

                        result_msg = "Point is in shadow" if is_shadowed else "Point has direct sunlight"

                        return ShadowQueryResponse(
                            is_shadowed=is_shadowed,
                            sun_azimuth=azimuth,
                            sun_elevation=elevation,
                            blocking_object=building_name,
                            latitude=request.latitude,
                            longitude=request.longitude,
                            timestamp=dt.isoformat(),
                            message=result_msg
                        )

                    # Wait a bit before checking again
                    await asyncio.sleep(0.05)  # 50ms

                # Timeout
                carb.log_warn(f"[ShadowAnalyzerAPI] Request {request_id} timed out")
                return ShadowQueryResponse(
                    is_shadowed=False,
                    sun_azimuth=azimuth,
                    sun_elevation=elevation,
                    blocking_object=None,
                    latitude=request.latitude,
                    longitude=request.longitude,
                    timestamp=dt.isoformat(),
                    message="Request timed out. The application may be busy."
                )

            except HTTPException:
                raise
            except Exception as e:
                carb.log_error(f"[ShadowAnalyzerAPI] Error processing shadow query: {e}")
                import traceback
                carb.log_error(f"[ShadowAnalyzerAPI] Traceback: {traceback.format_exc()}")
                raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Error processing shadow query: {str(e)}")

    def run(self):
        """Run the API server in a background thread."""
        carb.log_info(f"[ShadowAnalyzerAPI] Starting server on {self.host}:{self.port}")

        # Create uvicorn config
        config = uvicorn.Config(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info",
            access_log=True,
            # Disable lifespan to avoid asyncio conflicts
            lifespan="off"
        )
        self._server = uvicorn.Server(config)

        # Run server in a separate thread to avoid asyncio event loop conflicts
        def run_server():
            """Thread target to run the uvicorn server."""
            import asyncio
            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self._server.serve())
            finally:
                loop.close()

        server_thread = threading.Thread(target=run_server, daemon=True, name="APIServerThread")
        server_thread.start()
        carb.log_info("[ShadowAnalyzerAPI] Server thread started")

    def shutdown(self):
        """Shutdown the API server."""
        if self._server:
            carb.log_info("[ShadowAnalyzerAPI] Shutting down server")
            self._server.should_exit = True
            self._shutdown_event.set()
