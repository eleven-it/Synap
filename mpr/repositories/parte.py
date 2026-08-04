"""Parte de producción (mpr_parte, mpr_parte_linea, mpr_parte_ajuste)."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

import MySQLdb
from core.utils.administranet_types import (
    str_or_default,
    to_date_or_none,
    to_decimal_or_none,
    to_int_or_none,
)

from mpr.db import get_mysql_connection, mysql_cursor
from mpr.repositories.records import ParteAjusteRecord, ParteLineaRecord, ParteRecord
from mpr.repositories.turno_roster import obtener_turno_record

ORIGEN_DIRECTO_SUPERVISOR = "directo_supervisor"


def _parse_datetime(val: Any) -> datetime:
    if isinstance(val, datetime):
        return val
    if val is None:
        return datetime.now()
    return datetime.now()


def _row_to_parte(
    base_empresa: str,
    row: Dict[str, Any],
    *,
    with_relations: bool = False,
) -> ParteRecord:
    id_parte = int(row["id_mpr_parte"])
    turno = obtener_turno_record(base_empresa, int(row["id_mpr_turno"]))
    lineas = listar_lineas_parte(base_empresa, id_parte) if with_relations else None
    ajustes = listar_ajustes_parte(base_empresa, id_parte) if with_relations else None
    return ParteRecord(
        id_mpr_parte=id_parte,
        uuid_parte=row.get("uuid_parte"),
        fecha_produccion=to_date_or_none(row.get("fecha_produccion")) or date.today(),
        id_mpr_turno=int(row["id_mpr_turno"]),
        turno=turno,
        id_usuario=int(row.get("id_usuario") or 0),
        registrado_en=_parse_datetime(row.get("registrado_en")),
        notas=str_or_default(row.get("notas"), ""),
        movimiento_fisico_ok=bool(row.get("movimiento_fisico_ok", 0)),
        id_lista_produccion=to_int_or_none(row.get("id_lista_produccion")),
        base_empresa=base_empresa,
        lineas=lineas,
        ajustes=ajustes,
    )


def opp_acumulado_por_pack(
    base_empresa: str,
    pack_ids: Optional[List[int]] = None,
    *,
    desde: Optional[datetime] = None,
) -> Dict[int, Decimal]:
    """
    Suma cantidades de mpr_parte_linea + mpr_parte_ajuste por id_articulo.

    Si ``desde`` está definido, solo cuenta partes con ``registrado_en >= desde``
    (útil para FIFO de anulación de envíos tablero).
    """
    base = (base_empresa or "").strip()
    if not base:
        return {}

    ids_filter = ""
    params: List[Any] = []
    if pack_ids is not None:
        if not pack_ids:
            return {}
        clean = [to_int_or_none(i) for i in pack_ids]
        clean = [i for i in clean if i is not None]
        if not clean:
            return {}
        placeholders = ",".join(["%s"] * len(clean))
        ids_filter = f" AND pl.id_articulo IN ({placeholders})"
        params.extend(clean)

    filtro_fecha = ""
    if desde is not None:
        filtro_fecha = " AND p.registrado_en >= %s"
        params_fecha = [desde]
    else:
        params_fecha = []

    acum: Dict[int, Decimal] = {}
    with mysql_cursor(base, dict_cursor=True) as cursor:
        cursor.execute(
            f"""
            SELECT pl.id_articulo, SUM(pl.cantidad) AS total
            FROM mpr_parte_linea pl
            INNER JOIN mpr_parte p ON p.id_mpr_parte = pl.id_mpr_parte
            WHERE 1=1 {ids_filter}{filtro_fecha}
            GROUP BY pl.id_articulo
            """,
            params + params_fecha,
        )
        for row in cursor.fetchall() or []:
            aid = to_int_or_none(row.get("id_articulo"))
            total = to_decimal_or_none(row.get("total"))
            if aid is not None and total is not None:
                acum[aid] = acum.get(aid, Decimal("0")) + total

        ids_filter_aj = ids_filter.replace("pl.id_articulo", "a.id_articulo") if ids_filter else ""
        params_aj = list(params)
        if desde is not None:
            params_aj.append(desde)
        cursor.execute(
            f"""
            SELECT a.id_articulo, SUM(a.delta) AS total
            FROM mpr_parte_ajuste a
            INNER JOIN mpr_parte p ON p.id_mpr_parte = a.id_mpr_parte
            WHERE 1=1 {ids_filter_aj}{filtro_fecha}
            GROUP BY a.id_articulo
            """,
            params_aj,
        )
        for row in cursor.fetchall() or []:
            aid = to_int_or_none(row.get("id_articulo"))
            total = to_decimal_or_none(row.get("total"))
            if aid is not None and total is not None:
                acum[aid] = acum.get(aid, Decimal("0")) + total
    return acum


def obtener_parte_por_pk(
    base_empresa: str,
    parte_id: str,
    *,
    with_relations: bool = False,
) -> Optional[ParteRecord]:
    base = (base_empresa or "").strip()
    if not base or not parte_id:
        return None
    pid = (parte_id or "").strip()
    with mysql_cursor(base, dict_cursor=True) as cursor:
        if len(pid) == 36 and "-" in pid:
            cursor.execute(
                """
                SELECT id_mpr_parte, uuid_parte, fecha_produccion, id_mpr_turno, id_usuario,
                       registrado_en, notas, movimiento_fisico_ok, id_lista_produccion
                FROM mpr_parte WHERE uuid_parte = %s
                """,
                [pid],
            )
        else:
            id_int = to_int_or_none(pid)
            if id_int is None:
                return None
            cursor.execute(
                """
                SELECT id_mpr_parte, uuid_parte, fecha_produccion, id_mpr_turno, id_usuario,
                       registrado_en, notas, movimiento_fisico_ok, id_lista_produccion
                FROM mpr_parte WHERE id_mpr_parte = %s
                """,
                [id_int],
            )
        row = cursor.fetchone()
        if not row:
            return None
        return _row_to_parte(base, row, with_relations=with_relations)


def listar_lineas_parte(base_empresa: str, id_mpr_parte: int) -> List[ParteLineaRecord]:
    base = (base_empresa or "").strip()
    with mysql_cursor(base, dict_cursor=True) as cursor:
        cursor.execute(
            """
            SELECT id_articulo, id_operario, operario_nombre, cantidad
            FROM mpr_parte_linea WHERE id_mpr_parte = %s
            ORDER BY id_articulo, id_operario
            """,
            [int(id_mpr_parte)],
        )
        return [
            ParteLineaRecord(
                id_articulo=int(r["id_articulo"]),
                id_operario=int(r["id_operario"]),
                cantidad=to_decimal_or_none(r.get("cantidad")) or Decimal("0"),
                operario_nombre=str_or_default(r.get("operario_nombre"), "-"),
            )
            for r in (cursor.fetchall() or [])
        ]


def listar_ajustes_parte(base_empresa: str, id_mpr_parte: int) -> List[ParteAjusteRecord]:
    base = (base_empresa or "").strip()
    with mysql_cursor(base, dict_cursor=True) as cursor:
        cursor.execute(
            """
            SELECT id_mpr_parte_ajuste, uuid_ajuste, id_mpr_parte, id_articulo, id_operario,
                   delta, motivo, id_usuario, registrado_en, ajuste_fisico_ok
            FROM mpr_parte_ajuste WHERE id_mpr_parte = %s
            ORDER BY registrado_en
            """,
            [int(id_mpr_parte)],
        )
        return [
            ParteAjusteRecord(
                id_mpr_parte_ajuste=int(r["id_mpr_parte_ajuste"]),
                uuid_ajuste=r.get("uuid_ajuste"),
                id_mpr_parte=int(r["id_mpr_parte"]),
                id_articulo=int(r["id_articulo"]),
                id_operario=int(r["id_operario"]),
                delta=to_decimal_or_none(r.get("delta")) or Decimal("0"),
                motivo=str_or_default(r.get("motivo"), "-"),
                id_usuario=int(r.get("id_usuario") or 0),
                registrado_en=_parse_datetime(r.get("registrado_en")),
                ajuste_fisico_ok=bool(r.get("ajuste_fisico_ok", 0)),
                base_empresa=base,
            )
            for r in (cursor.fetchall() or [])
        ]


def obtener_linea_parte(
    base_empresa: str,
    id_mpr_parte: int,
    id_articulo: int,
    id_operario: int,
) -> Optional[ParteLineaRecord]:
    base = (base_empresa or "").strip()
    with mysql_cursor(base, dict_cursor=True) as cursor:
        cursor.execute(
            """
            SELECT id_articulo, id_operario, operario_nombre, cantidad
            FROM mpr_parte_linea
            WHERE id_mpr_parte = %s AND id_articulo = %s AND id_operario = %s
            """,
            [int(id_mpr_parte), int(id_articulo), int(id_operario)],
        )
        row = cursor.fetchone()
        if not row:
            return None
        return ParteLineaRecord(
            id_articulo=int(row["id_articulo"]),
            id_operario=int(row["id_operario"]),
            cantidad=to_decimal_or_none(row.get("cantidad")) or Decimal("0"),
            operario_nombre=str_or_default(row.get("operario_nombre"), "-"),
        )


def sum_ajustes_linea(
    base_empresa: str,
    id_mpr_parte: int,
    id_articulo: int,
    id_operario: int,
) -> Decimal:
    base = (base_empresa or "").strip()
    with mysql_cursor(base, dict_cursor=True) as cursor:
        cursor.execute(
            """
            SELECT COALESCE(SUM(delta), 0) AS total
            FROM mpr_parte_ajuste
            WHERE id_mpr_parte = %s AND id_articulo = %s AND id_operario = %s
            """,
            [int(id_mpr_parte), int(id_articulo), int(id_operario)],
        )
        row = cursor.fetchone()
        return to_decimal_or_none(row.get("total") if row else None) or Decimal("0")


def crear_parte_con_lineas(
    base_empresa: str,
    fecha_produccion: date,
    id_mpr_turno: int,
    id_usuario: int,
    lineas: List[Dict[str, Any]],
    notas: str = "",
    id_lista_produccion: Optional[int] = None,
    uuid_parte: Optional[str] = None,
) -> ParteRecord:
    base = (base_empresa or "").strip()
    uid = str(uuid_parte or uuid.uuid4())
    with mysql_cursor(base) as cursor:
        cursor.execute(
            """
            INSERT INTO mpr_parte
                (uuid_parte, fecha_produccion, id_mpr_turno, id_usuario, notas,
                 movimiento_fisico_ok, id_lista_produccion)
            VALUES (%s, %s, %s, %s, %s, 0, %s)
            """,
            [
                uid,
                fecha_produccion,
                int(id_mpr_turno),
                int(id_usuario),
                str_or_default(notas, ""),
                to_int_or_none(id_lista_produccion),
            ],
        )
        id_parte = int(cursor.lastrowid)
        for cel in lineas or []:
            id_art = to_int_or_none(cel.get("id_articulo"))
            id_op = to_int_or_none(cel.get("id_operario"))
            cantidad = to_decimal_or_none(cel.get("cantidad"))
            if id_art is None or id_op is None or cantidad is None or cantidad <= 0:
                continue
            id_maq = to_int_or_none(cel.get("id_mpr_maquina"))
            if id_maq is not None:
                cursor.execute(
                    """
                    INSERT INTO mpr_parte_linea
                        (id_mpr_parte, id_articulo, id_operario, operario_nombre, cantidad,
                         id_mpr_maquina, maquina_nombre, cantidad_declarada, cantidad_aprobada, gap, motivo)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 0, NULL)
                    ON DUPLICATE KEY UPDATE
                        cantidad = VALUES(cantidad),
                        operario_nombre = VALUES(operario_nombre),
                        maquina_nombre = VALUES(maquina_nombre),
                        cantidad_declarada = VALUES(cantidad_declarada),
                        cantidad_aprobada = VALUES(cantidad_aprobada),
                        gap = 0,
                        motivo = NULL
                    """,
                    [
                        id_parte,
                        id_art,
                        id_op,
                        str_or_default(cel.get("operario_nombre"), "-"),
                        cantidad,
                        id_maq,
                        str_or_default(cel.get("maquina_nombre"), "-"),
                        cantidad,
                        cantidad,
                    ],
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO mpr_parte_linea
                        (id_mpr_parte, id_articulo, id_operario, operario_nombre, cantidad)
                    VALUES (%s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        cantidad = VALUES(cantidad),
                        operario_nombre = VALUES(operario_nombre)
                    """,
                    [
                        id_parte,
                        id_art,
                        id_op,
                        str_or_default(cel.get("operario_nombre"), "-"),
                        cantidad,
                    ],
                )
    parte = obtener_parte_por_pk(base, uid, with_relations=True)
    if parte is None:
        raise RuntimeError("No se pudo leer el parte recién creado.")
    return parte


def actualizar_parte_record(
    base_empresa: str,
    parte: ParteRecord,
    update_fields=None,
) -> None:
    base = (base_empresa or "").strip()
    fields = set(update_fields or [])
    sets: List[str] = []
    params: List[Any] = []
    if "id_lista_produccion" in fields:
        sets.append("id_lista_produccion = %s")
        params.append(to_int_or_none(parte.id_lista_produccion))
    if "movimiento_fisico_ok" in fields:
        sets.append("movimiento_fisico_ok = %s")
        params.append(1 if parte.movimiento_fisico_ok else 0)
    if "notas" in fields:
        sets.append("notas = %s")
        params.append(str_or_default(parte.notas, ""))
    if not sets:
        return
    params.append(parte.id_mpr_parte)
    with mysql_cursor(base) as cursor:
        cursor.execute(
            f"UPDATE mpr_parte SET {', '.join(sets)} WHERE id_mpr_parte = %s",
            params,
        )


def crear_ajuste(
    base_empresa: str,
    id_mpr_parte: int,
    id_articulo: int,
    id_operario: int,
    delta: Decimal,
    motivo: str,
    id_usuario: int,
    uuid_ajuste: Optional[str] = None,
) -> ParteAjusteRecord:
    base = (base_empresa or "").strip()
    uid = str(uuid_ajuste or uuid.uuid4())
    with mysql_cursor(base) as cursor:
        cursor.execute(
            """
            INSERT INTO mpr_parte_ajuste
                (uuid_ajuste, id_mpr_parte, id_articulo, id_operario, delta, motivo,
                 id_usuario, ajuste_fisico_ok)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 0)
            """,
            [
                uid,
                int(id_mpr_parte),
                int(id_articulo),
                int(id_operario),
                delta,
                str_or_default(motivo, "-"),
                int(id_usuario),
            ],
        )
        id_aj = int(cursor.lastrowid)
    return ParteAjusteRecord(
        id_mpr_parte_ajuste=id_aj,
        uuid_ajuste=uid,
        id_mpr_parte=int(id_mpr_parte),
        id_articulo=int(id_articulo),
        id_operario=int(id_operario),
        delta=delta,
        motivo=str_or_default(motivo, "-"),
        id_usuario=int(id_usuario),
        registrado_en=datetime.now(),
        ajuste_fisico_ok=False,
        base_empresa=base,
    )


def actualizar_ajuste_fisico_ok(
    base_empresa: str,
    id_mpr_parte_ajuste: int,
    ok: bool,
) -> None:
    base = (base_empresa or "").strip()
    with mysql_cursor(base) as cursor:
        cursor.execute(
            "UPDATE mpr_parte_ajuste SET ajuste_fisico_ok = %s WHERE id_mpr_parte_ajuste = %s",
            [1 if ok else 0, int(id_mpr_parte_ajuste)],
        )


def eliminar_ajuste(base_empresa: str, id_mpr_parte_ajuste: int) -> None:
    base = (base_empresa or "").strip()
    with mysql_cursor(base) as cursor:
        cursor.execute(
            "DELETE FROM mpr_parte_ajuste WHERE id_mpr_parte_ajuste = %s",
            [int(id_mpr_parte_ajuste)],
        )


def _pares_a_docenas_pares(total: Decimal) -> Tuple[int, int]:
    """Descompone pares equivalentes en docenas enteras + pares sueltos (×12)."""
    entero = int(total or 0)
    if entero < 0:
        entero = 0
    return entero // 12, entero % 12


def obtener_parte_planilla_directo_supervisor(
    base_empresa: str,
    fecha: date,
    id_mpr_turno: int,
) -> Optional[Dict[str, Any]]:
    """Documento upsert planilla supervisor para (fecha, turno, origen directo).

    Si existen varios partes legacy apilados, devuelve el más reciente (id_mpr_parte DESC).
    El próximo guardado debe consolidarlos vía ``crear_o_actualizar_parte_planilla``.
    """
    base = (base_empresa or "").strip()
    tid = to_int_or_none(id_mpr_turno)
    if not base or fecha is None or tid is None:
        return None
    with mysql_cursor(base, dict_cursor=True) as cursor:
        cursor.execute(
            """
            SELECT id_mpr_parte, uuid_parte, estado, movimiento_fisico_ok, notas
            FROM mpr_parte
            WHERE fecha_produccion = %s AND id_mpr_turno = %s AND origen = %s
            ORDER BY id_mpr_parte DESC
            LIMIT 1
            """,
            [fecha, tid, ORIGEN_DIRECTO_SUPERVISOR],
        )
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "id_mpr_parte": int(row["id_mpr_parte"]),
            "uuid_parte": row.get("uuid_parte"),
            "estado": str(row.get("estado") or ""),
            "movimiento_fisico_ok": bool(row.get("movimiento_fisico_ok", 0)),
            "notas": str_or_default(row.get("notas"), ""),
        }


def tiene_parte_maquina_articulo_fecha(
    base_empresa: str,
    fecha: date,
    id_mpr_maquina: int,
    id_articulo: int,
) -> bool:
    """True si existe alguna línea de parte en esa fecha para máquina×artículo."""
    base = (base_empresa or "").strip()
    mid = to_int_or_none(id_mpr_maquina)
    aid = to_int_or_none(id_articulo)
    if not base or fecha is None or mid is None or aid is None:
        return False
    with mysql_cursor(base, dict_cursor=True) as cursor:
        cursor.execute(
            """
            SELECT 1
            FROM mpr_parte p
            INNER JOIN mpr_parte_linea pl ON pl.id_mpr_parte = p.id_mpr_parte
            WHERE p.fecha_produccion = %s
              AND pl.id_mpr_maquina = %s
              AND pl.id_articulo = %s
            LIMIT 1
            """,
            [fecha, mid, aid],
        )
        return cursor.fetchone() is not None


def fecha_planilla_tiene_parte_aprobado(base_empresa: str, fecha: date) -> bool:
    """True si el documento upsert del día (algún turno) ya está aprobado.

    Por cada turno se toma el parte más reciente (``id_mpr_parte`` DESC), igual
    que ``obtener_parte_planilla_directo_supervisor``. Si alguno está
    ``aprobado``, el día ya no admite volver a borrador (correcciones vía aprobar/delta).
    """
    base = (base_empresa or "").strip()
    if not base or fecha is None:
        return False
    vistos_turno: set[int] = set()
    with mysql_cursor(base, dict_cursor=True) as cursor:
        cursor.execute(
            """
            SELECT id_mpr_turno, estado
            FROM mpr_parte
            WHERE fecha_produccion = %s AND origen = %s
            ORDER BY id_mpr_parte DESC
            """,
            [fecha, ORIGEN_DIRECTO_SUPERVISOR],
        )
        for row in cursor.fetchall() or []:
            tid = to_int_or_none(row.get("id_mpr_turno"))
            if tid is None or tid in vistos_turno:
                continue
            vistos_turno.add(tid)
            if str(row.get("estado") or "").strip().lower() == "aprobado":
                return True
    return False


def sumar_cantidades_aprobadas_por_articulo(
    base_empresa: str,
    id_mpr_parte: int,
) -> Dict[int, Decimal]:
    """Suma cantidades efectivas aprobadas por artículo en un parte planilla."""
    base = (base_empresa or "").strip()
    pid = to_int_or_none(id_mpr_parte)
    if not base or pid is None:
        return {}
    acum: Dict[int, Decimal] = {}
    with mysql_cursor(base, dict_cursor=True) as cursor:
        cursor.execute(
            """
            SELECT id_articulo, cantidad, cantidad_aprobada, cantidad_declarada
            FROM mpr_parte_linea
            WHERE id_mpr_parte = %s
            """,
            [pid],
        )
        for row in cursor.fetchall() or []:
            aid = to_int_or_none(row.get("id_articulo"))
            if aid is None:
                continue
            aprob = to_decimal_or_none(row.get("cantidad_aprobada"))
            if aprob is None:
                aprob = to_decimal_or_none(row.get("cantidad")) or Decimal("0")
            if aprob <= 0:
                continue
            acum[aid] = acum.get(aid, Decimal("0")) + aprob
    return acum


def _insertar_lineas_planilla(
    cursor,
    id_parte: int,
    lineas: List[Dict[str, Any]],
    *,
    es_borrador: bool,
) -> None:
    for cel in lineas or []:
        id_art = to_int_or_none(cel.get("id_articulo"))
        id_op = to_int_or_none(cel.get("id_operario"))
        id_maq = to_int_or_none(cel.get("id_mpr_maquina"))
        cantidad = to_decimal_or_none(cel.get("cantidad"))
        if (
            id_art is None
            or id_op is None
            or id_maq is None
            or cantidad is None
            or cantidad <= 0
        ):
            continue
        if es_borrador:
            cursor.execute(
                """
                INSERT INTO mpr_parte_linea
                    (id_mpr_parte, id_articulo, id_operario, operario_nombre, cantidad,
                     id_mpr_maquina, maquina_nombre, cantidad_declarada, cantidad_aprobada, gap, motivo)
                VALUES (%s, %s, %s, %s, 0, %s, %s, %s, NULL, 0, NULL)
                """,
                [
                    int(id_parte),
                    id_art,
                    id_op,
                    str_or_default(cel.get("operario_nombre"), "-"),
                    id_maq,
                    str_or_default(cel.get("maquina_nombre"), "-"),
                    cantidad,
                ],
            )
        else:
            cursor.execute(
                """
                INSERT INTO mpr_parte_linea
                    (id_mpr_parte, id_articulo, id_operario, operario_nombre, cantidad,
                     id_mpr_maquina, maquina_nombre, cantidad_declarada, cantidad_aprobada, gap, motivo)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 0, NULL)
                """,
                [
                    int(id_parte),
                    id_art,
                    id_op,
                    str_or_default(cel.get("operario_nombre"), "-"),
                    cantidad,
                    id_maq,
                    str_or_default(cel.get("maquina_nombre"), "-"),
                    cantidad,
                    cantidad,
                ],
            )


def crear_o_actualizar_parte_planilla(
    base_empresa: str,
    fecha_produccion: date,
    id_mpr_turno: int,
    id_usuario: int,
    lineas: List[Dict[str, Any]],
    *,
    notas: str = "",
    estado: str = "borrador",
    id_usuario_supervisor: int = 0,
) -> ParteRecord:
    """Upsert planilla desktop: un ``mpr_parte`` por (fecha, turno, origen directo).

    Reemplaza las líneas por completo (delete + reinsert). Estados:
    - ``borrador``: cantidad_declarada, cantidad física 0.
    - ``aprobado``: cantidad = cantidad_aprobada = cantidad_declarada.
    """
    base = (base_empresa or "").strip()
    tid = to_int_or_none(id_mpr_turno)
    if not base or fecha_produccion is None or tid is None:
        raise ValueError("Parámetros inválidos para upsert planilla.")

    estado_norm = "aprobado" if str(estado or "").strip().lower() == "aprobado" else "borrador"
    es_borrador = estado_norm == "borrador"
    existente = obtener_parte_planilla_directo_supervisor(base, fecha_produccion, tid)

    if es_borrador and existente:
        if str(existente.get("estado") or "").strip().lower() == "aprobado":
            raise ValueError(
                "El parte de esta fecha ya está aprobado. "
                "Para corregir cantidades usá «Guardar parte de producción»."
            )

    with mysql_cursor(base) as cursor:
        if existente:
            id_parte = int(existente["id_mpr_parte"])
            uid = existente.get("uuid_parte") or str(uuid.uuid4())
            if es_borrador:
                cursor.execute(
                    """
                    UPDATE mpr_parte
                    SET estado = %s, notas = %s, movimiento_fisico_ok = 0,
                        id_usuario_supervisor = NULL, aprobado_en = NULL
                    WHERE id_mpr_parte = %s
                    """,
                    [estado_norm, str_or_default(notas, ""), id_parte],
                )
            else:
                cursor.execute(
                    """
                    UPDATE mpr_parte
                    SET estado = %s, notas = %s, id_usuario_supervisor = %s, aprobado_en = %s
                    WHERE id_mpr_parte = %s
                    """,
                    [
                        estado_norm,
                        str_or_default(notas, ""),
                        to_int_or_none(id_usuario_supervisor) or 0,
                        datetime.now(),
                        id_parte,
                    ],
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
                    tid,
                    to_int_or_none(id_usuario) or 0,
                    str_or_default(notas, ""),
                    estado_norm,
                    ORIGEN_DIRECTO_SUPERVISOR,
                ],
            )
            id_parte = int(cursor.lastrowid)
        _insertar_lineas_planilla(cursor, id_parte, lineas, es_borrador=es_borrador)

    parte = obtener_parte_por_pk(base, uid, with_relations=True)
    if parte is None:
        raise RuntimeError("No se pudo leer el parte planilla tras upsert.")
    return parte


def precarga_planilla_por_fecha(
    base_empresa: str,
    fecha: date,
) -> Dict[Tuple[int, int, int], Dict[str, Optional[int]]]:
    """
    Cantidades y operario precargados por (id_mpr_maquina, id_articulo, id_mpr_turno).

    Usa partes con ``origen='directo_supervisor'`` (documento upsert del día).
    Parte aprobado → cantidad_aprobada; otro estado → cantidad_declarada.
    Solo líneas con id_mpr_maquina no null.

    Si existen varios partes legacy apilados por turno, suma sus cantidades una
    sola vez en precarga; el próximo guardado debe consolidarlos en un único
    documento por turno vía ``crear_o_actualizar_parte_planilla``.
    """
    base = (base_empresa or "").strip()
    if not base or fecha is None:
        return {}
    resultado: Dict[Tuple[int, int, int], Dict[str, Optional[int]]] = {}
    with mysql_cursor(base, dict_cursor=True) as cursor:
        cursor.execute(
            """
            SELECT pl.id_mpr_maquina, pl.id_articulo, pl.id_operario, p.id_mpr_turno, p.estado,
                   pl.cantidad_declarada, pl.cantidad_aprobada
            FROM mpr_parte p
            INNER JOIN mpr_parte_linea pl ON pl.id_mpr_parte = p.id_mpr_parte
            WHERE p.fecha_produccion = %s
              AND p.origen = %s
              AND pl.id_mpr_maquina IS NOT NULL
            """,
            [fecha, ORIGEN_DIRECTO_SUPERVISOR],
        )
        for row in cursor.fetchall() or []:
            mid = to_int_or_none(row.get("id_mpr_maquina"))
            aid = to_int_or_none(row.get("id_articulo"))
            tid = to_int_or_none(row.get("id_mpr_turno"))
            if mid is None or aid is None or tid is None:
                continue
            estado = str(row.get("estado") or "").strip().lower()
            if estado == "aprobado":
                cant = to_decimal_or_none(row.get("cantidad_aprobada")) or Decimal("0")
            else:
                cant = to_decimal_or_none(row.get("cantidad_declarada")) or Decimal("0")
            if cant <= 0:
                continue
            clave = (mid, aid, tid)
            prev = resultado.get(clave, {"docenas": 0, "pares": 0, "id_operario": None})
            doc, par = _pares_a_docenas_pares(cant)
            prev_doc, prev_par = _pares_a_docenas_pares(
                Decimal(prev["docenas"] * 12 + prev["pares"])
            )
            total = Decimal(prev_doc * 12 + prev_par) + cant
            d, p = _pares_a_docenas_pares(total)
            id_operario = to_int_or_none(row.get("id_operario"))
            # La planilla tiene un operario por celda. Si existe legado con más
            # de uno, no se preselecciona ninguno para no representar un dato falso.
            if prev.get("id_operario") not in (None, id_operario):
                id_operario = None
            resultado[clave] = {"docenas": d, "pares": p, "id_operario": id_operario}
    return resultado


def acumular_celdas_grilla(
    base_empresa: str,
    fecha: date,
    id_mpr_turno: int,
) -> Dict[Tuple[int, int], Decimal]:
    """Cantidades efectivas por (id_articulo, id_operario) para fecha+turno."""
    base = (base_empresa or "").strip()
    celdas: Dict[Tuple[int, int], Decimal] = {}
    with mysql_cursor(base, dict_cursor=True) as cursor:
        cursor.execute(
            """
            SELECT p.id_mpr_parte FROM mpr_parte p
            WHERE p.fecha_produccion = %s AND p.id_mpr_turno = %s
            """,
            [fecha, int(id_mpr_turno)],
        )
        parte_ids = [int(r["id_mpr_parte"]) for r in (cursor.fetchall() or [])]
        for pid in parte_ids:
            cursor.execute(
                """
                SELECT id_articulo, id_operario, cantidad
                FROM mpr_parte_linea WHERE id_mpr_parte = %s
                """,
                [pid],
            )
            lineas = cursor.fetchall() or []
            ajustes_map: Dict[Tuple[int, int], Decimal] = {}
            cursor.execute(
                """
                SELECT id_articulo, id_operario, delta
                FROM mpr_parte_ajuste WHERE id_mpr_parte = %s
                """,
                [pid],
            )
            for aj in cursor.fetchall() or []:
                clave = (int(aj["id_articulo"]), int(aj["id_operario"]))
                ajustes_map[clave] = ajustes_map.get(clave, Decimal("0")) + (
                    to_decimal_or_none(aj.get("delta")) or Decimal("0")
                )
            for ln in lineas:
                clave = (int(ln["id_articulo"]), int(ln["id_operario"]))
                base_qty = to_decimal_or_none(ln.get("cantidad")) or Decimal("0")
                efectiva = base_qty + ajustes_map.get(clave, Decimal("0"))
                celdas[clave] = celdas.get(clave, Decimal("0")) + efectiva
    return celdas


def acumular_celdas_grilla_con_nombre(
    base_empresa: str,
    fecha: date,
    id_mpr_turno: int,
) -> Dict[Tuple[int, int], Dict[str, Any]]:
    """Cantidades y nombre por (id_articulo, id_operario) para fecha+turno."""
    base = (base_empresa or "").strip()
    resultado: Dict[Tuple[int, int], Dict[str, Any]] = {}
    celdas = acumular_celdas_grilla(base_empresa, fecha, id_mpr_turno)
    if not celdas:
        return resultado
    with mysql_cursor(base, dict_cursor=True) as cursor:
        cursor.execute(
            """
            SELECT p.id_mpr_parte FROM mpr_parte p
            WHERE p.fecha_produccion = %s AND p.id_mpr_turno = %s
            """,
            [fecha, int(id_mpr_turno)],
        )
        parte_ids = [int(r["id_mpr_parte"]) for r in (cursor.fetchall() or [])]
        nombres: Dict[Tuple[int, int], str] = {}
        for pid in parte_ids:
            cursor.execute(
                """
                SELECT id_articulo, id_operario, operario_nombre
                FROM mpr_parte_linea WHERE id_mpr_parte = %s
                """,
                [pid],
            )
            for ln in cursor.fetchall() or []:
                clave = (int(ln["id_articulo"]), int(ln["id_operario"]))
                nom = str_or_default(ln.get("operario_nombre"), "-").strip()
                if nom and nom != "-":
                    nombres[clave] = nom
    for clave, cantidad in celdas.items():
        resultado[clave] = {
            "cantidad": cantidad,
            "operario_nombre": nombres.get(clave, "-"),
        }
    return resultado


def acumular_celdas_clasificacion_maquina_turno(
    base_empresa: str,
    fecha: date,
    id_mpr_turno: Optional[int] = None,
) -> Dict[Tuple[int, int, int, int], Dict[str, Any]]:
    """Cantidades efectivas por (id_mpr_maquina|0, id_articulo, id_operario, id_mpr_turno).

    Lee partes de la fecha (y turno si se indica). Líneas sin máquina → id_mpr_maquina=0,
    maquina_nombre «—». Los ajustes por (artículo, operario) se suman al bucket de máquina
    con mayor cantidad en ese parte, o a máquina 0 si no hay líneas.
    """
    base = (base_empresa or "").strip()
    resultado: Dict[Tuple[int, int, int, int], Dict[str, Any]] = {}
    if not base or fecha is None:
        return resultado

    params: List[Any] = [fecha]
    filtro_turno = ""
    if id_mpr_turno is not None:
        filtro_turno = " AND p.id_mpr_turno = %s"
        params.append(int(id_mpr_turno))

    with mysql_cursor(base, dict_cursor=True) as cursor:
        cursor.execute(
            f"""
            SELECT p.id_mpr_parte, p.id_mpr_turno, t.nombre AS turno_nombre
            FROM mpr_parte p
            INNER JOIN mpr_turno t ON t.id_mpr_turno = p.id_mpr_turno
            WHERE p.fecha_produccion = %s{filtro_turno}
            """,
            params,
        )
        partes = cursor.fetchall() or []

        for parte in partes:
            pid = to_int_or_none(parte.get("id_mpr_parte"))
            tid = to_int_or_none(parte.get("id_mpr_turno"))
            turno_nombre = str_or_default(parte.get("turno_nombre"), "-")
            if pid is None or tid is None:
                continue

            cursor.execute(
                """
                SELECT id_articulo, id_operario, operario_nombre, cantidad,
                       id_mpr_maquina, maquina_nombre
                FROM mpr_parte_linea
                WHERE id_mpr_parte = %s
                """,
                [pid],
            )
            lineas = cursor.fetchall() or []
            ajustes_map: Dict[Tuple[int, int], Decimal] = {}
            cursor.execute(
                """
                SELECT id_articulo, id_operario, delta
                FROM mpr_parte_ajuste
                WHERE id_mpr_parte = %s
                """,
                [pid],
            )
            for aj in cursor.fetchall() or []:
                aid = to_int_or_none(aj.get("id_articulo"))
                oid = to_int_or_none(aj.get("id_operario"))
                if aid is None or oid is None:
                    continue
                clave_aj = (aid, oid)
                ajustes_map[clave_aj] = ajustes_map.get(clave_aj, Decimal("0")) + (
                    to_decimal_or_none(aj.get("delta")) or Decimal("0")
                )

            qty_por_clave: Dict[Tuple[int, int, int, int], Decimal] = {}
            meta_por_clave: Dict[Tuple[int, int, int, int], Dict[str, Any]] = {}

            for ln in lineas:
                aid = to_int_or_none(ln.get("id_articulo"))
                oid = to_int_or_none(ln.get("id_operario"))
                if aid is None or oid is None:
                    continue
                mid = to_int_or_none(ln.get("id_mpr_maquina")) or 0
                maq_nom = (
                    str_or_default(ln.get("maquina_nombre"), "-").strip()
                    if mid > 0
                    else "—"
                )
                if mid > 0 and (not maq_nom or maq_nom == "-"):
                    maq_nom = "—"
                qty = to_decimal_or_none(ln.get("cantidad")) or Decimal("0")
                clave = (mid, aid, oid, tid)
                qty_por_clave[clave] = qty_por_clave.get(clave, Decimal("0")) + qty
                prev = meta_por_clave.get(clave, {})
                nom_op = str_or_default(ln.get("operario_nombre"), "-").strip()
                meta_por_clave[clave] = {
                    "operario_nombre": nom_op if nom_op else prev.get("operario_nombre", "-"),
                    "maquina_nombre": maq_nom,
                    "turno_nombre": turno_nombre,
                    "id_mpr_turno": tid,
                }

            for (aid, oid), delta in ajustes_map.items():
                if delta == 0:
                    continue
                candidatos = [
                    k for k in qty_por_clave
                    if k[1] == aid and k[2] == oid and k[3] == tid
                ]
                if candidatos:
                    dest = max(candidatos, key=lambda k: qty_por_clave[k])
                else:
                    dest = (0, aid, oid, tid)
                    meta_por_clave.setdefault(
                        dest,
                        {
                            "operario_nombre": "-",
                            "maquina_nombre": "—",
                            "turno_nombre": turno_nombre,
                            "id_mpr_turno": tid,
                        },
                    )
                qty_por_clave[dest] = qty_por_clave.get(dest, Decimal("0")) + delta

            for clave, cantidad in qty_por_clave.items():
                if cantidad == 0:
                    continue
                meta = meta_por_clave.get(clave, {})
                prev = resultado.get(clave, {})
                resultado[clave] = {
                    "cantidad": (to_decimal_or_none(prev.get("cantidad")) or Decimal("0")) + cantidad,
                    "operario_nombre": meta.get("operario_nombre")
                    or prev.get("operario_nombre")
                    or "-",
                    "maquina_nombre": meta.get("maquina_nombre")
                    or prev.get("maquina_nombre")
                    or "—",
                    "turno_nombre": meta.get("turno_nombre")
                    or prev.get("turno_nombre")
                    or turno_nombre,
                    "id_mpr_turno": tid,
                }

    return resultado


def listar_partes_consulta(
    base_empresa: str,
    *,
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    estado: Optional[str] = None,
    id_usuario: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Listado de partes para la pantalla Consulta de partes (MySQL mpr_parte)."""
    base = (base_empresa or "").strip()
    if not base:
        return []

    where = ["1=1"]
    params: List[Any] = []
    if fecha_desde is not None:
        where.append("p.fecha_produccion >= %s")
        params.append(fecha_desde)
    if fecha_hasta is not None:
        where.append("p.fecha_produccion <= %s")
        params.append(fecha_hasta)
    estado_norm = (estado or "").strip().lower()
    if estado_norm:
        where.append("p.estado = %s")
        params.append(estado_norm)
    uid = to_int_or_none(id_usuario)
    if uid is not None:
        where.append("p.id_usuario = %s")
        params.append(uid)

    with mysql_cursor(base, dict_cursor=True) as cursor:
        join_usuarios = ""
        expr_usuario = "CAST(p.id_usuario AS CHAR)"
        try:
            cursor.execute("SHOW TABLES LIKE 'usuarios'")
            if cursor.fetchone():
                join_usuarios = (
                    " LEFT JOIN usuarios u ON u.id_usuario = p.id_usuario "
                )
                expr_usuario = (
                    "COALESCE(NULLIF(TRIM(CONCAT(COALESCE(u.nombre_usuario, ''), ' ', "
                    "COALESCE(u.apellido_usuario, ''))), ''), "
                    "NULLIF(TRIM(COALESCE(u.cod_usuario, '')), ''), "
                    "CAST(p.id_usuario AS CHAR))"
                )
        except Exception:
            join_usuarios = ""
            expr_usuario = "CAST(p.id_usuario AS CHAR)"

        cursor.execute(
            f"""
            SELECT p.id_mpr_parte, p.fecha_produccion, p.id_mpr_turno, p.origen, p.estado,
                   p.id_usuario, p.registrado_en, t.nombre AS turno_nombre,
                   MAX({expr_usuario}) AS usuario_nombre,
                   COALESCE(SUM(
                       CASE
                           WHEN LOWER(COALESCE(p.estado, '')) = 'aprobado'
                               THEN COALESCE(pl.cantidad_aprobada, pl.cantidad, 0)
                           ELSE COALESCE(pl.cantidad_declarada, pl.cantidad, 0)
                       END
                   ), 0) AS total_pares
            FROM mpr_parte p
            LEFT JOIN mpr_turno t ON t.id_mpr_turno = p.id_mpr_turno
            LEFT JOIN mpr_parte_linea pl ON pl.id_mpr_parte = p.id_mpr_parte
            {join_usuarios}
            WHERE {' AND '.join(where)}
            GROUP BY p.id_mpr_parte, p.fecha_produccion, p.id_mpr_turno, p.origen, p.estado,
                     p.id_usuario, p.registrado_en, t.nombre
            ORDER BY p.fecha_produccion DESC, p.id_mpr_turno DESC, p.id_mpr_parte DESC
            """,
            params,
        )
        out: List[Dict[str, Any]] = []
        for r in cursor.fetchall() or []:
            # to_date_or_none → 'YYYY-MM-DD' (str) o None; no es date/datetime.
            fp_iso = to_date_or_none(r.get("fecha_produccion"))
            fecha_str = ""
            if fp_iso:
                try:
                    fecha_str = datetime.strptime(fp_iso, "%Y-%m-%d").strftime("%d/%m/%Y")
                except (ValueError, TypeError):
                    fecha_str = ""
            out.append(
                {
                    "id_parte": int(r["id_mpr_parte"]),
                    "fecha_produccion": fp_iso,
                    "fecha_str": fecha_str,
                    "id_mpr_turno": to_int_or_none(r.get("id_mpr_turno")),
                    "turno_nombre": str_or_default(r.get("turno_nombre"), "-"),
                    "origen": str(r.get("origen") or ""),
                    "estado": str(r.get("estado") or ""),
                    "id_usuario": to_int_or_none(r.get("id_usuario")) or 0,
                    "usuario_nombre": str_or_default(r.get("usuario_nombre"), "-"),
                    "total_pares": float(
                        to_decimal_or_none(r.get("total_pares")) or Decimal("0")
                    ),
                    "registrado_en": r.get("registrado_en"),
                }
            )
        return out


def listar_partes_trazabilidad(
    base_empresa: str,
    id_lista_produccion: int,
) -> List[ParteRecord]:
    base = (base_empresa or "").strip()
    with mysql_cursor(base, dict_cursor=True) as cursor:
        cursor.execute(
            """
            SELECT id_mpr_parte, uuid_parte, fecha_produccion, id_mpr_turno, id_usuario,
                   registrado_en, notas, movimiento_fisico_ok, id_lista_produccion
            FROM mpr_parte
            WHERE id_lista_produccion = %s
            ORDER BY registrado_en
            """,
            [int(id_lista_produccion)],
        )
        rows = cursor.fetchall() or []
    return [
        _row_to_parte(base, row, with_relations=True)
        for row in rows
    ]


def operario_tiene_parte_fecha_turno(
    base_empresa: str,
    fecha: date,
    id_operario: int,
    id_mpr_turno: int,
) -> bool:
    """True si existe al menos una línea de parte para operario+fecha+turno (cualquier estado)."""
    base = (base_empresa or "").strip()
    oid = to_int_or_none(id_operario)
    tid = to_int_or_none(id_mpr_turno)
    f_prod = to_date_or_none(fecha)
    if not base or oid is None or tid is None or f_prod is None:
        return False
    with mysql_cursor(base, dict_cursor=True) as cursor:
        cursor.execute(
            """
            SELECT 1
            FROM mpr_parte p
            INNER JOIN mpr_parte_linea pl ON pl.id_mpr_parte = p.id_mpr_parte
            WHERE p.fecha_produccion = %s
              AND p.id_mpr_turno = %s
              AND pl.id_operario = %s
            LIMIT 1
            """,
            [f_prod, tid, oid],
        )
        return cursor.fetchone() is not None


def operario_estado_produccion_roster(
    base_empresa: str,
    fecha: date,
    id_operario: int,
    id_mpr_turno: int,
) -> Dict[str, bool]:
    """Estado de líneas de parte para decidir una edición de roster.

    Las líneas de borrador/pendiente no constituyen un bloqueo: pueden migrarse
    al reasignar el turno. Una parte aprobada o con movimiento físico sí bloquea
    cualquier cambio, porque su ledger ya representa producción consolidada.
    """
    estado = {
        "tiene_lineas": False,
        "tiene_aprobado_o_fisico": False,
        "tiene_borrador_o_pendiente": False,
    }
    base = (base_empresa or "").strip()
    oid = to_int_or_none(id_operario)
    tid = to_int_or_none(id_mpr_turno)
    f_prod = to_date_or_none(fecha)
    if not base or oid is None or tid is None or f_prod is None:
        return estado
    with mysql_cursor(base, dict_cursor=True) as cursor:
        cursor.execute(
            """
            SELECT LOWER(COALESCE(p.estado, '')) AS estado,
                   COALESCE(p.movimiento_fisico_ok, 0) AS movimiento_fisico_ok
            FROM mpr_parte p
            INNER JOIN mpr_parte_linea pl ON pl.id_mpr_parte = p.id_mpr_parte
            WHERE p.fecha_produccion = %s
              AND p.id_mpr_turno = %s
              AND pl.id_operario = %s
            """,
            [f_prod, tid, oid],
        )
        for row in cursor.fetchall() or []:
            estado["tiene_lineas"] = True
            nombre_estado = str_or_default(row.get("estado"), "").strip().lower()
            if nombre_estado == "aprobado" or bool(row.get("movimiento_fisico_ok")):
                estado["tiene_aprobado_o_fisico"] = True
            elif nombre_estado in {"borrador", "pendiente"}:
                estado["tiene_borrador_o_pendiente"] = True
            else:
                # Un estado desconocido no puede migrarse de manera segura.
                estado["tiene_aprobado_o_fisico"] = True
    return estado


def set_operarios_bloqueados_roster_en_rango(
    base_empresa: str,
    fecha_desde: date,
    fecha_hasta: date,
) -> set:
    """Celdas con parte aprobada o movimiento físico para el candado del roster."""
    base = (base_empresa or "").strip()
    f_desde = to_date_or_none(fecha_desde)
    f_hasta = to_date_or_none(fecha_hasta)
    if not base or f_desde is None or f_hasta is None:
        return set()
    resultado: set = set()
    with mysql_cursor(base, dict_cursor=True) as cursor:
        cursor.execute(
            """
            SELECT DISTINCT pl.id_operario, p.fecha_produccion, p.id_mpr_turno
            FROM mpr_parte p
            INNER JOIN mpr_parte_linea pl ON pl.id_mpr_parte = p.id_mpr_parte
            WHERE p.fecha_produccion BETWEEN %s AND %s
              AND (
                  LOWER(COALESCE(p.estado, '')) = 'aprobado'
                  OR COALESCE(p.movimiento_fisico_ok, 0) = 1
              )
            """,
            [f_desde, f_hasta],
        )
        for row in cursor.fetchall() or []:
            oid = to_int_or_none(row.get("id_operario"))
            f_prod = to_date_or_none(row.get("fecha_produccion"))
            tid = to_int_or_none(row.get("id_mpr_turno"))
            if oid is not None and f_prod is not None and tid is not None:
                resultado.add((oid, f_prod, tid))
    return resultado


def migrar_lineas_operario_entre_turnos(
    base_empresa: str,
    fecha: date,
    id_operario: int,
    id_turno_origen: int,
    id_turno_destino: int,
) -> Tuple[bool, Optional[str], Dict[str, int]]:
    """Mueve el ledger no físico de un operario a otro turno de la misma fecha.

    La transacción solo reasigna/combina filas de ``mpr_parte_linea`` y ajustes
    no físicos. No invoca MSTOCK ni modifica ``mpr_transicion_lote``.
    """
    base = (base_empresa or "").strip()
    oid = to_int_or_none(id_operario)
    origen = to_int_or_none(id_turno_origen)
    destino = to_int_or_none(id_turno_destino)
    f_prod = to_date_or_none(fecha)
    resumen = {"lineas_movidas": 0, "lineas_combinadas": 0, "ajustes_movidos": 0, "borradores_cc_movidos": 0}
    if not base or oid is None or origen is None or destino is None or f_prod is None:
        return False, "Datos inválidos para migrar el parte.", resumen
    if origen == destino:
        return True, None, resumen

    try:
        with get_mysql_connection(base) as conn:
            conn.autocommit(False)
            cursor = conn.cursor(MySQLdb.cursors.DictCursor)
            try:
                cursor.execute(
                    """
                    SELECT DISTINCT p.id_mpr_parte, p.id_usuario, p.origen,
                           LOWER(COALESCE(p.estado, '')) AS estado,
                           COALESCE(p.movimiento_fisico_ok, 0) AS movimiento_fisico_ok
                    FROM mpr_parte p
                    INNER JOIN mpr_parte_linea pl ON pl.id_mpr_parte = p.id_mpr_parte
                    WHERE p.fecha_produccion = %s AND p.id_mpr_turno = %s AND pl.id_operario = %s
                    FOR UPDATE
                    """,
                    [f_prod, origen, oid],
                )
                partes_origen = cursor.fetchall() or []
                for parte in partes_origen:
                    if (
                        str_or_default(parte.get("estado"), "").lower() not in {"borrador", "pendiente"}
                        or bool(parte.get("movimiento_fisico_ok"))
                    ):
                        conn.rollback()
                        return False, "No se puede migrar: el parte está aprobado o tiene movimiento físico.", resumen

                for parte in partes_origen:
                    id_parte_origen = to_int_or_none(parte.get("id_mpr_parte"))
                    if id_parte_origen is None:
                        continue
                    cursor.execute(
                        """
                        SELECT id_mpr_parte FROM mpr_parte
                        WHERE fecha_produccion = %s AND id_mpr_turno = %s
                          AND origen = %s AND LOWER(COALESCE(estado, '')) = %s
                        LIMIT 1 FOR UPDATE
                        """,
                        [f_prod, destino, str_or_default(parte.get("origen"), ORIGEN_DIRECTO_SUPERVISOR), parte["estado"]],
                    )
                    existente = cursor.fetchone()
                    if existente:
                        id_parte_destino = to_int_or_none(existente.get("id_mpr_parte"))
                    else:
                        cursor.execute(
                            """
                            INSERT INTO mpr_parte
                                (uuid_parte, fecha_produccion, id_mpr_turno, id_usuario, notas,
                                 movimiento_fisico_ok, estado, origen)
                            VALUES (%s, %s, %s, %s, %s, 0, %s, %s)
                            """,
                            [
                                str(uuid.uuid4()), f_prod, destino,
                                to_int_or_none(parte.get("id_usuario")) or 0, "",
                                parte["estado"], str_or_default(parte.get("origen"), ORIGEN_DIRECTO_SUPERVISOR),
                            ],
                        )
                        id_parte_destino = to_int_or_none(cursor.lastrowid)
                    if id_parte_destino is None:
                        raise RuntimeError("No se pudo crear el parte destino.")

                    cursor.execute(
                        """
                        SELECT * FROM mpr_parte_linea
                        WHERE id_mpr_parte = %s AND id_operario = %s FOR UPDATE
                        """,
                        [id_parte_origen, oid],
                    )
                    for linea in cursor.fetchall() or []:
                        id_linea = to_int_or_none(linea.get("id_mpr_parte_linea"))
                        articulo = to_int_or_none(linea.get("id_articulo"))
                        maquina = to_int_or_none(linea.get("id_mpr_maquina"))
                        if id_linea is None or articulo is None:
                            continue
                        cursor.execute(
                            """
                            SELECT id_mpr_parte_linea FROM mpr_parte_linea
                            WHERE id_mpr_parte = %s AND id_articulo = %s AND id_operario = %s
                              AND (id_mpr_maquina = %s OR (id_mpr_maquina IS NULL AND %s IS NULL))
                            LIMIT 1 FOR UPDATE
                            """,
                            [id_parte_destino, articulo, oid, maquina, maquina],
                        )
                        duplicada = cursor.fetchone()
                        if duplicada:
                            qty_origen = to_decimal_or_none(linea.get("cantidad")) or Decimal("0")
                            # Evitar fusionar cantidades físicas: solo ledger no acreditado.
                            if qty_origen > 0:
                                conn.rollback()
                                return (
                                    False,
                                    "No se puede migrar: hay cantidad física en el parte origen. "
                                    "Evitá riesgo de stock duplicado.",
                                    resumen,
                                )
                            cursor.execute(
                                """
                                SELECT COALESCE(cantidad, 0) AS cantidad
                                FROM mpr_parte_linea
                                WHERE id_mpr_parte_linea = %s
                                FOR UPDATE
                                """,
                                [to_int_or_none(duplicada.get("id_mpr_parte_linea"))],
                            )
                            dest_row = cursor.fetchone() or {}
                            if (to_decimal_or_none(dest_row.get("cantidad")) or Decimal("0")) > 0:
                                conn.rollback()
                                return (
                                    False,
                                    "No se puede migrar: el turno destino ya tiene cantidad física "
                                    "para ese artículo/máquina.",
                                    resumen,
                                )
                            cursor.execute(
                                """
                                UPDATE mpr_parte_linea
                                SET cantidad_declarada = COALESCE(cantidad_declarada, 0) + %s
                                WHERE id_mpr_parte_linea = %s
                                """,
                                [
                                    to_decimal_or_none(linea.get("cantidad_declarada")) or Decimal("0"),
                                    to_int_or_none(duplicada.get("id_mpr_parte_linea")),
                                ],
                            )
                            cursor.execute("DELETE FROM mpr_parte_linea WHERE id_mpr_parte_linea = %s", [id_linea])
                            resumen["lineas_combinadas"] += 1
                        else:
                            qty_origen = to_decimal_or_none(linea.get("cantidad")) or Decimal("0")
                            if qty_origen > 0:
                                conn.rollback()
                                return (
                                    False,
                                    "No se puede migrar: hay cantidad física en el parte origen. "
                                    "Evitá riesgo de stock duplicado.",
                                    resumen,
                                )
                            cursor.execute(
                                "UPDATE mpr_parte_linea SET id_mpr_parte = %s WHERE id_mpr_parte_linea = %s",
                                [id_parte_destino, id_linea],
                            )
                            resumen["lineas_movidas"] += 1

                    cursor.execute(
                        """
                        SELECT id_mpr_parte_ajuste FROM mpr_parte_ajuste
                        WHERE id_mpr_parte = %s AND id_operario = %s
                          AND COALESCE(ajuste_fisico_ok, 0) = 1
                        LIMIT 1 FOR UPDATE
                        """,
                        [id_parte_origen, oid],
                    )
                    if cursor.fetchone():
                        conn.rollback()
                        return False, "No se puede migrar: existe un ajuste con movimiento físico.", resumen
                    cursor.execute(
                        """
                        UPDATE mpr_parte_ajuste SET id_mpr_parte = %s
                        WHERE id_mpr_parte = %s AND id_operario = %s
                          AND COALESCE(ajuste_fisico_ok, 0) = 0
                        """,
                        [id_parte_destino, id_parte_origen, oid],
                    )
                    resumen["ajustes_movidos"] += max(0, cursor.rowcount)

                from mpr.repositories.clasificacion_borrador import migrar_borrador_operario_entre_turnos

                resumen["borradores_cc_movidos"] = migrar_borrador_operario_entre_turnos(
                    base, fecha, oid, origen, destino, cursor=cursor
                )
                conn.commit()
                return True, None, resumen
            except Exception:
                conn.rollback()
                raise
            finally:
                cursor.close()
                conn.autocommit(True)
    except Exception:
        return False, "No se pudieron migrar los datos de producción del operario.", resumen


def set_operarios_con_parte_en_rango(
    base_empresa: str,
    fecha_desde: date,
    fecha_hasta: date,
) -> set:
    """Conjunto de (id_operario, fecha_iso, id_mpr_turno) con parte en el rango."""
    base = (base_empresa or "").strip()
    f_desde = to_date_or_none(fecha_desde)
    f_hasta = to_date_or_none(fecha_hasta)
    if not base or f_desde is None or f_hasta is None:
        return set()
    resultado: set = set()
    with mysql_cursor(base, dict_cursor=True) as cursor:
        cursor.execute(
            """
            SELECT DISTINCT pl.id_operario, p.fecha_produccion, p.id_mpr_turno
            FROM mpr_parte p
            INNER JOIN mpr_parte_linea pl ON pl.id_mpr_parte = p.id_mpr_parte
            WHERE p.fecha_produccion >= %s AND p.fecha_produccion <= %s
            """,
            [f_desde, f_hasta],
        )
        for row in cursor.fetchall() or []:
            oid = to_int_or_none(row.get("id_operario"))
            f_prod = to_date_or_none(row.get("fecha_produccion"))
            tid = to_int_or_none(row.get("id_mpr_turno"))
            if oid is not None and f_prod is not None and tid is not None:
                # to_date_or_none ya normaliza a str YYYY-MM-DD
                resultado.add((oid, f_prod, tid))
    return resultado
