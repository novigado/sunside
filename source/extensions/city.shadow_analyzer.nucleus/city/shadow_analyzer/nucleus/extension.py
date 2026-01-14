"""
Nucleus Integration Extension

Manages connection to Nucleus server and provides USD storage/retrieval for building data.
"""

import omni.ext
import carb


class NucleusIntegrationExtension(omni.ext.IExt):
    """Extension for integrating City Shadow Analyzer with Omniverse Nucleus."""

    def on_startup(self, ext_id):
        """Called when the extension starts up."""
        carb.log_info("[city.shadow_analyzer.nucleus] Nucleus Integration Extension starting up")

        # Initialize Nucleus connection manager
        from .nucleus_manager import NucleusManager
        self._nucleus_manager = NucleusManager()

        # Check if Nucleus is available
        if self._nucleus_manager.check_connection():
            carb.log_info("[city.shadow_analyzer.nucleus] Successfully connected to Nucleus")
        else:
            carb.log_warn("[city.shadow_analyzer.nucleus] No Nucleus connection available - running in local mode")

        carb.log_info("[city.shadow_analyzer.nucleus] Nucleus Integration Extension started")

    def on_shutdown(self):
        """Called when the extension shuts down."""
        carb.log_info("[city.shadow_analyzer.nucleus] Nucleus Integration Extension shutting down")

        if hasattr(self, '_nucleus_manager'):
            self._nucleus_manager.shutdown()
            self._nucleus_manager = None
