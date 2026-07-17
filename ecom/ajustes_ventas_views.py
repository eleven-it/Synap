"""Vista y API — Ajustes de ventas ecom (validación stock en pedidos)."""

from __future__ import annotations

from django.urls import reverse
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from ecom.catalogo_producto_relay_views import _session_base_empresa
from ecom.permissions import EcomConfigAjustesVentasPermission
from ecom.pedido_masivo_stub_views import _StubMayoristappPermisoView
from ecom.services.ecom_config_mysql import (
    KEY_ENVIAR_MAIL_CONFIRMAR_PEDIDO,
    KEY_VALIDAR_STOCK_PEDIDOS,
    escribir_valor_configuracion_ecom,
    guardar_config_workflow_comercial,
    leer_config_workflow_comercial,
    pedidos_envian_mail_confirmacion,
    pedidos_validan_stock,
    workflow_jerarquia_comercial_activo,
)


def _parse_bool_flag(raw) -> bool:
    return raw in (True, "true", "True", 1, "1", "Si", "si", "Sí")


class AjustesVentasView(_StubMayoristappPermisoView):
    """Pantalla ajustes de ventas — ``/ecom/mayoristapp/ajustes-ventas/``."""

    template_name = "ecom/ajustes_ventas.html"
    permiso_requerido = "ecom.config_ajustes_ventas"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        base = _session_base_empresa(self.request)
        ctx["bootstrap"] = {
            "validar_stock_pedidos": pedidos_validan_stock(base) if base else True,
            "enviar_mail_confirmar_pedido": pedidos_envian_mail_confirmacion(base) if base else True,
            "workflow_jerarquia_activo": workflow_jerarquia_comercial_activo(base) if base else False,
            "workflow": leer_config_workflow_comercial(base) if base else {},
            "puede_editar_jerarquia": self._puede_editar_jerarquia(),
            "urls": {
                "guardar": reverse("ecom:api_ajustes_ventas"),
                "guardar_workflow": reverse("ecom:api_ajustes_workflow"),
                "jerarquia": reverse("ecom:api_jerarquia_nodos"),
                "hub": reverse("ecom:mayoristapp_pedidos_hub"),
            },
        }
        return ctx

    def _puede_editar_jerarquia(self) -> bool:
        user = getattr(self.request, "user", None)
        if getattr(user, "is_superuser", False):
            return True
        if hasattr(user, "tiene_permiso") and user.tiene_permiso("ecom.jerarquia.editar"):
            return True
        return False


class AjustesVentasAPIView(APIView):
    permission_classes = [EcomConfigAjustesVentasPermission]

    def get(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"ok": False, "error": "Sin base_empresa."}, status=400)
        return Response(
            {
                "ok": True,
                "validar_stock_pedidos": pedidos_validan_stock(base),
                "enviar_mail_confirmar_pedido": pedidos_envian_mail_confirmacion(base),
            }
        )

    def post(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"ok": False, "error": "Sin base_empresa."}, status=400)
        data = request.data if isinstance(request.data, dict) else {}

        raw_stock = data.get("validar_stock_pedidos")
        raw_mail = data.get("enviar_mail_confirmar_pedido")
        if raw_stock is None and raw_mail is None:
            return Response(
                {
                    "ok": False,
                    "error": "Falta al menos un campo: validar_stock_pedidos o enviar_mail_confirmar_pedido.",
                },
                status=400,
            )

        resp_data = {"ok": True, "message": "Ajustes guardados."}

        if raw_stock is not None:
            activo_stock = _parse_bool_flag(raw_stock)
            valor_stock = "Si" if activo_stock else "No"
            try:
                ok = escribir_valor_configuracion_ecom(
                    base, KEY_VALIDAR_STOCK_PEDIDOS, valor_stock
                )
            except Exception as exc:
                return Response(
                    {
                        "ok": False,
                        "error": f"No se pudo guardar validar_stock_pedidos: {exc}",
                    },
                    status=500,
                )
            if not ok:
                return Response(
                    {
                        "ok": False,
                        "error": "No se pudo guardar validar_stock_pedidos (base o clave inválida).",
                    },
                    status=500,
                )
            resp_data["validar_stock_pedidos"] = activo_stock

        if raw_mail is not None:
            activo_mail = _parse_bool_flag(raw_mail)
            valor_mail = "Si" if activo_mail else "No"
            try:
                ok = escribir_valor_configuracion_ecom(
                    base, KEY_ENVIAR_MAIL_CONFIRMAR_PEDIDO, valor_mail
                )
            except Exception as exc:
                return Response(
                    {
                        "ok": False,
                        "error": f"No se pudo guardar enviar_mail_confirmar_pedido: {exc}",
                    },
                    status=500,
                )
            if not ok:
                return Response(
                    {
                        "ok": False,
                        "error": "No se pudo guardar enviar_mail_confirmar_pedido (base o clave inválida).",
                    },
                    status=500,
                )
            resp_data["enviar_mail_confirmar_pedido"] = activo_mail

        return Response(resp_data)


class AjustesWorkflowAPIView(APIView):
    """API flags workflow comercial — ``POST /ecom/api/mayoristapp/ajustes/workflow/``."""

    permission_classes = [EcomConfigAjustesVentasPermission]

    def get(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"ok": False, "error": "Sin base_empresa."}, status=400)
        cfg = leer_config_workflow_comercial(base)
        return Response({"ok": True, **cfg})

    def post(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"ok": False, "error": "Sin base_empresa."}, status=400)
        data = request.data if isinstance(request.data, dict) else {}
        if not data:
            return Response(
                {"ok": False, "error": "Body JSON vacío."},
                status=400,
            )
        try:
            cfg = guardar_config_workflow_comercial(base, data)
        except Exception as exc:
            return Response(
                {
                    "ok": False,
                    "error": f"No se pudo guardar en configuracion_ecom: {exc}",
                },
                status=500,
            )
        return Response(
            {
                "ok": True,
                **cfg,
                "message": "Workflow comercial guardado.",
            }
        )
