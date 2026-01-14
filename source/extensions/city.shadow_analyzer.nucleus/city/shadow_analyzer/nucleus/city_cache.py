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

    def save_to_cache(
        self,
        latitude: float,
        longitude: float,
        radius: float,
        stage: Usd.Stage,
        metadata: Dict
    ) -> Tuple[bool, Optional[str]]:
        """
        Save city building data to Nucleus cache.

        Args:
            latitude: Center latitude
            longitude: Center longitude
            radius: Radius in kilometers
            stage: USD stage containing building geometry
            metadata: Dictionary with cache metadata (building_count, bounds, etc.)

        Returns:
            Tuple of (success: bool, nucleus_path: Optional[str])
        """
        if not self._nucleus_manager.is_connected():
            carb.log_warn("[CityCacheManager] Not connected to Nucleus, cannot cache")
            return False, None

        try:
            city_name, bounds_hash = self.generate_cache_key(latitude, longitude, radius)

            # Export stage to USD string
            import tempfile
            import os
            
            # Create temporary file
            temp_fd, temp_path = tempfile.mkstemp(suffix='.usd')
            os.close(temp_fd)
            
            try:
                # Export stage to temporary file
                stage.Export(temp_path)
                
                # Read file content
                with open(temp_path, 'r', encoding='utf-8') as f:
                    usd_content = f.read()
                
                # Add cache metadata
                cache_metadata = {
                    'latitude': latitude,
                    'longitude': longitude,
                    'radius_km': radius,
                    'building_count': metadata.get('building_count', 0),
                    'road_count': metadata.get('road_count', 0),
                    'bounds': metadata.get('bounds', {}),
                    'data_source': 'OpenStreetMap',
                    'cache_key': f"{city_name}/{bounds_hash}"
                }
                
                # Save to Nucleus
                success, nucleus_path = self._nucleus_manager.save_buildings_to_nucleus(
                    city_name,
                    bounds_hash,
                    usd_content,
                    cache_metadata
                )
                
                if success:
                    carb.log_info(f"[CityCacheManager] Successfully cached to: {nucleus_path}")
                else:
                    carb.log_error(f"[CityCacheManager] Failed to cache data")
                
                return success, nucleus_path
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.remove(temp_path)

        except Exception as e:
            carb.log_error(f"[CityCacheManager] Error saving to cache: {e}")
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
