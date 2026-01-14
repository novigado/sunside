"""Terrain elevation data loader using Open-Elevation API."""

import carb
import requests
from typing import List, Tuple, Optional
import numpy as np


class TerrainLoader:
    """Loads terrain elevation data from Open-Elevation API."""

    def __init__(self):
        """Initialize the terrain loader."""
        self.api_url = "https://api.open-elevation.com/api/v1/lookup"
        self._cache = {}  # Simple in-memory cache

    def load_elevation_grid(
        self,
        center_lat: float,
        center_lon: float,
        radius_m: float = 500.0,
        grid_resolution: int = 20
    ) -> Optional[Tuple[np.ndarray, float, float]]:
        """
        Load elevation data in a grid around a center point.

        Args:
            center_lat: Center latitude
            center_lon: Center longitude
            radius_m: Radius in meters (default 500m to match building data)
            grid_resolution: Number of sample points per side (e.g., 20 = 20x20 = 400 points)

        Returns:
            Tuple of (elevation_grid, lat_spacing, lon_spacing):
                - elevation_grid: 2D numpy array of elevations in meters
                - lat_spacing: Degrees per grid cell in latitude
                - lon_spacing: Degrees per grid cell in longitude
            Returns None if request fails.
        """
        carb.log_info(f"[TerrainLoader] Loading elevation grid at ({center_lat}, {center_lon})")
        carb.log_info(f"[TerrainLoader] Grid: {grid_resolution}x{grid_resolution}, radius: {radius_m}m")

        # Check cache
        cache_key = f"{center_lat:.5f},{center_lon:.5f},{radius_m},{grid_resolution}"
        if cache_key in self._cache:
            carb.log_info(f"[TerrainLoader] Using cached elevation data")
            return self._cache[cache_key]

        try:
            # Convert radius from meters to degrees (approximate)
            # At equator: 1 degree latitude ≈ 111,000 meters
            # Longitude varies by latitude
            import math
            lat_degrees = radius_m / 111000.0
            lon_degrees = radius_m / (111000.0 * math.cos(math.radians(center_lat)))

            # Create grid of lat/lon points
            locations = []
            lat_min = center_lat - lat_degrees
            lat_max = center_lat + lat_degrees
            lon_min = center_lon - lon_degrees
            lon_max = center_lon + lon_degrees

            lat_spacing = (lat_max - lat_min) / (grid_resolution - 1)
            lon_spacing = (lon_max - lon_min) / (grid_resolution - 1)

            for i in range(grid_resolution):
                for j in range(grid_resolution):
                    lat = lat_min + i * lat_spacing
                    lon = lon_min + j * lon_spacing
                    locations.append({"latitude": lat, "longitude": lon})

            carb.log_info(f"[TerrainLoader] Querying {len(locations)} elevation points...")

            # Query Open-Elevation API
            # Note: API has rate limits, so we may need to batch large requests
            response = requests.post(
                self.api_url,
                json={"locations": locations},
                timeout=30
            )
            response.raise_for_status()

            data = response.json()
            results = data.get("results", [])

            if len(results) != len(locations):
                carb.log_error(f"[TerrainLoader] Expected {len(locations)} results, got {len(results)}")
                return None

            # Convert to 2D elevation grid
            elevation_grid = np.zeros((grid_resolution, grid_resolution))
            for idx, result in enumerate(results):
                i = idx // grid_resolution
                j = idx % grid_resolution
                elevation_grid[i, j] = result.get("elevation", 0.0)

            carb.log_info(f"[TerrainLoader] Elevation range: {elevation_grid.min():.1f}m to {elevation_grid.max():.1f}m")

            # Cache the result
            result_tuple = (elevation_grid, lat_spacing, lon_spacing)
            self._cache[cache_key] = result_tuple

            return result_tuple

        except requests.exceptions.RequestException as e:
            carb.log_error(f"[TerrainLoader] Error fetching elevation data: {e}")
            return None
        except Exception as e:
            carb.log_error(f"[TerrainLoader] Error processing elevation data: {e}")
            import traceback
            carb.log_error(f"[TerrainLoader] Traceback: {traceback.format_exc()}")
            return None

    def get_elevation_at_point(
        self,
        latitude: float,
        longitude: float
    ) -> Optional[float]:
        """
        Get elevation at a single point.

        Args:
            latitude: Latitude
            longitude: Longitude

        Returns:
            Elevation in meters, or None if request fails
        """
        try:
            response = requests.post(
                self.api_url,
                json={"locations": [{"latitude": latitude, "longitude": longitude}]},
                timeout=10
            )
            response.raise_for_status()

            data = response.json()
            results = data.get("results", [])

            if len(results) > 0:
                elevation = results[0].get("elevation", 0.0)
                carb.log_info(f"[TerrainLoader] Elevation at ({latitude}, {longitude}): {elevation:.1f}m")
                return elevation

            return None

        except Exception as e:
            carb.log_error(f"[TerrainLoader] Error fetching single point elevation: {e}")
            return None
