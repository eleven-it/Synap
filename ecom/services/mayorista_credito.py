"""
Autorización de comprobante mayorista por límite de crédito (Fase P2).

Paridad legacy (`alta_pedido_confirmado.php` + `seleccionar-cliente.php`):
- Se calcula el atraso máximo del cliente (comprobante impago más antiguo en `cuentacliente`).
- Si el atraso supera `cliente.credito_limite_dias` (> 0) → 'No Autorizado'.
- Un alta originada por el propio cliente (autogestión) queda siempre 'No Autorizado'.
- El exceso NO bloquea el alta: sólo determina `comp_ped.autorizacion_sistema`.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional, Tuple

AUTORIZADO = "Autorizado"
NO_AUTORIZADO = "No Autorizado"

# Comprobantes de deuda considerados para el atraso (paridad legacy)
_TIPOS_DEUDA = ("FA", "FB", "FC", "FE", "FM", "NDA", "NDC", "NDE", "NDM", "NDB")

_SQL_ATRASO = """
    SELECT MIN(cuentacliente.Fecha) AS ultimaf
    FROM cuentacliente
    WHERE cuentacliente.TipoComprobante IN (%s)
      AND cuentacliente.Estado = 'N/Canc'
      AND cuentacliente.Anulado = 'No'
      AND cuentacliente.Codigo = %%s
""" % (",".join(["%s"] * len(_TIPOS_DEUDA)))


def dias_atraso(cur: Any, codigo_cliente: int) -> Optional[int]:
    """Días desde el comprobante impago más antiguo del cliente; None si no tiene deuda."""
    cur.execute(_SQL_ATRASO, [*_TIPOS_DEUDA, codigo_cliente])
    row = cur.fetchone()
    ultimaf = _valor(row, "ultimaf", 0)
    if not ultimaf or not str(ultimaf).strip():
        return None
    try:
        if isinstance(ultimaf, datetime):
            d2 = ultimaf.date()
        elif isinstance(ultimaf, date):
            d2 = ultimaf
        else:
            d2 = datetime.strptime(str(ultimaf)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None
    return abs((date.today() - d2).days)


def evaluar_autorizacion(
    cur: Any,
    codigo_cliente: int,
    credito_limite_dias: int,
    *,
    es_cliente: bool,
) -> Tuple[str, int]:
    """
    Devuelve (autorizacion, dias_exceso). No bloquea: sólo etiqueta el comprobante.
    """
    atraso = dias_atraso(cur, codigo_cliente)
    limite = int(credito_limite_dias or 0)
    exceso = bool(limite > 0 and atraso is not None and atraso > limite)

    if es_cliente or exceso:
        return NO_AUTORIZADO, (atraso if (exceso and atraso is not None) else 0)
    return AUTORIZADO, 0


def _valor(row: Any, key: str, idx: int) -> Any:
    if row is None:
        return None
    if isinstance(row, dict):
        return row.get(key)
    try:
        return row[idx]
    except (IndexError, KeyError, TypeError):
        return None
