from django.urls import path
from django.views.generic import RedirectView

from factura_compra_captura import web_views

app_name = "factura_compra_captura_web"

urlpatterns = [
    path(
        "revision/",
        RedirectView.as_view(
            pattern_name="factura_compra_captura_web:lista-expedientes",
            permanent=False,
        ),
        name="revision-redirige-lista",
    ),
    path(
        "expedientes/",
        web_views.ListaExpedientesCompraView.as_view(),
        name="lista-expedientes",
    ),
    path(
        "movil/",
        web_views.CapturaMovilView.as_view(),
        name="captura-movil",
    ),
    path(
        "revision/<uuid:pk>/",
        web_views.RevisionExpedienteView.as_view(),
        name="revision-expediente",
    ),
    path(
        "revision/<uuid:pk>/documento/<int:doc_pk>/",
        web_views.DocumentoFuenteServeView.as_view(),
        name="documento-fuente",
    ),
]
