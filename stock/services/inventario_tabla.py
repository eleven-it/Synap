# -*- coding: utf-8 -*-
"""Consulta inventario MPR pivoteada por tipo_mpr (módulo Stock)."""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from core.mysql_pool import mysql_cursor
from core.utils.administranet_types import str_codigo_manual_articulo, str_or_default, to_int_or_none

logger = logging.getLogger(__name__)

PAGE_SIZE = 150
_BUSQUEDA_MIN_LEN = 2

# Orden fijo de columnas (tipo_mpr en BD → etiqueta UI)
ETAPAS_INVENTARIO: Tuple[Tuple[str, str], ...] = (
    ("Produccion", "Producción"),
    ("SemiElaborado", "Semi elaborado"),
    ("2daSeleccion", "2da Selección"),
    ("Terminado", "Terminado"),
)

TIPOS_MPR_COLUMNAS = frozenset(t[0] for t in ETAPAS_INVENTARIO)


@dataclass
class InventarioTablaFiltros:
    marcas_incluidos: List[int] = field(default_factory=list)
    busqueda: Optional[str] = None
    id_articulo: Optional[int] = None
    incluir_ceros: bool = False
    presentacion: str = "unidades"
    page: int = 1

    @property
    def offset(self) -> int:
        p = max(1, self.page)
        return (p - 1) * PAGE_SIZE


def build_inventario_query_string(
    filtros: InventarioTablaFiltros,
    *,
    page: Optional[int] = None,
    id_articulo: Optional[int] = None,
    q: Optional[str] = None,
    clear_search: bool = False,
) -> str:
    """Arma query string para enlaces de paginación y limpiar."""
    from urllib.parse import urlencode

    pairs: List[Tuple[str, str]] = []
    for m in filtros.marcas_incluidos:
        pairs.append(("marcas_incluidos", str(m)))
    if filtros.incluir_ceros:
        pairs.append(("incluir_ceros", "1"))
    if filtros.presentacion and filtros.presentacion != "unidades":
        pairs.append(("presentacion", filtros.presentacion))
    if not clear_search:
        if id_articulo is not None:
            pairs.append(("id_articulo", str(id_articulo)))
        elif filtros.id_articulo is not None:
            pairs.append(("id_articulo", str(filtros.id_articulo)))
        elif q or filtros.busqueda:
            pairs.append(("q", q or filtros.busqueda or ""))
    p = page if page is not None else filtros.page
    if p and p > 1:
        pairs.append(("page", str(p)))
    return urlencode(pairs)


def parse_presentacion(raw: Optional[str]) -> str:
    modo = (raw or "unidades").strip().lower()
    return modo if modo in ("unidades", "docenas") else "unidades"


def parse_inventario_filtros(
    get_params: Any,
    *,
    marcas_getlist: Optional[Sequence[str]] = None,
) -> InventarioTablaFiltros:
    """Normaliza query string de /stock/inventario/."""
    marcas: List[int] = []
    raw_marcas = list(marcas_getlist or [])
    if not raw_marcas:
        single = get_params.get("marcas_incluidos") or get_params.get("marca")
        if single not in (None, "", []):
            raw_marcas = [single] if not isinstance(single, list) else list(single)
    for m in raw_marcas:
        try:
            marcas.append(int(str(m).strip()))
        except (TypeError, ValueError):
            continue

    q = (get_params.get("q") or "").strip() or None
    if q and len(q) < _BUSQUEDA_MIN_LEN:
        q = None

    id_art = to_int_or_none(get_params.get("id_articulo"))
    incluir = str(get_params.get("incluir_ceros") or "0").strip().lower() in (
        "1",
        "true",
        "yes",
        "si",
        "sí",
    )
    page = to_int_or_none(get_params.get("page")) or 1
    page = max(1, int(page))

    return InventarioTablaFiltros(
        marcas_incluidos=marcas,
        busqueda=q if not id_art else None,
        id_articulo=id_art,
        incluir_ceros=incluir,
        presentacion=parse_presentacion(get_params.get("presentacion")),
        page=page,
    )


def codigo_compuesto_articulo(id_manual: Any, cod_art_prov: Any) -> str:
    manual = str_codigo_manual_articulo(id_manual)
    prov = str_or_default(cod_art_prov, "").strip()
    if manual == "-" and not prov:
        return "-"
    if prov and manual != "-":
        return f"{manual} - {prov}"
    if manual != "-":
        return manual
    return prov or "-"


def ce_texto(valor: Any) -> str:
    """Normaliza valor CE (TALLES/COLOR): vacío o '-' → ''."""
    s = str_or_default(valor, "").strip()
    return "" if s in ("", "-") else s


def _nombre_tabla(cursor, nombre_lower: str) -> Optional[str]:
    cursor.execute("SHOW TABLES")
    for row in cursor.fetchall():
        nombre = (row[0] if not isinstance(row, dict) else list(row.values())[0]) or ""
        nombre = str(nombre).strip()
        if nombre.lower() == nombre_lower:
            return nombre
    return None


def listar_marcas_catalogo(base_empresa: str) -> List[Dict[str, Any]]:
    """Catálogo para tags filter: {value, label}."""
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl = _nombre_tabla(cursor, "marca")
            if not tbl:
                return []
            cursor.execute(
                f"SELECT CodMarca AS value, COALESCE(NombreMarca, '') AS label "
                f"FROM `{tbl.replace('`', '``')}` ORDER BY label"
            )
            return [
                {"value": int(r["value"]), "label": str_or_default(r.get("label"), "-")}
                for r in cursor.fetchall()
                if r.get("value") is not None
            ]
    except Exception as exc:
        logger.warning("listar_marcas_catalogo %s: %s", base_empresa, exc)
        return []


def _build_articulo_where(
    f: InventarioTablaFiltros,
    alias: str = "a",
) -> Tuple[str, List[Any]]:
    parts: List[str] = []
    params: List[Any] = []

    if f.id_articulo is not None:
        parts.append(f"{alias}.IDArt = %s")
        params.append(f.id_articulo)
        return " AND ".join(parts), params

    if f.marcas_incluidos:
        ph = ",".join(["%s"] * len(f.marcas_incluidos))
        parts.append(f"{alias}.CodigoMarca IN ({ph})")
        params.extend(f.marcas_incluidos)

    if f.busqueda:
        term = f"%{f.busqueda}%"
        parts.append(
            f"(IFNULL({alias}.id_manual, '') LIKE %s "
            f"OR IFNULL({alias}.CodArtProv, '') LIKE %s "
            f"OR IFNULL({alias}.NombreArticulo, '') LIKE %s "
            f"OR IFNULL({alias}.NroCodBarra, '') LIKE %s "
            f"OR IFNULL({alias}.NroCodBarraF, '') LIKE %s)"
        )
        params.extend([term, term, term, term, term])

    return " AND ".join(parts) if parts else "1=1", params


def _sql_agg_subquery(tbl_sd: str, tbl_dep: str) -> str:
    tsd = tbl_sd.replace("`", "``")
    tdep = tbl_dep.replace("`", "``")
    case_lines = []
    for tipo, _ in ETAPAS_INVENTARIO:
        case_lines.append(
            f"SUM(CASE WHEN TRIM(COALESCE(d.tipo_mpr, '')) = '{tipo}' "
            f"THEN COALESCE(sd.saldo, 0) ELSE 0 END) AS `{tipo}`"
        )
    return f"""
        SELECT sd.id_articulo,
               {', '.join(case_lines)}
        FROM `{tsd}` sd
        INNER JOIN `{tdep}` d ON d.CodDeposito = sd.id_deposito
        WHERE COALESCE(d.anulado, 'No') = 'No'
          AND COALESCE(d.suma_stock, 'Si') = 'Si'
          AND TRIM(COALESCE(d.tipo_mpr, '')) IN (
              'Produccion', 'SemiElaborado', '2daSeleccion', 'Terminado'
          )
        GROUP BY sd.id_articulo
    """


def consultar_inventario_tabla(
    base_empresa: str,
    filtros: InventarioTablaFiltros,
) -> Dict[str, Any]:
    """
    Devuelve filas pivoteadas, total_registros, page, page_size, sin_config_mpr.
    """
    vacio: Dict[str, Any] = {
        "filas": [],
        "total_registros": 0,
        "page": filtros.page,
        "page_size": PAGE_SIZE,
        "total_pages": 0,
        "sin_config_mpr": False,
    }
    if not (base_empresa or "").strip():
        return vacio

    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_sd = _nombre_tabla(cursor, "stock_deposito")
            tbl_dep = _nombre_tabla(cursor, "deposito")
            tbl_art = _nombre_tabla(cursor, "articulo")
            if not tbl_art:
                return vacio

            sin_config = False
            if tbl_dep:
                tdep = tbl_dep.replace("`", "``")
                cursor.execute(
                    f"SELECT COUNT(*) AS n FROM `{tdep}` "
                    f"WHERE COALESCE(anulado, 'No') = 'No' "
                    f"AND COALESCE(suma_stock, 'Si') = 'Si' "
                    f"AND TRIM(COALESCE(tipo_mpr, '')) IN "
                    f"('Produccion', 'SemiElaborado', '2daSeleccion', 'Terminado')"
                )
                row_cfg = cursor.fetchone()
                sin_config = not (row_cfg and int(row_cfg.get("n") or 0) > 0)

            where_art, params_art = _build_articulo_where(filtros)
            agg_sql = ""
            join_agg = ""
            if tbl_sd and tbl_dep:
                agg_sql = _sql_agg_subquery(tbl_sd, tbl_dep)
                join_agg = f"LEFT JOIN ({agg_sql}) agg ON agg.id_articulo = a.IDArt"
            else:
                join_agg = ""

            consolidado_expr = (
                "(COALESCE(agg.`Produccion`, 0) + COALESCE(agg.`SemiElaborado`, 0) + "
                "COALESCE(agg.`2daSeleccion`, 0) + COALESCE(agg.`Terminado`, 0))"
            )
            if not join_agg:
                consolidado_expr = "0"

            having_parts = []
            if not filtros.incluir_ceros and not filtros.id_articulo:
                having_parts.append(f"{consolidado_expr} > 0")
            having_sql = (" HAVING " + " AND ".join(having_parts)) if having_parts else ""

            tart = tbl_art.replace("`", "``")
            tbl_ce = _nombre_tabla(cursor, "articulo_valor_ce")
            join_ce = ""
            if tbl_ce:
                tce = tbl_ce.replace("`", "``")
                join_ce = f" LEFT JOIN `{tce}` avce ON avce.id_articulo = a.IDArt"
            from_sql = f"FROM `{tart}` a {join_agg}{join_ce}"

            count_sql = f"SELECT COUNT(*) AS n FROM (SELECT a.IDArt {from_sql} WHERE {where_art}{having_sql}) sub"
            cursor.execute(count_sql, tuple(params_art))
            count_row = cursor.fetchone()
            total = int(count_row.get("n") or 0) if count_row else 0

            select_cols = [
                "a.IDArt AS id_articulo",
                "a.id_manual AS id_manual",
                "a.CodArtProv AS cod_art_prov",
                "a.NombreArticulo AS nombre_articulo",
            ]
            if tbl_ce:
                select_cols.append("COALESCE(avce.valor1, '') AS talle")
                select_cols.append("COALESCE(avce.valor2, '') AS color")
            else:
                select_cols.append("'' AS talle")
                select_cols.append("'' AS color")
            for tipo, _ in ETAPAS_INVENTARIO:
                if join_agg:
                    select_cols.append(f"COALESCE(agg.`{tipo}`, 0) AS `{tipo}`")
                else:
                    select_cols.append(f"0 AS `{tipo}`")
            select_cols.append(f"{consolidado_expr} AS consolidado")

            order_sql = "ORDER BY a.id_manual, a.IDArt"
            limit_sql = "LIMIT %s OFFSET %s"
            sql = (
                f"SELECT {', '.join(select_cols)} {from_sql} "
                f"WHERE {where_art}{having_sql} {order_sql} {limit_sql}"
            )
            cursor.execute(sql, tuple(params_art) + (PAGE_SIZE, filtros.offset))
            rows = cursor.fetchall()

        filas_raw = []
        for r in rows:
            etapas_saldos = {}
            for tipo, _ in ETAPAS_INVENTARIO:
                try:
                    etapas_saldos[tipo] = float(r.get(tipo) or 0)
                except (TypeError, ValueError):
                    etapas_saldos[tipo] = 0.0
            try:
                consolidado = float(r.get("consolidado") or 0)
            except (TypeError, ValueError):
                consolidado = sum(etapas_saldos.values())

            filas_raw.append({
                "id_articulo": to_int_or_none(r.get("id_articulo")),
                "codigo_compuesto": codigo_compuesto_articulo(
                    r.get("id_manual"), r.get("cod_art_prov")
                ),
                "nombre_articulo": str_or_default(r.get("nombre_articulo"), "-"),
                "talle": ce_texto(r.get("talle")),
                "color": ce_texto(r.get("color")),
                "etapas_saldos": etapas_saldos,
                "consolidado": consolidado,
            })

        return {
            "filas": filas_raw,
            "total_registros": total,
            "page": filtros.page,
            "page_size": PAGE_SIZE,
            "total_pages": max(1, math.ceil(total / PAGE_SIZE)) if total else 0,
            "sin_config_mpr": sin_config,
        }
    except Exception as exc:
        logger.warning("consultar_inventario_tabla %s: %s", base_empresa, exc, exc_info=True)
        return vacio


def preparar_filas_inventario_presentacion(
    filas_raw: List[Dict[str, Any]],
    modo: str,
    base_empresa: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Enriquece filas con celdas docenas/unidades para plantilla."""
    from mpr.reportes_presentacion import _celda_stock_deposito
    from mpr.services import bulk_cantidad_promedio_bulto

    bulto_map: Dict[int, float] = {}
    if modo == "docenas" and base_empresa:
        ids = [int(f["id_articulo"]) for f in filas_raw if f.get("id_articulo") is not None]
        if ids:
            bulto_map = bulk_cantidad_promedio_bulto(base_empresa, ids)

    out: List[Dict[str, Any]] = []
    for fila in filas_raw:
        aid = fila.get("id_articulo")
        bulto = bulto_map.get(int(aid)) if aid is not None and modo == "docenas" else None
        etapas_celdas = []
        for tipo, label in ETAPAS_INVENTARIO:
            saldo = (fila.get("etapas_saldos") or {}).get(tipo, 0)
            etapas_celdas.append({
                "tipo_mpr": tipo,
                "label": label,
                "celda": _celda_stock_deposito(saldo, modo, cantidad_promedio_bulto=bulto),
            })
        consolidado = fila.get("consolidado", 0)
        out.append({
            "id_articulo": aid,
            "codigo_compuesto": fila.get("codigo_compuesto", "-"),
            "nombre_articulo": fila.get("nombre_articulo", "-"),
            "talle": ce_texto(fila.get("talle")),
            "color": ce_texto(fila.get("color")),
            "etapas": etapas_celdas,
            "consolidado": _celda_stock_deposito(
                consolidado, modo, cantidad_promedio_bulto=bulto
            ),
        })
    return out


def buscar_articulos_inventario(
    base_empresa: str,
    q: str,
    *,
    marcas_incluidos: Optional[List[int]] = None,
    incluir_ceros: bool = False,
    limit: int = 15,
) -> List[Dict[str, Any]]:
    """Búsqueda predictiva sobre universo completo (sin paginación de tabla)."""
    q = (q or "").strip()
    if len(q) < _BUSQUEDA_MIN_LEN:
        return []
    limit = min(max(1, limit), 50)
    f = InventarioTablaFiltros(
        marcas_incluidos=list(marcas_incluidos or []),
        busqueda=q,
        incluir_ceros=incluir_ceros,
        page=1,
    )
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_sd = _nombre_tabla(cursor, "stock_deposito")
            tbl_dep = _nombre_tabla(cursor, "deposito")
            tbl_art = _nombre_tabla(cursor, "articulo")
            if not tbl_art:
                return []

            where_art, params_art = _build_articulo_where(f)
            join_agg = ""
            consolidado_expr = "0"
            if tbl_sd and tbl_dep:
                agg_sql = _sql_agg_subquery(tbl_sd, tbl_dep)
                join_agg = f"LEFT JOIN ({agg_sql}) agg ON agg.id_articulo = a.IDArt"
                consolidado_expr = (
                    "(COALESCE(agg.`Produccion`, 0) + COALESCE(agg.`SemiElaborado`, 0) + "
                    "COALESCE(agg.`2daSeleccion`, 0) + COALESCE(agg.`Terminado`, 0))"
                )

            having_sql = ""
            if not incluir_ceros:
                having_sql = f" HAVING {consolidado_expr} > 0"

            tart = tbl_art.replace("`", "``")
            sql = (
                f"SELECT a.IDArt AS id_articulo, a.id_manual, a.CodArtProv AS cod_art_prov, "
                f"a.NombreArticulo AS nombre_articulo, {consolidado_expr} AS consolidado "
                f"FROM `{tart}` a {join_agg} WHERE {where_art}{having_sql} "
                f"ORDER BY a.NombreArticulo LIMIT %s"
            )
            cursor.execute(sql, tuple(params_art) + (limit,))
            rows = cursor.fetchall()
        return [
            {
                "id_articulo": to_int_or_none(r.get("id_articulo")),
                "codigo_compuesto": codigo_compuesto_articulo(
                    r.get("id_manual"), r.get("cod_art_prov")
                ),
                "id_manual": str_codigo_manual_articulo(r.get("id_manual")),
                "cod_art_prov": str_or_default(r.get("cod_art_prov"), ""),
                "nombre": str_or_default(r.get("nombre_articulo"), "-"),
                "marca_nombre": "",
            }
            for r in rows
        ]
    except Exception as exc:
        logger.warning("buscar_articulos_inventario %s: %s", base_empresa, exc)
        return []
