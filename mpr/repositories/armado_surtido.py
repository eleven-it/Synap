"""Armado surtido y lotes (mpr_armado_*)."""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from core.utils.administranet_types import str_or_default, to_int_or_none

from mpr.db import mysql_cursor
from mpr.repositories.records import ArmadoLoteRecord, ArmadoMovimientoRecord


def crear_lote_armado(
    base_empresa: str,
    modo: str,
    id_operario: Optional[int],
    id_usuario: int,
    deposito_origen: int,
    deposito_destino: int,
    cantidad_items: int,
    uuid_lote: Optional[str] = None,
) -> ArmadoLoteRecord:
    base = (base_empresa or "").strip()
    uid = str(uuid_lote or uuid.uuid4())
    with mysql_cursor(base) as cursor:
        cursor.execute(
            """
            INSERT INTO mpr_armado_lote
                (uuid_lote, modo, id_operario, id_usuario, deposito_origen, deposito_destino,
                 cantidad_items, cantidad_exitosos, cantidad_fallidos)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 0, 0)
            """,
            [
                uid,
                str(modo),
                to_int_or_none(id_operario),
                int(id_usuario),
                int(deposito_origen),
                int(deposito_destino),
                int(cantidad_items),
            ],
        )
        id_lote = int(cursor.lastrowid)
    return ArmadoLoteRecord(
        id_mpr_armado_lote=id_lote,
        uuid_lote=uid,
        modo=str(modo),
        id_operario=to_int_or_none(id_operario),
        id_usuario=int(id_usuario),
        deposito_origen=int(deposito_origen),
        deposito_destino=int(deposito_destino),
        cantidad_items=int(cantidad_items),
        base_empresa=base,
    )


def actualizar_conteos_lote(
    base_empresa: str,
    id_mpr_armado_lote: int,
    exitosos: int,
    fallidos: int,
) -> None:
    base = (base_empresa or "").strip()
    with mysql_cursor(base) as cursor:
        cursor.execute(
            """
            UPDATE mpr_armado_lote
            SET cantidad_exitosos = %s, cantidad_fallidos = %s
            WHERE id_mpr_armado_lote = %s
            """,
            [int(exitosos), int(fallidos), int(id_mpr_armado_lote)],
        )


def obtener_lote_por_uuid_or_id(
    base_empresa: str,
    ref: Any,
) -> Optional[ArmadoLoteRecord]:
    base = (base_empresa or "").strip()
    if not base or ref is None:
        return None
    with mysql_cursor(base, dict_cursor=True) as cursor:
        if isinstance(ref, int) or (isinstance(ref, str) and ref.isdigit()):
            cursor.execute(
                """
                SELECT id_mpr_armado_lote, uuid_lote, modo, id_operario, id_usuario,
                       deposito_origen, deposito_destino, cantidad_items,
                       cantidad_exitosos, cantidad_fallidos, ejecutado_en
                FROM mpr_armado_lote WHERE id_mpr_armado_lote = %s
                """,
                [int(ref)],
            )
        else:
            cursor.execute(
                """
                SELECT id_mpr_armado_lote, uuid_lote, modo, id_operario, id_usuario,
                       deposito_origen, deposito_destino, cantidad_items,
                       cantidad_exitosos, cantidad_fallidos, ejecutado_en
                FROM mpr_armado_lote WHERE uuid_lote = %s
                """,
                [str(ref)],
            )
        row = cursor.fetchone()
        if not row:
            return None
        ejecutado = row.get("ejecutado_en")
        if not isinstance(ejecutado, datetime):
            ejecutado = datetime.now()
        return ArmadoLoteRecord(
            id_mpr_armado_lote=int(row["id_mpr_armado_lote"]),
            uuid_lote=row.get("uuid_lote"),
            modo=str(row.get("modo") or "2da"),
            id_operario=to_int_or_none(row.get("id_operario")),
            id_usuario=int(row.get("id_usuario") or 0),
            deposito_origen=int(row.get("deposito_origen") or 0),
            deposito_destino=int(row.get("deposito_destino") or 0),
            cantidad_items=int(row.get("cantidad_items") or 0),
            cantidad_exitosos=int(row.get("cantidad_exitosos") or 0),
            cantidad_fallidos=int(row.get("cantidad_fallidos") or 0),
            ejecutado_en=ejecutado,
            base_empresa=base,
        )


def guardar_movimiento_con_lineas(
    base_empresa: str,
    codigo_movimiento: int,
    id_articulo_pack: int,
    cantidad_packs: int,
    deposito_origen: int,
    deposito_destino: int,
    lineas_enriquecidas: List[Dict[str, Any]],
    id_usuario: int,
    *,
    id_operario: Optional[int] = None,
    id_lista_produccion: Optional[int] = None,
    detalle: Optional[str] = None,
    modo: str = "2da",
    id_mpr_armado_lote: Optional[int] = None,
    estado_imputacion: str = "na",
) -> int:
    base = (base_empresa or "").strip()
    with mysql_cursor(base) as cursor:
        cursor.execute(
            """
            INSERT INTO mpr_armado_surtido_movimiento
                (codigo_movimiento, id_articulo_pack, cantidad_packs, deposito_origen,
                 deposito_destino, id_lista_produccion, id_mpr_armado_lote, modo,
                 estado_imputacion, id_operario, id_usuario, detalle)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            [
                int(codigo_movimiento),
                int(id_articulo_pack),
                int(cantidad_packs),
                int(deposito_origen),
                int(deposito_destino),
                to_int_or_none(id_lista_produccion),
                to_int_or_none(id_mpr_armado_lote),
                str(modo),
                str(estado_imputacion),
                to_int_or_none(id_operario),
                int(id_usuario),
                str_or_default(detalle, "")[:500],
            ],
        )
        id_mov = int(cursor.lastrowid)
        for ln in lineas_enriquecidas or []:
            qty_pack = int(ln.get("cantidad_por_pack") or 0)
            cursor.execute(
                """
                INSERT INTO mpr_armado_surtido_linea
                    (id_mpr_armado_surtido_movimiento, id_articulo_componente,
                     codigo_articulo, descripcion_articulo, cantidad_por_pack, cantidad_total)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                [
                    id_mov,
                    int(ln["id_articulo"]),
                    str_or_default(ln.get("codigo_articulo"), "-"),
                    str_or_default(ln.get("descripcion_articulo"), "-"),
                    qty_pack,
                    qty_pack * int(cantidad_packs),
                ],
            )
    return id_mov


def obtener_movimiento_por_codigo(
    base_empresa: str,
    codigo_movimiento: int,
    modo: Optional[str] = None,
) -> Optional[ArmadoMovimientoRecord]:
    base = (base_empresa or "").strip()
    sql = """
        SELECT id_mpr_armado_surtido_movimiento, codigo_movimiento, id_articulo_pack,
               cantidad_packs, modo, estado_imputacion, id_operario, id_usuario, creado_en,
               id_mpr_armado_lote
        FROM mpr_armado_surtido_movimiento
        WHERE codigo_movimiento = %s
    """
    params: List[Any] = [int(codigo_movimiento)]
    if modo:
        sql += " AND modo = %s"
        params.append(str(modo))
    sql += " LIMIT 1"
    with mysql_cursor(base, dict_cursor=True) as cursor:
        cursor.execute(sql, params)
        row = cursor.fetchone()
        if not row:
            return None
        creado = row.get("creado_en")
        if not isinstance(creado, datetime):
            creado = datetime.now()
        return ArmadoMovimientoRecord(
            id_mpr_armado_surtido_movimiento=int(row["id_mpr_armado_surtido_movimiento"]),
            codigo_movimiento=int(row["codigo_movimiento"]),
            id_articulo_pack=int(row["id_articulo_pack"]),
            cantidad_packs=int(row.get("cantidad_packs") or 0),
            modo=str(row.get("modo") or "2da"),
            estado_imputacion=str(row.get("estado_imputacion") or "na"),
            id_operario=to_int_or_none(row.get("id_operario")),
            id_usuario=int(row.get("id_usuario") or 0),
            creado_en=creado,
            id_mpr_armado_lote=to_int_or_none(row.get("id_mpr_armado_lote")),
            base_empresa=base,
        )


def actualizar_estado_imputacion_mov(
    base_empresa: str,
    id_mpr_armado_surtido_movimiento: int,
    estado: str,
) -> None:
    base = (base_empresa or "").strip()
    with mysql_cursor(base) as cursor:
        cursor.execute(
            """
            UPDATE mpr_armado_surtido_movimiento
            SET estado_imputacion = %s
            WHERE id_mpr_armado_surtido_movimiento = %s
            """,
            [str(estado), int(id_mpr_armado_surtido_movimiento)],
        )


def listar_movimientos_trazabilidad(
    base_empresa: str,
    id_lista_produccion: int,
) -> List[Dict[str, Any]]:
    base = (base_empresa or "").strip()
    with mysql_cursor(base, dict_cursor=True) as cursor:
        cursor.execute(
            """
            SELECT codigo_movimiento, cantidad_packs, modo, id_operario, id_usuario, creado_en
            FROM mpr_armado_surtido_movimiento
            WHERE id_lista_produccion = %s
            ORDER BY creado_en
            """,
            [int(id_lista_produccion)],
        )
        return list(cursor.fetchall() or [])


def listar_pendientes_imputacion_mysql(
    base_empresa: str,
    filtros: Optional[Dict[str, Any]] = None,
) -> List[ArmadoMovimientoRecord]:
    from mpr.models import (
        ESTADO_IMPUTACION_COMPLETO,
        ESTADO_IMPUTACION_PARCIAL,
        ESTADO_IMPUTACION_PENDIENTE,
        MODO_ARMADO_1RA,
    )

    base = (base_empresa or "").strip()
    filtros = filtros or {}
    sql = """
        SELECT id_mpr_armado_surtido_movimiento, codigo_movimiento, id_articulo_pack,
               cantidad_packs, modo, estado_imputacion, id_operario, id_usuario, creado_en,
               id_mpr_armado_lote
        FROM mpr_armado_surtido_movimiento
        WHERE modo = %s AND estado_imputacion IN (%s, %s)
    """
    params: List[Any] = [
        MODO_ARMADO_1RA,
        ESTADO_IMPUTACION_PENDIENTE,
        ESTADO_IMPUTACION_PARCIAL,
    ]
    id_lote = filtros.get("id_lote_armado")
    if id_lote:
        sql += " AND id_mpr_armado_lote = (SELECT id_mpr_armado_lote FROM mpr_armado_lote WHERE uuid_lote = %s OR id_mpr_armado_lote = %s LIMIT 1)"
        params.extend([str(id_lote), to_int_or_none(id_lote) or 0])
    id_art = to_int_or_none(filtros.get("id_articulo_pack"))
    if id_art:
        sql += " AND id_articulo_pack = %s"
        params.append(int(id_art))
    sql += " ORDER BY creado_en DESC"

    out: List[ArmadoMovimientoRecord] = []
    with mysql_cursor(base, dict_cursor=True) as cursor:
        cursor.execute(sql, params)
        for row in cursor.fetchall() or []:
            creado = row.get("creado_en")
            if not isinstance(creado, datetime):
                creado = datetime.now()
            rec = ArmadoMovimientoRecord(
                id_mpr_armado_surtido_movimiento=int(row["id_mpr_armado_surtido_movimiento"]),
                codigo_movimiento=int(row["codigo_movimiento"]),
                id_articulo_pack=int(row["id_articulo_pack"]),
                cantidad_packs=int(row.get("cantidad_packs") or 0),
                modo=str(row.get("modo") or MODO_ARMADO_1RA),
                estado_imputacion=str(row.get("estado_imputacion") or ESTADO_IMPUTACION_PENDIENTE),
                id_operario=to_int_or_none(row.get("id_operario")),
                id_usuario=int(row.get("id_usuario") or 0),
                creado_en=creado,
                id_mpr_armado_lote=to_int_or_none(row.get("id_mpr_armado_lote")),
                base_empresa=base,
            )
            if rec.estado_imputacion == ESTADO_IMPUTACION_COMPLETO:
                continue
            out.append(rec)
    return out
