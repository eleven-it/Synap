from django.urls import path

from factura_compra_captura.api import views

app_name = "factura_compra_captura_api"

urlpatterns = [
    path(
        "expedientes/",
        views.ExpedienteListCreateAPIView.as_view(),
        name="expediente-list-create",
    ),
    path(
        "expedientes/<uuid:pk>/",
        views.ExpedienteDetailPatchAPIView.as_view(),
        name="expediente-detail-patch",
    ),
    path(
        "expedientes/<uuid:pk>/transiciones/",
        views.ExpedienteTransicionAPIView.as_view(),
        name="expediente-transicion",
    ),
    path(
        "expedientes/<uuid:pk>/aprobar/",
        views.ExpedienteAprobarAPIView.as_view(),
        name="expediente-aprobar",
    ),
    path(
        "expedientes/<uuid:pk>/eventos/",
        views.ExpedienteEventosAPIView.as_view(),
        name="expediente-eventos",
    ),
    path(
        "expedientes/<uuid:expediente_pk>/documentos/",
        views.DocumentoFuenteListCreateAPIView.as_view(),
        name="documento-list-create",
    ),
    path(
        "expedientes/<uuid:expediente_pk>/documentos/<int:pk>/",
        views.DocumentoFuenteDetailAPIView.as_view(),
        name="documento-detail",
    ),
    path(
        "expedientes/<uuid:expediente_pk>/documentos/<int:pk>/reintentar-ocr/",
        views.DocumentoFuenteReintentarOcrAPIView.as_view(),
        name="documento-reintentar-ocr",
    ),
]
