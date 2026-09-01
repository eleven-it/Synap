"""
Vistas GET relay ventas netas (paridad mayoristapp relay-ventas-netas*.php).

Permisos: OperationalReportsPermission (vendedor) y ManagerialReportsPermission (gerencia),
mismo patrón que ReportQueryAPIView + reports/permissions.py.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional, Sequence

from django.utils.dateparse import parse_date
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from reports.permissions import ManagerialReportsPermission, OperationalReportsPermission
from reports.services.ventas_netas import (
    get_ventas_netas,
    listado_seleccion_ventas_netas,
    parse_filtrar_por,
)
from core.utils.administranet_types import to_int_or_none


def _session_user(request: Request) -> Dict[str, Any]:
    return (getattr(request, "session", None) or {}).get("user") or {}


def _base_empresa(request: Request) -> Optional[str]:
    bu = _session_user(request).get("base_empresa")
    return str(bu).strip() if bu else None


def _parse_date_qs(value: Optional[str]) -> Optional[date]:
    if value is None or not str(value).strip():
        return None
    d = parse_date(str(value).strip()[:10])
    return d


def _parse_bool_qs(value: Optional[str]) -> bool:
    if value is None:
        return False
    return str(value).strip().lower() in ("1", "true", "yes", "si", "sí")


def _vendedor_a_cargo_from_session(request: Request) -> Optional[Sequence[int]]:
    """Lista CodViajante a cargo (supervisor); si no existe en sesión, None."""
    raw = _session_user(request).get("vendedor_a_cargo")
    if raw is None:
        return None
    if isinstance(raw, (list, tuple)):
        out: List[int] = []
        for x in raw:
            try:
                out.append(int(x))
            except (TypeError, ValueError):
                continue
        return out or None
    return None


def _parse_int_list_qs(request: Request, *keys: str) -> List[int]:
    """Normaliza query params repetibles o CSV a lista de enteros únicos."""
    qp = request.query_params
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


def _merge_relay_response(result: Dict[str, Any], extra_meta: Dict[str, Any]) -> Dict[str, Any]:
    body = {
        "data": result.get("data") or [],
        "cabeceras": result.get("cabeceras") or [],
        "titulos": result.get("titulos") or [],
        "meta": {**(result.get("meta") or {}), **extra_meta},
    }
    if extra_meta.get("grafico"):
        data = body["data"]
        cab = body["cabeceras"]
        if cab and data:
            label_key = cab[0]
            metric_key = cab[-1]
            gdata = [["label", "value"]]
            for row in data:
                gdata.append([str(row.get(label_key, "")), float(row.get(metric_key) or 0)])
            body["gdata"] = gdata
            body["goption"] = {
                "title": "Ventas netas relay",
                "legend": {"position": "none"},
            }
    return body


class VentasNetasRelayAPIView(APIView):
    """
    Relay operativo: filtra por CodViajante de sesión (id_vendedor_usr).
    GET /api/reports/ventas-netas/relay/
    """

    permission_classes = [OperationalReportsPermission]

    def get(self, request: Request) -> Response:
        base = _base_empresa(request)
        if not base:
            return Response(
                {"detail": "No se encontró base_empresa en la sesión."},
                status=400,
            )

        que_informe = (request.query_params.get("queInforme") or request.query_params.get("que_informe") or "").strip().lower()
        fd = _parse_date_qs(request.query_params.get("fechaDesde") or request.query_params.get("fecha_desde"))
        fh = _parse_date_qs(request.query_params.get("fechaHasta") or request.query_params.get("fecha_hasta"))
        if que_informe != "seleccion" and (not fd or not fh):
            return Response(
                {"detail": "Parámetros fechaDesde y fechaHasta son obligatorios (YYYY-MM-DD)."},
                status=400,
            )

        session_u = _session_user(request)
        vid = session_u.get("id_vendedor_usr")
        if vid is None:
            return Response(
                {"detail": "Sesión sin id_vendedor_usr (CodViajante); no se puede filtrar relay vendedor."},
                status=403,
            )
        try:
            vendedor_id = int(vid)
        except (TypeError, ValueError):
            return Response(
                {"detail": "id_vendedor_usr inválido en sesión."},
                status=400,
            )

        cargo = _vendedor_a_cargo_from_session(request)
        if cargo:
            vendedor_filtro_id = None
            vendedor_filtro_cargo = cargo
        else:
            vendedor_filtro_id = vendedor_id
            vendedor_filtro_cargo = None

        listar_por = request.query_params.get("listarPor") or request.query_params.get("listar_por") or "mes"
        tipo = request.query_params.get("tipo") or "monto"
        filtrar_raw = request.query_params.get("filtrarPor") or request.query_params.get("filtrar_por")
        rango_doble = _parse_bool_qs(
            request.query_params.get("rangoDoble") or request.query_params.get("rango_doble")
        )
        fd2 = _parse_date_qs(
            request.query_params.get("fechaDesdeDos") or request.query_params.get("fecha_desde_dos")
        )
        fh2 = _parse_date_qs(
            request.query_params.get("fechaHastaDos") or request.query_params.get("fecha_hasta_dos")
        )
        op_rango = request.query_params.get("opRango") or request.query_params.get("op_rango")

        try:
            if que_informe == "seleccion":
                tabla = request.query_params.get("tabla") or ""
                result = listado_seleccion_ventas_netas(
                    base_empresa=base,
                    tabla=tabla,
                    usa_id_manual=bool(session_u.get("usa_id_manual")),
                    vendedor_a_cargo=vendedor_filtro_cargo,
                )
            else:
                result = get_ventas_netas(
                    base_empresa=base,
                    fecha_desde=fd,
                    fecha_hasta=fh,
                    vendedor_id=vendedor_filtro_id,
                    listar_por=listar_por,
                    tipo=tipo,
                    filtros=parse_filtrar_por(filtrar_raw),
                    rango_doble=rango_doble,
                    fecha_desde_dos=fd2,
                    fecha_hasta_dos=fh2,
                    op_rango=op_rango,
                    incluir_utilidades=False,
                    punto_venta_id=None,
                    sucursales=_parse_int_list_qs(request, "sucursales") or None,
                    punto_venta=_parse_int_list_qs(request, "puntoVenta", "punto_venta") or None,
                    vendedor_a_cargo=vendedor_filtro_cargo,
                )
        except Exception:
            return Response(
                {"detail": "Error al ejecutar consulta ventas netas relay."},
                status=500,
            )

        extra = {
            "scope": "vendedor",
            "ajax": request.query_params.get("ajax"),
            "queInforme": que_informe or None,
            "grafico": _parse_bool_qs(request.query_params.get("grafico")),
        }
        return Response(_merge_relay_response(result, extra))


class VentasNetasGerenciaRelayAPIView(APIView):
    """
    Relay gerencia: sin filtro CodViajante salvo vendedor_a_cargo en sesión.
    GET /api/reports/ventas-netas/relay/gerencia/
    """

    permission_classes = [ManagerialReportsPermission]

    def get(self, request: Request) -> Response:
        base = _base_empresa(request)
        if not base:
            return Response(
                {"detail": "No se encontró base_empresa en la sesión."},
                status=400,
            )

        que_informe = (request.query_params.get("queInforme") or request.query_params.get("que_informe") or "").strip().lower()
        fd = _parse_date_qs(request.query_params.get("fechaDesde") or request.query_params.get("fecha_desde"))
        fh = _parse_date_qs(request.query_params.get("fechaHasta") or request.query_params.get("fecha_hasta"))
        if que_informe != "seleccion" and (not fd or not fh):
            return Response(
                {"detail": "Parámetros fechaDesde y fechaHasta son obligatorios (YYYY-MM-DD)."},
                status=400,
            )

        listar_por = request.query_params.get("listarPor") or request.query_params.get("listar_por") or "mes"
        tipo = request.query_params.get("tipo") or "monto"
        filtrar_raw = request.query_params.get("filtrarPor") or request.query_params.get("filtrar_por")
        rango_doble = _parse_bool_qs(
            request.query_params.get("rangoDoble") or request.query_params.get("rango_doble")
        )
        fd2 = _parse_date_qs(
            request.query_params.get("fechaDesdeDos") or request.query_params.get("fecha_desde_dos")
        )
        fh2 = _parse_date_qs(
            request.query_params.get("fechaHastaDos") or request.query_params.get("fecha_hasta_dos")
        )
        op_rango = request.query_params.get("opRango") or request.query_params.get("op_rango")

        sucursales = _parse_int_list_qs(request, "sucursales") or None
        puntos_venta = _parse_int_list_qs(request, "puntoVenta", "punto_venta")

        punto_venta_id: Optional[int] = None
        punto_venta: Optional[List[int]] = None
        if len(puntos_venta) == 1:
            raw_pv = (
                request.query_params.get("puntoVenta")
                or request.query_params.get("punto_venta")
                or ""
            ).strip()
            if raw_pv and "," not in raw_pv:
                punto_venta_id = puntos_venta[0]
            else:
                punto_venta = puntos_venta
        elif len(puntos_venta) > 1:
            punto_venta = puntos_venta

        incluir_utilidades = que_informe in ("ut", "uti")

        kwargs_gerencia: Dict[str, Any] = {}
        for key in ("decimales", "grafico", "tipoInflacion", "artEnsambVenta"):
            if key in request.query_params:
                kwargs_gerencia[key] = request.query_params.get(key)

        cargo = _vendedor_a_cargo_from_session(request)

        try:
            if que_informe == "seleccion":
                tabla = request.query_params.get("tabla") or ""
                result = listado_seleccion_ventas_netas(
                    base_empresa=base,
                    tabla=tabla,
                    usa_id_manual=bool(_session_user(request).get("usa_id_manual")),
                    vendedor_a_cargo=cargo,
                )
            else:
                result = get_ventas_netas(
                    base_empresa=base,
                    fecha_desde=fd,
                    fecha_hasta=fh,
                    vendedor_id=None,
                    listar_por=listar_por,
                    tipo=tipo,
                    filtros=parse_filtrar_por(filtrar_raw),
                    rango_doble=rango_doble,
                    fecha_desde_dos=fd2,
                    fecha_hasta_dos=fh2,
                    op_rango=op_rango,
                    incluir_utilidades=incluir_utilidades,
                    punto_venta_id=punto_venta_id,
                    sucursales=sucursales,
                    punto_venta=punto_venta,
                    vendedor_a_cargo=cargo,
                    **kwargs_gerencia,
                )
        except Exception:
            return Response(
                {"detail": "Error al ejecutar consulta ventas netas relay gerencia."},
                status=500,
            )

        extra = {
            "scope": "gerencia",
            "queInforme": que_informe or None,
            "ajax": request.query_params.get("ajax"),
            "grafico": _parse_bool_qs(request.query_params.get("grafico")),
        }
        return Response(_merge_relay_response(result, extra))
