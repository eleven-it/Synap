# Celery tasks - ELIMINADO (No necesario para instalación mínima de Reportes)
# Celery no está instalado en requirements.txt para esta instalación mínima

# from __future__ import annotations
# 
# from celery import shared_task
# 
# from .cache import invalidate_report_cache
# 
# 
# @shared_task(bind=True, queue="reports")
# def enqueue_report_refresh(self, report_slug: str):
#     """Tarea dummy para agendar precálculos."""
#     # Comentario: Aquí se invocará a pipelines reales (SQL, dbt, etc.) para refrescar agregados.
#     invalidate_report_cache(report_slug)
#     return {"status": "scheduled", "slug": report_slug}
# 
# 
# @shared_task(bind=True, queue="reports")
# def build_daily_aggregates(self):
#     """Frecuencia diaria para recalcular métricas operativas."""
#     # Comentario: Este placeholder permitirá conectar con trabajos de agregación en versiones siguientes.
#     return {"status": "ok"}
# 
# 
# @shared_task(bind=True, queue="reports")
# def build_weekly_trends(self):
#     """Frecuencia semanal para métricas de tendencias."""
#     return {"status": "ok"}

# Funciones dummy para compatibilidad (sin Celery)
def enqueue_report_refresh(report_slug: str):
    """Función dummy para compatibilidad - Celery no disponible"""
    from .cache import invalidate_report_cache
    invalidate_report_cache(report_slug)
    return {"status": "scheduled", "slug": report_slug}


def build_daily_aggregates():
    """Función dummy para compatibilidad - Celery no disponible"""
    return {"status": "ok"}


def build_weekly_trends():
    """Función dummy para compatibilidad - Celery no disponible"""
    return {"status": "ok"}
