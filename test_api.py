"""
Test script for Shadow Analyzer REST API.

This script tests the API endpoints once the service is running.
"""

import requests
import json
from datetime import datetime, timezone

API_BASE = "http://localhost:8000"


def test_health():
    """Test the health check endpoint."""
    print("Testing /health endpoint...")
    response = requests.get(f"{API_BASE}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()


def test_sun_position():
    """Test the sun position endpoint."""
    print("Testing /api/v1/sun/position endpoint...")

    data = {
        "latitude": 40.7128,
        "longitude": -74.0060,
        "timestamp": "2026-01-13T15:00:00Z"
    }

    response = requests.post(
        f"{API_BASE}/api/v1/sun/position",
        json=data
    )

    print(f"Status: {response.status_code}")
    print(f"Request: {json.dumps(data, indent=2)}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()


def test_shadow_query():
    """Test the shadow query endpoint."""
    print("Testing /api/v1/shadow/query endpoint...")

    # Test NYC Times Square
    data = {
        "latitude": 40.7580,
        "longitude": -73.9855,
        "search_radius": 500
    }

    response = requests.post(
        f"{API_BASE}/api/v1/shadow/query",
        json=data
    )

    print(f"Status: {response.status_code}")
    print(f"Request: {json.dumps(data, indent=2)}")

    if response.status_code == 200:
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2)}")

        if result['is_shadowed']:
            print(f"\n🌙 Location is IN SHADOW")
            if result['sun_elevation'] < 0:
                print(f"☀️ Sun is below horizon (nighttime)")
            elif result.get('blocking_object'):
                print(f"🏢 Blocked by: {result['blocking_object']}")
        else:
            print(f"\n☀️ Location is IN SUNLIGHT")

        print(f"Sun azimuth: {result['sun_azimuth']:.1f}°")
        print(f"Sun elevation: {result['sun_elevation']:.1f}°")
    else:
        print(f"Error: {response.text}")

    print()


def test_multiple_locations():
    """Test multiple locations around the world."""
    print("Testing multiple locations...")

    locations = [
        {"name": "New York City", "lat": 40.7128, "lon": -74.0060},
        {"name": "London", "lat": 51.5074, "lon": -0.1278},
        {"name": "Tokyo", "lat": 35.6762, "lon": 139.6503},
        {"name": "Sydney", "lat": -33.8688, "lon": 151.2093},
    ]

    for loc in locations:
        response = requests.post(
            f"{API_BASE}/api/v1/shadow/query",
            json={
                "latitude": loc["lat"],
                "longitude": loc["lon"],
                "search_radius": 300
            }
        )

        if response.status_code == 200:
            result = response.json()
            shadow_status = "SHADOW" if result['is_shadowed'] else "SUNLIGHT"
            print(f"{loc['name']:20} - {shadow_status:10} (elevation: {result['sun_elevation']:6.1f}°)")
        else:
            print(f"{loc['name']:20} - ERROR: {response.status_code}")

    print()


if __name__ == "__main__":
    print("=" * 60)
    print("Shadow Analyzer REST API Test Suite")
    print("=" * 60)
    print()

    try:
        test_health()
        test_sun_position()
        test_shadow_query()
        test_multiple_locations()

        print("=" * 60)
        print("All tests completed!")
        print("=" * 60)

    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to API server.")
        print("Make sure the API service is running:")
        print("  .\\repo.bat launch city.shadow_analyzer.api.kit")
    except Exception as e:
        print(f"ERROR: {e}")
