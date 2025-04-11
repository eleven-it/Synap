from django.urls import path
from . import views
from .views import firebase_config_js, login_view, logout_view, reset_password_view, register_view, perfil_view


app_name = "login"  # Definir el namespace para la app

urlpatterns = [
    path("", login_view, name="login"),  # Este name es el que usás en {% url 'login' %}
    # path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("reset-password/", reset_password_view, name="reset_password"),
    path("register/", register_view, name="register"),
    path("firebase-config.js", firebase_config_js, name="firebase_config_js"),
    path("perfil/", perfil_view, name="perfil"),
]