from django.urls import path
from core import views

app_name = "core"

urlpatterns = [
    path("usuarios/", views.usuarios_admin_view, name="usuarios"),
    path("permisos/", views.listar_permisos, name="listar_permisos"),
    path("permisos/crear/", views.crear_permiso, name="crear_permiso"),
    path("permisos/eliminar/<int:permiso_id>/", views.eliminar_permiso, name="eliminar_permiso"),
    path("403/", views.error_403_view, name="error_403"),
]
