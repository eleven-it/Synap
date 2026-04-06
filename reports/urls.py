from django.urls import path, reverse_lazy
from django.views.generic import RedirectView

from .views import (
    ReportsCatalogView,
    DashboardDetailView,
    ReportsWorkspaceView,
    ReportBuilderListView,
    ReportBuilderDetailView,
    DataMapView,
)

app_name = "reports"

urlpatterns = [
    path("", ReportsCatalogView.as_view(), name="catalog"),
    path("workspace/", ReportsWorkspaceView.as_view(), name="workspace"),
    # Compatibilidad: slug histórico pending_orders → único slug pedidos-pendientes
    path(
        "dashboard/pending_orders/",
        RedirectView.as_view(
            url=reverse_lazy("reports:dashboard_detail", kwargs={"slug": "pedidos-pendientes"}),
            permanent=True,
        ),
        name="dashboard_pending_orders_redirect",
    ),
    # Catálogo: abre la vista ecom (informe operativo legacy mayoristapp)
    path(
        "dashboard/mayoristapp-presupuestos-vendedor/",
        RedirectView.as_view(
            url=reverse_lazy("ecom:mayoristapp_presupuestos_vendedor"),
            permanent=False,
        ),
        name="dashboard_mayoristapp_presupuestos_vendedor_redirect",
    ),
    path(
        "dashboard/mayoristapp-estado-pedidos-preparacion/",
        RedirectView.as_view(
            url=reverse_lazy("ecom:mayoristapp_estado_pedidos_preparacion"),
            permanent=False,
        ),
        name="dashboard_mayoristapp_estado_pedidos_preparacion_redirect",
    ),
    path("dashboard/<slug:slug>/", DashboardDetailView.as_view(), name="dashboard_detail"),
    path("builder/", ReportBuilderListView.as_view(), name="builder_list"),
    path("builder/data-map/", DataMapView.as_view(), name="data_map"),  # Ruta específica debe ir ANTES de la genérica
    path("builder/<slug:slug>/", ReportBuilderDetailView.as_view(), name="builder_detail"),
]


