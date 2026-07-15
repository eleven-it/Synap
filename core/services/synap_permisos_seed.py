"""
Semilla idempotente del catálogo de permisos Synap (tabla ``synap_permiso``).

Fuente: ``core.constantes_permisos.PERMISOS_POR_MODULO`` + comodines
``MODULOS_CON_COMODIN``. NO escribe en ``permiso_sistema`` (tabla VB6).

Además expone ``asegurar_synap_schema_si_procede`` para garantizar (con cache
por empresa) que el DDL ``synap_*`` y el catálogo existen tras el login, sin
inyectar nada en las tablas compartidas con AdministraNET.
"""
import logging
from typing import Any, Dict, List, Tuple

from django.conf import settings
from django.core.cache import cache

from core.constantes_permisos import MODULOS_CON_COMODIN, PERMISOS_POR_MODULO

logger = logging.getLogger(__name__)

CACHE_KEY_PREFIX = "synap_schema_ensure:"


def _filas_catalogo() -> List[Tuple[str, str, str]]:
    """Construye ``(key_permiso, modulo, nombre)`` para el catálogo Synap."""
    filas: List[Tuple[str, str, str]] = []
    for modulo, permisos in PERMISOS_POR_MODULO.items():
        for codigo, nombre in permisos:
            filas.append((codigo.strip(), (modulo or "-").strip()[:64], (nombre or "-").strip()[:255]))
    for modulo in MODULOS_CON_COMODIN:
        filas.append((f"{modulo}.*", modulo[:64], f"Acceso total a {modulo}"[:255]))
    return filas


def seed_synap_permiso_catalog(conn) -> Dict[str, Any]:
    """
    Inserta/actualiza el catálogo de permisos en ``synap_permiso`` de forma idempotente.

    Usa ``INSERT ... ON DUPLICATE KEY UPDATE`` sobre la clave única ``key_permiso``.
    Devuelve un dict con el conteo procesado. No hace commit (lo gestiona el proveedor).
    """
    filas = _filas_catalogo()
    if not filas:
        return {"success": True, "procesados": 0, "message": "Catálogo Synap vacío"}

    cursor = conn.cursor()
    try:
        cursor.executemany(
            """
            INSERT INTO synap_permiso (key_permiso, modulo, nombre, activo)
            VALUES (%s, %s, %s, 1)
            ON DUPLICATE KEY UPDATE
                modulo = VALUES(modulo),
                nombre = VALUES(nombre),
                activo = 1
            """,
            filas,
        )
        return {
            "success": True,
            "procesados": len(filas),
            "message": f"Catálogo Synap sembrado ({len(filas)} permisos)",
        }
    finally:
        cursor.close()


def asegurar_synap_schema_si_procede(base_empresa: str) -> None:
    """
    Garantiza (con cache por empresa) que existen las tablas ``synap_*`` y el
    catálogo de permisos en la base de la empresa.

    Reemplazo directo de ``asegurar_permisos_synap_si_procede`` que NO inyecta en
    ``permiso_sistema``. Cualquier excepción se registra y se ignora (no rompe login).

    Se controla con ``SYNAP_AUTO_ENSURE_SCHEMA`` (default True).
    """
    if not getattr(settings, "SYNAP_AUTO_ENSURE_SCHEMA", True):
        return
    if not (base_empresa or "").strip():
        return

    cache_key = f"{CACHE_KEY_PREFIX}{base_empresa.strip()}"
    ttl = getattr(settings, "SYNAP_AUTO_ENSURE_SCHEMA_TTL", 86400)  # 24h

    try:
        if cache.get(cache_key):
            return
    except Exception as e:  # pragma: no cover - cache opcional
        logger.debug("Cache no disponible para asegurar schema Synap (%s): %s", base_empresa, e)

    try:
        # Import diferido para evitar ciclo con catalog.py.
        from core.mysql_pool import get_connection
        from core.services.legacy_mysql_schema.catalog import run_synap_permisos_tables_mysql

        with get_connection(base_empresa) as conn:
            result = run_synap_permisos_tables_mysql(conn)

        try:
            cache.set(cache_key, True, timeout=ttl)
        except Exception:
            pass

        if not result.get("success"):
            logger.warning(
                "Esquema Synap no aplicado por completo en %s: %s",
                base_empresa, result.get("message"),
            )
    except Exception as e:
        logger.warning(
            "No se pudo asegurar esquema Synap para %s (login no afectado): %s",
            base_empresa, e, exc_info=True,
        )
