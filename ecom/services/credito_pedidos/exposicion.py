"""Cálculo de exposición Balance+All por capas configurables."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict

from core.utils.administranet_types import to_decimal_or_none

from ecom.services.credito_pedidos.politica import PoliticaCredito

CAPA_CXC = "cxc"
CAPA_PED_ABIERTOS = "ped_abiertos"
CAPA_REMITOS_NF = "remitos_nf"
CAPA_CHEQUES = "cheques"
CAPA_DOC_ACTUAL = "doc_actual"


@dataclass(frozen=True)
class ResultadoExposicion:
    capas: Dict[str, Decimal]
    total: Decimal


def _dec(v: Any, default: str = "0") -> Decimal:
    r = to_decimal_or_none(v)
    return r if r is not None else Decimal(default)


def _valor(row: Any, key: str, idx: int = 0) -> Any:
    if row is None:
        return None
    if isinstance(row, dict):
        return row.get(key)
    try:
        return row[idx]
    except (IndexError, KeyError, TypeError):
        return None


def _capa_cxc(cur: Any, id_cliente: int) -> Decimal:
    cur.execute(
        "SELECT COALESCE(saldo, 0) AS monto FROM cliente WHERE Codigo = %s LIMIT 1",
        [id_cliente],
    )
    row = cur.fetchone()
    return _dec(_valor(row, "monto", 0))


def _capa_ped_abiertos(cur: Any, id_cliente: int) -> Decimal:
    cur.execute(
        """
        SELECT COALESCE(SUM(comp_ped.ImporteVenta), 0) AS monto
        FROM comp_ped
        WHERE comp_ped.Codigo = %s
          AND comp_ped.TipoComprobante = 'PED'
          AND comp_ped.Anulado = 'No'
          AND comp_ped.Estado = 'Pendiente'
        """,
        [id_cliente],
    )
    row = cur.fetchone()
    return _dec(_valor(row, "monto", 0))


def _capa_remitos_nf(cur: Any, id_cliente: int) -> Decimal:
    cur.execute(
        """
        SELECT COALESCE(SUM(comp_ped.ImporteVenta), 0) AS monto
        FROM comp_ped
        WHERE comp_ped.Codigo = %s
          AND comp_ped.TipoComprobante = 'REM'
          AND comp_ped.Anulado = 'No'
          AND comp_ped.Estado = 'Pendiente'
        """,
        [id_cliente],
    )
    row = cur.fetchone()
    return _dec(_valor(row, "monto", 0))


def _capa_cheques(cur: Any, id_cliente: int) -> Decimal:
    cur.execute(
        """
        SELECT
            COALESCE(cliente.credito_cheque, 0)
            + COALESCE(cliente.credito_cheque_tercero, 0) AS monto
        FROM cliente
        WHERE cliente.Codigo = %s
        LIMIT 1
        """,
        [id_cliente],
    )
    row = cur.fetchone()
    return _dec(_valor(row, "monto", 0))


def calcular_exposicion(
    cur: Any,
    id_cliente: int,
    politica: PoliticaCredito,
    *,
    doc_actual: Decimal = Decimal("0"),
) -> ResultadoExposicion:
    """Suma solo las capas ON de la política."""
    capas: Dict[str, Decimal] = {}
    if politica.capa_cxc:
        capas[CAPA_CXC] = _capa_cxc(cur, id_cliente)
    if politica.capa_ped_abiertos:
        capas[CAPA_PED_ABIERTOS] = _capa_ped_abiertos(cur, id_cliente)
    if politica.capa_remitos_nf:
        capas[CAPA_REMITOS_NF] = _capa_remitos_nf(cur, id_cliente)
    if politica.capa_cheques:
        capas[CAPA_CHEQUES] = _capa_cheques(cur, id_cliente)
    if politica.capa_doc_actual and doc_actual > 0:
        capas[CAPA_DOC_ACTUAL] = _dec(doc_actual)

    total = sum(capas.values(), Decimal("0"))
    return ResultadoExposicion(capas=capas, total=total)
