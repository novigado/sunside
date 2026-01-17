"""
Test script for Shadow Analyzer API.

This script demonstrates how to:
1. Check sun position for Gothenburg
2. Query shadow status at GPS coordinates
"""

import requests
import json
from datetime import datetime, timezone

# API endpoint
API_BASE = "http://localhost:8000"

def test_health():
    """Test API health check."""
    print("=" * 60)
    print("Testing Health Endpoint")
    print("=" * 60)

    response = requests.get(f"{API_BASE}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()

def test_sun_position(lat, lon):
    """Test sun position calculation."""
    print("=" * 60)
    print(f"Testing Sun Position for ({lat}, {lon})")
    print("=" * 60)

    payload = {
        "latitude": lat,
        "longitude": lon
    }

    response = requests.post(f"{API_BASE}/api/v1/sun/position", json=payload)
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response: {json.dumps(result, indent=2)}")
    print(f"\nSummary:")
    print(f"  Sun Azimuth: {result['azimuth']:.2f}° (0=North, 90=East, 180=South, 270=West)")
    print(f"  Sun Elevation: {result['elevation']:.2f}° (90=overhead, negative=below horizon)")
    print()
    return result

def test_shadow_query(lat, lon, search_radius=500):
    """Test shadow detection at GPS coordinates."""
    print("=" * 60)
    print(f"Testing Shadow Query for ({lat}, {lon})")
    print("=" * 60)

    payload = {
        "latitude": lat,
        "longitude": lon,
        "search_radius": search_radius
    }

    response = requests.post(f"{API_BASE}/api/v1/shadow/query", json=payload)
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response: {json.dumps(result, indent=2)}")
    print(f"\nSummary:")
    print(f"  Location: ({result['latitude']}, {result['longitude']})")
    print(f"  Sun Elevation: {result['sun_elevation']:.2f}°")
    print(f"  Sun Azimuth: {result['sun_azimuth']:.2f}°")

    if result['is_shadowed']:
        print(f"  Status: 🌑 IN SHADOW")
        if result['blocking_object']:
            print(f"  Blocked by: {result['blocking_object']}")
    else:
        print(f"  Status: ☀️ SUNLIGHT")

    if result.get('message'):
        print(f"  Note: {result['message']}")
    print()
    return result

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("CITY SHADOW ANALYZER API TEST")
    print("=" * 60)
    print()

    # Gothenburg coordinates (default location)
    GOTHENBURG_LAT = 57.70716
    GOTHENBURG_LON = 11.96679

    try:
        # Test 1: Health check
        test_health()

        # Test 2: Sun position
        sun_result = test_sun_position(GOTHENBURG_LAT, GOTHENBURG_LON)

        # Test 3: Shadow query
        # Note: First time will load buildings from OpenStreetMap
        print("NOTE: First shadow query will load building data from OpenStreetMap.")
        print("      This may take 10-30 seconds depending on area density.")
        print()
        shadow_result = test_shadow_query(GOTHENBURG_LAT, GOTHENBURG_LON)

        print("=" * 60)
        print("TESTS COMPLETE!")
        print("=" * 60)
        print("\nTo test different locations, modify the coordinates and run again.")
        print("You can also use curl:")
        print(f'  curl -X POST {API_BASE}/api/v1/shadow/query \\')
        print(f'       -H "Content-Type: application/json" \\')
        print(f'       -d \'{{"latitude": 57.70716, "longitude": 11.96679}}\'')

    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to API server at", API_BASE)
        print("Make sure the City Shadow Analyzer application is running.")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
