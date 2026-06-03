"""
API del panel «Resumen ejecutivo (ventas)» y clasificación por sucursal.
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
from core.utils.empresa_sesion import (
    empresa_django_diagnostico,
    ensure_empresa_django_from_request,
    get_empresa_django_from_request,
)

from .models import SucursalCanalEjecutivo
from .permissions import ManagerialReportsPermission
from .services.connection_pool import get_mysql_pool
from .services.executive_sales_summary import fetch_sucursales_activas, run_executive_summary


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


def _parse_sucursales_filtro(qp) -> list[int] | None:
    """
    Query ``sucursales`` (repetible o CSV). Vacío = todas las clasificadas.
    Compat: ``sucursal`` único (legacy).
    """
    if not qp:
        return None
    raw_list = list(qp.getlist("sucursales"))
    if not raw_list and qp.get("sucursales"):
        raw_list = [qp.get("sucursales")]
    legacy = qp.get("sucursal")
    if legacy not in (None, "", "todas", "all", "*"):
        raw_list.append(legacy)
    ids: list[int] = []
    for raw in raw_list:
        for part in str(raw).split(","):
            part = part.strip()
            if not part or part.lower() in ("todas", "all", "*"):
                continue
            sid = to_int_or_none(part)
            if sid is not None and sid >= 0:
                ids.append(int(sid))
    if not ids:
        return None
    return sorted(set(ids))


def _parse_top_orden(qp) -> str | None:
    """Query ``top_orden``: ``importe_neto`` o ``unidades`` (normaliza el servicio)."""
    if not qp:
        return None
    raw = qp.get("top_orden")
    if raw is None or str(raw).strip() == "":
        return None
    return str(raw).strip()


def _sucursales_por_canal(empresa_id: int) -> tuple[list[int], list[int]]:
    qs = SucursalCanalEjecutivo.objects.filter(empresa_id=empresa_id)
    may = list(
        qs.filter(canal=SucursalCanalEjecutivo.Canal.MAYORISTA).values_list(
            "id_sucursal", flat=True
        )
    )
    mino = list(
        qs.filter(canal=SucursalCanalEjecutivo.Canal.MINORISTA).values_list(
            "id_sucursal", flat=True
        )
    )
    return may, mino


def _sucursal_item(s: dict) -> dict:
    sid = int(s["id_sucursal"])
    nombre = (s.get("nombre_sucursal") or f"Sucursal {sid}").strip()
    return {
        "id_sucursal": sid,
        "nombre_sucursal": nombre,
        "label": nombre,
    }


class ExecutiveSummaryAPIView(APIView):
    """GET: KPIs, series y tarjetas mayorista / minorista / consolidado."""

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
        sucursales_filtro = _parse_sucursales_filtro(request.query_params)
        top_orden = _parse_top_orden(request.query_params)
        may_ids, min_ids = _sucursales_por_canal(empresa.id) if empresa else ([], [])

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
                        sucursales_filtro=sucursales_filtro,
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


class SucursalCanalEjecutivoAPIView(APIView):
    """
    GET: sucursales activas (MySQL) + columnas según clasificación guardada.
    PUT: reemplaza asignaciones (mayorista / minorista); sin asignar no entra al reporte.
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
                    sucursales = fetch_sucursales_activas(cursor)
                finally:
                    cursor.close()
        except Exception as exc:
            return Response(
                {"detail": f"Error al listar sucursales: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        asig: dict[int, str] = {}
        if empresa:
            asig = {
                int(r.id_sucursal): r.canal
                for r in SucursalCanalEjecutivo.objects.filter(empresa=empresa)
            }
        col_may, col_min, col_centro = [], [], []
        for s in sucursales:
            item = _sucursal_item(s)
            sid = item["id_sucursal"]
            c = asig.get(sid)
            if c == SucursalCanalEjecutivo.Canal.MAYORISTA:
                col_may.append(item)
            elif c == SucursalCanalEjecutivo.Canal.MINORISTA:
                col_min.append(item)
            else:
                col_centro.append(item)

        clasificadas = sorted(
            col_may + col_min,
            key=lambda x: (x.get("nombre_sucursal") or "").lower(),
        )
        out = {
            "sucursales": sucursales,
            "sucursales_clasificadas": clasificadas,
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
            diag = empresa_django_diagnostico(request)
            out["meta"] = {
                "empresa_django": False,
                "nota": "No se encontró Empresa en Synap (CUIT/nombre) para esta base. "
                "Las clasificaciones no se pueden guardar hasta que exista el registro.",
                "diagnostico": diag,
            }
        return Response(out)

    def put(self, request, *args, **kwargs):
        empresa = ensure_empresa_django_from_request(request, auto_provision=True)
        if not empresa:
            diag = empresa_django_diagnostico(request)
            detail = (
                "No se encontró la empresa en Synap para esta sesión. "
                "Verifique que exista un registro en Empresa (administración Synap) con el mismo "
                "CUIT o nombre que DatosEmpresa de la base en sesión."
            )
            if diag.get("base_empresa"):
                detail += f" Base: {diag['base_empresa']}."
            if diag.get("nombre_datosempresa"):
                detail += f" Nombre AdministraNET: {diag['nombre_datosempresa']}."
            if diag.get("cuit_datosempresa"):
                detail += f" CUIT AdministraNET: {diag['cuit_datosempresa']}."
            if diag.get("empresa_inactiva_id"):
                detail += (
                    f" Existe Empresa id={diag['empresa_inactiva_id']} inactiva; "
                    "reactívela en Synap."
                )
            return Response(
                {"detail": detail, "diagnostico": diag},
                status=status.HTTP_400_BAD_REQUEST,
            )

        body = request.data or {}
        mayorista = body.get("mayorista") or body.get("mayorista_ids") or []
        minorista = body.get("minorista") or body.get("minorista_ids") or []
        if not isinstance(mayorista, list) or not isinstance(minorista, list):
            return Response(
                {"detail": "Se esperan listas mayorista y minorista de id_sucursal."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        may_set = {to_int_or_none(x) for x in mayorista}
        min_set = {to_int_or_none(x) for x in minorista}
        may_set.discard(None)
        min_set.discard(None)
        overlap = may_set & min_set
        if overlap:
            return Response(
                {"detail": f"Una sucursal no puede estar en ambas columnas: {sorted(overlap)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            SucursalCanalEjecutivo.objects.filter(empresa=empresa).delete()
            rows = []
            for sid in sorted(may_set):
                rows.append(
                    SucursalCanalEjecutivo(
                        empresa=empresa,
                        id_sucursal=int(sid),
                        canal=SucursalCanalEjecutivo.Canal.MAYORISTA,
                    )
                )
            for sid in sorted(min_set):
                rows.append(
                    SucursalCanalEjecutivo(
                        empresa=empresa,
                        id_sucursal=int(sid),
                        canal=SucursalCanalEjecutivo.Canal.MINORISTA,
                    )
                )
            if rows:
                SucursalCanalEjecutivo.objects.bulk_create(rows)

        return Response({"ok": True, "guardados": len(rows)})


# Compatibilidad: la URL antigua de PV delega en sucursal.
class PuntoVentaCanalEjecutivoAPIView(SucursalCanalEjecutivoAPIView):
    """Obsoleto: usar ``SucursalCanalEjecutivoAPIView`` (clasificación por sucursal)."""
