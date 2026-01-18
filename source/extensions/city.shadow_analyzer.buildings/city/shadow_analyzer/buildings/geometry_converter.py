"""Convert OSM building data to USD geometry."""

import carb
from pxr import Gf, Usd, UsdGeom
from typing import List, Dict, Tuple, Optional
import math


class BuildingGeometryConverter:
    """Converts building data to USD 3D geometry."""

    def __init__(self, stage: Usd.Stage):
        """
        Initialize the converter.

        Args:
            stage: USD stage to create geometry in
        """
        self.stage = stage
        self.reference_lat = None
        self.reference_lon = None

    def set_reference_point(self, latitude: float, longitude: float):
        """
        Set the reference point for coordinate conversion.

        Args:
            latitude: Reference latitude
            longitude: Reference longitude
        """
        self.reference_lat = latitude
        self.reference_lon = longitude
        carb.log_info(f"[BuildingConverter] Reference point set to ({latitude}, {longitude})")

        # Store reference point in scene metadata for API access
        buildings_prim = self.stage.GetPrimAtPath("/World/Buildings")
        if buildings_prim:
            buildings_prim.SetCustomDataByKey("reference_latitude", latitude)
            buildings_prim.SetCustomDataByKey("reference_longitude", longitude)

    def load_reference_point_from_scene(self) -> bool:
        """
        Load reference point from scene metadata if buildings exist.

        Returns:
            True if reference point was loaded, False otherwise
        """
        print("[BuildingConverter] Checking for buildings at /World/Buildings...")
        buildings_prim = self.stage.GetPrimAtPath("/World/Buildings")
        if not buildings_prim:
            print("[BuildingConverter] No buildings prim found at /World/Buildings")
            return False

        print(f"[BuildingConverter] Buildings prim found: {buildings_prim.GetPath()}")
        print(f"[BuildingConverter] Buildings prim is valid: {buildings_prim.IsValid()}")

        ref_lat = buildings_prim.GetCustomDataByKey("reference_latitude")
        ref_lon = buildings_prim.GetCustomDataByKey("reference_longitude")

        print(f"[BuildingConverter] reference_latitude: {ref_lat}")
        print(f"[BuildingConverter] reference_longitude: {ref_lon}")

        if ref_lat is not None and ref_lon is not None:
            self.reference_lat = ref_lat
            self.reference_lon = ref_lon
            print(f"[BuildingConverter] Loaded reference point from scene: ({ref_lat}, {ref_lon})")
            carb.log_info(f"[BuildingConverter] Loaded reference point from scene: ({ref_lat}, {ref_lon})")
            return True

        return False

    def gps_to_scene_coords(self, lat: float, lon: float) -> Tuple[float, float]:
        """
        Convert GPS coordinates to scene coordinates.
        Returns (x, z) for use in XZ ground plane with Y-up coordinate system.

        Args:
            lat: Latitude
            lon: Longitude

        Returns:
            Tuple of (x, z) scene coordinates for XZ plane
        """
        if self.reference_lat is None or self.reference_lon is None:
            raise ValueError("Reference point not set. Call set_reference_point() first.")

        # Calculate offset from reference point
        lat_diff = lat - self.reference_lat
        lon_diff = lon - self.reference_lon

        # Convert to meters (approximately)
        meters_per_lat_degree = 111000.0
        meters_per_lon_degree = 111000.0 * math.cos(math.radians(lat))

        z = lat_diff * meters_per_lat_degree      # Latitude -> Z (north-south)
        x = -(lon_diff * meters_per_lon_degree)   # Longitude -> X (east-west), negated to fix left-right flip

        return (x, z)

    def create_building_mesh(
        self,
        building: Dict,
        parent_path: str = "/World/Buildings"
    ) -> Optional[str]:
        """
        Create a 3D mesh from building data.

        Args:
            building: Building dictionary with coordinates and height
            parent_path: USD path for parent prim

        Returns:
            Path to created building prim, or None if failed
        """
        building_id = building["id"]
        building_path = f"{parent_path}/Building_{building_id}"

        try:
            coordinates = building["coordinates"]
            height = building["height"]

            if len(coordinates) < 3:
                carb.log_warn(f"[BuildingConverter] Building {building_id} has < 3 points, skipping")
                return None

            # Convert GPS coordinates to scene coordinates
            scene_coords = []
            for lat, lon in coordinates:
                x, z = self.gps_to_scene_coords(lat, lon)
                scene_coords.append((x, z))

            # Calculate average terrain elevation at building location
            total_elevation = 0.0
            for x, z in scene_coords:
                total_elevation += self.get_terrain_elevation_at_point(x, z)
            base_elevation = total_elevation / len(scene_coords)

            # Create extruded polygon (building as box with polygon base)
            mesh = UsdGeom.Mesh.Define(self.stage, building_path)

            # Build vertices: bottom + top faces
            # USD uses Z-up coordinate system, so buildings lie in XZ plane with Y as height
            # Buildings sit on terrain at base_elevation
            points = []
            for x, z in scene_coords:
                points.append(Gf.Vec3f(x, base_elevation, z))  # Bottom face at terrain elevation
            for x, z in scene_coords:
                points.append(Gf.Vec3f(x, base_elevation + height, z))  # Top face (base + height)

            mesh.CreatePointsAttr(points)

            # Build faces
            num_verts = len(scene_coords)
            face_counts = []
            face_indices = []

            # Bottom face (reversed winding for correct normal)
            face_counts.append(num_verts)
            for i in range(num_verts - 1, -1, -1):
                face_indices.append(i)

            # Top face
            face_counts.append(num_verts)
            for i in range(num_verts):
                face_indices.append(i + num_verts)

            # Side faces
            for i in range(num_verts):
                next_i = (i + 1) % num_verts
                face_counts.append(4)
                face_indices.extend([
                    i, next_i,
                    next_i + num_verts, i + num_verts
                ])

            mesh.CreateFaceVertexCountsAttr(face_counts)
            mesh.CreateFaceVertexIndicesAttr(face_indices)

            # Set color based on building type
            color = self._get_building_color(building["type"])
            mesh.CreateDisplayColorAttr([color])

            carb.log_info(f"[BuildingConverter] Created building mesh at {building_path}")
            return building_path

        except Exception as e:
            carb.log_error(f"[BuildingConverter] Error creating building {building_id}: {e}")
            return None

    def _get_building_color(self, building_type: str) -> Gf.Vec3f:
        """
        Get color for building based on type.

        Args:
            building_type: OSM building type

        Returns:
            RGB color
        """
        color_map = {
            "residential": Gf.Vec3f(0.8, 0.7, 0.6),  # Beige
            "commercial": Gf.Vec3f(0.6, 0.7, 0.8),   # Light blue
            "industrial": Gf.Vec3f(0.5, 0.5, 0.5),   # Gray
            "office": Gf.Vec3f(0.7, 0.8, 0.9),       # Pale blue
            "retail": Gf.Vec3f(0.9, 0.8, 0.7),       # Light orange
            "house": Gf.Vec3f(0.85, 0.75, 0.65),     # Tan
            "apartments": Gf.Vec3f(0.75, 0.65, 0.55), # Brown
        }

        return color_map.get(building_type, Gf.Vec3f(0.7, 0.7, 0.7))  # Default gray

    def create_buildings_from_data(
        self,
        buildings: List[Dict],
        reference_lat: float,
        reference_lon: float
    ) -> List[str]:
        """
        Create all buildings in the scene.

        Args:
            buildings: List of building dictionaries
            reference_lat: Reference point latitude
            reference_lon: Reference point longitude

        Returns:
            List of created building prim paths
        """
        # Ensure parent exists FIRST
        parent_path = "/World/Buildings"
        if not self.stage.GetPrimAtPath(parent_path):
            UsdGeom.Xform.Define(self.stage, parent_path)

        # NOW set reference point (after prim exists, so metadata can be saved)
        self.set_reference_point(reference_lat, reference_lon)

        created_paths = []
        for building in buildings:
            path = self.create_building_mesh(building, parent_path)
            if path:
                created_paths.append(path)

        carb.log_info(f"[BuildingConverter] Created {len(created_paths)} buildings")
        return created_paths

    def clear_buildings(self):
        """Remove all buildings from the scene."""
        parent_path = "/World/Buildings"
        if self.stage.GetPrimAtPath(parent_path):
            self.stage.RemovePrim(parent_path)
            carb.log_info("[BuildingConverter] Cleared all buildings")

    def create_road_mesh(
        self,
        road: Dict,
        parent_path: str = "/World/Roads"
    ) -> Optional[str]:
        """
        Create a road mesh from OSM road data.

        Args:
            road: Road dictionary with coordinates and metadata
            parent_path: Parent prim path

        Returns:
            Path to created road prim, or None if failed
        """
        road_id = road["id"]
        road_path = f"{parent_path}/Road_{road_id}"

        try:
            coordinates = road["coordinates"]
            width = road["width"]

            if len(coordinates) < 2:
                return None

            # Convert GPS coordinates to scene coordinates
            scene_coords = []
            for lat, lon in coordinates:
                x, z = self.gps_to_scene_coords(lat, lon)
                scene_coords.append((x, z))

            # Create road as flat ribbon/strip along the path
            mesh = UsdGeom.Mesh.Define(self.stage, road_path)

            # Build vertices for road strip
            points = []
            half_width = width / 2.0

            for i, (x, z) in enumerate(scene_coords):
                # Calculate perpendicular offset for road width
                if i < len(scene_coords) - 1:
                    # Direction to next point
                    dx = scene_coords[i+1][0] - x
                    dz = scene_coords[i+1][1] - z
                else:
                    # Use direction from previous point
                    dx = x - scene_coords[i-1][0]
                    dz = z - scene_coords[i-1][1]

                # Normalize and rotate 90 degrees for perpendicular
                length = math.sqrt(dx*dx + dz*dz)
                if length > 0:
                    dx /= length
                    dz /= length

                # Perpendicular vector (rotate 90 degrees)
                perp_x = -dz
                perp_z = dx

                # Get terrain elevation at this point
                terrain_elev = self.get_terrain_elevation_at_point(x, z)
                road_y = terrain_elev + 0.05  # Slightly above terrain to avoid z-fighting

                # Create two vertices (left and right edges of road)
                points.append(Gf.Vec3f(x - perp_x * half_width, road_y, z - perp_z * half_width))  # Left edge
                points.append(Gf.Vec3f(x + perp_x * half_width, road_y, z + perp_z * half_width))  # Right edge

            mesh.CreatePointsAttr(points)

            # Build faces (triangles connecting road segments)
            face_counts = []
            face_indices = []

            for i in range(len(scene_coords) - 1):
                # Two vertices per segment, create quad as two triangles
                v0 = i * 2      # Left of segment i
                v1 = i * 2 + 1  # Right of segment i
                v2 = (i + 1) * 2      # Left of segment i+1
                v3 = (i + 1) * 2 + 1  # Right of segment i+1

                # First triangle
                face_counts.append(3)
                face_indices.extend([v0, v2, v1])

                # Second triangle
                face_counts.append(3)
                face_indices.extend([v1, v2, v3])

            mesh.CreateFaceVertexCountsAttr(face_counts)
            mesh.CreateFaceVertexIndicesAttr(face_indices)

            # Set road color based on type
            color = self._get_road_color(road["type"])
            mesh.CreateDisplayColorAttr([color])

            return road_path

        except Exception as e:
            carb.log_error(f"[BuildingConverter] Error creating road {road_id}: {e}")
            return None

    def _get_road_color(self, road_type: str) -> Gf.Vec3f:
        """Get color for road based on type."""
        color_map = {
            "motorway": Gf.Vec3f(0.9, 0.7, 0.4),      # Orange
            "trunk": Gf.Vec3f(0.9, 0.8, 0.5),         # Light orange
            "primary": Gf.Vec3f(0.8, 0.8, 0.6),       # Yellow-gray
            "secondary": Gf.Vec3f(0.7, 0.7, 0.7),     # Light gray
            "tertiary": Gf.Vec3f(0.6, 0.6, 0.6),      # Gray
            "residential": Gf.Vec3f(0.5, 0.5, 0.5),   # Dark gray
            "service": Gf.Vec3f(0.4, 0.4, 0.4),       # Darker gray
            "pedestrian": Gf.Vec3f(0.7, 0.6, 0.5),    # Beige
            "footway": Gf.Vec3f(0.6, 0.5, 0.4),       # Brown
            "path": Gf.Vec3f(0.5, 0.4, 0.3),          # Dark brown
        }
        return color_map.get(road_type, Gf.Vec3f(0.5, 0.5, 0.5))  # Default gray

    def create_roads_from_data(
        self,
        roads: List[Dict],
        reference_lat: float,
        reference_lon: float
    ) -> List[str]:
        """
        Create all roads in the scene.

        Args:
            roads: List of road dictionaries
            reference_lat: Reference point latitude
            reference_lon: Reference point longitude

        Returns:
            List of created road prim paths
        """
        self.set_reference_point(reference_lat, reference_lon)

        # Ensure parent exists
        parent_path = "/World/Roads"
        if not self.stage.GetPrimAtPath(parent_path):
            UsdGeom.Xform.Define(self.stage, parent_path)

        created_paths = []
        for road in roads:
            path = self.create_road_mesh(road, parent_path)
            if path:
                created_paths.append(path)

        carb.log_info(f"[BuildingConverter] Created {len(created_paths)} roads")
        return created_paths

    def create_ground_plane(
        self,
        reference_lat: float,
        reference_lon: float,
        size: float = 1000.0
    ) -> str:
        """
        Create a ground plane for the scene.

        Args:
            reference_lat: Reference point latitude
            reference_lon: Reference point longitude
            size: Size of the ground plane in meters

        Returns:
            Path to created ground plane prim
        """
        ground_path = "/World/Ground"

        # Remove existing ground if any
        if self.stage.GetPrimAtPath(ground_path):
            self.stage.RemovePrim(ground_path)

        # Create mesh for ground plane
        mesh = UsdGeom.Mesh.Define(self.stage, ground_path)

        half_size = size / 2.0

        # Create 4 corner vertices
        points = [
            Gf.Vec3f(-half_size, 0.0, -half_size),
            Gf.Vec3f(half_size, 0.0, -half_size),
            Gf.Vec3f(half_size, 0.0, half_size),
            Gf.Vec3f(-half_size, 0.0, half_size),
        ]

        mesh.CreatePointsAttr(points)

        # Create quad face
        mesh.CreateFaceVertexCountsAttr([4])
        mesh.CreateFaceVertexIndicesAttr([0, 1, 2, 3])

        # Set ground color (grass green)
        mesh.CreateDisplayColorAttr([Gf.Vec3f(0.4, 0.6, 0.3)])

        carb.log_info(f"[BuildingConverter] Created ground plane ({size}m x {size}m)")
        return ground_path

    def get_terrain_elevation_at_point(self, x: float, z: float) -> float:
        """
        Get terrain elevation at a specific scene coordinate by querying the terrain mesh.

        Args:
            x: X coordinate in scene space
            z: Z coordinate in scene space

        Returns:
            Elevation (Y value) at that point, or 0.0 if no terrain exists
        """
        terrain_prim = self.stage.GetPrimAtPath("/World/Terrain")
        if not terrain_prim or not terrain_prim.IsA(UsdGeom.Mesh):
            return 0.0

        try:
            mesh = UsdGeom.Mesh(terrain_prim)
            points_attr = mesh.GetPointsAttr()
            if not points_attr:
                return 0.0

            points = points_attr.Get()
            if not points or len(points) == 0:
                return 0.0

            # Find the closest terrain vertex to the query point
            # This is a simple approach - could use interpolation for better accuracy
            min_dist_sq = float('inf')
            closest_elevation = 0.0

            for point in points:
                dx = point[0] - x
                dz = point[2] - z
                dist_sq = dx * dx + dz * dz

                if dist_sq < min_dist_sq:
                    min_dist_sq = dist_sq
                    closest_elevation = point[1]  # Y value is elevation

            return closest_elevation

        except Exception as e:
            carb.log_warn(f"[BuildingConverter] Error querying terrain elevation: {e}")
            return 0.0
