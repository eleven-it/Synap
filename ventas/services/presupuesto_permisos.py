# -*- coding: utf-8 -*-
"""Flags de `permisos_sistema` relevantes para UI y validación del Presupuesto (PRE)."""

from __future__ import annotations

from typing import Any, Dict, Optional

from core.utils.administranet_types import to_decimal_or_none


def _es_si(val: Any) -> bool:
    if val is None:
        return False
    s = str(val).strip().lower()
    return s in ("si", "sí", "1", "yes", "true")


def contexto_ui_presupuesto(raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Convierte la fila `permisos_sistema` del puesto en flags tipados para plantillas.
    Si no hay fila, los booleanos quedan en False salvo defaults seguros documentados.
    """
    r = raw or {}
    lim_pie = to_decimal_or_none(r.get("lim_desc_pie"))
    lim_ren = to_decimal_or_none(r.get("lim_desc_renglon"))

    return {
        "raw": r,
        "mod_item_pre_ped_si": _es_si(r.get("mod_item_pre_ped")),
        "plantillas_si": _es_si(r.get("plantillas")),
        "mod_descuento_pie_si": _es_si(r.get("mod_descuento_pie")),
        "mod_descuento_renglon_si": _es_si(r.get("mod_descuento_renglon")),
        "mod_lista_de_precio_si": _es_si(r.get("mod_lista_de_precio")),
        "cambia_cv_si": _es_si(r.get("cambia_cv")),
        "utiliza_lista_oficial_si": _es_si(r.get("utiliza_lista_oficial")),
        "factura_importe_cero_si": _es_si(r.get("factura_importe_cero")),
        "modifica_vendedor_si": _es_si(r.get("modifica_vendedor")),
        "obliga_cambvendedor_si": _es_si(r.get("obliga_cambvendedor")),
        "modifica_comp_talonario_si": _es_si(r.get("modifica_comp_talonario")),
        "acceso_comp_ventas_talonario_si": _es_si(r.get("acceso_comp_ventas_talonario")),
        "carga_comp_ped_si": _es_si(r.get("carga_comp_ped")),
        "lim_desc_pie": lim_pie,
        "lim_desc_renglon": lim_ren,
        "mod_precio_fact_si": _es_si(r.get("Mod_Precio_Fact")),
    }
