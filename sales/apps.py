from django.apps import AppConfig


class SalesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'sales'
    verbose_name = 'Sales Management'

    def ready(self):
        """Conectar señales cuando la app esté lista"""
        import sales.signals
