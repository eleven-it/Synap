from django.urls import path

from factura_compra_captura import web_views

app_name = "factura_compra_captura_web"

urlpatterns = [
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
]
