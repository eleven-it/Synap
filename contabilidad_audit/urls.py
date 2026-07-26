from django.urls import path

from contabilidad_audit import views

app_name = "contabilidad_audit"

urlpatterns = [
    path("manual/", views.manual_usuario_view, name="manual_usuario"),
    path("auditoria/", views.auditoria_tablero, name="auditoria_tablero"),
    path(
        "auditoria/ejercicios-periodos/",
        views.auditoria_ejercicios_periodos,
        name="auditoria_ejercicios_periodos",
    ),
    path("auditoria/configuracion/", views.auditoria_configuracion, name="auditoria_configuracion"),
    path(
        "auditoria/configuracion/historial/",
        views.auditoria_configuracion_historial,
        name="auditoria_configuracion_historial",
    ),
    path("auditoria/dry-run/", views.auditoria_dry_run, name="auditoria_dry_run"),
    path(
        "auditoria/rei/<uuid:dry_run_id>/",
        views.auditoria_rei_aprobacion,
        name="auditoria_rei_aprobacion",
    ),
    path("auditoria/apply/", views.auditoria_apply_confirmacion, name="auditoria_apply"),
    path("auditoria/apply/ejecutar/", views.auditoria_apply, name="auditoria_apply_ejecutar"),
    path("auditoria/lotes/", views.auditoria_lotes, name="auditoria_lotes"),
    path(
        "auditoria/lotes/<str:lote_id>/rollback/",
        views.auditoria_lote_rollback,
        name="auditoria_lote_rollback",
    ),
]
