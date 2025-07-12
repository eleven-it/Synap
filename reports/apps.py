from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ReportsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'reports'
    verbose_name = _('Reports')
    
    def ready(self):
        """Inicialización de la app cuando está lista"""
        # try:
        #     import reports.signals  # noqa
        # except ImportError:
        #     pass 
        pass 