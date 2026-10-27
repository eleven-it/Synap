# -*- coding: utf-8 -*-
"""Stock producción del informe PPP: cantidad armable desde semi (componentes Fabricado)."""
from __future__ import annotations

import logging
from typing import Dict, List, Sequence, Tuple

from mpr.services import get_deposito_semi_elaborado_mpr

from reports.services.pedidos_pendientes_produccion_calcs import (
    compute_stock_produccion_armable,
    es_tipo_art_fab_fabricado,
    formula_cantidad_por_unidad_terminado,
)

logger = logging.getLogger(__name__)


def fetch_stock_produccion_armable_map(
    cursor,
    base_empresa: str,
    id_arts: Sequence[int],
) -> Dict[int, float]:
    """
    Por artículo terminado (ensamblado=Si, id_en_abm): mínimo armable según saldo semi
    de componentes Fabricado en la receta vigente. Sin receta / sin Fabricados → 0.
    """
    ids = [int(x) for x in id_arts if x is not None]
    resultado: Dict[int, float] = {i: 0.0 for i in ids}
    if not ids:
        return resultado

    dep_semi = get_deposito_semi_elaborado_mpr(base_empresa)
    if not dep_semi:
        return resultado

    ph = ",".join(["%s"] * len(ids))
    cursor.execute(
        f"""
        SELECT IDArt, id_en_abm
        FROM articulo
        WHERE IDArt IN ({ph})
          AND id_en_abm IS NOT NULL AND id_en_abm <> 0
          AND COALESCE(ensamblado, 'No') = 'Si'
        """,
        ids,
    )
    pack_abm: Dict[int, int] = {}
    abm_ids: List[int] = []
    for row in cursor.fetchall() or []:
        try:
            id_a = int(row[0])
            id_abm = int(row[1])
        except (TypeError, ValueError, IndexError):
            continue
        pack_abm[id_a] = id_abm
        abm_ids.append(id_abm)

    if not abm_ids:
        return resultado

    abm_ids = list(dict.fromkeys(abm_ids))
    ph_abm = ",".join(["%s"] * len(abm_ids))
    cursor.execute(
        f"""
        SELECT
            f.id_en_abm,
            f.id_articulo,
            COALESCE(f.cantidad_articulo, 0) AS cantidad_articulo,
            COALESCE(f.tipo_unidad, '') AS tipo_unidad,
            f.cantidad_unidad_display,
            f.cantidad_dividir,
            COALESCE(a.tipo_art_fab, '') AS tipo_art_fab
        FROM en_abm_formula f
        INNER JOIN articulo a ON a.IDArt = f.id_articulo
        WHERE f.id_en_abm IN ({ph_abm})
          AND COALESCE(f.anulado, 'No') = 'No'
        """,
        abm_ids,
    )
    lineas_por_abm: Dict[int, List[Tuple[int, float]]] = {}
    comp_ids: List[int] = []
    for row in cursor.fetchall() or []:
        try:
            id_abm = int(row[0])
            id_comp = int(row[1])
            tipo_fab = row[6]
        except (TypeError, ValueError, IndexError):
            continue
        if not es_tipo_art_fab_fabricado(tipo_fab):
            continue
        qty_u = formula_cantidad_por_unidad_terminado(
            row[2],
            row[3],
            row[4],
            row[5],
        )
        if qty_u <= 0:
            continue
        lineas_por_abm.setdefault(id_abm, []).append((id_comp, qty_u))
        comp_ids.append(id_comp)

    if not comp_ids:
        return resultado

    comp_ids = list(dict.fromkeys(comp_ids))
    ph_comp = ",".join(["%s"] * len(comp_ids))
    cursor.execute(
        f"""
        SELECT sd.id_articulo, COALESCE(sd.saldo, 0)
        FROM stock_deposito sd
        INNER JOIN deposito d ON d.CodDeposito = sd.id_deposito
          AND COALESCE(d.anulado, 'No') = 'No'
          AND COALESCE(d.suma_stock, 'Si') = 'Si'
        WHERE sd.id_deposito = %s
          AND sd.id_articulo IN ({ph_comp})
        """,
        [int(dep_semi)] + comp_ids,
    )
    saldos_semi: Dict[int, float] = {}
    for sid_art, saldo in cursor.fetchall() or []:
        try:
            saldos_semi[int(sid_art)] = float(saldo or 0)
        except (TypeError, ValueError):
            continue

    for id_pack, id_abm in pack_abm.items():
        lineas = lineas_por_abm.get(id_abm) or []
        if not lineas:
            continue
        pares = [
            (saldos_semi.get(id_c, 0.0), qty_u)
            for id_c, qty_u in lineas
        ]
        resultado[id_pack] = compute_stock_produccion_armable(pares)

    return resultado
