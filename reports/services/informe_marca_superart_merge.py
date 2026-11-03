# -*- coding: utf-8 -*-
"""Combina árboles Marca/SuperArt/Artículo con distintos prefijos de métrica."""
from __future__ import annotations

from typing import Any, Dict, List, Sequence


def _node_key_marca(node: Dict[str, Any]) -> tuple:
    return (node.get("codigo_marca"), node.get("nombre_marca"))


def _node_key_super(node: Dict[str, Any]) -> tuple:
    return (node.get("codigo_superart"), node.get("nombre_superart"))


def _node_key_art(node: Dict[str, Any]) -> tuple:
    return (node.get("id_articulo"), node.get("codigo_articulo"))


def merge_metric_prefixes(
    base_arbol: Sequence[Dict[str, Any]],
    extra_arboles: Sequence[tuple[str, Sequence[Dict[str, Any]]]],
) -> List[Dict[str, Any]]:
    """
    ``extra_arboles``: lista de (prefijo, árbol) cuyas métricas se copian al árbol base
    en nodos coincidentes (marca → superart → artículo).
    """
    out = [dict(n) for n in base_arbol]
    for _prefix, arbol in extra_arboles:
        super_map = {}
        art_map = {}
        for marca in arbol or []:
            mk = _node_key_marca(marca)
            for sa in marca.get("children") or []:
                sk = (mk, _node_key_super(sa))
                super_map[sk] = sa.get("metrics") or {}
                for art in sa.get("children") or []:
                    ak = (sk, _node_key_art(art))
                    art_map[ak] = art.get("metrics") or {}

        for marca in out:
            mk = _node_key_marca(marca)
            for sa in marca.get("children") or []:
                sk = (mk, _node_key_super(sa))
                extra_m = super_map.get(sk)
                if extra_m:
                    sa.setdefault("metrics", {})
                    sa["metrics"].update(extra_m)
                for art in sa.get("children") or []:
                    ak = (sk, _node_key_art(art))
                    extra_a = art_map.get(ak)
                    if extra_a:
                        art.setdefault("metrics", {})
                        art["metrics"].update(extra_a)
    return out


def add_docenas_from_pares_arbol(arbol: Sequence[Dict[str, Any]], meses: Sequence[str], mes_labels: Dict[str, str]) -> None:
    """Deriva métricas Docenas_* a partir de Pares_* (/12) en el árbol in-place."""
    from reports.services.informe_marca_superart_periodo import empty_metric_map

    def walk(node: Dict[str, Any]) -> None:
        metrics = node.setdefault("metrics", {})
        docenas = empty_metric_map(meses, "Docenas")
        for key, val in list(metrics.items()):
            if key.startswith("Pares_"):
                doc_key = "Docenas_" + key[len("Pares_") :]
                try:
                    docenas[doc_key] = round(float(val or 0) / 12.0, 4)
                except (TypeError, ValueError):
                    docenas[doc_key] = 0.0
        metrics.update(docenas)
        for ch in node.get("children") or []:
            walk(ch)

    for marca in arbol or []:
        walk(marca)
