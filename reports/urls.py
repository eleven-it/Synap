from django.urls import path

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
    path("dashboard/<slug:slug>/", DashboardDetailView.as_view(), name="dashboard_detail"),
    path("builder/", ReportBuilderListView.as_view(), name="builder_list"),
    path("builder/data-map/", DataMapView.as_view(), name="data_map"),  # Ruta específica debe ir ANTES de la genérica
    path("builder/<slug:slug>/", ReportBuilderDetailView.as_view(), name="builder_detail"),
]


