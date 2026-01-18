"""Main UI extension for City Shadow Analyzer."""

import asyncio
import math
import omni.ext
import omni.ui as ui
import omni.usd
import omni.appwindow
import omni.kit.app
import carb
import carb.input
import carb.events
from datetime import datetime, timezone
from pxr import Gf, Sdf, Usd, UsdGeom, UsdLux
from city.shadow_analyzer.sun import SunCalculator
from city.shadow_analyzer.buildings import (
    BuildingLoader,
    BuildingGeometryConverter,
    ShadowAnalyzer,
    TerrainLoader,
    TerrainMeshGenerator
)
import omni.kit.raycast.query
from omni.kit.viewport.utility import get_viewport_from_window_name


class CityAnalyzerUIExtension(omni.ext.IExt):
    """Extension providing UI controls for shadow analysis."""

    def on_startup(self, ext_id):
        """Called when the extension starts up."""
        carb.log_info("[city.shadow_analyzer.ui] Shadow Analyzer UI starting")

        self._ext_id = ext_id
        self._window = None
        self._sun_calculator = SunCalculator()
        self._building_loader = BuildingLoader()
        self._terrain_loader = TerrainLoader()
        self._geometry_converter = None  # Will be initialized when stage is available
        # Note: BuildingGeometryConverter and TerrainMeshGenerator are created when needed (requires stage)

        # Default location (Gothenburg, Sweden - 57.749254, 12.263287)
        self._latitude = 57.749253539442606
        self._longitude = 12.263287434196503
        self._current_time = datetime.now(timezone.utc)

        # Query point location (default same as observer location)
        self._query_latitude = 57.749253539442606
        self._query_longitude = 12.263287434196503

        # Scene elements
        self._sun_light_prim_path = "/World/SunLight"
        self._ground_prim_path = "/World/Ground"

        # Query system
        self._query_mode_active = False
        self._query_markers = []  # Store query point markers
        self._viewport_click_sub = None
        self._last_query_result = None
        self._prev_mouse_state = False  # Track mouse button state

        # Create UI window
        self._create_ui()

        # Initialize scene
        self._initialize_scene()

        # Create reference grid
        self._create_reference_grid()

        # Try to set up Nucleus caching (deferred so it doesn't block UI startup)
        asyncio.ensure_future(self._setup_nucleus_cache_async())

    async def _setup_nucleus_cache_async(self):
        """Initialize Nucleus caching asynchronously."""
        # Wait a bit for nucleus extension to fully start
        await asyncio.sleep(0.5)
        self._setup_nucleus_cache()

    def on_shutdown(self):
        """Called when the extension shuts down."""
        self._deactivate_query_mode()
        if self._window:
            self._window.destroy()
            self._window = None
        carb.log_info("[city.shadow_analyzer.ui] Shadow Analyzer UI shutting down")

    def _setup_nucleus_cache(self):
        """Initialize Nucleus caching if available."""
        try:
            # Import Nucleus manager
            from city.shadow_analyzer.nucleus import get_nucleus_manager
            from city.shadow_analyzer.nucleus.city_cache import CityCacheManager

            # Get global nucleus manager instance
            nucleus_manager = get_nucleus_manager()

            # Create cache manager
            self._nucleus_cache = CityCacheManager(nucleus_manager)

            # Set cache on building loader
            self._building_loader.set_nucleus_cache(self._nucleus_cache)

            # Set cache on terrain loader (if it supports it)
            if hasattr(self._terrain_loader, 'set_nucleus_cache'):
                self._terrain_loader.set_nucleus_cache(self._nucleus_cache)

            carb.log_info("[city.shadow_analyzer.ui] ✅ Nucleus caching enabled")

        except RuntimeError as e:
            # Nucleus extension not loaded yet
            carb.log_warn(f"[city.shadow_analyzer.ui] Nucleus caching not available: {e}")
        except Exception as e:
            carb.log_error(f"[city.shadow_analyzer.ui] Error setting up Nucleus cache: {e}")
            import traceback
            carb.log_error(traceback.format_exc())

    def _create_ui(self):
        """Create the main UI window."""
        self._window = ui.Window("Shadow Analyzer", width=400, height=600)

        with self._window.frame:
            with ui.VStack(spacing=10, style={"margin": 10}):
                # Title
                ui.Label("City Shadow Analyzer",
                        style={"font_size": 24, "alignment": ui.Alignment.CENTER})
                ui.Spacer(height=10)

                # Location settings
                with ui.CollapsableFrame("Location Settings", collapsed=False):
                    with ui.VStack(spacing=5):
                        with ui.HStack():
                            ui.Label("Latitude:", width=100)
                            self._lat_field = ui.FloatField(height=20)
                            self._lat_field.model.set_value(self._latitude)

                        with ui.HStack():
                            ui.Label("Longitude:", width=100)
                            self._lon_field = ui.FloatField(height=20)
                            self._lon_field.model.set_value(self._longitude)

                        ui.Label("(Positive = North/East, Negative = South/West)",
                                style={"font_size": 12, "color": 0x80FFFFFF})

                # Time settings
                with ui.CollapsableFrame("Time Settings", collapsed=False):
                    with ui.VStack(spacing=5):
                        ui.Label("Current Time (UTC):", style={"font_size": 14})
                        self._time_label = ui.Label(
                            self._current_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
                            style={"font_size": 12}
                        )

                        with ui.HStack():
                            ui.Button("Use Current Time", clicked_fn=self._update_current_time, width=200)

                # Sun position display
                with ui.CollapsableFrame("Sun Position", collapsed=False):
                    with ui.VStack(spacing=5):
                        self._azimuth_label = ui.Label("Azimuth: --°")
                        self._elevation_label = ui.Label("Elevation: --°")
                        self._sun_status_label = ui.Label("Status: --")

                # Query results
                with ui.CollapsableFrame("Point Query Results", collapsed=False):
                    with ui.VStack(spacing=5):
                        ui.Label("Query Point GPS Coordinates",
                                style={"font_size": 13, "color": 0xFFFFFFFF})

                        with ui.HStack():
                            ui.Label("Latitude:", width=100)
                            self._query_lat_field = ui.FloatField(height=20)
                            self._query_lat_field.model.set_value(self._query_latitude)

                        with ui.HStack():
                            ui.Label("Longitude:", width=100)
                            self._query_lon_field = ui.FloatField(height=20)
                            self._query_lon_field.model.set_value(self._query_longitude)

                        ui.Spacer(height=5)
                        self._query_result_label = ui.Label("No query yet",
                                                           style={"font_size": 14})
                        self._query_position_label = ui.Label("")
                        self._query_detail_label = ui.Label("", word_wrap=True)

                # Actions
                ui.Spacer(height=10)
                with ui.VStack(spacing=5):
                    ui.Button("Update Sun Position",
                             clicked_fn=self._update_sun_position,
                             height=40,
                             style={"background_color": 0xFF4CAF50})

                    self._load_map_button = ui.Button("Load Map with Terrain & Buildings",
                             clicked_fn=self._load_map_with_terrain,
                             height=40,
                             style={"background_color": 0xFFFF9800},
                             tooltip="Load OpenStreetMap buildings, roads, and terrain elevation data")

                    self._map_status_label = ui.Label("No map data loaded",
                                                      style={"font_size": 12, "color": 0x80FFFFFF})

                    ui.Button("Create Test Scene",
                             clicked_fn=self._create_test_scene,
                             height=30)

                    self._query_mode_button = ui.Button("Query Point at GPS Coordinates",
                             clicked_fn=self._toggle_query_mode,
                             height=35,
                             style={"background_color": 0xFF2196F3})

                    ui.Button("Clear Query Markers",
                             clicked_fn=self._clear_query_markers,
                             height=25)

                    ui.Button("Focus Camera on Scene",
                             clicked_fn=self._focus_camera_on_scene,
                             height=30,
                             style={"background_color": 0xFF9C27B0})

                # Info
                ui.Spacer()
                with ui.CollapsableFrame("Info", collapsed=True):
                    ui.Label(
                        "This tool calculates sun position and shadow casting for a given location and time.\n\n"
                        "Features:\n"
                        "• Real-time sun position calculation\n"
                        "• Visual shadow rendering with RTX\n"
                        "• OpenStreetMap building integration\n"
                        "• Point query system for GPS coordinates\n\n"
                        "Building data © OpenStreetMap contributors",
                        word_wrap=True,
                        style={"font_size": 12}
                    )

    def _initialize_scene(self):
        """Initialize the scene with basic setup."""
        stage = omni.usd.get_context().get_stage()
        if not stage:
            carb.log_warn("[Shadow Analyzer] No stage available yet")
            return

        # Create default prim if needed
        if not stage.GetDefaultPrim():
            world_prim = stage.DefinePrim("/World", "Xform")
            stage.SetDefaultPrim(world_prim)

        carb.log_info("[Shadow Analyzer] Scene initialized")

    def _update_current_time(self):
        """Update to current UTC time."""
        self._current_time = datetime.now(timezone.utc)
        self._time_label.text = self._current_time.strftime("%Y-%m-%d %H:%M:%S UTC")
        carb.log_info(f"[Shadow Analyzer] Time updated to: {self._current_time}")

    def _update_sun_position(self):
        """Calculate and update sun position in the scene."""
        # Get current values from UI
        self._latitude = self._lat_field.model.get_value_as_float()
        self._longitude = self._lon_field.model.get_value_as_float()

        # Calculate sun position
        azimuth, elevation, distance = self._sun_calculator.calculate_sun_position(
            self._latitude, self._longitude, self._current_time
        )

        # Update UI
        self._azimuth_label.text = f"Azimuth: {azimuth:.2f}° (0°=N, 90°=E, 180°=S, 270°=W)"
        self._elevation_label.text = f"Elevation: {elevation:.2f}° (90°=overhead, 0°=horizon)"

        if elevation > 0:
            self._sun_status_label.text = "Status: ☀️ Sun is above horizon"
            self._sun_status_label.style = {"color": 0xFFFFAA00}
        else:
            self._sun_status_label.text = "Status: 🌙 Sun is below horizon (nighttime)"
            self._sun_status_label.style = {"color": 0xFF6666FF}

        # Update sun light in scene
        self._update_sun_light(azimuth, elevation)

        carb.log_info(f"[Shadow Analyzer] Sun updated: az={azimuth:.2f}°, el={elevation:.2f}°")

    def _update_sun_light(self, azimuth: float, elevation: float):
        """Update or create sun light in the scene."""
        stage = omni.usd.get_context().get_stage()
        if not stage:
            carb.log_warn("[Shadow Analyzer] No stage available")
            return

        # Get direction vector
        direction = self._sun_calculator.get_sun_direction_vector(azimuth, elevation)

        # Get or create sun light
        sun_light = UsdLux.DistantLight.Get(stage, self._sun_light_prim_path)
        if not sun_light:
            sun_light = UsdLux.DistantLight.Define(stage, self._sun_light_prim_path)
            sun_light.CreateIntensityAttr(1000)  # Reduced from 50000
            sun_light.CreateColorAttr(Gf.Vec3f(1.0, 0.95, 0.9))  # Slight warm tint

        # Update light direction
        # Note: DistantLight in USD points along -Z axis by default
        # We need to rotate it to point in our calculated direction
        import math

        # Calculate rotation to point light in the direction
        # Convert direction to rotation angles
        x, y, z = direction

        # Calculate rotation angles (in degrees)
        # Elevation rotation around X axis
        elevation_rad = math.asin(-y)
        # Azimuth rotation around Y axis
        azimuth_rad = math.atan2(x, -z)

        # Convert to degrees
        rot_x = math.degrees(elevation_rad)
        rot_y = math.degrees(azimuth_rad)

        # Apply rotation
        xform = UsdGeom.Xform(sun_light)
        xform.ClearXformOpOrder()

        # Rotate around Y (azimuth), then X (elevation)
        rotate_y_op = xform.AddRotateYOp()
        rotate_y_op.Set(rot_y)
        rotate_x_op = xform.AddRotateXOp()
        rotate_x_op.Set(rot_x)

        carb.log_info(f"[Shadow Analyzer] Sun light updated at {self._sun_light_prim_path}")

    def _create_test_scene(self):
        """Create a simple test scene with buildings."""
        stage = omni.usd.get_context().get_stage()
        if not stage:
            carb.log_error("[Shadow Analyzer] No stage available")
            return

        carb.log_info("[Shadow Analyzer] Creating test scene...")

        # Clear existing content (except sun light)
        world_prim = stage.GetPrimAtPath("/World")
        if not world_prim:
            world_prim = stage.DefinePrim("/World", "Xform")
            stage.SetDefaultPrim(world_prim)

        # Create ground plane
        ground = UsdGeom.Mesh.Define(stage, self._ground_prim_path)
        ground.CreatePointsAttr([
            Gf.Vec3f(-50, 0, -50),
            Gf.Vec3f(50, 0, -50),
            Gf.Vec3f(50, 0, 50),
            Gf.Vec3f(-50, 0, 50)
        ])
        ground.CreateFaceVertexCountsAttr([4])
        ground.CreateFaceVertexIndicesAttr([0, 1, 2, 3])
        ground.CreateNormalsAttr([Gf.Vec3f(0, 1, 0)] * 4)
        ground.SetNormalsInterpolation("vertex")

        # Create simple building blocks (representing city buildings)
        buildings_data = [
            # (x, z, width, height, depth)
            (10, 10, 5, 15, 5),    # Tall building
            (-10, 10, 8, 8, 8),     # Medium cube
            (0, -15, 6, 20, 6),     # Very tall building
            (15, -10, 4, 12, 4),    # Another building
            (-15, -15, 7, 10, 7),   # Another building
        ]

        for i, (x, z, width, height, depth) in enumerate(buildings_data):
            building_path = f"/World/Building_{i+1}"
            building = UsdGeom.Cube.Define(stage, building_path)

            # Position and scale
            building.AddTranslateOp().Set(Gf.Vec3d(x, height/2, z))
            building.AddScaleOp().Set(Gf.Vec3d(width/2, height/2, depth/2))

            # Add color variation
            color = Gf.Vec3f(0.7 + i*0.05, 0.6 + i*0.03, 0.5 + i*0.02)
            building.CreateDisplayColorAttr([color])

        # Update sun position
        self._update_sun_position()

        carb.log_info("[Shadow Analyzer] Test scene created successfully")

    def _load_buildings(self):
        """Load scene from OpenStreetMap (buildings, roads, ground) for the current location."""
        print("=" * 80)
        print("BUTTON CLICKED! _load_buildings function was called")
        print("=" * 80)

        # IMMEDIATE VISUAL FEEDBACK via status label (this works!)
        self._building_status_label.text = "⏳ Button clicked! Starting to load..."
        self._building_status_label.style = {"font_size": 12, "color": 0xFFFFFF00}  # Yellow

        # Schedule the actual loading work to happen after UI refresh
        import omni.kit.app
        async def _do_load():
            # Now update button (after UI has had a chance to refresh)
            self._load_buildings_button.enabled = False
            self._load_buildings_button.text = "⏳ Loading..."
            self._load_buildings_button.set_style({"background_color": 0xFF757575})

            # Update status again
            self._building_status_label.text = "⏳ Loading scene from OpenStreetMap..."

            # Give UI one more frame to update
            await omni.kit.app.get_app().next_update_async()

            # Now do the actual work
            self._load_buildings_sync()

        # Schedule it
        asyncio.ensure_future(_do_load())

    def _get_status_label(self):
        """Get the appropriate status label based on which button was pressed."""
        # Use map status label if it exists (combined button), otherwise use specific labels
        if hasattr(self, '_map_status_label'):
            return self._map_status_label
        elif hasattr(self, '_building_status_label'):
            return self._building_status_label
        elif hasattr(self, '_terrain_status_label'):
            return self._terrain_status_label
        else:
            # Fallback - shouldn't happen
            return None

    def _load_buildings_sync(self, from_combined_button=False):
        """Synchronous part of building loading with Nucleus caching.
        
        Args:
            from_combined_button: If True, don't restore individual button (called from combined load)
        """
        carb.log_info("[Shadow Analyzer] ===== LOADING SCENE =====")
        carb.log_info("[Shadow Analyzer] Button clicked - starting load process")

        # Get current location from UI
        self._latitude = self._lat_field.model.get_value_as_float()
        self._longitude = self._lon_field.model.get_value_as_float()

        carb.log_info(f"[Shadow Analyzer] Coordinates: ({self._latitude}, {self._longitude})")

        # Get the appropriate status label
        status_label = self._get_status_label()

        # Get stage
        stage = omni.usd.get_context().get_stage()
        if not stage:
            if status_label:
                status_label.text = "Error: No stage available"
                status_label.style = {"font_size": 12, "color": 0xFFFF0000}
            if hasattr(self, '_load_buildings_button') and not from_combined_button:
                self._load_buildings_button.enabled = True
                self._load_buildings_button.text = "Load Buildings from OpenStreetMap"
                self._load_buildings_button.set_style({"background_color": 0xFFFF9800})
            return

        try:
            # ========== STEP 1: Try to load from Nucleus cache ==========
            if self._nucleus_cache:
                carb.log_info("[Shadow Analyzer] 🔍 Checking Nucleus cache...")
                if status_label:
                    status_label.text = "🔍 Checking Nucleus cache..."
                    status_label.style = {"font_size": 12, "color": 0xFFFFFF00}  # Yellow

                success, cached_stage, metadata = self._nucleus_cache.load_usd_from_cache(
                    self._latitude,
                    self._longitude,
                    radius=0.5
                )

                if success and cached_stage:
                    carb.log_info("[Shadow Analyzer] ✅ CACHE HIT! Loading from Nucleus...")
                    if metadata:
                        carb.log_info(f"[Shadow Analyzer] Cached at: {metadata.get('saved_at', 'unknown')}")
                        carb.log_info(f"[Shadow Analyzer] Buildings: {metadata.get('building_count', 0)}")
                        carb.log_info(f"[Shadow Analyzer] Roads: {metadata.get('road_count', 0)}")

                    # Clear existing scene
                    for path in ["/World/Buildings", "/World/Roads", "/World/Ground"]:
                        prim = stage.GetPrimAtPath(path)
                        if prim:
                            stage.RemovePrim(path)

                    # Copy cached geometry to scene
                    self._copy_cached_scene_to_stage(cached_stage, stage)

                    # Update status (with safety check for metadata)
                    if metadata:
                        building_count = metadata.get('building_count', 0)
                        road_count = metadata.get('road_count', 0)
                        status_text = f"✓ Loaded from cache: {building_count} buildings, {road_count} roads"
                    else:
                        status_text = "✓ Loaded from cache"

                    if status_label:
                        status_label.text = status_text
                        status_label.style = {"font_size": 12, "color": 0xFF4CAF50}  # Green

                    # Restore button
                    if hasattr(self, '_load_buildings_button') and not from_combined_button:
                        self._load_buildings_button.enabled = True
                        self._load_buildings_button.text = "Load Buildings from OpenStreetMap"
                        self._load_buildings_button.set_style({"background_color": 0xFFFF9800})

                    carb.log_info("[Shadow Analyzer] ✅ Successfully loaded scene from Nucleus cache!")
                    return
                else:
                    carb.log_info("[Shadow Analyzer] ⚠️ Cache miss - will load from OpenStreetMap")

            # ========== STEP 2: Cache miss - load from OpenStreetMap ==========
            carb.log_info("[Shadow Analyzer] 🌍 Loading from OpenStreetMap...")
            if status_label:
                status_label.text = "⏳ Loading scene from OpenStreetMap..."
                status_label.style = {"font_size": 12, "color": 0xFFFFFF00}  # Yellow

            # Clear in-memory cache to ensure fresh data
            self._building_loader.clear_cache()
            carb.log_info("[Shadow Analyzer] In-memory cache cleared")

            # Load comprehensive scene data from OpenStreetMap (0.5km radius)
            carb.log_info(f"[Shadow Analyzer] Fetching scene data at ({self._latitude}, {self._longitude})")
            scene_data = self._building_loader.load_scene_data(
                self._latitude,
                self._longitude,
                radius_km=0.5
            )

            buildings_data = scene_data.get("buildings", [])
            roads_data = scene_data.get("roads", [])

            if not buildings_data and not roads_data:
                if status_label:
                    status_label.text = "No data found in this area"
                    status_label.style = {"font_size": 12, "color": 0xFFFF0000}  # Red
                carb.log_warn("[Shadow Analyzer] No data found")

                # Restore button
                if hasattr(self, '_load_buildings_button') and not from_combined_button:
                    self._load_buildings_button.enabled = True
                    self._load_buildings_button.text = "Load Buildings from OpenStreetMap"
                    self._load_buildings_button.set_style({"background_color": 0xFFFF9800})  # Original color
                return

            # Get stage
            stage = omni.usd.get_context().get_stage()
            if not stage:
                if status_label:
                    status_label.text = "Error: No stage available"
                    status_label.style = {"font_size": 12, "color": 0xFFFF0000}

                # Restore button
                if hasattr(self, '_load_buildings_button') and not from_combined_button:
                    self._load_buildings_button.enabled = True
                    self._load_buildings_button.text = "Load Buildings from OpenStreetMap"
                    self._load_buildings_button.set_style({"background_color": 0xFFFF9800})  # Original color
                return

            # Create geometry converter (needs stage)
            geometry_converter = BuildingGeometryConverter(stage)

            # Clear existing scene elements
            for path in ["/World/Buildings", "/World/Roads", "/World/Ground"]:
                prim = stage.GetPrimAtPath(path)
                if prim:
                    stage.RemovePrim(path)

            # Create ground plane first (underneath everything)
            carb.log_info(f"[Shadow Analyzer] Creating ground plane...")
            geometry_converter.create_ground_plane(
                self._latitude,
                self._longitude,
                size=1000.0  # 1km x 1km ground
            )

            # Create roads
            if roads_data:
                carb.log_info(f"[Shadow Analyzer] Creating {len(roads_data)} roads in scene...")
                geometry_converter.create_roads_from_data(
                    roads_data,
                    self._latitude,
                    self._longitude
                )

            # Create buildings
            if buildings_data:
                carb.log_info(f"[Shadow Analyzer] Creating {len(buildings_data)} buildings in scene...")
                carb.log_info(f"[Shadow Analyzer] Reference point: ({self._latitude}, {self._longitude})")

                # Log first few building IDs to verify different data
                sample_ids = [b['id'] for b in buildings_data[:5]]
                carb.log_info(f"[Shadow Analyzer] Sample building IDs: {sample_ids}")

                geometry_converter.create_buildings_from_data(
                    buildings_data,
                    self._latitude,
                    self._longitude
                )

            # ========== STEP 3: Save to Nucleus cache ==========
            if self._nucleus_cache:
                carb.log_info("[Shadow Analyzer] 💾 Saving scene to Nucleus cache...")
                if status_label:
                    status_label.text = "💾 Saving to Nucleus cache..."

                try:
                    # Create a temporary stage with just the scene geometry
                    temp_stage = self._export_scene_to_temp_stage(stage, buildings_data, roads_data)

                    # Prepare metadata
                    metadata = {
                        'building_count': len(buildings_data) if buildings_data else 0,
                        'road_count': len(roads_data) if roads_data else 0,
                        'bounds': {
                            'center_lat': self._latitude,
                            'center_lon': self._longitude,
                            'radius_km': 0.5
                        },
                        'data_source': 'OpenStreetMap'
                    }

                    # Save to Nucleus
                    success, nucleus_path = self._nucleus_cache.save_to_cache(
                        self._latitude,
                        self._longitude,
                        0.5,
                        temp_stage,
                        metadata
                    )

                    if success:
                        carb.log_info(f"[Shadow Analyzer] ✅ Saved to Nucleus: {nucleus_path}")
                    else:
                        carb.log_warn(f"[Shadow Analyzer] ⚠️ Failed to save to Nucleus cache")

                except Exception as cache_error:
                    carb.log_warn(f"[Shadow Analyzer] Cache save error: {cache_error}")
                    # Continue anyway - cache failure shouldn't break the load

            # Update status
            status_parts = []
            if buildings_data:
                status_parts.append(f"{len(buildings_data)} buildings")
            if roads_data:
                status_parts.append(f"{len(roads_data)} roads")

            status_text = f"✓ Loaded {', '.join(status_parts)} at ({self._latitude:.5f}, {self._longitude:.5f})"
            if status_label:
                status_label.text = status_text
                status_label.style = {"font_size": 12, "color": 0xFF4CAF50}  # Green
            carb.log_info(f"[Shadow Analyzer] Successfully loaded scene at ({self._latitude}, {self._longitude})")

            # Restore button after success
            if hasattr(self, '_load_buildings_button') and not from_combined_button:
                self._load_buildings_button.enabled = True
                self._load_buildings_button.text = "Load Buildings from OpenStreetMap"
                self._load_buildings_button.set_style({"background_color": 0xFFFF9800})  # Original color

        except Exception as e:
            error_msg = f"Error loading scene: {str(e)}"
            if status_label:
                status_label.text = error_msg
                status_label.style = {"font_size": 12, "color": 0xFFFF0000}  # Red
            carb.log_error(f"[Shadow Analyzer] {error_msg}")
            import traceback
            carb.log_error(traceback.format_exc())

            # Restore button after error
            if hasattr(self, '_load_buildings_button') and not from_combined_button:
                self._load_buildings_button.enabled = True
                self._load_buildings_button.text = "Load Buildings from OpenStreetMap"
                self._load_buildings_button.set_style({"background_color": 0xFFFF9800})  # Original color

    def _copy_cached_scene_to_stage(self, cached_stage: Usd.Stage, target_stage: Usd.Stage):
        """
        Copy cached scene geometry from cached stage to target stage.

        Args:
            cached_stage: Stage loaded from Nucleus cache
            target_stage: Current scene stage to copy into
        """
        from pxr import Sdf

        carb.log_info("[Shadow Analyzer] Copying cached geometry to scene...")

        # Copy each top-level prim from cache
        for prim_name in ["Buildings", "Roads", "Ground"]:
            source_path = f"/{prim_name}"
            source_prim = cached_stage.GetPrimAtPath(source_path)

            if source_prim and source_prim.IsValid():
                target_path = f"/World/{prim_name}"

                # Create parent if needed
                world_prim = target_stage.GetPrimAtPath("/World")
                if not world_prim:
                    UsdGeom.Xform.Define(target_stage, "/World")

                # Copy the prim hierarchy
                Sdf.CopySpec(
                    cached_stage.GetRootLayer(),
                    source_path,
                    target_stage.GetRootLayer(),
                    target_path
                )

                carb.log_info(f"[Shadow Analyzer]   ✓ Copied {prim_name}")

        carb.log_info("[Shadow Analyzer] Finished copying cached geometry")

    def _export_scene_to_temp_stage(
        self,
        source_stage: Usd.Stage,
        buildings_data: list,
        roads_data: list
    ) -> Usd.Stage:
        """
        Export current scene geometry to a temporary stage for caching.

        Args:
            source_stage: Current scene stage
            buildings_data: Building data (for metadata)
            roads_data: Road data (for metadata)

        Returns:
            Temporary USD stage containing only the cacheable geometry
        """
        from pxr import Sdf

        carb.log_info("[Shadow Analyzer] Exporting scene to temporary stage...")

        # Create in-memory temporary stage
        temp_stage = Usd.Stage.CreateInMemory()

        # Copy each element we want to cache
        for prim_name in ["Buildings", "Roads", "Ground"]:
            source_path = f"/World/{prim_name}"
            source_prim = source_stage.GetPrimAtPath(source_path)

            if source_prim and source_prim.IsValid():
                target_path = f"/{prim_name}"

                # Copy the prim hierarchy
                Sdf.CopySpec(
                    source_stage.GetRootLayer(),
                    source_path,
                    temp_stage.GetRootLayer(),
                    target_path
                )

                carb.log_info(f"[Shadow Analyzer]   ✓ Exported {prim_name}")
            else:
                carb.log_warn(f"[Shadow Analyzer]   ⚠️ No {prim_name} prim found to export")

        carb.log_info("[Shadow Analyzer] Finished exporting to temp stage")
        return temp_stage

    def _copy_cached_terrain_to_stage(self, cached_stage: Usd.Stage, target_stage: Usd.Stage):
        """
        Copy cached terrain geometry from cached stage to target stage.

        Args:
            cached_stage: Stage loaded from Nucleus cache
            target_stage: Current scene stage to copy into
        """
        from pxr import Sdf

        carb.log_info("[Shadow Analyzer] Copying cached terrain to scene...")

        # Copy Terrain prim from cache
        source_path = "/Terrain"
        source_prim = cached_stage.GetPrimAtPath(source_path)

        if source_prim and source_prim.IsValid():
            target_path = "/World/Terrain"

            # Create parent if needed
            world_prim = target_stage.GetPrimAtPath("/World")
            if not world_prim:
                from pxr import UsdGeom
                UsdGeom.Xform.Define(target_stage, "/World")

            # Copy the terrain prim hierarchy
            Sdf.CopySpec(
                cached_stage.GetRootLayer(),
                source_path,
                target_stage.GetRootLayer(),
                target_path
            )

            carb.log_info(f"[Shadow Analyzer]   ✓ Copied Terrain")
        else:
            carb.log_warn("[Shadow Analyzer]   ⚠️ No Terrain prim found in cached stage")

        carb.log_info("[Shadow Analyzer] Finished copying cached terrain")

    def _export_terrain_to_temp_stage(self, source_stage: Usd.Stage) -> Usd.Stage:
        """
        Export current terrain geometry to a temporary stage for caching.

        Args:
            source_stage: Current scene stage

        Returns:
            Temporary USD stage containing only the terrain geometry
        """
        from pxr import Sdf

        carb.log_info("[Shadow Analyzer] Exporting terrain to temporary stage...")

        # Create in-memory temporary stage
        temp_stage = Usd.Stage.CreateInMemory()

        # Copy Terrain prim
        source_path = "/World/Terrain"
        source_prim = source_stage.GetPrimAtPath(source_path)

        if source_prim and source_prim.IsValid():
            target_path = "/Terrain"

            # Copy the prim hierarchy
            Sdf.CopySpec(
                source_stage.GetRootLayer(),
                source_path,
                temp_stage.GetRootLayer(),
                target_path
            )

            carb.log_info(f"[Shadow Analyzer]   ✓ Exported Terrain")
        else:
            carb.log_warn("[Shadow Analyzer]   ⚠️ No Terrain prim found to export")

        carb.log_info("[Shadow Analyzer] Finished exporting terrain to temp stage")
        return temp_stage

    def _load_terrain(self):
        """Load terrain elevation data (async wrapper)."""
        # Immediate status update
        self._terrain_status_label.text = "⏳ Button clicked! Starting to load terrain..."

        # Schedule async work
        async def _do_load():
            # Update button after UI refresh
            self._load_terrain_button.enabled = False
            self._load_terrain_button.text = "⏳ Loading Terrain..."
            self._load_terrain_button.set_style({"background_color": 0xFF757575})  # Gray

            # Wait for UI update
            await omni.kit.app.get_app().next_update_async()

            # Do actual work
            self._load_terrain_sync()

        # Schedule it
        asyncio.ensure_future(_do_load())

    def _load_terrain_sync(self, from_combined_button=False):
        """Synchronous part of terrain loading with Nucleus caching.
        
        Args:
            from_combined_button: If True, don't restore individual button (called from combined load)
        """
        carb.log_info("[Shadow Analyzer] ===== LOADING TERRAIN ELEVATION DATA =====")

        # Get the appropriate status label based on context
        status_label = self._get_status_label()

        # Update status
        if status_label:
            status_label.text = "⏳ Loading terrain elevation data..."
            status_label.style = {"font_size": 12, "color": 0xFFFFFF00}  # Yellow

        # Get current location from UI
        latitude = self._lat_field.model.get_value_as_float()
        longitude = self._lon_field.model.get_value_as_float()
        grid_resolution = 20  # Default resolution

        carb.log_info(f"[Shadow Analyzer] Loading terrain at ({latitude}, {longitude})")

        try:
            # Get stage
            stage = omni.usd.get_context().get_stage()
            if not stage:
                if status_label:
                    status_label.text = "Error: No stage available"
                    status_label.style = {"font_size": 12, "color": 0xFFFF0000}
                self._restore_terrain_button()
                return

            # STEP 1: Check Nucleus cache first
            if self._nucleus_cache:
                carb.log_info(f"[Shadow Analyzer] 🔍 Checking Nucleus terrain cache for ({latitude:.5f}, {longitude:.5f})...")

                success, cached_stage, metadata = self._nucleus_cache.load_terrain_from_cache(
                    latitude, longitude, radius=0.5, resolution=grid_resolution
                )

                if success and cached_stage:
                    carb.log_info(f"[Shadow Analyzer] ✅ TERRAIN CACHE HIT! Loading from Nucleus...")
                    carb.log_info(f"[Shadow Analyzer] Terrain cache metadata: {metadata}")

                    # Clear existing terrain
                    terrain_prim = stage.GetPrimAtPath("/World/Terrain")
                    if terrain_prim:
                        stage.RemovePrim("/World/Terrain")

                    # Copy cached terrain to scene
                    self._copy_cached_terrain_to_stage(cached_stage, stage)

                    # Get elevation info from metadata (with safety check)
                    if metadata:
                        min_elev = metadata.get('min_elevation', 0.0)
                        max_elev = metadata.get('max_elevation', 0.0)
                    else:
                        min_elev = 0.0
                        max_elev = 0.0

                    # Check if buildings exist and need to be adjusted for terrain
                    buildings_prim = stage.GetPrimAtPath("/World/Buildings")
                    if buildings_prim and buildings_prim.IsValid():
                        carb.log_info(f"[Shadow Analyzer] Buildings exist - adjusting for terrain elevation...")
                        self._adjust_buildings_for_terrain(stage)
                        status_text = f"✓ Terrain loaded from cache: {min_elev:.1f}m to {max_elev:.1f}m (buildings adjusted)"
                    else:
                        status_text = f"✓ Terrain loaded from cache: {min_elev:.1f}m to {max_elev:.1f}m elevation"

                    if status_label:
                        status_label.text = status_text
                        status_label.style = {"font_size": 12, "color": 0xFF4CAF50}  # Green
                    self._restore_terrain_button()
                    return  # Done! No need to query Open-Elevation API

            # STEP 2: Cache miss - load from Open-Elevation API
            carb.log_info(f"[Shadow Analyzer] ❌ Terrain cache miss, loading from Open-Elevation API...")

            result = self._terrain_loader.load_elevation_grid(
                latitude,
                longitude,
                radius_m=500.0,
                grid_resolution=grid_resolution
            )

            if result is None:
                if status_label:
                    status_label.text = "Error loading terrain data"
                    status_label.style = {"font_size": 12, "color": 0xFFFF0000}  # Red
                carb.log_error("[Shadow Analyzer] Failed to load terrain data")
                self._restore_terrain_button()
                return

            elevation_grid, lat_spacing, lon_spacing = result

            # Create terrain mesh generator
            terrain_generator = TerrainMeshGenerator(stage)

            # Clear existing terrain
            terrain_prim = stage.GetPrimAtPath("/World/Terrain")
            if terrain_prim:
                stage.RemovePrim("/World/Terrain")

            # Create terrain mesh
            carb.log_info(f"[Shadow Analyzer] Creating terrain mesh...")
            success = terrain_generator.create_terrain_mesh(
                elevation_grid,
                latitude,
                longitude,
                lat_spacing,
                lon_spacing,
                latitude,  # Use current location as reference
                longitude
            )

            if not success:
                if status_label:
                    status_label.text = "Error creating terrain mesh"
                    status_label.style = {"font_size": 12, "color": 0xFFFF0000}
                self._restore_terrain_button()
                return

            min_elev = elevation_grid.min()
            max_elev = elevation_grid.max()

            # STEP 3: Save to Nucleus cache
            if self._nucleus_cache:
                carb.log_info(f"[Shadow Analyzer] 💾 Saving terrain to Nucleus cache...")

                # Export terrain to temporary stage
                temp_stage = self._export_terrain_to_temp_stage(stage)

                # Prepare metadata
                metadata = {
                    'min_elevation': float(min_elev),
                    'max_elevation': float(max_elev),
                    'grid_resolution': grid_resolution,
                    'lat_spacing': float(lat_spacing),
                    'lon_spacing': float(lon_spacing),
                    'data_source': 'Open-Elevation API'
                }

                # Save to cache
                success, nucleus_path = self._nucleus_cache.save_terrain_to_cache(
                    latitude, longitude, 0.5, grid_resolution, temp_stage, metadata
                )

                if success:
                    carb.log_info(f"[Shadow Analyzer] ✅ Saved terrain to Nucleus: {nucleus_path}")
                else:
                    carb.log_warn(f"[Shadow Analyzer] ⚠️ Failed to save terrain to Nucleus cache")

            # Check if buildings exist and need to be adjusted for terrain
            buildings_prim = stage.GetPrimAtPath("/World/Buildings")
            if buildings_prim and buildings_prim.IsValid():
                carb.log_info(f"[Shadow Analyzer] Buildings exist - adjusting for terrain elevation...")
                self._adjust_buildings_for_terrain(stage)
                status_text = f"✓ Terrain loaded: {min_elev:.1f}m to {max_elev:.1f}m (buildings adjusted)"
            else:
                status_text = f"✓ Terrain loaded: {min_elev:.1f}m to {max_elev:.1f}m elevation"

            if status_label:
                status_label.text = status_text
                status_label.style = {"font_size": 12, "color": 0xFF4CAF50}  # Green
            carb.log_info(f"[Shadow Analyzer] Successfully loaded terrain")

            if not from_combined_button:
                self._restore_terrain_button()

        except Exception as e:
            error_msg = f"Error loading terrain: {str(e)}"
            if status_label:
                status_label.text = error_msg
                status_label.style = {"font_size": 12, "color": 0xFFFF0000}  # Red
            carb.log_error(f"[Shadow Analyzer] {error_msg}")
            import traceback
            carb.log_error(traceback.format_exc())
            if not from_combined_button:
                self._restore_terrain_button()

    def _restore_terrain_button(self):
        """Restore terrain button to default state."""
        if hasattr(self, '_load_terrain_button'):
            self._load_terrain_button.enabled = True
            self._load_terrain_button.text = "Load Terrain Elevation Data"
            self._load_terrain_button.set_style({"background_color": 0xFF8BC34A})

    def _toggle_query_mode(self):
        """Toggle query mode on/off."""
        carb.log_info("[Shadow Analyzer] ========== QUERY BUTTON CLICKED ==========")
        # Simplified: just perform a single query at viewport center
        self._perform_center_query()

    def _perform_center_query(self):
        """Perform a shadow query at the specified GPS coordinates."""
        carb.log_info("[Shadow Analyzer] _perform_center_query() called")
        carb.log_info("[Shadow Analyzer] Performing GPS coordinate query")

        # Get query coordinates from UI
        self._query_latitude = self._query_lat_field.model.get_value_as_float()
        self._query_longitude = self._query_lon_field.model.get_value_as_float()

        carb.log_info(f"[Shadow Analyzer] Query coordinates: lat={self._query_latitude}, lon={self._query_longitude}")

        # Ensure there's a reference grid for visual context
        self._create_reference_grid()

        # Temporarily enable query mode for this operation
        self._query_mode_active = True

        # Get viewport API
        viewport_api = get_viewport_from_window_name("Viewport")
        if not viewport_api:
            carb.log_warn("[Shadow Analyzer] Could not get viewport API")
            self._query_mode_active = False
            return

        # Get viewport size
        viewport_window = ui.Workspace.get_window("Viewport")
        if not viewport_window:
            self._query_mode_active = False
            return

        # Use center of viewport (x,y not used for GPS query but kept for compatibility)
        width = viewport_window.width
        height = viewport_window.height
        x = width / 2
        y = height / 2

        self._on_viewport_click(x, y)

        # Reset query mode
        self._query_mode_active = False

    def _activate_query_mode(self):
        """Activate query mode - simplified to just update button."""
        self._query_mode_active = True
        self._query_mode_button.text = "🎯 Click to Query Center"
        self._query_mode_button.style = {"background_color": 0xFF4CAF50}
        carb.log_info("[Shadow Analyzer] Query mode ready")

    def _deactivate_query_mode(self):
        """Deactivate query mode."""
        self._query_mode_active = False
        self._query_mode_button.text = "Activate Query Mode"
        self._query_mode_button.style = {"background_color": 0xFF2196F3}

        if self._viewport_click_sub:
            self._viewport_click_sub = None

        carb.log_info("[Shadow Analyzer] Query mode deactivated")

    def _on_viewport_click(self, x: float, y: float):
        """Handle query for specified GPS coordinates."""
        if not self._query_mode_active:
            return

        carb.log_info(f"[Shadow Analyzer] ===== QUERYING GPS COORDINATES =====")
        carb.log_info(f"[Shadow Analyzer] Query: lat={self._query_latitude}, lon={self._query_longitude}")

        stage = omni.usd.get_context().get_stage()
        if not stage:
            carb.log_error("[Shadow Analyzer] No stage available")
            return

        # Initialize geometry converter if needed
        if self._geometry_converter is None:
            self._geometry_converter = BuildingGeometryConverter(stage)
            carb.log_info("[Shadow Analyzer] Created geometry converter instance")

        # Try to load reference point from buildings in scene
        has_buildings = self._geometry_converter.load_reference_point_from_scene()
        if not has_buildings:
            carb.log_warn("[Shadow Analyzer] ⚠️ NO BUILDINGS FOUND IN SCENE - using UI coordinates as reference")
            carb.log_warn(f"[Shadow Analyzer] UI reference: ({self._latitude}, {self._longitude})")
            # Fall back to UI coordinates if no buildings loaded
            self._geometry_converter.set_reference_point(self._latitude, self._longitude)
        else:
            carb.log_info(f"[Shadow Analyzer] ✓ Using building reference point: "
                         f"({self._geometry_converter.reference_lat:.6f}, {self._geometry_converter.reference_lon:.6f})")

        # Convert GPS coordinates to scene coordinates using the SAME reference as buildings
        try:
            x, z = self._geometry_converter.gps_to_scene_coords(self._query_latitude, self._query_longitude)
            y = 0.0  # Y = height (ground level)
            query_point = Gf.Vec3f(x, y, z)

            # Calculate GPS offsets for logging
            lat_offset = self._query_latitude - self._geometry_converter.reference_lat
            lon_offset = self._query_longitude - self._geometry_converter.reference_lon
            
            carb.log_info(f"[Shadow Analyzer] ========== COORDINATE CONVERSION ==========")
            carb.log_info(f"[Shadow Analyzer] Query GPS: ({self._query_latitude:.6f}°, {self._query_longitude:.6f}°)")
            carb.log_info(f"[Shadow Analyzer] Reference GPS: ({self._geometry_converter.reference_lat:.6f}°, {self._geometry_converter.reference_lon:.6f}°)")
            carb.log_info(f"[Shadow Analyzer] GPS offset: {lat_offset:.6f}° lat, {lon_offset:.6f}° lon")
            
            # Calculate distance in meters
            meters_per_lat = 111000.0
            meters_per_lon = 111000.0 * math.cos(math.radians(self._query_latitude))
            lat_distance = abs(lat_offset * meters_per_lat)
            lon_distance = abs(lon_offset * meters_per_lon)
            total_distance = math.sqrt((lat_offset * meters_per_lat)**2 + (lon_offset * meters_per_lon)**2)
            
            carb.log_info(f"[Shadow Analyzer] Distance from reference: {lat_distance:.1f}m N/S, {lon_distance:.1f}m E/W (total: {total_distance:.1f}m)")
            carb.log_info(f"[Shadow Analyzer] Scene coordinates: X={query_point[0]:.2f}m, Y={query_point[1]:.2f}m, Z={query_point[2]:.2f}m")
            carb.log_info(f"[Shadow Analyzer] ==========================================")

        except ValueError as e:
            carb.log_error(f"[Shadow Analyzer] ❌ Error converting coordinates: {e}")
            return

        # Create visual marker BEFORE shadow analysis
        self._create_query_marker(query_point)

        # Query if this point is in sun or shadow
        self._query_point_for_shadow(query_point, "/World/Ground")

    def _query_point_for_shadow(self, point: Gf.Vec3f, hit_prim_path: str):
        """Query if a point is in sunlight or shadow using real ray casting."""
        stage = omni.usd.get_context().get_stage()
        if not stage:
            return

        # Get sun position AT THE QUERY POINT's GPS location
        azimuth, elevation, _ = self._sun_calculator.calculate_sun_position(
            self._query_latitude, self._query_longitude, self._current_time
        )

        # Check if sun is below horizon
        if elevation <= 0:
            self._query_result_label.text = "🌙 NIGHT (Sun below horizon)"
            self._query_result_label.style = {"color": 0xFF6666FF, "font_size": 16}
            self._query_position_label.text = f"GPS: ({self._query_latitude:.6f}°, {self._query_longitude:.6f}°)"
            self._query_detail_label.text = f"Sun elevation: {elevation:.2f}° (below horizon)"
            return

        # Get sun direction vector (light direction FROM sun TO ground)
        sun_dir_vec = self._sun_calculator.get_sun_direction_vector(azimuth, elevation)
        sun_direction = Gf.Vec3f(sun_dir_vec[0], sun_dir_vec[1], sun_dir_vec[2])

        carb.log_info(f"[Shadow Analyzer] Querying point {point}")
        carb.log_info(f"[Shadow Analyzer] Sun: elevation={elevation:.2f}°, azimuth={azimuth:.2f}°")
        carb.log_info(f"[Shadow Analyzer] Sun direction: {sun_direction}")

        # Use shadow analyzer to check for occlusion
        shadow_analyzer = ShadowAnalyzer(stage)
        is_shadowed, blocking_object = shadow_analyzer.is_point_in_shadow(
            point, sun_direction, max_distance=10000.0
        )

        # Update UI with results
        if is_shadowed:
            self._query_result_label.text = "🌑 SHADOW"
            self._query_result_label.style = {"color": 0xFFAA00FF, "font_size": 16}

            building_name = "Building" if blocking_object else "Unknown object"
            if blocking_object:
                # Extract building ID from path like "/World/Buildings/Building_123456"
                parts = blocking_object.split("/")
                if len(parts) > 0:
                    building_name = parts[-1]

            detail = f"Blocked by {building_name}\nSun: {elevation:.1f}° elevation, {azimuth:.1f}° azimuth"
        else:
            self._query_result_label.text = "☀️ SUNLIGHT"
            self._query_result_label.style = {"color": 0xFFFFAA00, "font_size": 16}
            detail = f"Direct sunlight\nSun: {elevation:.1f}° elevation, {azimuth:.1f}° azimuth"

        self._query_position_label.text = f"GPS: ({self._query_latitude:.6f}°, {self._query_longitude:.6f}°)"
        self._query_detail_label.text = detail

        carb.log_info(f"[Shadow Analyzer] Result: {'SHADOW' if is_shadowed else 'SUNLIGHT'}")

        # Update marker color to reflect result
        self._update_marker_color(is_shadowed)

    def _update_marker_color(self, is_shadowed: bool):
        """Update the most recent marker's color based on shadow result."""
        if not self._query_markers:
            return

        stage = omni.usd.get_context().get_stage()
        if not stage:
            return

        # Get the most recent marker
        marker_path = self._query_markers[-1]
        marker_prim = stage.GetPrimAtPath(marker_path)
        if not marker_prim:
            return

        marker = UsdGeom.Sphere(marker_prim)

        # Set color based on result
        if is_shadowed:
            color = Gf.Vec3f(0.8, 0.1, 0.9)  # Bright purple/magenta for shadow
        else:
            color = Gf.Vec3f(1.0, 0.9, 0.0)  # Yellow for sunlight

        marker.CreateDisplayColorAttr([color])
        carb.log_info(f"[Shadow Analyzer] Updated marker color: {'SHADOW (purple)' if is_shadowed else 'SUNLIGHT (yellow)'}")

    def _create_query_marker(self, position: Gf.Vec3f):
        """Create a visual marker at the queried point."""
        stage = omni.usd.get_context().get_stage()
        if not stage:
            carb.log_error("[Shadow Analyzer] ❌ No stage available for marker creation")
            return

        marker_index = len(self._query_markers)
        marker_path = f"/World/QueryMarker_{marker_index}"

        carb.log_info(f"[Shadow Analyzer] ========== CREATING MARKER ==========")
        carb.log_info(f"[Shadow Analyzer] Marker #{marker_index} at path: {marker_path}")
        carb.log_info(f"[Shadow Analyzer] Ground position: ({position[0]:.2f}, {position[1]:.2f}, {position[2]:.2f})")

        # Check if marker already exists and remove it
        if stage.GetPrimAtPath(marker_path):
            carb.log_info(f"[Shadow Analyzer] Removing existing marker at {marker_path}")
            stage.RemovePrim(marker_path)

        # Create sphere at query point (raised 10m above ground for visibility)
        marker = UsdGeom.Sphere.Define(stage, marker_path)
        marker.CreateRadiusAttr(10.0)  # 10 meter radius - VERY visible

        # Set position - raise it 10m above ground level
        raised_position = Gf.Vec3d(position[0], position[1] + 10.0, position[2])

        carb.log_info(f"[Shadow Analyzer] Raised position: ({raised_position[0]:.2f}, {raised_position[1]:.2f}, {raised_position[2]:.2f})")

        xformable = UsdGeom.Xformable(marker)
        translate_ops = [op for op in xformable.GetOrderedXformOps() if op.GetOpType() == UsdGeom.XformOp.TypeTranslate]

        if translate_ops:
            # Use existing translate op
            translate_ops[0].Set(raised_position)
            carb.log_info(f"[Shadow Analyzer] Updated existing translate op")
        else:
            # Add new translate op
            marker.AddTranslateOp().Set(raised_position)
            carb.log_info(f"[Shadow Analyzer] Added new translate op")

        # Start with blue color (will be updated after shadow analysis)
        # Blue = query location, before we know shadow status
        color = Gf.Vec3f(0.3, 0.7, 1.0)  # Bright cyan/blue

        # If we already have a result, color accordingly
        if "SUNLIGHT" in self._query_result_label.text:
            color = Gf.Vec3f(1.0, 0.9, 0.0)  # Yellow for sunlight
        elif "SHADOW" in self._query_result_label.text:
            color = Gf.Vec3f(0.8, 0.1, 0.9)  # Bright purple/magenta for shadow
        elif "NIGHT" in self._query_result_label.text:
            color = Gf.Vec3f(0.2, 0.2, 0.6)  # Dark blue for night

        marker.CreateDisplayColorAttr([color])

        self._query_markers.append(marker_path)

        carb.log_info(f"[Shadow Analyzer] ✓ Marker created at ({position[0]:.2f}, {raised_position[1]:.2f}, {position[2]:.2f}) - Total: {len(self._query_markers)}")
        carb.log_info(f"[Shadow Analyzer] ==========================================")
        
        # Automatically focus camera on the marker
        self._focus_camera_on_marker(raised_position)

    def _clear_query_markers(self):
        """Clear all query markers from the scene."""
        stage = omni.usd.get_context().get_stage()
        if not stage:
            return

        for marker_path in self._query_markers:
            prim = stage.GetPrimAtPath(marker_path)
            if prim:
                stage.RemovePrim(marker_path)

        self._query_markers.clear()
        carb.log_info("[Shadow Analyzer] Cleared all query markers")

        # Reset query result display
        self._query_result_label.text = "No query yet"
        self._query_result_label.style = {"color": 0xFFFFFFFF, "font_size": 14}
        self._query_position_label.text = ""
        self._query_detail_label.text = ""

    def _focus_camera_on_scene(self):
        """Position camera for a good overview of the scene."""
        carb.log_info("[Shadow Analyzer] Focusing camera on scene...")

        stage = omni.usd.get_context().get_stage()
        if not stage:
            carb.log_warn("[Shadow Analyzer] No stage available")
            return

        try:
            # Get the default perspective camera
            camera_path = "/OmniverseKit_Persp"
            camera_prim = stage.GetPrimAtPath(camera_path)

            if not camera_prim or not camera_prim.IsValid():
                carb.log_warn("[Shadow Analyzer] Default camera not found, trying /World/Camera")
                camera_path = "/World/Camera"
                camera_prim = stage.GetPrimAtPath(camera_path)

            if camera_prim and camera_prim.IsValid():
                from pxr import UsdGeom

                camera_xform = UsdGeom.Xformable(camera_prim)

                # Set camera to a good bird's-eye view position
                # Position: 200m away on diagonal, 150m up
                camera_pos = Gf.Vec3d(200, 150, 200)  # X, Y, Z

                # Calculate rotation to look at origin
                look_at = Gf.Vec3d(0, 0, 0)
                direction = (look_at - camera_pos).GetNormalized()

                # Calculate pitch and yaw
                import math
                xz_length = math.sqrt(direction[0]**2 + direction[2]**2)
                pitch = math.degrees(math.atan2(-direction[1], xz_length))
                yaw = math.degrees(math.atan2(direction[0], -direction[2]))

                # Clear and set transforms
                camera_xform.ClearXformOpOrder()

                # Add translate
                translate_op = camera_xform.AddTranslateOp()
                translate_op.Set(camera_pos)

                # Add rotations
                rotate_y_op = camera_xform.AddRotateYOp()
                rotate_y_op.Set(yaw)

                rotate_x_op = camera_xform.AddRotateXOp()
                rotate_x_op.Set(pitch)

                carb.log_info(f"[Shadow Analyzer] Camera positioned at ({camera_pos[0]}, {camera_pos[1]}, {camera_pos[2]})")
                carb.log_info(f"[Shadow Analyzer] Looking at origin with pitch={pitch:.1f}°, yaw={yaw:.1f}°")

            else:
                carb.log_warn("[Shadow Analyzer] Could not find valid camera to position")

        except Exception as e:
            carb.log_error(f"[Shadow Analyzer] Error positioning camera: {e}")
            import traceback
            carb.log_error(traceback.format_exc())

    def _focus_camera_on_marker(self, marker_position: Gf.Vec3d):
        """Focus camera on a specific marker position."""
        carb.log_info(f"[Shadow Analyzer] Focusing camera on marker at ({marker_position[0]:.2f}, {marker_position[1]:.2f}, {marker_position[2]:.2f})")
        
        stage = omni.usd.get_context().get_stage()
        if not stage:
            carb.log_warn("[Shadow Analyzer] No stage available for camera focus")
            return

        try:
            # Get the default perspective camera
            camera_path = "/OmniverseKit_Persp"
            camera_prim = stage.GetPrimAtPath(camera_path)

            if not camera_prim or not camera_prim.IsValid():
                carb.log_warn("[Shadow Analyzer] Default camera not found, trying /World/Camera")
                camera_path = "/World/Camera"
                camera_prim = stage.GetPrimAtPath(camera_path)

            if camera_prim and camera_prim.IsValid():
                # Position camera to look at marker from above and to the side
                # Camera position: offset from marker by 100m back, 100m up, 100m to the side
                camera_pos = Gf.Vec3d(
                    marker_position[0] + 100.0,  # 100m east
                    marker_position[1] + 100.0,  # 100m up
                    marker_position[2] + 100.0   # 100m south
                )
                
                carb.log_info(f"[Shadow Analyzer] Setting camera position to ({camera_pos[0]:.2f}, {camera_pos[1]:.2f}, {camera_pos[2]:.2f})")
                
                # Set camera translation
                xformable = UsdGeom.Xformable(camera_prim)
                translate_op = None
                
                # Find or create translate op
                for op in xformable.GetOrderedXformOps():
                    if op.GetOpType() == UsdGeom.XformOp.TypeTranslate:
                        translate_op = op
                        break
                
                if translate_op:
                    translate_op.Set(camera_pos)
                else:
                    xformable.AddTranslateOp().Set(camera_pos)
                
                # Calculate look-at rotation (camera looks at marker)
                direction = Gf.Vec3d(
                    marker_position[0] - camera_pos[0],
                    marker_position[1] - camera_pos[1],
                    marker_position[2] - camera_pos[2]
                )
                direction.Normalize()
                
                # Simple rotation to look at marker (approximate)
                import math
                pitch = math.degrees(math.asin(-direction[1]))  # Look down
                yaw = math.degrees(math.atan2(direction[0], -direction[2]))  # Look towards marker
                
                carb.log_info(f"[Shadow Analyzer] Camera rotation: pitch={pitch:.1f}°, yaw={yaw:.1f}°")
                
                # Set camera rotation
                rotate_op = None
                for op in xformable.GetOrderedXformOps():
                    if op.GetOpType() == UsdGeom.XformOp.TypeRotateXYZ:
                        rotate_op = op
                        break
                
                rotation = Gf.Vec3d(pitch, yaw, 0)
                if rotate_op:
                    rotate_op.Set(rotation)
                else:
                    xformable.AddRotateXYZOp().Set(rotation)
                
                carb.log_info(f"[Shadow Analyzer] ✓ Camera focused on marker")
            else:
                carb.log_warn("[Shadow Analyzer] Could not find valid camera prim")
                
        except Exception as e:
            carb.log_error(f"[Shadow Analyzer] Error focusing camera: {e}")
            import traceback
            carb.log_error(traceback.format_exc())

    def _focus_camera_on_scene(self):
        """Position camera for a good overview of the scene."""
        carb.log_info("[Shadow Analyzer] Focusing camera on scene...")

        stage = omni.usd.get_context().get_stage()
        if not stage:
            carb.log_warn("[Shadow Analyzer] No stage available")
            return

        try:
            # Get the default perspective camera
            camera_path = "/OmniverseKit_Persp"
            camera_prim = stage.GetPrimAtPath(camera_path)

            if not camera_prim or not camera_prim.IsValid():
                carb.log_warn("[Shadow Analyzer] Default camera not found, trying /World/Camera")
                camera_path = "/World/Camera"
                camera_prim = stage.GetPrimAtPath(camera_path)

            if camera_prim and camera_prim.IsValid():
                from pxr import UsdGeom

                camera_xform = UsdGeom.Xformable(camera_prim)

                # Set camera to a good bird's-eye view position
                # Position: 200m away on diagonal, 150m up
                camera_pos = Gf.Vec3d(200, 150, 200)  # X, Y, Z

                # Calculate rotation to look at origin
                look_at = Gf.Vec3d(0, 0, 0)
                direction = (look_at - camera_pos).GetNormalized()

                # Calculate pitch and yaw
                import math
                xz_length = math.sqrt(direction[0]**2 + direction[2]**2)
                pitch = math.degrees(math.atan2(-direction[1], xz_length))
                yaw = math.degrees(math.atan2(direction[0], -direction[2]))

                # Clear and set transforms
                camera_xform.ClearXformOpOrder()

                # Add translate
                translate_op = camera_xform.AddTranslateOp()
                translate_op.Set(camera_pos)

                # Add rotations
                rotate_y_op = camera_xform.AddRotateYOp()
                rotate_y_op.Set(yaw)

                rotate_x_op = camera_xform.AddRotateXOp()
                rotate_x_op.Set(pitch)

                carb.log_info(f"[Shadow Analyzer] Camera positioned at ({camera_pos[0]}, {camera_pos[1]}, {camera_pos[2]})")
                carb.log_info(f"[Shadow Analyzer] Looking at origin with pitch={pitch:.1f}°, yaw={yaw:.1f}°")

            else:
                carb.log_warn("[Shadow Analyzer] Could not find valid camera to position")

        except Exception as e:
            carb.log_error(f"[Shadow Analyzer] Error positioning camera: {e}")
            import traceback
            carb.log_error(traceback.format_exc())

    def _create_reference_grid(self):
        """Create a simple reference grid to help visualize marker positions."""
        stage = omni.usd.get_context().get_stage()
        if not stage:
            return

        # Remove existing grid
        grid_path = "/World/ReferenceGrid"
        if stage.GetPrimAtPath(grid_path):
            stage.RemovePrim(grid_path)

        # Create a simple ground plane (100m x 100m) with grid lines
        from pxr import UsdGeom

        # Create parent xform
        xform = UsdGeom.Xform.Define(stage, grid_path)

        # Create ground plane (200m x 200m, centered at origin)
        plane_path = f"{grid_path}/Ground"
        plane = UsdGeom.Mesh.Define(stage, plane_path)

        # Simple square at Y=0
        points = [
            Gf.Vec3f(-100, 0, -100),
            Gf.Vec3f(100, 0, -100),
            Gf.Vec3f(100, 0, 100),
            Gf.Vec3f(-100, 0, 100)
        ]
        plane.CreatePointsAttr(points)
        plane.CreateFaceVertexCountsAttr([4])
        plane.CreateFaceVertexIndicesAttr([0, 1, 2, 3])

        # Green color for ground
        plane.CreateDisplayColorAttr([Gf.Vec3f(0.2, 0.6, 0.2)])

        carb.log_info("[Shadow Analyzer] Created reference grid (200m x 200m)")

    def _adjust_buildings_for_terrain(self, stage):
        """Adjust existing buildings to sit on terrain instead of Y=0."""
        try:
            geometry_converter = BuildingGeometryConverter(stage)
            buildings_prim = stage.GetPrimAtPath("/World/Buildings")
            if not buildings_prim:
                return

            adjusted_count = 0
            for child in buildings_prim.GetAllChildren():
                if not child.IsA(UsdGeom.Mesh):
                    continue

                mesh = UsdGeom.Mesh(child)
                points_attr = mesh.GetPointsAttr()
                if not points_attr:
                    continue

                points = list(points_attr.Get())
                if not points:
                    continue

                # Detect how many bottom vertices (assumed to be first half at Y=0)
                num_points = len(points)
                num_base_verts = num_points // 2

                # Calculate average terrain elevation for this building
                total_elevation = 0.0
                for i in range(num_base_verts):
                    point = points[i]
                    terrain_elev = geometry_converter.get_terrain_elevation_at_point(point[0], point[2])
                    total_elevation += terrain_elev

                base_elevation = total_elevation / num_base_verts if num_base_verts > 0 else 0.0

                # Only adjust if building is at Y=0 (not already adjusted)
                first_point_y = points[0][1]
                if abs(first_point_y) < 0.1:  # Close to zero
                    # Adjust all vertices by base_elevation
                    new_points = []
                    for point in points:
                        new_points.append(Gf.Vec3f(point[0], point[1] + base_elevation, point[2]))

                    mesh.GetPointsAttr().Set(new_points)
                    adjusted_count += 1

            if adjusted_count > 0:
                carb.log_info(f"[Shadow Analyzer] Adjusted {adjusted_count} buildings for terrain elevation")

        except Exception as e:
            carb.log_error(f"[Shadow Analyzer] Error adjusting buildings for terrain: {e}")

    def _load_map_with_terrain(self):
        """Load both terrain and buildings together (async wrapper)."""
        # Immediate status update
        self._map_status_label.text = "⏳ Starting to load map data..."

        # Schedule async work
        async def _do_load():
            # Update button after UI refresh
            self._load_map_button.enabled = False
            self._load_map_button.text = "⏳ Loading Map..."
            self._load_map_button.set_style({"background_color": 0xFF757575})  # Gray

            # Wait for UI update
            await omni.kit.app.get_app().next_update_async()

            try:
                # Do actual work - load buildings first, then terrain
                # Pass from_combined_button=True to prevent individual button restoration
                self._load_buildings_sync(from_combined_button=True)

                # Small delay before terrain
                await omni.kit.app.get_app().next_update_async()

                self._load_terrain_sync(from_combined_button=True)

                # Restore the combined button after both operations complete
                self._restore_map_button()

            except Exception as e:
                # If anything goes wrong, still restore the button
                carb.log_error(f"[Shadow Analyzer] Error in combined map loading: {str(e)}")
                self._restore_map_button()

        # Schedule it
        asyncio.ensure_future(_do_load())

    def _restore_map_button(self):
        """Restore map button to original state."""
        self._load_map_button.enabled = True
        self._load_map_button.text = "Load Map with Terrain & Buildings"
        self._load_map_button.set_style({"background_color": 0xFFFF9800})
