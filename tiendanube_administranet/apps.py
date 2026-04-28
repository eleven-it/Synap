from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class TiendanubeAdministranetConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tiendanube_administranet'
    verbose_name = _('Tiendanube-AdministraNET Integration')
    
    def ready(self):
        """Import signals when app is ready."""
        import tiendanube_administranet.signals
