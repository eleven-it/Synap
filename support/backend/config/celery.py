"""Configuración de Celery para Support."""
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

app = Celery("support_service")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks(lambda: [f"apps.{a}" for a in [
    "cases", "sla", "audit", "knowledge", "integrations"
]])

app.conf.beat_schedule = {
    "sla-checks-every-2min": {
        "task": "sla.run_sla_checks",
        "schedule": 120.0,  # cada 2 minutos
    },
}

@app.task(bind=True)
def debug_task(self):
    """Tarea de prueba."""
    print(f"Request: {self.request!r}")
