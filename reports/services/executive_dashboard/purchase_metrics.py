"""Métricas compras — OC pendientes (paridad subconsulta BO)."""
from __future__ import annotations

from typing import Any

from .base import DashboardFilters, build_meta, round_money


def fetch_compras_resumen(cursor, filters: DashboardFilters) -> dict[str, Any]:
    notas = [
        "OC pendientes: cuentaproveedor TipoComprobante=OC, Estado=Pendiente, renglón stockp pendiente.",
        "No usar stock_deposito.saldo_pedido_proveedor.",
        "compras_validacion: pendiente_vb6",
    ]
    sql = """
        SELECT
            COUNT(DISTINCT cp_oc.CodigoMovimiento) AS oc_pendientes_cantidad,
            COALESCE(SUM(
                COALESCE(sp_oc.cantidad_pendiente,
                    sp_oc.Cantidad - COALESCE(sp_oc.cantidad_entregada, 0))
            ), 0) AS oc_pendientes_unidades,
            COALESCE(SUM(COALESCE(sp_oc.PrecioNetoxR, 0)), 0) AS oc_pendientes_importe
        FROM stockp sp_oc
        INNER JOIN cuentaproveedor cp_oc ON cp_oc.CodigoMovimiento = sp_oc.CodigoMovimiento
        WHERE cp_oc.TipoComprobante = 'OC'
            AND (sp_oc.Comprobante = 'OC' OR sp_oc.Comprobante IS NULL)
            AND cp_oc.Estado = 'Pendiente'
            AND cp_oc.Anulado = 'No'
            AND (sp_oc.anulado IS NULL OR sp_oc.anulado = 'No')
            AND (COALESCE(sp_oc.cantidad_pendiente,
                sp_oc.Cantidad - COALESCE(sp_oc.cantidad_entregada, 0)) > 0)
    """
    cursor.execute(sql)
    row = cursor.fetchone()
    cantidad = int(row[0] or 0) if row else 0
    unidades = float(row[1] or 0) if row else 0.0
    importe = float(row[2] or 0) if row else 0.0

    return {
        "oc_pendientes_cantidad": cantidad,
        "oc_pendientes_unidades": round(unidades, 2),
        "oc_pendientes_importe": round_money(importe),
        "disponible": True,
        "meta": build_meta(filters, notas_semanticas=notas),
    }
