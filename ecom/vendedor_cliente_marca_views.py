"""API y vista HTML — config Vendedor → Cliente → Marca."""

from __future__ import annotations

from typing import Any, Dict, List

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
    _normalizar_ids_domicilio,
    anular_terna,
    buscar_clientes_activos,
    buscar_marcas_activas,
    buscar_sucursales_cliente,
    crear_terna,
    crear_ternas_lote,
    listar_ternas,
)
from ventas.services.vendedor_asignacion_mysql import buscar_vendedores_activos


def _sess_user(request) -> Dict[str, Any]:
    return (getattr(request, "session", None) or {}).get("user") or {}


def _usuario_mod_from_request(request) -> str:
    u = _sess_user(request)
    return str(u.get("cod_usuario") or u.get("nombre_usuario") or "-")[:60]


def _extraer_ids_domicilio(data: Dict[str, Any]) -> List[int]:
    """Lee ``ids_cliente_domicilio`` (lista) o un único ``id_cliente_domicilio`` (compat)."""
    ids_raw = data.get("ids_cliente_domicilio")
    if isinstance(ids_raw, list) and len(ids_raw) > 0:
        return _normalizar_ids_domicilio(ids_raw)
    single = to_int_or_none(data.get("id_cliente_domicilio"))
    if single is not None and single > 0:
        return [single]
    return []


def _mensaje_resumen_lote(resumen: Dict[str, Any]) -> str:
    partes: List[str] = []
    n_creadas = int(resumen.get("n_creadas") or 0)
    n_ya = int(resumen.get("n_ya_existian") or 0)
    n_conf = int(resumen.get("n_conflictos") or 0)
    n_err = int(resumen.get("n_errores") or 0)
    if n_creadas:
        partes.append(
            f"Se crearon {n_creadas} relación{'es' if n_creadas != 1 else ''}."
        )
    if n_ya:
        partes.append(f"{n_ya} ya existía{'n' if n_ya != 1 else ''}.")
    if n_conf:
        partes.append(f"{n_conf} conflicto{'s' if n_conf != 1 else ''}.")
    if n_err:
        partes.append(f"{n_err} error{'es' if n_err != 1 else ''}.")
    if not partes:
        return "No se procesó ninguna sucursal."
    return " ".join(partes)


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
                    "sucursales": reverse("ecom:api_vendedor_cliente_marca_sucursales"),
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
            id_cliente_domicilio=to_int_or_none(request.query_params.get("id_cliente_domicilio")),
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
        cod_viajante = to_int_or_none(data.get("CodViajante"))
        id_cliente = to_int_or_none(data.get("id_cliente"))
        cod_marca = to_int_or_none(data.get("CodMarca"))
        ids_domicilio = _extraer_ids_domicilio(data)
        usuario_mod = _usuario_mod_from_request(request)

        if not ids_domicilio:
            return Response(
                {"ok": False, "error": "Falta id_cliente_domicilio o ids_cliente_domicilio válidos."},
                status=400,
            )

        if len(ids_domicilio) == 1:
            try:
                ok, msg, terna = crear_terna(
                    base,
                    cod_viajante,
                    id_cliente,
                    cod_marca,
                    ids_domicilio[0],
                    usuario_mod=usuario_mod,
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

        resumen = crear_ternas_lote(
            base,
            cod_viajante,
            id_cliente,
            cod_marca,
            ids_domicilio,
            usuario_mod=usuario_mod,
        )
        ok_any = (resumen["n_creadas"] + resumen["n_ya_existian"]) > 0
        mensaje = _mensaje_resumen_lote(resumen)
        body: Dict[str, Any] = {
            "ok": ok_any,
            "message": mensaje,
            "resumen": resumen,
            "lote": True,
        }

        if not ok_any and resumen["n_conflictos"] > 0 and resumen["n_errores"] == 0:
            body["code"] = "conflicto_marca"
            body["error"] = mensaje
            return Response(body, status=409)
        if not ok_any:
            body["error"] = mensaje
            return Response(body, status=400)
        if resumen["n_creadas"] > 0:
            return Response(body, status=201)
        return Response(body, status=200)


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


class VendedorClienteMarcaSucursalesAPIView(APIView):
    permission_classes = [EcomConfigVendedorClienteMarcaPermission]

    def get(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"ok": False, "error": "Sin base_empresa."}, status=400)
        idc = to_int_or_none(request.query_params.get("id_cliente"))
        if idc is None:
            return Response({"ok": False, "error": "Falta id_cliente."}, status=400)
        rows = buscar_sucursales_cliente(
            base,
            idc,
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
