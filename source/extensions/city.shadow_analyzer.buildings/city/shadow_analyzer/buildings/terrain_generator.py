"""Generate USD terrain mesh from elevation data."""

import carb
import numpy as np
from pxr import Gf, Usd, UsdGeom, UsdShade, Sdf
from typing import Tuple
import math


class TerrainMeshGenerator:
    """Generate USD terrain mesh from elevation grid."""

    def __init__(self, stage: Usd.Stage):
        """Initialize terrain mesh generator."""
        self.stage = stage
        # Store terrain data for elevation queries
        self.elevation_grid = None
        self.center_lat = None
        self.center_lon = None
        self.lat_spacing = None
        self.lon_spacing = None
        self.reference_lat = None
        self.reference_lon = None
        self.meters_per_lat_degree = 111000.0
        self.meters_per_lon_degree = None

    def create_terrain_mesh(
        self,
        elevation_grid: np.ndarray,
        center_lat: float,
        center_lon: float,
        lat_spacing: float,
        lon_spacing: float,
        reference_lat: float,
        reference_lon: float
    ) -> bool:
        """
        Create a terrain mesh from elevation grid data.

        Args:
            elevation_grid: 2D numpy array of elevations (meters)
            center_lat: Center latitude of the grid
            center_lon: Center longitude of the grid
            lat_spacing: Degrees per grid cell in latitude
            lon_spacing: Degrees per grid cell in longitude
            reference_lat: Reference point latitude (for coordinate conversion)
            reference_lon: Reference point longitude (for coordinate conversion)

        Returns:
            True if successful, False otherwise
        """
        carb.log_info(f"[TerrainMeshGenerator] Creating terrain mesh from {elevation_grid.shape} grid")

        try:
            # Store terrain data for elevation queries
            self.elevation_grid = elevation_grid
            self.center_lat = center_lat
            self.center_lon = center_lon
            self.lat_spacing = lat_spacing
            self.lon_spacing = lon_spacing
            self.reference_lat = reference_lat
            self.reference_lon = reference_lon
            self.meters_per_lon_degree = 111000.0 * math.cos(math.radians(reference_lat))

            # Get or create terrain prim
            terrain_path = "/World/Terrain"
            terrain_prim = self.stage.GetPrimAtPath(terrain_path)
            if terrain_prim.IsValid():
                self.stage.RemovePrim(terrain_path)

            # Create mesh
            mesh = UsdGeom.Mesh.Define(self.stage, terrain_path)

            # Generate vertices
            rows, cols = elevation_grid.shape
            vertices = []
            face_vertex_counts = []
            face_vertex_indices = []

            # Convert elevation grid to 3D vertices
            # Use same coordinate system as buildings: XZ plane with Y up
            self.meters_per_lon_degree = 111000.0 * math.cos(math.radians(reference_lat))

            # Calculate grid bounds relative to reference point
            grid_lat_min = center_lat - (lat_spacing * (rows - 1) / 2)
            grid_lon_min = center_lon - (lon_spacing * (cols - 1) / 2)

            for i in range(rows):
                for j in range(cols):
                    # Get lat/lon for this grid point
                    lat = grid_lat_min + i * lat_spacing
                    lon = grid_lon_min + j * lon_spacing

                    # Convert to scene coordinates (same as BuildingGeometryConverter)
                    lat_diff = lat - reference_lat
                    lon_diff = lon - reference_lon

                    x = lon_diff * self.meters_per_lon_degree     # X = East/West
                    z = -(lat_diff * self.meters_per_lat_degree)  # Z = North/South, negated to fix north-south flip
                    y = elevation_grid[i, j]                 # Y = height

                    vertices.append(Gf.Vec3f(x, y, z))

            # Generate triangles (two triangles per grid cell)
            for i in range(rows - 1):
                for j in range(cols - 1):
                    # Vertex indices for this cell
                    v0 = i * cols + j
                    v1 = i * cols + (j + 1)
                    v2 = (i + 1) * cols + (j + 1)
                    v3 = (i + 1) * cols + j

                    # First triangle (v0, v1, v2)
                    face_vertex_counts.append(3)
                    face_vertex_indices.extend([v0, v1, v2])

                    # Second triangle (v0, v2, v3)
                    face_vertex_counts.append(3)
                    face_vertex_indices.extend([v0, v2, v3])

            # Set mesh attributes
            mesh.GetPointsAttr().Set(vertices)
            mesh.GetFaceVertexCountsAttr().Set(face_vertex_counts)
            mesh.GetFaceVertexIndicesAttr().Set(face_vertex_indices)

            # Compute normals for better lighting
            UsdGeom.Mesh(mesh).ComputeExtent(vertices)

            # Apply material (earth-tone color)
            self._apply_terrain_material(terrain_path)

            carb.log_info(f"[TerrainMeshGenerator] Created terrain mesh with {len(vertices)} vertices, {len(face_vertex_counts)} faces")
            carb.log_info(f"[TerrainMeshGenerator] Elevation range: {elevation_grid.min():.1f}m to {elevation_grid.max():.1f}m")

            return True

        except Exception as e:
            carb.log_error(f"[TerrainMeshGenerator] Error creating terrain mesh: {e}")
            import traceback
            carb.log_error(f"[TerrainMeshGenerator] Traceback: {traceback.format_exc()}")
            return False

    def _apply_terrain_material(self, mesh_path: str):
        """Apply earth-tone material to terrain mesh."""
        try:
            # Create material
            material_path = f"{mesh_path}/Material"
            material = UsdShade.Material.Define(self.stage, material_path)

            # Create shader
            shader = UsdShade.Shader.Define(self.stage, f"{material_path}/Shader")
            shader.CreateIdAttr("UsdPreviewSurface")

            # Set earth-tone color (brown/tan)
            shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(0.6, 0.5, 0.4))
            # Removed opacity - keep terrain opaque for proper rendering
            shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.9)
            shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.0)

            # Connect shader output
            material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")

            # Bind material to mesh
            mesh_prim = self.stage.GetPrimAtPath(mesh_path)
            UsdShade.MaterialBindingAPI(mesh_prim).Bind(material)

            carb.log_info(f"[TerrainMeshGenerator] Applied terrain material")

        except Exception as e:
            carb.log_warn(f"[TerrainMeshGenerator] Could not apply material: {e}")

    def clear_terrain(self):
        """Remove terrain mesh from stage."""
        terrain_path = "/World/Terrain"
        terrain_prim = self.stage.GetPrimAtPath(terrain_path)
        if terrain_prim.IsValid():
            self.stage.RemovePrim(terrain_path)
            carb.log_info(f"[TerrainMeshGenerator] Cleared terrain mesh")

    def get_elevation_at_scene_coords(self, x: float, z: float) -> float:
        """
        Query terrain elevation at given scene coordinates.

        Args:
            x: Scene X coordinate (East/West)
            z: Scene Z coordinate (North/South)

        Returns:
            Elevation in meters (Y coordinate), or 0.0 if terrain not loaded
        """
        if self.elevation_grid is None:
            carb.log_warn(f"[TerrainMeshGenerator] get_elevation_at_scene_coords called but elevation_grid is None!")
            return 0.0

        try:
            # Convert scene coords back to GPS
            lon_diff = x / self.meters_per_lon_degree
            lat_diff = -z / self.meters_per_lat_degree  # Z is negated

            lat = self.reference_lat + lat_diff
            lon = self.reference_lon + lon_diff

            # Convert GPS to grid indices
            rows, cols = self.elevation_grid.shape
            grid_lat_min = self.center_lat - (self.lat_spacing * (rows - 1) / 2)
            grid_lon_min = self.center_lon - (self.lon_spacing * (cols - 1) / 2)

            # Calculate grid indices
            i = int((lat - grid_lat_min) / self.lat_spacing)
            j = int((lon - grid_lon_min) / self.lon_spacing)

            # Check bounds
            if 0 <= i < rows and 0 <= j < cols:
                elevation = float(self.elevation_grid[i, j])
                return elevation
            else:
                # Outside grid - return 0 (will trigger fallback in building code)
                # Reduced logging to avoid spam - only log first few
                if not hasattr(self, '_outside_warnings'):
                    self._outside_warnings = 0
                if self._outside_warnings < 5:
                    carb.log_warn(f"[TerrainMeshGenerator] Query at ({x:.1f}, {z:.1f}) -> GPS({lat:.6f}, {lon:.6f}) -> indices({i}, {j}) OUTSIDE grid bounds ({rows}x{cols})")
                    self._outside_warnings += 1
                    if self._outside_warnings == 5:
                        carb.log_warn(f"[TerrainMeshGenerator] Further 'outside grid' warnings suppressed...")
                return 0.0

        except Exception as e:
            carb.log_error(f"[TerrainMeshGenerator] Error querying elevation at ({x:.1f}, {z:.1f}): {e}")
            import traceback
            carb.log_error(traceback.format_exc())
            return 0.0

    def get_average_elevation(self) -> float:
        """Get the average elevation of the terrain."""
        if self.elevation_grid is None:
            return 0.0
        return float(self.elevation_grid.mean())
