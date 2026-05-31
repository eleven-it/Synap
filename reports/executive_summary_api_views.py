"""
API del panel «Resumen ejecutivo (ventas)» y clasificación PV.
"""
from __future__ import annotations

from datetime import date, datetime

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.administranet_types import to_int_or_none
from core.utils.empresa_sesion import get_empresa_django_from_request

from .models import PuntoVentaCanalEjecutivo
from .permissions import ManagerialReportsPermission
from .services.connection_pool import get_mysql_pool
from .services.executive_sales_summary import fetch_puntos_venta_activos, run_executive_summary


def _base_empresa(request) -> str | None:
    if hasattr(request, "session") and request.session:
        u = request.session.get("user") or {}
        be = u.get("base_empresa")
        if be:
            return str(be).strip() or None
    if hasattr(request.user, "base_empresa") and request.user.base_empresa:
        return str(request.user.base_empresa).strip() or None
    return getattr(settings, "DEFAULT_BASE_EMPRESA", None)


def _parse_fecha_opcional(raw) -> date | None:
    if not raw:
        return None
    try:
        return datetime.strptime(str(raw)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _resolve_fecha_referencia(qp) -> date:
    """Día de referencia intradía: ``fecha_fin`` del intervalo, atajo ``fecha`` o hoy."""
    fi = _parse_fecha_opcional(qp.get("fecha_inicio") if qp else None)
    ff = _parse_fecha_opcional(qp.get("fecha_fin") if qp else None)
    if fi and ff:
        return ff
    legacy = _parse_fecha_opcional(qp.get("fecha") if qp else None)
    if legacy:
        return legacy
    return timezone.localdate()


def _parse_cod_sucursal(qp) -> int | None:
    """Query ``sucursal``: id numérico o vacío / ``todas`` = sin filtro."""
    if not qp:
        return None
    raw = qp.get("sucursal")
    if raw in (None, "", "todas", "all", "*"):
        return None
    sid = to_int_or_none(raw)
    if sid is None or sid < 0:
        return None
    return int(sid)


def _parse_top_orden(qp) -> str | None:
    """Query ``top_orden``: ``importe_neto`` o ``unidades`` (normaliza el servicio)."""
    if not qp:
        return None
    raw = qp.get("top_orden")
    if raw is None or str(raw).strip() == "":
        return None
    return str(raw).strip()


def _ids_por_canal(empresa_id: int) -> tuple[list[int], list[int]]:
    qs = PuntoVentaCanalEjecutivo.objects.filter(empresa_id=empresa_id)
    may = list(qs.filter(canal=PuntoVentaCanalEjecutivo.Canal.MAYORISTA).values_list("id_pv", flat=True))
    mino = list(qs.filter(canal=PuntoVentaCanalEjecutivo.Canal.MINORISTA).values_list("id_pv", flat=True))
    return may, mino


class ExecutiveSummaryAPIView(APIView):
    """GET: KPIs, series y split mayorista/minorista."""

    permission_classes = [ManagerialReportsPermission]

    def get(self, request, *args, **kwargs):
        base = _base_empresa(request)
        if not base:
            return Response(
                {"detail": "No se pudo determinar la base de datos de la empresa."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        empresa = get_empresa_django_from_request(request)
        fecha_ref = _resolve_fecha_referencia(request.query_params)
        cod_sucursal = _parse_cod_sucursal(request.query_params)
        top_orden = _parse_top_orden(request.query_params)
        may_ids, min_ids = _ids_por_canal(empresa.id) if empresa else ([], [])

        pool = get_mysql_pool()
        try:
            with pool.get_connection(base) as conn:
                cursor = conn.cursor()
                try:
                    payload = run_executive_summary(
                        cursor,
                        fecha_ref,
                        may_ids,
                        min_ids,
                        cod_sucursal=cod_sucursal,
                        top_productos_orden=top_orden,
                    )
                finally:
                    cursor.close()
        except Exception as exc:
            return Response(
                {"detail": f"Error al consultar datos: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if not empresa:
            meta = payload.get("meta") or {}
            meta["empresa_django"] = False
            meta["nota"] = (
                "Clasificación mayorista/salón no aplicada: no hay Empresa Django vinculada "
                "(CUIT/nombre) a esta base de sesión."
            )
            payload["meta"] = meta

        return Response(payload)


class PuntoVentaCanalEjecutivoAPIView(APIView):
    """
    GET: lista de PV activos (MySQL) + columnas según asignación guardada.
    PUT: reemplaza asignaciones (mayorista / minorista); el resto queda sin asignar.
    """

    permission_classes = [ManagerialReportsPermission]

    def get(self, request, *args, **kwargs):
        base = _base_empresa(request)
        if not base:
            return Response(
                {"detail": "No se pudo determinar la base de datos de la empresa."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        empresa = get_empresa_django_from_request(request)

        pool = get_mysql_pool()
        try:
            with pool.get_connection(base) as conn:
                cursor = conn.cursor()
                try:
                    pvs = fetch_puntos_venta_activos(cursor)
                finally:
                    cursor.close()
        except Exception as exc:
            return Response(
                {"detail": f"Error al listar puntos de venta: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        asig = {}
        if empresa:
            asig = {
                r.id_pv: r.canal
                for r in PuntoVentaCanalEjecutivo.objects.filter(empresa=empresa)
            }
        col_may, col_min, col_centro = [], [], []
        for pv in pvs:
            id_pv = pv["id_pv"]
            c = asig.get(id_pv)
            if c == PuntoVentaCanalEjecutivo.Canal.MAYORISTA:
                col_may.append(pv)
            elif c == PuntoVentaCanalEjecutivo.Canal.MINORISTA:
                col_min.append(pv)
            else:
                col_centro.append(pv)

        out = {
            "puntos_venta": pvs,
            "columnas": {
                "mayorista": col_may,
                "sin_asignar": col_centro,
                "minorista": col_min,
            },
            "conteos": {
                "mayorista": len(col_may),
                "sin_asignar": len(col_centro),
                "minorista": len(col_min),
            },
        }
        if not empresa:
            out["meta"] = {
                "empresa_django": False,
                "nota": "No se encontró Empresa en Synap (CUIT/nombre) para esta base. "
                "Las clasificaciones PV no se pueden guardar hasta que exista el registro.",
            }
        return Response(out)

    def put(self, request, *args, **kwargs):
        empresa = get_empresa_django_from_request(request)
        if not empresa:
            return Response(
                {
                    "detail": "No se encontró la empresa en Synap para esta sesión. "
                    "Verifique que exista un registro en Empresa con el mismo CUIT o nombre que DatosEmpresa "
                    "de la base indicada en sesión (base_empresa).",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        body = request.data or {}
        mayorista = body.get("mayorista") or body.get("mayorista_ids") or []
        minorista = body.get("minorista") or body.get("minorista_ids") or []
        if not isinstance(mayorista, list) or not isinstance(minorista, list):
            return Response(
                {"detail": "Se esperan listas mayorista y minorista de id_pv."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        may_set = {to_int_or_none(x) for x in mayorista}
        min_set = {to_int_or_none(x) for x in minorista}
        may_set.discard(None)
        min_set.discard(None)
        overlap = may_set & min_set
        if overlap:
            return Response(
                {"detail": f"Un PV no puede estar en ambas columnas: {sorted(overlap)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            PuntoVentaCanalEjecutivo.objects.filter(empresa=empresa).delete()
            rows = []
            for pid in sorted(may_set):
                rows.append(
                    PuntoVentaCanalEjecutivo(
                        empresa=empresa,
                        id_pv=int(pid),
                        canal=PuntoVentaCanalEjecutivo.Canal.MAYORISTA,
                    )
                )
            for pid in sorted(min_set):
                rows.append(
                    PuntoVentaCanalEjecutivo(
                        empresa=empresa,
                        id_pv=int(pid),
                        canal=PuntoVentaCanalEjecutivo.Canal.MINORISTA,
                    )
                )
            if rows:
                PuntoVentaCanalEjecutivo.objects.bulk_create(rows)

        return Response({"ok": True, "guardados": len(rows)})
