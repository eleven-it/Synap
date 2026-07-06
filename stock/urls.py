from django.urls import path

from . import views
from . import api_views

app_name = "stock"

urlpatterns = [
    path("ingreso-movimiento/", views.alta_movimiento_view, name="alta_movimiento"),
    path("movimientos/", views.visualiza_movimientos_view, name="visualiza_movimientos"),
    path("movimientos/<int:codigo_movimiento>/", views.detalle_movimiento_view, name="detalle_movimiento"),
    path("movimientos/<int:codigo_movimiento>/pdf/", views.movimiento_pdf_view, name="movimiento_pdf"),
    path("referencias/", views.ref_movstock_list_view, name="ref_movstock_list"),
    path("referencias/nueva/", views.ref_movstock_create_view, name="ref_movstock_create"),
    path("referencias/<int:pk>/editar/", views.ref_movstock_edit_view, name="ref_movstock_edit"),
    path("inventario/", views.inventario_view, name="inventario"),
    path("consulta-avanzada/", views.consulta_avanzada_view, name="consulta_avanzada"),
    # API para formulario Ingreso Mov. Stock
    path("api/inventario/articulos/", api_views.api_inventario_articulos, name="api_inventario_articulos"),
    path("api/ingreso/datos-iniciales/", api_views.api_ingreso_datos_iniciales, name="api_ingreso_datos"),
    path("api/ingreso/articulos/", api_views.api_ingreso_articulos, name="api_ingreso_articulos"),
    path("api/ingreso/articulos-por-codigo/", api_views.api_ingreso_articulos_por_codigo, name="api_ingreso_articulos_por_codigo"),
    path("api/ingreso/lotes-articulo/", api_views.api_ingreso_lotes_articulo, name="api_ingreso_lotes_articulo"),
    path("api/ingreso/saldo/", api_views.api_ingreso_saldo, name="api_ingreso_saldo"),
    path("api/ingreso/renglones/", api_views.api_ingreso_renglones, name="api_ingreso_renglones"),
    path("api/ingreso/renglones/add/", api_views.api_ingreso_renglon_add, name="api_ingreso_renglon_add"),
    path("api/ingreso/renglones/<int:orden>/remove/", api_views.api_ingreso_renglon_remove, name="api_ingreso_renglon_remove"),
    path("api/ingreso/renglones/<int:orden>/", api_views.api_ingreso_renglon_update, name="api_ingreso_renglon_update"),
    path("api/ingreso/pedidos-pendientes/", api_views.api_ingreso_pedidos_pendientes, name="api_ingreso_pedidos_pendientes"),
    path("api/ingreso/proyectos/", api_views.api_ingreso_proyectos, name="api_ingreso_proyectos"),
    path("api/ingreso/series-renglon/", api_views.api_ingreso_series_renglon, name="api_ingreso_series_renglon"),
    path("api/ingreso/series-disponibles/", api_views.api_ingreso_series_disponibles, name="api_ingreso_series_disponibles"),
    path("api/ingreso/serie-add/", api_views.api_ingreso_serie_add, name="api_ingreso_serie_add"),
    path("api/ingreso/serie-remove/", api_views.api_ingreso_serie_remove, name="api_ingreso_serie_remove"),
    path("api/ingreso/confirmar/", api_views.api_ingreso_confirmar, name="api_ingreso_confirmar"),
    path("api/ingreso/limpiar-temporales/", api_views.api_ingreso_limpiar_temporales, name="api_ingreso_limpiar_temporales"),
]
