"""
Nucleus Integration Extension

Manages connection to Nucleus server and provides USD storage/retrieval for building data.
"""

import omni.ext
import omni.ui as ui
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
        self._is_connected = self._nucleus_manager.check_connection()
        if self._is_connected:
            carb.log_info("[city.shadow_analyzer.nucleus] ✅ Successfully connected to Nucleus")
            carb.log_info(f"[city.shadow_analyzer.nucleus] Server: {self._nucleus_manager.nucleus_server}")
            carb.log_info(f"[city.shadow_analyzer.nucleus] Project Path: {self._nucleus_manager.project_path}")
        else:
            carb.log_warn("[city.shadow_analyzer.nucleus] ⚠️  No Nucleus connection available - running in local mode")

        # Create status window
        self._build_ui()

        carb.log_info("[city.shadow_analyzer.nucleus] Nucleus Integration Extension started")

    def _build_ui(self):
        """Build the Nucleus status UI window."""
        self._window = ui.Window("Nucleus Status", width=400, height=200)

        with self._window.frame:
            with ui.VStack(spacing=10, height=0):
                ui.Label("Nucleus Integration Status",
                        style={"font_size": 18, "color": 0xFFFFFFFF})

                ui.Spacer(height=10)

                # Connection status
                with ui.HStack(spacing=10):
                    ui.Label("Connection:", width=120)
                    if self._is_connected:
                        ui.Label("✅ Connected",
                               style={"color": 0xFF00FF00})
                    else:
                        ui.Label("⚠️  Not Connected",
                               style={"color": 0xFFFFAA00})

                # Server URL
                with ui.HStack(spacing=10):
                    ui.Label("Server:", width=120)
                    ui.Label(self._nucleus_manager.nucleus_server)

                # Project path
                with ui.HStack(spacing=10):
                    ui.Label("Project Path:", width=120)
                    ui.Label(self._nucleus_manager.project_path)

                ui.Spacer(height=10)

                # Test connection button
                ui.Button("Test Connection", clicked_fn=self._test_connection, height=30)

                ui.Spacer()

                # Info label
                self._info_label = ui.Label("",
                                           style={"color": 0xFFAAAAAA, "font_size": 12})

    def _test_connection(self):
        """Test the Nucleus connection."""
        carb.log_info("[city.shadow_analyzer.nucleus] Testing Nucleus connection...")
        self._is_connected = self._nucleus_manager.check_connection()

        if self._is_connected:
            self._info_label.text = "✅ Connection successful!"
            carb.log_info("[city.shadow_analyzer.nucleus] Connection test: SUCCESS")
        else:
            self._info_label.text = "⚠️  Connection failed. Is Nucleus running?"
            carb.log_warn("[city.shadow_analyzer.nucleus] Connection test: FAILED")

    def on_shutdown(self):
        """Called when the extension shuts down."""
        carb.log_info("[city.shadow_analyzer.nucleus] Nucleus Integration Extension shutting down")

        if hasattr(self, '_window') and self._window:
            self._window.destroy()
            self._window = None

        if hasattr(self, '_nucleus_manager'):
            self._nucleus_manager.shutdown()
            self._nucleus_manager = None
