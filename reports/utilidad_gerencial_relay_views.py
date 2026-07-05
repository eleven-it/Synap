"""
Vistas GET relay — Informe "Utilidad gerencial" (+ inflación)
(paridad mayoristapp ``relay-ventas-netas-gerencia.php`` modo ``ut`` / ``uti``).

- Operativo (``OperationalReportsPermission``): scope forzado al vendedor de sesión
  (``id_vendedor_usr``); no puede ampliar alcance vía ``filtrarPor`` (anti-bypass).
- Gerencial (``ManagerialReportsPermission``): ve todos; supervisor restringido a
  ``vendedor_a_cargo`` salvo filtro explícito de vendedor.

Modos: ``queInforme=seleccion`` (opciones de filtros) y el informe de utilidad.
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
from reports.services.utilidad_gerencial import get_utilidad_gerencial
from reports.services.ventas_netas import listado_seleccion_ventas_netas

logger = logging.getLogger(__name__)

_FILTRO_KEYS = {
    "cliente", "tipocliente", "vendedor", "articulo", "proveedor",
    "zona", "categoria", "rubro", "subrubro", "marca",
}


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


def parse_filtrar_por(raw: Optional[str]) -> Dict[str, List[Any]]:
    """
    Parsea ``clave|id|label||clave|id|label...`` → ``{clave: [id, ...]}``.

    Solo toma el índice 1 (id) de cada bloque, ignora ``todos`` y valores no
    numéricos (defensa anti-inyección; paridad ``armar_sql_utilidad``).
    """
    out: Dict[str, List[Any]] = {}
    if not raw or not str(raw).strip():
        return out
    for chunk in str(raw).split("||"):
        chunk = chunk.strip()
        if not chunk:
            continue
        parts = chunk.split("|")
        if len(parts) < 2:
            continue
        key = parts[0].strip().lower()
        val = parts[1].strip()
        if key not in _FILTRO_KEYS or not val or val.lower() == "todos":
            continue
        try:
            num = int(val)
        except ValueError:
            continue
        out.setdefault(key, []).append(num)
    return out


def parse_punto_venta(raw: Optional[str]) -> List[int]:
    """
    Parsea ``pvSelec`` ``id|nombre|linea||...``. Si algún bloque marca ``todos``
    devuelve lista vacía (= todos, sin filtro). Solo ids numéricos.
    """
    if not raw or not str(raw).strip():
        return []
    out: List[int] = []
    for chunk in str(raw).split("||"):
        chunk = chunk.strip()
        if not chunk:
            continue
        parts = chunk.split("|")
        if len(parts) >= 2 and parts[1].strip().lower() == "todos":
            return []
        val = parts[0].strip()
        if not val:
            continue
        try:
            out.append(int(val))
        except ValueError:
            continue
    return out


def _con_inflacion(request: Request) -> bool:
    qi = (request.query_params.get("queInforme") or "").strip().lower()
    if qi == "uti":
        return True
    modo = (request.query_params.get("modo") or "").strip().lower()
    return modo in ("inflacion", "inflación")


class _UtilidadGerencialBaseAPIView(APIView):
    scope = "operativo"

    def resolver_vendedor(self, request: Request) -> tuple[Optional[int], Optional[List[int]]]:
        """Devuelve (vendedor_id_forzado, vendedor_a_cargo). Subclase define alcance."""
        raise NotImplementedError

    def get(self, request: Request) -> Response:
        base = _base_empresa(request)
        if not base:
            return Response({"detail": "No se encontró base_empresa en la sesión."}, status=400)

        que_informe = (request.query_params.get("queInforme") or "").strip().lower()
        if que_informe == "seleccion":
            tabla = (request.query_params.get("tabla") or "").strip().lower()
            try:
                vend_id, cargo = self.resolver_vendedor(request)
            except PermissionError as exc:
                return Response({"detail": str(exc)}, status=403)
            try:
                data = listado_seleccion_ventas_netas(
                    base_empresa=base,
                    tabla=tabla,
                    usa_id_manual=bool(_session_user(request).get("usa_id_manual")),
                    vendedor_a_cargo=cargo if vend_id is None else [vend_id],
                )
            except Exception:
                logger.exception("utilidad_gerencial seleccion base=%s tabla=%s", base, tabla)
                return Response({"detail": "Error al listar opciones."}, status=500)
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

        listar_por = (
            request.query_params.get("listarPor")
            or request.query_params.get("agrupoPor")
            or request.query_params.get("listar_por")
            or "cliente"
        )
        filtros = parse_filtrar_por(
            request.query_params.get("filtrarPor") or request.query_params.get("filtrar_por")
        )
        punto_venta = parse_punto_venta(
            request.query_params.get("pvSelec") or request.query_params.get("puntoVenta")
        )
        tipo_inflacion = request.query_params.get("tipoInflacion") or request.query_params.get("tipo_inflacion")

        try:
            vend_id, cargo = self.resolver_vendedor(request)
        except PermissionError as exc:
            return Response({"detail": str(exc)}, status=403)

        try:
            result = get_utilidad_gerencial(
                base,
                fecha_desde=fd,
                fecha_hasta=fh,
                listar_por=listar_por,
                filtros=filtros,
                punto_venta_id=punto_venta,
                vendedor_id=vend_id,
                vendedor_a_cargo=cargo,
                con_inflacion=_con_inflacion(request),
                tipo_inflacion=tipo_inflacion,
            )
        except ValueError as ve:
            return Response({"detail": str(ve)}, status=400)
        except Exception:
            logger.exception("utilidad_gerencial base=%s", base)
            return Response({"detail": "Error al ejecutar el informe."}, status=500)

        result["meta"]["scope"] = self.scope
        return Response(result)


class UtilidadGerencialRelayAPIView(_UtilidadGerencialBaseAPIView):
    """GET /api/reports/utilidad-gerencial/relay/ (operativo)."""

    permission_classes = [OperationalReportsPermission]
    scope = "operativo"

    def resolver_vendedor(self, request: Request):
        propio = _session_user(request).get("id_vendedor_usr")
        propio_i: Optional[int] = None
        if propio is not None and str(propio).strip() != "":
            try:
                propio_i = int(propio)
            except (TypeError, ValueError):
                propio_i = None
        if propio_i is None:
            raise PermissionError(
                "Sesión sin id_vendedor_usr (CodViajante); no se puede aplicar el informe operativo."
            )
        return propio_i, None


class UtilidadGerencialGerenciaRelayAPIView(_UtilidadGerencialBaseAPIView):
    """GET /api/reports/utilidad-gerencial/relay/gerencia/ (gerencial)."""

    permission_classes = [ManagerialReportsPermission]
    scope = "gerencia"

    def resolver_vendedor(self, request: Request):
        cargo = _int_list_from_session(_session_user(request).get("vendedor_a_cargo"))
        return None, (cargo or None)
