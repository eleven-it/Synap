# -*- coding: utf-8 -*-
"""Agregación Marca → SuperArt → Artículo con columnas mensuales (informes BestSox)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from core.utils.administranet_types import to_int_or_none

from mpr.services_fabricados_superart import (
    SIN_SUPERART_LABEL,
    etiqueta_mes,
    normalizar_meses_yyyy_mm,
    superart_desde_id_manual,
)


def _mes_label_corto(ym: str) -> str:
    """Etiqueta corta tipo «Ago» para columnas Excel."""
    full = etiqueta_mes(ym)
    if " " in full:
        return full.split(" ", 1)[0]
    return full


def metric_keys_for_meses(meses: Sequence[str], prefix: str) -> List[str]:
    keys = [f"{prefix}_{_mes_label_corto(m)}" for m in meses]
    keys.append(f"{prefix}_Total")
    return keys


def empty_metric_map(meses: Sequence[str], prefix: str) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for m in meses:
        out[f"{prefix}_{_mes_label_corto(m)}"] = 0.0
    out[f"{prefix}_Total"] = 0.0
    return out


def _acum_metric(dest: Dict[str, float], prefix: str, ym: str, meses: Sequence[str], delta: float) -> None:
    if ym in meses:
        key = f"{prefix}_{_mes_label_corto(ym)}"
        dest[key] = round(float(dest.get(key) or 0) + delta, 4)
    dest[f"{prefix}_Total"] = round(float(dest.get(f"{prefix}_Total") or 0) + delta, 4)


def _display_marca(codigo_marca: Any, nombre_marca: Any) -> Tuple[int, str]:
    cod = to_int_or_none(codigo_marca) or 0
    nombre = str(nombre_marca or "").strip()
    if cod == 0 and not nombre:
        return 0, "Sin marca"
    if not nombre:
        return cod, f"Marca {cod}"
    return cod, nombre


def agregar_filas_marca_superart_periodo(
    filas_sql: Sequence[Dict[str, Any]],
    meses: Sequence[str],
    *,
    metric_prefix: str,
    metric_field: str = "cantidad",
    fuente_field: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Construye árbol marca → superart → artículo con métricas por mes + total.

    Cada fila SQL debe traer: id_articulo, id_manual, codigo_marca, nombre_marca,
    codigo_articulo, nombre_articulo, ym, cantidad (o metric_field), opcional fuente.
    """
    meses_ord = normalizar_meses_yyyy_mm(meses)
    marcas: Dict[Tuple[int, str], Dict[str, Any]] = {}
    super_idx: Dict[Tuple[Tuple[int, str], str], Dict[str, Any]] = {}

    for row in filas_sql or []:
        aid = to_int_or_none(row.get("id_articulo"))
        if aid is None:
            continue
        ym = str(row.get("ym") or "").strip()
        if ym and ym not in meses_ord:
            continue
        try:
            qty = float(row.get(metric_field) or row.get("cantidad") or 0)
        except (TypeError, ValueError):
            qty = 0.0
        if abs(qty) < 1e-9:
            continue

        cod_m, nom_m = _display_marca(row.get("codigo_marca"), row.get("nombre_marca"))
        _, cod_sa, desc_sa = superart_desde_id_manual(row.get("id_manual"))
        if not desc_sa:
            desc_sa = SIN_SUPERART_LABEL
        mk = (cod_m, nom_m)
        if mk not in marcas:
            marcas[mk] = {
                "tipo": "marca",
                "codigo_marca": cod_m,
                "nombre_marca": nom_m,
                "metrics": empty_metric_map(meses_ord, metric_prefix),
                "children": [],
            }
        marca = marcas[mk]
        _acum_metric(marca["metrics"], metric_prefix, ym, meses_ord, qty)

        sk = (mk, cod_sa or desc_sa)
        if sk not in super_idx:
            super_node = {
                "tipo": "superart",
                "codigo_superart": cod_sa,
                "nombre_superart": desc_sa,
                "metrics": empty_metric_map(meses_ord, metric_prefix),
                "children": [],
            }
            super_idx[sk] = super_node
            marca["children"].append(super_node)
        superart = super_idx[sk]
        _acum_metric(superart["metrics"], metric_prefix, ym, meses_ord, qty)

        art_key = aid
        art_node = next(
            (c for c in superart["children"] if c.get("tipo") == "articulo" and c.get("id_articulo") == art_key),
            None,
        )
        if not art_node:
            art_node = {
                "tipo": "articulo",
                "id_articulo": aid,
                "codigo_articulo": row.get("codigo_articulo") or aid,
                "nombre_articulo": row.get("nombre_articulo") or f"Artículo {aid}",
                "metrics": empty_metric_map(meses_ord, metric_prefix),
                "children": [],
            }
            if fuente_field and row.get(fuente_field):
                art_node["fuente"] = row.get(fuente_field)
            superart["children"].append(art_node)
        _acum_metric(art_node["metrics"], metric_prefix, ym, meses_ord, qty)

    arbol = list(marcas.values())
    arbol.sort(key=lambda m: (-float((m.get("metrics") or {}).get(f"{metric_prefix}_Total") or 0), m["nombre_marca"]))
    for marca in arbol:
        supers = marca.get("children") or []
        supers.sort(
            key=lambda s: (
                -float((s.get("metrics") or {}).get(f"{metric_prefix}_Total") or 0),
                (s.get("nombre_superart") or "").upper(),
            )
        )
        for sa in supers:
            arts = sa.get("children") or []
            arts.sort(
                key=lambda a: (
                    -float((a.get("metrics") or {}).get(f"{metric_prefix}_Total") or 0),
                    str(a.get("nombre_articulo") or "").upper(),
                )
            )
        marca["children"] = supers

    totales = empty_metric_map(meses_ord, metric_prefix)
    for marca in arbol:
        for k, v in (marca.get("metrics") or {}).items():
            totales[k] = round(float(totales.get(k) or 0) + float(v or 0), 4)

    return {
        "meses": meses_ord,
        "mes_labels": {m: _mes_label_corto(m) for m in meses_ord},
        "metric_prefix": metric_prefix,
        "marca_superart_jerarquia": arbol,
        "totales_generales": totales,
    }


def totales_por_marca_tabla(arbol: Sequence[Dict[str, Any]], metric_prefix: str) -> List[Dict[str, Any]]:
    """Filas planas «Totales por marca» (cabecera superior)."""
    out: List[Dict[str, Any]] = []
    for marca in arbol or []:
        metrics = dict(marca.get("metrics") or {})
        supers = marca.get("children") or []
        arts = sum(len(sa.get("children") or []) for sa in supers)
        out.append(
            {
                "codigo_marca": marca.get("codigo_marca"),
                "nombre_marca": marca.get("nombre_marca"),
                "superarts": len(supers),
                "articulos": arts,
                **metrics,
            }
        )
    return out
