from django.urls import path
from . import views
from .views import login_view, logout_view, perfil_view, get_empresas_api

app_name = "login"  # Definir el namespace para la app

urlpatterns = [
    path("", login_view, name="login"),  # Este name es el que usás en {% url 'login' %}
    path("logout/", logout_view, name="logout"),
    path("perfil/", perfil_view, name="perfil"),
    path("api/empresas/", get_empresas_api, name="get_empresas"),
]

