"""Extension entry point for sun position calculation."""

import omni.ext
import carb


class CityAnalyzerSunExtension(omni.ext.IExt):
    """Extension for calculating sun position based on time and location."""

    def on_startup(self, ext_id):
        """Called when the extension starts up."""
        carb.log_info("[city.shadow_analyzer.sun] Sun position extension starting")
        self._ext_id = ext_id

    def on_shutdown(self):
        """Called when the extension shuts down."""
        carb.log_info("[city.shadow_analyzer.sun] Sun position extension shutting down")
