"""
REST API Extension for City Shadow Analyzer.

Provides HTTP endpoints for shadow analysis queries from smartphones and web applications.
"""

import omni.ext
import carb
import asyncio
import threading
from typing import Optional
from .api_server import ShadowAnalyzerAPI


class CityAnalyzerAPIExtension(omni.ext.IExt):
    """Extension that provides REST API for shadow analysis."""

    def __init__(self):
        """Initialize the API extension."""
        super().__init__()
        self._api_server: Optional[ShadowAnalyzerAPI] = None
        self._server_thread: Optional[threading.Thread] = None

    def on_startup(self, ext_id):
        """Called when the extension starts up."""
        carb.log_info("[city.shadow_analyzer.api] Shadow Analyzer API extension starting up")
        
        # Get settings
        settings = carb.settings.get_settings()
        host = settings.get("/exts/city.shadow_analyzer.api/host") or "0.0.0.0"
        port = settings.get("/exts/city.shadow_analyzer.api/port") or 8000
        
        carb.log_info(f"[city.shadow_analyzer.api] Starting API server on {host}:{port}")
        
        # Create and start API server
        self._api_server = ShadowAnalyzerAPI(host=host, port=port)
        
        # Run server in separate thread to not block Kit
        self._server_thread = threading.Thread(
            target=self._run_server,
            daemon=True
        )
        self._server_thread.start()
        
        carb.log_info("[city.shadow_analyzer.api] API server started successfully")
        carb.log_info(f"[city.shadow_analyzer.api] API documentation available at http://{host}:{port}/docs")

    def _run_server(self):
        """Run the API server in a separate thread."""
        try:
            self._api_server.run()
        except Exception as e:
            carb.log_error(f"[city.shadow_analyzer.api] Server error: {e}")

    def on_shutdown(self):
        """Called when the extension shuts down."""
        carb.log_info("[city.shadow_analyzer.api] Shadow Analyzer API extension shutting down")
        
        if self._api_server:
            self._api_server.shutdown()
            self._api_server = None
        
        if self._server_thread:
            self._server_thread = None
        
        carb.log_info("[city.shadow_analyzer.api] API server stopped")
