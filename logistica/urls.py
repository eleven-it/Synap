from django.urls import path

from logistica.api_entregas import (
    LogisticaEntregasCatalogosAPIView,
    LogisticaEntregasClientesAutocompleteAPIView,
    LogisticaEntregasEntregaAPIView,
    LogisticaEntregasListaAPIView,
    LogisticaEntregasMotivosAPIView,
    LogisticaEntregasRemitoDetalleAPIView,
)
from logistica.views_entregas import LogisticaEntregasView

app_name = "logistica"

urlpatterns = [
    path("entregas/", LogisticaEntregasView.as_view(), name="entregas"),
    path(
        "api/entregas/lista/",
        LogisticaEntregasListaAPIView.as_view(),
        name="api_entregas_lista",
    ),
    path(
        "api/entregas/catalogos/",
        LogisticaEntregasCatalogosAPIView.as_view(),
        name="api_entregas_catalogos",
    ),
    path(
        "api/entregas/remito/<int:cod_mov>/",
        LogisticaEntregasRemitoDetalleAPIView.as_view(),
        name="api_entregas_remito",
    ),
    path(
        "api/entregas/entrega/",
        LogisticaEntregasEntregaAPIView.as_view(),
        name="api_entregas_entrega",
    ),
    path(
        "api/entregas/motivos-no-entrega/",
        LogisticaEntregasMotivosAPIView.as_view(),
        name="api_entregas_motivos",
    ),
    path(
        "api/entregas/clientes/autocomplete/",
        LogisticaEntregasClientesAutocompleteAPIView.as_view(),
        name="api_entregas_clientes_autocomplete",
    ),
]
