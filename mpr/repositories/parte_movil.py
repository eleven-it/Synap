"""Parte de producción cargado por el operario desde el móvil.

Modelo de dos etapas: el parte móvil nace en estado `pendiente` (o `borrador`)
con `origen='movil_operario'` y NO ejecuta asiento físico. La `cantidad` física
se mantiene en 0 hasta la aprobación del supervisor (Fase 7); la cantidad real
declarada se guarda en `cantidad_declarada`.
"""
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from core.utils.administranet_types import str_or_default, to_decimal_or_none, to_int_or_none

from mpr.db import mysql_cursor

ORIGEN_MOVIL = "movil_operario"
ESTADOS_EDITABLES = ("borrador", "pendiente")


def obtener_parte_movil_editable(
    base_empresa: str,
    fecha: date,
    id_mpr_turno: int,
    id_usuario: int,
) -> Optional[Dict[str, Any]]:
    """Parte móvil editable (borrador/pendiente) del usuario para fecha+turno.

    Devuelve {id_parte, uuid, estado, lineas: {(id_articulo,id_maquina): cantidad_declarada}}.
    """
    base = (base_empresa or "").strip()
    tid = to_int_or_none(id_mpr_turno)
    uid = to_int_or_none(id_usuario)
    if not base or tid is None or uid is None:
        return None
    with mysql_cursor(base, dict_cursor=True) as cursor:
        cursor.execute(
            """
            SELECT id_mpr_parte, uuid_parte, estado
            FROM mpr_parte
            WHERE fecha_produccion = %s AND id_mpr_turno = %s AND id_usuario = %s
              AND origen = %s AND estado IN ('borrador','pendiente')
            ORDER BY id_mpr_parte DESC
            LIMIT 1
            """,
            [fecha, tid, uid, ORIGEN_MOVIL],
        )
        row = cursor.fetchone()
        if not row:
            return None
        id_parte = int(row["id_mpr_parte"])
        cursor.execute(
            """
            SELECT id_articulo, id_mpr_maquina, cantidad_declarada
            FROM mpr_parte_linea WHERE id_mpr_parte = %s
            """,
            [id_parte],
        )
        lineas: Dict[Tuple[int, Optional[int]], Decimal] = {}
        for r in cursor.fetchall() or []:
            aid = to_int_or_none(r.get("id_articulo"))
            mid = to_int_or_none(r.get("id_mpr_maquina"))
            cant = to_decimal_or_none(r.get("cantidad_declarada")) or Decimal("0")
            if aid is not None:
                lineas[(aid, mid)] = cant
        return {
            "id_parte": id_parte,
            "uuid": row.get("uuid_parte"),
            "estado": str(row.get("estado") or ""),
            "lineas": lineas,
        }


def obtener_cabecera_parte(base_empresa: str, id_parte: int) -> Optional[Dict[str, Any]]:
    """Cabecera del parte para el flujo de aprobación."""
    base = (base_empresa or "").strip()
    pid = to_int_or_none(id_parte)
    if not base or pid is None:
        return None
    with mysql_cursor(base, dict_cursor=True) as cursor:
        cursor.execute(
            """
            SELECT id_mpr_parte, uuid_parte, fecha_produccion, id_mpr_turno, id_usuario,
                   estado, origen, movimiento_fisico_ok, id_usuario_supervisor
            FROM mpr_parte WHERE id_mpr_parte = %s
            """,
            [pid],
        )
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "id_parte": int(row["id_mpr_parte"]),
            "uuid": row.get("uuid_parte"),
            "fecha_produccion": row.get("fecha_produccion"),
            "id_mpr_turno": to_int_or_none(row.get("id_mpr_turno")),
            "id_usuario": to_int_or_none(row.get("id_usuario")),
            "estado": str(row.get("estado") or ""),
            "origen": str(row.get("origen") or ""),
            "movimiento_fisico_ok": bool(row.get("movimiento_fisico_ok", 0)),
            "id_usuario_supervisor": to_int_or_none(row.get("id_usuario_supervisor")),
        }


def listar_lineas_aprobacion(base_empresa: str, id_parte: int) -> List[Dict[str, Any]]:
    """Líneas del parte con datos para aprobación (incluye id de línea y máquina)."""
    base = (base_empresa or "").strip()
    pid = to_int_or_none(id_parte)
    if not base or pid is None:
        return []
    with mysql_cursor(base, dict_cursor=True) as cursor:
        cursor.execute(
            """
            SELECT id_mpr_parte_linea, id_articulo, id_operario, operario_nombre,
                   id_mpr_maquina, maquina_nombre, cantidad_declarada, cantidad_aprobada,
                   gap, motivo
            FROM mpr_parte_linea WHERE id_mpr_parte = %s
            ORDER BY id_mpr_maquina, id_articulo
            """,
            [pid],
        )
        out: List[Dict[str, Any]] = []
        for r in cursor.fetchall() or []:
            out.append({
                "id_mpr_parte_linea": int(r["id_mpr_parte_linea"]),
                "id_articulo": to_int_or_none(r.get("id_articulo")),
                "id_operario": to_int_or_none(r.get("id_operario")),
                "operario_nombre": str_or_default(r.get("operario_nombre"), "-"),
                "id_mpr_maquina": to_int_or_none(r.get("id_mpr_maquina")),
                "maquina_nombre": str_or_default(r.get("maquina_nombre"), None),
                "cantidad_declarada": to_decimal_or_none(r.get("cantidad_declarada")) or Decimal("0"),
                "cantidad_aprobada": to_decimal_or_none(r.get("cantidad_aprobada")),
                "gap": to_decimal_or_none(r.get("gap")) or Decimal("0"),
                "motivo": r.get("motivo"),
            })
        return out


def actualizar_linea_aprobacion(
    cursor,
    id_mpr_parte_linea: int,
    cantidad_aprobada: Decimal,
    gap: Decimal,
    motivo: Optional[str],
) -> None:
    """Fija cantidad_aprobada/gap/motivo y sincroniza `cantidad` física (=aprobada)."""
    cursor.execute(
        """
        UPDATE mpr_parte_linea
        SET cantidad_aprobada = %s, gap = %s, motivo = %s, cantidad = %s
        WHERE id_mpr_parte_linea = %s
        """,
        [
            cantidad_aprobada,
            gap,
            (motivo or None),
            cantidad_aprobada,
            int(id_mpr_parte_linea),
        ],
    )


def marcar_parte_aprobado(cursor, id_parte: int, id_usuario_supervisor: int) -> None:
    """Cierra el parte: estado=aprobado, auditoría y movimiento_fisico_ok=1."""
    from datetime import datetime

    cursor.execute(
        """
        UPDATE mpr_parte
        SET estado = 'aprobado', id_usuario_supervisor = %s, aprobado_en = %s,
            movimiento_fisico_ok = 1
        WHERE id_mpr_parte = %s
        """,
        [int(id_usuario_supervisor), datetime.now(), int(id_parte)],
    )


def listar_partes_pendientes(
    base_empresa: str,
    *,
    fecha: Optional[date] = None,
    id_mpr_turno: Optional[int] = None,
    incluir_borrador: bool = False,
) -> List[Dict[str, Any]]:
    """Partes en estado pendiente (y opcionalmente borrador) para la bandeja."""
    base = (base_empresa or "").strip()
    if not base:
        return []
    estados = "('pendiente','borrador')" if incluir_borrador else "('pendiente')"
    where = [f"p.estado IN {estados}"]
    params: List[Any] = []
    if fecha is not None:
        where.append("p.fecha_produccion = %s")
        params.append(fecha)
    tid = to_int_or_none(id_mpr_turno)
    if tid is not None:
        where.append("p.id_mpr_turno = %s")
        params.append(tid)
    with mysql_cursor(base, dict_cursor=True) as cursor:
        cursor.execute(
            f"""
            SELECT p.id_mpr_parte, p.fecha_produccion, p.id_mpr_turno, p.origen, p.estado,
                   p.registrado_en, t.nombre AS turno_nombre,
                   COUNT(pl.id_mpr_parte_linea) AS lineas,
                   COALESCE(SUM(pl.cantidad_declarada), 0) AS total_declarado,
                   MAX(pl.operario_nombre) AS operario_nombre
            FROM mpr_parte p
            LEFT JOIN mpr_turno t ON t.id_mpr_turno = p.id_mpr_turno
            LEFT JOIN mpr_parte_linea pl ON pl.id_mpr_parte = p.id_mpr_parte
            WHERE {' AND '.join(where)}
            GROUP BY p.id_mpr_parte, p.fecha_produccion, p.id_mpr_turno, p.origen, p.estado,
                     p.registrado_en, t.nombre
            ORDER BY p.fecha_produccion DESC, p.id_mpr_turno DESC, p.id_mpr_parte DESC
            """,
            params,
        )
        out: List[Dict[str, Any]] = []
        for r in cursor.fetchall() or []:
            out.append({
                "id_parte": int(r["id_mpr_parte"]),
                "fecha_produccion": r.get("fecha_produccion"),
                "id_mpr_turno": to_int_or_none(r.get("id_mpr_turno")),
                "turno_nombre": str_or_default(r.get("turno_nombre"), "-"),
                "origen": str(r.get("origen") or ""),
                "estado": str(r.get("estado") or ""),
                "operario_nombre": str_or_default(r.get("operario_nombre"), "-"),
                "lineas": int(r.get("lineas") or 0),
                "total_declarado": to_decimal_or_none(r.get("total_declarado")) or Decimal("0"),
                "registrado_en": r.get("registrado_en"),
            })
        return out


def _insertar_lineas(cursor, id_parte: int, id_operario: int, operario_nombre: str, lineas: List[Dict[str, Any]]) -> None:
    for cel in lineas or []:
        aid = to_int_or_none(cel.get("id_articulo"))
        mid = to_int_or_none(cel.get("id_mpr_maquina"))
        declarada = to_decimal_or_none(cel.get("cantidad_declarada")) or Decimal("0")
        if aid is None or declarada <= 0:
            continue
        cursor.execute(
            """
            INSERT INTO mpr_parte_linea
                (id_mpr_parte, id_articulo, id_operario, operario_nombre, cantidad,
                 id_mpr_maquina, maquina_nombre, cantidad_declarada, cantidad_aprobada, gap, motivo)
            VALUES (%s, %s, %s, %s, 0, %s, %s, %s, NULL, 0, NULL)
            """,
            [
                id_parte,
                aid,
                int(id_operario),
                str_or_default(operario_nombre, "-"),
                mid,
                str_or_default(cel.get("maquina_nombre"), None),
                declarada,
            ],
        )


def crear_o_actualizar_parte_movil(
    base_empresa: str,
    fecha_produccion: date,
    id_mpr_turno: int,
    id_usuario: int,
    id_operario: int,
    operario_nombre: str,
    lineas: List[Dict[str, Any]],
    estado: str = "pendiente",
    notas: str = "",
) -> Tuple[int, str]:
    """Crea o reemplaza el parte móvil editable del usuario para fecha+turno.

    Reemplaza las líneas por completo. Devuelve (id_parte, uuid).
    """
    base = (base_empresa or "").strip()
    estado_norm = estado if estado in ESTADOS_EDITABLES else "pendiente"
    existente = obtener_parte_movil_editable(base, fecha_produccion, id_mpr_turno, id_usuario)
    with mysql_cursor(base) as cursor:
        if existente:
            id_parte = int(existente["id_parte"])
            uid = existente.get("uuid") or str(uuid.uuid4())
            cursor.execute(
                "UPDATE mpr_parte SET estado = %s, notas = %s WHERE id_mpr_parte = %s",
                [estado_norm, str_or_default(notas, ""), id_parte],
            )
            cursor.execute("DELETE FROM mpr_parte_linea WHERE id_mpr_parte = %s", [id_parte])
        else:
            uid = str(uuid.uuid4())
            cursor.execute(
                """
                INSERT INTO mpr_parte
                    (uuid_parte, fecha_produccion, id_mpr_turno, id_usuario, notas,
                     movimiento_fisico_ok, id_lista_produccion, estado, origen)
                VALUES (%s, %s, %s, %s, %s, 0, NULL, %s, %s)
                """,
                [
                    uid,
                    fecha_produccion,
                    int(id_mpr_turno),
                    int(id_usuario),
                    str_or_default(notas, ""),
                    estado_norm,
                    ORIGEN_MOVIL,
                ],
            )
            id_parte = int(cursor.lastrowid)
        _insertar_lineas(cursor, id_parte, id_operario, operario_nombre, lineas)
    return id_parte, uid
