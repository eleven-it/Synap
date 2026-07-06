"""Base para extractores MySQL (solo lectura)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from core.mysql_pool import get_connection


def rows_as_dicts(cursor) -> List[Dict[str, Any]]:
    cols = [d[0] for d in cursor.description] if cursor.description else []
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


class BaseExtractor(ABC):
    entity_type: str = ""

    def __init__(self, base_empresa: str):
        self.base_empresa = (base_empresa or "").strip()

    @abstractmethod
    def count(self) -> int:
        ...

    @abstractmethod
    def extract(self, *, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        ...

    def _execute(self, sql: str, params: list | tuple = ()) -> List[Dict[str, Any]]:
        with get_connection(self.base_empresa) as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            return rows_as_dicts(cursor)

    def _scalar(self, sql: str, params: list | tuple = ()) -> int:
        with get_connection(self.base_empresa) as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            row = cursor.fetchone()
            return int(row[0] or 0) if row else 0
