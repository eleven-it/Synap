from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class PurchasesConfig(AppConfig):
    """
    Configuración de la aplicación de Compras
    Gestiona órdenes de compra, solicitudes, cotizaciones y proveedores
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'purchases'
    verbose_name = _('Purchases')
    
    def ready(self):
        """
        Inicialización de la aplicación cuando Django está listo
        """
        import purchases.signals  # noqa 