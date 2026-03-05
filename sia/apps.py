from django.apps import AppConfig


class SiaConfig(AppConfig):
    """Configuración de la app Strategic Insights & Alignment (SIA)."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'sia'
    verbose_name = 'Insights Estratégicos y Alineamiento'

    def ready(self):
        """Hook de inicialización del módulo."""
        # Aquí se pueden registrar señales, tareas periódicas, etc.
        pass

