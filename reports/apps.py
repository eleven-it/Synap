from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ReportsConfig(AppConfig):
    """Configuración de la app de reportes."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "reports"
    verbose_name = _("Reports & Dashboards")

    def ready(self):
        """Hook de inicialización del módulo."""
        # Comentario: Aquí se registrarán señales, tareas periódicas y catálogos por defecto.
        from . import signals  # noqa: F401  # Importación diferida para evitar ciclos.


