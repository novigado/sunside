"""Shadow analysis using ray casting against building geometry."""

import carb
from pxr import Gf, Usd, UsdGeom
from typing import Tuple, Optional, List
import math


class ShadowAnalyzer:
    """Analyze shadows by ray casting against building geometry."""

    def __init__(self, stage: Usd.Stage):
        """
        Initialize the shadow analyzer.

        Args:
            stage: USD stage containing the scene
        """
        self.stage = stage
        self.buildings_cache = None

    def is_point_in_shadow(
        self,
        point: Gf.Vec3f,
        sun_direction: Gf.Vec3f,
        max_distance: float = 10000.0
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if a point is in shadow by casting a ray toward the sun.

        Args:
            point: 3D point to check (scene coordinates)
            sun_direction: Direction vector FROM sun TO ground (normalized)
            max_distance: Maximum ray distance in meters

        Returns:
            Tuple of (is_shadowed, blocking_object_path):
                - is_shadowed: True if point is in shadow
                - blocking_object_path: Path of object casting shadow, or None
        """
        # Ray direction is OPPOSITE of sun direction (from point toward sun)
        ray_direction = Gf.Vec3f(-sun_direction[0], -sun_direction[1], -sun_direction[2])

        # Normalize ray direction
        length = math.sqrt(ray_direction[0]**2 + ray_direction[1]**2 + ray_direction[2]**2)
        if length > 0:
            ray_direction = Gf.Vec3f(
                ray_direction[0] / length,
                ray_direction[1] / length,
                ray_direction[2] / length
            )

        # Start ray slightly above the point to avoid self-intersection
        ray_origin = Gf.Vec3f(point[0], point[1] + 0.1, point[2])

        carb.log_info(f"[ShadowAnalyzer] Casting ray from {ray_origin} toward sun (dir: {ray_direction})")

        # Check for intersection with buildings
        hit_result = self._cast_ray_against_buildings(ray_origin, ray_direction, max_distance)

        if hit_result:
            hit_distance, hit_path = hit_result
            carb.log_info(f"[ShadowAnalyzer] Ray hit {hit_path} at distance {hit_distance:.2f}m - SHADOW")
            return True, hit_path
        else:
            carb.log_info(f"[ShadowAnalyzer] Ray did not hit any buildings - SUNLIGHT")
            return False, None

    def _cast_ray_against_buildings(
        self,
        origin: Gf.Vec3f,
        direction: Gf.Vec3f,
        max_distance: float
    ) -> Optional[Tuple[float, str]]:
        """
        Cast a ray and check for intersections with building meshes.

        Args:
            origin: Ray origin point
            direction: Ray direction (normalized)
            max_distance: Maximum ray distance

        Returns:
            Tuple of (distance, prim_path) if hit, None otherwise
        """
        buildings_prim = self.stage.GetPrimAtPath("/World/Buildings")
        if not buildings_prim:
            carb.log_warn("[ShadowAnalyzer] No buildings found at /World/Buildings")
            return None

        closest_hit = None
        closest_distance = max_distance

        # Iterate through all building meshes
        for child in buildings_prim.GetAllChildren():
            if not child.IsA(UsdGeom.Mesh):
                continue

            mesh = UsdGeom.Mesh(child)

            # Get mesh geometry
            points_attr = mesh.GetPointsAttr()
            if not points_attr:
                continue

            points = points_attr.Get()
            if not points:
                continue

            # Get face data
            face_counts_attr = mesh.GetFaceVertexCountsAttr()
            face_indices_attr = mesh.GetFaceVertexIndicesAttr()

            if not face_counts_attr or not face_indices_attr:
                continue

            face_counts = face_counts_attr.Get()
            face_indices = face_indices_attr.Get()

            # Check ray intersection with each face
            hit_result = self._intersect_mesh(
                origin, direction, points, face_counts, face_indices, max_distance
            )

            if hit_result is not None:
                hit_distance = hit_result
                if hit_distance < closest_distance:
                    closest_distance = hit_distance
                    closest_hit = (hit_distance, str(child.GetPath()))

        return closest_hit

    def _intersect_mesh(
        self,
        ray_origin: Gf.Vec3f,
        ray_direction: Gf.Vec3f,
        points: List[Gf.Vec3f],
        face_counts: List[int],
        face_indices: List[int],
        max_distance: float
    ) -> Optional[float]:
        """
        Check if ray intersects with mesh triangles.

        Uses Möller-Trumbore algorithm for ray-triangle intersection.

        Args:
            ray_origin: Ray origin
            ray_direction: Ray direction
            points: Mesh vertex positions
            face_counts: Number of vertices per face
            face_indices: Vertex indices for each face
            max_distance: Maximum ray distance

        Returns:
            Distance to hit point, or None if no intersection
        """
        closest_t = None
        index_offset = 0

        for face_count in face_counts:
            # Get face indices
            face_verts = face_indices[index_offset:index_offset + face_count]
            index_offset += face_count

            # Triangulate face (simple fan triangulation)
            if face_count < 3:
                continue

            # For each triangle in the face
            for i in range(1, face_count - 1):
                v0 = points[face_verts[0]]
                v1 = points[face_verts[i]]
                v2 = points[face_verts[i + 1]]

                # Möller-Trumbore intersection
                t = self._ray_triangle_intersect(ray_origin, ray_direction, v0, v1, v2)

                if t is not None and 0 < t < max_distance:
                    if closest_t is None or t < closest_t:
                        closest_t = t

        return closest_t

    def _ray_triangle_intersect(
        self,
        ray_origin: Gf.Vec3f,
        ray_direction: Gf.Vec3f,
        v0: Gf.Vec3f,
        v1: Gf.Vec3f,
        v2: Gf.Vec3f
    ) -> Optional[float]:
        """
        Ray-triangle intersection using Möller-Trumbore algorithm.

        Args:
            ray_origin: Ray origin
            ray_direction: Ray direction
            v0, v1, v2: Triangle vertices

        Returns:
            Distance along ray to intersection, or None if no intersection
        """
        epsilon = 1e-6

        # Edge vectors
        edge1 = Gf.Vec3f(v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2])
        edge2 = Gf.Vec3f(v2[0] - v0[0], v2[1] - v0[1], v2[2] - v0[2])

        # Cross product: ray_direction × edge2
        h = Gf.Vec3f(
            ray_direction[1] * edge2[2] - ray_direction[2] * edge2[1],
            ray_direction[2] * edge2[0] - ray_direction[0] * edge2[2],
            ray_direction[0] * edge2[1] - ray_direction[1] * edge2[0]
        )

        # Dot product: edge1 · h
        a = edge1[0] * h[0] + edge1[1] * h[1] + edge1[2] * h[2]

        if abs(a) < epsilon:
            return None  # Ray parallel to triangle

        f = 1.0 / a
        s = Gf.Vec3f(
            ray_origin[0] - v0[0],
            ray_origin[1] - v0[1],
            ray_origin[2] - v0[2]
        )

        # Barycentric coordinate u
        u = f * (s[0] * h[0] + s[1] * h[1] + s[2] * h[2])
        if u < 0.0 or u > 1.0:
            return None

        # Cross product: s × edge1
        q = Gf.Vec3f(
            s[1] * edge1[2] - s[2] * edge1[1],
            s[2] * edge1[0] - s[0] * edge1[2],
            s[0] * edge1[1] - s[1] * edge1[0]
        )

        # Barycentric coordinate v
        v = f * (ray_direction[0] * q[0] + ray_direction[1] * q[1] + ray_direction[2] * q[2])
        if v < 0.0 or u + v > 1.0:
            return None

        # Distance along ray
        t = f * (edge2[0] * q[0] + edge2[1] * q[1] + edge2[2] * q[2])

        if t > epsilon:
            return t

        return None

    def analyze_grid(
        self,
        center: Gf.Vec3f,
        grid_size: int,
        grid_spacing: float,
        sun_direction: Gf.Vec3f
    ) -> List[Tuple[Gf.Vec3f, bool]]:
        """
        Analyze shadow coverage over a grid of points.

        Args:
            center: Center point of grid
            grid_size: Number of points per side (e.g., 10 = 10×10 = 100 points)
            grid_spacing: Distance between grid points in meters
            sun_direction: Direction vector from sun

        Returns:
            List of (point, is_shadowed) tuples
        """
        results = []
        half_extent = (grid_size - 1) * grid_spacing / 2.0

        for i in range(grid_size):
            for j in range(grid_size):
                x = center[0] - half_extent + i * grid_spacing
                z = center[2] - half_extent + j * grid_spacing
                point = Gf.Vec3f(x, center[1], z)

                is_shadowed, _ = self.is_point_in_shadow(point, sun_direction)
                results.append((point, is_shadowed))

        shadowed_count = sum(1 for _, shadowed in results if shadowed)
        shadow_percentage = (shadowed_count / len(results)) * 100

        carb.log_info(
            f"[ShadowAnalyzer] Grid analysis: {shadowed_count}/{len(results)} "
            f"points in shadow ({shadow_percentage:.1f}%)"
        )

        return results
