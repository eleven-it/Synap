# -*- coding: utf-8 -*-
"""Consulta Stock y existencias — SQL compartido (informe legacy y dashboard gerencial)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from reports.services.connection_pool import get_mysql_pool

_BUSQUEDA_MIN_LEN = 2
DEFAULT_PAGE_SIZE = 150
FULL_FETCH_THRESHOLD = 10_000

_SORT_SQL: Dict[str, str] = {
    "id_manual": "a.id_manual",
    "codigo_barras": (
        "COALESCE("
        "NULLIF(TRIM(IFNULL(a.NroCodBarraF, '')), ''), "
        "NULLIF(TRIM(IFNULL(a.NroCodBarra, '')), ''), "
        "''"
        ")"
    ),
    "nombre": "a.NombreArticulo",
    "rubro_nombre": "ru.NombreRubro",
    "subrubro_nombre": "su.NombreSubRubro",
    "deposito_nombre": "dep.NombreDeposito",
}

_CODIGO_BARRAS_EXPR = """
    COALESCE(
        NULLIF(TRIM(IFNULL(a.NroCodBarraF, '')), ''),
        NULLIF(TRIM(IFNULL(a.NroCodBarra, '')), ''),
        ''
    )
"""

_CODIGO_BARRAS_SELECT = f"{_CODIGO_BARRAS_EXPR.strip()} AS codigo_barras"

_RESERVADO_JOIN_SQL = """
    LEFT JOIN (
        SELECT sp_res.IDArt AS id_articulo,
            sp_res.CodDeposito AS id_deposito,
            SUM(COALESCE(sp_res.cantidad_pendiente,
                sp_res.Cantidad - COALESCE(sp_res.cantidad_entregada, 0))) AS reservado
        FROM stockp sp_res
        INNER JOIN comp_ped cp_res ON cp_res.CodigoMovimiento = sp_res.CodigoMovimiento
        WHERE cp_res.TipoComprobante = 'PED'
            AND (sp_res.Comprobante = 'PED' OR sp_res.Comprobante IS NULL)
            AND cp_res.Anulado = 'No'
            AND (sp_res.anulado IS NULL OR sp_res.anulado = 'No')
            AND cp_res.Estado IN ('En preparación', 'Preparado')
            AND (COALESCE(sp_res.cantidad_pendiente,
                sp_res.Cantidad - COALESCE(sp_res.cantidad_entregada, 0)) > 0)
        GROUP BY sp_res.IDArt, sp_res.CodDeposito
    ) res ON res.id_articulo = a.IDArt AND res.id_deposito = sd.id_deposito
"""


@dataclass
class StockExistenciasFilters:
    depositos_incluidos: List[int] = field(default_factory=list)
    incluir_stock_cero: bool = False
    marcas_incluidos: List[int] = field(default_factory=list)
    rubros_incluidos: List[int] = field(default_factory=list)
    subrubros_incluidos: List[int] = field(default_factory=list)
    busqueda: Optional[str] = None
    sort_col: str = "nombre"
    sort_dir: str = "asc"
    agrupacion_activa: bool = False
    limit: int = DEFAULT_PAGE_SIZE
    offset: int = 0


def parse_stock_existencias_filters(
    filters: Optional[Dict[str, Any]],
    payload_limit: Optional[int] = None,
    payload_offset: Optional[int] = None,
) -> StockExistenciasFilters:
    """Normaliza filtros del payload API."""
    filters = filters or {}

    depositos_incluidos = filters.get("depositos_incluidos", [])
    if isinstance(depositos_incluidos, str):
        depositos_incluidos = [depositos_incluidos] if depositos_incluidos else []
    elif not isinstance(depositos_incluidos, list):
        depositos_incluidos = []
    depositos_incluidos = [
        int(x)
        for x in depositos_incluidos
        if str(x).strip() and str(x).replace("-", "").isdigit()
    ]

    raw_stock = filters.get("incluir_stock_cero") or filters.get("stock_cero") or "no"
    incluir_cero = str(raw_stock).strip().lower() in ("si", "sí", "1", "true", "yes")

    def _parse_int_id_list(key: str) -> List[int]:
        raw = filters.get(key)
        if raw is None:
            return []
        if isinstance(raw, str):
            raw = [raw] if str(raw).strip() else []
        elif not isinstance(raw, list):
            return []
        out: List[int] = []
        for x in raw:
            try:
                out.append(int(str(x).strip()))
            except (TypeError, ValueError):
                continue
        return out

    marcas_incluidos = _parse_int_id_list("marcas_incluidos")
    rubros_incluidos = _parse_int_id_list("rubros_incluidos")
    subrubros_incluidos = _parse_int_id_list("subrubros_incluidos")

    def _opt_int(key: str):
        v = filters.get(key)
        if v is None or v == "":
            return None
        try:
            return int(v)
        except (TypeError, ValueError):
            return None

    if not marcas_incluidos:
        cm = _opt_int("codigo_marca")
        if cm is not None:
            marcas_incluidos = [cm]
    if not rubros_incluidos:
        cr = _opt_int("codigo_rubro")
        if cr is not None:
            rubros_incluidos = [cr]
    if not subrubros_incluidos:
        isr = _opt_int("id_subrubro")
        if isr is not None:
            subrubros_incluidos = [isr]

    busqueda = filters.get("busqueda")
    if busqueda is not None:
        busqueda = str(busqueda).strip() or None

    sort_col = str(filters.get("sort_col") or "nombre").strip()
    if sort_col not in _SORT_SQL:
        sort_col = "nombre"
    sort_dir = str(filters.get("sort_dir") or "asc").strip().lower()
    if sort_dir not in ("asc", "desc"):
        sort_dir = "asc"

    agrupacion_activa = str(filters.get("agrupacion_activa", "")).lower() in (
        "1",
        "true",
        "yes",
        "si",
        "sí",
    )

    limit = int(payload_limit) if payload_limit is not None else DEFAULT_PAGE_SIZE
    offset = int(payload_offset) if payload_offset is not None else 0
    if offset < 0:
        offset = 0
    if limit < 1:
        limit = DEFAULT_PAGE_SIZE

    if agrupacion_activa or limit >= FULL_FETCH_THRESHOLD:
        limit = 2_147_483_647
        offset = 0

    return StockExistenciasFilters(
        depositos_incluidos=depositos_incluidos,
        incluir_stock_cero=incluir_cero,
        marcas_incluidos=marcas_incluidos,
        rubros_incluidos=rubros_incluidos,
        subrubros_incluidos=subrubros_incluidos,
        busqueda=busqueda,
        sort_col=sort_col,
        sort_dir=sort_dir,
        agrupacion_activa=agrupacion_activa,
        limit=limit,
        offset=offset,
    )


def _like_pattern(term: str) -> str:
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _search_where_sql(busqueda: Optional[str]) -> Tuple[str, List[str]]:
    if not busqueda or len(busqueda.strip()) < _BUSQUEDA_MIN_LEN:
        return "", []
    pattern = _like_pattern(busqueda.strip())
    clause = f"""
        AND (
            a.NombreArticulo LIKE %s ESCAPE '\\\\'
            OR CAST(a.CodigoArticulo AS CHAR) LIKE %s ESCAPE '\\\\'
            OR IFNULL(a.id_manual, '') LIKE %s ESCAPE '\\\\'
            OR {_CODIGO_BARRAS_EXPR.strip()} LIKE %s ESCAPE '\\\\'
            OR IFNULL(dep.NombreDeposito, '') LIKE %s ESCAPE '\\\\'
            OR IFNULL(ru.NombreRubro, '') LIKE %s ESCAPE '\\\\'
            OR IFNULL(su.NombreSubRubro, '') LIKE %s ESCAPE '\\\\'
        )
    """
    return clause, [pattern] * 7


def _build_where(f: StockExistenciasFilters) -> Tuple[str, str, List[Any]]:
    """Devuelve (where_art_sql, where_sd_sql, params_art)."""
    where_art = [
        "a.Discontinuo = 'No'",
        "a.disponible_vta = 'Si'",
        "a.tipo_art = 'Articulo'",
    ]
    params: List[Any] = []

    if f.marcas_incluidos:
        where_art.append("a.CodigoMarca IN (" + ",".join(["%s"] * len(f.marcas_incluidos)) + ")")
        params.extend(f.marcas_incluidos)
    if f.rubros_incluidos:
        where_art.append("a.CodigoRubro IN (" + ",".join(["%s"] * len(f.rubros_incluidos)) + ")")
        params.extend(f.rubros_incluidos)
    if f.subrubros_incluidos:
        where_art.append("a.IDSubRubro IN (" + ",".join(["%s"] * len(f.subrubros_incluidos)) + ")")
        params.extend(f.subrubros_incluidos)

    where_sd: List[str] = []
    if f.depositos_incluidos:
        where_sd.append(
            "sd.id_deposito IN (" + ",".join(str(d) for d in f.depositos_incluidos) + ")"
        )
    if not f.incluir_stock_cero:
        where_sd.append("COALESCE(sd.saldo, 0) > 0")

    search_sql, search_params = _search_where_sql(f.busqueda)
    where_art_sql = " AND ".join(where_art) + search_sql
    where_sd_sql = (" AND " + " AND ".join(where_sd)) if where_sd else ""
    return where_art_sql, where_sd_sql, params + search_params


def _order_by_sql(f: StockExistenciasFilters) -> str:
    col_sql = _SORT_SQL.get(f.sort_col, _SORT_SQL["nombre"])
    direction = "DESC" if f.sort_dir == "desc" else "ASC"
    if f.sort_col == "nombre":
        return f"ORDER BY {col_sql} {direction}, sd.id_deposito ASC"
    return f"ORDER BY {col_sql} {direction}, a.NombreArticulo ASC, sd.id_deposito ASC"


def _from_clause() -> str:
    """Parte desde stock_deposito (STRAIGHT_JOIN) para reducir filas antes de articulo."""
    return f"""
        FROM stock_deposito sd
        STRAIGHT_JOIN articulo a ON a.IDArt = sd.id_articulo
        INNER JOIN deposito dep ON dep.CodDeposito = sd.id_deposito
        LEFT JOIN marca ma ON ma.CodMarca = a.CodigoMarca
        LEFT JOIN rubro ru ON ru.CodigoRubro = a.CodigoRubro
        LEFT JOIN subrubro su ON su.IDSubRubro = a.IDSubRubro
        {_RESERVADO_JOIN_SQL}
    """


def normalize_row(cols: List[str], row: tuple) -> Dict[str, Any]:
    item: Dict[str, Any] = {}
    for i, c in enumerate(cols):
        v = row[i]
        if c in ("stock", "reservado", "disponible") and v is not None:
            item[c] = float(v)
        elif c in ("id_art", "codigo_articulo", "id_deposito") and v is not None:
            item[c] = int(v) if str(v).replace("-", "").isdigit() else v
        elif c == "codigo_barras":
            if v is None or v == "":
                item[c] = ""
            elif isinstance(v, (bytes, bytearray)):
                item[c] = v.decode("latin1", errors="replace").strip()
            else:
                item[c] = str(v).strip()
        else:
            item[c] = v
    return item


def execute_stock_existencias(base_empresa: str, f: StockExistenciasFilters) -> Dict[str, Any]:
    """
    Ejecuta COUNT + SELECT paginado.
    Retorna dict con keys: data, total_registros, filters_applied, notes.
    """
    where_art_sql, where_sd_sql, params = _build_where(f)
    from_sql = _from_clause()
    where_full = f"WHERE {where_art_sql}{where_sd_sql}"

    notes: List[str] = []
    if f.busqueda and len(f.busqueda.strip()) >= _BUSQUEDA_MIN_LEN:
        notes.append(
            f"Búsqueda en servidor (mín. {_BUSQUEDA_MIN_LEN} caracteres): artículo, código, barras, depósito, rubro, subrubro."
        )
    if f.agrupacion_activa:
        notes.append("Agrupación activa: se devolvió el universo completo para agrupar en el cliente.")
    elif f.limit < FULL_FETCH_THRESHOLD:
        notes.append(
            f"Paginación servidor: {f.limit} filas por página (offset {f.offset}). "
            "Desplazamiento infinito en la tabla."
        )

    pool = get_mysql_pool()
    with pool.get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("SET SESSION max_execution_time = 300000")
        except Exception:
            pass

        sql_count = f"SELECT COUNT(*) {from_sql} {where_full}"
        cursor.execute(sql_count, tuple(params))
        count_row = cursor.fetchone()
        total_registros = int(count_row[0] or 0) if count_row else 0

        order_sql = _order_by_sql(f)
        limit_sql = ""
        limit_params: List[Any] = []
        if f.limit < FULL_FETCH_THRESHOLD:
            limit_sql = " LIMIT %s OFFSET %s"
            limit_params = [f.limit, f.offset]

        sql = f"""
            SELECT /*+ MAX_EXECUTION_TIME(300000) */
                a.IDArt AS id_art,
                COALESCE(a.CodigoArticulo, 0) AS codigo_articulo,
                a.id_manual AS id_manual,
                {_CODIGO_BARRAS_SELECT},
                a.NombreArticulo AS nombre,
                sd.id_deposito AS id_deposito,
                IFNULL(dep.NombreDeposito, CONCAT('Depósito ', sd.id_deposito)) AS deposito_nombre,
                IFNULL(ma.NombreMarca, '') AS marca_nombre,
                IFNULL(ru.NombreRubro, '') AS rubro_nombre,
                IFNULL(su.NombreSubRubro, '') AS subrubro_nombre,
                COALESCE(sd.saldo, 0) AS stock,
                COALESCE(res.reservado, 0) AS reservado,
                GREATEST(0, COALESCE(sd.saldo, 0) - COALESCE(res.reservado, 0)) AS disponible
            {from_sql}
            {where_full}
            {order_sql}
            {limit_sql}
        """
        cursor.execute(sql, tuple(params) + tuple(limit_params))
        rows = cursor.fetchall()
        cols = [d[0] for d in cursor.description]
        data = [normalize_row(cols, row) for row in rows]

    return {
        "data": data,
        "total_registros": total_registros,
        "filters_applied": {
            "depositos_incluidos": f.depositos_incluidos,
            "incluir_stock_cero": f.incluir_stock_cero,
            "marcas_incluidos": f.marcas_incluidos,
            "rubros_incluidos": f.rubros_incluidos,
            "subrubros_incluidos": f.subrubros_incluidos,
            "busqueda": f.busqueda,
            "sort_col": f.sort_col,
            "sort_dir": f.sort_dir,
            "agrupacion_activa": f.agrupacion_activa,
            "limit": f.limit,
            "offset": f.offset,
        },
        "notes": notes,
    }
