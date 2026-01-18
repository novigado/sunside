"""Generate USD terrain mesh from elevation data."""

import carb
import numpy as np
from pxr import Gf, Usd, UsdGeom, UsdShade
from typing import Tuple
import math


class TerrainMeshGenerator:
    """Generate USD terrain mesh from elevation grid."""

    def __init__(self, stage: Usd.Stage):
        """Initialize terrain mesh generator."""
        self.stage = stage

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
            meters_per_lat_degree = 111000.0
            meters_per_lon_degree = 111000.0 * math.cos(math.radians(reference_lat))

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

                    x = lon_diff * meters_per_lon_degree     # X = East/West
                    z = -(lat_diff * meters_per_lat_degree)  # Z = North/South, negated to fix north-south flip
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
            shader.CreateInput("diffuseColor", Gf.Vec3f).Set(Gf.Vec3f(0.6, 0.5, 0.4))
            shader.CreateInput("roughness", Gf.Float).Set(0.9)
            shader.CreateInput("metallic", Gf.Float).Set(0.0)

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
