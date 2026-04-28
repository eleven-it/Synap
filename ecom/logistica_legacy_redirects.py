"""Redirecciones 301 desde rutas antiguas /ecom/api/logistica/… hacia el módulo ``logistica``."""

from django.http import HttpResponsePermanentRedirect
from django.urls import reverse


def redirect_api_remito_legacy(request, cod_mov):
    url = reverse("logistica:api_entregas_remito", kwargs={"cod_mov": cod_mov})
    if request.GET:
        url = f"{url}?{request.GET.urlencode()}"
    return HttpResponsePermanentRedirect(url)
