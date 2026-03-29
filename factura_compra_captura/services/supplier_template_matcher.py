"""
Coincidencia de plantilla por CUIT / reglas del registry (Stage 5).
"""

from __future__ import annotations

import re
from typing import Any

from factura_compra_captura.services.supplier_template_registry import SUPPLIER_TEMPLATES


def _cuit_solo_digitos(cuit: str | None) -> str:
    if not cuit:
        return ""
    return re.sub(r"\D", "", str(cuit).strip())


def match_supplier_template(
    campos_cabecera: dict[str, Any],
    header: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Devuelve ``template_id`` (o ``None``), ``matched_by`` y ``confidence`` 0..1.
    """
    _ = header
    nd = _cuit_solo_digitos((campos_cabecera or {}).get("proveedor_cuit_texto"))
    best_id: str | None = None
    best_pri = -1
    for tid, rules in SUPPLIER_TEMPLATES.items():
        if tid == "generic":
            continue
        pri = int(rules.get("priority") or 0)
        mcd = (rules.get("match_cuit_digits") or "").strip()
        if len(mcd) == 11 and nd == mcd and pri > best_pri:
            best_id = tid
            best_pri = pri
    if best_id:
        return {
            "template_id": best_id,
            "matched_by": "cuit_legacy",
            "confidence": min(1.0, 0.88 + 0.04 * (best_pri / 100.0)),
        }
    return {
        "template_id": None,
        "matched_by": None,
        "confidence": 0.0,
    }
