"""Servicios de catálogos MPR: líneas, máquinas y pertenencia versionada.

Orquesta validaciones y delega la persistencia en
`mpr.repositories.maquina_linea`. La fuente de verdad es MySQL (una BD por
empresa), siguiendo el estándar AdministraNET.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

import MySQLdb

from mpr.repositories import maquina_articulo as repo_art
from mpr.repositories import maquina_linea as repo

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Líneas
# --------------------------------------------------------------------------- #
def listar_lineas(base_empresa: str, solo_activas: bool = False) -> List[Dict[str, Any]]:
    try:
        return repo.listar_lineas(base_empresa, solo_activas=solo_activas)
    except Exception as e:
        logger.error("Error al listar líneas en %s: %s", base_empresa, e, exc_info=True)
        return []


def obtener_linea(base_empresa: str, id_linea: int) -> Optional[Dict[str, Any]]:
    try:
        return repo.obtener_linea(base_empresa, id_linea)
    except Exception as e:
        logger.error("Error al obtener línea %s en %s: %s", id_linea, base_empresa, e, exc_info=True)
        return None


def crear_linea(base_empresa: str, nombre: str) -> Tuple[bool, Optional[int], Optional[str]]:
    if not (base_empresa or "").strip():
        return False, None, "Empresa inválida."
    if not (nombre or "").strip():
        return False, None, "El nombre de la línea no puede estar vacío."
    try:
        id_linea = repo.crear_linea(base_empresa, nombre)
        return True, id_linea, None
    except MySQLdb.IntegrityError:
        return False, None, "Ya existe una línea con ese nombre en la empresa."
    except Exception as e:
        logger.error("Error al crear línea en %s: %s", base_empresa, e, exc_info=True)
        return False, None, "Error al crear línea."


def actualizar_linea(base_empresa: str, id_linea: int, nombre: str) -> Tuple[bool, Optional[str]]:
    if not (base_empresa or "").strip():
        return False, "Empresa inválida."
    if not (nombre or "").strip():
        return False, "El nombre de la línea no puede estar vacío."
    if not repo.obtener_linea(base_empresa, id_linea):
        return False, "Línea no encontrada."
    try:
        repo.actualizar_linea(base_empresa, id_linea, nombre)
        return True, None
    except MySQLdb.IntegrityError:
        return False, "Ya existe una línea con ese nombre en la empresa."
    except Exception as e:
        logger.error("Error al actualizar línea %s en %s: %s", id_linea, base_empresa, e, exc_info=True)
        return False, "Error al actualizar línea."


def toggle_linea_activa(base_empresa: str, id_linea: int, activa: bool) -> Tuple[bool, Optional[str]]:
    if not (base_empresa or "").strip():
        return False, "Empresa inválida."
    if not repo.obtener_linea(base_empresa, id_linea):
        return False, "Línea no encontrada."
    try:
        repo.toggle_linea_activa(base_empresa, id_linea, activa)
        return True, None
    except Exception as e:
        logger.error("Error al cambiar estado línea %s en %s: %s", id_linea, base_empresa, e, exc_info=True)
        return False, "Error al cambiar estado de la línea."


# --------------------------------------------------------------------------- #
# Máquinas
# --------------------------------------------------------------------------- #
def listar_maquinas(base_empresa: str, solo_activas: bool = False) -> List[Dict[str, Any]]:
    try:
        return repo.listar_maquinas(base_empresa, solo_activas=solo_activas)
    except Exception as e:
        logger.error("Error al listar máquinas en %s: %s", base_empresa, e, exc_info=True)
        return []


def obtener_maquina(base_empresa: str, id_maquina: int) -> Optional[Dict[str, Any]]:
    try:
        return repo.obtener_maquina(base_empresa, id_maquina)
    except Exception as e:
        logger.error("Error al obtener máquina %s en %s: %s", id_maquina, base_empresa, e, exc_info=True)
        return None


def crear_maquina(base_empresa: str, codigo: str, nombre: str) -> Tuple[bool, Optional[int], Optional[str]]:
    if not (base_empresa or "").strip():
        return False, None, "Empresa inválida."
    if not (codigo or "").strip():
        return False, None, "El código de la máquina no puede estar vacío."
    try:
        id_maquina = repo.crear_maquina(base_empresa, codigo, nombre)
        return True, id_maquina, None
    except MySQLdb.IntegrityError:
        return False, None, "Ya existe una máquina con ese código en la empresa."
    except Exception as e:
        logger.error("Error al crear máquina en %s: %s", base_empresa, e, exc_info=True)
        return False, None, "Error al crear máquina."


def actualizar_maquina(base_empresa: str, id_maquina: int, codigo: str, nombre: str) -> Tuple[bool, Optional[str]]:
    if not (base_empresa or "").strip():
        return False, "Empresa inválida."
    if not (codigo or "").strip():
        return False, "El código de la máquina no puede estar vacío."
    if not repo.obtener_maquina(base_empresa, id_maquina):
        return False, "Máquina no encontrada."
    try:
        repo.actualizar_maquina(base_empresa, id_maquina, codigo, nombre)
        return True, None
    except MySQLdb.IntegrityError:
        return False, "Ya existe una máquina con ese código en la empresa."
    except Exception as e:
        logger.error("Error al actualizar máquina %s en %s: %s", id_maquina, base_empresa, e, exc_info=True)
        return False, "Error al actualizar máquina."


def toggle_maquina_activa(base_empresa: str, id_maquina: int, activa: bool) -> Tuple[bool, Optional[str]]:
    if not (base_empresa or "").strip():
        return False, "Empresa inválida."
    if not repo.obtener_maquina(base_empresa, id_maquina):
        return False, "Máquina no encontrada."
    try:
        repo.toggle_maquina_activa(base_empresa, id_maquina, activa)
        return True, None
    except Exception as e:
        logger.error("Error al cambiar estado máquina %s en %s: %s", id_maquina, base_empresa, e, exc_info=True)
        return False, "Error al cambiar estado de la máquina."


# --------------------------------------------------------------------------- #
# Pertenencia máquina->línea (versionada)
# --------------------------------------------------------------------------- #
def asignar_maquina_linea(
    base_empresa: str,
    id_maquina: int,
    id_linea: int,
    desde: Optional[date] = None,
) -> Tuple[bool, Optional[str]]:
    """Asigna una máquina a una línea a partir de `desde` (hoy por defecto),
    cerrando la pertenencia previa."""
    if not (base_empresa or "").strip():
        return False, "Empresa inválida."
    maquina = repo.obtener_maquina(base_empresa, id_maquina)
    if not maquina:
        return False, "Máquina no encontrada."
    linea = repo.obtener_linea(base_empresa, id_linea)
    if not linea:
        return False, "Línea no encontrada."
    if not linea.get("activo"):
        return False, "No se puede asignar a una línea inactiva."
    fecha = desde or date.today()
    actual = repo.linea_vigente_de_maquina(base_empresa, id_maquina, fecha)
    if actual == int(id_linea):
        return False, "La máquina ya pertenece a esa línea."
    try:
        repo.asignar_maquina_linea(base_empresa, id_maquina, id_linea, fecha)
        return True, None
    except Exception as e:
        logger.error(
            "Error al asignar máquina %s a línea %s en %s: %s",
            id_maquina, id_linea, base_empresa, e, exc_info=True,
        )
        return False, "Error al asignar la máquina a la línea."


def listar_historico_maquina_linea(base_empresa: str, id_maquina: int) -> List[Dict[str, Any]]:
    try:
        return repo.listar_historico_maquina_linea(base_empresa, id_maquina)
    except Exception as e:
        logger.error(
            "Error al listar histórico máquina-línea %s en %s: %s",
            id_maquina, base_empresa, e, exc_info=True,
        )
        return []


# --------------------------------------------------------------------------- #
# Habilitación máquina->artículo (versionada; varios vigentes por máquina)
# --------------------------------------------------------------------------- #
def buscar_articulos(base_empresa: str, q: str, limit: int = 25) -> List[Dict[str, Any]]:
    try:
        return repo_art.buscar_articulos(base_empresa, q, limit=limit)
    except Exception as e:
        logger.error("Error al buscar artículos en %s: %s", base_empresa, e, exc_info=True)
        return []


def listar_articulos_vigentes_maquina(
    base_empresa: str, id_maquina: int, fecha: Optional[date] = None
) -> List[Dict[str, Any]]:
    try:
        return repo_art.listar_articulos_vigentes(base_empresa, id_maquina, fecha or date.today())
    except Exception as e:
        logger.error(
            "Error al listar artículos vigentes máquina %s en %s: %s",
            id_maquina, base_empresa, e, exc_info=True,
        )
        return []


def historico_maquina_articulo(base_empresa: str, id_maquina: int) -> List[Dict[str, Any]]:
    try:
        return repo_art.historico_maquina_articulo(base_empresa, id_maquina)
    except Exception as e:
        logger.error(
            "Error al listar histórico máquina-artículo %s en %s: %s",
            id_maquina, base_empresa, e, exc_info=True,
        )
        return []


def habilitar_articulo_maquina(
    base_empresa: str,
    id_maquina: int,
    id_articulo: int,
    desde: Optional[date] = None,
) -> Tuple[bool, Optional[str]]:
    if not (base_empresa or "").strip():
        return False, "Empresa inválida."
    if not repo.obtener_maquina(base_empresa, id_maquina):
        return False, "Máquina no encontrada."
    aid = _to_int(id_articulo)
    if aid is None:
        return False, "Artículo inválido."
    if not repo_art.articulos_por_ids(base_empresa, [aid]):
        return False, "El artículo no existe en la empresa."
    fecha = desde or date.today()
    if repo_art.articulo_vigente(base_empresa, id_maquina, aid, fecha):
        return False, "El artículo ya está habilitado (vigente) en esta máquina."
    try:
        repo_art.habilitar_articulo(base_empresa, id_maquina, aid, fecha)
        return True, None
    except Exception as e:
        logger.error(
            "Error al habilitar artículo %s en máquina %s (%s): %s",
            aid, id_maquina, base_empresa, e, exc_info=True,
        )
        return False, "Error al habilitar el artículo."


def deshabilitar_articulo_maquina(
    base_empresa: str,
    id_maquina: int,
    id_articulo: int,
    hasta: Optional[date] = None,
) -> Tuple[bool, Optional[str]]:
    if not (base_empresa or "").strip():
        return False, "Empresa inválida."
    if not repo.obtener_maquina(base_empresa, id_maquina):
        return False, "Máquina no encontrada."
    aid = _to_int(id_articulo)
    if aid is None:
        return False, "Artículo inválido."
    fecha = hasta or date.today()
    try:
        afectadas = repo_art.deshabilitar_articulo(base_empresa, id_maquina, aid, fecha)
        if not afectadas:
            return False, "El artículo no estaba habilitado en esta máquina."
        return True, None
    except Exception as e:
        logger.error(
            "Error al deshabilitar artículo %s en máquina %s (%s): %s",
            aid, id_maquina, base_empresa, e, exc_info=True,
        )
        return False, "Error al deshabilitar el artículo."


def _to_int(value: Any) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
