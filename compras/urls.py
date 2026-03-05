from django.urls import path

from . import views

app_name = "compras"

urlpatterns = [
    path("facturacion/", views.factura_compra, name="factura_compra"),
    path("remito-compra/", views.remito_compra_form, name="remito_compra_form"),
    path("remito-compra/eliminar-renglon/", views.eliminar_renglon, name="eliminar_renglon"),
    path("remito-compra/añadir-renglon/", views.añadir_renglon, name="añadir_renglon"),
    path("remito-compra/lista-comp/", views.lista_comp_remito, name="lista_comp_remito"),
    # Hub comprobantes de compra (CargaComprobantesP.frm) — bajo menú Stock
    path("comprobantes-proveedor/", views.hub_comprobantes_proveedor, name="hub_comprobantes"),
    path("comprobantes-proveedor/factura/<int:codigo_proveedor>/", views.factura_compra_form, name="factura_compra_form"),
    path("comprobantes-proveedor/orden-pago/<int:codigo_proveedor>/<str:tipo>/", views.orden_pago_form, name="orden_pago_form"),
    path("comprobantes-proveedor/nota-credito/<int:codigo_proveedor>/<str:tipo>/", views.nota_credito_form, name="nota_credito_form"),
    path("comprobantes-proveedor/nota-debito/<int:codigo_proveedor>/", views.nota_debito_form, name="nota_debito_form"),
    path("comprobantes-proveedor/ctacte/<int:codigo_proveedor>/", views.ctacte_proveedor, name="ctacte_proveedor"),
    path("comprobantes-proveedor/imputacion/<int:codigo_proveedor>/", views.imputacion_form, name="imputacion_form"),
    path("comprobantes-proveedor/desimputacion/<int:codigo_proveedor>/", views.desimputacion_form, name="desimputacion_form"),
]
