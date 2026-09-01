"""Filtros, metadatos y acceso MySQL para dashboard gerencial."""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Generator, Iterator

from django.utils import timezone

from core.utils.administranet_types import to_int_or_none

from .exceptions import InvalidDashboardFilters, LegacyReadError

DEFINICION_CONTRATO = "executive-dashboard-v1"


@dataclass(frozen=True)
class DashboardFilters:
    base_empresa: str
    fecha_referencia: date
    fecha_inicio: date
    fecha_fin: date
    sucursales_filtro: tuple[int, ...] = ()
    puntos_venta: tuple[int, ...] = ()
    limit: int = 100
    offset: int = 0
    busqueda: str | None = None

    @property
    def cod_sucursal(self) -> int | None:
        """Compat ``executive-dashboard-v1``: escalar solo si hay exactamente una sucursal."""
        return self.sucursales_filtro[0] if len(self.sucursales_filtro) == 1 else None

    @property
    def fecha_inicio_str(self) -> str:
        return self.fecha_inicio.isoformat()

    @property
    def fecha_fin_str(self) -> str:
        return self.fecha_fin.isoformat()

    @property
    def sucursales(self) -> list[int] | None:
        if not self.sucursales_filtro:
            return None
        return list(self.sucursales_filtro)


def _parse_int_list_qp(qp, *keys: str) -> tuple[int, ...]:
    """Lista de enteros desde query params repetibles o CSV."""
    if not qp:
        return ()
    raw_list: list = []
    for key in keys:
        if hasattr(qp, "getlist"):
            raw_list.extend(qp.getlist(key))
        val = qp.get(key) if hasattr(qp, "get") else None
        if val not in (None, ""):
            raw_list.append(val)
    ids: list[int] = []
    for raw in raw_list:
        for part in str(raw).split(","):
            part = part.strip()
            if not part or part.lower() in ("todas", "all", "*"):
                continue
            sid = to_int_or_none(part)
            if sid is not None and sid >= 0:
                ids.append(int(sid))
    return tuple(sorted(set(ids)))


def _parse_fecha(raw: str | None) -> date | None:
    if not raw:
        return None
    try:
        return datetime.strptime(str(raw)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def resolve_filters_from_query_params(
    qp,
    *,
    base_empresa: str,
    default_fecha: date | None = None,
) -> DashboardFilters:
    """Resuelve período canónico ``fecha_inicio`` / ``fecha_fin`` (default: hoy).

    ``fecha`` (legacy) sin intervalo explícito equivale a un solo día (inicio = fin).
    ``fecha_referencia`` se deriva siempre de ``fecha_fin`` (compatibilidad meta/API).
    """
    hoy = default_fecha or timezone.localdate()
    fi_raw = _parse_fecha(qp.get("fecha_inicio") if qp else None)
    ff_raw = _parse_fecha(qp.get("fecha_fin") if qp else None)
    fecha_legacy = _parse_fecha(qp.get("fecha") if qp else None)

    if fi_raw and ff_raw:
        fecha_inicio, fecha_fin = fi_raw, ff_raw
    elif fecha_legacy:
        fecha_inicio = fecha_fin = fecha_legacy
    else:
        fecha_inicio = fecha_fin = hoy

    if fecha_inicio > fecha_fin:
        raise InvalidDashboardFilters("fecha_inicio no puede ser posterior a fecha_fin.")

    sucursales_filtro = _parse_int_list_qp(qp, "sucursales")
    if not sucursales_filtro and qp:
        raw_suc = qp.get("sucursal")
        if raw_suc not in (None, "", "todas", "all", "*"):
            sid = to_int_or_none(raw_suc)
            if sid is not None and sid >= 0:
                sucursales_filtro = (int(sid),)

    puntos_venta = _parse_int_list_qp(qp, "puntos_venta", "punto_venta")

    limit = to_int_or_none(qp.get("limit") if qp else None) or 100
    offset = to_int_or_none(qp.get("offset") if qp else None) or 0
    limit = max(1, min(500, int(limit)))
    offset = max(0, int(offset))

    busqueda = None
    if qp:
        raw_q = qp.get("busqueda") or qp.get("q")
        if raw_q not in (None, ""):
            s = str(raw_q).strip()[:120]
            if len(s) >= 2:
                busqueda = s

    return DashboardFilters(
        base_empresa=str(base_empresa).strip(),
        fecha_referencia=fecha_fin,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        sucursales_filtro=sucursales_filtro,
        puntos_venta=puntos_venta,
        limit=limit,
        offset=offset,
        busqueda=busqueda,
    )


def build_meta(filters: DashboardFilters, **extra: Any) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "definicion": DEFINICION_CONTRATO,
        "base_empresa": filters.base_empresa,
        "fecha_referencia": filters.fecha_referencia.isoformat(),
        "periodo": {
            "inicio": filters.fecha_inicio.isoformat(),
            "fin": filters.fecha_fin.isoformat(),
        },
        "cod_sucursal_filtro": list(filters.sucursales_filtro)
        if filters.sucursales_filtro
        else None,
        "punto_venta_filtros": list(filters.puntos_venta) if filters.puntos_venta else None,
        "notas_semanticas": [],
    }
    meta.update(extra)
    return meta


def mpr_modulo_activo() -> bool:
    """True si el módulo ``mpr`` está activo en ModuleConfig y la app está instalada."""
    try:
        from core.module_manager import ModuleManager

        return ModuleManager().is_module_active("mpr")
    except Exception:
        return False


def sql_fecha_en_periodo(alias: str, filters: DashboardFilters) -> tuple[str, list]:
    """Cláusula AND para filtrar ``alias.Fecha`` en [fecha_inicio, fecha_fin]."""
    return (
        f" AND {alias}.Fecha >= %s AND {alias}.Fecha <= %s",
        [filters.fecha_inicio_str, filters.fecha_fin_str],
    )


def round_money(value: float) -> float:
    return round(float(value or 0), 2)


def build_paginated_response(
    filters: DashboardFilters,
    filas: list,
    total_registros: int,
    total_monto: float | None = None,
    *,
    notas_semanticas: list[str] | None = None,
) -> dict[str, Any]:
    """Respuesta estándar P1: filas + totales + paginación."""
    notas = list(notas_semanticas or [])
    payload: dict[str, Any] = {
        "filas": filas,
        "total_registros": int(total_registros),
        "limit": filters.limit,
        "offset": filters.offset,
        "disponible": True,
        "meta": build_meta(filters, notas_semanticas=notas),
    }
    if total_monto is not None:
        payload["total_monto"] = round_money(total_monto)
    return payload


@contextmanager
def legacy_cursor(base_empresa: str) -> Generator[Any, None, None]:
    """Cursor MySQL para base_empresa (pool Synap)."""
    from reports.services.connection_pool import get_mysql_pool

    pool = get_mysql_pool()
    try:
        conn_ctx = pool.get_connection(base_empresa)
    except Exception as exc:
        raise LegacyReadError(str(exc)) from exc

    with conn_ctx as conn:
        cursor = conn.cursor()
        try:
            try:
                cursor.execute("SET SESSION max_execution_time = 300000")
            except Exception:
                pass
            yield cursor
        finally:
            cursor.close()


def base_empresa_from_request(request) -> str | None:
    from django.conf import settings

    if hasattr(request, "session") and request.session:
        u = request.session.get("user") or {}
        be = u.get("base_empresa")
        if be:
            return str(be).strip() or None
    if hasattr(request.user, "base_empresa") and request.user.base_empresa:
        return str(request.user.base_empresa).strip() or None
    default = getattr(settings, "DEFAULT_BASE_EMPRESA", None)
    return str(default).strip() if default else None
