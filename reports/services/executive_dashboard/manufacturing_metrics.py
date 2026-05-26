"""Métricas manufactura — paridad TableroView MPR."""
from __future__ import annotations

from typing import Any

from mpr.exceptions import MprSchemaError
from mpr.services import (
    listar_lista_produccion_agrupada,
    listar_opt_listado,
    listar_pedidos_fabrica,
    listar_ventana_pack,
)

from .base import DashboardFilters, build_meta


def fetch_manufactura_resumen(base_empresa: str, filters: DashboardFilters) -> dict[str, Any]:
    notas = [
        "KPIs alineados al tablero MPR (/mpr/).",
        "pedidos_fabrica_pendientes: conteo con límite 5000 (ver meta).",
    ]
    try:
        agrupada = listar_lista_produccion_agrupada(
            base_empresa, limit=50, excluir_filas_opt_liberadas_mstock=True
        )
        unidades_pendientes = sum(
            float(r.get("cantidad_pendiente_prod") or 0) for r in agrupada
        )
        pedidos = listar_pedidos_fabrica(base_empresa, limit=5000, estado="Pendiente")
        pedidos_count = len(pedidos)
        atrasadas = listar_opt_listado(base_empresa, limit=500, solo_atrasadas=True)
        opt_atrasadas = len(
            {r["id_lista_produccion"] for r in atrasadas if r.get("id_lista_produccion")}
        )
        ventana_pack = listar_ventana_pack(base_empresa, limit=15)
        items_urgentes = min(15, len(ventana_pack) + opt_atrasadas)
        return {
            "pedidos_fabrica_pendientes": pedidos_count,
            "opt_atrasadas": opt_atrasadas,
            "unidades_pendientes_produccion": round(unidades_pendientes, 2),
            "items_urgentes": items_urgentes,
            "disponible": True,
            "meta": build_meta(filters, notas_semanticas=notas),
        }
    except MprSchemaError as exc:
        return {
            "pedidos_fabrica_pendientes": 0,
            "opt_atrasadas": 0,
            "unidades_pendientes_produccion": 0.0,
            "items_urgentes": 0,
            "disponible": False,
            "error": {"tipo": "mpr_schema_not_ready", "mensaje": str(exc)},
            "meta": build_meta(filters, notas_semanticas=notas),
        }
