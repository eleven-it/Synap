"""
Vistas GET relay — Informe "Cobranzas por vendedor"
(paridad mayoristapp ``listado-cobranzas-vendedor.php`` +
``informes-json/cobranza_lista_vendedor_resumen.php``).

Dos endpoints, mismo criterio que ventas netas / clientes sin ventas:
- Operativo (``OperationalReportsPermission``): scope forzado al vendedor de
  sesión (``id_vendedor_usr`` / ``vendedor_a_cargo``); ``codViajante`` entrante
  NO puede ampliar el alcance (anti-bypass, REQ-COB-006).
- Gerencial (``ManagerialReportsPermission``): ``codViajante=<id>`` restringe;
  ``todos``/ausente = todos los vendedores.

Modos: ``queInforme=seleccion`` (lista de vendedores) y el resumen de cobranzas.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any, Dict, List, Optional

from django.utils.dateparse import parse_date
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from reports.permissions import ManagerialReportsPermission, OperationalReportsPermission
from reports.services.clientes_sin_ventas import listado_vendedores_seleccion
from reports.services.cobranzas_vendedor import get_cobranzas_vendedor

logger = logging.getLogger(__name__)


def _session_user(request: Request) -> Dict[str, Any]:
    return (getattr(request, "session", None) or {}).get("user") or {}


def _base_empresa(request: Request) -> Optional[str]:
    bu = _session_user(request).get("base_empresa")
    return str(bu).strip() if bu else None


def _parse_date_qs(value: Optional[str]) -> Optional[date]:
    if value is None or not str(value).strip():
        return None
    return parse_date(str(value).strip()[:10])


def _int_list_from_session(raw: Any) -> List[int]:
    out: List[int] = []
    if isinstance(raw, (list, tuple)):
        for x in raw:
            try:
                out.append(int(x))
            except (TypeError, ValueError):
                continue
    return out


def _cod_viajante_qs(request: Request) -> Optional[int]:
    """``codViajante`` entrante como int; ``todos``/vacío/no numérico → None."""
    raw = request.query_params.get("codViajante") or request.query_params.get("cod_viajante")
    if raw is None:
        return None
    raw = str(raw).strip()
    if raw == "" or raw.lower() == "todos":
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


class _CobranzasVendedorBaseAPIView(APIView):
    """Lógica compartida operativo/gerencial."""

    scope = "operativo"

    def resolver_cod_viajantes(self, request: Request) -> Optional[List[int]]:
        """Lista final de CodViajante a consultar (None = todos)."""
        raise NotImplementedError

    def get(self, request: Request) -> Response:
        base = _base_empresa(request)
        if not base:
            return Response({"detail": "No se encontró base_empresa en la sesión."}, status=400)

        que_informe = (
            request.query_params.get("queInforme") or request.query_params.get("que_informe") or ""
        ).strip().lower()

        try:
            cod_viajantes = self.resolver_cod_viajantes(request)
        except PermissionError as exc:
            return Response({"detail": str(exc)}, status=403)

        if que_informe == "seleccion":
            try:
                data = listado_vendedores_seleccion(base, cod_viajantes=cod_viajantes)
            except Exception:
                logger.exception("cobranzas_vendedor seleccion base=%s", base)
                return Response({"detail": "Error al listar vendedores."}, status=500)
            return Response(data)

        fd = _parse_date_qs(
            request.query_params.get("fechaDesde") or request.query_params.get("fecha_desde")
        )
        fh = _parse_date_qs(
            request.query_params.get("fechaHasta") or request.query_params.get("fecha_hasta")
        )
        if not fd or not fh:
            return Response(
                {"detail": "Parámetros fechaDesde y fechaHasta son obligatorios (YYYY-MM-DD)."},
                status=400,
            )

        modo = request.query_params.get("modo") or request.query_params.get("tipo") or "mes"

        try:
            result = get_cobranzas_vendedor(
                base,
                fecha_desde=fd,
                fecha_hasta=fh,
                cod_viajantes=cod_viajantes,
                modo=modo,
            )
        except ValueError as ve:
            return Response({"detail": str(ve)}, status=400)
        except Exception:
            logger.exception("cobranzas_vendedor base=%s", base)
            return Response({"detail": "Error al ejecutar el informe."}, status=500)

        result["meta"] = {
            "scope": self.scope,
            "queInforme": que_informe or "cobranzas",
        }
        return Response(result)


class CobranzasVendedorRelayAPIView(_CobranzasVendedorBaseAPIView):
    """GET /api/reports/cobranzas-vendedor/relay/ (operativo)."""

    permission_classes = [OperationalReportsPermission]
    scope = "operativo"

    def resolver_cod_viajantes(self, request: Request) -> Optional[List[int]]:
        session_u = _session_user(request)
        cargo = _int_list_from_session(session_u.get("vendedor_a_cargo"))
        propio = session_u.get("id_vendedor_usr")
        propio_i: Optional[int] = None
        if propio is not None and str(propio).strip() != "":
            try:
                propio_i = int(propio)
            except (TypeError, ValueError):
                propio_i = None

        permitidos = cargo if cargo else ([propio_i] if propio_i is not None else [])
        if not permitidos:
            raise PermissionError(
                "Sesión sin id_vendedor_usr (CodViajante); no se puede aplicar el informe operativo."
            )
        # Anti-bypass: si envían codViajante, solo puede restringir dentro de lo permitido.
        pedido = _cod_viajante_qs(request)
        if pedido is not None and pedido in permitidos:
            return [pedido]
        return permitidos


class CobranzasVendedorGerenciaRelayAPIView(_CobranzasVendedorBaseAPIView):
    """GET /api/reports/cobranzas-vendedor/relay/gerencia/ (gerencial)."""

    permission_classes = [ManagerialReportsPermission]
    scope = "gerencia"

    def resolver_cod_viajantes(self, request: Request) -> Optional[List[int]]:
        pedido = _cod_viajante_qs(request)
        if pedido is not None:
            return [pedido]
        cargo = _int_list_from_session(_session_user(request).get("vendedor_a_cargo"))
        return cargo or None  # None = todos los vendedores
