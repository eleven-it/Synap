"""Conexión de solo lectura a Azure SQL BEST."""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# Host/DB/user por defecto (dev). La contraseña SOLO vía BEST_AZURE_PASSWORD.
_DEFAULTS = {
    "SERVER": "m52q7iitok.database.windows.net",
    "DATABASE": "BEST",
    "USER": "interfase$bestsox",
    "PORT": "1433",
}


def best_connection_config() -> dict[str, str]:
    password = (os.environ.get("BEST_AZURE_PASSWORD") or "").strip()
    if not password:
        raise RuntimeError(
            "Falta BEST_AZURE_PASSWORD en el entorno. "
            "Configurá las credenciales Azure BEST en .env (no versionar secretos)."
        )
    return {
        "SERVER": os.environ.get("BEST_AZURE_SERVER", _DEFAULTS["SERVER"]),
        "DATABASE": os.environ.get("BEST_AZURE_DATABASE", _DEFAULTS["DATABASE"]),
        "USER": os.environ.get("BEST_AZURE_USER", _DEFAULTS["USER"]),
        "PASSWORD": password,
        "PORT": os.environ.get("BEST_AZURE_PORT", _DEFAULTS["PORT"]),
    }


def connect_best(*, timeout: int = 90):
    """Abre conexión pymssql a BEST. Lanza ImportError/OSError/Exception si falla."""
    try:
        import pymssql
    except ImportError as exc:
        raise ImportError(
            "Falta el driver pymssql en el entorno. Instalá pymssql para consultar Azure BEST."
        ) from exc

    cfg = best_connection_config()
    return pymssql.connect(
        server=cfg["SERVER"],
        port=int(cfg["PORT"]),
        database=cfg["DATABASE"],
        user=cfg["USER"],
        password=cfg["PASSWORD"],
        timeout=timeout,
    )


def fetch_dict(conn, sql: str, params: tuple[Any, ...] | None = None) -> list[dict]:
    cur = conn.cursor(as_dict=True)
    cur.execute(sql, params or ())
    return list(cur.fetchall())
