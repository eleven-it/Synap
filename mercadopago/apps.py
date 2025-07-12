from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class MercadoPagoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'mercadopago'
    verbose_name = _('MercadoPago Integration')
    
    def ready(self):
        """Inicialización de la app cuando Django está listo"""
        try:
            import mercadopago.signals  # noqa
        except ImportError:
            pass 