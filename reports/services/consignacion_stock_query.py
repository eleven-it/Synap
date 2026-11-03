# -*- coding: utf-8 -*-
"""Consultas read-only stock en consignación (remitos − facturado − devuelto)."""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Sequence

from core.utils.administranet_types import to_date_or_none

from mpr.services import mysql_cursor
from reports.services.articulo_pack_unidades import (
    docenas_desde_prendas,
    prendas_desde_packs,
    unidades_por_pack_compras,
)

logger = logging.getLogger(__name__)

CONSIGNACION_DETALLE_KEYWORD = "EN CONSIGNACION"


def _remito_es_consignacion_sql(alias: str = "h") -> str:
    h = alias.strip() or "h"
    return f"""(
        TRIM(COALESCE({h}.modalidad_remit, '')) IN ('Consignacion', 'Consignación')
        OR UPPER(COALESCE({h}.Detalle, '')) LIKE '%{CONSIGNACION_DETALLE_KEYWORD}%'
    )"""


def fetch_remitos_consignacion_cabeceras(
    cursor,
    *,
    remito_desde: date,
    remito_hasta: date,
) -> List[Dict[str, Any]]:
    hasta_excl = remito_hasta + timedelta(days=1)
    cons = _remito_es_consignacion_sql("h")
    cursor.execute(
        f"""
        SELECT h.CodigoMovimiento,
               h.NroComprobante,
               h.Fecha,
               h.Codigo AS codigo_cliente,
               COALESCE(c.NombreCliente, '') AS nombre_cliente,
               TRIM(COALESCE(h.modalidad_remit, '')) AS modalidad_remit,
               COALESCE(h.Detalle, '') AS detalle,
               CASE
                 WHEN TRIM(COALESCE(h.modalidad_remit, '')) IN ('Consignacion', 'Consignación')
                 THEN 'modalidad_remit'
                 ELSE 'detalle'
               END AS criterio_origen
        FROM comp_ped h
        LEFT JOIN cliente c ON c.Codigo = h.Codigo
        WHERE h.TipoComprobante = 'REM'
          AND IFNULL(h.Anulado, 'No') = 'No'
          AND h.Fecha >= %s AND h.Fecha < %s
          AND {cons}
        ORDER BY h.Fecha, h.CodigoMovimiento
        """,
        [remito_desde.isoformat(), hasta_excl.isoformat()],
    )
    rows = cursor.fetchall() or []
    if rows and not isinstance(rows[0], dict):
        cols = [d[0] for d in cursor.description] if cursor.description else []
        return [dict(zip(cols, r)) for r in rows]
    return list(rows)


def fetch_saldo_consignacion_por_articulo(
    cursor,
    *,
    remito_desde: date,
    remito_hasta: date,
    corte_facturas: date,
) -> List[Dict[str, Any]]:
    """
    Agrega remitido / facturado / devuelto / saldo por cliente × artículo.
    """
    hasta_remito = remito_hasta + timedelta(days=1)
    corte_excl = corte_facturas + timedelta(days=1)
    cons = _remito_es_consignacion_sql("h")
    cursor.execute(
        f"""
        SELECT h.Codigo AS codigo_cliente,
               COALESCE(c.NombreCliente, '') AS nombre_cliente,
               COALESCE(a.CodigoMarca, 0) AS codigo_marca,
               COALESCE(m.NombreMarca, '') AS nombre_marca,
               s.IDArt AS id_articulo,
               COALESCE(a.id_manual, '') AS id_manual,
               COALESCE(a.NombreArticulo, '') AS nombre_articulo,
               COALESCE(um.nombre_unimed, '') AS nombre_unimed,
               COALESCE(SUM(s.Cantidad), 0) AS packs_remitidos,
               COALESCE(SUM(
                   COALESCE((
                       SELECT SUM(stf.Cantidad)
                       FROM stock stf
                       INNER JOIN cuentacliente fa ON fa.CodigoMovimiento = stf.CodigoMovimiento
                       INNER JOIN rem_fact rf ON rf.CodigoMovimientoF = fa.CodigoMovimiento
                           AND rf.CodigoMovimientoR = h.CodigoMovimiento
                           AND IFNULL(rf.Anulado, 'No') = 'No'
                       WHERE stf.id_stock_remito_origen = s.id_stock
                         AND IFNULL(stf.Anulado, 'No') = 'No'
                         AND IFNULL(fa.Anulado, 'No') = 'No'
                         AND fa.Fecha < %s
                   ), 0)
               ), 0) AS packs_facturados,
               COALESCE(SUM(COALESCE(s.CantNC, 0)), 0) AS packs_devueltos
        FROM comp_ped h
        INNER JOIN stock s ON s.CodigoMovimiento = h.CodigoMovimiento
        INNER JOIN articulo a ON a.IDArt = s.IDArt
        LEFT JOIN cliente c ON c.Codigo = h.Codigo
        LEFT JOIN marca m ON m.CodigoMarca = a.CodigoMarca
        LEFT JOIN unidmed um ON um.id_unimed = a.id_unimed
        WHERE h.TipoComprobante = 'REM'
          AND IFNULL(h.Anulado, 'No') = 'No'
          AND IFNULL(s.Anulado, 'No') = 'No'
          AND h.Fecha >= %s AND h.Fecha < %s
          AND {cons}
        GROUP BY h.Codigo, COALESCE(c.NombreCliente, ''), s.IDArt,
                 COALESCE(a.id_manual, ''), COALESCE(a.NombreArticulo, ''),
                 COALESCE(a.CodigoMarca, 0), COALESCE(m.NombreMarca, ''),
                 COALESCE(um.nombre_unimed, '')
        """,
        [corte_excl.isoformat(), remito_desde.isoformat(), hasta_remito.isoformat()],
    )
    rows = cursor.fetchall() or []
    if rows and not isinstance(rows[0], dict):
        cols = [d[0] for d in cursor.description] if cursor.description else []
        rows = [dict(zip(cols, r)) for r in rows]
    out: List[Dict[str, Any]] = []
    for row in rows:
        rem = float(row.get("packs_remitidos") or 0)
        fac = float(row.get("packs_facturados") or 0)
        dev = float(row.get("packs_devueltos") or 0)
        saldo = round(rem - fac - dev, 4)
        if abs(saldo) < 1e-9:
            continue
        upp = unidades_por_pack_compras(
            row.get("nombre_unimed"),
            nombre_articulo=row.get("nombre_articulo"),
            id_manual=row.get("id_manual"),
        )
        prendas = prendas_desde_packs(saldo, upp)
        out.append(
            {
                **row,
                "packs_saldo": saldo,
                "prendas_saldo": prendas,
                "docenas_saldo": docenas_desde_prendas(prendas),
            }
        )
    return out


def fetch_remitos_consignacion_resumen(
    cursor,
    *,
    remito_desde: date,
    remito_hasta: date,
    corte_facturas: date,
) -> List[Dict[str, Any]]:
    cabeceras = fetch_remitos_consignacion_cabeceras(
        cursor, remito_desde=remito_desde, remito_hasta=remito_hasta
    )
    if not cabeceras:
        return []
    corte_excl = corte_facturas + timedelta(days=1)
    out: List[Dict[str, Any]] = []
    for cab in cabeceras:
        codmov = cab.get("CodigoMovimiento")
        cursor.execute(
            """
            SELECT COALESCE(SUM(s.Cantidad), 0) AS rem,
                   COALESCE(SUM(COALESCE(s.CantNC, 0)), 0) AS dev,
                   COUNT(*) AS renglones
            FROM stock s
            WHERE s.CodigoMovimiento = %s AND IFNULL(s.Anulado, 'No') = 'No'
            """,
            [codmov],
        )
        rem_row = cursor.fetchone() or (0, 0, 0)
        if isinstance(rem_row, dict):
            rem = float(rem_row.get("rem") or 0)
            dev = float(rem_row.get("dev") or 0)
            reng = int(rem_row.get("renglones") or 0)
        else:
            rem, dev, reng = float(rem_row[0] or 0), float(rem_row[1] or 0), int(rem_row[2] or 0)
        cursor.execute(
            """
            SELECT COALESCE(SUM(stf.Cantidad), 0)
            FROM stock srem
            INNER JOIN stock stf ON stf.id_stock_remito_origen = srem.id_stock
            INNER JOIN cuentacliente fa ON fa.CodigoMovimiento = stf.CodigoMovimiento
            INNER JOIN rem_fact rf ON rf.CodigoMovimientoF = fa.CodigoMovimiento
                AND rf.CodigoMovimientoR = %s
                AND IFNULL(rf.Anulado, 'No') = 'No'
            WHERE srem.CodigoMovimiento = %s
              AND IFNULL(stf.Anulado, 'No') = 'No'
              AND IFNULL(fa.Anulado, 'No') = 'No'
              AND fa.Fecha < %s
            """,
            [codmov, codmov, corte_excl.isoformat()],
        )
        fac_row = cursor.fetchone()
        fac = float((fac_row[0] if fac_row else 0) or 0)
        saldo = round(rem - fac - dev, 4)
        out.append(
            {
                **cab,
                "packs_remitidos": rem,
                "packs_facturados": fac,
                "packs_devueltos": dev,
                "packs_saldo": saldo,
                "renglones": reng,
            }
        )
    return out


def consultar_consignacion_stock(
    base_empresa: str,
    *,
    remito_desde_iso: str,
    remito_hasta_iso: str,
    corte_facturas_iso: Optional[str] = None,
) -> Dict[str, Any]:
    rem_desde = to_date_or_none(remito_desde_iso)
    rem_hasta = to_date_or_none(remito_hasta_iso)
    corte = to_date_or_none(corte_facturas_iso) or rem_hasta
    if not rem_desde or not rem_hasta or not (base_empresa or "").strip():
        return {"filas_articulo": [], "remitos": [], "totales": {}}
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            filas = fetch_saldo_consignacion_por_articulo(
                cursor,
                remito_desde=rem_desde,
                remito_hasta=rem_hasta,
                corte_facturas=corte,
            )
            remitos = fetch_remitos_consignacion_resumen(
                cursor,
                remito_desde=rem_desde,
                remito_hasta=rem_hasta,
                corte_facturas=corte,
            )
    except Exception as exc:
        logger.warning("consultar_consignacion_stock %s: %s", base_empresa, exc, exc_info=True)
        return {"filas_articulo": [], "remitos": [], "totales": {}}

    packs = round(sum(float(r.get("packs_saldo") or 0) for r in filas), 4)
    prendas = round(sum(float(r.get("prendas_saldo") or 0) for r in filas), 4)
    docenas = round(sum(float(r.get("docenas_saldo") or 0) for r in filas), 4)
    return {
        "filas_articulo": filas,
        "remitos": remitos,
        "totales": {"packs_saldo": packs, "prendas_saldo": prendas, "docenas_saldo": docenas},
    }
