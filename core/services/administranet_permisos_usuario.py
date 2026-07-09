"""
Permisos de usuario según AdministraNET (MySQL).

Fachada de la fuente de verdad de permisos. Según ``settings.SYNAP_PERMISOS_SOURCE``
resuelve los permisos desde las tablas propias de Synap (``synap_*``) o desde las
tablas legacy compartidas con VB6 (``permiso_sistema`` + ``permiso_sistema_puesto``),
o ambas (modo ``dual`` para validar paridad).

Siempre suma los permisos complementarios de la tabla ``permisos`` (Clavemenu VB6),
que es lectura genuinamente legacy y no se migra.

Usado por middleware (request.user.get_permisos_totales) y self_checkout (has_permission).
"""
import logging
from typing import Optional, Set

from django.conf import settings

from core.services.synap_permisos import (
    get_permisos_complementarios_legacy,
    get_permisos_desde_synap_store,
    get_permisos_legacy_synap,
    puesto_tiene_mapeo_synap,
)

logger = logging.getLogger(__name__)

# Permisos Reports que se agregan a usuario/puesto "Supervisor" (nombre o cod_usuario)
REPORTS_PERMISSIONS_FOR_SUPERVISOR = {
    "reports.ver",
    "reports.*",
    "reports.view_operational",
    "reports.view_managerial",
    "reports.dashboard",
    "reports.exportar",
    "reports.builder",
    "reports.programar",
}


def _resolver_permisos_base(base_empresa: str, id_puesto: Optional[int]) -> Set[str]:
    """
    Resuelve el set base de permisos del puesto según ``settings.SYNAP_PERMISOS_SOURCE``:
    - ``legacy`` (default): permiso_sistema + permiso_sistema_puesto.
    - ``synap``: tablas synap_*; si el puesto no tiene mapeo, fallback a legacy.
    - ``dual``: unión de ambas; registra advertencia si difieren (validación de paridad).
    NO incluye complementarios (Clavemenu) ni permisos de supervisor: eso lo hace la fachada.
    """
    source = str(getattr(settings, "SYNAP_PERMISOS_SOURCE", "legacy") or "legacy").strip().lower()

    if source == "synap":
        permisos = get_permisos_desde_synap_store(base_empresa, id_puesto)
        if not permisos and not puesto_tiene_mapeo_synap(base_empresa, id_puesto):
            logger.info(
                "SYNAP_PERMISOS_SOURCE=synap: puesto %s sin mapeo en synap_*; fallback a legacy.",
                id_puesto,
            )
            return get_permisos_legacy_synap(base_empresa, id_puesto)
        return permisos

    if source == "dual":
        permisos_synap = get_permisos_desde_synap_store(base_empresa, id_puesto)
        permisos_legacy = get_permisos_legacy_synap(base_empresa, id_puesto)
        if permisos_synap != permisos_legacy:
            solo_synap = permisos_synap - permisos_legacy
            solo_legacy = permisos_legacy - permisos_synap
            logger.warning(
                "SYNAP_PERMISOS_SOURCE=dual: divergencia de permisos puesto %s (%s). "
                "solo_synap=%s solo_legacy=%s",
                id_puesto, base_empresa, sorted(solo_synap), sorted(solo_legacy),
            )
        return permisos_synap | permisos_legacy

    # 'legacy' (default) y cualquier valor desconocido
    return get_permisos_legacy_synap(base_empresa, id_puesto)


def get_permisos_totales_administranet(
    base_empresa: str,
    id_puesto: Optional[int],
    cod_usuario: Optional[str] = None,
    nombre_puesto: Optional[str] = None,
) -> Set[str]:
    """
    Obtiene el set de key_permiso efectivos del puesto/usuario.

    Reglas AdministraNET (invariantes en todas las fuentes):
    - Usuario con cod_usuario == 'supervisor' tiene todos los permisos ("*").
    - Puesto/usuario con nombre_puesto == 'Supervisor' o cod_usuario == 'supervisor'
      recibe además los permisos de Reports (reports.ver, reports.*, etc.).
    - Se suman siempre los permisos complementarios de la tabla ``permisos`` (Clavemenu VB6).

    El set base (permisos por puesto) proviene de ``synap_*`` o legacy según
    ``settings.SYNAP_PERMISOS_SOURCE`` (ver ``_resolver_permisos_base``).
    """
    cod_usuario_lower = (cod_usuario or "").strip().lower()
    nombre_puesto_lower = (nombre_puesto or "").strip().lower()

    if cod_usuario_lower == "supervisor":
        return {"*"}

    permisos: Set[str] = set()

    if base_empresa and id_puesto:
        permisos |= _resolver_permisos_base(base_empresa, id_puesto)
        # Complementarios legacy (Clavemenu VB6): siempre se suman.
        permisos |= get_permisos_complementarios_legacy(base_empresa, id_puesto)

    if cod_usuario_lower == "supervisor" or nombre_puesto_lower == "supervisor":
        permisos.update(REPORTS_PERMISSIONS_FOR_SUPERVISOR)
        logger.debug(
            "Permisos Reports agregados para cod_usuario=%s nombre_puesto=%s",
            cod_usuario_lower,
            nombre_puesto_lower,
        )

    return permisos


def tiene_permiso_administranet(
    base_empresa: str,
    id_puesto: Optional[int],
    codigo: str,
    cod_usuario: Optional[str] = None,
    nombre_puesto: Optional[str] = None,
) -> bool:
    """
    Verifica si el puesto/usuario tiene el permiso (o wildcard).
    codigo puede ser un key_permiso (ej: 'reports.ver') o se acepta 'modulo.*'.
    """
    permisos = get_permisos_totales_administranet(
        base_empresa, id_puesto, cod_usuario=cod_usuario, nombre_puesto=nombre_puesto
    )
    if "*" in permisos:
        return True
    if codigo in permisos:
        return True
    for perm in permisos:
        if perm.endswith(".*"):
            modulo = perm[:-2]
            if codigo.startswith(modulo + "."):
                return True
            if codigo.startswith(modulo + "_"):
                return True
    return False
