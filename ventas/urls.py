from django.urls import path

from ventas import views
from ventas import views_presupuesto

app_name = "ventas"

urlpatterns = [
    path("objetivos-venta/", views.objetivos_periodos_list_view, name="objetivos_periodos_list"),
    path("objetivos-venta/nuevo/", views.objetivos_periodo_nuevo_redirect_view, name="objetivos_periodo_nuevo"),
    path(
        "api/objetivos-venta/periodo/crear/",
        views.api_crear_periodo_objetivos,
        name="api_objetivos_periodo_crear",
    ),
    path(
        "api/objetivos-venta/periodo/descripcion/",
        views.api_actualizar_descripcion_periodo,
        name="api_objetivos_periodo_descripcion",
    ),
    path(
        "objetivos-venta/<int:id_periodo>/anular/",
        views.objetivos_periodo_anular_view,
        name="objetivos_periodo_anular",
    ),
    path("objetivos-venta/<int:id_periodo>/", views.objetivos_periodo_detalle_view, name="objetivos_periodo_detalle"),
    path("api/objetivos-venta/guardar/", views.objetivos_venta_guardar_api, name="api_objetivos_guardar"),
    path("api/vendedores/buscar/", views.api_vendedores_buscar, name="api_vendedores_buscar"),
    # Presupuestos de venta (PRE)
    path("presupuestos/", views_presupuesto.presupuesto_list_view, name="presupuesto_list"),
    path("presupuestos/nuevo/", views_presupuesto.presupuesto_nuevo_view, name="presupuesto_nuevo"),
    path(
        "presupuestos/<int:codigo_movimiento>/exportar-xlsx/",
        views_presupuesto.presupuesto_export_xlsx_view,
        name="presupuesto_export_xlsx",
    ),
    path(
        "presupuestos/<int:codigo_movimiento>/",
        views_presupuesto.presupuesto_detalle_view,
        name="presupuesto_detalle",
    ),
    path(
        "api/presupuestos/clientes/buscar/",
        views_presupuesto.api_presupuesto_clientes_buscar,
        name="api_presupuesto_clientes_buscar",
    ),
    path(
        "api/presupuestos/crear/",
        views_presupuesto.api_presupuesto_crear,
        name="api_presupuesto_crear",
    ),
    path(
        "api/presupuestos/<int:codigo_movimiento>/",
        views_presupuesto.api_presupuesto_retrieve,
        name="api_presupuesto_retrieve",
    ),
    path(
        "api/presupuestos/",
        views_presupuesto.api_presupuesto_list,
        name="api_presupuesto_list",
    ),
]
