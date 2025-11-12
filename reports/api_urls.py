from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .api_views import (
    ReportCatalogAPIView,
    ReportQueryAPIView,
    KPIAPIView,
    ReportExportAPIView,
    SavedDashboardViewSet,
    WorkspaceSelectionAPIView,
)

app_name = "reports-api"

router = DefaultRouter()
router.register(r"saved-dashboards", SavedDashboardViewSet, basename="saved-dashboards")

urlpatterns = [
    path("catalog/", ReportCatalogAPIView.as_view(), name="reports-catalog"),
    path("query/", ReportQueryAPIView.as_view(), name="reports-query"),
    path("kpi/", KPIAPIView.as_view(), name="reports-kpi"),
    path("export/", ReportExportAPIView.as_view(), name="reports-export"),
    path("workspace/", WorkspaceSelectionAPIView.as_view(), name="reports-workspace"),
]
urlpatterns += router.urls


