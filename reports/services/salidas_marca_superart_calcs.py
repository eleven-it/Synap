# -*- coding: utf-8 -*-
"""Cálculos y agrupación — informe Salidas por marca y SuperArtículo."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from django.http import QueryDict

from core.utils.administranet_types import to_int_or_none
from mpr.services_fabricados_superart import (
    _match_superarts_filtro,
    _normalizar_superarts_incluidos,
    etiqueta_mes,
    normalizar_meses_yyyy_mm,
    parse_filtros_fabricados_superart,
    parse_superarts_incluidos_desde_get,
)
from reports.services.compras_marca_superart_calcs import (
    MARCAS_COMPRAS_CODIGOS,
    _docenas_desde_prendas,
    _fmt_num,
    _packs_prendas,
    _resolve_marca_codigo_fila,
    marca_codigo_desde_nombre,
    sql_expresion_superart_compras,
    sql_marcas_compras_universo,
    superart_desde_articulo_compras,
    unidades_nu_desde_nombre,
)

SALIDAS_MARCA_SUPERART_SLUG = "salidas-marca-superart"

DEPOSITO_TERMINADO = 6

VIA_REM_FACTURADO = "rem_facturado"
VIA_REM_SIN_FACTURAR = "rem_sin_facturar"
VIA_REM_CONSIGNACION = "rem_consignacion"
VIA_FACTURA_DIRECTA = "factura_directa"
VIA_NCA = "nca"

VIAS_TRAZABILIDAD: Tuple[str, ...] = (
    VIA_REM_FACTURADO,
    VIA_REM_SIN_FACTURAR,
    VIA_REM_CONSIGNACION,
    VIA_FACTURA_DIRECTA,
    VIA_NCA,
)

VIA_LABELS: Dict[str, str] = {
    VIA_REM_FACTURADO: "REM facturado",
    VIA_REM_SIN_FACTURAR: "REM sin facturar",
    VIA_REM_CONSIGNACION: "REM consignación",
    VIA_FACTURA_DIRECTA: "Factura directa",
    VIA_NCA: "NCA (devolución)",
}


def _as_list(raw: Any) -> List[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        return [raw] if raw.strip() else []
    if isinstance(raw, (list, tuple)):
        return [str(x) for x in raw if str(x).strip()]
    return [str(raw)]


def parse_filters_from_payload(filters: Dict[str, Any]) -> Dict[str, Any]:
    qd = QueryDict(mutable=True)
    desde = (filters.get("desde") or filters.get("fecha_inicio") or filters.get("fecha_desde") or "").strip()
    hasta = (filters.get("hasta") or filters.get("fecha_fin") or filters.get("fecha_hasta") or "").strip()
    if desde:
        qd["desde"] = desde
    if hasta:
        qd["hasta"] = hasta
    for m in _as_list(filters.get("marcas_incluidos") or []):
        qd.appendlist("marcas_incluidos", m)
    superarts = filters.get("q_superart") or filters.get("superarts_incluidos") or []
    for s in _as_list(superarts):
        for part in str(s).split(","):
            part = part.strip()
            if part:
                qd.appendlist("q_superart", part)
    for m in _as_list(filters.get("marcas_excluidos") or []):
        qd.appendlist("marcas_excluidos", m)
    for s in _as_list(filters.get("superarts_excluidos") or []):
        qd.appendlist("superarts_excluidos", s)
    return parse_filtros_fabricados_superart(
        qd,
        marcas_getlist=qd.getlist("marcas_incluidos"),
    )


def parse_superarts_from_query_params(get_params) -> List[str]:
    return parse_superarts_incluidos_desde_get(get_params)


def sql_via_trazabilidad_salidas(alias_st: str = "st", alias_rem: str = "rem") -> str:
    st = alias_st.strip() or "st"
    rem = alias_rem.strip() or "rem"
    return f"""
        CASE
          WHEN COALESCE({st}.TipoComp, '') = 'Remito Salida' THEN
            CASE
              WHEN UPPER(TRIM(COALESCE({rem}.modalidad_remit, ''))) LIKE '%%CONSIG%%' THEN '{VIA_REM_CONSIGNACION}'
              WHEN UPPER(TRIM(COALESCE({rem}.modalidad_remit, ''))) LIKE '%%SIN FACT%%'
                OR UPPER(TRIM(COALESCE({rem}.modalidad_remit, ''))) IN ('NORMAL SIN FACTURAR', 'SIN FACTURAR')
                THEN '{VIA_REM_SIN_FACTURAR}'
              ELSE '{VIA_REM_FACTURADO}'
            END
          WHEN COALESCE({st}.TipoComp, '') = 'Venta'
            AND (COALESCE({st}.codmov_remito, 0) = 0) THEN '{VIA_FACTURA_DIRECTA}'
          WHEN COALESCE({st}.TipoComp, '') = 'Devol - Cliente' THEN '{VIA_NCA}'
          ELSE 'otro'
        END
    """.strip()


def sql_packs_netos_salidas(alias_st: str = "st") -> str:
    st = alias_st.strip() or "st"
    return f"""
        CASE
          WHEN COALESCE({st}.TipoComp, '') = 'Remito Salida' THEN COALESCE({st}.Salida, 0)
          WHEN COALESCE({st}.TipoComp, '') = 'Venta'
            AND (COALESCE({st}.codmov_remito, 0) = 0) THEN COALESCE({st}.Salida, 0)
          WHEN COALESCE({st}.TipoComp, '') = 'Devol - Cliente' THEN -COALESCE({st}.Entrada, 0)
          ELSE 0
        END
    """.strip()


def _init_via_por_mes(meses_ord: Sequence[str]) -> Dict[str, Dict[str, float]]:
    return {v: {m: 0.0 for m in meses_ord} for v in VIAS_TRAZABILIDAD}


def _acum_via(via_map: Dict[str, Dict[str, float]], via: str, ym: str, packs: float) -> None:
    if via not in via_map or ym not in via_map[via]:
        return
    via_map[via][ym] = round(via_map[via].get(ym, 0) + packs, 4)


def agrupar_salidas_marca_superart(
    filas_sql: Sequence[Dict[str, Any]],
    meses: Sequence[str],
    *,
    superarts_incluidos: Optional[Sequence[str]] = None,
    superarts_excluidos: Optional[Sequence[str]] = None,
    marcas_incluidos_ids: Optional[Sequence[int]] = None,
    marcas_excluidos_ids: Optional[Sequence[int]] = None,
) -> Dict[str, Any]:
    meses_ord = normalizar_meses_yyyy_mm(meses)
    if not meses_ord:
        meses_ord = []

    incl_marcas = set(int(x) for x in (marcas_incluidos_ids or []) if to_int_or_none(x) is not None)
    excl_marcas = set(int(x) for x in (marcas_excluidos_ids or []) if to_int_or_none(x) is not None)
    terminos_sa = _normalizar_superarts_incluidos(list(superarts_incluidos or []))
    terminos_sa_ex = _normalizar_superarts_incluidos(list(superarts_excluidos or []))

    por_art: Dict[Tuple[str, int], Dict[str, Any]] = {}
    articulos_vistos: set[int] = set()
    packs_por_via_mes = _init_via_por_mes(meses_ord)
    packs_por_via: Dict[str, float] = {v: 0.0 for v in VIAS_TRAZABILIDAD}

    for row in filas_sql or []:
        aid = to_int_or_none(row.get("id_articulo") or row.get("id_art"))
        if aid is None:
            continue
        ym = str(row.get("ym") or "").strip()
        if ym not in meses_ord:
            continue
        marca_cod = _resolve_marca_codigo_fila(row)
        if marca_cod not in MARCAS_COMPRAS_CODIGOS:
            continue
        cod_marca_int = to_int_or_none(row.get("codigo_marca"))
        if incl_marcas and (cod_marca_int is None or int(cod_marca_int) not in incl_marcas):
            continue
        if excl_marcas and cod_marca_int is not None and int(cod_marca_int) in excl_marcas:
            continue

        try:
            packs_raw = float(row.get("packs") or row.get("packs_netos") or 0)
        except (TypeError, ValueError):
            packs_raw = 0.0
        if abs(packs_raw) < 1e-9:
            continue

        via = str(row.get("via_trazabilidad") or "").strip()
        if via not in VIAS_TRAZABILIDAD:
            continue

        nom_art = str(row.get("nombre_articulo") or row.get("descripcion_articulo") or "")
        sk, cod_sa, desc_sa = superart_desde_articulo_compras(row.get("id_manual"), nom_art)
        if not _match_superarts_filtro(cod_sa, desc_sa, sk, terminos_sa):
            continue
        if terminos_sa_ex and _match_superarts_filtro(cod_sa, desc_sa, sk, terminos_sa_ex):
            continue

        packs, prendas = _packs_prendas(packs_raw, nom_art)
        key = (marca_cod, int(aid))
        if key not in por_art:
            por_art[key] = {
                "marca_codigo": marca_cod,
                "nombre_marca": str(row.get("nombre_marca") or marca_cod).strip() or marca_cod,
                "codigo_marca": cod_marca_int or 0,
                "id_articulo": int(aid),
                "codigo_articulo": str(row.get("codigo_articulo") or row.get("codigo") or "-"),
                "descripcion_articulo": nom_art or "-",
                "superart_key": sk,
                "codigo_superart": cod_sa,
                "descripcion_superart": desc_sa,
                "por_mes": {m: {"packs": 0.0, "prendas": 0.0, "docenas": 0.0} for m in meses_ord},
                "por_via": {v: 0.0 for v in VIAS_TRAZABILIDAD},
                "total_packs": 0.0,
                "total_prendas": 0.0,
                "total_docenas": 0.0,
            }
        art = por_art[key]
        cell = art["por_mes"][ym]
        cell["packs"] = round(cell["packs"] + packs, 4)
        cell["prendas"] = round(cell["prendas"] + prendas, 4)
        cell["docenas"] = _docenas_desde_prendas(cell["prendas"])
        art["por_via"][via] = round(art["por_via"].get(via, 0) + packs, 4)
        art["total_packs"] = round(art["total_packs"] + packs, 4)
        art["total_prendas"] = round(art["total_prendas"] + prendas, 4)
        art["total_docenas"] = _docenas_desde_prendas(art["total_prendas"])
        _acum_via(packs_por_via_mes, via, ym, packs)
        packs_por_via[via] = round(packs_por_via.get(via, 0) + packs, 4)
        articulos_vistos.add(int(aid))

    marcas_idx: Dict[str, Dict[str, Any]] = {}
    super_idx: Dict[Tuple[str, str], Dict[str, Any]] = {}

    for art in por_art.values():
        mc = art["marca_codigo"]
        if mc not in marcas_idx:
            marcas_idx[mc] = {
                "marca_codigo": mc,
                "nombre_marca": art["nombre_marca"],
                "por_mes": {m: {"packs": 0.0, "prendas": 0.0, "docenas": 0.0} for m in meses_ord},
                "por_via": {v: 0.0 for v in VIAS_TRAZABILIDAD},
                "total_packs": 0.0,
                "total_prendas": 0.0,
                "total_docenas": 0.0,
                "filas_superart": [],
            }
        marca = marcas_idx[mc]
        sk = art["superart_key"]
        skey = (mc, sk)
        if skey not in super_idx:
            super_node = {
                "superart_key": sk,
                "codigo_superart": art["codigo_superart"],
                "descripcion_superart": art["descripcion_superart"],
                "por_mes": {m: {"packs": 0.0, "prendas": 0.0, "docenas": 0.0} for m in meses_ord},
                "por_via": {v: 0.0 for v in VIAS_TRAZABILIDAD},
                "total_packs": 0.0,
                "total_prendas": 0.0,
                "total_docenas": 0.0,
                "articulos": [],
            }
            super_idx[skey] = super_node
            marca["filas_superart"].append(super_node)
        sa = super_idx[skey]
        sa["articulos"].append(art)

    for mc, marca in marcas_idx.items():
        marca["total_packs"] = 0.0
        marca["total_prendas"] = 0.0
        marca["total_docenas"] = 0.0
        for v in VIAS_TRAZABILIDAD:
            marca["por_via"][v] = 0.0
        for m in meses_ord:
            marca["por_mes"][m] = {"packs": 0.0, "prendas": 0.0, "docenas": 0.0}
        for sa in marca["filas_superart"]:
            sa["total_packs"] = 0.0
            sa["total_prendas"] = 0.0
            sa["total_docenas"] = 0.0
            for v in VIAS_TRAZABILIDAD:
                sa["por_via"][v] = 0.0
            for m in meses_ord:
                sa["por_mes"][m] = {"packs": 0.0, "prendas": 0.0, "docenas": 0.0}
            for art in sa["articulos"]:
                for m in meses_ord:
                    sa["por_mes"][m]["packs"] = round(
                        sa["por_mes"][m]["packs"] + art["por_mes"][m]["packs"], 4
                    )
                    sa["por_mes"][m]["prendas"] = round(
                        sa["por_mes"][m]["prendas"] + art["por_mes"][m]["prendas"], 4
                    )
                    sa["por_mes"][m]["docenas"] = _docenas_desde_prendas(sa["por_mes"][m]["prendas"])
                sa["total_packs"] = round(sa["total_packs"] + art["total_packs"], 4)
                sa["total_prendas"] = round(sa["total_prendas"] + art["total_prendas"], 4)
                sa["total_docenas"] = _docenas_desde_prendas(sa["total_prendas"])
                for v in VIAS_TRAZABILIDAD:
                    sa["por_via"][v] = round(sa["por_via"].get(v, 0) + art["por_via"].get(v, 0), 4)
            sa["articulos"].sort(key=lambda a: (-a["total_packs"], a["codigo_articulo"]))
            for m in meses_ord:
                marca["por_mes"][m]["packs"] = round(
                    marca["por_mes"][m]["packs"] + sa["por_mes"][m]["packs"], 4
                )
                marca["por_mes"][m]["prendas"] = round(
                    marca["por_mes"][m]["prendas"] + sa["por_mes"][m]["prendas"], 4
                )
                marca["por_mes"][m]["docenas"] = _docenas_desde_prendas(marca["por_mes"][m]["prendas"])
            marca["total_packs"] = round(marca["total_packs"] + sa["total_packs"], 4)
            marca["total_prendas"] = round(marca["total_prendas"] + sa["total_prendas"], 4)
            marca["total_docenas"] = _docenas_desde_prendas(marca["total_prendas"])
            for v in VIAS_TRAZABILIDAD:
                marca["por_via"][v] = round(marca["por_via"].get(v, 0) + sa["por_via"].get(v, 0), 4)
        marca["filas_superart"].sort(key=lambda s: (-s["total_packs"], (s["descripcion_superart"] or "").upper()))

    filas_marca = sorted(
        marcas_idx.values(),
        key=lambda m: (
            MARCAS_COMPRAS_CODIGOS.index(m["marca_codigo"])
            if m["marca_codigo"] in MARCAS_COMPRAS_CODIGOS
            else 99
        ),
    )

    totales_por_mes = {m: {"packs": 0.0, "prendas": 0.0, "docenas": 0.0} for m in meses_ord}
    total_packs = total_prendas = 0.0
    packs_por_marca_mes: Dict[str, Dict[str, float]] = {
        c: {m: 0.0 for m in meses_ord} for c in MARCAS_COMPRAS_CODIGOS
    }
    packs_por_marca: Dict[str, float] = {c: 0.0 for c in MARCAS_COMPRAS_CODIGOS}

    for marca in filas_marca:
        mc = marca["marca_codigo"]
        for m in meses_ord:
            p = marca["por_mes"][m]["packs"]
            totales_por_mes[m]["packs"] = round(totales_por_mes[m]["packs"] + p, 4)
            totales_por_mes[m]["prendas"] = round(
                totales_por_mes[m]["prendas"] + marca["por_mes"][m]["prendas"], 4
            )
            totales_por_mes[m]["docenas"] = _docenas_desde_prendas(totales_por_mes[m]["prendas"])
            if mc in packs_por_marca_mes:
                packs_por_marca_mes[mc][m] = round(packs_por_marca_mes[mc].get(m, 0) + p, 4)
        total_packs = round(total_packs + marca["total_packs"], 4)
        total_prendas = round(total_prendas + marca["total_prendas"], 4)
        if mc in packs_por_marca:
            packs_por_marca[mc] = round(packs_por_marca[mc] + marca["total_packs"], 4)

    total_docenas = _docenas_desde_prendas(total_prendas)

    return {
        "meses": meses_ord,
        "mes_labels": {m: etiqueta_mes(m) for m in meses_ord},
        "filas_marca": filas_marca,
        "totales_por_mes": totales_por_mes,
        "total_packs": total_packs,
        "total_prendas": total_prendas,
        "total_docenas": total_docenas,
        "articulos_con_salida": len(articulos_vistos),
        "packs_por_marca_mes": packs_por_marca_mes,
        "packs_por_marca": packs_por_marca,
        "packs_por_via": packs_por_via,
        "packs_por_via_mes": packs_por_via_mes,
        "via_labels": dict(VIA_LABELS),
    }


def flatten_filas_superart_por_marca(filas_marca: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for marca in filas_marca or []:
        mc = marca.get("marca_codigo") or ""
        for sa in marca.get("filas_superart") or []:
            row = {
                "marca_codigo": mc,
                "nombre_marca": marca.get("nombre_marca") or mc,
                "codigo_superart": sa.get("codigo_superart") or "",
                "descripcion_superart": sa.get("descripcion_superart") or "",
                "por_mes": dict(sa.get("por_mes") or {}),
                "por_via": dict(sa.get("por_via") or {}),
                "total_packs": sa.get("total_packs") or 0,
                "total_prendas": sa.get("total_prendas") or 0,
                "total_docenas": sa.get("total_docenas") or 0,
            }
            out.append(row)
    return out


def build_totals_planos(agrupado: Dict[str, Any]) -> Dict[str, float]:
    totals: Dict[str, float] = {
        "packs": float(agrupado.get("total_packs") or 0),
        "prendas": float(agrupado.get("total_prendas") or 0),
        "docenas": _docenas_desde_prendas(float(agrupado.get("total_prendas") or 0)),
        "articulos": float(agrupado.get("articulos_con_salida") or 0),
    }
    for mc, val in (agrupado.get("packs_por_marca") or {}).items():
        totals[f"packs_{mc}"] = float(val or 0)
    for mc, meses in (agrupado.get("packs_por_marca_mes") or {}).items():
        for ym, packs in (meses or {}).items():
            totals[f"packs_{mc}_{ym}"] = float(packs or 0)
    for via, val in (agrupado.get("packs_por_via") or {}).items():
        totals[f"packs_via_{via}"] = float(val or 0)
    mstock = agrupado.get("mstock_kpi_packs")
    if mstock is not None:
        totals["mstock_kpi_packs"] = float(mstock or 0)
    return totals


def preparar_salidas_marca_superart_presentacion(data: Dict[str, Any]) -> Dict[str, Any]:
    meses = list(data.get("meses") or [])
    meses_columnas = [{"ym": m, "label": (data.get("mes_labels") or {}).get(m, m)} for m in meses]

    def _cols(por_mes: Dict[str, Any]) -> List[Dict[str, str]]:
        out_cols: List[Dict[str, str]] = []
        for m in meses:
            cell = por_mes.get(m) or {}
            packs = cell.get("packs") or 0
            prendas = cell.get("prendas") or 0
            out_cols.append(
                {
                    "ym": m,
                    "packs": packs,
                    "prendas": prendas,
                    "display": f"{_fmt_num(packs)} pk · {_fmt_num(prendas)} pr",
                }
            )
        return out_cols

    def _via_cols(por_via: Dict[str, Any]) -> List[Dict[str, Any]]:
        labels = data.get("via_labels") or VIA_LABELS
        out_v: List[Dict[str, Any]] = []
        for v in VIAS_TRAZABILIDAD:
            out_v.append(
                {
                    "via": v,
                    "label": labels.get(v, v),
                    "packs": float(por_via.get(v) or 0),
                }
            )
        return out_v

    filas_marca = []
    for marca in data.get("filas_marca") or []:
        mcopy = dict(marca)
        mcopy["columnas_mes"] = _cols(marca.get("por_mes") or {})
        mcopy["columnas_via"] = _via_cols(marca.get("por_via") or {})
        supers = []
        for sa in marca.get("filas_superart") or []:
            sc = dict(sa)
            sc["columnas_mes"] = _cols(sa.get("por_mes") or {})
            sc["columnas_via"] = _via_cols(sa.get("por_via") or {})
            sc["total_display"] = (
                f"{_fmt_num(sa.get('total_packs'))} pk · {_fmt_num(sa.get('total_prendas'))} pr"
            )
            supers.append(sc)
        mcopy["filas_superart"] = supers
        mcopy["total_display"] = (
            f"{_fmt_num(marca.get('total_packs'))} pk · {_fmt_num(marca.get('total_prendas'))} pr"
        )
        filas_marca.append(mcopy)

    totales_columnas = _cols(data.get("totales_por_mes") or {})
    return {
        **data,
        "meses_columnas": meses_columnas,
        "filas_marca": filas_marca,
        "totales_columnas": totales_columnas,
        "totales_via_columnas": _via_cols(data.get("packs_por_via") or {}),
        "total_packs_display": _fmt_num(data.get("total_packs")),
        "total_prendas_display": _fmt_num(data.get("total_prendas")),
        "total_docenas_display": _fmt_num(data.get("total_docenas")),
    }


__all__ = [
    "SALIDAS_MARCA_SUPERART_SLUG",
    "sql_expresion_superart_compras",
    "sql_marcas_compras_universo",
    "marca_codigo_desde_nombre",
    "superart_desde_articulo_compras",
    "unidades_nu_desde_nombre",
]
