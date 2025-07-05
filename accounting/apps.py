from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AccountingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounting'
    verbose_name = _('Accounting')

    def ready(self):
        """Configuración inicial del módulo de contabilidad"""
        # Importar señales si existen
        try:
            import accounting.signals
        except ImportError:
            pass 