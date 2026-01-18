# Bugfix: Loading Map Button Stuck in "Loading" State

## Issue Description

**Reported Problem:**
After loading buildings and terrain using the "Load Map with Terrain & Buildings" button, the button would get stuck displaying "⏳ Loading Map..." and remain disabled/inactive, preventing users from loading additional maps.

**Symptoms:**
- ✗ Button text stuck as "⏳ Loading Map..." instead of returning to "Load Map with Terrain & Buildings"
- ✗ Button remained gray and disabled after loading completed successfully
- ✗ Users could not load a new map without restarting the application
- ✗ The button never re-enabled even though the map data loaded successfully

## Root Cause Analysis

The issue was in the `_load_map_with_terrain()` function in `extension.py`:

1. **User clicks the combined button** → `_load_map_button` is disabled
2. **Function calls** `_load_buildings_sync()` and `_load_terrain_sync()`
3. **Those sync functions** tried to restore their individual buttons:
   - `_load_buildings_sync()` → restores `_load_buildings_button`
   - `_load_terrain_sync()` → restores `_load_terrain_button`
4. **Problem**: The combined `_load_map_button` was never restored!

```python
# BEFORE (buggy code):
async def _do_load():
    self._load_map_button.enabled = False
    self._load_map_button.text = "⏳ Loading Map..."
    
    # These functions restored their OWN buttons, not the combined button!
    self._load_buildings_sync()
    self._load_terrain_sync()
    
    # ❌ MISSING: No call to restore _load_map_button
```

## Solution Implemented

Added a `from_combined_button` parameter to both sync functions to control button restoration behavior:

### 1. Modified Function Signatures

```python
def _load_buildings_sync(self, from_combined_button=False):
    """
    Args:
        from_combined_button: If True, don't restore individual button
    """

def _load_terrain_sync(self, from_combined_button=False):
    """
    Args:
        from_combined_button: If True, don't restore individual button  
    """
```

### 2. Updated Combined Loader

```python
async def _do_load():
    # Disable combined button
    self._load_map_button.enabled = False
    self._load_map_button.text = "⏳ Loading Map..."
    
    try:
        # Pass from_combined_button=True to suppress individual restoration
        self._load_buildings_sync(from_combined_button=True)
        self._load_terrain_sync(from_combined_button=True)
        
        # ✅ FIXED: Restore the combined button
        self._restore_map_button()
        
    except Exception as e:
        # Restore even on error
        self._restore_map_button()
```

### 3. Updated Button Restoration Logic

All button restoration code in both sync functions now checks the flag:

```python
# Only restore individual button if NOT called from combined button
if hasattr(self, '_load_buildings_button') and not from_combined_button:
    self._load_buildings_button.enabled = True
    self._load_buildings_button.text = "Load Buildings from OpenStreetMap"
    self._load_buildings_button.set_style({"background_color": 0xFFFF9800})
```

## Files Modified

- `source/extensions/city.shadow_analyzer.ui/city/shadow_analyzer/ui/extension.py`
  - Modified `_load_map_with_terrain()` method
  - Modified `_load_buildings_sync()` method signature and 7 button restoration points
  - Modified `_load_terrain_sync()` method signature and 2 button restoration points

## Testing Recommendations

### Test Case 1: Normal Load
1. Enter valid coordinates (e.g., New York: 40.7128, -74.0060)
2. Click "Load Map with Terrain & Buildings"
3. **Verify**: Button shows "⏳ Loading Map..." and is gray/disabled
4. Wait for loading to complete
5. **Verify**: Button returns to "Load Map with Terrain & Buildings" and orange color
6. **Verify**: Button is enabled and clickable

### Test Case 2: Load Multiple Times
1. Load a map at coordinates 40.7128, -74.0060
2. Wait for completion
3. Change coordinates to 51.5074, -0.1278 (London)
4. Click button again
5. **Verify**: Button responds correctly to second load
6. **Verify**: Second load completes and button restores

### Test Case 3: Error Handling
1. Enter invalid coordinates (e.g., 999, 999)
2. Click "Load Map with Terrain & Buildings"
3. **Verify**: Error message appears
4. **Verify**: Button still restores to enabled state after error

### Test Case 4: Individual Buttons Still Work
1. Click "Load Buildings from OpenStreetMap" individually
2. **Verify**: That button restores correctly
3. Click "Load Terrain Elevation Data" individually  
4. **Verify**: That button restores correctly

## Expected Behavior After Fix

✅ Combined button disables during load  
✅ Combined button shows loading state  
✅ Combined button restores after success  
✅ Combined button restores after error  
✅ Button is re-enabled for subsequent loads  
✅ Individual buttons still work independently  

## Technical Details

**Branch**: `bugfix/loading-map-button-stuck`  
**Commit**: `54226d0`  
**Lines Changed**: 37 insertions, 17 deletions  

**Key Changes**:
- Added `from_combined_button` parameter to 2 functions
- Updated 9 button restoration code blocks to check the parameter
- Added `try/except` wrapper with guaranteed button restoration
- Added `_restore_map_button()` calls after both sync operations

## Status

✅ **FIXED** - Button now properly restores to enabled state after loading completes or errors
