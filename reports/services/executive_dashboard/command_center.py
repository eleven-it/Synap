"""Orquestador dashboard gerencial."""
from __future__ import annotations

import logging
from typing import Any

from .base import DashboardFilters, build_meta, legacy_cursor
from .cross_metrics import fetch_cruzados_resumen
from .exceptions import LegacyReadError
from .inventory_metrics import fetch_inventario_resumen
from .manufacturing_metrics import fetch_manufactura_resumen
from .purchase_metrics import fetch_compras_resumen
from .tesoreria_metrics import fetch_tesoreria_resumen
from .ventas_cobros_metrics import fetch_ventas_cobros_resumen
from reports.services.executive_sales_summary import fetch_sucursales_ejecutivo

from .ventas_metrics import fetch_ventas_resumen

logger = logging.getLogger(__name__)

ENDPOINTS_RELATIVOS = {
    "ventas": "/api/reports/executive-dashboard/ventas/resumen/",
    "ventas_pedidos_pendientes": "/api/reports/executive-dashboard/ventas/pedidos-pendientes/",
    "ventas_remitos_nf": "/api/reports/executive-dashboard/ventas/remitos-no-facturados/",
    "inventario": "/api/reports/executive-dashboard/inventario/resumen/",
    "inventario_existencias": "/api/reports/executive-dashboard/inventario/existencias/",
    "compras": "/api/reports/executive-dashboard/compras/resumen/",
    "manufactura": "/api/reports/executive-dashboard/manufactura/resumen/",
    "cruzados": "/api/reports/executive-dashboard/cruzados/resumen/",
    "cruzados_backorder": "/api/reports/executive-dashboard/cruzados/backorder/",
    "tesoreria": "/api/reports/executive-dashboard/tesoreria/resumen/",
    "ventas_cobros": "/api/reports/executive-dashboard/ventas/cobros/resumen/",
    "executive_summary_dia": "/api/reports/executive-summary/",
}


def _area_sin_meta_interno(area_payload: dict[str, Any]) -> dict[str, Any]:
    """Quita meta anidado de sub-área para el orquestador."""
    out = {k: v for k, v in area_payload.items() if k != "meta"}
    return out


def _safe_legacy_area(name: str, fn, *args, **kwargs) -> dict[str, Any]:
    try:
        return fn(*args, **kwargs)
    except LegacyReadError as exc:
        logger.warning("Dashboard área %s: %s", name, exc)
        return {
            "disponible": False,
            "error": {"tipo": "legacy_transient_failure", "mensaje": str(exc)},
        }


def run_command_center(filters: DashboardFilters) -> dict[str, Any]:
    areas: dict[str, Any] = {}
    notas_globales: list[str] = []

    sucursales_disponibles: list = []
    try:
        with legacy_cursor(filters.base_empresa) as cursor:
            ventas_full = fetch_ventas_resumen(cursor, filters)
            areas["ventas"] = _area_sin_meta_interno(ventas_full)
            notas_globales.extend(ventas_full.get("meta", {}).get("notas_semanticas") or [])

            inv_full = _safe_legacy_area(
                "inventario", fetch_inventario_resumen, cursor, filters
            )
            if inv_full.get("disponible") is not False:
                areas["inventario"] = _area_sin_meta_interno(inv_full)
            else:
                areas["inventario"] = inv_full

            comp_full = _safe_legacy_area(
                "compras", fetch_compras_resumen, cursor, filters
            )
            if comp_full.get("disponible") is not False:
                areas["compras"] = _area_sin_meta_interno(comp_full)
            else:
                areas["compras"] = comp_full

            cruz_full = _safe_legacy_area(
                "cruzados", fetch_cruzados_resumen, cursor, filters
            )
            if cruz_full.get("disponible") is not False:
                areas["cruzados"] = _area_sin_meta_interno(cruz_full)
            else:
                areas["cruzados"] = cruz_full

            tes_full = _safe_legacy_area(
                "tesoreria", fetch_tesoreria_resumen, cursor, filters
            )
            if tes_full.get("disponible") is not False:
                areas["tesoreria"] = _area_sin_meta_interno(tes_full)
            else:
                areas["tesoreria"] = tes_full

            cob_full = _safe_legacy_area(
                "ventas_cobros", fetch_ventas_cobros_resumen, cursor, filters
            )
            if cob_full.get("disponible") is not False:
                areas["ventas_cobros"] = _area_sin_meta_interno(cob_full)
            else:
                areas["ventas_cobros"] = cob_full

            try:
                sucursales_disponibles = fetch_sucursales_ejecutivo(cursor)
            except Exception:
                logger.warning(
                    "No se pudieron cargar sucursales para command center", exc_info=True
                )
    except LegacyReadError:
        raise

    areas["manufactura"] = _area_sin_meta_interno(
        fetch_manufactura_resumen(filters.base_empresa, filters)
    )

    meta = build_meta(
        filters,
        notas_semanticas=notas_globales,
        endpoints=ENDPOINTS_RELATIVOS,
    )
    return {
        "fecha_referencia": filters.fecha_referencia.isoformat(),
        "periodo": {
            "inicio": filters.fecha_inicio.isoformat(),
            "fin": filters.fecha_fin.isoformat(),
        },
        "areas": areas,
        "sucursales_disponibles": sucursales_disponibles,
        "meta": meta,
    }
