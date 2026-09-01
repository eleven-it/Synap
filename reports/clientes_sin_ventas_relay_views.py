"""
Vistas GET relay — Informe "Clientes sin ventas por vendedor"
(paridad mayoristapp ``relay-clientes-vendedor.php``).

Dos endpoints, mismo criterio que ventas netas:
- Operativo (``OperationalReportsPermission``): scope forzado al vendedor de sesión
  (``id_vendedor_usr``) o su cartera ``vendedor_a_cargo``; ``filtrarPor`` NO puede
  ampliar el alcance (anti-bypass, REQ-CSV-004).
- Gerencial (``ManagerialReportsPermission``): respeta ``filtrarPor`` y
  ``vendedor_a_cargo``; sin filtro = todos.

Modos: ``queInforme=seleccion`` (lista de vendedores) y ``sin_ventas`` (listado).
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any, Dict, List, Optional, Sequence

from django.utils.dateparse import parse_date
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.administranet_types import to_int_or_none
from reports.permissions import ManagerialReportsPermission, OperationalReportsPermission
from reports.services.clientes_sin_ventas import (
    get_clientes_sin_ventas,
    listado_vendedores_seleccion,
    parse_filtrar_por,
)

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


def _parse_bool_qs(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in ("1", "true", "yes", "si", "sí")


def _int_list_from_session(raw: Any) -> List[int]:
    out: List[int] = []
    if isinstance(raw, (list, tuple)):
        for x in raw:
            try:
                out.append(int(x))
            except (TypeError, ValueError):
                continue
    return out


def _usa_id_manual(request: Request) -> bool:
    val = _session_user(request).get("usa_id_manual")
    if isinstance(val, str):
        return val.strip().lower() in ("1", "true", "si", "sí")
    return bool(val)


def _incluir_domicilio(request: Request) -> bool:
    """Query param ``incluirDomicilio`` con fallback al default de sesión."""
    qp = request.query_params.get("incluirDomicilio") or request.query_params.get("incluir_domicilio")
    if qp is not None and str(qp).strip() != "":
        return _parse_bool_qs(qp)
    return _parse_bool_qs(str(_session_user(request).get("usa_domicilio_cliente_informes") or ""))


def _parse_int_list_qs(request: Request, *keys: str) -> List[int]:
    """Normaliza query params repetibles o CSV a lista de enteros únicos."""
    qp = getattr(request, "query_params", None) or request.GET
    out: List[int] = []
    seen: set[int] = set()
    for key in keys:
        raw_values = qp.getlist(key)
        if not raw_values:
            single = qp.get(key)
            if single is not None and str(single).strip():
                raw_values = [single]
        for raw in raw_values:
            for part in str(raw).split(","):
                parsed = to_int_or_none(part.strip())
                if parsed is not None and parsed not in seen:
                    seen.add(parsed)
                    out.append(parsed)
    return out


class _ClientesSinVentasBaseAPIView(APIView):
    """Lógica compartida operativo/gerencial."""

    scope = "operativo"

    def resolver_cod_viajantes(
        self, request: Request, filtro_ids: List[int]
    ) -> Optional[List[int]]:
        """
        Devuelve la lista final de CodViajante a consultar (None = todos).
        Cada subclase define el alcance permitido.
        """
        raise NotImplementedError

    def get(self, request: Request) -> Response:
        base = _base_empresa(request)
        if not base:
            return Response({"detail": "No se encontró base_empresa en la sesión."}, status=400)

        que_informe = (
            request.query_params.get("queInforme") or request.query_params.get("que_informe") or ""
        ).strip().lower()

        filtro_ids = parse_filtrar_por(
            request.query_params.get("filtrarPor") or request.query_params.get("filtrar_por")
        )

        try:
            cod_viajantes = self.resolver_cod_viajantes(request, filtro_ids)
        except PermissionError as exc:
            return Response({"detail": str(exc)}, status=403)

        if que_informe == "seleccion":
            try:
                data = listado_vendedores_seleccion(base, cod_viajantes=cod_viajantes)
            except Exception:
                logger.exception("clientes_sin_ventas seleccion base=%s", base)
                return Response({"detail": "Error al listar vendedores."}, status=500)
            return Response(data)

        fd = _parse_date_qs(request.query_params.get("fechaDesde") or request.query_params.get("fecha_desde"))
        fh = _parse_date_qs(request.query_params.get("fechaHasta") or request.query_params.get("fecha_hasta"))
        if not fd or not fh:
            return Response(
                {"detail": "Parámetros fechaDesde y fechaHasta son obligatorios (YYYY-MM-DD)."},
                status=400,
            )

        try:
            sucursales = _parse_int_list_qs(request, "sucursales")
            puntos_venta = _parse_int_list_qs(request, "puntoVenta", "punto_venta")
            result = get_clientes_sin_ventas(
                base,
                fecha_desde=fd,
                fecha_hasta=fh,
                cod_viajantes=cod_viajantes,
                sucursales=sucursales or None,
                puntos_venta=puntos_venta or None,
                usa_id_manual=_usa_id_manual(request),
                incluir_domicilio=_incluir_domicilio(request),
            )
        except ValueError as ve:
            return Response({"detail": str(ve)}, status=400)
        except Exception:
            logger.exception("clientes_sin_ventas base=%s", base)
            return Response({"detail": "Error al ejecutar el informe."}, status=500)

        result_meta = {
            "scope": self.scope,
            "queInforme": que_informe or "sin_ventas",
            "ajax": request.query_params.get("ajax"),
        }
        # Estructura compatible con el front (lista con un objeto, como el relay PHP).
        return Response([{**result, "meta": result_meta}])


class ClientesSinVentasRelayAPIView(_ClientesSinVentasBaseAPIView):
    """GET /api/reports/clientes-sin-ventas/relay/ (operativo)."""

    permission_classes = [OperationalReportsPermission]
    scope = "operativo"

    def resolver_cod_viajantes(self, request: Request, filtro_ids: List[int]) -> Optional[List[int]]:
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
        # Anti-bypass: el filtro solo puede restringir dentro de lo permitido.
        if filtro_ids:
            interseccion = [v for v in filtro_ids if v in permitidos]
            return interseccion or permitidos
        return permitidos


class ClientesSinVentasGerenciaRelayAPIView(_ClientesSinVentasBaseAPIView):
    """GET /api/reports/clientes-sin-ventas/relay/gerencia/ (gerencial)."""

    permission_classes = [ManagerialReportsPermission]
    scope = "gerencia"

    def resolver_cod_viajantes(self, request: Request, filtro_ids: List[int]) -> Optional[List[int]]:
        if filtro_ids:
            return filtro_ids
        cargo = _int_list_from_session(_session_user(request).get("vendedor_a_cargo"))
        return cargo or None  # None = todos los vendedores
