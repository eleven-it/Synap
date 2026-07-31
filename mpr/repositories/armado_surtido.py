"""Armado surtido y lotes (mpr_armado_*)."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from core.services.legacy_mysql_schema.helpers import columna_existe
from core.utils.administranet_types import str_or_default, to_date_or_none, to_int_or_none

from mpr.db import mysql_cursor
from mpr.repositories.records import ArmadoLoteRecord, ArmadoMovimientoRecord


def _columnas_mpr_armado_lote(cursor) -> List[str]:
    """Columnas disponibles en mpr_armado_lote (fallback si migración pendiente)."""
    base_cols = [
        "id_mpr_armado_lote",
        "uuid_lote",
        "modo",
        "id_operario",
        "id_usuario",
        "deposito_origen",
        "deposito_destino",
        "cantidad_items",
        "cantidad_exitosos",
        "cantidad_fallidos",
        "ejecutado_en",
    ]
    extras = ["fecha_realizado", "estado", "movimiento_fisico_ok", "detalle"]
    out = list(base_cols)
    for col in extras:
        if columna_existe(cursor, "mpr_armado_lote", col):
            out.append(col)
    return out


def _fecha_desde_row(val: Any) -> Optional[date]:
    if val is None:
        return None
    if isinstance(val, date) and not isinstance(val, datetime):
        return val
    if isinstance(val, datetime):
        return val.date()
    iso = to_date_or_none(val)
    if iso:
        try:
            return date.fromisoformat(iso)
        except ValueError:
            return None
    return None


def _row_a_armado_lote_record(base: str, row: Dict[str, Any]) -> ArmadoLoteRecord:
    ejecutado = row.get("ejecutado_en")
    if not isinstance(ejecutado, datetime):
        ejecutado = datetime.now()
    mov_ok = row.get("movimiento_fisico_ok")
    if mov_ok is None:
        mov_fisico_ok = True
    else:
        mov_fisico_ok = bool(int(mov_ok))
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
        fecha_realizado=_fecha_desde_row(row.get("fecha_realizado")),
        estado=str_or_default(row.get("estado"), "aprobado"),
        movimiento_fisico_ok=mov_fisico_ok,
        detalle=str_or_default(row.get("detalle"), ""),
        base_empresa=base,
    )


def crear_lote_armado(
    base_empresa: str,
    modo: str,
    id_operario: Optional[int],
    id_usuario: int,
    deposito_origen: int,
    deposito_destino: int,
    cantidad_items: int,
    uuid_lote: Optional[str] = None,
    *,
    fecha_realizado: Optional[date] = None,
    estado: str = "aprobado",
    detalle: Optional[str] = None,
    movimiento_fisico_ok: bool = True,
) -> ArmadoLoteRecord:
    base = (base_empresa or "").strip()
    uid = str(uuid_lote or uuid.uuid4())
    fecha_sql = to_date_or_none(fecha_realizado) if fecha_realizado else None
    est = str_or_default(estado, "aprobado")
    det = str_or_default(detalle, "")[:500]
    mov_ok = 1 if movimiento_fisico_ok else 0
    with mysql_cursor(base) as cursor:
        cols = [
            "uuid_lote", "modo", "id_operario", "id_usuario",
            "deposito_origen", "deposito_destino", "cantidad_items",
            "cantidad_exitosos", "cantidad_fallidos",
        ]
        vals: List[Any] = [
            uid, str(modo), to_int_or_none(id_operario), int(id_usuario),
            int(deposito_origen), int(deposito_destino), int(cantidad_items), 0, 0,
        ]
        if columna_existe(cursor, "mpr_armado_lote", "fecha_realizado"):
            cols.append("fecha_realizado")
            vals.append(fecha_sql)
        if columna_existe(cursor, "mpr_armado_lote", "estado"):
            cols.append("estado")
            vals.append(est)
        if columna_existe(cursor, "mpr_armado_lote", "movimiento_fisico_ok"):
            cols.append("movimiento_fisico_ok")
            vals.append(mov_ok)
        if columna_existe(cursor, "mpr_armado_lote", "detalle"):
            cols.append("detalle")
            vals.append(det)
        placeholders = ", ".join(["%s"] * len(cols))
        col_sql = ", ".join(cols)
        cursor.execute(
            f"INSERT INTO mpr_armado_lote ({col_sql}) VALUES ({placeholders})",
            vals,
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
        fecha_realizado=fecha_realizado,
        estado=est,
        movimiento_fisico_ok=bool(movimiento_fisico_ok),
        detalle=det,
        base_empresa=base,
    )


def actualizar_lote_armado(
    base_empresa: str,
    id_mpr_armado_lote: int,
    *,
    cantidad_exitosos: Optional[int] = None,
    cantidad_fallidos: Optional[int] = None,
    cantidad_items: Optional[int] = None,
    estado: Optional[str] = None,
    movimiento_fisico_ok: Optional[bool] = None,
    fecha_realizado: Optional[date] = None,
    detalle: Optional[str] = None,
) -> None:
    """Actualiza campos del lote (conteos, estado, fecha, etc.)."""
    base = (base_empresa or "").strip()
    sets: List[str] = []
    params: List[Any] = []
    if cantidad_exitosos is not None:
        sets.append("cantidad_exitosos = %s")
        params.append(int(cantidad_exitosos))
    if cantidad_fallidos is not None:
        sets.append("cantidad_fallidos = %s")
        params.append(int(cantidad_fallidos))
    if cantidad_items is not None:
        sets.append("cantidad_items = %s")
        params.append(int(cantidad_items))
    if estado is not None:
        sets.append("estado = %s")
        params.append(str_or_default(estado, "aprobado"))
    if movimiento_fisico_ok is not None:
        sets.append("movimiento_fisico_ok = %s")
        params.append(1 if movimiento_fisico_ok else 0)
    if fecha_realizado is not None:
        sets.append("fecha_realizado = %s")
        params.append(to_date_or_none(fecha_realizado))
    if detalle is not None:
        sets.append("detalle = %s")
        params.append(str_or_default(detalle, "")[:500])
    if not sets:
        return
    params.append(int(id_mpr_armado_lote))
    with mysql_cursor(base) as cursor:
        cursor.execute(
            f"UPDATE mpr_armado_lote SET {', '.join(sets)} WHERE id_mpr_armado_lote = %s",
            params,
        )


def actualizar_conteos_lote(
    base_empresa: str,
    id_mpr_armado_lote: int,
    exitosos: int,
    fallidos: int,
) -> None:
    actualizar_lote_armado(
        base_empresa,
        id_mpr_armado_lote,
        cantidad_exitosos=exitosos,
        cantidad_fallidos=fallidos,
    )


def obtener_lote_por_uuid_or_id(
    base_empresa: str,
    ref: Any,
) -> Optional[ArmadoLoteRecord]:
    base = (base_empresa or "").strip()
    if not base or ref is None:
        return None
    with mysql_cursor(base, dict_cursor=True) as cursor:
        cols = _columnas_mpr_armado_lote(cursor)
        col_sql = ", ".join(cols)
        if isinstance(ref, int) or (isinstance(ref, str) and ref.isdigit()):
            cursor.execute(
                f"SELECT {col_sql} FROM mpr_armado_lote WHERE id_mpr_armado_lote = %s",
                [int(ref)],
            )
        else:
            cursor.execute(
                f"SELECT {col_sql} FROM mpr_armado_lote WHERE uuid_lote = %s",
                [str(ref)],
            )
        row = cursor.fetchone()
        if not row:
            return None
        return _row_a_armado_lote_record(base, row)


def listar_lotes_borrador(
    base_empresa: str,
    modo: str,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Lotes en estado borrador para el modo indicado."""
    base = (base_empresa or "").strip()
    if not base:
        return []
    lim = max(1, min(int(limit or 50), 100))
    with mysql_cursor(base, dict_cursor=True) as cursor:
        if not columna_existe(cursor, "mpr_armado_lote", "estado"):
            return []
        cols = _columnas_mpr_armado_lote(cursor)
        col_sql = ", ".join(cols)
        cursor.execute(
            f"""
            SELECT {col_sql}
            FROM mpr_armado_lote
            WHERE modo = %s AND estado = 'borrador'
            ORDER BY ejecutado_en DESC
            LIMIT %s
            """,
            [str(modo), lim],
        )
        rows = cursor.fetchall() or []
    out: List[Dict[str, Any]] = []
    for row in rows:
        rec = _row_a_armado_lote_record(base, row)
        out.append({
            "id_mpr_armado_lote": rec.id_mpr_armado_lote,
            "uuid_lote": rec.uuid_lote,
            "modo": rec.modo,
            "deposito_origen": rec.deposito_origen,
            "deposito_destino": rec.deposito_destino,
            "cantidad_items": rec.cantidad_items,
            "detalle": rec.detalle,
            "fecha_realizado": rec.fecha_realizado.isoformat() if rec.fecha_realizado else None,
            "ejecutado_en": rec.ejecutado_en.isoformat() if rec.ejecutado_en else None,
        })
    return out


def _tabla_items_lote_existe(cursor) -> bool:
    cursor.execute(
        "SELECT 1 FROM information_schema.TABLES "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'mpr_armado_lote_item' LIMIT 1"
    )
    return cursor.fetchone() is not None


def reemplazar_items_lote(
    base_empresa: str,
    id_lote: int,
    armados: List[Dict[str, Any]],
) -> None:
    """Borra ítems previos del lote e inserta snapshot (borrador o post-aprobación)."""
    base = (base_empresa or "").strip()
    id_l = int(id_lote)
    with mysql_cursor(base) as cursor:
        if not _tabla_items_lote_existe(cursor):
            return
        cursor.execute(
            "DELETE FROM mpr_armado_lote_item WHERE id_mpr_armado_lote = %s",
            [id_l],
        )
        for orden, item in enumerate(armados or []):
            id_pack = to_int_or_none(item.get("id_articulo_pack"))
            qty = to_int_or_none(item.get("cantidad_packs"))
            if not id_pack or not qty or qty < 1:
                continue
            cursor.execute(
                """
                INSERT INTO mpr_armado_lote_item
                    (id_mpr_armado_lote, id_articulo_pack, cantidad_packs, orden)
                VALUES (%s, %s, %s, %s)
                """,
                [id_l, int(id_pack), int(qty), int(orden)],
            )
            id_item = int(cursor.lastrowid)
            for ln in item.get("lineas") or []:
                id_c = to_int_or_none(ln.get("id_articulo"))
                qty_pp = to_int_or_none(ln.get("cantidad_por_pack"))
                if not id_c or not qty_pp or qty_pp < 1:
                    continue
                cursor.execute(
                    """
                    INSERT INTO mpr_armado_lote_item_linea
                        (id_mpr_armado_lote_item, id_articulo_componente,
                         codigo_articulo, descripcion_articulo, cantidad_por_pack)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    [
                        id_item,
                        int(id_c),
                        str_or_default(ln.get("codigo_articulo"), "-")[:64],
                        str_or_default(ln.get("descripcion_articulo"), "-")[:255],
                        int(qty_pp),
                    ],
                )


def listar_items_lote(base_empresa: str, id_lote: int) -> List[Dict[str, Any]]:
    """Ítems del lote con líneas de composición."""
    base = (base_empresa or "").strip()
    id_l = int(id_lote)
    with mysql_cursor(base, dict_cursor=True) as cursor:
        if not _tabla_items_lote_existe(cursor):
            return []
        cursor.execute(
            """
            SELECT id_mpr_armado_lote_item, id_articulo_pack, cantidad_packs, orden
            FROM mpr_armado_lote_item
            WHERE id_mpr_armado_lote = %s
            ORDER BY orden, id_mpr_armado_lote_item
            """,
            [id_l],
        )
        items = cursor.fetchall() or []
        out: List[Dict[str, Any]] = []
        for it in items:
            id_item = int(it["id_mpr_armado_lote_item"])
            cursor.execute(
                """
                SELECT id_articulo_componente, codigo_articulo, descripcion_articulo,
                       cantidad_por_pack
                FROM mpr_armado_lote_item_linea
                WHERE id_mpr_armado_lote_item = %s
                ORDER BY id_mpr_armado_lote_item_linea
                """,
                [id_item],
            )
            lineas = []
            for ln in cursor.fetchall() or []:
                lineas.append({
                    "id_articulo": int(ln["id_articulo_componente"]),
                    "codigo_articulo": str_or_default(ln.get("codigo_articulo"), "-"),
                    "descripcion_articulo": str_or_default(ln.get("descripcion_articulo"), "-"),
                    "cantidad_por_pack": int(ln.get("cantidad_por_pack") or 0),
                })
            out.append({
                "id_articulo_pack": int(it["id_articulo_pack"]),
                "cantidad_packs": int(it.get("cantidad_packs") or 0),
                "lineas": lineas,
            })
        return out


def listar_movimientos_armado_por_fecha(
    base_empresa: str,
    *,
    fecha_realizado: date,
    modo: str = "1ra",
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """
    Movimientos de armado aprobados con ``mpr_armado_lote.fecha_realizado`` = fecha.

    Incluye descripción del pack desde ``articulo`` cuando está disponible.
    """
    from core.services.legacy_mysql_schema.helpers import nombre_columna_ci

    base = (base_empresa or "").strip()
    if isinstance(fecha_realizado, date) and not isinstance(fecha_realizado, datetime):
        fecha = fecha_realizado.isoformat()
    else:
        fecha = to_date_or_none(fecha_realizado)
    modo_n = (modo or "1ra").strip().lower()
    if not base or not fecha or modo_n not in ("1ra", "2da"):
        return []
    lim = max(1, min(int(limit or 100), 200))
    with mysql_cursor(base, dict_cursor=True) as cursor:
        if not columna_existe(cursor, "mpr_armado_lote", "fecha_realizado"):
            return []
        cursor.execute(
            """
            SELECT m.id_mpr_armado_surtido_movimiento,
                   m.codigo_movimiento,
                   m.id_articulo_pack,
                   m.cantidad_packs,
                   m.modo,
                   m.creado_en,
                   m.id_mpr_armado_lote,
                   l.fecha_realizado
            FROM mpr_armado_surtido_movimiento m
            INNER JOIN mpr_armado_lote l
                ON l.id_mpr_armado_lote = m.id_mpr_armado_lote
            WHERE l.fecha_realizado = %s
              AND m.modo = %s
              AND COALESCE(l.estado, 'aprobado') = 'aprobado'
            ORDER BY m.creado_en DESC, m.id_mpr_armado_surtido_movimiento DESC
            LIMIT %s
            """,
            [fecha, modo_n, lim],
        )
        rows = cursor.fetchall() or []
        if not rows:
            return []
        ids_pack = sorted({
            int(r["id_articulo_pack"])
            for r in rows
            if to_int_or_none(r.get("id_articulo_pack")) is not None
        })
        meta: Dict[int, Dict[str, str]] = {}
        if ids_pack:
            cursor.execute("SHOW TABLES LIKE 'articulo'")
            if cursor.fetchone():
                ph = ",".join(["%s"] * len(ids_pack))
                cursor.execute(
                    f"""
                    SELECT IDArt AS id_articulo,
                           COALESCE(CodigoArticuloT, CAST(CodigoArticulo AS CHAR), '') AS codigo,
                           COALESCE(NombreArticulo, '') AS descripcion
                    FROM articulo
                    WHERE IDArt IN ({ph})
                    """,
                    ids_pack,
                )
                for ar in cursor.fetchall() or []:
                    aid = to_int_or_none(ar.get("id_articulo"))
                    if aid is None:
                        continue
                    meta[int(aid)] = {
                        "codigo": str_or_default(ar.get("codigo"), "-"),
                        "descripcion": str_or_default(ar.get("descripcion"), "-"),
                    }
        # nro_comprobante: nombres físicos varían (codigo_movimiento vs CodigoMovimiento)
        codigos = [
            to_int_or_none(r.get("codigo_movimiento"))
            for r in rows
        ]
        codigos = [c for c in codigos if c]
        nro_por_cod: Dict[int, str] = {}
        if codigos:
            cursor.execute("SHOW TABLES LIKE 'movimiento_stock'")
            if cursor.fetchone():
                col_cod = (
                    nombre_columna_ci(cursor, "movimiento_stock", "codigo_movimiento")
                    or nombre_columna_ci(cursor, "movimiento_stock", "CodigoMovimiento")
                )
                col_nro = (
                    nombre_columna_ci(cursor, "movimiento_stock", "nro_comprobante")
                    or nombre_columna_ci(cursor, "movimiento_stock", "NroComprobante")
                )
                if col_cod and col_nro:
                    ph = ",".join(["%s"] * len(codigos))
                    cursor.execute(
                        f"""
                        SELECT `{col_cod}` AS codigo, `{col_nro}` AS nro
                        FROM movimiento_stock
                        WHERE `{col_cod}` IN ({ph})
                        """,
                        codigos,
                    )
                    for ms in cursor.fetchall() or []:
                        c = to_int_or_none(ms.get("codigo"))
                        if c is not None:
                            nro_por_cod[int(c)] = str_or_default(ms.get("nro"), "-")

        out: List[Dict[str, Any]] = []
        for r in rows:
            id_pack = to_int_or_none(r.get("id_articulo_pack"))
            if id_pack is None:
                continue
            info = meta.get(int(id_pack)) or {}
            cod_mov = to_int_or_none(r.get("codigo_movimiento"))
            out.append({
                "id_movimiento": to_int_or_none(r.get("id_mpr_armado_surtido_movimiento")),
                "id_articulo_pack": int(id_pack),
                "codigo_articulo": info.get("codigo") or "-",
                "descripcion_articulo": info.get("descripcion") or f"ID {id_pack}",
                "cantidad_packs": int(r.get("cantidad_packs") or 0),
                "codigo_movimiento": cod_mov,
                "nro_comprobante": nro_por_cod.get(int(cod_mov), "-") if cod_mov else "-",
                "id_lote": to_int_or_none(r.get("id_mpr_armado_lote")),
            })
        return out


def listar_movimientos_de_lote(
    base_empresa: str,
    id_lote: int,
) -> List[Dict[str, Any]]:
    """Movimientos MSTOCK del lote con líneas de composición."""
    base = (base_empresa or "").strip()
    id_l = int(id_lote)
    with mysql_cursor(base, dict_cursor=True) as cursor:
        cursor.execute(
            """
            SELECT id_mpr_armado_surtido_movimiento, codigo_movimiento, id_articulo_pack,
                   cantidad_packs, modo, estado_imputacion, id_operario, id_usuario, creado_en,
                   deposito_origen, deposito_destino, detalle
            FROM mpr_armado_surtido_movimiento
            WHERE id_mpr_armado_lote = %s
            ORDER BY creado_en, id_mpr_armado_surtido_movimiento
            """,
            [id_l],
        )
        movs = cursor.fetchall() or []
        out: List[Dict[str, Any]] = []
        for mov in movs:
            id_mov = int(mov["id_mpr_armado_surtido_movimiento"])
            cursor.execute(
                """
                SELECT id_articulo_componente, codigo_articulo, descripcion_articulo,
                       cantidad_por_pack, cantidad_total
                FROM mpr_armado_surtido_linea
                WHERE id_mpr_armado_surtido_movimiento = %s
                ORDER BY id_mpr_armado_surtido_linea
                """,
                [id_mov],
            )
            lineas = []
            for ln in cursor.fetchall() or []:
                lineas.append({
                    "id_articulo": int(ln["id_articulo_componente"]),
                    "codigo_articulo": str_or_default(ln.get("codigo_articulo"), "-"),
                    "descripcion_articulo": str_or_default(ln.get("descripcion_articulo"), "-"),
                    "cantidad_por_pack": int(ln.get("cantidad_por_pack") or 0),
                    "cantidad_total": int(ln.get("cantidad_total") or 0),
                })
            out.append({
                "id_mpr_armado_surtido_movimiento": id_mov,
                "codigo_movimiento": int(mov["codigo_movimiento"]),
                "id_articulo_pack": int(mov["id_articulo_pack"]),
                "cantidad_packs": int(mov.get("cantidad_packs") or 0),
                "modo": str(mov.get("modo") or "2da"),
                "estado_imputacion": str(mov.get("estado_imputacion") or "na"),
                "deposito_origen": int(mov.get("deposito_origen") or 0),
                "deposito_destino": int(mov.get("deposito_destino") or 0),
                "detalle": str_or_default(mov.get("detalle"), ""),
                "lineas": lineas,
            })
        return out


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
