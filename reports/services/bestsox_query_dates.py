# -*- coding: utf-8 -*-
"""Fechas de filtro para consultas BestSox (objetos date, no strings ISO)."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from core.utils.administranet_types import to_date_or_none


def parse_filter_date(value: Any) -> Optional[date]:
    """
    Convierte filtros de informe a ``datetime.date``.

    ``to_date_or_none`` devuelve str YYYY-MM-DD (contrato MySQL); las consultas
    BestSox necesitan ``date`` para ``timedelta`` / comparaciones tipadas.
    """
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    iso = to_date_or_none(value)
    if not iso:
        return None
    return date.fromisoformat(iso)
