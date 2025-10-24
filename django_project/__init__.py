# Configuración de Celery para el proyecto
from .celery import app as celery_app

__all__ = ('celery_app',) 