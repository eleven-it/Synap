"""
Sincronización automática de permisos Synap → permiso_sistema (AdministraNET).
Usado tras login para asegurar que la base de la empresa tenga los key_permiso que Synap usa.
"""
import logging
from typing import List, Dict, Tuple

from django.conf import settings
from django.core.cache import cache

from core.constantes_permisos import PERMISOS_POR_MODULO
from core.services.administranet_permiso_sistema import AdministraNETPermisoSistemaService

logger = logging.getLogger(__name__)

# Clave de cache por empresa; TTL en segundos (por defecto 24h)
CACHE_KEY_PREFIX = "synap_perm_sync:"
MODULOS_CON_COMODIN = ("reports", "stock")


def _lista_permisos_synap(grupo_permiso: str = "Synap") -> List[Dict]:
    """Construye la lista de permisos a sincronizar (misma lógica que sync_synap_permissions_to_adminet)."""
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


def sincronizar_permisos_synap_para_empresa(
    base_empresa: str, grupo_permiso: str = "Synap"
) -> Tuple[int, int]:
    """
    Sincroniza los permisos de Synap en la tabla permiso_sistema de una base de empresa.
    Solo crea los que no existan (idempotente).
    Devuelve (creados, existentes).
    """
    servicio = AdministraNETPermisoSistemaService()
    permisos_synap = _lista_permisos_synap(grupo_permiso)
    creados = 0
    existentes = 0
    for permiso_data in permisos_synap:
        try:
            lista = servicio.listar_permisos(
                base_empresa=base_empresa, busqueda=permiso_data["key_permiso"]
            )
            if any(p.get("key_permiso") == permiso_data["key_permiso"] for p in lista):
                existentes += 1
            else:
                nuevo_id = servicio.crear_permiso(base_empresa, permiso_data)
                if nuevo_id:
                    creados += 1
        except Exception as e:
            logger.warning(
                "Error al sincronizar permiso %s en %s: %s",
                permiso_data.get("key_permiso"),
                base_empresa,
                e,
            )
    return creados, existentes


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
