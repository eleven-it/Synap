from django.urls import path

from .views import (
    ReportsCatalogView,
    DashboardDetailView,
    ReportsWorkspaceView,
)

app_name = "reports"

urlpatterns = [
    path("", ReportsCatalogView.as_view(), name="catalog"),
    path("workspace/", ReportsWorkspaceView.as_view(), name="workspace"),
    path("dashboard/<slug:slug>/", DashboardDetailView.as_view(), name="dashboard_detail"),
]


