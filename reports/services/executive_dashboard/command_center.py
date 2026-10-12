"""Orquestador dashboard gerencial."""
from __future__ import annotations

import logging
from typing import Any

from .area_visibility import resolve_cc_areas
from .base import DashboardFilters, build_meta, legacy_cursor, mpr_modulo_activo
from .cross_metrics import fetch_cruzados_resumen
from .comercial_v45 import fetch_comercial_ventas_v45
from .exceptions import is_legacy_db_error, legacy_area_failure_payload
from .inventory_metrics import fetch_inventario_resumen
from .manufacturing_metrics import fetch_manufactura_resumen
from .purchase_metrics import fetch_compras_resumen
from .banco_metrics import fetch_tesoreria_banco_resumen
from .tesoreria_metrics import fetch_tesoreria_resumen, list_movimientos_caja
from .ventas_cobros_metrics import fetch_ventas_cobros_resumen, list_cobros_detalle
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
    "tesoreria_banco": "/api/reports/executive-dashboard/tesoreria/banco/resumen/",
    "tesoreria_movimientos_caja": "/api/reports/executive-dashboard/tesoreria/movimientos-caja/",
    "ventas_cobros": "/api/reports/executive-dashboard/ventas/cobros/resumen/",
    "ventas_cobros_detalle": "/api/reports/executive-dashboard/ventas/cobros/detalle/",
    "executive_summary_dia": "/api/reports/executive-summary/",
}

ENDPOINT_AREA = {
    "ventas": "ventas",
    "ventas_pedidos_pendientes": "ventas",
    "ventas_remitos_nf": "ventas",
    "inventario": "inventario",
    "inventario_existencias": "inventario",
    "compras": "compras",
    "manufactura": "manufactura",
    "cruzados": "cruzados",
    "cruzados_backorder": "cruzados",
    "tesoreria": "tesoreria",
    "tesoreria_banco": "tesoreria",
    "tesoreria_movimientos_caja": "tesoreria",
    "ventas_cobros": "ventas_cobros",
    "ventas_cobros_detalle": "ventas_cobros",
}


def _area_sin_meta_interno(area_payload: dict[str, Any]) -> dict[str, Any]:
    """Quita meta anidado de sub-área para el orquestador."""
    out = {k: v for k, v in area_payload.items() if k != "meta"}
    return out


def _safe_legacy_area(name: str, fn, *args, **kwargs) -> dict[str, Any]:
    try:
        return fn(*args, **kwargs)
    except Exception as exc:
        if not is_legacy_db_error(exc):
            raise
        logger.warning("Dashboard área %s: %s", name, exc)
        return legacy_area_failure_payload(exc)


def run_command_center(
    filters: DashboardFilters, *, allowed_areas: dict[str, bool] | None = None,
    show_stock_costs: bool = True,
    v45_sales: bool = False, gross_sales: bool = False, compare_sales: bool = False,
) -> dict[str, Any]:
    areas: dict[str, Any] = {}
    notas_globales: list[str] = []
    mpr_on = mpr_modulo_activo()
    configured = resolve_cc_areas(mpr_active=mpr_on)
    selected = allowed_areas if allowed_areas is not None else configured
    areas_habilitadas = {
        key: bool(enabled and selected.get(key))
        for key, enabled in configured.items()
    }

    sucursales_disponibles: list = []
    with legacy_cursor(filters.base_empresa) as cursor:
        if areas_habilitadas.get("ventas"):
            if v45_sales:
                ventas_full = _safe_legacy_area(
                    "ventas", fetch_comercial_ventas_v45, cursor, filters,
                    gross=gross_sales, include_profit=show_stock_costs,
                    compare_previous=compare_sales,
                )
            else:
                ventas_full = _safe_legacy_area("ventas", fetch_ventas_resumen, cursor, filters)
            if ventas_full.get("disponible") is not False:
                areas["ventas"] = _area_sin_meta_interno(ventas_full)
                notas_globales.extend(ventas_full.get("meta", {}).get("notas_semanticas") or [])
            else:
                areas["ventas"] = ventas_full

        for area_name, fetch_fn in (
            ("inventario", fetch_inventario_resumen),
            ("compras", fetch_compras_resumen),
            ("cruzados", fetch_cruzados_resumen),
            ("ventas_cobros", fetch_ventas_cobros_resumen),
        ):
            if not areas_habilitadas.get(area_name):
                continue
            area_full = _safe_legacy_area(area_name, fetch_fn, cursor, filters)
            if area_name == "inventario" and not show_stock_costs:
                area_full["valor_stock"] = None
            if area_full.get("disponible") is not False:
                areas[area_name] = _area_sin_meta_interno(area_full)
            else:
                areas[area_name] = area_full

        if areas_habilitadas.get("tesoreria"):
            tesoreria_full = _safe_legacy_area(
                "tesoreria", fetch_tesoreria_resumen, cursor, filters
            )
            banco_full = _safe_legacy_area(
                "tesoreria_banco", fetch_tesoreria_banco_resumen, cursor, filters
            )
            if tesoreria_full.get("disponible") is not False:
                tesoreria_area = _area_sin_meta_interno(tesoreria_full)
                if banco_full.get("disponible") is not False:
                    tesoreria_area["banco"] = _area_sin_meta_interno(banco_full)
                else:
                    tesoreria_area["banco"] = banco_full
                areas["tesoreria"] = tesoreria_area
            else:
                areas["tesoreria"] = tesoreria_full

        if areas_habilitadas.get("ventas"):
            try:
                sucursales_disponibles = fetch_sucursales_ejecutivo(cursor)
                if filters.sucursales_filtro:
                    permitidas = set(filters.sucursales_filtro)
                    sucursales_disponibles = [
                        row for row in sucursales_disponibles
                        if row.get("id_sucursal") in permitidas
                    ]
            except Exception:
                logger.warning(
                    "No se pudieron cargar sucursales para command center", exc_info=True
                )

    if areas_habilitadas.get("manufactura"):
        areas["manufactura"] = _area_sin_meta_interno(
            fetch_manufactura_resumen(filters.base_empresa, filters)
        )

    meta = build_meta(
        filters,
        notas_semanticas=notas_globales,
        endpoints={
            key: url for key, url in ENDPOINTS_RELATIVOS.items()
            if areas_habilitadas.get(ENDPOINT_AREA.get(key, ""), False)
        },
        modulos={"mpr": mpr_on},
    )
    meta["areas_habilitadas"] = areas_habilitadas
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
