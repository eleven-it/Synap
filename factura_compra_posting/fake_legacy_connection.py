"""
Conexión simulada para tests UT-ADP-* (posting_tests.md §4).
No usa drivers MySQL.
"""

from __future__ import annotations


class FakeLegacyConnection:
    def __init__(self) -> None:
        self.log: list[str] = []
        self.in_tx = False

    def begin(self) -> None:
        self.in_tx = True
        self.log.append("BEGIN")

    def commit(self) -> None:
        self.log.append("COMMIT")
        self.in_tx = False

    def rollback(self) -> None:
        self.log.append("ROLLBACK")
        self.in_tx = False

    def execute(self, sql: str, params: tuple | None = None) -> None:
        p = params or ()
        self.log.append(f"EXEC:{sql[:120]!r}|params={len(p)}")
