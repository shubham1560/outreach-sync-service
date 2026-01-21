"""
Django app configuration for the internal service.
"""
from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Configuration for the core app."""
    
    name = "core"

    def ready(self):
        """Import signals when Django is ready."""
        import core.signals
