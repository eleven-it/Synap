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

# Inventario UI: una sola página con todo el ámbito (filtro de texto en cliente).
# Tope de seguridad si el catálogo crece mucho; por encima se trunca y se informa.
PAGE_SIZE = 5000
_BUSQUEDA_MIN_LEN = 2

# Orden fijo de columnas (tipo_mpr en BD → etiqueta UI)
ETAPAS_INVENTARIO: Tuple[Tuple[str, str], ...] = (
    ("Produccion", "Producción"),
    ("SemiElaborado", "Semi elaborado"),
    ("2daSeleccion", "2da Selección"),
    ("Terminado", "Terminado"),
)

ETAPAS_FABRICADOS: Tuple[Tuple[str, str], ...] = (
    ("Produccion", "Producción"),
    ("SemiElaborado", "Semi elaborado"),
    ("2daSeleccion", "2da Selección"),
)

ETAPAS_TERMINADOS: Tuple[Tuple[str, str], ...] = (
    ("Terminado", "Terminado"),
)

TIPOS_MPR_COLUMNAS = frozenset(t[0] for t in ETAPAS_INVENTARIO)

AMBITO_FABRICADOS = "fabricados"
AMBITO_TERMINADOS = "terminados"
AMBITOS_VALIDOS = frozenset({AMBITO_FABRICADOS, AMBITO_TERMINADOS})

# Filtro de saldo en etapas del ámbito: Todos | Con stock (>0) | Sin stock (≤0)
FILTRO_STOCK_TODOS = "todos"
FILTRO_STOCK_CON = "con_stock"
FILTRO_STOCK_SIN = "sin_stock"
FILTROS_STOCK_VALIDOS = frozenset({FILTRO_STOCK_TODOS, FILTRO_STOCK_CON, FILTRO_STOCK_SIN})
FILTRO_STOCK_DEFAULT = FILTRO_STOCK_TODOS

# tipo_art_fab Admin por ámbito (Fabricado 2da = packs/componentes fabricados)
TIPOS_ART_FAB_POR_AMBITO: Dict[str, Tuple[str, ...]] = {
    AMBITO_FABRICADOS: ("Fabricado", "Fabricado 2da"),
    AMBITO_TERMINADOS: ("Terminado",),
}


@dataclass
class InventarioTablaFiltros:
    marcas_incluidos: List[int] = field(default_factory=list)
    busqueda: Optional[str] = None
    id_articulo: Optional[int] = None
    filtro_stock: str = FILTRO_STOCK_DEFAULT
    presentacion: str = "unidades"
    ambito: str = AMBITO_TERMINADOS
    page: int = 1

    @property
    def offset(self) -> int:
        p = max(1, self.page)
        return (p - 1) * PAGE_SIZE

    @property
    def incluir_ceros(self) -> bool:
        """Compat: True cuando el listado no exige saldo positivo (todos o sin stock)."""
        return self.filtro_stock != FILTRO_STOCK_CON


def parse_ambito(raw: Optional[str]) -> str:
    modo = (raw or AMBITO_TERMINADOS).strip().lower()
    return modo if modo in AMBITOS_VALIDOS else AMBITO_TERMINADOS


def etapas_para_ambito(ambito: Optional[str]) -> Tuple[Tuple[str, str], ...]:
    """Columnas de etapa visibles según Fabricados | Terminados."""
    if parse_ambito(ambito) == AMBITO_FABRICADOS:
        return ETAPAS_FABRICADOS
    return ETAPAS_TERMINADOS


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
    if filtros.filtro_stock and filtros.filtro_stock != FILTRO_STOCK_DEFAULT:
        pairs.append(("filtro_stock", filtros.filtro_stock))
    if filtros.presentacion and filtros.presentacion != "unidades":
        pairs.append(("presentacion", filtros.presentacion))
    if filtros.ambito and filtros.ambito != AMBITO_TERMINADOS:
        pairs.append(("ambito", filtros.ambito))
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


def parse_filtro_stock(raw: Optional[str], *, incluir_ceros_legacy: Optional[str] = None) -> str:
    """
    Normaliza filtro de saldo.

    Preferencia: ``filtro_stock`` (todos|con_stock|sin_stock).
    Legacy: ``incluir_ceros=1`` → todos; ``incluir_ceros=0`` → con_stock.
    Default: todos.
    """
    modo = (raw or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "todos": FILTRO_STOCK_TODOS,
        "all": FILTRO_STOCK_TODOS,
        "con_stock": FILTRO_STOCK_CON,
        "con": FILTRO_STOCK_CON,
        "positivo": FILTRO_STOCK_CON,
        "sin_stock": FILTRO_STOCK_SIN,
        "sin": FILTRO_STOCK_SIN,
        "cero": FILTRO_STOCK_SIN,
        "ceros": FILTRO_STOCK_SIN,
        "negativo": FILTRO_STOCK_SIN,
        "negativos": FILTRO_STOCK_SIN,
    }
    if modo in aliases:
        return aliases[modo]
    if modo in FILTROS_STOCK_VALIDOS:
        return modo
    if incluir_ceros_legacy is not None:
        legacy = str(incluir_ceros_legacy or "").strip().lower()
        if legacy in ("1", "true", "yes", "si", "sí"):
            return FILTRO_STOCK_TODOS
        if legacy in ("0", "false", "no"):
            return FILTRO_STOCK_CON
    return FILTRO_STOCK_DEFAULT


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
    page = to_int_or_none(get_params.get("page")) or 1
    page = max(1, int(page))

    raw_filtro = get_params.get("filtro_stock")
    legacy_ceros = None
    if raw_filtro in (None, ""):
        # Solo aplicar legacy si vino explícito en la query
        if hasattr(get_params, "__contains__"):
            if "incluir_ceros" in get_params:
                legacy_ceros = get_params.get("incluir_ceros")
        elif get_params.get("incluir_ceros") is not None:
            legacy_ceros = get_params.get("incluir_ceros")

    return InventarioTablaFiltros(
        marcas_incluidos=marcas,
        busqueda=q if not id_art else None,
        id_articulo=id_art,
        filtro_stock=parse_filtro_stock(raw_filtro, incluir_ceros_legacy=legacy_ceros),
        presentacion=parse_presentacion(get_params.get("presentacion")),
        ambito=parse_ambito(get_params.get("ambito")),
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


def sql_expr_codigo_barras_ean(alias: str = "a") -> str:
    """EAN preferido: NroCodBarraF, fallback NroCodBarra (paridad informes Stock)."""
    a = (alias or "a").strip() or "a"
    return (
        f"COALESCE("
        f"NULLIF(TRIM(IFNULL({a}.NroCodBarraF, '')), ''), "
        f"NULLIF(TRIM(IFNULL({a}.NroCodBarra, '')), ''), "
        f"'')"
    )


def codigo_barras_ean_desde_row(row: Dict[str, Any]) -> str:
    """Normaliza EAN desde fila SQL (campo codigo_barras o ean1/ean2)."""
    directo = str_or_default(row.get("codigo_barras"), "").strip()
    if directo:
        return directo
    for key in ("ean2", "NroCodBarraF", "ean1", "NroCodBarra"):
        val = str_or_default(row.get(key), "").strip()
        if val:
            return val
    return ""


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


def _clausula_busqueda_inventario(
    busqueda: str,
    *,
    alias: str = "a",
    alias_ce: Optional[str] = None,
) -> Tuple[str, List[Any]]:
    """
    Texto libre sobre columnas visibles/utiles de la grilla: código, nombre,
    barras, talle y color (CE) cuando hay join a articulo_valor_ce.
    """
    q = (busqueda or "").strip()
    if not q:
        return "", []
    term = f"%{q}%"
    partes = [
        f"IFNULL({alias}.id_manual, '') LIKE %s",
        f"IFNULL({alias}.CodArtProv, '') LIKE %s",
        f"IFNULL({alias}.NombreArticulo, '') LIKE %s",
        f"IFNULL({alias}.NroCodBarra, '') LIKE %s",
        f"IFNULL({alias}.NroCodBarraF, '') LIKE %s",
    ]
    params: List[Any] = [term, term, term, term, term]
    if alias_ce:
        partes.append(f"IFNULL({alias_ce}.valor1, '') LIKE %s")
        partes.append(f"IFNULL({alias_ce}.valor2, '') LIKE %s")
        params.extend([term, term])
    return "(" + " OR ".join(partes) + ")", params


def _build_articulo_where(
    f: InventarioTablaFiltros,
    alias: str = "a",
    *,
    alias_ce: Optional[str] = None,
) -> Tuple[str, List[Any]]:
    parts: List[str] = []
    params: List[Any] = []

    tipos_fab = TIPOS_ART_FAB_POR_AMBITO.get(parse_ambito(f.ambito), TIPOS_ART_FAB_POR_AMBITO[AMBITO_TERMINADOS])
    if len(tipos_fab) == 1:
        parts.append(f"COALESCE(TRIM({alias}.tipo_art_fab), '') = %s")
        params.append(tipos_fab[0])
    else:
        ph = ",".join(["%s"] * len(tipos_fab))
        parts.append(f"COALESCE(TRIM({alias}.tipo_art_fab), '') IN ({ph})")
        params.extend(tipos_fab)

    if f.id_articulo is not None:
        parts.append(f"{alias}.IDArt = %s")
        params.append(f.id_articulo)
        return " AND ".join(parts), params

    if f.marcas_incluidos:
        ph = ",".join(["%s"] * len(f.marcas_incluidos))
        parts.append(f"{alias}.CodigoMarca IN ({ph})")
        params.extend(f.marcas_incluidos)

    if f.busqueda:
        clausula, params_q = _clausula_busqueda_inventario(
            f.busqueda, alias=alias, alias_ce=alias_ce
        )
        if clausula:
            parts.append(clausula)
            params.extend(params_q)

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


def _sql_tiene_stock_positivo_expr(
    alias: str = "agg",
    *,
    etapas: Optional[Tuple[Tuple[str, str], ...]] = None,
) -> str:
    """
    Expresión que indica si el artículo tiene saldo positivo en alguna etapa
    del ámbito activo.

    No usa el consolidado: un saldo negativo en una etapa no debe ocultar el
    saldo disponible de otra etapa del mismo artículo.
    """
    cols = etapas if etapas is not None else ETAPAS_INVENTARIO
    return "(" + " OR ".join(
        f"COALESCE({alias}.`{tipo}`, 0) > 0"
        for tipo, _ in cols
    ) + ")"


def _sql_sin_stock_positivo_expr(
    alias: str = "agg",
    *,
    etapas: Optional[Tuple[Tuple[str, str], ...]] = None,
) -> str:
    """Sin stock: ninguna etapa del ámbito tiene saldo > 0 (ceros y negativos)."""
    return f"(NOT {_sql_tiene_stock_positivo_expr(alias, etapas=etapas)})"


def _sql_where_filtro_stock(
    filtro_stock: str,
    *,
    etapas: Optional[Tuple[Tuple[str, str], ...]] = None,
    tiene_agg: bool = True,
) -> str:
    """Fragmento AND … según filtro_stock; vacío si todos."""
    modo = parse_filtro_stock(filtro_stock)
    if modo == FILTRO_STOCK_TODOS:
        return ""
    if not tiene_agg:
        # Sin depósitos MPR no hay saldos: con_stock → vacío; sin_stock → todos (todos ≤0)
        if modo == FILTRO_STOCK_CON:
            return " AND 0 > 0"
        return ""
    if modo == FILTRO_STOCK_CON:
        return f" AND {_sql_tiene_stock_positivo_expr(etapas=etapas)}"
    if modo == FILTRO_STOCK_SIN:
        return f" AND {_sql_sin_stock_positivo_expr(etapas=etapas)}"
    return ""


def _sql_consolidado_expr(
    alias: str = "agg",
    *,
    etapas: Optional[Tuple[Tuple[str, str], ...]] = None,
) -> str:
    cols = etapas if etapas is not None else ETAPAS_INVENTARIO
    return "(" + " + ".join(
        f"COALESCE({alias}.`{tipo}`, 0)"
        for tipo, _ in cols
    ) + ")"


def consultar_inventario_tabla(
    base_empresa: str,
    filtros: InventarioTablaFiltros,
) -> Dict[str, Any]:
    """
    Devuelve filas pivoteadas, total_registros, page, page_size, sin_config_mpr.
    """
    etapas = etapas_para_ambito(filtros.ambito)
    vacio: Dict[str, Any] = {
        "filas": [],
        "total_registros": 0,
        "filas_cargadas": 0,
        "truncado": False,
        "page": 1,
        "page_size": PAGE_SIZE,
        "total_pages": 1,
        "sin_config_mpr": False,
        "etapas": etapas,
        "ambito": parse_ambito(filtros.ambito),
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

            tbl_ce = _nombre_tabla(cursor, "articulo_valor_ce")
            where_art, params_art = _build_articulo_where(
                filtros, alias_ce="avce" if tbl_ce else None
            )
            agg_sql = ""
            join_agg = ""
            if tbl_sd and tbl_dep:
                agg_sql = _sql_agg_subquery(tbl_sd, tbl_dep)
                join_agg = f"LEFT JOIN ({agg_sql}) agg ON agg.id_articulo = a.IDArt"
            else:
                join_agg = ""

            consolidado_expr = (
                _sql_consolidado_expr(etapas=etapas) if join_agg else "0"
            )

            where_stock_sql = ""
            if not filtros.id_articulo:
                where_stock_sql = _sql_where_filtro_stock(
                    filtros.filtro_stock,
                    etapas=etapas,
                    tiene_agg=bool(join_agg),
                )

            tart = tbl_art.replace("`", "``")
            join_ce = ""
            if tbl_ce:
                tce = tbl_ce.replace("`", "``")
                join_ce = f" LEFT JOIN `{tce}` avce ON avce.id_articulo = a.IDArt"
            from_sql = f"FROM `{tart}` a {join_agg}{join_ce}"

            count_sql = (
                f"SELECT COUNT(*) AS n FROM "
                f"(SELECT a.IDArt {from_sql} WHERE {where_art}{where_stock_sql}) sub"
            )
            cursor.execute(count_sql, tuple(params_art))
            count_row = cursor.fetchone()
            total = int(count_row.get("n") or 0) if count_row else 0

            select_cols = [
                "a.IDArt AS id_articulo",
                "a.id_manual AS id_manual",
                "a.CodArtProv AS cod_art_prov",
                "a.NombreArticulo AS nombre_articulo",
                f"{sql_expr_codigo_barras_ean('a')} AS codigo_barras",
            ]
            if tbl_ce:
                select_cols.append("COALESCE(avce.valor1, '') AS talle")
                select_cols.append("COALESCE(avce.valor2, '') AS color")
            else:
                select_cols.append("'' AS talle")
                select_cols.append("'' AS color")
            for tipo, _ in etapas:
                if join_agg:
                    select_cols.append(f"COALESCE(agg.`{tipo}`, 0) AS `{tipo}`")
                else:
                    select_cols.append(f"0 AS `{tipo}`")
            select_cols.append(f"{consolidado_expr} AS consolidado")

            order_sql = "ORDER BY a.id_manual, a.IDArt"
            # Sin OFFSET: siempre página única; tope PAGE_SIZE como red de seguridad.
            limit_sql = "LIMIT %s"
            sql = (
                f"SELECT {', '.join(select_cols)} {from_sql} "
                f"WHERE {where_art}{where_stock_sql} {order_sql} {limit_sql}"
            )
            cursor.execute(sql, tuple(params_art) + (PAGE_SIZE,))
            rows = cursor.fetchall()

        filas_raw = []
        for r in rows:
            etapas_saldos = {}
            for tipo, _ in etapas:
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
                "codigo_barras": codigo_barras_ean_desde_row(r),
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
            "filas_cargadas": len(filas_raw),
            "truncado": bool(total > len(filas_raw)),
            "page": 1,
            "page_size": PAGE_SIZE,
            "total_pages": 1,
            "sin_config_mpr": sin_config,
            "etapas": etapas,
            "ambito": parse_ambito(filtros.ambito),
        }
    except Exception as exc:
        logger.warning("consultar_inventario_tabla %s: %s", base_empresa, exc, exc_info=True)
        return vacio


def preparar_filas_inventario_presentacion(
    filas_raw: List[Dict[str, Any]],
    modo: str,
    base_empresa: Optional[str] = None,
    *,
    ambito: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Enriquece filas con celdas docenas/unidades para plantilla."""
    from mpr.reportes_presentacion import _celda_stock_deposito
    from mpr.services import bulk_cantidad_promedio_bulto

    etapas = etapas_para_ambito(ambito)
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
        for tipo, label in etapas:
            saldo = (fila.get("etapas_saldos") or {}).get(tipo, 0)
            etapas_celdas.append({
                "tipo_mpr": tipo,
                "label": label,
                "celda": _celda_stock_deposito(
                    saldo, modo, cantidad_promedio_bulto=bulto, clamp_negativos=False
                ),
            })
        consolidado = fila.get("consolidado", 0)
        out.append({
            "id_articulo": aid,
            "codigo_barras": str_or_default(fila.get("codigo_barras"), "").strip(),
            "codigo_compuesto": fila.get("codigo_compuesto", "-"),
            "nombre_articulo": fila.get("nombre_articulo", "-"),
            "talle": ce_texto(fila.get("talle")),
            "color": ce_texto(fila.get("color")),
            "etapas": etapas_celdas,
            "consolidado": _celda_stock_deposito(
                consolidado, modo, cantidad_promedio_bulto=bulto, clamp_negativos=False
            ),
        })
    return out


def buscar_articulos_inventario(
    base_empresa: str,
    q: str,
    *,
    marcas_incluidos: Optional[List[int]] = None,
    filtro_stock: Optional[str] = None,
    incluir_ceros: Optional[bool] = None,
    ambito: Optional[str] = None,
    limit: int = 15,
) -> List[Dict[str, Any]]:
    """Búsqueda predictiva sobre universo del ámbito (sin paginación de tabla)."""
    q = (q or "").strip()
    if len(q) < _BUSQUEDA_MIN_LEN:
        return []
    limit = min(max(1, limit), 50)
    ambito_norm = parse_ambito(ambito)
    etapas = etapas_para_ambito(ambito_norm)
    if filtro_stock:
        fs = parse_filtro_stock(filtro_stock)
    elif incluir_ceros is True:
        fs = FILTRO_STOCK_TODOS
    elif incluir_ceros is False:
        fs = FILTRO_STOCK_CON
    else:
        fs = FILTRO_STOCK_DEFAULT
    f = InventarioTablaFiltros(
        marcas_incluidos=list(marcas_incluidos or []),
        busqueda=q,
        filtro_stock=fs,
        ambito=ambito_norm,
        page=1,
    )
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_sd = _nombre_tabla(cursor, "stock_deposito")
            tbl_dep = _nombre_tabla(cursor, "deposito")
            tbl_art = _nombre_tabla(cursor, "articulo")
            if not tbl_art:
                return []

            tbl_ce = _nombre_tabla(cursor, "articulo_valor_ce")
            where_art, params_art = _build_articulo_where(
                f, alias_ce="avce" if tbl_ce else None
            )
            join_agg = ""
            consolidado_expr = "0"
            if tbl_sd and tbl_dep:
                agg_sql = _sql_agg_subquery(tbl_sd, tbl_dep)
                join_agg = f"LEFT JOIN ({agg_sql}) agg ON agg.id_articulo = a.IDArt"
                consolidado_expr = _sql_consolidado_expr(etapas=etapas)

            where_stock_sql = _sql_where_filtro_stock(
                f.filtro_stock,
                etapas=etapas,
                tiene_agg=bool(join_agg),
            )

            tart = tbl_art.replace("`", "``")
            join_ce = ""
            select_ce = "'' AS talle, '' AS color"
            if tbl_ce:
                tce = tbl_ce.replace("`", "``")
                join_ce = f" LEFT JOIN `{tce}` avce ON avce.id_articulo = a.IDArt"
                select_ce = "COALESCE(avce.valor1, '') AS talle, COALESCE(avce.valor2, '') AS color"
            sql = (
                f"SELECT a.IDArt AS id_articulo, a.id_manual, a.CodArtProv AS cod_art_prov, "
                f"a.NombreArticulo AS nombre_articulo, "
                f"{sql_expr_codigo_barras_ean('a')} AS codigo_barras, "
                f"{select_ce}, "
                f"{consolidado_expr} AS consolidado "
                f"FROM `{tart}` a {join_agg}{join_ce} WHERE {where_art}{where_stock_sql} "
                f"ORDER BY a.NombreArticulo LIMIT %s"
            )
            cursor.execute(sql, tuple(params_art) + (limit,))
            rows = cursor.fetchall()
        return [
            {
                "id_articulo": to_int_or_none(r.get("id_articulo")),
                "codigo_barras": codigo_barras_ean_desde_row(r),
                "codigo_compuesto": codigo_compuesto_articulo(
                    r.get("id_manual"), r.get("cod_art_prov")
                ),
                "id_manual": str_codigo_manual_articulo(r.get("id_manual")),
                "cod_art_prov": str_or_default(r.get("cod_art_prov"), ""),
                "nombre": str_or_default(r.get("nombre_articulo"), "-"),
                "talle": ce_texto(r.get("talle")),
                "color": ce_texto(r.get("color")),
                "marca_nombre": "",
            }
            for r in rows
        ]
    except Exception as exc:
        logger.warning("buscar_articulos_inventario %s: %s", base_empresa, exc)
        return []
