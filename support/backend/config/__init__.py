# Configuración del proyecto support_service.
# Celery se carga al importar la app.
from .celery import app as celery_app

__all__ = ("celery_app",)
