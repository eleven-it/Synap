"""Resolución de política de crédito por cliente y canal."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from core.utils.administranet_types import to_int_or_none

CANAL_PED = "PED"
CANAL_PRE = "PRE"


@dataclass(frozen=True)
class PoliticaCredito:
    id: int
    id_cliente: int
    canal: str
    limite_dias: Optional[int]
    capa_cxc: bool
    capa_ped_abiertos: bool
    capa_remitos_nf: bool
    capa_cheques: bool
    capa_doc_actual: bool
    incluir_mora: bool


def _capa_on(val: Any) -> bool:
    return str(val or "").strip().lower() in ("si", "sí", "1", "true")


def _valor(row: Any, key: str, idx: int) -> Any:
    if row is None:
        return None
    if isinstance(row, dict):
        return row.get(key)
    try:
        return row[idx]
    except (IndexError, KeyError, TypeError):
        return None


def _politica_desde_row(row: Any) -> PoliticaCredito:
    return PoliticaCredito(
        id=int(to_int_or_none(_valor(row, "id", 0)) or 0),
        id_cliente=int(to_int_or_none(_valor(row, "id_cliente", 1)) or 0),
        canal=str(_valor(row, "canal", 2) or CANAL_PED).upper(),
        limite_dias=to_int_or_none(_valor(row, "limite_dias", 3)),
        capa_cxc=_capa_on(_valor(row, "capa_cxc", 4)),
        capa_ped_abiertos=_capa_on(_valor(row, "capa_ped_abiertos", 5)),
        capa_remitos_nf=_capa_on(_valor(row, "capa_remitos_nf", 6)),
        capa_cheques=_capa_on(_valor(row, "capa_cheques", 7)),
        capa_doc_actual=_capa_on(_valor(row, "capa_doc_actual", 8)),
        incluir_mora=_capa_on(_valor(row, "incluir_mora", 9)),
    )


def politica_default_empresa(canal: str) -> PoliticaCredito:
    """Defaults alineados al DDL ``ecom_credito_politica``."""
    return PoliticaCredito(
        id=0,
        id_cliente=0,
        canal=(canal or CANAL_PED).upper(),
        limite_dias=None,
        capa_cxc=True,
        capa_ped_abiertos=True,
        capa_remitos_nf=False,
        capa_cheques=False,
        capa_doc_actual=True,
        incluir_mora=True,
    )


def resolver_politica(cur: Any, id_cliente: int, canal: str) -> PoliticaCredito:
    """
    Busca política específica del cliente/canal; si no existe, la default empresa (id_cliente=0).
    """
    canal_norm = (canal or CANAL_PED).upper()
    idc = int(to_int_or_none(id_cliente) or 0)
    sql = """
        SELECT id, id_cliente, canal, limite_dias,
               capa_cxc, capa_ped_abiertos, capa_remitos_nf, capa_cheques, capa_doc_actual,
               incluir_mora
        FROM ecom_credito_politica
        WHERE id_cliente = %s AND canal = %s AND activo = 'Si'
        ORDER BY id DESC
        LIMIT 1
    """
    for id_buscar in (idc, 0):
        if id_buscar == 0 and idc == 0:
            continue
        cur.execute(sql, [id_buscar, canal_norm])
        row = cur.fetchone()
        if row:
            return _politica_desde_row(row)
    return politica_default_empresa(canal_norm)
