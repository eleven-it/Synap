from django.urls import path

from .api_views import (
    ReportCatalogAPIView,
    ReportQueryAPIView,
    KPIAPIView,
    ReportExportAPIView,
    WorkspaceSelectionAPIView,
)

app_name = "reports-api"

urlpatterns = [
    path("catalog/", ReportCatalogAPIView.as_view(), name="reports-catalog"),
    path("query/", ReportQueryAPIView.as_view(), name="reports-query"),
    path("kpi/", KPIAPIView.as_view(), name="reports-kpi"),
    path("export/", ReportExportAPIView.as_view(), name="reports-export"),
    path("workspace/", WorkspaceSelectionAPIView.as_view(), name="reports-workspace"),
]


