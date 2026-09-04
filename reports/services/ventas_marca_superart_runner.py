# -*- coding: utf-8 -*-
"""
Informe Ventas por marca y SuperArt: jerarquía Marca → SuperArt → Artículo.

Reutiliza signo FA/NC, factor docenas, importe post-pie y filtros catálogo de VMM / ventas_objetivos_bo.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set, Tuple

from django.conf import settings

from core.utils.administranet_types import str_or_default, to_date_or_none, to_decimal_or_none, to_int_or_none
from reports.models import ReportDefinition
from reports.services.connection_pool import get_mysql_pool
from reports.services.articulo_venta_sql import sql_excluir_tipo_art_gasto
from reports.services.ajustes_sin_mercaderia import (
    CODIGO_SINTETICO_AJUSTES as CODIGO_MARCA_AJUSTES,
    ID_MANUAL_AJUSTES,
    NOMBRE_AJUSTES as NOMBRE_MARCA_AJUSTES,
    NOMBRE_FA_NC_CABECERA as NOMBRE_SUPERART_AJUSTES,
    NOTA_AJUSTES_INCLUIDOS,
    NOTA_AJUSTES_OMITIDOS_CATALOGO,
    consultar_ajustes_sin_mercaderia,
    filtros_catalogo_restringen,
    pin_ajustes_al_final,
)
from reports.services.query_runner import QueryResult, QueryRunnerService
from reports.services.ventas_marcas_mensual_rules import sql_signo_imp_post_pie_expr
from reports.services.ventas_marcas_mensual_runner import (
    _resolve_marcas_incluidos,
    _sql_factor_docenas_expr,
)
from reports.services.ventas_objetivos_bo_runner import (
    _parse_int_list,
    _sql_in_viajantes,
    _vo_sql_filtros_articulo,
)
from ventas.services.objetivos_mysql import alcance_objetivos_cod_viajante, ctx_desde_runner

logger = logging.getLogger(__name__)

_METRIC_ORDER_MAP = {
    "facturacion_periodo": "facturacion",
    "packs": "packs",
    "docenas": "docenas",
}

_ORDER_DIRECTION_MAP = {
    "asc": 1,
    "desc": -1,
}

TIPOS_COMP_VENTA = "('FA','FB','FC','FE','FM','NCA','NCB','NCC','NCE','NCM')"
STOCK_TIPO_COMP_VENTA = "('Venta','Venta TPV','Devol - Cliente','ND Anul NC')"


def _parse_str_list(raw: Any) -> List[str]:
    if isinstance(raw, str):
        raw = [raw] if raw.strip() else []
    elif not isinstance(raw, list):
        raw = []
    out: List[str] = []
    for item in raw:
        s = str_or_default(item, "").strip()
        if s:
            out.append(s)
    return out


def _norm_yyyy_mm_dd(raw: Any) -> str:
    fecha_normalizada = to_date_or_none(raw)
    if fecha_normalizada is None:
        return str_or_default(raw, "").strip()[:10]
    return fecha_normalizada


def _parse_sorting(filters: Dict[str, Any]) -> Tuple[str, str]:
    raw_field = str_or_default(filters.get("ordenar_por"), "facturacion_periodo").strip().lower()
    raw_dir = str_or_default(filters.get("orden_forma"), "desc").strip().lower()
    field = raw_field if raw_field in _METRIC_ORDER_MAP else "facturacion_periodo"
    direction = raw_dir if raw_dir in _ORDER_DIRECTION_MAP else "desc"
    return field, direction


def _sort_scalar(value: Any, direction: str) -> float:
    n = float(value or 0)
    return n if direction == "asc" else -n


def _display_marca(codigo_marca: Any, nombre_marca: Any) -> Tuple[int, str]:
    cod = to_int_or_none(codigo_marca) or 0
    nombre = str_or_default(nombre_marca, "").strip()
    if cod == 0 and not nombre:
        return 0, "Sin marca"
    if not nombre:
        return cod, "Sin marca"
    return cod, nombre


def _display_superart(id_manual: Any) -> Tuple[str, str]:
    manual = str_or_default(id_manual, "").strip()
    if manual == ID_MANUAL_AJUSTES:
        return ID_MANUAL_AJUSTES, NOMBRE_SUPERART_AJUSTES
    if not manual:
        return "", "Sin SuperArt"
    return manual, manual


def _acumular_metricas(dest: Dict[str, Any], packs: float, docenas: float, facturacion: float) -> None:
    dest["packs"] = float(dest.get("packs") or 0) + packs
    dest["docenas"] = float(dest.get("docenas") or 0) + docenas
    dest["facturacion"] = float(dest.get("facturacion") or 0) + facturacion


def _nest_marca_superart_articulo(filas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Construye árbol marca → superart → artículo desde filas SQL agregadas.
    """
    marcas: Dict[Tuple[int, str], Dict[str, Any]] = {}
    super_idx: Dict[Tuple[Tuple[int, str], Tuple[str, str]], Dict[str, Any]] = {}

    for row in filas:
        cod_marca, nom_marca = _display_marca(row.get("codigo_marca"), row.get("nombre_marca"))
        id_manual, nom_superart = _display_superart(row.get("id_manual"))
        id_art = to_int_or_none(row.get("id_art")) or 0
        nom_art = str_or_default(row.get("nombre_articulo"), "").strip() or "Sin artículo"
        packs = float(row.get("packs") or 0)
        docenas = float(row.get("docenas") or 0)
        fact = float(row.get("facturacion") or 0)

        if abs(packs) < 1e-9 and abs(docenas) < 1e-9 and abs(fact) < 0.01:
            continue

        mk = (cod_marca, nom_marca)
        if mk not in marcas:
            marcas[mk] = {
                "tipo": "marca",
                "codigo_marca": cod_marca,
                "nombre_marca": nom_marca,
                "packs": 0.0,
                "docenas": 0.0,
                "facturacion": 0.0,
                "children": [],
            }
        marca = marcas[mk]
        _acumular_metricas(marca, packs, docenas, fact)

        sk = (mk, (id_manual, nom_superart))
        if sk not in super_idx:
            super_node = {
                "tipo": "superart",
                "id_manual": id_manual,
                "nombre_superart": nom_superart,
                "packs": 0.0,
                "docenas": 0.0,
                "facturacion": 0.0,
                "children": [],
            }
            super_idx[sk] = super_node
            marca["children"].append(super_node)
        superart = super_idx[sk]
        _acumular_metricas(superart, packs, docenas, fact)

        superart["children"].append(
            {
                "tipo": "articulo",
                "id_art": id_art,
                "nombre_articulo": nom_art,
                "packs": packs,
                "docenas": docenas,
                "facturacion": fact,
            }
        )

    out = list(marcas.values())
    out.sort(key=lambda m: ((m.get("nombre_marca") or "").upper(), int(m.get("codigo_marca") or 0)))
    for marca in out:
        supers = marca.get("children") or []
        supers.sort(
            key=lambda s: (
                (s.get("nombre_superart") or "").upper(),
                str(s.get("id_manual") or ""),
            )
        )
        for sa in supers:
            arts = sa.get("children") or []
            arts.sort(
                key=lambda a: (
                    (a.get("nombre_articulo") or "").upper(),
                    int(a.get("id_art") or 0),
                )
            )
            sa["children"] = arts
        marca["children"] = supers
    return out


def _flatten_filas_marca_superart(arbol: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filas planas a nivel artículo para data[] y export."""
    planas: List[Dict[str, Any]] = []
    for marca in arbol or []:
        cod_marca = int(marca.get("codigo_marca") or 0)
        nom_marca = str_or_default(marca.get("nombre_marca"), "").strip()
        for superart in marca.get("children") or []:
            id_manual = str_or_default(superart.get("id_manual"), "").strip()
            nom_superart = str_or_default(superart.get("nombre_superart"), "").strip()
            for art in superart.get("children") or []:
                planas.append(
                    {
                        "codigo_marca": cod_marca,
                        "nombre_marca": nom_marca,
                        "id_manual": id_manual,
                        "nombre_superart": nom_superart,
                        "id_art": int(art.get("id_art") or 0),
                        "nombre_articulo": str_or_default(art.get("nombre_articulo"), "").strip(),
                        "packs": float(art.get("packs") or 0),
                        "docenas": float(art.get("docenas") or 0),
                        "facturacion": float(art.get("facturacion") or 0),
                    }
                )
    planas.sort(
        key=lambda r: (
            str(r.get("nombre_marca") or "").upper(),
            int(r.get("codigo_marca") or 0),
            str(r.get("nombre_superart") or "").upper(),
            str(r.get("id_manual") or ""),
            str(r.get("nombre_articulo") or "").upper(),
            int(r.get("id_art") or 0),
        )
    )
    return planas


def _group_metric(node: Dict[str, Any], metric_key: str) -> float:
    return float(node.get(metric_key) or 0)


def _sort_arbol_marca_superart(
    arbol: List[Dict[str, Any]],
    metric_key: str,
    direction: str,
) -> List[Dict[str, Any]]:
    """Ordena marca → superart → artículo por métrica (packs, docenas o facturacion)."""
    out: List[Dict[str, Any]] = []
    for marca in arbol or []:
        marca_copy = dict(marca)
        supers_out: List[Dict[str, Any]] = []
        for superart in marca_copy.get("children") or []:
            sa_copy = dict(superart)
            arts = sorted(
                sa_copy.get("children") or [],
                key=lambda a: (
                    _sort_scalar(_group_metric(a, metric_key), direction),
                    (a.get("nombre_articulo") or "").upper(),
                    int(a.get("id_art") or 0),
                ),
            )
            sa_copy["children"] = arts
            supers_out.append(sa_copy)
        marca_copy["children"] = sorted(
            supers_out,
            key=lambda s: (
                _sort_scalar(_group_metric(s, metric_key), direction),
                (s.get("nombre_superart") or "").upper(),
                str(s.get("id_manual") or ""),
            ),
        )
        out.append(marca_copy)
    return sorted(
        out,
        key=lambda m: (
            _sort_scalar(_group_metric(m, metric_key), direction),
            (m.get("nombre_marca") or "").upper(),
            int(m.get("codigo_marca") or 0),
        ),
    )


def _totales_desde_arbol(arbol: List[Dict[str, Any]]) -> Dict[str, Any]:
    packs = docenas = fact = 0.0
    articulos: Set[int] = set()
    for marca in arbol or []:
        packs += float(marca.get("packs") or 0)
        docenas += float(marca.get("docenas") or 0)
        fact += float(marca.get("facturacion") or 0)
        for superart in marca.get("children") or []:
            for art in superart.get("children") or []:
                iid = to_int_or_none(art.get("id_art"))
                if iid and iid > 0:
                    articulos.add(int(iid))
    return {
        "packs": packs,
        "docenas": docenas,
        "facturacion": fact,
        "articulos": len(articulos),
    }


def _filtros_catalogo_restringen(
    marcas_incluidos: List[int],
    marcas_excluidos: List[int],
    rubros_incluidos: List[int],
    rubros_excluidos: List[int],
    subrubros_incluidos: List[int],
    subrubros_excluidos: List[int],
    superarts: List[str],
) -> bool:
    return filtros_catalogo_restringen(
        marcas_incluidos,
        marcas_excluidos,
        rubros_incluidos,
        rubros_excluidos,
        subrubros_incluidos,
        subrubros_excluidos,
        superarts,
    )


def _consultar_ajustes_sin_mercaderia(
    cursor,
    where_cc_parts: List[str],
    params_cc: List[Any],
) -> List[Dict[str, Any]]:
    """Adapta cabeceras sin renglón SuperArt a filas del árbol marca → SuperArt → cliente."""
    filas: List[Dict[str, Any]] = []
    for row in consultar_ajustes_sin_mercaderia(
        cursor,
        where_cc_parts,
        params_cc,
        renglon_ok_sql=sql_excluir_tipo_art_gasto("art"),
        group_by="cliente",
    ):
        filas.append(
            {
                "codigo_marca": CODIGO_MARCA_AJUSTES,
                "nombre_marca": NOMBRE_MARCA_AJUSTES,
                "id_manual": ID_MANUAL_AJUSTES,
                "id_art": 0,
                "nombre_articulo": row["nombre_cliente"],
                "packs": 0.0,
                "docenas": 0.0,
                "facturacion": float(row.get("facturacion") or 0),
            }
        )
    return filas


def _pin_ajustes_al_final(arbol: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return pin_ajustes_al_final(
        arbol,
        es_ajuste=lambda m: int(m.get("codigo_marca") or 0) == CODIGO_MARCA_AJUSTES,
    )


def run_ventas_marca_superart(report: ReportDefinition, payload: Dict, user) -> QueryResult:
    svc = QueryRunnerService(user)
    filters = payload.get("filters", {}) or {}

    fecha_inicio, fecha_fin = svc._resolve_period_dates(filters)
    fi_fac_raw = filters.get("fecha_inicio_facturacion")
    ff_fac_raw = filters.get("fecha_fin_facturacion")
    fi_fac = str_or_default(fi_fac_raw, "").strip() or fecha_inicio
    ff_fac = str_or_default(ff_fac_raw, "").strip() or fecha_fin

    if not fi_fac or not ff_fac:
        return QueryResult(
            meta={"slug": report.slug, "name": report.name, "category": report.category, "version": report.version},
            data=[],
            totals={},
            notes=["Debe proporcionar fecha de inicio y fecha fin, o seleccionar un período predefinido."],
        )

    base_empresa = filters.get("base_empresa")
    if not base_empresa and hasattr(user, "base_empresa"):
        base_empresa = getattr(user, "base_empresa", None)
    if not base_empresa:
        base_empresa = getattr(settings, "DEFAULT_BASE_EMPRESA", None)
    if not base_empresa:
        return QueryResult(
            meta={"slug": report.slug, "name": report.name, "category": report.category, "version": report.version},
            data=[],
            totals={},
            notes=["No se pudo determinar la base de datos de la empresa."],
        )

    sucursales_ints, puntos_venta_ints = svc._parse_sucursales_pv(filters)
    clientes_excluidos = svc._parse_clientes_excluidos(filters)
    vendedores_excluidos = svc._parse_vendedores_excluidos(filters)
    clientes_incluir = _parse_int_list(filters.get("clientes_incluir", []))
    vendedores_incluir = _parse_int_list(filters.get("vendedores_incluir", []))

    rubros_incluidos = _parse_int_list(filters.get("rubros_incluidos", []))
    rubros_excluidos = _parse_int_list(filters.get("rubros_excluidos", []))
    subrubros_incluidos = _parse_int_list(filters.get("subrubros_incluidos", []))
    subrubros_excluidos = _parse_int_list(filters.get("subrubros_excluidos", []))
    marcas_excluidos = _parse_int_list(filters.get("marcas_excluidos", []))

    raw_marcas = filters.get("marcas_incluidos")
    if raw_marcas is None:
        raw_marcas = filters.get("marcas_incluidas")

    superarts = _parse_str_list(filters.get("superarts_incluidos"))
    if not superarts:
        superarts = _parse_str_list(filters.get("id_manuales"))

    rubros_excluidos = [x for x in rubros_excluidos if x not in set(rubros_incluidos)]
    subrubros_excluidos = [x for x in subrubros_excluidos if x not in set(subrubros_incluidos)]

    ordenar_por, orden_forma = _parse_sorting(filters)
    metric_key = _METRIC_ORDER_MAP.get(ordenar_por) or "facturacion"

    alcance_ctx = ctx_desde_runner(user, str(base_empresa), filters)
    try:
        alcance_cv = alcance_objetivos_cod_viajante(str(base_empresa), alcance_ctx)
    except Exception:
        logger.exception("ventas_marca_superart: no se pudo validar el alcance comercial")
        return QueryResult(
            meta={
                "slug": report.slug,
                "name": report.name,
                "category": report.category,
                "version": report.version,
                "extra": {
                    "tabs": {
                        "marca_superart_jerarquia": [],
                        "marca_superart_filas": [],
                    },
                },
            },
            data=[],
            totals={},
            notes=["Error al validar el alcance comercial; no se mostrarán datos."],
        )

    clientes_excluidos = [c for c in clientes_excluidos if to_int_or_none(c) not in set(clientes_incluir)]
    vendedores_excluidos = [v for v in vendedores_excluidos if int(v) not in set(vendedores_incluir)]

    alcance_viaj_filtro: List[int] = []
    if alcance_cv is not None:
        if not alcance_cv:
            return QueryResult(
                meta={"slug": report.slug, "name": report.name, "category": report.category, "version": report.version},
                data=[],
                totals={},
                notes=["Sin vendedores en el alcance comercial del usuario."],
            )
        alcance_set = set(int(x) for x in alcance_cv)
        if vendedores_incluir:
            alcance_viaj_filtro = [v for v in vendedores_incluir if v in alcance_set]
            if not alcance_viaj_filtro:
                return QueryResult(
                    meta={"slug": report.slug, "name": report.name, "category": report.category, "version": report.version},
                    data=[],
                    totals={},
                    notes=["Los vendedores solicitados no están en su alcance comercial."],
                )
        else:
            alcance_viaj_filtro = sorted(alcance_set)
        vendedores_excluidos = [v for v in vendedores_excluidos if int(v) not in set(alcance_viaj_filtro)]

    fi_sql = _norm_yyyy_mm_dd(fi_fac)
    ff_sql = _norm_yyyy_mm_dd(ff_fac)

    signo_qty = """
        CASE
            WHEN cc.TipoComprobante IN ('FA','FB','FC','FE','FM') THEN COALESCE(st.Cantidad, 0)
            WHEN cc.TipoComprobante IN ('NCA','NCB','NCC','NCE','NCM') THEN -COALESCE(st.Cantidad, 0)
            ELSE 0
        END
    """
    signo_imp = sql_signo_imp_post_pie_expr()
    factor_sql = _sql_factor_docenas_expr()

    where_cc_parts = [
        "cc.Fecha >= %s",
        "cc.Fecha <= %s",
        "cc.Anulado = 'No'",
        "cc.CodigoMovimiento <> 0",
        f"cc.TipoComprobante IN {TIPOS_COMP_VENTA}",
    ]
    params_cc: List[Any] = [fi_sql, ff_sql]
    where_parts = [
        "cc.Fecha >= %s",
        "cc.Fecha <= %s",
        "cc.Anulado = 'No'",
        "cc.CodigoMovimiento <> 0",
        f"cc.TipoComprobante IN {TIPOS_COMP_VENTA}",
        "st.Anulado = 'No'",
        f"st.TipoComp IN {STOCK_TIPO_COMP_VENTA}",
        sql_excluir_tipo_art_gasto("art"),
    ]
    params: List[Any] = [fi_sql, ff_sql]

    def _append_cc_filter(clause: str, values: List[Any]) -> None:
        where_parts.append(clause)
        params.extend(values)
        where_cc_parts.append(clause)
        params_cc.extend(values)

    if sucursales_ints:
        phs = ",".join(["%s"] * len(sucursales_ints))
        _append_cc_filter(f"cc.CodSucursal IN ({phs})", sucursales_ints)
    if puntos_venta_ints:
        phpv = ",".join(["%s"] * len(puntos_venta_ints))
        _append_cc_filter(f"cc.id_pv IN ({phpv})", puntos_venta_ints)
    if clientes_excluidos:
        ph = ",".join(["%s"] * len(clientes_excluidos))
        _append_cc_filter(f"cc.Codigo NOT IN ({ph})", clientes_excluidos)
    if clientes_incluir:
        ph = ",".join(["%s"] * len(clientes_incluir))
        _append_cc_filter(f"cc.Codigo IN ({ph})", clientes_incluir)
    if vendedores_excluidos:
        phv = ",".join(["%s"] * len(vendedores_excluidos))
        _append_cc_filter(f"cc.CodViajante NOT IN ({phv})", vendedores_excluidos)
    if vendedores_incluir:
        phvi = ",".join(["%s"] * len(vendedores_incluir))
        _append_cc_filter(f"cc.CodViajante IN ({phvi})", vendedores_incluir)
    if alcance_viaj_filtro:
        alcance_sql, alcance_params = _sql_in_viajantes("cc", alcance_viaj_filtro)
        _append_cc_filter(alcance_sql.lstrip(" AND "), alcance_params)

    sql_rows: List[Dict[str, Any]] = []
    marcas_incluidos: List[int] = []

    try:
        pool = get_mysql_pool()
        with pool.get_connection(str(base_empresa).strip()) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("SET SESSION max_execution_time = 90000")
            except Exception:
                pass

            marcas_incluidos = _resolve_marcas_incluidos(cursor, raw_marcas)
            marcas_excluidos = [x for x in marcas_excluidos if x not in set(marcas_incluidos)]

            cat_sql, cat_params = _vo_sql_filtros_articulo(
                "art",
                rubros_incluidos=rubros_incluidos,
                rubros_excluidos=rubros_excluidos,
                subrubros_incluidos=subrubros_incluidos,
                subrubros_excluidos=subrubros_excluidos,
                marcas_incluidos=marcas_incluidos,
                marcas_excluidos=marcas_excluidos,
            )
            if superarts:
                ph_sa = ",".join(["%s"] * len(superarts))
                cat_sql += f" AND art.id_manual IN ({ph_sa})"
                cat_params = list(cat_params) + superarts

            where_s = " AND ".join(where_parts) + cat_sql

            sql = f"""
                SELECT
                    COALESCE(art.CodigoMarca, 0) AS codigo_marca,
                    COALESCE(MAX(m.NombreMarca), '') AS nombre_marca,
                    COALESCE(art.id_manual, '') AS id_manual,
                    COALESCE(art.IDArt, 0) AS id_art,
                    COALESCE(MAX(art.NombreArticulo), '') AS nombre_articulo,
                    SUM({signo_qty}) AS packs,
                    SUM({signo_qty} / {factor_sql}) AS docenas,
                    SUM({signo_imp}) AS facturacion
                FROM stock st
                INNER JOIN cuentacliente cc ON cc.CodigoMovimiento = st.CodigoMovimiento
                INNER JOIN cliente cl ON cl.Codigo = cc.Codigo
                LEFT JOIN articulo art ON art.IDArt = st.IDArt
                LEFT JOIN marca m ON m.CodMarca = art.CodigoMarca
                LEFT JOIN unidmed um ON um.id_unimed = art.id_unimed
                WHERE {where_s}
                GROUP BY art.CodigoMarca, art.id_manual, art.IDArt
                HAVING ABS(packs) > 0.00001 OR ABS(facturacion) > 0.01
            """
            cursor.execute(sql, params + cat_params)
            cols = [d[0] for d in cursor.description]
            for r in cursor.fetchall():
                row = dict(zip(cols, r))
                dec_packs = to_decimal_or_none(row.get("packs"))
                dec_docenas = to_decimal_or_none(row.get("docenas"))
                dec_fact = to_decimal_or_none(row.get("facturacion"), quantize="0.01")
                row["packs"] = float(dec_packs) if dec_packs is not None else 0.0
                row["docenas"] = float(dec_docenas) if dec_docenas is not None else 0.0
                row["facturacion"] = float(dec_fact) if dec_fact is not None else 0.0
                sql_rows.append(row)

            if not _filtros_catalogo_restringen(
                marcas_incluidos,
                marcas_excluidos,
                rubros_incluidos,
                rubros_excluidos,
                subrubros_incluidos,
                subrubros_excluidos,
                superarts,
            ):
                sql_rows.extend(_consultar_ajustes_sin_mercaderia(cursor, where_cc_parts, params_cc))

    except Exception as ex:
        logger.exception("ventas_marca_superart: error SQL")
        return QueryResult(
            meta={"slug": report.slug, "name": report.name, "category": report.category, "version": report.version},
            data=[],
            totals={},
            notes=[f"Error al ejecutar la consulta: {ex}"],
        )

    arbol = _nest_marca_superart_articulo(sql_rows)
    arbol = _sort_arbol_marca_superart(arbol, metric_key, orden_forma)
    arbol = _pin_ajustes_al_final(arbol)
    planas = _flatten_filas_marca_superart(arbol)
    totals = _totales_desde_arbol(arbol)

    filters_applied = {
        "fecha_inicio_facturacion": fi_sql,
        "fecha_fin_facturacion": ff_sql,
        "marcas_incluidos": marcas_incluidos,
        "marcas_excluidos": marcas_excluidos,
        "rubros_incluidos": rubros_incluidos,
        "rubros_excluidos": rubros_excluidos,
        "subrubros_incluidos": subrubros_incluidos,
        "subrubros_excluidos": subrubros_excluidos,
        "superarts_incluidos": superarts,
        "sucursales": sucursales_ints,
        "punto_venta": puntos_venta_ints,
        "clientes_excluidos": clientes_excluidos,
        "clientes_incluir": clientes_incluir,
        "vendedores_excluidos": vendedores_excluidos,
        "vendedores_incluir": vendedores_incluir,
        "ordenar_por": ordenar_por,
        "orden_forma": orden_forma,
        "base_empresa_used": str(base_empresa),
    }

    notes = [
        f"Ventas del período: {fi_sql} a {ff_sql}. Jerarquía Marca → SuperArt → Artículo."
    ]
    catalogo_restringe = _filtros_catalogo_restringen(
        marcas_incluidos,
        marcas_excluidos,
        rubros_incluidos,
        rubros_excluidos,
        subrubros_incluidos,
        subrubros_excluidos,
        superarts,
    )
    if any(int(m.get("codigo_marca") or 0) == CODIGO_MARCA_AJUSTES for m in arbol):
        notes.append(NOTA_AJUSTES_INCLUIDOS)
    elif catalogo_restringe:
        notes.append(NOTA_AJUSTES_OMITIDOS_CATALOGO)

    return QueryResult(
        meta={
            "slug": report.slug,
            "name": report.name,
            "category": report.category,
            "version": report.version,
            "filters_applied": filters_applied,
            "extra": {
                "tabs": {
                    "marca_superart_jerarquia": arbol,
                    "marca_superart_filas": planas,
                },
                "ordenar_por": ordenar_por,
                "orden_forma": orden_forma,
            },
        },
        data=planas,
        totals=totals,
        notes=notes,
    )
