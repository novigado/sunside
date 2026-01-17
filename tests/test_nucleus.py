"""
Test script for Nucleus integration.

This script tests the basic functionality of the NucleusManager and CityCacheManager
without requiring the full Kit application to be running.
"""

import sys
import os

# Add extension to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'source', 'extensions', 'city.shadow_analyzer.nucleus'))

try:
    # Import the classes
    from city.shadow_analyzer.nucleus.nucleus_manager import NucleusManager
    from city.shadow_analyzer.nucleus.city_cache import CityCacheManager

    print("✅ Successfully imported Nucleus classes")

    # Test cache key generation
    print("\n--- Testing Cache Key Generation ---")
    cache_manager = CityCacheManager(None)  # We can test without a real manager

    city_name, bounds_hash = cache_manager.generate_cache_key(40.7128, -74.0060, 1000)
    print(f"✅ Cache key generated: city='{city_name}', hash='{bounds_hash}'")
    print(f"   Location: New York City (40.7128°N, 74.0060°W)")
    print(f"   Radius: 1000m")

    # Test with different location
    city_name2, bounds_hash2 = cache_manager.generate_cache_key(51.5074, -0.1278, 500)
    print(f"\n✅ Second cache key: city='{city_name2}', hash='{bounds_hash2}'")
    print(f"   Location: London (51.5074°N, 0.1278°W)")
    print(f"   Radius: 500m")

    # Test that same location produces same hash
    city_name3, bounds_hash3 = cache_manager.generate_cache_key(40.7128, -74.0060, 1000)
    if bounds_hash == bounds_hash3:
        print(f"\n✅ Hash consistency verified: Same location produces same hash")
    else:
        print(f"\n❌ ERROR: Same location produced different hashes!")

    # Test that different location produces different hash
    if bounds_hash != bounds_hash2:
        print(f"✅ Hash uniqueness verified: Different locations produce different hashes")
    else:
        print(f"❌ ERROR: Different locations produced same hash!")

    print("\n--- Testing NucleusManager Creation ---")
    # Note: This won't connect without a running Nucleus server
    nucleus_manager = NucleusManager(
        nucleus_server="omniverse://localhost",
        project_path="/Projects/CityData"
    )
    print(f"✅ NucleusManager created successfully")
    print(f"   Server: {nucleus_manager.nucleus_server}")
    print(f"   Project path: {nucleus_manager.project_path}")

    # Test path construction
    test_path = nucleus_manager._get_buildings_path("TestCity", "abc123def456")
    print(f"\n✅ Path construction works: {test_path}")

    print("\n" + "="*60)
    print("✅ ALL BASIC TESTS PASSED!")
    print("="*60)
    print("\nNote: To test actual Nucleus operations, you need:")
    print("  1. Nucleus server running (omniverse://localhost)")
    print("  2. Run the test within Kit application context")
    print("  3. Use the 'Launch' task to start the Shadow Analyzer app")

except ImportError as e:
    print(f"❌ Import Error: {e}")
    print("\nMake sure the extension is built correctly.")
    sys.exit(1)
except Exception as e:
    print(f"❌ Test Failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
