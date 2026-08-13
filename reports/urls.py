from django.shortcuts import redirect
from django.urls import path

from .views import (
    ReportsCatalogView,
    DashboardDetailView,
    ReportsWorkspaceView,
    ReportBuilderListView,
    ReportBuilderDetailView,
    DataMapView,
    ValidacionSaldoStockView,
)

app_name = "reports"


def _redirect_ventas_bom_docenas(request):
    return redirect("reports:dashboard_detail", slug="ventas-bom-docenas")


urlpatterns = [
    path("", ReportsCatalogView.as_view(), name="catalog"),
    path("workspace/", ReportsWorkspaceView.as_view(), name="workspace"),
    path("analisis/validacion-saldo-stock/", ValidacionSaldoStockView.as_view(), name="validacion_saldo_stock"),
    path("ventas-bom-docenas/", _redirect_ventas_bom_docenas, name="ventas_bom_docenas_shortcut"),
    path("dashboard/<slug:slug>/", DashboardDetailView.as_view(), name="dashboard_detail"),
    path("builder/", ReportBuilderListView.as_view(), name="builder_list"),
    path("builder/data-map/", DataMapView.as_view(), name="data_map"),  # Ruta específica debe ir ANTES de la genérica
    path("builder/<slug:slug>/", ReportBuilderDetailView.as_view(), name="builder_detail"),
]


