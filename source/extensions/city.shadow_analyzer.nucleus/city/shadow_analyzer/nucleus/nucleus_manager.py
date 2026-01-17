"""
Nucleus Manager

Handles all interactions with Omniverse Nucleus server including:
- Connection management
- Building data caching
- Results storage
- Collaborative access
"""

import omni.client
import carb
from typing import Optional, Tuple, List, Dict
from datetime import datetime
import json


class NucleusManager:
    """Manages Nucleus server connections and USD file operations."""

    def __init__(self):
        """Initialize the Nucleus manager."""
        self._settings = carb.settings.get_settings()

        # Get Nucleus server from settings or use default
        self._nucleus_server = self._settings.get_as_string(
            "exts/city.shadow_analyzer.nucleus/nucleus_server"
        ) or "omniverse://localhost"

        self._project_path = self._settings.get_as_string(
            "exts/city.shadow_analyzer.nucleus/project_path"
        ) or "/Projects/CityData"

        # Full base path for city data
        self._base_path = f"{self._nucleus_server}{self._project_path}"

        carb.log_info(f"[NucleusManager] Configured for Nucleus server: {self._nucleus_server}")
        carb.log_info(f"[NucleusManager] Base path: {self._base_path}")

        # Disable authentication popup for headless/service mode (if available)
        try:
            if hasattr(omni.client, 'set_authentication_message_box_enabled'):
                omni.client.set_authentication_message_box_enabled(False)
        except Exception as e:
            carb.log_warn(f"[NucleusManager] Could not disable auth popup: {e}")

        # Set up token-based authentication
        self._setup_authentication()

        self._connected = False

    def _setup_authentication(self):
        """Set up authentication for Nucleus connection."""
        username = self._settings.get_as_string("exts/city.shadow_analyzer.nucleus/username") or ""
        password = self._settings.get_as_string("exts/city.shadow_analyzer.nucleus/password") or ""

        if username and password:
            carb.log_info(f"[NucleusManager] Setting up authentication callback for user: {username}")

            # Register authentication callback - this is the standard way
            def auth_callback(url: str):
                # Return credentials as tuple
                return (username, password)

            try:
                omni.client.register_authentication_callback(auth_callback)
                carb.log_info("[NucleusManager] Authentication callback registered")
            except Exception as e:
                carb.log_error(f"[NucleusManager] Failed to register auth callback: {e}")
        else:
            carb.log_info("[NucleusManager] No credentials configured, attempting anonymous access")

    @property
    def nucleus_server(self) -> str:
        """Get the Nucleus server URL."""
        return self._nucleus_server

    @property
    def project_path(self) -> str:
        """Get the project path on Nucleus."""
        return self._project_path

    @property
    def base_path(self) -> str:
        """Get the full base path (server + project path)."""
        return self._base_path

    def check_connection(self) -> bool:
        """
        Check if we can connect to the Nucleus server.

        Returns:
            bool: True if connected, False otherwise
        """
        try:
            result, _ = omni.client.stat(self._nucleus_server)
            self._connected = (result == omni.client.Result.OK)

            if self._connected:
                carb.log_info(f"[NucleusManager] Successfully connected to {self._nucleus_server}")
                # Ensure project path exists
                self._ensure_directory(self._base_path)
            else:
                carb.log_warn(f"[NucleusManager] Cannot connect to {self._nucleus_server}: {result}")

            return self._connected
        except Exception as e:
            carb.log_error(f"[NucleusManager] Error checking connection: {e}")
            return False

    def _ensure_directory(self, path: str) -> bool:
        """
        Ensure a directory exists on Nucleus, create if it doesn't.

        Args:
            path: Full Nucleus path to directory

        Returns:
            bool: True if directory exists or was created
        """
        result, _ = omni.client.stat(path)

        if result == omni.client.Result.OK:
            return True
        elif result == omni.client.Result.ERROR_NOT_FOUND:
            # Create directory
            result = omni.client.create_folder(path)
            if result == omni.client.Result.OK:
                carb.log_info(f"[NucleusManager] Created directory: {path}")
                return True
            else:
                carb.log_error(f"[NucleusManager] Failed to create directory {path}: {result}")
                return False
        else:
            carb.log_error(f"[NucleusManager] Error checking directory {path}: {result}")
            return False

    def get_city_data_path(self, city_name: str) -> str:
        """
        Get the Nucleus path for a city's data.

        Args:
            city_name: Name of the city (e.g., "manhattan", "brooklyn")

        Returns:
            str: Full Nucleus path to city directory
        """
        return f"{self._base_path}/{city_name}"

    def get_buildings_usd_path(self, city_name: str, bounds_hash: str) -> str:
        """
        Get the Nucleus path for cached building USD file.

        Args:
            city_name: Name of the city
            bounds_hash: Hash of the geographic bounds (for unique identification)

        Returns:
            str: Full Nucleus path to buildings USD file
        """
        city_path = self.get_city_data_path(city_name)
        return f"{city_path}/buildings_{bounds_hash}.usd"

    def check_buildings_cache(self, city_name: str, bounds_hash: str) -> Tuple[bool, Optional[str]]:
        """
        Check if building data is cached on Nucleus.

        Args:
            city_name: Name of the city
            bounds_hash: Hash of the geographic bounds

        Returns:
            Tuple of (exists: bool, path: Optional[str])
        """
        if not self._connected:
            return False, None

        usd_path = self.get_buildings_usd_path(city_name, bounds_hash)
        result, _ = omni.client.stat(usd_path)

        if result == omni.client.Result.OK:
            carb.log_info(f"[NucleusManager] Found cached buildings at: {usd_path}")
            return True, usd_path
        else:
            carb.log_info(f"[NucleusManager] No cached buildings for {city_name}/{bounds_hash}")
            return False, None

    def save_buildings_to_nucleus(
        self,
        city_name: str,
        bounds_hash: str,
        usd_content,  # Can be str or bytes
        metadata: Dict
    ) -> Tuple[bool, Optional[str]]:
        """
        Save building USD data to Nucleus.

        Args:
            city_name: Name of the city
            bounds_hash: Hash of the geographic bounds
            usd_content: USD file content as string or bytes
            metadata: Dictionary of metadata (bounds, building count, timestamp, etc.)

        Returns:
            Tuple of (success: bool, nucleus_path: Optional[str])
        """
        if not self._connected:
            carb.log_warn("[NucleusManager] Not connected to Nucleus, cannot save")
            return False, None

        try:
            # Ensure city directory exists
            city_path = self.get_city_data_path(city_name)
            if not self._ensure_directory(city_path):
                return False, None

            # Get USD file path
            usd_path = self.get_buildings_usd_path(city_name, bounds_hash)

            # Save USD content (handle both string and bytes)
            if isinstance(usd_content, str):
                usd_content = usd_content.encode('utf-8')
            
            result = omni.client.write_file(usd_path, usd_content)
            if result != omni.client.Result.OK:
                carb.log_error(f"[NucleusManager] Failed to write USD file: {result}")
                return False, None

            # Save metadata as JSON sidecar file
            metadata_path = f"{usd_path}.meta.json"
            metadata['saved_at'] = datetime.utcnow().isoformat()
            metadata_json = json.dumps(metadata, indent=2)

            result = omni.client.write_file(metadata_path, metadata_json.encode('utf-8'))
            if result != omni.client.Result.OK:
                carb.log_warn(f"[NucleusManager] Failed to write metadata: {result}")

            carb.log_info(f"[NucleusManager] Successfully saved buildings to: {usd_path}")
            return True, usd_path

        except Exception as e:
            carb.log_error(f"[NucleusManager] Error saving to Nucleus: {e}")
            return False, None

    def load_buildings_from_nucleus(self, city_name: str, bounds_hash: str) -> Tuple[bool, Optional[str]]:
        """
        Load building USD data from Nucleus.

        Args:
            city_name: Name of the city
            bounds_hash: Hash of the geographic bounds

        Returns:
            Tuple of (success: bool, usd_content: Optional[str])
        """
        if not self._connected:
            return False, None

        exists, usd_path = self.check_buildings_cache(city_name, bounds_hash)
        if not exists:
            return False, None

        try:
            # Read USD file (can be binary or text format)
            result, _, content = omni.client.read_file(usd_path)
            if result != omni.client.Result.OK:
                carb.log_error(f"[NucleusManager] Failed to read USD file: {result}")
                return False, None

            # Content object from omni.client can be used directly (works as bytes)
            carb.log_info(f"[NucleusManager] Successfully loaded buildings from Nucleus")
            return True, content

        except Exception as e:
            carb.log_error(f"[NucleusManager] Error loading from Nucleus: {e}")
            return False, None

    def get_metadata(self, city_name: str, bounds_hash: str) -> Optional[Dict]:
        """
        Load metadata for cached buildings.

        Args:
            city_name: Name of the city
            bounds_hash: Hash of the geographic bounds

        Returns:
            Optional[Dict]: Metadata dictionary or None if not found
        """
        if not self._connected:
            return None

        usd_path = self.get_buildings_usd_path(city_name, bounds_hash)
        metadata_path = f"{usd_path}.meta.json"

        try:
            result, _, content = omni.client.read_file(metadata_path)
            if result != omni.client.Result.OK:
                return None

            # Convert Content object to bytes for json.loads
            metadata = json.loads(bytes(content))
            return metadata

        except Exception as e:
            carb.log_warn(f"[NucleusManager] Error loading metadata: {e}")
            return None

    def list_cached_cities(self) -> List[str]:
        """
        List all cities with cached data on Nucleus.

        Returns:
            List[str]: List of city names
        """
        if not self._connected:
            return []

        try:
            result, entries = omni.client.list(self._base_path)
            if result != omni.client.Result.OK:
                return []

            cities = [entry.relative_path for entry in entries if entry.flags & omni.client.ItemFlags.CAN_HAVE_CHILDREN]
            carb.log_info(f"[NucleusManager] Found {len(cities)} cached cities")
            return cities

        except Exception as e:
            carb.log_error(f"[NucleusManager] Error listing cities: {e}")
            return []

    def save_shadow_results(
        self,
        city_name: str,
        analysis_id: str,
        results_data: Dict
    ) -> Tuple[bool, Optional[str]]:
        """
        Save shadow analysis results to Nucleus.

        Args:
            city_name: Name of the city
            analysis_id: Unique ID for this analysis
            results_data: Dictionary containing shadow query results

        Returns:
            Tuple of (success: bool, nucleus_path: Optional[str])
        """
        if not self._connected:
            return False, None

        try:
            # Create results directory
            results_path = f"{self.get_city_data_path(city_name)}/results"
            self._ensure_directory(results_path)

            # Save results as JSON
            result_file = f"{results_path}/shadow_analysis_{analysis_id}.json"
            results_json = json.dumps(results_data, indent=2)

            result = omni.client.write_file(result_file, results_json.encode('utf-8'))
            if result == omni.client.Result.OK:
                carb.log_info(f"[NucleusManager] Saved shadow results to: {result_file}")
                return True, result_file
            else:
                carb.log_error(f"[NucleusManager] Failed to save results: {result}")
                return False, None

        except Exception as e:
            carb.log_error(f"[NucleusManager] Error saving results: {e}")
            return False, None

    # Terrain caching methods

    def get_terrain_usd_path(self, city_name: str, bounds_hash: str) -> str:
        """
        Get the Nucleus path for cached terrain USD file.

        Args:
            city_name: Name of the city
            bounds_hash: Hash of the geographic bounds + resolution

        Returns:
            str: Full Nucleus path to terrain USD file
        """
        city_path = self.get_city_data_path(city_name)
        return f"{city_path}/terrain_{bounds_hash}.usd"

    def check_terrain_cache(self, city_name: str, bounds_hash: str) -> Tuple[bool, Optional[str]]:
        """
        Check if terrain data is cached on Nucleus.

        Args:
            city_name: Name of the city
            bounds_hash: Hash of the geographic bounds + resolution

        Returns:
            Tuple of (exists: bool, path: Optional[str])
        """
        if not self._connected:
            return False, None

        usd_path = self.get_terrain_usd_path(city_name, bounds_hash)
        result, _ = omni.client.stat(usd_path)

        if result == omni.client.Result.OK:
            carb.log_info(f"[NucleusManager] Found cached terrain at: {usd_path}")
            return True, usd_path
        else:
            carb.log_info(f"[NucleusManager] No cached terrain for {city_name}/{bounds_hash}")
            return False, None

    def save_terrain_to_nucleus(
        self,
        city_name: str,
        bounds_hash: str,
        usd_content: bytes,
        metadata: Dict
    ) -> Tuple[bool, Optional[str]]:
        """
        Save terrain USD data to Nucleus.

        Args:
            city_name: Name of the city
            bounds_hash: Hash of the geographic bounds + resolution
            usd_content: USD file content as bytes (can be binary USDC format)
            metadata: Dictionary of metadata (bounds, resolution, timestamp, etc.)

        Returns:
            Tuple of (success: bool, nucleus_path: Optional[str])
        """
        if not self._connected:
            carb.log_warn("[NucleusManager] Not connected to Nucleus, cannot save terrain")
            return False, None

        try:
            # Ensure city directory exists
            city_path = self.get_city_data_path(city_name)
            if not self._ensure_directory(city_path):
                return False, None

            # Get USD file path
            usd_path = self.get_terrain_usd_path(city_name, bounds_hash)

            # Save USD content (already bytes, no need to encode)
            if isinstance(usd_content, str):
                usd_content = usd_content.encode('utf-8')
            
            result = omni.client.write_file(usd_path, usd_content)
            if result != omni.client.Result.OK:
                carb.log_error(f"[NucleusManager] Failed to write terrain USD file: {result}")
                return False, None

            # Save metadata as JSON sidecar file
            metadata_path = f"{usd_path}.meta.json"
            metadata['saved_at'] = datetime.utcnow().isoformat()
            metadata_json = json.dumps(metadata, indent=2)

            result = omni.client.write_file(metadata_path, metadata_json.encode('utf-8'))
            if result != omni.client.Result.OK:
                carb.log_warn(f"[NucleusManager] Failed to write terrain metadata: {result}")

            carb.log_info(f"[NucleusManager] Successfully saved terrain to: {usd_path}")
            return True, usd_path

        except Exception as e:
            carb.log_error(f"[NucleusManager] Error saving terrain to Nucleus: {e}")
            return False, None

    def load_terrain_from_nucleus(self, city_name: str, bounds_hash: str) -> Tuple[bool, Optional[bytes]]:
        """
        Load terrain USD data from Nucleus.

        Args:
            city_name: Name of the city
            bounds_hash: Hash of the geographic bounds + resolution

        Returns:
            Tuple of (success: bool, usd_content: Optional[bytes|str])
        """
        if not self._connected:
            return False, None

        exists, usd_path = self.check_terrain_cache(city_name, bounds_hash)
        if not exists:
            return False, None

        try:
            # Read USD file (can be binary or text format)
            result, _, content = omni.client.read_file(usd_path)
            if result != omni.client.Result.OK:
                carb.log_error(f"[NucleusManager] Failed to read terrain USD file: {result}")
                return False, None

            # Content object from omni.client can be used as bytes directly
            # Just return it as-is for deserializer to handle
            usd_content = content
            
            carb.log_info(f"[NucleusManager] Successfully loaded terrain from Nucleus")
            return True, usd_content

        except Exception as e:
            carb.log_error(f"[NucleusManager] Error loading terrain from Nucleus: {e}")
            return False, None

    def get_terrain_metadata(self, city_name: str, bounds_hash: str) -> Optional[Dict]:
        """
        Load metadata for cached terrain.

        Args:
            city_name: Name of the city
            bounds_hash: Hash of the geographic bounds + resolution

        Returns:
            Optional[Dict]: Metadata dictionary or None if not found
        """
        if not self._connected:
            return None

        usd_path = self.get_terrain_usd_path(city_name, bounds_hash)
        metadata_path = f"{usd_path}.meta.json"

        try:
            result, _, content = omni.client.read_file(metadata_path)
            if result != omni.client.Result.OK:
                return None

            # Convert Content object to bytes for json.loads
            metadata = json.loads(bytes(content))
            return metadata

        except Exception as e:
            carb.log_warn(f"[NucleusManager] Error loading terrain metadata: {e}")
            return None

    def is_connected(self) -> bool:
        """Check if currently connected to Nucleus."""
        return self._connected

    def shutdown(self):
        """Clean up resources."""
        carb.log_info("[NucleusManager] Shutting down Nucleus manager")
        self._connected = False
