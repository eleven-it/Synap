# -*- coding: utf-8 -*-
"""Presentación jerárquica Cliente → Marca → SuperArt → Artículo (consignación)."""
from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple

from core.utils.administranet_types import to_int_or_none

from mpr.services_fabricados_superart import SIN_SUPERART_LABEL, superart_desde_id_manual


def nest_consignacion_cliente_marca(filas: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    clientes: Dict[Tuple[int, str], Dict[str, Any]] = {}
    marca_idx: Dict[Tuple[Tuple[int, str], Tuple[int, str]], Dict[str, Any]] = {}
    super_idx: Dict[Any, Dict[str, Any]] = {}

    for row in filas or []:
        cod_cli = to_int_or_none(row.get("codigo_cliente")) or 0
        nom_cli = str(row.get("nombre_cliente") or "").strip() or f"Cliente {cod_cli}"
        cod_m = to_int_or_none(row.get("codigo_marca")) or 0
        nom_m = str(row.get("nombre_marca") or "").strip() or "Sin marca"
        _, cod_sa, desc_sa = superart_desde_id_manual(row.get("id_manual"))
        if not desc_sa:
            desc_sa = SIN_SUPERART_LABEL
        aid = to_int_or_none(row.get("id_articulo")) or 0

        packs = float(row.get("packs_saldo") or 0)
        prendas = float(row.get("prendas_saldo") or 0)
        docenas = float(row.get("docenas_saldo") or 0)
        if abs(packs) < 1e-9:
            continue

        ck = (cod_cli, nom_cli)
        if ck not in clientes:
            clientes[ck] = {
                "tipo": "cliente",
                "codigo_cliente": cod_cli,
                "nombre_cliente": nom_cli,
                "packs_saldo": 0.0,
                "prendas_saldo": 0.0,
                "docenas_saldo": 0.0,
                "children": [],
            }
        cli = clientes[ck]
        for k, v in (
            ("packs_saldo", packs),
            ("prendas_saldo", prendas),
            ("docenas_saldo", docenas),
        ):
            cli[k] = round(float(cli.get(k) or 0) + v, 4)

        mk = (ck, (cod_m, nom_m))
        if mk not in marca_idx:
            marca_node = {
                "tipo": "marca",
                "codigo_marca": cod_m,
                "nombre_marca": nom_m,
                "packs_saldo": 0.0,
                "prendas_saldo": 0.0,
                "docenas_saldo": 0.0,
                "children": [],
            }
            marca_idx[mk] = marca_node
            cli["children"].append(marca_node)
        marca = marca_idx[mk]
        for k, v in (
            ("packs_saldo", packs),
            ("prendas_saldo", prendas),
            ("docenas_saldo", docenas),
        ):
            marca[k] = round(float(marca.get(k) or 0) + v, 4)

        sk = (mk, (cod_sa, desc_sa))
        if sk not in super_idx:
            sa_node = {
                "tipo": "superart",
                "codigo_superart": cod_sa,
                "nombre_superart": desc_sa,
                "packs_saldo": 0.0,
                "prendas_saldo": 0.0,
                "docenas_saldo": 0.0,
                "children": [],
            }
            super_idx[sk] = sa_node
            marca["children"].append(sa_node)
        sa = super_idx[sk]
        for k, v in (
            ("packs_saldo", packs),
            ("prendas_saldo", prendas),
            ("docenas_saldo", docenas),
        ):
            sa[k] = round(float(sa.get(k) or 0) + v, 4)

        sa["children"].append(
            {
                "tipo": "articulo",
                "id_articulo": aid,
                "nombre_articulo": row.get("nombre_articulo") or f"Artículo {aid}",
                "packs_saldo": packs,
                "prendas_saldo": prendas,
                "docenas_saldo": docenas,
            }
        )

    out = list(clientes.values())
    out.sort(key=lambda c: (c.get("nombre_cliente") or "").upper())
    return out


def totales_marca_consignacion(filas: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_marca: Dict[Tuple[int, str], Dict[str, Any]] = {}
    arts: Dict[Tuple[int, str], set] = {}
    supers: Dict[Tuple[int, str], set] = {}
    for row in filas or []:
        cod_m = to_int_or_none(row.get("codigo_marca")) or 0
        nom_m = str(row.get("nombre_marca") or "").strip() or "Sin marca"
        key = (cod_m, nom_m)
        if key not in by_marca:
            by_marca[key] = {
                "codigo_marca": cod_m,
                "nombre_marca": nom_m,
                "packs_saldo": 0.0,
                "prendas_saldo": 0.0,
                "docenas_saldo": 0.0,
                "articulos": 0,
                "superarts": 0,
            }
            arts[key] = set()
            supers[key] = set()
        for k in ("packs_saldo", "prendas_saldo", "docenas_saldo"):
            by_marca[key][k] = round(float(by_marca[key][k]) + float(row.get(k) or 0), 4)
        arts[key].add(to_int_or_none(row.get("id_articulo")))
        _, cod_sa, _ = superart_desde_id_manual(row.get("id_manual"))
        supers[key].add(cod_sa or "")
    out = []
    for key, row in by_marca.items():
        row["articulos"] = len(arts[key])
        row["superarts"] = len(supers[key])
        out.append(row)
    out.sort(key=lambda r: (-float(r.get("packs_saldo") or 0), r.get("nombre_marca") or ""))
    return out
