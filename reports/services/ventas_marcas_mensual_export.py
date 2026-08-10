# -*- coding: utf-8 -*-
"""Export Excel informe ventas-marcas-mensual: hoja Detalle a grano renglón."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from core.utils.administranet_types import str_or_default, to_int_or_none
from reports.services.ventas_marcas_mensual_rules import sql_signo_imp_post_pie_expr
from reports.services.ventas_marcas_mensual_runner import (
    _parse_coef_proyeccion,
    _parse_incluir_proyeccion,
    _resolve_marcas_incluidos,
    _sql_factor_docenas_expr,
    ceil_proy_unidades,
    round_proy_facturacion,
)

DETALLE_EXPORT_HEADERS = [
    "fecha",
    "tipo_comprobante",
    "nro_comprobante",
    "nombre_vendedor",
    "nombre_cliente",
    "id_manual",
    "nombre_articulo",
    "nombre_marca",
    "anio_mes",
    "unidades",
    "facturacion",
]

DETALLE_EXPORT_HEADERS_PROY = DETALLE_EXPORT_HEADERS + ["unidades_proy", "facturacion_proy"]

COMPARE_MATRIZ_HEADERS = [
    "nombre_vendedor",
    "nombre_cliente",
    "anio_mes",
    "unidades_a",
    "facturacion_a",
    "unidades_b",
    "facturacion_b",
]


def _signo_qty_sql() -> str:
    return """
        CASE
            WHEN cc.TipoComprobante IN ('FA','FB','FC','FE','FM') THEN COALESCE(st.Cantidad, 0)
            WHEN cc.TipoComprobante IN ('NCA','NCB','NCC','NCE','NCM') THEN -COALESCE(st.Cantidad, 0)
            ELSE 0
        END
    """


def _cat_sql_for_marcas(
    cursor,
    marcas_incluidos: List[int],
    superarts: List[str],
) -> Tuple[str, List[Any]]:
    from reports.services.ventas_objetivos_bo_runner import _vo_sql_filtros_articulo

    cat_sql, cat_params = _vo_sql_filtros_articulo("art", marcas_incluidos=marcas_incluidos)
    if superarts:
        ph_sa = ",".join(["%s"] * len(superarts))
        cat_sql += f" AND art.id_manual IN ({ph_sa})"
        cat_params = list(cat_params) + superarts
    return cat_sql, cat_params


def fetch_detalle_renglones(
    cursor,
    *,
    where_s: str,
    params: List[Any],
    cat_sql: str,
    cat_params: List[Any],
    modo_unidades: str,
    coef_proyeccion: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """Consulta grano renglón stock/cuentacliente con los mismos filtros que la matriz."""
    signo_qty = _signo_qty_sql()
    signo_imp = sql_signo_imp_post_pie_expr()
    factor_sql = _sql_factor_docenas_expr()
    use_docenas = modo_unidades == "docenas"

    sql = f"""
        SELECT
            DATE_FORMAT(cc.Fecha, '%%Y-%%m-%%d') AS fecha,
            cc.TipoComprobante AS tipo_comprobante,
            COALESCE(cc.NroComprobante, '') AS nro_comprobante,
            cc.CodViajante AS ven,
            COALESCE(v.Nombre, '') AS vend_nombre,
            cc.Codigo AS codigo_cliente,
            COALESCE(cl.nombre_cliente, '') AS nombre_cliente,
            COALESCE(art.id_manual, '') AS id_manual,
            COALESCE(art.NombreArticulo, '') AS nombre_articulo,
            COALESCE(m.NombreMarca, '') AS nombre_marca,
            DATE_FORMAT(cc.Fecha, '%%Y%%m') AS anio_mes,
            ({signo_qty}) AS packs,
            ({signo_qty}) / {factor_sql} AS docenas,
            ({signo_imp}) AS facturacion
        FROM stock st
        INNER JOIN cuentacliente cc ON cc.CodigoMovimiento = st.CodigoMovimiento
        INNER JOIN cliente cl ON cl.Codigo = cc.Codigo
        LEFT JOIN articulo art ON art.IDArt = st.IDArt
        LEFT JOIN marca m ON m.CodMarca = art.CodigoMarca
        LEFT JOIN unidmed um ON um.id_unimed = art.id_unimed
        LEFT JOIN viajantes v ON v.CodViajante = cc.CodViajante
        WHERE {where_s}
          AND (ABS({signo_qty}) > 0.00001 OR ABS({signo_imp}) > 0.01)
        ORDER BY cc.Fecha, cc.CodViajante, cc.Codigo, art.id_manual
    """
    cursor.execute(sql, params + cat_params)
    cols = [d[0] for d in cursor.description]
    out: List[Dict[str, Any]] = []
    for r in cursor.fetchall():
        row = dict(zip(cols, r))
        packs = float(row.pop("packs") or 0)
        docenas = float(row.pop("docenas") or 0)
        fact = float(row.pop("facturacion") or 0)
        u = docenas if use_docenas else packs
        if abs(u) < 1e-9 and abs(fact) < 0.01:
            continue
        plana: Dict[str, Any] = {
            "fecha": str_or_default(row.get("fecha"), ""),
            "tipo_comprobante": str_or_default(row.get("tipo_comprobante"), ""),
            "nro_comprobante": str_or_default(row.get("nro_comprobante"), ""),
            "cod_viajante": to_int_or_none(row.get("ven")) or 0,
            "nombre_vendedor": str_or_default(row.get("vend_nombre"), "").strip(),
            "codigo_cliente": str_or_default(row.get("codigo_cliente"), "").strip(),
            "nombre_cliente": str_or_default(row.get("nombre_cliente"), "").strip(),
            "id_manual": str_or_default(row.get("id_manual"), "").strip(),
            "nombre_articulo": str_or_default(row.get("nombre_articulo"), "").strip(),
            "nombre_marca": str_or_default(row.get("nombre_marca"), "").strip(),
            "anio_mes": str_or_default(row.get("anio_mes"), ""),
            "unidades": u,
            "facturacion": fact,
        }
        if coef_proyeccion is not None:
            plana["unidades_proy"] = ceil_proy_unidades(u, coef_proyeccion)
            plana["facturacion_proy"] = round_proy_facturacion(fact, coef_proyeccion)
        out.append(plana)
    return out


def fetch_detalle_for_filters(
    cursor,
    filters: Dict[str, Any],
    *,
    where_s: str,
    params: List[Any],
    raw_marcas: Any,
    superarts: List[str],
) -> List[Dict[str, Any]]:
    """Arma catálogo SQL y ejecuta detalle según filtros (una marca o comparar)."""
    modo_unidades = str_or_default(filters.get("modo_unidades"), "packs").strip().lower()
    if modo_unidades not in ("packs", "docenas"):
        modo_unidades = "packs"
    incluir_proyeccion = _parse_incluir_proyeccion(filters)
    coef = _parse_coef_proyeccion(filters) if incluir_proyeccion else None

    modo_cmp = str_or_default(filters.get("modo_comparacion"), "una").strip().lower()
    if modo_cmp == "comparar":
        marcas_a = _resolve_marcas_incluidos(cursor, filters.get("marca_a"))
        marcas_b = _resolve_marcas_incluidos(cursor, filters.get("marca_b"))
        marcas_union = sorted(set(marcas_a + marcas_b))
        cat_sql, cat_params = _cat_sql_for_marcas(cursor, marcas_union, superarts)
    else:
        marcas_incluidos = _resolve_marcas_incluidos(cursor, raw_marcas)
        cat_sql, cat_params = _cat_sql_for_marcas(cursor, marcas_incluidos, superarts)

    return fetch_detalle_renglones(
        cursor,
        where_s=where_s + cat_sql,
        params=params + cat_params,
        cat_sql="",
        cat_params=[],
        modo_unidades=modo_unidades,
        coef_proyeccion=coef,
    )


def resolve_detalle_headers(sample: Dict[str, Any]) -> List[str]:
    if not sample:
        return list(DETALLE_EXPORT_HEADERS)
    if "unidades_proy" in sample:
        return list(DETALLE_EXPORT_HEADERS_PROY)
    return list(DETALLE_EXPORT_HEADERS)
