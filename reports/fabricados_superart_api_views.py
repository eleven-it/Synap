# -*- coding: utf-8 -*-
"""APIs de autocompletado para el informe fabricados-superart."""
from __future__ import annotations

from django.http import JsonResponse
from django.views import View

from reports.permissions import user_can_access_fabricados_superart


class FabricadosSuperartMarcasBuscarAPIView(View):
    def get(self, request, *args, **kwargs):
        if not user_can_access_fabricados_superart(getattr(request, "user", None)):
            return JsonResponse({"detail": "No autorizado"}, status=403)
        from mpr.services_fabricados_superart import buscar_marcas_predictivo

        base_empresa = _base_empresa(request)
        if not base_empresa:
            return JsonResponse({"marcas": []})
        q = (request.GET.get("q") or "").strip()
        try:
            limit = int(request.GET.get("limit") or 25)
        except (ValueError, TypeError):
            limit = 25
        marcas = buscar_marcas_predictivo(base_empresa, q, limit=limit)
        return JsonResponse({"marcas": marcas})


class FabricadosSuperartSuperartBuscarAPIView(View):
    def get(self, request, *args, **kwargs):
        if not user_can_access_fabricados_superart(getattr(request, "user", None)):
            return JsonResponse({"detail": "No autorizado"}, status=403)
        from mpr.services_fabricados_superart import buscar_superart_predictivo

        base_empresa = _base_empresa(request)
        if not base_empresa:
            return JsonResponse({"superarts": []})
        q = (request.GET.get("q") or "").strip()
        try:
            limit = int(request.GET.get("limit") or 25)
        except (ValueError, TypeError):
            limit = 25
        items = buscar_superart_predictivo(base_empresa, q, limit=limit)
        return JsonResponse({"superarts": items})


def _base_empresa(request) -> str | None:
    session_user = (request.session or {}).get("user") or {}
    if isinstance(session_user, dict):
        be = (session_user.get("base_empresa") or "").strip()
        if be:
            return be
    return (getattr(request.user, "base_empresa", None) or "").strip() or None
