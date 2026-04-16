from django.urls import path

from .views import ia_chat, ia_configuration, ia_home

app_name = "ia"

urlpatterns = [
    path("", ia_home, name="home"),
    path("configuracion/", ia_configuration, name="configuration"),
    path("agentes/<slug:slug>/chat/", ia_chat, name="chat"),
]
