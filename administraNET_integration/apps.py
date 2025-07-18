from django.apps import AppConfig


class AdministraNETIntegrationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'administraNET_integration'
    verbose_name = 'Integración administraNET'
    
    def ready(self):
        """Inicialización de la aplicación"""
        # Importar señales si existen
        try:
            import administraNET_integration.signals
        except ImportError:
            pass
