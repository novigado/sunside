"""Main UI extension for City Shadow Analyzer."""

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
from city.shadow_analyzer.buildings import BuildingLoader, BuildingGeometryConverter, ShadowAnalyzer
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
        # Note: BuildingGeometryConverter is created when needed (requires stage)

        # Default location (New York City, USA)
        self._latitude = 40.7128
        self._longitude = -74.0060
        self._current_time = datetime.now(timezone.utc)

        # Query point location (default same as observer location)
        self._query_latitude = 40.7128
        self._query_longitude = -74.0060

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

    def on_shutdown(self):
        """Called when the extension shuts down."""
        self._deactivate_query_mode()
        if self._window:
            self._window.destroy()
            self._window = None
        carb.log_info("[city.shadow_analyzer.ui] Shadow Analyzer UI shutting down")

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

                    self._load_buildings_button = ui.Button("Load Buildings from OpenStreetMap",
                             clicked_fn=self._load_buildings,
                             height=40,
                             style={"background_color": 0xFFFF9800},
                             tooltip="Click to load buildings and roads from OpenStreetMap")

                    self._building_status_label = ui.Label("No buildings loaded",
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
        carb.log_info("[Shadow Analyzer] ===== LOADING SCENE FROM OPENSTREETMAP =====")
        carb.log_info("[Shadow Analyzer] Button clicked - starting load process")

        # IMMEDIATE VISUAL FEEDBACK: Disable button and change appearance
        print("Attempting to disable button and change its appearance...")
        self._load_buildings_button.enabled = False
        self._load_buildings_button.text = "⏳ Loading..."
        self._load_buildings_button.set_style({"background_color": 0xFF757575})  # Gray during loading
        print("Button appearance changed!")

        # Update status
        self._building_status_label.text = "⏳ Loading scene from OpenStreetMap..."
        self._building_status_label.style = {"font_size": 12, "color": 0xFFFFFF00}  # Yellow

        # Get current location from UI
        self._latitude = self._lat_field.model.get_value_as_float()
        self._longitude = self._lon_field.model.get_value_as_float()

        carb.log_info(f"[Shadow Analyzer] Coordinates: ({self._latitude}, {self._longitude})")

        try:
            # Clear cache to ensure fresh data for new location
            self._building_loader.clear_cache()
            carb.log_info("[Shadow Analyzer] Cache cleared")

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
                self._building_status_label.text = "No data found in this area"
                self._building_status_label.style = {"font_size": 12, "color": 0xFFFF0000}  # Red
                carb.log_warn("[Shadow Analyzer] No data found")
                
                # Restore button
                self._load_buildings_button.enabled = True
                self._load_buildings_button.text = "Load Buildings from OpenStreetMap"
                self._load_buildings_button.set_style({"background_color": 0xFFFF9800})  # Original color
                return

            # Get stage
            stage = omni.usd.get_context().get_stage()
            if not stage:
                self._building_status_label.text = "Error: No stage available"
                self._building_status_label.style = {"font_size": 12, "color": 0xFFFF0000}
                
                # Restore button
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

            # Update status
            status_parts = []
            if buildings_data:
                status_parts.append(f"{len(buildings_data)} buildings")
            if roads_data:
                status_parts.append(f"{len(roads_data)} roads")

            status_text = f"✓ Loaded {', '.join(status_parts)} at ({self._latitude:.5f}, {self._longitude:.5f})"
            self._building_status_label.text = status_text
            self._building_status_label.style = {"font_size": 12, "color": 0xFF4CAF50}  # Green
            carb.log_info(f"[Shadow Analyzer] Successfully loaded scene at ({self._latitude}, {self._longitude})")
            
            # Restore button after success
            self._load_buildings_button.enabled = True
            self._load_buildings_button.text = "Load Buildings from OpenStreetMap"
            self._load_buildings_button.set_style({"background_color": 0xFFFF9800})  # Original color

        except Exception as e:
            error_msg = f"Error loading scene: {str(e)}"
            self._building_status_label.text = error_msg
            self._building_status_label.style = {"font_size": 12, "color": 0xFFFF0000}  # Red
            carb.log_error(f"[Shadow Analyzer] {error_msg}")
            import traceback
            carb.log_error(traceback.format_exc())
            
            # Restore button after error
            self._load_buildings_button.enabled = True
            self._load_buildings_button.text = "Load Buildings from OpenStreetMap"
            self._load_buildings_button.set_style({"background_color": 0xFFFF9800})  # Original color

    def _toggle_query_mode(self):
        """Toggle query mode on/off."""
        # Simplified: just perform a single query at viewport center
        self._perform_center_query()

    def _perform_center_query(self):
        """Perform a shadow query at the specified GPS coordinates."""
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

        # Convert GPS coordinates to scene coordinates using the SAME system as buildings
        # This ensures query point is in correct position relative to buildings

        # Calculate offset from reference location (where buildings are centered)
        lat_diff = self._query_latitude - self._latitude
        lon_diff = self._query_longitude - self._longitude

        # Convert to meters (same as BuildingGeometryConverter)
        import math
        meters_per_lat_degree = 111000.0
        meters_per_lon_degree = 111000.0 * math.cos(math.radians(self._query_latitude))

        # Map to scene coordinates (XZ plane with Y up, same as buildings)
        z = lat_diff * meters_per_lat_degree    # Z = North/South (latitude)
        x = lon_diff * meters_per_lon_degree    # X = East/West (longitude)
        y = 0.0  # Y = height (ground level)

        query_point = Gf.Vec3f(x, y, z)

        carb.log_info(f"[Shadow Analyzer] GPS offset: {lat_diff:.6f}° lat, {lon_diff:.6f}° lon")
        carb.log_info(f"[Shadow Analyzer] Distance: {abs(lat_diff * meters_per_lat_degree):.1f}m N/S, {abs(lon_diff * meters_per_lon_degree):.1f}m E/W")
        carb.log_info(f"[Shadow Analyzer] Scene position: X={query_point[0]:.2f}m, Y={query_point[1]:.2f}m, Z={query_point[2]:.2f}m")

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
            carb.log_error("[Shadow Analyzer] No stage available for marker creation")
            return

        marker_index = len(self._query_markers)
        marker_path = f"/World/QueryMarker_{marker_index}"

        carb.log_info(f"[Shadow Analyzer] Creating marker #{marker_index} at {marker_path}")

        # Check if marker already exists and remove it
        if stage.GetPrimAtPath(marker_path):
            stage.RemovePrim(marker_path)

        # Create sphere at query point (raised 10m above ground for visibility)
        marker = UsdGeom.Sphere.Define(stage, marker_path)
        marker.CreateRadiusAttr(10.0)  # 10 meter radius - VERY visible

        # Set position - raise it 10m above ground level
        raised_position = Gf.Vec3d(position[0], position[1] + 10.0, position[2])

        xformable = UsdGeom.Xformable(marker)
        translate_ops = [op for op in xformable.GetOrderedXformOps() if op.GetOpType() == UsdGeom.XformOp.TypeTranslate]

        if translate_ops:
            # Use existing translate op
            translate_ops[0].Set(raised_position)
        else:
            # Add new translate op
            marker.AddTranslateOp().Set(raised_position)

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
