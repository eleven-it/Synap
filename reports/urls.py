from django.urls import path

from .views import ReportsCatalogView, DashboardDetailView, SavedDashboardsView

app_name = "reports"

urlpatterns = [
    path("", ReportsCatalogView.as_view(), name="catalog"),
    path("saved/", SavedDashboardsView.as_view(), name="saved_dashboards"),
    path("dashboard/<slug:slug>/", DashboardDetailView.as_view(), name="dashboard_detail"),
]


