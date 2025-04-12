from django.urls import path
from core.views import usuarios_admin_view
from .views import error_403_view

app_name = "core"

urlpatterns = [
    path("usuarios/", usuarios_admin_view, name="usuarios"),
    path("403/", error_403_view, name="error_403"),    
]
