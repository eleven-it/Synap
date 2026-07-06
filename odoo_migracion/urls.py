from django.urls import path

from . import views

app_name = "odoo_migracion"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("conexiones/", views.conexion_list, name="conexion_list"),
    path("conexiones/nueva/", views.conexion_form, name="conexion_create"),
    path("conexiones/<int:pk>/editar/", views.conexion_form, name="conexion_edit"),
    path("conexiones/<int:pk>/probar/", views.conexion_test, name="conexion_test"),
    path("conexiones/<int:pk>/rotar-api-key/", views.conexion_rotate_key, name="conexion_rotate_key"),
    path("jobs/", views.job_list, name="job_list"),
    path("inventario/", views.discovery_view, name="discovery"),
    path("wizard/", views.wizard_migracion, name="wizard"),
    path("validacion/", views.validacion_view, name="validacion"),
    path("mapeos/", views.mapping_list, name="mapping_list"),
]
