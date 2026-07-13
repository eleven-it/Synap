"""API y vista HTML — config Vendedor → Cliente → Marca."""

from __future__ import annotations

from typing import Any, Dict

from django.urls import reverse
from django.views.generic import TemplateView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.administranet_types import to_int_or_none
from ecom.catalogo_producto_relay_views import _session_base_empresa
from ecom.permissions import EcomConfigVendedorClienteMarcaPermission
from ecom.pedido_masivo_stub_views import _StubMayoristappPermisoView
from ecom.services.vendedor_cliente_marca import (
    ConflictoMarcaCliente,
    anular_terna,
    buscar_clientes_activos,
    buscar_marcas_activas,
    crear_terna,
    listar_ternas,
)
from ventas.services.vendedor_asignacion_mysql import buscar_vendedores_activos


def _sess_user(request) -> Dict[str, Any]:
    return (getattr(request, "session", None) or {}).get("user") or {}


def _usuario_mod_from_request(request) -> str:
    u = _sess_user(request)
    return str(u.get("cod_usuario") or u.get("nombre_usuario") or "-")[:60]


class ConfigVendedorClienteMarcaView(_StubMayoristappPermisoView):
    """Pantalla config ternas — ``/ecom/mayoristapp/config/vendedor-cliente-marca/``."""

    template_name = "ecom/config_vendedor_cliente_marca.html"
    permiso_requerido = "ecom.config_vendedor_cliente_marca"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(
            {
                "urls_api": {
                    "ternas": reverse("ecom:api_vendedor_cliente_marca_ternas"),
                    "crear": reverse("ecom:api_vendedor_cliente_marca_crear"),
                    "anular": reverse("ecom:api_vendedor_cliente_marca_anular"),
                    "vendedores": reverse("ecom:api_vendedor_cliente_marca_vendedores"),
                    "clientes": reverse("ecom:api_vendedor_cliente_marca_clientes"),
                    "marcas": reverse("ecom:api_vendedor_cliente_marca_marcas"),
                    "hub": reverse("ecom:mayoristapp_pedidos_hub"),
                },
            }
        )
        return ctx


class VendedorClienteMarcaTernasAPIView(APIView):
    permission_classes = [EcomConfigVendedorClienteMarcaPermission]

    def get(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"ok": False, "error": "Sin base_empresa."}, status=400)
        ok, err, rows = listar_ternas(
            base,
            cod_viajante=to_int_or_none(request.query_params.get("CodViajante")),
            id_cliente=to_int_or_none(request.query_params.get("id_cliente")),
            solo_activas=str(request.query_params.get("solo_activas", "1")).strip()
            not in ("0", "false", "False", "no", "No"),
            limit=to_int_or_none(request.query_params.get("limit")) or 200,
        )
        if not ok:
            return Response({"ok": False, "error": err}, status=400)
        return Response({"ok": True, "ternas": rows})


class VendedorClienteMarcaCrearAPIView(APIView):
    permission_classes = [EcomConfigVendedorClienteMarcaPermission]

    def post(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"ok": False, "error": "Sin base_empresa."}, status=400)
        data = request.data if isinstance(request.data, dict) else {}
        try:
            ok, msg, terna = crear_terna(
                base,
                to_int_or_none(data.get("CodViajante")),
                to_int_or_none(data.get("id_cliente")),
                to_int_or_none(data.get("CodMarca")),
                usuario_mod=_usuario_mod_from_request(request),
            )
        except ConflictoMarcaCliente as exc:
            return Response(
                {
                    "ok": False,
                    "code": "conflicto_marca",
                    "error": exc.message,
                    "message": exc.message,
                    "dueno": exc.dueno,
                },
                status=409,
            )
        if not ok:
            return Response({"ok": False, "error": msg}, status=400)
        return Response({"ok": True, "message": msg, "terna": terna}, status=201)


class VendedorClienteMarcaAnularAPIView(APIView):
    permission_classes = [EcomConfigVendedorClienteMarcaPermission]

    def post(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"ok": False, "error": "Sin base_empresa."}, status=400)
        data = request.data if isinstance(request.data, dict) else {}
        tid = to_int_or_none(data.get("id") or data.get("id_terna"))
        ok, msg = anular_terna(base, tid, usuario_mod=_usuario_mod_from_request(request))
        if not ok:
            return Response({"ok": False, "error": msg}, status=400)
        return Response({"ok": True, "message": msg})


class VendedorClienteMarcaVendedoresAPIView(APIView):
    permission_classes = [EcomConfigVendedorClienteMarcaPermission]

    def get(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"ok": False, "error": "Sin base_empresa."}, status=400)
        ok, err, rows = buscar_vendedores_activos(
            base,
            q=str(request.query_params.get("q") or ""),
            limit=to_int_or_none(request.query_params.get("limit")) or 40,
        )
        if not ok:
            return Response({"ok": False, "error": err}, status=400)
        # Normalizar clave CodViajante para el front de ternas
        out = [
            {
                "CodViajante": r["id_vendedor"],
                "nombre": r["nombre"],
                "etiqueta": r["etiqueta"],
            }
            for r in rows
        ]
        return Response({"ok": True, "items": out})


class VendedorClienteMarcaClientesAPIView(APIView):
    permission_classes = [EcomConfigVendedorClienteMarcaPermission]

    def get(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"ok": False, "error": "Sin base_empresa."}, status=400)
        rows = buscar_clientes_activos(
            base,
            q=str(request.query_params.get("q") or ""),
            limit=to_int_or_none(request.query_params.get("limit")) or 30,
        )
        return Response({"ok": True, "items": rows})


class VendedorClienteMarcaMarcasAPIView(APIView):
    permission_classes = [EcomConfigVendedorClienteMarcaPermission]

    def get(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"ok": False, "error": "Sin base_empresa."}, status=400)
        rows = buscar_marcas_activas(
            base,
            q=str(request.query_params.get("q") or ""),
            limit=to_int_or_none(request.query_params.get("limit")) or 30,
        )
        return Response({"ok": True, "items": rows})
