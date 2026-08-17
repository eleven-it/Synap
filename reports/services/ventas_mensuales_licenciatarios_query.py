# -*- coding: utf-8 -*-
"""Consulta read-only AdministraNET para ventas mensuales licenciatarios."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Iterable, List, Optional, Sequence

from core.utils.administranet_types import str_or_default, to_decimal_or_none
from reports.models import MonthlyReportingPack
from reports.services.connection_pool import get_mysql_pool
from reports.services.ventas_marcas_mensual_rules import (
    sql_base_where_clauses,
    sql_factor_docenas_expr,
    sql_signo_imp_post_pie_expr,
    sql_signo_qty_expr,
)
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AnetSalesRow:
    codigo_cliente: int
    nombre_cliente: str
    month: date
    units: Decimal
    amount: Decimal
    units_men: Decimal = Decimal("0")
    units_women: Decimal = Decimal("0")
    amount_men: Decimal = Decimal("0")
    amount_women: Decimal = Decimal("0")
    superart: str = ""


def build_anet_sales_sql(*, include_superart: bool = False) -> str:
    """Arma SQL agregado pack×cliente×mes reutilizando reglas VMM."""
    signo_qty = sql_signo_qty_expr()
    signo_imp = sql_signo_imp_post_pie_expr()
    factor_sql = sql_factor_docenas_expr()
    where_parts = sql_base_where_clauses()
    superart_select = ", COALESCE(art.id_manual, '') AS superart" if include_superart else ""
    superart_group = ", art.id_manual" if include_superart else ""
    # articulo usa CodigoMarca (FK a marca.CodMarca). pack.marca_anet es NombreMarca
    # (LB/LEV/PUM/PUW/PUS) según Monthly Reporting / VMM Best Sox.
    where_s = (
        " AND ".join(where_parts)
        + " AND art.CodigoMarca = ("
        + "SELECT m.CodMarca FROM marca m "
        + "WHERE m.NombreMarca = %s "
        + "AND (m.anulado IS NULL OR m.anulado = 'No') "
        + "LIMIT 1)"
    )
    return f"""
        SELECT
            cc.Codigo AS codigo_cliente,
            COALESCE(cl.nombre_cliente, '') AS nombre_cliente,
            DATE_FORMAT(cc.Fecha, '%%Y-%%m-01') AS month_start,
            SUM({signo_qty}) AS packs_qty,
            SUM({signo_qty} / {factor_sql}) AS docenas_qty,
            SUM({signo_imp}) AS facturacion
            {superart_select}
        FROM stock st
        INNER JOIN cuentacliente cc ON cc.CodigoMovimiento = st.CodigoMovimiento
        INNER JOIN cliente cl ON cl.Codigo = cc.Codigo
        LEFT JOIN articulo art ON art.IDArt = st.IDArt
        LEFT JOIN unidmed um ON um.id_unimed = art.id_unimed
        WHERE {where_s}
        GROUP BY cc.Codigo, cl.nombre_cliente, DATE_FORMAT(cc.Fecha, '%%Y-%%m-01')
                 {superart_group}
        HAVING ABS(SUM({signo_qty})) > 0.00001 OR ABS(SUM({signo_imp})) > 0.01
    """


def parse_anet_sales_row(
    raw: dict,
    *,
    unit_mode: str,
    classify_genero=None,
) -> AnetSalesRow:
    """Normaliza fila SQL a AnetSalesRow con unidades según pack."""
    month_raw = str_or_default(raw.get("month_start"), "")[:10]
    year = int(month_raw[0:4])
    month_num = int(month_raw[5:7])
    month = date(year, month_num, 1)
    mode = str_or_default(unit_mode, "").strip().lower()
    if mode == "dozens":
        units = to_decimal_or_none(raw.get("docenas_qty")) or Decimal("0")
    else:
        units = to_decimal_or_none(raw.get("packs_qty")) or Decimal("0")
    amount = to_decimal_or_none(raw.get("facturacion")) or Decimal("0")
    superart = str_or_default(raw.get("superart"), "").strip()
    units_men = Decimal("0")
    units_women = Decimal("0")
    amount_men = Decimal("0")
    amount_women = Decimal("0")
    if classify_genero and superart:
        genero = classify_genero(superart)
        if genero == "men":
            units_men = units
            amount_men = amount
        elif genero == "women":
            units_women = units
            amount_women = amount
    return AnetSalesRow(
        codigo_cliente=int(raw["codigo_cliente"]),
        nombre_cliente=str_or_default(raw.get("nombre_cliente"), ""),
        month=month,
        units=units,
        amount=amount,
        units_men=units_men,
        units_women=units_women,
        amount_men=amount_men,
        amount_women=amount_women,
        superart=superart,
    )


def fetch_anet_sales(
    *,
    base_empresa: str,
    pack: MonthlyReportingPack,
    date_from: date,
    date_to: date,
    cliente_ids: Optional[Sequence[int]] = None,
    classify_genero=None,
    register_unknown_superart=None,
) -> List[AnetSalesRow]:
    """
    Ejecuta consulta read-only AdministraNET para un pack y rango de fechas.

    AdministraNET: SOLO SELECT.
    """
    include_superart = pack.template_family == MonthlyReportingPack.TemplateFamily.PUMA
    sql = build_anet_sales_sql(include_superart=include_superart)
    params: List[Any] = [
        date_from.isoformat(),
        date_to.isoformat(),
        str_or_default(pack.marca_anet, "").strip(),
    ]
    if cliente_ids:
        placeholders = ",".join(["%s"] * len(cliente_ids))
        sql = sql.replace(
            "WHERE cc.Fecha >=",
            f"WHERE cc.Codigo IN ({placeholders}) AND cc.Fecha >=",
        )
        params = list(cliente_ids) + params

    rows: List[AnetSalesRow] = []
    pool = get_mysql_pool()
    with pool.get_connection(str(base_empresa).strip()) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("SET SESSION max_execution_time = 90000")
        except Exception:
            pass
        cursor.execute(sql, params)
        cols = [d[0] for d in cursor.description]
        for record in cursor.fetchall():
            raw = dict(zip(cols, record))
            row = parse_anet_sales_row(
                raw,
                unit_mode=pack.unit_mode,
                classify_genero=classify_genero,
            )
            if include_superart and row.superart and classify_genero:
                genero = classify_genero(row.superart)
                if genero is None and register_unknown_superart:
                    register_unknown_superart(row.superart, {"cliente": row.codigo_cliente})
            rows.append(row)
    return rows


def aggregate_anet_rows(rows: Iterable[AnetSalesRow]) -> dict[tuple[int, date], AnetSalesRow]:
    """Agrega filas ANET por cliente×mes (sin SuperArt en clave)."""
    acc: dict[tuple[int, date], AnetSalesRow] = {}
    for row in rows:
        key = (row.codigo_cliente, row.month)
        prev = acc.get(key)
        if prev is None:
            acc[key] = AnetSalesRow(
                codigo_cliente=row.codigo_cliente,
                nombre_cliente=row.nombre_cliente,
                month=row.month,
                units=row.units,
                amount=row.amount,
                units_men=row.units_men,
                units_women=row.units_women,
                amount_men=row.amount_men,
                amount_women=row.amount_women,
            )
        else:
            acc[key] = AnetSalesRow(
                codigo_cliente=prev.codigo_cliente,
                nombre_cliente=prev.nombre_cliente,
                month=prev.month,
                units=prev.units + row.units,
                amount=prev.amount + row.amount,
                units_men=prev.units_men + row.units_men,
                units_women=prev.units_women + row.units_women,
                amount_men=prev.amount_men + row.amount_men,
                amount_women=prev.amount_women + row.amount_women,
            )
    return acc


def search_anet_clients(base_empresa: str, q: str, *, limit: int = 50) -> List[dict[str, str]]:
    """Búsqueda read-only de clientes AdministraNET para modal de match."""
    term = str_or_default(q, "").strip()
    if len(term) < 2:
        return []
    base = str_or_default(base_empresa, "").strip()
    if not base:
        return []
    pool = get_mysql_pool()
    with pool.get_connection(base) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT cliente.Codigo AS id, COALESCE(cliente.nombre_cliente, '') AS text
                FROM cliente
                WHERE COALESCE(cliente.anulado, 'No') = 'No'
                  AND (
                    cliente.nombre_cliente LIKE %s
                    OR CAST(cliente.Codigo AS CHAR) LIKE %s
                  )
                ORDER BY cliente.nombre_cliente ASC
                LIMIT %s
                """,
                (f"%{term}%", f"%{term}%", int(limit)),
            )
            return [
                {"id": str(row[0]), "text": str_or_default(row[1], "")}
                for row in cursor.fetchall()
            ]
        finally:
            cursor.close()
