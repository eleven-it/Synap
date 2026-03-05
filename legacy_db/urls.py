from django.urls import path

from legacy_db import views

app_name = "legacy_db"

urlpatterns = [
    path("proveedores/", views.api_proveedores_list, name="api_proveedores_list"),
    path("sucursales/", views.api_sucursales_list, name="api_sucursales_list"),
    path("precheck/", views.api_precheck, name="api_precheck"),
    path("op-lock-info/", views.api_op_lock_info, name="api_op_lock_info"),
]
