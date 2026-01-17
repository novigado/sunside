"""
City Cache Manager

Handles intelligent caching of city building data on Nucleus server.
Provides transparent fallback to OpenStreetMap when cache misses occur.
"""

import hashlib
import carb
from typing import Optional, Tuple, List, Dict
from pxr import Usd, UsdGeom
from .nucleus_manager import NucleusManager


class CityCacheManager:
    """Manages city building data caching on Nucleus."""

    def __init__(self, nucleus_manager: NucleusManager):
        """
        Initialize the city cache manager.

        Args:
            nucleus_manager: NucleusManager instance for Nucleus operations
        """
        self._nucleus_manager = nucleus_manager
        carb.log_info("[CityCacheManager] Initialized")

    def generate_cache_key(
        self,
        latitude: float,
        longitude: float,
        radius: float
    ) -> Tuple[str, str]:
        """
        Generate cache key for a geographic area.

        Args:
            latitude: Center latitude
            longitude: Center longitude
            radius: Radius in kilometers

        Returns:
            Tuple of (city_name, bounds_hash)
        """
        # Generate city name from coordinates (simplified)
        # In production, could use reverse geocoding
        city_name = f"city_{abs(int(latitude))}N_{abs(int(longitude))}W"

        # Generate unique hash for exact bounds
        bounds_str = f"{latitude:.6f},{longitude:.6f},{radius:.3f}"
        bounds_hash = hashlib.md5(bounds_str.encode()).hexdigest()[:12]

        return city_name, bounds_hash

    def is_cached(
        self,
        latitude: float,
        longitude: float,
        radius: float
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if city data is cached on Nucleus.

        Args:
            latitude: Center latitude
            longitude: Center longitude
            radius: Radius in kilometers

        Returns:
            Tuple of (is_cached: bool, nucleus_path: Optional[str])
        """
        if not self._nucleus_manager.is_connected():
            return False, None

        city_name, bounds_hash = self.generate_cache_key(latitude, longitude, radius)
        return self._nucleus_manager.check_buildings_cache(city_name, bounds_hash)

    def load_from_cache(
        self,
        latitude: float,
        longitude: float,
        radius: float
    ) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """
        Load city building data from Nucleus cache.

        Args:
            latitude: Center latitude
            longitude: Center longitude
            radius: Radius in kilometers

        Returns:
            Tuple of (success: bool, nucleus_path: Optional[str], metadata: Optional[Dict])
        """
        is_cached, nucleus_path = self.is_cached(latitude, longitude, radius)

        if not is_cached:
            carb.log_info(f"[CityCacheManager] Cache miss for ({latitude}, {longitude})")
            return False, None, None

        city_name, bounds_hash = self.generate_cache_key(latitude, longitude, radius)

        # Get metadata
        metadata = self._nucleus_manager.get_metadata(city_name, bounds_hash)

        carb.log_info(f"[CityCacheManager] Cache HIT for ({latitude}, {longitude})")
        carb.log_info(f"[CityCacheManager] Loading from: {nucleus_path}")

        if metadata:
            carb.log_info(f"[CityCacheManager] Cached data from: {metadata.get('saved_at', 'unknown')}")
            carb.log_info(f"[CityCacheManager] Contains {metadata.get('building_count', 0)} buildings")

        return True, nucleus_path, metadata

    def load_usd_from_cache(
        self,
        latitude: float,
        longitude: float,
        radius: float
    ) -> Tuple[bool, Optional[Usd.Stage], Optional[Dict]]:
        """
        Load USD stage directly from Nucleus cache.

        Args:
            latitude: Center latitude
            longitude: Center longitude
            radius: Radius in kilometers

        Returns:
            Tuple of (success: bool, stage: Optional[Usd.Stage], metadata: Optional[Dict])
        """
        is_cached, nucleus_path = self.is_cached(latitude, longitude, radius)

        if not is_cached:
            carb.log_info(f"[CityCacheManager] Cache miss for ({latitude}, {longitude})")
            return False, None, None

        try:
            city_name, bounds_hash = self.generate_cache_key(latitude, longitude, radius)

            # Load USD content from Nucleus
            success, usd_content = self._nucleus_manager.load_buildings_from_nucleus(city_name, bounds_hash)

            if not success or not usd_content:
                carb.log_error(f"[CityCacheManager] Failed to load USD content from Nucleus")
                return False, None, None

            # Deserialize USD content to stage
            stage = self._deserialize_usd_stage(usd_content)

            if not stage:
                carb.log_error(f"[CityCacheManager] Failed to deserialize USD stage")
                return False, None, None

            # Get metadata
            metadata = self._nucleus_manager.get_metadata(city_name, bounds_hash)

            carb.log_info(f"[CityCacheManager] Successfully loaded USD stage from cache")
            if metadata:
                carb.log_info(f"[CityCacheManager] Contains {metadata.get('building_count', 0)} buildings")

            return True, stage, metadata

        except Exception as e:
            carb.log_error(f"[CityCacheManager] Error loading from cache: {e}")
            import traceback
            carb.log_error(traceback.format_exc())
            return False, None, None

    def save_to_cache(
        self,
        latitude: float,
        longitude: float,
        radius: float,
        stage: Usd.Stage,
        metadata: Dict
    ) -> Tuple[bool, Optional[str]]:
        """
        Save building/scene data to Nucleus cache.

        Args:
            latitude: Center latitude
            longitude: Center longitude
            radius: Radius in kilometers
            stage: USD stage containing scene geometry (buildings, roads, ground)
            metadata: Dictionary with cache metadata (building_count, road_count, bounds, etc.)

        Returns:
            Tuple of (success: bool, nucleus_path: Optional[str])
        """
        if not self._nucleus_manager.is_connected():
            carb.log_warn("[CityCacheManager] Not connected to Nucleus, cannot cache buildings")
            return False, None

        try:
            city_name, bounds_hash = self.generate_cache_key(latitude, longitude, radius)

            # Export stage to USD file
            import tempfile
            import os

            temp_fd, temp_path = tempfile.mkstemp(suffix='.usd')
            os.close(temp_fd)

            try:
                # Export stage to temporary file
                stage.Export(temp_path)

                # Read file content as binary (USD can be binary format)
                with open(temp_path, 'rb') as f:
                    usd_content = f.read()

                # Add cache metadata
                cache_metadata = {
                    'latitude': latitude,
                    'longitude': longitude,
                    'radius_km': radius,
                    'building_count': metadata.get('building_count', 0),
                    'road_count': metadata.get('road_count', 0),
                    'bounds': metadata.get('bounds', {}),
                    'data_source': metadata.get('data_source', 'OpenStreetMap'),
                    'cache_key': f"{city_name}/{bounds_hash}"
                }

                # Save to Nucleus (handles both binary and text USD formats)
                success, nucleus_path = self._nucleus_manager.save_buildings_to_nucleus(
                    city_name,
                    bounds_hash,
                    usd_content,  # Pass bytes directly
                    cache_metadata
                )

                if success:
                    carb.log_info(f"[CityCacheManager] Successfully cached buildings to: {nucleus_path}")
                else:
                    carb.log_error(f"[CityCacheManager] Failed to cache building data")

                return success, nucleus_path

            finally:
                # Clean up temporary file
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except:
                        pass  # Ignore cleanup errors

        except Exception as e:
            carb.log_error(f"[CityCacheManager] Error saving buildings to cache: {e}")
            import traceback
            carb.log_error(traceback.format_exc())
            return False, None

    def _deserialize_usd_stage(self, usd_content) -> Optional[Usd.Stage]:
        """
        Deserialize USD content to USD stage.

        Args:
            usd_content: USD file content as string or bytes

        Returns:
            USD Stage or None if deserialization fails
        """
        import tempfile
        import os

        temp_fd, temp_path = tempfile.mkstemp(suffix='.usd')

        try:
            # Write content to temp file
            os.close(temp_fd)

            # Handle multiple content types:
            # - bytes: binary USD data
            # - str: text USD data
            # - omni.client Content object: can be used as bytes
            if isinstance(usd_content, str):
                # Text format
                with open(temp_path, 'w', encoding='utf-8') as f:
                    f.write(usd_content)
            else:
                # Binary format or Content object - write as binary
                with open(temp_path, 'wb') as f:
                    f.write(usd_content)

            # Open stage from temp file
            stage = Usd.Stage.Open(temp_path)

            return stage

        except Exception as e:
            carb.log_error(f"[CityCacheManager] Error deserializing USD: {e}")
            return None

        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass  # Ignore cleanup errors

    def generate_terrain_cache_key(
        self,
        latitude: float,
        longitude: float,
        radius: float,
        resolution: int
    ) -> Tuple[str, str]:
        """
        Generate cache key for terrain data (includes resolution).

        Args:
            latitude: Center latitude
            longitude: Center longitude
            radius: Radius in kilometers
            resolution: Resolution in meters

        Returns:
            Tuple of (city_name, bounds_hash)
        """
        city_name = f"city_{abs(int(latitude))}N_{abs(int(longitude))}W"

        # Include resolution in hash for terrain
        bounds_str = f"{latitude:.6f},{longitude:.6f},{radius:.3f},res{resolution}"
        bounds_hash = hashlib.md5(bounds_str.encode()).hexdigest()[:12]

        return city_name, bounds_hash

    def is_terrain_cached(
        self,
        latitude: float,
        longitude: float,
        radius: float,
        resolution: int
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if terrain data is cached on Nucleus.

        Args:
            latitude: Center latitude
            longitude: Center longitude
            radius: Radius in kilometers
            resolution: Resolution in meters

        Returns:
            Tuple of (is_cached: bool, nucleus_path: Optional[str])
        """
        if not self._nucleus_manager.is_connected():
            return False, None

        city_name, bounds_hash = self.generate_terrain_cache_key(latitude, longitude, radius, resolution)
        return self._nucleus_manager.check_terrain_cache(city_name, bounds_hash)

    def load_terrain_from_cache(
        self,
        latitude: float,
        longitude: float,
        radius: float,
        resolution: int
    ) -> Tuple[bool, Optional[Usd.Stage], Optional[Dict]]:
        """
        Load terrain USD stage from Nucleus cache.

        Args:
            latitude: Center latitude
            longitude: Center longitude
            radius: Radius in kilometers
            resolution: Resolution in meters

        Returns:
            Tuple of (success: bool, stage: Optional[Usd.Stage], metadata: Optional[Dict])
        """
        is_cached, nucleus_path = self.is_terrain_cached(latitude, longitude, radius, resolution)

        if not is_cached:
            carb.log_info(f"[CityCacheManager] Terrain cache miss for ({latitude}, {longitude}) res={resolution}m")
            return False, None, None

        try:
            city_name, bounds_hash = self.generate_terrain_cache_key(latitude, longitude, radius, resolution)

            # Load USD content from Nucleus
            success, usd_content = self._nucleus_manager.load_terrain_from_nucleus(city_name, bounds_hash)

            if not success or not usd_content:
                carb.log_error(f"[CityCacheManager] Failed to load terrain USD from Nucleus")
                return False, None, None

            # Deserialize USD content to stage
            stage = self._deserialize_usd_stage(usd_content)

            if not stage:
                carb.log_error(f"[CityCacheManager] Failed to deserialize terrain USD")
                return False, None, None

            # Get metadata
            metadata = self._nucleus_manager.get_terrain_metadata(city_name, bounds_hash)

            carb.log_info(f"[CityCacheManager] Terrain cache HIT - loaded from Nucleus")
            if metadata:
                carb.log_info(f"[CityCacheManager] Resolution: {metadata.get('resolution_meters', resolution)}m")

            return True, stage, metadata

        except Exception as e:
            carb.log_error(f"[CityCacheManager] Error loading terrain from cache: {e}")
            import traceback
            carb.log_error(traceback.format_exc())
            return False, None, None

    def save_terrain_to_cache(
        self,
        latitude: float,
        longitude: float,
        radius: float,
        resolution: int,
        stage: Usd.Stage,
        metadata: Dict
    ) -> Tuple[bool, Optional[str]]:
        """
        Save terrain data to Nucleus cache.

        Args:
            latitude: Center latitude
            longitude: Center longitude
            radius: Radius in kilometers
            resolution: Resolution in meters
            stage: USD stage containing terrain geometry
            metadata: Dictionary with cache metadata (resolution, bounds, etc.)

        Returns:
            Tuple of (success: bool, nucleus_path: Optional[str])
        """
        if not self._nucleus_manager.is_connected():
            carb.log_warn("[CityCacheManager] Not connected to Nucleus, cannot cache terrain")
            return False, None

        try:
            city_name, bounds_hash = self.generate_terrain_cache_key(latitude, longitude, radius, resolution)

            # Export stage to USD string
            import tempfile
            import os

            temp_fd, temp_path = tempfile.mkstemp(suffix='.usd')
            os.close(temp_fd)

            try:
                # Export stage to temporary file
                stage.Export(temp_path)

                # Read file content as binary (USD can be binary format)
                with open(temp_path, 'rb') as f:
                    usd_content = f.read()

                # Add cache metadata
                cache_metadata = {
                    'latitude': latitude,
                    'longitude': longitude,
                    'radius_km': radius,
                    'resolution_meters': resolution,
                    'bounds': metadata.get('bounds', {}),
                    'data_source': metadata.get('data_source', 'OpenTopography'),
                    'cache_key': f"{city_name}/terrain_{bounds_hash}"
                }

                # Save to Nucleus
                success, nucleus_path = self._nucleus_manager.save_terrain_to_nucleus(
                    city_name,
                    bounds_hash,
                    usd_content,
                    cache_metadata
                )

                if success:
                    carb.log_info(f"[CityCacheManager] Successfully cached terrain to: {nucleus_path}")
                else:
                    carb.log_error(f"[CityCacheManager] Failed to cache terrain data")

                return success, nucleus_path

            finally:
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.remove(temp_path)

        except Exception as e:
            carb.log_error(f"[CityCacheManager] Error saving terrain to cache: {e}")
            import traceback
            carb.log_error(traceback.format_exc())
            return False, None

    def list_cached_cities(self) -> List[str]:
        """
        List all cached cities on Nucleus.

        Returns:
            List[str]: List of city names
        """
        return self._nucleus_manager.list_cached_cities()

    def get_cache_stats(self) -> Dict:
        """
        Get statistics about the cache.

        Returns:
            Dict with cache statistics
        """
        if not self._nucleus_manager.is_connected():
            return {
                'connected': False,
                'cities_cached': 0
            }

        cities = self.list_cached_cities()

        return {
            'connected': True,
            'nucleus_server': self._nucleus_manager.get_nucleus_server(),
            'base_path': self._nucleus_manager.get_base_path(),
            'cities_cached': len(cities),
            'cached_cities': cities
        }
