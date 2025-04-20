from django.urls import path
from . import views

app_name = "clientes"

urlpatterns = [
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("historial/", views.historial_view, name="historial"),
    path("perfil/", views.perfil_view, name="perfil"),
]
