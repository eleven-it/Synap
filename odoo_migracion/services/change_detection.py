"""Detección de cambios para sync incremental."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


def row_payload_hash(row: Mapping[str, Any]) -> str:
    """Hash estable del payload de origen (excluye claves volátiles)."""
    skip = frozenset({"fecha_mod", "fecha_alta", "updated_at"})
    normalized = {k: row[k] for k in sorted(row.keys()) if k not in skip}
    raw = json.dumps(normalized, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]
