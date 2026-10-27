# -*- coding: utf-8 -*-
"""Reporte MPR: fabricado de 1ra por superartículo y mes."""
from __future__ import annotations

import logging
from datetime import date
from typing import Any, Dict, List, Optional, Sequence, Tuple

from core.utils.administranet_types import to_int_or_none

from mpr.reportes_transicion_lote_sql import (
    fetch_fabricado_primera_por_articulo_mes,
    normalizar_meses_yyyy_mm,
)
from mpr.services import _fetch_descripciones_articulo, mysql_cursor

logger = logging.getLogger(__name__)

SIN_SUPERART_CODIGO = ""
SIN_SUPERART_LABEL = "Sin superartículo"

_MESES_CORTO = (
    "",
    "Ene",
    "Feb",
    "Mar",
    "Abr",
    "May",
    "Jun",
    "Jul",
    "Ago",
    "Sep",
    "Oct",
    "Nov",
    "Dic",
)


def mes_actual_yyyy_mm(hoy: Optional[date] = None) -> str:
    d = hoy or date.today()
    return f"{d.year:04d}-{d.month:02d}"


def opciones_meses_selector(cantidad: int = 36, hoy: Optional[date] = None) -> List[Dict[str, str]]:
    """Últimos N meses calendario para multi-select (valor ISO año-mes)."""
    d = hoy or date.today()
    y, m = d.year, d.month
    out: List[Dict[str, str]] = []
    for _ in range(cantidad):
        val = f"{y:04d}-{m:02d}"
        label = f"{_MESES_CORTO[m]} {y}" if 1 <= m <= 12 else val
        out.append({"value": val, "label": label})
        m -= 1
        if m < 1:
            m = 12
            y -= 1
    return out


def etiqueta_mes(ym: str) -> str:
    try:
        y, m = ym.split("-", 1)
        mi = int(m)
        return f"{_MESES_CORTO[mi]} {y}" if 1 <= mi <= 12 else ym
    except (ValueError, IndexError):
        return ym


def superart_desde_id_manual(id_manual: Any) -> Tuple[str, str, str]:
    """
    Retorna (clave_agrupación, código_display, descripción_display).
    Paridad con ventas_marca_superart: id_manual = SuperArt.
    """
    manual = str(id_manual or "").strip()
    if not manual:
        return "__sin_superart__", SIN_SUPERART_CODIGO, SIN_SUPERART_LABEL
    return manual.upper(), manual, manual


def _match_busqueda_superart(codigo: str, descripcion: str, q: str) -> bool:
    if not q:
        return True
    qq = q.lower()
    return qq in (codigo or "").lower() or qq in (descripcion or "").lower()


def agrupar_fabricados_por_superart(
    filas_sql: Sequence[Dict[str, Any]],
    meses: Sequence[str],
    desc_map: Dict[int, Tuple[str, str]],
    *,
    busqueda_superart: str = "",
) -> Dict[str, Any]:
    meses_ord = normalizar_meses_yyyy_mm(meses)
    if not meses_ord:
        meses_ord = []

    por_art: Dict[int, Dict[str, Any]] = {}
    for row in filas_sql or []:
        aid = to_int_or_none(row.get("id_articulo"))
        if aid is None:
            continue
        ym = str(row.get("ym") or "").strip()
        if ym not in meses_ord:
            continue
        try:
            qty = float(row.get("cantidad") or 0)
        except (TypeError, ValueError):
            qty = 0.0
        if qty <= 0:
            continue
        sk, cod_sa, desc_sa = superart_desde_id_manual(row.get("id_manual"))
        cod_art, nom_art = desc_map.get(aid, ("-", "-"))
        if aid not in por_art:
            por_art[aid] = {
                "id_articulo": aid,
                "codigo_articulo": cod_art,
                "descripcion_articulo": nom_art,
                "superart_key": sk,
                "codigo_superart": cod_sa,
                "descripcion_superart": desc_sa,
                "por_mes": {m: 0.0 for m in meses_ord},
                "total": 0.0,
            }
        por_art[aid]["por_mes"][ym] = round(por_art[aid]["por_mes"].get(ym, 0) + qty, 4)
        por_art[aid]["total"] = round(por_art[aid]["total"] + qty, 4)

    super_idx: Dict[str, Dict[str, Any]] = {}
    for art in por_art.values():
        sk = art["superart_key"]
        if sk not in super_idx:
            super_idx[sk] = {
                "superart_key": sk,
                "codigo_superart": art["codigo_superart"],
                "descripcion_superart": art["descripcion_superart"],
                "por_mes": {m: 0.0 for m in meses_ord},
                "total": 0.0,
                "articulos": [],
            }
        sa = super_idx[sk]
        sa["articulos"].append(art)
        for m in meses_ord:
            sa["por_mes"][m] = round(sa["por_mes"].get(m, 0) + art["por_mes"].get(m, 0), 4)
        sa["total"] = round(sa["total"] + art["total"], 4)

    q = (busqueda_superart or "").strip()
    filas_super: List[Dict[str, Any]] = []
    for sa in super_idx.values():
        if not _match_busqueda_superart(sa["codigo_superart"], sa["descripcion_superart"], q):
            continue
        sa["articulos"].sort(key=lambda a: (-a["total"], a["codigo_articulo"]))
        filas_super.append(sa)

    filas_super.sort(key=lambda r: (-r["total"], r["descripcion_superart"].upper()))

    totales_por_mes = {m: 0.0 for m in meses_ord}
    total_general = 0.0
    for sa in filas_super:
        for m in meses_ord:
            totales_por_mes[m] = round(totales_por_mes.get(m, 0) + sa["por_mes"].get(m, 0), 4)
        total_general = round(total_general + sa["total"], 4)

    mes_pico = ""
    mes_pico_cantidad = 0.0
    for m in meses_ord:
        v = totales_por_mes.get(m, 0)
        if v > mes_pico_cantidad:
            mes_pico_cantidad = v
            mes_pico = m

    superarts_con_prod = sum(1 for sa in filas_super if sa["total"] > 0)

    return {
        "meses": meses_ord,
        "mes_labels": {m: etiqueta_mes(m) for m in meses_ord},
        "filas_superart": filas_super,
        "totales_por_mes": totales_por_mes,
        "total_general": total_general,
        "kpis": {
            "total_fabricado_primera": total_general,
            "superarts_con_produccion": superarts_con_prod,
            "mes_pico": mes_pico,
            "mes_pico_cantidad": mes_pico_cantidad,
            "mes_pico_label": etiqueta_mes(mes_pico) if mes_pico else "—",
        },
    }


def parse_filtros_fabricados_superart(
    get_params,
    *,
    marcas_getlist: Optional[Sequence[str]] = None,
    hoy: Optional[date] = None,
) -> Dict[str, Any]:
    meses_raw: List[str] = []
    if hasattr(get_params, "getlist"):
        meses_raw = list(get_params.getlist("meses") or [])
    if not meses_raw:
        single = (get_params.get("meses") or "").strip()
        if single:
            meses_raw = [p.strip() for p in single.split(",") if p.strip()]
    meses = normalizar_meses_yyyy_mm(meses_raw)
    if not meses:
        meses = [mes_actual_yyyy_mm(hoy)]

    marcas: List[int] = []
    raw_marcas = list(marcas_getlist or [])
    if not raw_marcas and get_params.get("marcas_incluidos"):
        raw_marcas = [get_params.get("marcas_incluidos")]
    for m in raw_marcas:
        mi = to_int_or_none(m)
        if mi is not None:
            marcas.append(int(mi))

    busqueda = (get_params.get("q_superart") or get_params.get("q") or "").strip()
    return {
        "meses": meses,
        "marcas_incluidos": marcas,
        "busqueda_superart": busqueda,
    }


def reporte_mpr_fabricados_superart(
    base_empresa: str,
    *,
    meses: Sequence[str],
    marcas_incluidos: Optional[Sequence[int]] = None,
    busqueda_superart: str = "",
) -> Dict[str, Any]:
    vacio = {
        "meses": normalizar_meses_yyyy_mm(meses) or [mes_actual_yyyy_mm()],
        "mes_labels": {},
        "filas_superart": [],
        "totales_por_mes": {},
        "total_general": 0.0,
        "kpis": {
            "total_fabricado_primera": 0.0,
            "superarts_con_produccion": 0,
            "mes_pico": "",
            "mes_pico_cantidad": 0.0,
            "mes_pico_label": "—",
        },
    }
    if not (base_empresa or "").strip():
        return vacio
    meses_norm = normalizar_meses_yyyy_mm(meses) or [mes_actual_yyyy_mm()]
    vacio["meses"] = meses_norm
    vacio["mes_labels"] = {m: etiqueta_mes(m) for m in meses_norm}
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            rows = fetch_fabricado_primera_por_articulo_mes(
                cursor,
                meses_norm,
                marcas_ids=marcas_incluidos or None,
            )
    except Exception as exc:
        logger.warning("reporte_mpr_fabricados_superart %s: %s", base_empresa, exc, exc_info=True)
        return vacio

    art_ids = list({to_int_or_none(r.get("id_articulo")) for r in rows})
    art_ids = [a for a in art_ids if a is not None]
    desc_map = _fetch_descripciones_articulo(base_empresa, art_ids) if art_ids else {}
    return agrupar_fabricados_por_superart(
        rows,
        meses_norm,
        desc_map,
        busqueda_superart=busqueda_superart,
    )
