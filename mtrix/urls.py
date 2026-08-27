from django.urls import path

from mtrix import views

app_name = "mtrix"

urlpatterns = [
    path("", views.hub, name="hub"),
    path("preview/<str:tipo>/", views.preview, name="preview"),
    path("configuracion/", views.configuracion, name="configuracion"),
    path("jobs/", views.job_list, name="job_list"),
    path("jobs/<uuid:job_id>/", views.job_detail, name="job_detail"),
    path("jobs/<uuid:job_id>/descargar/", views.job_download, name="job_download"),
    path("jobs/<uuid:job_id>/enviar-sftp/", views.job_enviar_sftp, name="job_enviar_sftp"),
    path("generar/", views.generar, name="generar"),
    path("api/jobs/<uuid:job_id>/", views.api_job, name="api_job"),
    path("api/sftp/probar/", views.api_sftp_probar, name="api_sftp_probar"),
]
