from django.urls import path

from .views import ReportsCatalogView, DashboardDetailView, ReportsWorkspaceView, ReportsWorkspaceTVView

app_name = "reports"

urlpatterns = [
    path("", ReportsCatalogView.as_view(), name="catalog"),
    path("workspace/", ReportsWorkspaceView.as_view(), name="workspace"),
    path("workspace/tv/", ReportsWorkspaceTVView.as_view(), name="workspace_tv"),
    path(
        "workspace/tv/",
        ReportsWorkspaceTVView.as_view(),
        name="workspace_tv",
    ),
    path("dashboard/<slug:slug>/", DashboardDetailView.as_view(), name="dashboard_detail"),
]


