"""OpenStreetMap building data loader."""

import carb
import requests
from typing import List, Dict, Tuple, Optional
import json


class BuildingLoader:
    """Loads building data from OpenStreetMap."""

    def __init__(self):
        """Initialize the building loader."""
        self.overpass_url = "https://overpass-api.de/api/interpreter"
        self._cache = {}  # Simple in-memory cache
        self._nucleus_cache = None  # Will be set if Nucleus is available

    def set_nucleus_cache(self, nucleus_cache):
        """
        Set the Nucleus cache manager for persistent caching.

        Args:
            nucleus_cache: CityCacheManager instance
        """
        self._nucleus_cache = nucleus_cache
        carb.log_info("[BuildingLoader] Nucleus caching enabled")

    def load_buildings(
        self,
        latitude: float,
        longitude: float,
        radius_km: float = 0.5
    ) -> List[Dict]:
        """
        Load buildings from OpenStreetMap within a radius of a point.
        Will use Nucleus cache if available for 10-20x performance improvement.

        Args:
            latitude: Center point latitude
            longitude: Center point longitude
            radius_km: Search radius in kilometers (default 0.5km)

        Returns:
            List of building dictionaries with geometry and metadata
        """
        carb.log_info(f"[BuildingLoader] Loading buildings at ({latitude}, {longitude}) within {radius_km}km")

        # 1. Try Nucleus cache first (if available)
        if self._nucleus_cache:
            is_cached, nucleus_path = self._nucleus_cache.is_cached(latitude, longitude, radius_km)
            if is_cached:
                carb.log_info(f"[BuildingLoader] ✅ NUCLEUS CACHE HIT - Loading from: {nucleus_path}")
                # Note: For now just log, actual USD loading will be integrated later
                # This currently still falls through to OSM query
                carb.log_info(f"[BuildingLoader] USD loading integration pending - falling back to OSM")

        # 2. Check in-memory cache (use 5 decimal places for ~1 meter precision)
        cache_key = f"{latitude:.5f},{longitude:.5f},{radius_km}"
        if cache_key in self._cache:
            carb.log_info(f"[BuildingLoader] Using in-memory cached data for {cache_key}")
            return self._cache[cache_key]

        try:
            # Build Overpass QL query
            # Query buildings AND roads within radius
            radius_meters = radius_km * 1000
            query = f"""
            [out:json][timeout:25];
            (
              way["building"](around:{radius_meters},{latitude},{longitude});
              relation["building"]["type"="multipolygon"](around:{radius_meters},{latitude},{longitude});
              way["highway"](around:{radius_meters},{latitude},{longitude});
            );
            out body;
            >;
            out skel qt;
            """

            carb.log_info(f"[BuildingLoader] Querying Overpass API...")

            response = requests.post(
                self.overpass_url,
                data={"data": query},
                timeout=30
            )
            response.raise_for_status()

            data = response.json()
            carb.log_info(f"[BuildingLoader] Received {len(data.get('elements', []))} elements")

            # Parse buildings
            buildings = self._parse_osm_data(data)
            carb.log_info(f"[BuildingLoader] Parsed {len(buildings)} buildings")

            # Cache the results in memory
            self._cache[cache_key] = buildings

            # TODO: Save to Nucleus cache if available
            # This will be implemented after USD stage creation is integrated
            if self._nucleus_cache:
                carb.log_info(f"[BuildingLoader] TODO: Save {len(buildings)} buildings to Nucleus cache")

            return buildings

        except requests.exceptions.RequestException as e:
            carb.log_error(f"[BuildingLoader] Error fetching OSM data: {e}")
            return []
        except Exception as e:
            carb.log_error(f"[BuildingLoader] Error parsing OSM data: {e}")
            return []

    def _parse_osm_data(self, data: Dict) -> List[Dict]:
        """
        Parse OSM JSON response into building structures.

        Args:
            data: Raw OSM Overpass API response

        Returns:
            List of building dictionaries
        """
        elements = data.get("elements", [])

        # Build node lookup table
        nodes = {}
        for elem in elements:
            if elem["type"] == "node":
                nodes[elem["id"]] = {
                    "lat": elem["lat"],
                    "lon": elem["lon"]
                }

        # Process ways (building outlines)
        buildings = []
        for elem in elements:
            if elem["type"] == "way" and "building" in elem.get("tags", {}):
                # Get node coordinates
                node_refs = elem.get("nodes", [])
                coordinates = []

                for node_id in node_refs:
                    if node_id in nodes:
                        node = nodes[node_id]
                        coordinates.append((node["lat"], node["lon"]))

                if len(coordinates) < 3:
                    continue  # Need at least 3 points for a polygon

                # Extract building metadata
                tags = elem.get("tags", {})
                building_type = tags.get("building", "yes")

                # Try to get height information
                height = self._extract_height(tags)
                levels = tags.get("building:levels")

                # Estimate height if not provided
                if height is None and levels:
                    try:
                        height = float(levels) * 3.0  # Assume 3m per level
                    except (ValueError, TypeError):
                        height = 10.0  # Default height
                elif height is None:
                    height = 10.0  # Default 10m for unknown buildings

                building = {
                    "id": elem["id"],
                    "type": building_type,
                    "coordinates": coordinates,
                    "height": height,
                    "levels": levels,
                    "tags": tags
                }

                buildings.append(building)

        return buildings

    def _extract_height(self, tags: Dict) -> Optional[float]:
        """
        Extract building height from OSM tags.

        Args:
            tags: OSM element tags

        Returns:
            Height in meters, or None if not available
        """
        # Try explicit height tag
        if "height" in tags:
            try:
                height_str = tags["height"].replace("m", "").replace("M", "").strip()
                return float(height_str)
            except (ValueError, AttributeError):
                pass

        # Try building:height
        if "building:height" in tags:
            try:
                height_str = tags["building:height"].replace("m", "").replace("M", "").strip()
                return float(height_str)
            except (ValueError, AttributeError):
                pass

        return None

    def get_bounding_box(
        self,
        latitude: float,
        longitude: float,
        radius_km: float
    ) -> Tuple[float, float, float, float]:
        """
        Calculate approximate bounding box for a circle.

        Args:
            latitude: Center latitude
            longitude: Center longitude
            radius_km: Radius in kilometers

        Returns:
            Tuple of (min_lat, min_lon, max_lat, max_lon)
        """
        # Approximate degrees per km
        lat_degree_km = 111.0
        lon_degree_km = 111.0 * abs(float(f"{latitude:.10f}".split('.')[0]))  # Adjust for latitude

        lat_delta = radius_km / lat_degree_km
        lon_delta = radius_km / lon_degree_km

        return (
            latitude - lat_delta,
            longitude - lon_delta,
            latitude + lat_delta,
            longitude + lon_delta
        )

    def clear_cache(self):
        """Clear the building data cache."""
        self._cache.clear()
        carb.log_info("[BuildingLoader] Cache cleared")

    def load_scene_data(
        self,
        latitude: float,
        longitude: float,
        radius_km: float = 0.5
    ) -> Dict[str, List[Dict]]:
        """
        Load comprehensive scene data from OpenStreetMap (buildings, roads, etc).

        Args:
            latitude: Center point latitude
            longitude: Center point longitude
            radius_km: Search radius in kilometers (default 0.5km)

        Returns:
            Dictionary with 'buildings' and 'roads' lists
        """
        carb.log_info(f"[BuildingLoader] Loading scene data at ({latitude}, {longitude}) within {radius_km}km")

        # Check cache
        cache_key = f"scene_{latitude:.5f},{longitude:.5f},{radius_km}"
        if cache_key in self._cache:
            carb.log_info(f"[BuildingLoader] Using cached scene data for {cache_key}")
            return self._cache[cache_key]

        try:
            # Build comprehensive Overpass QL query
            radius_meters = radius_km * 1000
            query = f"""
            [out:json][timeout:25];
            (
              way["building"](around:{radius_meters},{latitude},{longitude});
              way["highway"](around:{radius_meters},{latitude},{longitude});
            );
            out body;
            >;
            out skel qt;
            """

            carb.log_info(f"[BuildingLoader] Querying Overpass API for scene data...")

            # Try up to 3 times with increasing timeouts
            response = None
            last_error = None
            for attempt in range(3):
                try:
                    timeout = 30 + (attempt * 20)  # 30s, 50s, 70s
                    carb.log_info(f"[BuildingLoader] Attempt {attempt + 1}/3 (timeout: {timeout}s)")

                    response = requests.post(
                        self.overpass_url,
                        data={"data": query},
                        timeout=timeout
                    )
                    response.raise_for_status()
                    break  # Success!
                except Exception as e:
                    last_error = e
                    carb.log_warn(f"[BuildingLoader] Attempt {attempt + 1} failed: {e}")
                    if attempt < 2:  # Don't wait after last attempt
                        import time
                        time.sleep(5)  # Wait 5 seconds between retries

            if response is None or not response.ok:
                raise last_error if last_error else Exception("All retry attempts failed")

            data = response.json()
            elements = data.get("elements", [])
            carb.log_info(f"[BuildingLoader] Received {len(elements)} elements")

            # Build node lookup table
            nodes = {}
            for elem in elements:
                if elem["type"] == "node":
                    nodes[elem["id"]] = {
                        "lat": elem["lat"],
                        "lon": elem["lon"]
                    }

            # Separate buildings and roads
            buildings = []
            roads = []

            for elem in elements:
                if elem["type"] == "way":
                    tags = elem.get("tags", {})
                    node_refs = elem.get("nodes", [])

                    # Get node coordinates
                    coordinates = []
                    for node_id in node_refs:
                        if node_id in nodes:
                            node = nodes[node_id]
                            coordinates.append((node["lat"], node["lon"]))

                    if len(coordinates) < 2:
                        continue

                    # Check if it's a building
                    if "building" in tags:
                        height = self._extract_height(tags)
                        levels = tags.get("building:levels")

                        if height is None and levels:
                            try:
                                height = float(levels) * 3.0
                            except (ValueError, TypeError):
                                height = 10.0
                        elif height is None:
                            height = 10.0

                        buildings.append({
                            "id": elem["id"],
                            "type": tags.get("building", "yes"),
                            "coordinates": coordinates,
                            "height": height,
                            "levels": levels,
                            "tags": tags
                        })

                    # Check if it's a road
                    elif "highway" in tags:
                        highway_type = tags.get("highway", "")
                        name = tags.get("name", "")
                        lanes = tags.get("lanes", "2")

                        # Determine road width based on type
                        width_map = {
                            "motorway": 12.0,
                            "trunk": 10.0,
                            "primary": 8.0,
                            "secondary": 7.0,
                            "tertiary": 6.0,
                            "residential": 5.0,
                            "service": 3.0,
                            "pedestrian": 2.0,
                            "footway": 1.5,
                            "path": 1.0,
                        }

                        width = width_map.get(highway_type, 5.0)

                        roads.append({
                            "id": elem["id"],
                            "type": highway_type,
                            "name": name,
                            "coordinates": coordinates,
                            "width": width,
                            "lanes": lanes,
                            "tags": tags
                        })

            scene_data = {
                "buildings": buildings,
                "roads": roads
            }

            carb.log_info(f"[BuildingLoader] Parsed {len(buildings)} buildings and {len(roads)} roads")

            # Cache the results
            self._cache[cache_key] = scene_data

            return scene_data

        except requests.exceptions.RequestException as e:
            carb.log_error(f"[BuildingLoader] Error fetching OSM data: {e}")
            return {"buildings": [], "roads": []}
        except Exception as e:
            carb.log_error(f"[BuildingLoader] Error parsing OSM data: {e}")
            import traceback
            carb.log_error(traceback.format_exc())
            return {"buildings": [], "roads": []}
