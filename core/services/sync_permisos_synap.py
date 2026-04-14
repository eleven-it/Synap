"""
Sincronización automática de permisos Synap → permiso_sistema (AdministraNET).
Usado tras login para asegurar que la base de la empresa tenga los key_permiso que Synap usa.

Optimización: usa 1 conexión, 1 SELECT bulk y 1 INSERT batch en vez de N queries.
"""
import logging
from typing import List, Dict, Tuple

import MySQLdb

from django.conf import settings
from django.core.cache import cache

from core.constantes_permisos import PERMISOS_POR_MODULO

logger = logging.getLogger(__name__)

CACHE_KEY_PREFIX = "synap_perm_sync:"
MODULOS_CON_COMODIN = ("reports", "stock", "self_checkout", "logistica")


def _lista_permisos_synap(grupo_permiso: str = "Synap") -> List[Dict]:
    """Construye la lista de permisos a sincronizar."""
    permisos = []
    for modulo, lista_permisos in PERMISOS_POR_MODULO.items():
        for codigo, nombre in lista_permisos:
            permisos.append({
                "key_permiso": codigo,
                "nombre_permiso": nombre,
                "grupo_permiso": grupo_permiso,
                "tipo_permiso": "Si-No",
                "default_permiso": "No",
                "detalle_permiso": f"Permiso de Synap - Módulo {modulo}",
                "detalle_valor_permiso": "Si-No",
            })
    for modulo in MODULOS_CON_COMODIN:
        permisos.append({
            "key_permiso": f"{modulo}.*",
            "nombre_permiso": f"Acceso total a {modulo}",
            "grupo_permiso": grupo_permiso,
            "tipo_permiso": "Si-No",
            "default_permiso": "No",
            "detalle_permiso": f"Permiso comodín para acceso total al módulo {modulo}",
            "detalle_valor_permiso": "Si-No",
        })
    return permisos


def _get_mysql_connection(base_empresa: str):
    """Abre una conexión directa a la base MySQL de la empresa."""
    mysql_config = settings.DATABASES['mysql']
    return MySQLdb.connect(
        host=mysql_config['HOST'],
        port=int(mysql_config['PORT']),
        user=mysql_config['USER'],
        passwd=mysql_config['PASSWORD'],
        db=base_empresa,
        charset='latin1',
    )


def sincronizar_permisos_synap_para_empresa(
    base_empresa: str, grupo_permiso: str = "Synap"
) -> Tuple[int, int]:
    """
    Sincroniza los permisos de Synap en permiso_sistema de una empresa.
    Usa 1 conexión + 1 SELECT bulk + 1 INSERT batch (idempotente).
    Devuelve (creados, existentes).
    """
    permisos_synap = _lista_permisos_synap(grupo_permiso)
    if not permisos_synap:
        return 0, 0

    conn = _get_mysql_connection(base_empresa)
    try:
        cursor = conn.cursor()

        cursor.execute("SELECT key_permiso FROM permiso_sistema")
        keys_existentes = {row[0] for row in cursor.fetchall()}

        por_insertar = [
            p for p in permisos_synap if p["key_permiso"] not in keys_existentes
        ]
        existentes = len(permisos_synap) - len(por_insertar)

        if por_insertar:
            cursor.executemany(
                """INSERT INTO permiso_sistema
                   (key_permiso, nombre_permiso, detalle_permiso,
                    grupo_permiso, tipo_permiso, default_permiso, detalle_valor_permiso)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                [
                    (
                        p["key_permiso"].strip(),
                        p["nombre_permiso"].strip(),
                        p["detalle_permiso"].strip(),
                        p["grupo_permiso"].strip(),
                        p["tipo_permiso"].strip(),
                        p["default_permiso"].strip(),
                        p["detalle_valor_permiso"].strip(),
                    )
                    for p in por_insertar
                ],
            )
            conn.commit()

        cursor.close()
        return len(por_insertar), existentes
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def asegurar_permisos_synap_si_procede(base_empresa: str) -> None:
    """
    Ejecuta la sincronización de permisos Synap para la empresa solo si:
    - Está habilitado (SYNAP_AUTO_SYNC_PERMISSIONS),
    - Y no se ha sincronizado recientemente (cache por empresa con TTL).
    No debe romper el flujo: cualquier excepción se registra y se ignora.
    Punto de uso recomendado: justo después de un login exitoso.
    """
    if not getattr(settings, "SYNAP_AUTO_SYNC_PERMISSIONS", True):
        return
    if not (base_empresa or "").strip():
        return

    cache_key = f"{CACHE_KEY_PREFIX}{base_empresa.strip()}"
    ttl = getattr(settings, "SYNAP_AUTO_SYNC_PERMISSIONS_TTL", 86400)  # 24h

    try:
        if cache.get(cache_key):
            logger.debug("Permisos Synap ya sincronizados recientemente para %s (cache)", base_empresa)
            return
    except Exception as e:
        logger.debug("Cache no disponible para sync permisos (%s), se ejecutará sync: %s", base_empresa, e)

    try:
        creados, existentes = sincronizar_permisos_synap_para_empresa(base_empresa)
        try:
            cache.set(cache_key, True, timeout=ttl)
        except Exception:
            pass
        if creados > 0:
            logger.info(
                "Permisos Synap sincronizados para %s: %d creados, %d existentes",
                base_empresa, creados, existentes,
            )
    except Exception as e:
        logger.warning(
            "No se pudo sincronizar permisos Synap para %s (login no afectado): %s",
            base_empresa, e, exc_info=True,
        )
