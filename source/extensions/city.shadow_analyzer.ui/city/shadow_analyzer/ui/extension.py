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

        # Default location (New York City)
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

                # Info
                ui.Spacer()
                with ui.CollapsableFrame("Info", collapsed=True):
                    ui.Label(
                        "This tool calculates sun position and shadow casting for a given location and time.\n\n"
                        "Features:\n"
                        "• Real-time sun position calculation\n"
                        "• Visual shadow rendering with RTX\n"
                        "• Point query system (coming soon)\n"
                        "• Real city data integration (coming soon)",
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

        carb.log_info(f"[Shadow Analyzer] Querying GPS coordinates: lat={self._query_latitude}, lon={self._query_longitude}")

        # Perform raycast to find 3D point
        stage = omni.usd.get_context().get_stage()
        if not stage:
            return

        # Convert GPS coordinates to scene coordinates
        # For now, use a simple mapping: relative to observer location
        # This simulates querying different locations in the city
        # In a real implementation, this would use actual geographic coordinates
        
        # Calculate offset from observer location in degrees
        lat_diff = self._query_latitude - self._latitude
        lon_diff = self._query_longitude - self._longitude
        
        # Convert to meters (approximately)
        # 1 degree latitude ≈ 111 km
        # 1 degree longitude ≈ 111 km * cos(latitude)
        import math
        meters_per_lat_degree = 111000.0
        meters_per_lon_degree = 111000.0 * math.cos(math.radians(self._query_latitude))
        
        lat_meters = lat_diff * meters_per_lat_degree
        lon_meters = lon_diff * meters_per_lon_degree
        
        # Map to scene coordinates (assuming Z up, X east, Y north)
        # Scale down to fit in scene (1 meter in real world = 0.01 units in scene for better visualization)
        scene_scale = 0.01
        test_point = Gf.Vec3f(
            lon_meters * scene_scale,  # X = East/West
            lat_meters * scene_scale,  # Y = North/South
            0.0  # Z = height (ground level)
        )
        
        # Determine if point is likely on ground or building
        # For now, assume ground level
        hit_prim_path = "/World/Ground"
        
        carb.log_info(f"[Shadow Analyzer] GPS offset: {lat_diff:.6f}° lat, {lon_diff:.6f}° lon")
        carb.log_info(f"[Shadow Analyzer] Scene position: ({test_point[0]:.2f}, {test_point[1]:.2f}, {test_point[2]:.2f})")

        # Query if this point is in sun or shadow
        self._query_point_for_shadow(test_point, hit_prim_path)

        # Create visual marker
        self._create_query_marker(test_point)

    def _query_point_for_shadow(self, point: Gf.Vec3f, hit_prim_path: str):
        """Query if a point is in sunlight or shadow."""
        stage = omni.usd.get_context().get_stage()
        if not stage:
            return

        # Get sun position AT THE QUERY POINT's GPS location
        # (not the observer location - we want to know the sun angle at the queried GPS coordinates)
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

        # Get sun direction (direction FROM point TOWARD sun, opposite of light direction)
        sun_dir = self._sun_calculator.get_sun_direction_vector(azimuth, elevation)
        # Reverse direction - we want to cast ray FROM point TOWARD sun
        ray_direction = Gf.Vec3f(-sun_dir[0], -sun_dir[1], -sun_dir[2])

        # Offset point slightly above surface to avoid self-intersection
        ray_origin = point + Gf.Vec3f(0, 0.1, 0)

        carb.log_info(f"[Shadow Analyzer] Casting ray from {ray_origin} toward sun in direction {ray_direction}")
        carb.log_info(f"[Shadow Analyzer] Sun elevation: {elevation:.2f}°, azimuth: {azimuth:.2f}°")

        # Cast ray toward sun to check for occlusion
        try:
            ray_query = omni.kit.raycast.query.acquire_raycast_query_interface()
            if ray_query:
                # Get viewport for raycast context
                viewport_api = get_viewport_from_window_name("Viewport")
                if not viewport_api:
                    carb.log_warn("[Shadow Analyzer] Could not get viewport for shadow ray")
                    self._query_result_label.text = "⚠️ ERROR: Viewport not found"
                    return
                
                # For now, assume SUNLIGHT if we can't do proper occlusion testing
                # TODO: Implement proper ray casting for shadow detection
                carb.log_info(f"[Shadow Analyzer] Point at {point}, sun elevation {elevation:.1f}°")
                
                # Simple heuristic: if sun is high (>20°), likely sunlight; if low, possible shadow
                is_on_ground = "Ground" in hit_prim_path
                
                if is_on_ground and elevation > 20:
                    result = "☀️ LIKELY SUNLIGHT"
                    color = 0xFFFFAA00
                    detail = f"Point on ground, sun at {elevation:.1f}° elevation (>{20}° threshold)"
                elif is_on_ground and elevation <= 20:
                    result = "🌑 POSSIBLE SHADOW"
                    color = 0xFFAA00FF  
                    detail = f"Point on ground, sun low at {elevation:.1f}° (<={20}° threshold)"
                else:
                    result = "☀️ SUNLIGHT"
                    color = 0xFFFFAA00
                    detail = f"Point on building/object, sun at {elevation:.1f}°"
                
                self._query_result_label.text = result
                self._query_result_label.style = {"color": color, "font_size": 16}
                self._query_position_label.text = f"GPS: ({self._query_latitude:.6f}°, {self._query_longitude:.6f}°)"
                self._query_detail_label.text = detail

        except Exception as e:
            carb.log_error(f"[Shadow Analyzer] Error during query: {e}")
            self._query_result_label.text = "⚠️ ERROR during query"
            self._query_result_label.style = {"color": 0xFFFF0000}

    def _create_query_marker(self, position: Gf.Vec3f):
        """Create a visual marker at the queried point."""
        stage = omni.usd.get_context().get_stage()
        if not stage:
            return

        marker_index = len(self._query_markers)
        marker_path = f"/World/QueryMarker_{marker_index}"

        # Check if marker already exists and remove it
        if stage.GetPrimAtPath(marker_path):
            stage.RemovePrim(marker_path)

        # Create small sphere at query point
        marker = UsdGeom.Sphere.Define(stage, marker_path)
        marker.CreateRadiusAttr(0.3)
        
        # Set position - check if translate op exists first
        xformable = UsdGeom.Xformable(marker)
        translate_ops = [op for op in xformable.GetOrderedXformOps() if op.GetOpType() == UsdGeom.XformOp.TypeTranslate]
        
        if translate_ops:
            # Use existing translate op
            translate_ops[0].Set(Gf.Vec3d(position[0], position[1], position[2]))
        else:
            # Add new translate op
            marker.AddTranslateOp().Set(Gf.Vec3d(position[0], position[1], position[2]))

        # Color based on result
        if "SUNLIGHT" in self._query_result_label.text:
            color = Gf.Vec3f(1.0, 0.9, 0.0)  # Yellow for sunlight
        elif "SHADOW" in self._query_result_label.text:
            color = Gf.Vec3f(0.6, 0.2, 0.8)  # Purple for shadow
        else:
            color = Gf.Vec3f(0.5, 0.5, 1.0)  # Blue for night

        marker.CreateDisplayColorAttr([color])

        self._query_markers.append(marker_path)
        carb.log_info(f"[Shadow Analyzer] Created marker at {position}")

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
