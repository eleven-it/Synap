import os
from celery import Celery
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')

app = Celery('django_project')

# Usar la configuración de Django para Celery
app.config_from_object('django.conf:settings', namespace='CELERY')

# Descubrir tareas en todas las apps
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS) 