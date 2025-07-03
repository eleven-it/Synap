from django.urls import path
from . import views

app_name = "proveedores"

urlpatterns = [
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("perfil/", views.perfil_view, name="perfil"),
    path("historial/", views.historial_view, name="historial"),
]
