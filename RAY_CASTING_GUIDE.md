# Ray Casting Point Query System - User Guide

## 🎯 New Feature: Point Query System

The City Shadow Analyzer now includes a ray casting system that allows you to click anywhere in the 3D scene and determine if that point is in sunlight or shadow!

## How to Use

### Step 1: Set Up the Scene
1. Launch the application
2. Set your location (latitude/longitude)
3. Set the time (or use current time)
4. Click **"Update Sun Position"** to calculate sun angle
5. Click **"Create Test Scene"** to generate buildings

### Step 2: Activate Query Mode
1. Click the **"Activate Query Mode"** button
2. The button will turn green and say "🎯 Query Mode ACTIVE"
3. Your cursor is now ready to query points

### Step 3: Query Points
1. Click anywhere in the 3D viewport:
   - On buildings
   - On the ground
   - On any surface
2. The system will:
   - Cast a ray from that point toward the sun
   - Check if any buildings block the ray
   - Display the result in the UI

### Step 4: Read Results

The **"Point Query Results"** panel will show:

**☀️ SUNLIGHT** (Yellow/Orange)
- No obstruction between point and sun
- Direct sunlight available
- Shows sun position (azimuth, elevation)

**🌑 SHADOW** (Purple)
- Building blocks the sun
- Shows which building is blocking
- Shows distance to blocking object

**🌙 NIGHT** (Blue)
- Sun is below the horizon
- No sunlight available regardless of buildings

### Step 5: Visual Markers

Each query creates a colored marker sphere:
- **Yellow sphere** = Sunlight point
- **Purple sphere** = Shadow point
- **Blue sphere** = Night (sun below horizon)

Click **"Clear Query Markers"** to remove all markers

### Step 6: Deactivate Query Mode

Click **"Activate Query Mode"** again to turn off query mode (button turns blue)

## Tips for Testing

### Test Scenario 1: Shadow Behind Building
1. Create test scene
2. Set time to have sun from the East (morning)
3. Query a point on the west side of a tall building
4. Should show **SHADOW** (blocked by building)

### Test Scenario 2: Open Area
1. Query a point on the ground between buildings
2. If sun elevation is high, should show **SUNLIGHT**
3. Try different times to see how shadows move

### Test Scenario 3: Top of Building
1. Query a point on top of a tall building
2. Should almost always show **SUNLIGHT** (unless another taller building blocks)

### Test Scenario 4: Multiple Points
1. Query several points around a building
2. Watch shadow pattern emerge
3. Notice how shadow side changes with sun direction

### Test Scenario 5: Time-Based Changes
1. Query a specific point
2. Change the time (earlier or later in day)
3. Update sun position
4. Query the same point again
5. See how result changes from sunlight to shadow or vice versa

## Understanding the Results

### Query Result Details Include:
- **Result**: SUNLIGHT, SHADOW, or NIGHT
- **Position**: 3D coordinates (x, y, z) of queried point
- **Sun Position**: Azimuth and elevation angles
- **Blocker Info** (if in shadow): Name of blocking object and distance

### Ray Casting Logic:
1. Point is clicked in viewport
2. 3D position is determined via raycast
3. Ray is cast FROM that point TOWARD the sun
4. If ray hits a building → **SHADOW**
5. If ray reaches sun without hitting anything → **SUNLIGHT**
6. If sun below horizon → **NIGHT**

## Camera Controls

To navigate and find good query points:
- **Right-click + Drag**: Rotate camera around scene
- **Middle-click + Drag**: Pan camera
- **Scroll Wheel**: Zoom in/out
- **F**: Frame selection (select object first)

## Technical Details

### Ray Casting Features:
- Uses NVIDIA RTX ray tracing acceleration
- Accurate occlusion testing
- Handles multiple buildings
- Filters out self-intersections
- 1000-unit ray length (more than enough for city blocks)

### Coordinate System:
- +Y is up
- Ground plane at Y=0
- Buildings have positive Y positions
- Sun direction calculated from astronomy

## Troubleshooting

### "No surface hit"
- You clicked in empty space
- Try clicking on visible geometry (ground or buildings)

### "Error during query"
- Check the console for details
- May need to recreate scene
- Try clicking "Update Sun Position" first

### Query mode not working
- Make sure you clicked "Activate Query Mode"
- Button should be green
- Try clicking "Update Sun Position" first

### Wrong results
- Verify sun position is updated
- Check that sun is above horizon (elevation > 0)
- Ensure test scene has buildings

## Next Steps

### To Add More Buildings:
- Edit the `_create_test_scene()` method
- Add more entries to `buildings_data` list
- Rebuild and relaunch

### To Load Real City Data:
- Coming soon: OpenStreetMap integration
- Will load real building footprints
- Convert to 3D geometry

### To Add API:
- Coming soon: REST API endpoint
- Query format: `/api/shadow/query?lat=X&lon=Y&time=ISO8601`
- Returns JSON with sunlight/shadow status

## Performance Notes

- Query is nearly instant (uses GPU ray tracing)
- Can handle dozens of buildings efficiently
- Markers are lightweight (spheres)
- Clear markers periodically to avoid clutter

---

**Enjoy testing your shadow analysis system!** 🌞🏙️
