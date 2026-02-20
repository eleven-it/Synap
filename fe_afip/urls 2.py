from django.urls import path
from . import views

app_name = "fe_afip"
urlpatterns = [
    path("", views.config_list, name="config_list"),
    path("config/", views.config_form, name="config_form"),
    path("config/<int:pk>/edit/", views.config_form, name="config_edit"),
    path("browse/", views.browse_path, name="browse_path"),
    path("certificados/", views.cert_wizard, name="cert_wizard"),
    path("certificados/subir/", views.cert_upload, name="cert_upload"),
]
