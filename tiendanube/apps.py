from django.apps import AppConfig


class TiendanubeConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tiendanube'

    def ready(self):
        """Registrar señales cuando la app se carga."""
        import tiendanube.signals

# Extensión para menú de navegación de módulos

def get_nav_submenu_items():
    return [
        {'label': 'Dashboard', 'url': '/tiendanube/'},
        {'label': 'Products', 'url': '/tiendanube/products/'},
        {'label': 'Orders', 'url': '/tiendanube/orders/'},
        {'label': 'Settings', 'url': '/tiendanube/settings/'},
    ]
