# Celery configuration - ELIMINADO (No necesario para instalación mínima de Reportes)
# Celery no está instalado en requirements.txt para esta instalación mínima

# import os
# from celery import Celery

# # Establecer la variable de entorno para las configuraciones de Django
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')

# # Crear la instancia de Celery
# app = Celery('synap')

# # Usar la configuración de Django para Celery
# app.config_from_object('django.conf:settings', namespace='CELERY')

# # Descubrir automáticamente las tareas en todas las aplicaciones instaladas
# app.autodiscover_tasks()

# @app.task(bind=True)
# def debug_task(self):
#     """Tarea de debug para probar Celery"""
#     print(f'Request: {self.request!r}')
