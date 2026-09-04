# -*- coding: utf-8 -*-
"""FA/NC de cabecera sin renglón de mercadería vigente.

Cierra el gap entre informes de renglón (stock) y Ventas Netas (SubtotalDesc).
Solo debe usarse cuando no hay filtro de catálogo.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, List, Optional

from core.utils.administranet_types import str_or_default, to_decimal_or_none, to_int_or_none
from reports.services.ventas_marcas_mensual_rules import (
    TIPOS_FAC,
    TIPOS_NC,
    sql_comprobantes_in_clause,
    sql_stock_tipo_comp_in_clause,
)

CODIGO_SINTETICO_AJUSTES = -1
NOMBRE_AJUSTES = "Ajustes sin mercadería"
ID_MANUAL_AJUSTES = "__ajustes_cabecera__"
NOMBRE_FA_NC_CABECERA = "FA/NC de cabecera"

STOCK_TIPO_COMP_SQL = f"({sql_stock_tipo_comp_in_clause()})"
TIPOS_COMP_SQL = f"({sql_comprobantes_in_clause()})"
STOCK_TIPO_COMP_VENTA = STOCK_TIPO_COMP_SQL
TIPOS_COMP_VENTA = TIPOS_COMP_SQL

NOTA_AJUSTES_INCLUIDOS = (
    "La fila «Ajustes sin mercadería» agrupa FA/NC de cabecera sin renglón de stock vigente "
    "(por ejemplo notas de crédito financieras). Se incluye para que la facturación coincida "
    "con Ventas Netas."
)
NOTA_AJUSTES_OMITIDOS_CATALOGO = (
    "Con filtros de catálogo (marca, rubro, subrubro o SuperArt) no se incluyen "
    "FA/NC de cabecera sin mercadería; la facturación puede diferir de Ventas Netas."
)


def filtros_catalogo_restringen(
    marcas_incluidos: Optional[Iterable[Any]] = None,
    marcas_excluidos: Optional[Iterable[Any]] = None,
    rubros_incluidos: Optional[Iterable[Any]] = None,
    rubros_excluidos: Optional[Iterable[Any]] = None,
    subrubros_incluidos: Optional[Iterable[Any]] = None,
    subrubros_excluidos: Optional[Iterable[Any]] = None,
    superarts: Optional[Iterable[Any]] = None,
) -> bool:
    """Si hay filtro de catálogo, los ajustes de cabecera no alinearían con Ventas Netas."""
    return bool(
        marcas_incluidos
        or marcas_excluidos
        or rubros_incluidos
        or rubros_excluidos
        or subrubros_incluidos
        or subrubros_excluidos
        or superarts
    )


def sql_signo_subtotal_cabecera_expr() -> str:
    fac = ",".join(f"'{t}'" for t in TIPOS_FAC)
    nc = ",".join(f"'{t}'" for t in TIPOS_NC)
    return f"""
        CASE
            WHEN cc.TipoComprobante IN ({fac})
                THEN COALESCE(cc.SubtotalDesc, 0)
            WHEN cc.TipoComprobante IN ({nc})
                THEN -COALESCE(cc.SubtotalDesc, 0)
            ELSE 0
        END
    """


def consultar_ajustes_sin_mercaderia(
    cursor,
    where_cc_parts: List[str],
    params_cc: List[Any],
    *,
    renglon_ok_sql: str,
    group_by: str = "cliente",
) -> List[Dict[str, Any]]:
    """
    Cabeceras FA/NC sin renglón de stock vigente (Anulado=No, TipoComp venta/devolución
    y ``renglon_ok_sql``, p. ej. tipo_art ≠ Gasto o solo Articulo).

    group_by:
      - ``cliente``: una fila por cliente (totales de período).
      - ``cliente_mes``: una fila por cliente × yyyyMM.
    """
    if not where_cc_parts:
        return []
    where_cc = " AND ".join(where_cc_parts)
    signo = sql_signo_subtotal_cabecera_expr()
    select_mes = ""
    group_sql = "cc.Codigo"
    if group_by == "cliente_mes":
        # %%Y%%m: pymysql interpreta %% como % literal (igual que VMM).
        select_mes = "DATE_FORMAT(cc.Fecha, '%%Y%%m') AS anio_mes,"
        group_sql = "cc.Codigo, DATE_FORMAT(cc.Fecha, '%%Y%%m')"
    sql = f"""
        SELECT
            cc.Codigo AS codigo_cliente,
            COALESCE(MAX(cl.nombre_cliente), '') AS nombre_cliente,
            {select_mes}
            SUM({signo}) AS facturacion
        FROM cuentacliente cc
        INNER JOIN cliente cl ON cl.Codigo = cc.Codigo
        WHERE {where_cc}
          AND NOT EXISTS (
              SELECT 1
              FROM stock st
              LEFT JOIN articulo art ON art.IDArt = st.IDArt
              WHERE st.CodigoMovimiento = cc.CodigoMovimiento
                AND st.Anulado = 'No'
                AND st.TipoComp IN {STOCK_TIPO_COMP_SQL}
                AND {renglon_ok_sql}
          )
        GROUP BY {group_sql}
        HAVING ABS(facturacion) > 0.01
    """
    cursor.execute(sql, params_cc)
    cols = [d[0] for d in cursor.description]
    filas: List[Dict[str, Any]] = []
    for r in cursor.fetchall():
        row = dict(zip(cols, r))
        dec_fact = to_decimal_or_none(row.get("facturacion"), quantize="0.01")
        fact = float(dec_fact) if dec_fact is not None else 0.0
        if abs(fact) < 0.01:
            continue
        codigo = to_int_or_none(row.get("codigo_cliente")) or 0
        nombre = str_or_default(row.get("nombre_cliente"), "").strip() or f"Cliente {codigo}"
        out: Dict[str, Any] = {
            "codigo_cliente": codigo,
            "nombre_cliente": nombre,
            "facturacion": fact,
        }
        if group_by == "cliente_mes":
            mes = str_or_default(row.get("anio_mes"), "").strip()
            if not mes:
                continue
            out["anio_mes"] = mes
        filas.append(out)
    return filas


def pin_ajustes_al_final(
    nodos: List[Dict[str, Any]],
    *,
    es_ajuste: Callable[[Dict[str, Any]], bool],
    hijos_key: str = "children",
) -> List[Dict[str, Any]]:
    """Deja el nodo sintético al pie y marca ``es_ajuste_cabecera`` en el subárbol."""
    ajustes: List[Dict[str, Any]] = []
    resto: List[Dict[str, Any]] = []

    def _marcar(nodo: Dict[str, Any]) -> None:
        nodo["es_ajuste_cabecera"] = True
        for hijo in nodo.get(hijos_key) or nodo.get("clientes") or []:
            if isinstance(hijo, dict):
                _marcar(hijo)

    for nodo in nodos or []:
        if es_ajuste(nodo):
            _marcar(nodo)
            ajustes.append(nodo)
        else:
            resto.append(nodo)
    return resto + ajustes
