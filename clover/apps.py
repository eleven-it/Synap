from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CloverConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'clover'
    verbose_name = _('Clover Payment Integration')
    
    def ready(self):
        """Inicializar la app cuando Django esté listo"""
        try:
            import clover.signals
        except ImportError:
            pass 