"""Servicios de catálogos MPR: líneas, máquinas y pertenencia versionada.

Orquesta validaciones y delega la persistencia en
`mpr.repositories.maquina_linea`. La fuente de verdad es MySQL (una BD por
empresa), siguiendo el estándar AdministraNET.
"""
from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import MySQLdb

from core.utils.administranet_types import str_or_default, to_decimal_or_none, to_int_or_none
from mpr.db import mysql_cursor
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


def guardar_observacion_planilla_maquina(
    base_empresa: str,
    id_maquina: int,
    observacion: str,
) -> Tuple[bool, Optional[str], str]:
    """Valida y persiste la observación de planilla Control de Calidad por máquina."""
    if not (base_empresa or "").strip():
        return False, "Empresa inválida.", ""
    mid = _to_int(id_maquina)
    if mid is None:
        return False, "Máquina inválida.", ""
    if not repo.obtener_maquina(base_empresa, mid):
        return False, "Máquina no encontrada.", ""
    texto = str(observacion or "").strip()
    if len(texto) > 220:
        return False, "La observación no puede superar 220 caracteres.", ""
    try:
        repo.actualizar_observacion_planilla(base_empresa, mid, texto)
        return True, None, texto
    except Exception as e:
        logger.error(
            "Error al guardar observación planilla máquina %s en %s: %s",
            mid, base_empresa, e, exc_info=True,
        )
        return False, "Error al guardar la observación.", ""


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
def buscar_articulos(
    base_empresa: str,
    q: str,
    limit: int = 25,
    tipo_art_fab: Optional[str] = None,
) -> List[Dict[str, Any]]:
    try:
        return repo_art.buscar_articulos(
            base_empresa, q, limit=limit, tipo_art_fab=tipo_art_fab
        )
    except Exception as e:
        logger.error("Error al buscar artículos en %s: %s", base_empresa, e, exc_info=True)
        return []


def listar_articulos_vigentes_todas_maquinas(
    base_empresa: str, fecha: Optional[date] = None
) -> Dict[int, List[Dict[str, Any]]]:
    try:
        return repo_art.listar_articulos_vigentes_todas_maquinas(
            base_empresa, fecha or date.today()
        )
    except Exception as e:
        logger.error(
            "Error al listar artículos vigentes todas máquinas en %s: %s",
            base_empresa, e, exc_info=True,
        )
        return {}


def _franjas_cantidad_vacias() -> Dict[str, float]:
    return {"manana": 0.0, "tarde": 0.0, "noche": 0.0}


def cantidades_parte_planilla_por_fecha(
    base_empresa: str,
    fecha: date,
) -> Dict[Tuple[int, int], Dict[str, float]]:
    """
    Suma cantidades de partes del día por (id_maquina, id_articulo) y franja horaria.

    Parte aprobado → cantidad_aprobada (0 si null); otro estado → cantidad_declarada.
    Solo líneas con id_mpr_maquina no null.
    """
    base = (base_empresa or "").strip()
    if not base or fecha is None:
        return {}
    try:
        from mpr.services import _franja_horaria_turno, listar_turnos

        turnos_por_id = {
            t["id"]: t for t in listar_turnos(base, solo_activos=False)
        }
        acumulado: Dict[Tuple[int, int], Dict[str, Decimal]] = {}
        with mysql_cursor(base, dict_cursor=True) as cursor:
            cursor.execute(
                """
                SELECT pl.id_mpr_maquina, pl.id_articulo, p.estado, p.id_mpr_turno,
                       pl.cantidad_declarada, pl.cantidad_aprobada
                FROM mpr_parte p
                INNER JOIN mpr_parte_linea pl ON pl.id_mpr_parte = p.id_mpr_parte
                WHERE p.fecha_produccion = %s
                  AND pl.id_mpr_maquina IS NOT NULL
                """,
                [fecha],
            )
            for row in cursor.fetchall() or []:
                mid = to_int_or_none(row.get("id_mpr_maquina"))
                aid = to_int_or_none(row.get("id_articulo"))
                if mid is None or aid is None:
                    continue
                estado = str(row.get("estado") or "").strip().lower()
                if estado == "aprobado":
                    cant = to_decimal_or_none(row.get("cantidad_aprobada")) or Decimal("0")
                else:
                    cant = to_decimal_or_none(row.get("cantidad_declarada")) or Decimal("0")
                if cant <= 0:
                    continue
                id_turno = to_int_or_none(row.get("id_mpr_turno"))
                turno = turnos_por_id.get(id_turno) or {}
                franja = _franja_horaria_turno(
                    str(turno.get("nombre") or ""),
                    turno.get("hora_inicio"),
                )
                if not franja:
                    continue
                clave = (mid, aid)
                bucket = acumulado.setdefault(
                    clave,
                    {"manana": Decimal("0"), "tarde": Decimal("0"), "noche": Decimal("0")},
                )
                bucket[franja] = bucket[franja] + cant
        resultado: Dict[Tuple[int, int], Dict[str, float]] = {}
        for clave, franjas in acumulado.items():
            resultado[clave] = {
                franja: float(valor) for franja, valor in franjas.items()
            }
        return resultado
    except Exception as e:
        logger.error(
            "Error al obtener cantidades planilla CQ %s en %s: %s",
            fecha, base_empresa, e, exc_info=True,
        )
        return {}


def _serializar_cantidad_franjas(cantidades: Dict[str, float]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for franja in ("manana", "tarde", "noche"):
        valor = cantidades.get(franja, 0) or 0
        if isinstance(valor, Decimal):
            valor = float(valor)
        if valor == 0:
            out[franja] = None
        elif float(valor) == int(float(valor)):
            out[franja] = int(float(valor))
        else:
            out[franja] = float(valor)
    return out


def construir_datos_planilla_control_calidad(
    base_empresa: str,
    fecha: date,
    id_linea: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Datos JSON para imprimir la planilla Control de Calidad a una fecha dada.

    Fecha futura: artículos vigentes hoy y cantidades vacías; operarios del roster
    de la fecha solicitada.
    """
    from mpr.services import operarios_roster_por_linea

    hoy = date.today()
    es_futuro = fecha > hoy
    fecha_articulos = hoy if es_futuro else fecha
    id_linea_filtro = _to_int(id_linea) if id_linea is not None else None

    maquinas_raw = listar_maquinas(base_empresa, solo_activas=True)
    if id_linea_filtro is not None:
        maquinas_raw = [
            m for m in maquinas_raw
            if m.get("id_linea_actual") == id_linea_filtro
        ]

    articulos_por_maquina = listar_articulos_vigentes_todas_maquinas(
        base_empresa, fecha_articulos
    )
    cantidades_map: Dict[Tuple[int, int], Dict[str, float]] = {}
    if not es_futuro:
        cantidades_map = cantidades_parte_planilla_por_fecha(base_empresa, fecha)

    maquinas: List[Dict[str, Any]] = []
    id_lineas_planilla: set = set()
    for m in maquinas_raw:
        mid = m.get("id")
        articulos_raw = articulos_por_maquina.get(mid, []) if mid is not None else []
        if not articulos_raw:
            continue
        if m.get("id_linea_actual") is not None:
            id_lineas_planilla.add(m.get("id_linea_actual"))
        articulos: List[Dict[str, Any]] = []
        for art in articulos_raw:
            aid = art.get("id_articulo")
            cantidades = _franjas_cantidad_vacias()
            if aid is not None and not es_futuro:
                cantidades = cantidades_map.get((mid, aid), _franjas_cantidad_vacias())
            articulos.append(
                {
                    "id_articulo": aid,
                    "codigo_manual": art.get("codigo_manual") or "",
                    "codigo_articulo": art.get("codigo_articulo") or "",
                    "descripcion_articulo": art.get("descripcion_articulo") or "",
                    "talle": art.get("talle") or "",
                    "color": art.get("color") or "",
                    "vigencia_desde": (
                        art.get("vigencia_desde").isoformat()
                        if art.get("vigencia_desde") else None
                    ),
                    "creado_en": art.get("creado_en"),
                    "id_mpr_maquina_articulo": art.get("id_mpr_maquina_articulo"),
                    "cantidades": _serializar_cantidad_franjas(cantidades),
                }
            )
        codigo = str(m.get("codigo") or "")
        nombre = str(m.get("nombre") or "")
        maquinas.append(
            {
                "id": mid,
                "codigo": codigo,
                "nombre": nombre,
                "id_linea_actual": m.get("id_linea_actual"),
                "linea_actual_nombre": m.get("linea_actual_nombre") or "",
                "observacion_planilla": m.get("observacion_planilla") or "",
                "codigo_search": f"{codigo} {nombre}".strip().lower(),
                "articulos": articulos,
            }
        )

    operadores_por_linea = operarios_roster_por_linea(
        base_empresa, fecha, id_lineas_planilla
    )
    operadores_json = {
        str(k): v for k, v in operadores_por_linea.items()
    }

    return {
        "fecha": fecha.isoformat(),
        "fecha_articulos": fecha_articulos.isoformat(),
        "es_futuro": es_futuro,
        "maquinas": maquinas,
        "operadores_por_linea": operadores_json,
    }


def _operarios_roster_celda_por_linea(
    base_empresa: str,
    fecha: date,
    id_lineas: Iterable[Any],
) -> Dict[int, Dict[str, List[Dict[str, Any]]]]:
    """
    Operarios del roster por línea y franja, con id y nombre para celdas planilla.
    """
    from mpr.services import _franja_horaria_turno, listar_empleados_operarios, listar_turnos

    lineas_set = {
        id_linea
        for valor in (id_lineas or [])
        if (id_linea := _to_int(valor)) is not None
    }
    vacio = {
        id_linea: {"manana": [], "tarde": [], "noche": []}
        for id_linea in lineas_set
    }
    if not (base_empresa or "").strip() or fecha is None or not lineas_set:
        return vacio
    try:
        from mpr.repositories.operario_linea import lineas_habituales_vigentes
        from mpr.repositories.turno_roster import listar_roster_rango

        filas = listar_roster_rango(base_empresa, fecha, fecha)
        if not filas:
            return vacio
        turnos_por_id = {
            t["id"]: t for t in listar_turnos(base_empresa, solo_activos=False)
        }
        nombres_por_id = {
            op["id"]: (op.get("label") or "").strip()
            for op in listar_empleados_operarios(base_empresa, busqueda=None, limit=500)
        }
        resultado = {
            id_linea: {"manana": [], "tarde": [], "noche": []}
            for id_linea in lineas_set
        }
        vistos: Dict[int, Dict[str, set]] = {
            id_linea: {"manana": set(), "tarde": set(), "noche": set()}
            for id_linea in lineas_set
        }
        lineas_habituales = lineas_habituales_vigentes(base_empresa, fecha)
        for fila in filas:
            id_operario = _to_int(fila.get("id_operario"))
            if id_operario is None:
                continue
            id_linea = (
                _to_int(fila.get("id_mpr_linea"))
                or lineas_habituales.get(id_operario)
            )
            if id_linea not in lineas_set:
                continue
            id_turno = _to_int(fila.get("id_mpr_turno"))
            turno = turnos_por_id.get(id_turno) or {}
            franja = _franja_horaria_turno(
                str(fila.get("nombre_turno") or turno.get("nombre") or ""),
                turno.get("hora_inicio"),
            )
            if not franja or id_operario in vistos[id_linea][franja]:
                continue
            nombre = nombres_por_id.get(id_operario) or ""
            if not nombre:
                continue
            vistos[id_linea][franja].add(id_operario)
            resultado[id_linea][franja].append(
                {"id_operario": id_operario, "nombre": nombre.upper()}
            )
        return resultado
    except Exception as e:
        logger.warning(
            "Error operarios roster celda planilla %s (%s): %s",
            base_empresa, fecha, e, exc_info=True,
        )
        return vacio


def _turnos_columnas_planilla(base_empresa: str) -> List[Dict[str, Any]]:
    from mpr.services import _franja_horaria_turno, listar_turnos

    columnas: List[Dict[str, Any]] = []
    for turno in listar_turnos(base_empresa, solo_activos=True):
        tid = turno.get("id")
        if tid is None:
            continue
        franja = _franja_horaria_turno(
            str(turno.get("nombre") or ""),
            turno.get("hora_inicio"),
        )
        if not franja:
            continue
        columnas.append({
            "id": int(tid),
            "nombre": str(turno.get("nombre") or ""),
            "franja": franja,
        })
    orden = {"manana": 0, "tarde": 1, "noche": 2}
    columnas.sort(key=lambda c: (orden.get(c["franja"], 9), c["id"]))
    return columnas


def _franja_a_turno_id(turnos_columnas: List[Dict[str, Any]]) -> Dict[str, int]:
    mapping: Dict[str, int] = {}
    for col in turnos_columnas:
        franja = col.get("franja")
        if franja and franja not in mapping:
            mapping[str(franja)] = int(col["id"])
    return mapping


def construir_grilla_parte_planilla(
    base_empresa: str,
    fecha: date,
    *,
    id_linea: Optional[int] = None,
    id_maquina: Optional[int] = None,
    marcas_incluidos: Optional[Sequence[int]] = None,
    q: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Grilla analista máquina×artículo con columnas turno M/T/N (planilla QC).

    Envuelve ``construir_datos_planilla_control_calidad`` + cupo Fabricando +
    precarga por (fecha, máquina, artículo, turno). No altera ``construir_grilla_parte``.
    """
    from mpr.repositories.parte import (
        fecha_planilla_tiene_parte_aprobado,
        precarga_planilla_por_fecha,
    )
    from mpr.repositories.transicion_lote import (
        fecha_tiene_control_calidad,
        turnos_con_control_calidad,
    )
    from mpr.services import (
        _fabricando_por_componentes,
        _fetch_descripciones_articulo,
        _filtrar_ids_por_marcas,
        _pivot_stock_por_tipo_mpr,
        _query_enviados_todos_componentes,
        obtener_config_mpr,
    )

    resultado: Dict[str, Any] = {
        "filas": [],
        "filas_vacio": True,
        "turnos_columnas": [],
        "fecha": fecha.isoformat() if fecha else None,
        "dia_bloqueado_cc": False,
        "dia_aprobado": False,
        "turnos_bloqueados": [],
    }
    base = (base_empresa or "").strip()
    if not base or fecha is None:
        return resultado

    turnos_columnas = _turnos_columnas_planilla(base)
    resultado["turnos_columnas"] = turnos_columnas
    franja_turno = _franja_a_turno_id(turnos_columnas)

    id_linea_filtro = _to_int(id_linea) if id_linea is not None else None
    id_maquina_filtro = _to_int(id_maquina) if id_maquina is not None else None
    q_norm = (q or "").strip().lower()

    planilla = construir_datos_planilla_control_calidad(
        base, fecha, id_linea=id_linea_filtro
    )
    maquinas_raw = planilla.get("maquinas") or []
    if id_maquina_filtro is not None:
        maquinas_raw = [m for m in maquinas_raw if m.get("id") == id_maquina_filtro]

    articulo_ids: List[int] = []
    for maq in maquinas_raw:
        for art in maq.get("articulos") or []:
            aid = _to_int(art.get("id_articulo"))
            if aid is not None:
                articulo_ids.append(aid)
    articulo_ids = list(dict.fromkeys(articulo_ids))

    fabricando_map: Dict[int, float] = {}
    desc_map: Dict[int, Tuple[str, str]] = {}
    if articulo_ids:
        try:
            envios_map = _query_enviados_todos_componentes(base)
            stock_pivot, _ = _pivot_stock_por_tipo_mpr(base, articulo_ids)
            fabricando_map = _fabricando_por_componentes(
                base, articulo_ids, envios_map, stock_pivot
            )
            desc_map = _fetch_descripciones_articulo(base, articulo_ids)
        except Exception as exc:
            logger.warning(
                "construir_grilla_parte_planilla cupo %s: %s", base, exc, exc_info=True
            )

    if marcas_incluidos and articulo_ids:
        permitidos = _filtrar_ids_por_marcas(base, articulo_ids, marcas_incluidos)
        articulo_ids_set = set(permitidos)
    else:
        articulo_ids_set = set(articulo_ids)

    id_lineas_planilla = {
        m.get("id_linea_actual")
        for m in maquinas_raw
        if m.get("id_linea_actual") is not None
    }
    operarios_celda = _operarios_roster_celda_por_linea(base, fecha, id_lineas_planilla)

    precarga: Dict[Tuple[int, int, int], Dict[str, int]] = {}
    if not planilla.get("es_futuro"):
        precarga = precarga_planilla_por_fecha(base, fecha)

    turnos_bloqueados = turnos_con_control_calidad(base, fecha)
    dia_bloqueado_cc = fecha_tiene_control_calidad(base, fecha)
    dia_aprobado = False
    if not planilla.get("es_futuro"):
        dia_aprobado = fecha_planilla_tiene_parte_aprobado(base, fecha)

    # Con bloqueo OFF (cutover/ajuste) se habilitan celdas aunque Fabricando = 0.
    bloquear_fab = bool(
        obtener_config_mpr(base).get("bloquear_parte_supera_fabricando", True)
    )

    filas: List[Dict[str, Any]] = []
    for maq in maquinas_raw:
        mid = maq.get("id")
        if mid is None:
            continue
        maq_nombre = str(maq.get("nombre") or "")
        id_linea_maq = maq.get("id_linea_actual")
        ops_linea = operarios_celda.get(int(id_linea_maq or 0), {})
        for art in maq.get("articulos") or []:
            aid = _to_int(art.get("id_articulo"))
            if aid is None or aid not in articulo_ids_set:
                continue
            descripcion = str(art.get("descripcion_articulo") or "")
            codigo = str(art.get("codigo_manual") or art.get("codigo_articulo") or "")
            if q_norm:
                busqueda = f"{descripcion} {codigo}".lower()
                if q_norm not in busqueda:
                    continue
            fab = float(fabricando_map.get(aid, 0.0) or 0.0)
            turnos_payload: Dict[int, Dict[str, Any]] = {}
            ingresado = 0
            cant_franjas = art.get("cantidades") or {}
            for col in turnos_columnas:
                tid = int(col["id"])
                franja = col["franja"]
                prec = precarga.get((int(mid), aid, tid), {})
                doc = int(prec.get("docenas") or 0)
                par = int(prec.get("pares") or 0)
                if doc == 0 and par == 0 and not planilla.get("es_futuro"):
                    raw = cant_franjas.get(franja)
                    if raw is not None:
                        entero = int(float(raw))
                        doc, par = entero // 12, entero % 12
                ingresado += doc * 12 + par
                turnos_payload[tid] = {
                    "docenas": doc,
                    "pares": par,
                    "operario_id": to_int_or_none(prec.get("id_operario")),
                    "operarios": list(ops_linea.get(franja) or []),
                    "franja": franja,
                    "bloqueado": dia_bloqueado_cc or tid in turnos_bloqueados,
                }
            cod_desc = desc_map.get(aid, (codigo, descripcion))
            filas.append({
                "id_mpr_maquina": int(mid),
                "maquina_nombre": maq_nombre,
                "id_articulo": aid,
                "descripcion": descripcion or str_or_default(cod_desc[1], "-"),
                "codigo_tooltip": str(cod_desc[0] or codigo or ""),
                "fabricando": fab,
                "ingresado": ingresado,
                "tiene_precarga": ingresado > 0,
                "inputs_habilitados": (
                    (fab > 0 or not bloquear_fab) and not dia_bloqueado_cc
                ),
                "turnos": turnos_payload,
                "show_maquina": False,
                "rowspan_maquina": 1,
            })

    _anotar_rowspan_maquina_filas(filas)
    resultado["filas"] = filas
    resultado["filas_vacio"] = len(filas) == 0
    resultado["turnos_bloqueados"] = sorted(turnos_bloqueados)
    resultado["dia_bloqueado_cc"] = dia_bloqueado_cc
    resultado["dia_aprobado"] = dia_aprobado
    return resultado


def _anotar_rowspan_maquina_filas(filas: List[Dict[str, Any]]) -> None:
    """Marca show_maquina / rowspan_maquina para combinar celdas de la misma máquina."""
    if not filas:
        return
    i = 0
    n = len(filas)
    while i < n:
        mid = filas[i].get("id_mpr_maquina")
        j = i + 1
        while j < n and filas[j].get("id_mpr_maquina") == mid:
            j += 1
        span = j - i
        filas[i]["show_maquina"] = True
        filas[i]["rowspan_maquina"] = span
        for k in range(i + 1, j):
            filas[k]["show_maquina"] = False
            filas[k]["rowspan_maquina"] = 1
        i = j


def construir_grilla_carga_articulos(
    base_empresa: str,
    id_linea: Optional[int] = None,
    fecha: Optional[date] = None,
) -> Dict[str, Any]:
    """Contexto para la grilla de carga de artículos por máquina (supervisor)."""
    hoy = date.today()
    fecha_ref = fecha or hoy
    if fecha_ref > hoy:
        fecha_ref = hoy
    lineas = listar_lineas(base_empresa, solo_activas=True)
    id_linea_filtro = _to_int(id_linea) if id_linea is not None else None
    maquinas_raw = listar_maquinas(base_empresa, solo_activas=True)
    if id_linea_filtro is not None:
        maquinas_raw = [
            m for m in maquinas_raw
            if m.get("id_linea_actual") == id_linea_filtro
        ]
    articulos_por_maquina = listar_articulos_vigentes_todas_maquinas(
        base_empresa, fecha_ref
    )
    maquinas: List[Dict[str, Any]] = []
    con_articulos = 0
    for m in maquinas_raw:
        mid = m.get("id")
        articulos = articulos_por_maquina.get(mid, []) if mid is not None else []
        if articulos:
            con_articulos += 1
        codigo = str(m.get("codigo") or "")
        nombre = str(m.get("nombre") or "")
        maquinas.append(
            {
                **m,
                "articulos": articulos,
                "codigo_search": f"{codigo} {nombre}".strip().lower(),
            }
        )
    return {
        "maquinas": maquinas,
        "lineas": lineas,
        "id_linea_filtro": id_linea_filtro,
        "fecha": fecha_ref,
        "fecha_hoy": hoy,
        "es_fecha_pasada": fecha_ref < hoy,
        "total_maquinas": len(maquinas),
        "con_articulos": con_articulos,
    }


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
    hoy = date.today()
    fecha = desde or hoy
    if fecha > hoy:
        return False, "No se pueden asignar artículos en fechas futuras."
    if repo_art.articulo_vigente(base_empresa, id_maquina, aid, fecha):
        return False, "El artículo ya está habilitado (vigente) en esta máquina."
    try:
        if fecha == hoy:
            repo_art.habilitar_articulo(base_empresa, id_maquina, aid, hoy, hasta=None)
        else:
            repo_art.habilitar_articulo(
                base_empresa,
                id_maquina,
                aid,
                fecha,
                hasta=fecha + timedelta(days=1),
            )
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
    fecha: Optional[date] = None,
) -> Tuple[bool, Optional[str]]:
    if not (base_empresa or "").strip():
        return False, "Empresa inválida."
    if not repo.obtener_maquina(base_empresa, id_maquina):
        return False, "Máquina no encontrada."
    aid = _to_int(id_articulo)
    if aid is None:
        return False, "Artículo inválido."
    hoy = date.today()
    ref = fecha or hoy
    if ref > hoy:
        return False, "No se pueden modificar asignaciones en fechas futuras."
    from mpr.repositories.parte import tiene_parte_maquina_articulo_fecha

    if tiene_parte_maquina_articulo_fecha(base_empresa, ref, id_maquina, aid):
        return (
            False,
            "No se puede quitar el artículo: hay parte de producción registrado "
            "para esa máquina y fecha.",
        )
    try:
        if ref == hoy:
            afectadas = repo_art.deshabilitar_articulo(base_empresa, id_maquina, aid, hoy)
            if not afectadas:
                return False, "El artículo no estaba habilitado en esta máquina."
        else:
            if not repo_art.quitar_cobertura_fecha(base_empresa, id_maquina, aid, ref):
                return False, "El artículo no estaba habilitado en esta máquina para esa fecha."
        return True, None
    except Exception as e:
        logger.error(
            "Error al deshabilitar artículo %s en máquina %s (%s): %s",
            aid, id_maquina, base_empresa, e, exc_info=True,
        )
        return False, "Error al deshabilitar el artículo."


def enriquecer_filas_tablero_indicadores_fabricando(
    base_empresa: str,
    filas: List[Dict[str, Any]],
    *,
    fecha: Optional[date] = None,
) -> List[Dict[str, Any]]:
    """
    Enriquece filas del tablero Par con indicadores de máquina en columna Fabricando.

    Idempotente: filas sin ``id_articulo`` (p. ej. Pack) se omiten sin error.
    """
    if not filas:
        return filas

    fecha_ref = fecha or date.today()
    fecha_iso = fecha_ref.isoformat()
    fecha_ddmmyyyy = fecha_ref.strftime("%d/%m/%Y")
    base = (base_empresa or "").strip()
    if not base:
        return filas

    maquinas_raw = listar_maquinas(base, solo_activas=True)
    maquina_por_id = {
        int(m["id"]): m for m in maquinas_raw if _to_int(m.get("id")) is not None
    }
    articulos_por_maquina = listar_articulos_vigentes_todas_maquinas(base, fecha_ref)

    maquinas_por_articulo: Dict[int, List[Dict[str, Any]]] = {}
    linea_nombre_por_id: Dict[int, str] = {}
    for mid, articulos in (articulos_por_maquina or {}).items():
        maq = maquina_por_id.get(int(mid))
        if not maq:
            continue
        id_linea = _to_int(maq.get("id_linea_actual"))
        linea_nombre = str(maq.get("linea_actual_nombre") or "")
        if id_linea is not None and linea_nombre:
            linea_nombre_por_id[id_linea] = linea_nombre
        for art in articulos or []:
            aid = _to_int(art.get("id_articulo"))
            if aid is None:
                continue
            maquinas_por_articulo.setdefault(aid, []).append(
                {
                    "id": int(mid),
                    "codigo": str(maq.get("codigo") or ""),
                    "nombre": str(maq.get("nombre") or ""),
                    "id_linea": id_linea,
                    "linea_nombre": linea_nombre,
                }
            )

    for aid, asignadas in list(maquinas_por_articulo.items()):
        vistos: set = set()
        unicas: List[Dict[str, Any]] = []
        for m in asignadas:
            if m["id"] not in vistos:
                vistos.add(m["id"])
                unicas.append(m)
        unicas.sort(key=_clave_orden_maquina_item)
        maquinas_por_articulo[aid] = unicas

    cantidades_map = cantidades_parte_planilla_por_fecha(base, fecha_ref)
    id_lineas = {
        m["id_linea"]
        for maqs in maquinas_por_articulo.values()
        for m in maqs
        if m.get("id_linea") is not None
    }
    operarios_celda = _operarios_roster_celda_por_linea(base, fecha_ref, id_lineas)

    for fila in filas:
        aid = _to_int(fila.get("id_articulo"))
        if aid is None:
            continue

        enviado = float(fila.get("enviado") or 0)
        maquinas_asignadas = list(maquinas_por_articulo.get(aid, []))
        tiene_maquina = bool(maquinas_asignadas)
        fabricando_sin_maquina = enviado > 0 and not tiene_maquina

        fila["tiene_maquina"] = tiene_maquina
        fila["fabricando_sin_maquina"] = fabricando_sin_maquina
        fila["maquinas_asignadas"] = maquinas_asignadas

        grupos_por_linea: Dict[Any, Dict[str, Any]] = {}
        for m in maquinas_asignadas:
            lid = _to_int(m.get("id_linea"))
            key = lid if lid is not None else "__sin_linea__"
            if key not in grupos_por_linea:
                linea_nom = (
                    linea_nombre_por_id.get(lid, m.get("linea_nombre") or f"Línea {lid}")
                    if lid is not None
                    else "Sin fila"
                )
                ops = operarios_celda.get(lid, {}) if lid is not None else {}
                grupos_por_linea[key] = {
                    "nombre": linea_nom,
                    "id_linea": lid,
                    "roster": {
                        "manana": [
                            o.get("nombre", "")
                            for o in (ops.get("manana") or [])
                            if o.get("nombre")
                        ],
                        "tarde": [
                            o.get("nombre", "")
                            for o in (ops.get("tarde") or [])
                            if o.get("nombre")
                        ],
                        "noche": [
                            o.get("nombre", "")
                            for o in (ops.get("noche") or [])
                            if o.get("nombre")
                        ],
                    },
                    "maquinas": [],
                }
            mid = m["id"]
            cant = cantidades_map.get((mid, aid), _franjas_cantidad_vacias())
            franjas = _serializar_cantidad_franjas(cant)
            grupos_por_linea[key]["maquinas"].append(
                {
                    "id": mid,
                    "codigo": m.get("codigo") or "",
                    "nombre": m.get("nombre") or "",
                    "manana": franjas.get("manana", 0),
                    "tarde": franjas.get("tarde", 0),
                    "noche": franjas.get("noche", 0),
                    "tiene_parte": any(
                        float(franjas.get(f) or 0) > 0
                        for f in ("manana", "tarde", "noche")
                    ),
                }
            )

        def _ord_grupo(item: Tuple[Any, Dict[str, Any]]) -> Tuple[int, str]:
            key, g = item
            if key == "__sin_linea__":
                return (9_999_999, g.get("nombre") or "")
            return (int(key) if isinstance(key, int) else 9_999_998, g.get("nombre") or "")

        grupos_fila = [g for _, g in sorted(grupos_por_linea.items(), key=_ord_grupo)]
        for g in grupos_fila:
            g["maquinas"] = sorted(g.get("maquinas") or [], key=_clave_orden_maquina_item)

        fabricando_detalle = {
            "articulo": str(fila.get("descripcion_articulo") or ""),
            "codigo": str(fila.get("codigo_manual") or ""),
            "fabricando_pares": enviado,
            "grupos_fila": grupos_fila,
            "fecha_iso": fecha_iso,
            "fecha_ddmmyyyy": fecha_ddmmyyyy,
        }
        fila["fabricando_detalle"] = fabricando_detalle
        fila["fabricando_detalle_json"] = json.dumps(fabricando_detalle, ensure_ascii=False)

    return filas


def enriquecer_filas_tablero_armado_maquina(
    base_empresa: str,
    filas: List[Dict[str, Any]],
    *,
    fecha: Optional[date] = None,
) -> List[Dict[str, Any]]:
    """
    Enriquece filas del tablero de Armado (pack) con nro. de máquina y reordena
    como Control de calidad: máquina 1..N, luego sin máquina; dentro, id_articulo.

    La máquina del pack se resuelve vía componentes BOM + asignación vigente
    ``mpr_maquina_articulo`` (menor código numérico si hay varias).
    """
    if not filas:
        return filas

    base = (base_empresa or "").strip()
    if not base:
        for fila in filas:
            fila.setdefault("id_mpr_maquina", 0)
            fila.setdefault("maquina_nombre", "—")
            fila.setdefault("tiene_maquina", False)
            fila.setdefault("show_maquina", True)
            fila.setdefault("rowspan_maquina", 1)
            fila.setdefault("maquina_tint", 0)
        return filas

    from mpr.services import (
        _anotar_rowspan_maquina_clasificacion,
        _orden_maquina_clasificacion,
        bulk_bom_detalle,
        bulk_id_en_abm,
    )

    fecha_ref = fecha or date.today()
    pack_ids: List[int] = []
    for fila in filas:
        aid = _to_int(fila.get("id_articulo"))
        if aid is not None:
            pack_ids.append(aid)

    abm_map = bulk_id_en_abm(base, pack_ids) if pack_ids else {}
    bom_map = (
        bulk_bom_detalle(base, list(set(abm_map.values()))) if abm_map else {}
    )

    componentes_por_pack: Dict[int, List[int]] = {}
    for pack_id, id_abm in abm_map.items():
        bom = bom_map.get(id_abm) or {}
        comps: List[int] = []
        for comp in bom.get("componentes") or []:
            cid = _to_int(comp.get("id_articulo"))
            qty = to_int_or_none(comp.get("cantidad_articulo"))
            if cid is not None and qty is not None and int(qty) > 0:
                comps.append(cid)
        componentes_por_pack[int(pack_id)] = comps

    maquinas_raw = listar_maquinas(base, solo_activas=True)
    maquina_por_id = {
        int(m["id"]): m for m in maquinas_raw if _to_int(m.get("id")) is not None
    }
    articulos_por_maquina = listar_articulos_vigentes_todas_maquinas(base, fecha_ref)

    maquinas_por_articulo: Dict[int, List[Dict[str, Any]]] = {}
    for mid, articulos in (articulos_por_maquina or {}).items():
        maq = maquina_por_id.get(int(mid))
        if not maq:
            continue
        item = {
            "id": int(mid),
            "codigo": str(maq.get("codigo") or ""),
            "nombre": str(maq.get("nombre") or ""),
        }
        for art in articulos or []:
            aid = _to_int(art.get("id_articulo"))
            if aid is None:
                continue
            maquinas_por_articulo.setdefault(aid, []).append(item)

    for aid, asignadas in list(maquinas_por_articulo.items()):
        vistos: set = set()
        unicas: List[Dict[str, Any]] = []
        for m in asignadas:
            if m["id"] not in vistos:
                vistos.add(m["id"])
                unicas.append(m)
        unicas.sort(key=_clave_orden_maquina_item)
        maquinas_por_articulo[aid] = unicas

    for fila in filas:
        pack_id = _to_int(fila.get("id_articulo"))
        candidatas: List[Dict[str, Any]] = []
        vistos_m: set = set()
        for cid in componentes_por_pack.get(pack_id or -1, []):
            for m in maquinas_por_articulo.get(cid, []):
                if m["id"] not in vistos_m:
                    vistos_m.add(m["id"])
                    candidatas.append(m)
        candidatas.sort(key=_clave_orden_maquina_item)
        if candidatas:
            elegida = candidatas[0]
            codigo = str(elegida.get("codigo") or "").strip()
            nombre = str(elegida.get("nombre") or "").strip()
            fila["id_mpr_maquina"] = int(elegida["id"])
            fila["maquina_nombre"] = codigo or nombre or "—"
            fila["tiene_maquina"] = True
            fila["maquinas_asignadas"] = candidatas
        else:
            fila["id_mpr_maquina"] = 0
            fila["maquina_nombre"] = "—"
            fila["tiene_maquina"] = False
            fila["maquinas_asignadas"] = []

    filas.sort(
        key=lambda f: (
            _orden_maquina_clasificacion(
                int(f.get("id_mpr_maquina") or 0),
                str(f.get("maquina_nombre") or ""),
            ),
            int(f.get("id_articulo") or 0),
            str(f.get("codigo_manual") or ""),
        )
    )
    _anotar_rowspan_maquina_clasificacion(filas)
    return filas


def _clave_orden_maquina_item(m: Any) -> Tuple[int, str]:
    """Clave de orden: número de máquina (código/id) y código textual."""
    if not isinstance(m, dict):
        return (9_999_999, "")
    codigo = str(m.get("codigo") or "").strip()
    n: Optional[int] = None
    if codigo.isdigit():
        n = int(codigo)
    else:
        digitos = "".join(ch for ch in codigo if ch.isdigit())
        if digitos:
            try:
                n = int(digitos)
            except ValueError:
                n = None
    if n is None:
        n = _to_int(m.get("id"))
    if n is None:
        n = 9_999_999
    return (n, codigo.lower())


def _orden_numerico_maquina(maquinas: Any) -> int:
    """Menor código/id numérico de máquinas asignadas (1…N). Sin máquinas → sentinela alto."""
    mejor: Optional[int] = None
    for m in maquinas or []:
        n, _ = _clave_orden_maquina_item(m)
        if n >= 9_999_999:
            continue
        if mejor is None or n < mejor:
            mejor = n
    return mejor if mejor is not None else 9_999_999


def ordenar_filas_tablero_maquina_marca(
    filas: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Orden del tablero:
    1. Con máquina asignada, luego sin máquina.
    2. Entre los que tienen máquina: por número de máquina 1…N (menor código/id).
    3. Luego por marca (nombre o código) y descripción.
    """
    if not filas:
        return filas

    def _clave(fila: Dict[str, Any]) -> Tuple[int, int, str, str]:
        con_maquina = 0 if fila.get("tiene_maquina") else 1
        if con_maquina == 0:
            n_maq = _orden_numerico_maquina(fila.get("maquinas_asignadas"))
        else:
            n_maq = 9_999_999
        marca = str(fila.get("marca_nombre") or "").strip().casefold()
        if not marca:
            cm = fila.get("codigo_marca")
            marca = f"#{cm}" if cm is not None else "\uffff"
        desc = str(fila.get("descripcion_articulo") or "").strip().casefold()
        return (con_maquina, n_maq, marca, desc)

    return sorted(filas, key=_clave)


def _to_int(value: Any) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
