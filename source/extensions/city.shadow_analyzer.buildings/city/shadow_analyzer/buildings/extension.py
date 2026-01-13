"""Extension for loading building data from OpenStreetMap."""

import omni.ext
import carb


class CityBuildingsExtension(omni.ext.IExt):
    """Extension that provides OpenStreetMap building loading capability."""

    def on_startup(self, ext_id):
        """Called when the extension starts up."""
        carb.log_info("[city.shadow_analyzer.buildings] Buildings extension starting")
        self._ext_id = ext_id

    def on_shutdown(self):
        """Called when the extension shuts down."""
        carb.log_info("[city.shadow_analyzer.buildings] Buildings extension shutting down")
