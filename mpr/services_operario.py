"""Servicios de mapeo operario<->usuario de login (MPR).

Orquesta el vínculo entre un legajo de operario (`sue_abm_empleado`) y un
usuario de login (`usuarios`), fuente de verdad en MySQL por empresa.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

import MySQLdb

from mpr.repositories import operario_linea as repo_ol
from mpr.repositories import operario_usuario as repo

logger = logging.getLogger(__name__)


def resolver_operario_por_usuario(base_empresa: str, id_usuario: int) -> Optional[int]:
    try:
        return repo.resolver_operario_por_usuario(base_empresa, id_usuario)
    except Exception as e:
        logger.debug("Resolver operario por usuario (%s): %s", base_empresa, e)
        return None


def listar_mapeos(base_empresa: str) -> List[Dict[str, Any]]:
    try:
        return repo.listar_mapeos(base_empresa)
    except Exception as e:
        logger.error("Error al listar mapeos operario-usuario en %s: %s", base_empresa, e, exc_info=True)
        return []


def listar_usuarios(base_empresa: str) -> List[Dict[str, Any]]:
    try:
        return repo.listar_usuarios(base_empresa)
    except Exception as e:
        logger.error("Error al listar usuarios en %s: %s", base_empresa, e, exc_info=True)
        return []


def map_operario_usuario(
    base_empresa: str, id_operario: int, id_usuario: int
) -> Tuple[bool, Optional[str]]:
    if not (base_empresa or "").strip():
        return False, "Empresa inválida."
    try:
        oid = int(id_operario)
        uid = int(id_usuario)
    except (TypeError, ValueError):
        return False, "Operario o usuario inválido."
    try:
        repo.map_operario_usuario(base_empresa, oid, uid)
        return True, None
    except MySQLdb.IntegrityError:
        return False, "Ese usuario ya está vinculado a otro operario."
    except Exception as e:
        logger.error(
            "Error al mapear operario %s con usuario %s en %s: %s",
            id_operario, id_usuario, base_empresa, e, exc_info=True,
        )
        return False, "Error al vincular operario y usuario."


def desmapear_usuario(base_empresa: str, id_usuario: int) -> Tuple[bool, Optional[str]]:
    if not (base_empresa or "").strip():
        return False, "Empresa inválida."
    try:
        uid = int(id_usuario)
    except (TypeError, ValueError):
        return False, "Usuario inválido."
    try:
        afectadas = repo.desmapear_usuario(base_empresa, uid)
        if not afectadas:
            return False, "Ese usuario no tenía un vínculo activo."
        return True, None
    except Exception as e:
        logger.error("Error al desvincular usuario %s en %s: %s", id_usuario, base_empresa, e, exc_info=True)
        return False, "Error al desvincular el usuario."


# --------------------------------------------------------------------------- #
# Línea habitual del operario (versionada) + resolución de línea
# --------------------------------------------------------------------------- #
def linea_habitual_operario(
    base_empresa: str, id_operario: int, fecha: Optional[date] = None
) -> Optional[int]:
    try:
        return repo_ol.linea_habitual_vigente(base_empresa, id_operario, fecha or date.today())
    except Exception as e:
        logger.debug("Línea habitual operario %s (%s): %s", id_operario, base_empresa, e)
        return None


def historico_linea_operario(base_empresa: str, id_operario: int) -> List[Dict[str, Any]]:
    try:
        return repo_ol.listar_historico(base_empresa, id_operario)
    except Exception as e:
        logger.error("Error histórico línea operario %s en %s: %s", id_operario, base_empresa, e, exc_info=True)
        return []


def set_linea_habitual_operario(
    base_empresa: str,
    id_operario: int,
    id_linea: int,
    desde: Optional[date] = None,
) -> Tuple[bool, Optional[str]]:
    from mpr.repositories import maquina_linea as repo_ml
    if not (base_empresa or "").strip():
        return False, "Empresa inválida."
    try:
        oid = int(id_operario)
        lid = int(id_linea)
    except (TypeError, ValueError):
        return False, "Operario o línea inválidos."
    linea = repo_ml.obtener_linea(base_empresa, lid)
    if not linea:
        return False, "Línea no encontrada."
    if not linea.get("activo"):
        return False, "No se puede asignar una línea inactiva."
    fecha = desde or date.today()
    actual = repo_ol.linea_habitual_vigente(base_empresa, oid, fecha)
    if actual == lid:
        return False, "El operario ya tiene esa línea como habitual."
    try:
        repo_ol.set_linea_habitual(base_empresa, oid, lid, fecha)
        return True, None
    except Exception as e:
        logger.error(
            "Error al fijar línea habitual operario %s->linea %s (%s): %s",
            id_operario, id_linea, base_empresa, e, exc_info=True,
        )
        return False, "Error al fijar la línea habitual."


def resolver_linea_operario(
    base_empresa: str,
    id_operario: int,
    fecha: date,
    id_turno: Optional[int] = None,
) -> Optional[int]:
    """Resuelve la línea del operario para una fecha: override del roster del día
    (si existe) y, en su defecto, la línea habitual vigente."""
    from mpr.repositories import turno_roster as repo_r
    try:
        override = repo_r.override_linea_roster(base_empresa, fecha, id_operario)
        if override is not None:
            return override
    except Exception as e:
        logger.debug("Override roster línea (%s): %s", base_empresa, e)
    return linea_habitual_operario(base_empresa, id_operario, fecha)
