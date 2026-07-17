from django.urls import path
from . import views
from . import webauthn_views
from .views import login_view, logout_view, perfil_view, get_empresas_api

app_name = "login"  # Definir el namespace para la app

urlpatterns = [
    path("", login_view, name="login"),  # Este name es el que usás en {% url 'login' %}
    path("logout/", logout_view, name="logout"),
    path("perfil/", perfil_view, name="perfil"),
    path("api/empresas/", get_empresas_api, name="get_empresas"),
    path(
        "api/webauthn/preference/",
        webauthn_views.preference,
        name="webauthn_preference",
    ),
    path(
        "api/webauthn/register/options/",
        webauthn_views.register_options,
        name="webauthn_register_options",
    ),
    path(
        "api/webauthn/register/verify/",
        webauthn_views.register_verify,
        name="webauthn_register_verify",
    ),
    path(
        "api/webauthn/authenticate/options/",
        webauthn_views.authenticate_options,
        name="webauthn_authenticate_options",
    ),
    path(
        "api/webauthn/authenticate/verify/",
        webauthn_views.authenticate_verify,
        name="webauthn_authenticate_verify",
    ),
    path(
        "api/webauthn/credentials/",
        webauthn_views.credentials_list,
        name="webauthn_credentials_list",
    ),
    path(
        "api/webauthn/credentials/revoke/",
        webauthn_views.credentials_revoke,
        name="webauthn_credentials_revoke",
    ),
]

