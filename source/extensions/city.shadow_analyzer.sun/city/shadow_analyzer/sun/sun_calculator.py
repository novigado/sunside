"""
Sun position calculator using astronomical algorithms.

This module calculates the position of the sun in the sky based on:
- Date and time (UTC)
- Geographic location (latitude, longitude)

The sun position is returned as azimuth and elevation angles,
which can be used to position a directional light in a 3D scene.
"""

import math
from datetime import datetime, timezone
from typing import Tuple
import carb


class SunCalculator:
    """Calculate sun position using simplified astronomical algorithms."""

    def __init__(self):
        """Initialize the sun calculator."""
        pass

    @staticmethod
    def calculate_sun_position(
        latitude: float,
        longitude: float,
        dt: datetime = None
    ) -> Tuple[float, float, float]:
        """
        Calculate the sun's position in the sky.

        Args:
            latitude: Latitude in degrees (-90 to 90, positive = North)
            longitude: Longitude in degrees (-180 to 180, positive = East)
            dt: Datetime object (if None, uses current UTC time)

        Returns:
            Tuple of (azimuth, elevation, distance):
                - azimuth: Angle in degrees (0 = North, 90 = East, 180 = South, 270 = West)
                - elevation: Angle in degrees above horizon (90 = directly overhead, negative = below horizon)
                - distance: Distance to sun in AU (astronomical units) - always ~1.0
        """
        if dt is None:
            dt = datetime.now(timezone.utc)

        # Convert to UTC if not already
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)

        # Calculate Julian date
        jd = SunCalculator._get_julian_date(dt)

        # Calculate Julian centuries from J2000.0
        t = (jd - 2451545.0) / 36525.0

        # Calculate sun's ecliptic longitude (simplified)
        l = (280.460 + 36000.771 * t) % 360.0
        g = math.radians((357.528 + 35999.050 * t) % 360.0)

        # Sun's ecliptic longitude
        lambda_sun = l + 1.915 * math.sin(g) + 0.020 * math.sin(2 * g)
        lambda_sun = math.radians(lambda_sun % 360.0)

        # Sun's ecliptic latitude (approximately 0 for simplified calculation)
        beta_sun = 0.0

        # Obliquity of the ecliptic
        epsilon = math.radians(23.439 - 0.013 * t)

        # Convert to equatorial coordinates (Right Ascension and Declination)
        ra = math.atan2(math.cos(epsilon) * math.sin(lambda_sun), math.cos(lambda_sun))
        dec = math.asin(math.sin(epsilon) * math.sin(lambda_sun))

        # Calculate local sidereal time
        lst = SunCalculator._get_local_sidereal_time(dt, longitude)

        # Calculate hour angle
        ha = lst - ra

        # Convert to horizontal coordinates (azimuth and elevation)
        lat_rad = math.radians(latitude)

        # Calculate elevation (altitude)
        sin_el = (math.sin(lat_rad) * math.sin(dec) +
                  math.cos(lat_rad) * math.cos(dec) * math.cos(ha))
        elevation = math.degrees(math.asin(sin_el))

        # Calculate azimuth
        cos_az = ((math.sin(dec) - math.sin(lat_rad) * sin_el) /
                  (math.cos(lat_rad) * math.cos(math.asin(sin_el))))

        # Clamp to avoid numerical errors
        cos_az = max(-1.0, min(1.0, cos_az))
        azimuth = math.degrees(math.acos(cos_az))

        # Adjust azimuth based on hour angle
        if math.sin(ha) > 0:
            azimuth = 360.0 - azimuth

        # Distance is approximately 1 AU
        distance = 1.0

        carb.log_info(f"[SunCalculator] Position at {dt}: az={azimuth:.2f}°, el={elevation:.2f}°")

        return azimuth, elevation, distance

    @staticmethod
    def _get_julian_date(dt: datetime) -> float:
        """Calculate Julian Date from datetime."""
        a = (14 - dt.month) // 12
        y = dt.year + 4800 - a
        m = dt.month + 12 * a - 3

        jdn = (dt.day + (153 * m + 2) // 5 + 365 * y +
               y // 4 - y // 100 + y // 400 - 32045)

        jd = jdn + (dt.hour - 12) / 24.0 + dt.minute / 1440.0 + dt.second / 86400.0

        return jd

    @staticmethod
    def _get_local_sidereal_time(dt: datetime, longitude: float) -> float:
        """Calculate local sidereal time in radians."""
        jd = SunCalculator._get_julian_date(dt)
        t = (jd - 2451545.0) / 36525.0

        # Greenwich sidereal time (in degrees)
        gst = (280.46061837 + 360.98564736629 * (jd - 2451545.0) +
               0.000387933 * t * t - t * t * t / 38710000.0) % 360.0

        # Local sidereal time
        lst = (gst + longitude) % 360.0

        return math.radians(lst)

    @staticmethod
    def get_sun_direction_vector(azimuth: float, elevation: float) -> Tuple[float, float, float]:
        """
        Convert sun position (azimuth, elevation) to a direction vector.

        Args:
            azimuth: Azimuth angle in degrees
            elevation: Elevation angle in degrees

        Returns:
            Tuple of (x, y, z) representing the direction FROM the sun TO the observer.
            This is the direction you'd point a directional light.
        """
        az_rad = math.radians(azimuth)
        el_rad = math.radians(elevation)

        # Convert to Cartesian coordinates (OpenUSD/Omniverse coordinate system)
        # In USD: +Y is up, +X is right, +Z is forward
        x = math.cos(el_rad) * math.sin(az_rad)
        y = -math.sin(el_rad)  # Negative because light points down from sun
        z = -math.cos(el_rad) * math.cos(az_rad)

        return (x, y, z)
