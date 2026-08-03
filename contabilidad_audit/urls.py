from django.urls import path

from contabilidad_audit import cotizacion_views, views

app_name = "contabilidad_audit"

urlpatterns = [
    path("manual/", views.manual_usuario_view, name="manual_usuario"),
    path("cotizacion-dolar/", cotizacion_views.cotizacion_dolar_view, name="cotizacion_dolar"),
    path("api/cotizacion/vigente/", cotizacion_views.cotizacion_api_vigente, name="cotizacion_api_vigente"),
    path("api/cotizacion/sugerencia/", cotizacion_views.cotizacion_api_sugerencia, name="cotizacion_api_sugerencia"),
    path("api/cotizacion/aceptar/", cotizacion_views.cotizacion_api_aceptar, name="cotizacion_api_aceptar"),
    path("api/cotizacion/manual/", cotizacion_views.cotizacion_api_manual, name="cotizacion_api_manual"),
    path("api/cotizacion/historial/", cotizacion_views.cotizacion_api_historial, name="cotizacion_api_historial"),
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
        "auditoria/lotes/<str:lote_id>/",
        views.auditoria_lote_detalle,
        name="auditoria_lote_detalle",
    ),
    path(
        "auditoria/lotes/<str:lote_id>/rollback/",
        views.auditoria_lote_rollback,
        name="auditoria_lote_rollback",
    ),
    path("auditoria/asientos/", views.auditoria_asientos_eliminar, name="auditoria_asientos"),
    path(
        "auditoria/asientos/preview/",
        views.auditoria_asientos_preview,
        name="auditoria_asientos_preview",
    ),
    path(
        "auditoria/asientos/eliminar/",
        views.auditoria_asientos_eliminar_ejecutar,
        name="auditoria_asientos_eliminar",
    ),
]
