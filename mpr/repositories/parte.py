"""Parte de producción (mpr_parte, mpr_parte_linea, mpr_parte_ajuste)."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from core.utils.administranet_types import (
    str_or_default,
    to_date_or_none,
    to_decimal_or_none,
    to_int_or_none,
)

from mpr.db import mysql_cursor
from mpr.repositories.records import ParteAjusteRecord, ParteLineaRecord, ParteRecord
from mpr.repositories.turno_roster import obtener_turno_record


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
