# -*- coding: utf-8 -*-
"""Reporte MPR: fabricado de 1ra por superartículo y mes."""
from __future__ import annotations

import logging
from calendar import monthrange
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

from core.utils.administranet_types import to_date_or_none, to_int_or_none

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


def _parse_fecha_iso(value: Any) -> Optional[date]:
    iso = to_date_or_none(value)
    if not iso:
        return None
    try:
        return datetime.strptime(str(iso)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def primer_dia_mes_calendario(hoy: Optional[date] = None) -> date:
    d = hoy or date.today()
    return d.replace(day=1)


def ultimo_dia_mes_calendario(hoy: Optional[date] = None) -> date:
    d = hoy or date.today()
    return d.replace(day=monthrange(d.year, d.month)[1])


def meses_en_rango(desde: date, hasta: date) -> List[str]:
    """Meses calendario AAAA-MM que intersectan [desde, hasta] (inclusive)."""
    if desde > hasta:
        desde, hasta = hasta, desde
    out: List[str] = []
    y, m = desde.year, desde.month
    end_y, end_m = hasta.year, hasta.month
    while (y, m) <= (end_y, end_m):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            m = 1
            y += 1
    return out


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


def _normalizar_superarts_incluidos(raw: Sequence[str]) -> List[str]:
    out: List[str] = []
    seen: set[str] = set()
    for item in raw or []:
        part = str(item or "").strip()
        if not part:
            continue
        key = part.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(part)
    return out


def parse_superarts_incluidos_desde_get(get_params) -> List[str]:
    """Lista q_superart: parámetro repetido, getlist o valores separados por coma."""
    raw: List[str] = []
    if hasattr(get_params, "getlist"):
        raw = list(get_params.getlist("q_superart") or [])
    if not raw:
        single = (get_params.get("q_superart") or get_params.get("q") or "").strip()
        if single:
            raw = [p.strip() for p in single.split(",") if p.strip()]
    else:
        expanded: List[str] = []
        for item in raw:
            for part in str(item).split(","):
                part = part.strip()
                if part:
                    expanded.append(part)
        raw = expanded
    return _normalizar_superarts_incluidos(raw)


def _match_superarts_filtro(
    codigo: str,
    descripcion: str,
    superart_key: str,
    terminos: Sequence[str],
) -> bool:
    """OR entre términos; vacío = sin filtro. Compatible con búsqueda parcial (un valor)."""
    if not terminos:
        return True
    cod_l = (codigo or "").lower()
    desc_l = (descripcion or "").lower()
    key_l = (superart_key or "").lower()
    for term in terminos:
        t = str(term or "").strip().lower()
        if not t:
            continue
        if t == cod_l or t == desc_l or t == key_l:
            return True
        if t in cod_l or t in desc_l:
            return True
    return False


def agrupar_fabricados_por_superart(
    filas_sql: Sequence[Dict[str, Any]],
    meses: Sequence[str],
    desc_map: Dict[int, Tuple[str, str]],
    *,
    superarts_incluidos: Optional[Sequence[str]] = None,
    busqueda_superart: str = "",
    superarts_excluidos: Optional[Sequence[str]] = None,
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

    terminos = _normalizar_superarts_incluidos(list(superarts_incluidos or []))
    if not terminos and (busqueda_superart or "").strip():
        terminos = _normalizar_superarts_incluidos([busqueda_superart])
    terminos_ex = _normalizar_superarts_incluidos(list(superarts_excluidos or []))
    filas_super: List[Dict[str, Any]] = []
    for sa in super_idx.values():
        if not _match_superarts_filtro(
            sa["codigo_superart"],
            sa["descripcion_superart"],
            sa.get("superart_key") or "",
            terminos,
        ):
            continue
        if terminos_ex and _match_superarts_filtro(
            sa["codigo_superart"],
            sa["descripcion_superart"],
            sa.get("superart_key") or "",
            terminos_ex,
        ):
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
    ref = hoy or date.today()
    desde_raw = (get_params.get("desde") or get_params.get("fecha_desde") or "").strip()
    hasta_raw = (get_params.get("hasta") or get_params.get("fecha_hasta") or "").strip()
    desde_d = _parse_fecha_iso(desde_raw) or primer_dia_mes_calendario(ref)
    hasta_d = _parse_fecha_iso(hasta_raw) or ref
    if hasta_d < desde_d:
        desde_d, hasta_d = hasta_d, desde_d

    meses_raw: List[str] = []
    if hasattr(get_params, "getlist"):
        meses_raw = list(get_params.getlist("meses") or [])
    if not meses_raw:
        single = (get_params.get("meses") or "").strip()
        if single:
            meses_raw = [p.strip() for p in single.split(",") if p.strip()]
    meses_legacy = normalizar_meses_yyyy_mm(meses_raw)
    if meses_legacy and not desde_raw and not hasta_raw:
        meses = meses_legacy
    else:
        meses = meses_en_rango(desde_d, hasta_d)
    if not meses:
        meses = [mes_actual_yyyy_mm(ref)]

    marcas: List[int] = []
    raw_marcas = list(marcas_getlist or [])
    if not raw_marcas and get_params.get("marcas_incluidos"):
        raw_marcas = [get_params.get("marcas_incluidos")]
    for m in raw_marcas:
        mi = to_int_or_none(m)
        if mi is not None:
            marcas.append(int(mi))

    superarts = parse_superarts_incluidos_desde_get(get_params)

    marcas_ex: List[int] = []
    raw_ex: List[str] = []
    if hasattr(get_params, "getlist"):
        raw_ex = list(get_params.getlist("marcas_excluidos") or [])
    if not raw_ex and get_params.get("marcas_excluidos"):
        raw_ex = [get_params.get("marcas_excluidos")]
    for m in raw_ex:
        for part in str(m).split(","):
            mi = to_int_or_none(part.strip())
            if mi is not None and int(mi) not in marcas_ex:
                marcas_ex.append(int(mi))
    sa_ex_raw: List[str] = []
    if hasattr(get_params, "getlist"):
        sa_ex_raw = list(get_params.getlist("superarts_excluidos") or [])
    if not sa_ex_raw and get_params.get("superarts_excluidos"):
        sa_ex_raw = [get_params.get("superarts_excluidos")]
    sa_ex_parts: List[str] = []
    for s_ in sa_ex_raw:
        sa_ex_parts.extend(p.strip() for p in str(s_).split(",") if p.strip())
    superarts_ex = _normalizar_superarts_incluidos(sa_ex_parts)
    return {
        "desde_iso": desde_d.isoformat(),
        "hasta_iso": hasta_d.isoformat(),
        "meses": meses,
        "marcas_incluidos": marcas,
        "superarts_incluidos": superarts,
        "marcas_excluidos": marcas_ex,
        "superarts_excluidos": superarts_ex,
        # Compat lectura legacy (primer valor o cadena vacía)
        "busqueda_superart": superarts[0] if len(superarts) == 1 else "",
    }


def buscar_marcas_predictivo(
    base_empresa: str,
    q: str,
    *,
    limit: int = 25,
) -> List[Dict[str, Any]]:
    """Sugerencias de marca para autocompletar (value/label)."""
    from stock.services.inventario_tabla import listar_marcas_catalogo

    texto = (q or "").strip().lower()
    if not texto or not (base_empresa or "").strip():
        return []
    catalogo = listar_marcas_catalogo(base_empresa)
    out: List[Dict[str, Any]] = []
    for item in catalogo:
        label = str(item.get("label") or "")
        if texto in label.lower():
            out.append({"value": item.get("value"), "label": label})
            if len(out) >= max(1, limit):
                break
    return out


def buscar_superart_predictivo(
    base_empresa: str,
    q: str,
    *,
    limit: int = 25,
) -> List[Dict[str, str]]:
    """Superartículos distintos (id_manual) para autocompletar."""
    texto = (q or "").strip()
    if len(texto) < 1 or not (base_empresa or "").strip():
        return []
    lim = max(1, min(int(limit or 25), 50))
    like = f"%{texto}%"
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            cursor.execute(
                """
                SELECT DISTINCT TRIM(a.id_manual) AS codigo
                FROM articulo a
                WHERE TRIM(COALESCE(a.id_manual, '')) <> ''
                  AND a.id_manual LIKE %s
                ORDER BY codigo
                LIMIT %s
                """,
                (like, lim),
            )
            rows = cursor.fetchall() or []
    except Exception as exc:
        logger.warning("buscar_superart_predictivo %s: %s", base_empresa, exc)
        return []
    out: List[Dict[str, str]] = []
    for row in rows:
        codigo = str((row.get("codigo") if isinstance(row, dict) else row[0]) or "").strip()
        if not codigo:
            continue
        out.append({"codigo": codigo, "descripcion": codigo})
    return out


def reporte_mpr_fabricados_superart(
    base_empresa: str,
    *,
    meses: Sequence[str],
    marcas_incluidos: Optional[Sequence[int]] = None,
    superarts_incluidos: Optional[Sequence[str]] = None,
    busqueda_superart: str = "",
    marcas_excluidos: Optional[Sequence[int]] = None,
    superarts_excluidos: Optional[Sequence[str]] = None,
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
                marcas_excluidos_ids=marcas_excluidos or None,
            )
    except Exception as exc:
        logger.warning("reporte_mpr_fabricados_superart %s: %s", base_empresa, exc, exc_info=True)
        return vacio

    art_ids = list({to_int_or_none(r.get("id_articulo")) for r in rows})
    art_ids = [a for a in art_ids if a is not None]
    desc_map = _fetch_descripciones_articulo(base_empresa, art_ids) if art_ids else {}
    superarts = _normalizar_superarts_incluidos(list(superarts_incluidos or []))
    if not superarts and (busqueda_superart or "").strip():
        superarts = _normalizar_superarts_incluidos([busqueda_superart])
    return agrupar_fabricados_por_superart(
        rows,
        meses_norm,
        desc_map,
        superarts_incluidos=superarts,
        superarts_excluidos=superarts_excluidos,
    )
