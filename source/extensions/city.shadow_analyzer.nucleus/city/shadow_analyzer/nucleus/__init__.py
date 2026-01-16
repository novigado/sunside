"""
City Shadow Analyzer - Nucleus Integration Extension

Provides Nucleus server integration for:
- Caching building data as USD files
- Caching terrain elevation data as USD files
- Storing shadow analysis results
- Collaborative access to city models
"""

from .extension import *
from .nucleus_manager import NucleusManager
from .city_cache import CityCacheManager

# Global singleton instance
_nucleus_manager_instance = None


def get_nucleus_manager() -> NucleusManager:
    """
    Get the global NucleusManager singleton instance.
    
    This function returns the singleton instance of NucleusManager that is
    created when the nucleus extension starts up. It allows other extensions
    to access Nucleus functionality without creating multiple instances.
    
    Returns:
        NucleusManager: The global nucleus manager instance
        
    Raises:
        RuntimeError: If the nucleus extension hasn't been initialized yet
    
    Example:
        ```python
        from city.shadow_analyzer.nucleus import get_nucleus_manager
        
        nucleus_mgr = get_nucleus_manager()
        if nucleus_mgr.is_connected():
            # Use Nucleus for caching
            pass
        ```
    """
    global _nucleus_manager_instance
    
    if _nucleus_manager_instance is None:
        raise RuntimeError(
            "Nucleus manager not initialized. "
            "Make sure the city.shadow_analyzer.nucleus extension is enabled and started."
        )
    
    return _nucleus_manager_instance


def _set_nucleus_manager(manager: NucleusManager):
    """
    Set the global nucleus manager instance (internal use only).
    
    This function is called by the NucleusIntegrationExtension during startup.
    
    Args:
        manager: The NucleusManager instance to set as global singleton
    """
    global _nucleus_manager_instance
    _nucleus_manager_instance = manager


def _clear_nucleus_manager():
    """
    Clear the global nucleus manager instance (internal use only).
    
    This function is called by the NucleusIntegrationExtension during shutdown.
    """
    global _nucleus_manager_instance
    _nucleus_manager_instance = None


__all__ = [
    "NucleusIntegrationExtension",
    "NucleusManager",
    "CityCacheManager",
    "get_nucleus_manager",
]
