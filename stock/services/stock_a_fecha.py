"""Reconstrucción de saldos de stock a una fecha de corte (tabla legacy `stock`)."""
from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal
from typing import Dict, Optional, Sequence, Tuple

from core.mysql_pool import mysql_cursor
from core.utils.administranet_types import to_date_or_none, to_decimal_or_none, to_int_or_none

logger = logging.getLogger(__name__)


def _nombre_tabla(cursor, nombre_lower: str) -> Optional[str]:
    cursor.execute("SHOW TABLES LIKE %s", (nombre_lower,))
    row = cursor.fetchone()
    if row:
        return next(iter(row.values()))
    cursor.execute("SHOW TABLES")
    for r in cursor.fetchall() or []:
        nombre = next(iter(r.values()))
        if str(nombre).lower() == nombre_lower.lower():
            return nombre
    return None


def _normalizar_fecha_corte(fecha_corte) -> Optional[date]:
    if isinstance(fecha_corte, date):
        return fecha_corte
    parsed = to_date_or_none(fecha_corte)
    if not parsed:
        return None
    try:
        from datetime import datetime

        return datetime.strptime(str(parsed)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def saldos_stock_a_fecha(
    base_empresa: str,
    fecha_corte,
    *,
    id_depositos: Optional[Sequence[int]] = None,
) -> Dict[Tuple[int, int], Decimal]:
    """
    Saldos por (id_articulo, id_deposito) hasta fecha inclusive.

    Criterio VB6 Info_Stock «a fecha»: DATE(stock.Fecha) <= corte AND Anulado <> 'Si'.
    """
    vacio: Dict[Tuple[int, int], Decimal] = {}
    if not (base_empresa or "").strip():
        return vacio

    corte = _normalizar_fecha_corte(fecha_corte)
    if corte is None:
        return vacio

    depositos: list[int] = []
    if id_depositos:
        for dep in id_depositos:
            did = to_int_or_none(dep)
            if did is not None:
                depositos.append(did)

    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_stock = _nombre_tabla(cursor, "stock")
            if not tbl_stock:
                return vacio

            tstock = tbl_stock.replace("`", "``")
            where = (
                "DATE(s.Fecha) <= %s "
                "AND COALESCE(s.Anulado, 'No') <> 'Si'"
            )
            params: list = [corte.isoformat()]
            if depositos:
                ph = ",".join(["%s"] * len(depositos))
                where += f" AND s.CodDeposito IN ({ph})"
                params.extend(depositos)

            sql = f"""
                SELECT s.IDArt AS IDArt,
                       s.CodDeposito AS CodDeposito,
                       SUM(COALESCE(s.Entrada, 0)) - SUM(COALESCE(s.Salida, 0)) AS saldo
                FROM `{tstock}` s
                WHERE {where}
                GROUP BY s.IDArt, s.CodDeposito
            """
            cursor.execute(sql, tuple(params))
            rows = cursor.fetchall() or []

        resultado: Dict[Tuple[int, int], Decimal] = {}
        for row in rows:
            id_art = to_int_or_none(row.get("IDArt"))
            id_dep = to_int_or_none(row.get("CodDeposito"))
            saldo = to_decimal_or_none(row.get("saldo"))
            if id_art is None or id_dep is None or saldo is None:
                continue
            if saldo == 0:
                continue
            resultado[(id_art, id_dep)] = saldo
        return resultado
    except Exception as exc:
        logger.warning("saldos_stock_a_fecha %s: %s", base_empresa, exc, exc_info=True)
        return vacio
