from django.urls import path

from . import views

app_name = "compras"

urlpatterns = [
    path("remito-compra/", views.remito_compra_form, name="remito_compra_form"),
    path("remito-compra/eliminar-renglon/", views.eliminar_renglon, name="eliminar_renglon"),
    path("remito-compra/añadir-renglon/", views.añadir_renglon, name="añadir_renglon"),
    path("remito-compra/lista-comp/", views.lista_comp_remito, name="lista_comp_remito"),
]
