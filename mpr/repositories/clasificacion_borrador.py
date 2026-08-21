"""Borrador de control de calidad MPR (precarga sin movimiento de stock).

Persiste cantidades semi / 2da / scrap por fecha, turno, artículo, operario y máquina.
No interviene en ``mpr_transicion_lote`` ni en MSTOCK hasta confirmar el CC.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from core.utils.administranet_types import to_date_or_none, to_decimal_or_none, to_int_or_none

from mpr.db import mysql_cursor

ClaveLineaBorrador = Tuple[int, int, int, int]


def normalizar_linea_cc_borrador(linea: Dict[str, Any]) -> Dict[str, Any]:
    """Normaliza una línea 007 y traduce el centinela Semi 0 a ``None``."""
    id_operario = to_int_or_none(linea.get("id_operario"))
    id_turno = to_int_or_none(linea.get("id_mpr_turno"))
    return {
        "id_articulo": to_int_or_none(linea.get("id_articulo")),
        "id_operario": id_operario if id_operario and id_operario > 0 else None,
        "id_mpr_turno": id_turno if id_turno and id_turno > 0 else None,
        "cant_semi": to_decimal_or_none(linea.get("cant_semi")) or Decimal("0"),
        "cant_2da": to_decimal_or_none(linea.get("cant_2da")) or Decimal("0"),
        "cant_scrap": to_decimal_or_none(linea.get("cant_scrap")) or Decimal("0"),
    }


def _lineas_cc_consolidado_validas(lineas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Separa Semi consolidado de 2da/scrap y aplica el centinela MySQL."""
    acumulado: Dict[Tuple[int, int, int], Dict[str, Any]] = {}

    def _sumar(
        aid: int,
        oid: int,
        tid: int,
        *,
        semi: Decimal = Decimal("0"),
        segunda: Decimal = Decimal("0"),
        scrap: Decimal = Decimal("0"),
    ) -> None:
        destino = acumulado.setdefault(
            (aid, oid, tid),
            {
                "id_articulo": aid,
                "id_operario": oid,
                "id_mpr_turno": tid,
                "cant_semi": Decimal("0"),
                "cant_2da": Decimal("0"),
                "cant_scrap": Decimal("0"),
            },
        )
        destino["cant_semi"] += semi
        destino["cant_2da"] += segunda
        destino["cant_scrap"] += scrap

    for linea in lineas or []:
        normalizada = normalizar_linea_cc_borrador(linea)
        aid = normalizada["id_articulo"]
        if aid is None:
            continue
        semi = normalizada["cant_semi"]
        if semi > 0:
            _sumar(aid, 0, 0, semi=semi)
        segunda = normalizada["cant_2da"]
        scrap = normalizada["cant_scrap"]
        oid = normalizada["id_operario"]
        tid = normalizada["id_mpr_turno"]
        if (segunda > 0 or scrap > 0) and oid is not None and tid is not None:
            _sumar(aid, oid, tid, segunda=segunda, scrap=scrap)
    return list(acumulado.values())


def upsert_borrador_cc_consolidado(
    base_empresa: str,
    fecha: date,
    id_usuario: int,
    lineas: List[Dict[str, Any]],
) -> None:
    """Reemplaza el borrador 007 de una fecha sin tocar stock ni ledger."""
    base = (base_empresa or "").strip()
    f_prod = to_date_or_none(fecha)
    uid = to_int_or_none(id_usuario)
    if not base or f_prod is None or uid is None:
        return
    lineas_validas = _lineas_cc_consolidado_validas(lineas)
    with mysql_cursor(base) as cursor:
        if not lineas_validas:
            cursor.execute(
                "DELETE FROM mpr_cc_borrador WHERE fecha_produccion = %s",
                [f_prod],
            )
            return
        cursor.execute(
            """
            INSERT INTO mpr_cc_borrador (fecha_produccion, id_usuario)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE
                id_usuario = VALUES(id_usuario),
                actualizado_en = CURRENT_TIMESTAMP
            """,
            [f_prod, uid],
        )
        cursor.execute(
            """
            SELECT id_mpr_cc_borrador
            FROM mpr_cc_borrador
            WHERE fecha_produccion = %s
            LIMIT 1
            """,
            [f_prod],
        )
        row = cursor.fetchone()
        if not row:
            return
        id_borrador = to_int_or_none(
            row.get("id_mpr_cc_borrador") if isinstance(row, dict) else row[0]
        )
        if id_borrador is None:
            return
        cursor.execute(
            "DELETE FROM mpr_cc_borrador_linea WHERE id_mpr_cc_borrador = %s",
            [id_borrador],
        )
        for linea in lineas_validas:
            cursor.execute(
                """
                INSERT INTO mpr_cc_borrador_linea (
                    id_mpr_cc_borrador, id_articulo, id_operario, id_mpr_turno,
                    cant_semi, cant_2da, cant_scrap
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                [
                    id_borrador,
                    linea["id_articulo"],
                    linea["id_operario"],
                    linea["id_mpr_turno"],
                    linea["cant_semi"],
                    linea["cant_2da"],
                    linea["cant_scrap"],
                ],
            )


def listar_lineas_borrador_cc_consolidado(
    base_empresa: str,
    fecha: date,
) -> List[Dict[str, Any]]:
    """Lista el shape 007 y traduce los centinelas de Semi a ``None``."""
    base = (base_empresa or "").strip()
    f_prod = to_date_or_none(fecha)
    if not base or f_prod is None:
        return []
    with mysql_cursor(base, dict_cursor=True) as cursor:
        cursor.execute(
            """
            SELECT l.id_articulo, l.id_operario, l.id_mpr_turno,
                   l.cant_semi, l.cant_2da, l.cant_scrap
            FROM mpr_cc_borrador b
            INNER JOIN mpr_cc_borrador_linea l
              ON l.id_mpr_cc_borrador = b.id_mpr_cc_borrador
            WHERE b.fecha_produccion = %s
            ORDER BY l.id_articulo, l.id_operario, l.id_mpr_turno
            """,
            [f_prod],
        )
        return [
            normalizar_linea_cc_borrador(linea)
            for linea in (cursor.fetchall() or [])
        ]


def eliminar_borrador_cc_articulo(
    base_empresa: str,
    fecha: date,
    id_articulo: int,
    *,
    cursor=None,
) -> None:
    """Borra solo las líneas 007 del artículo indicado."""
    base = (base_empresa or "").strip()
    f_prod = to_date_or_none(fecha)
    aid = to_int_or_none(id_articulo)
    if not base or f_prod is None or aid is None:
        return
    def _eliminar(cur) -> None:
        cur.execute(
            """
            DELETE l
            FROM mpr_cc_borrador_linea l
            INNER JOIN mpr_cc_borrador b
              ON b.id_mpr_cc_borrador = l.id_mpr_cc_borrador
            WHERE b.fecha_produccion = %s AND l.id_articulo = %s
            """,
            [f_prod, aid],
        )
    if cursor is not None:
        _eliminar(cursor)
        return
    with mysql_cursor(base) as propio_cursor:
        _eliminar(propio_cursor)


def tiene_borrador_cc_consolidado(base_empresa: str, fecha: date) -> bool:
    """Indica si existe una cabecera nueva 007 para la fecha."""
    base = (base_empresa or "").strip()
    f_prod = to_date_or_none(fecha)
    if not base or f_prod is None:
        return False
    with mysql_cursor(base) as cursor:
        cursor.execute(
            "SELECT 1 FROM mpr_cc_borrador WHERE fecha_produccion = %s LIMIT 1",
            [f_prod],
        )
        return cursor.fetchone() is not None


def _linea_tiene_cantidad(linea: Dict[str, Any]) -> bool:
    semi = to_decimal_or_none(linea.get("cant_semi")) or Decimal("0")
    seg2da = to_decimal_or_none(linea.get("cant_2da")) or Decimal("0")
    scrap = to_decimal_or_none(linea.get("cant_scrap")) or Decimal("0")
    return semi > 0 or seg2da > 0 or scrap > 0


def upsert_borrador(
    base_empresa: str,
    fecha: date,
    id_mpr_turno: int,
    id_usuario: int,
    lineas: List[Dict[str, Any]],
) -> None:
    """Upsert cabecera por (fecha, turno) y reemplaza líneas con qty > 0.

    Si no quedan líneas con cantidad, elimina el borrador completo.
    """
    base = (base_empresa or "").strip()
    tid = to_int_or_none(id_mpr_turno)
    uid = to_int_or_none(id_usuario)
    if not base or tid is None or uid is None:
        return

    lineas_validas: List[Dict[str, Any]] = []
    for ln in lineas or []:
        aid = to_int_or_none(ln.get("id_articulo"))
        oid = to_int_or_none(ln.get("id_operario"))
        if aid is None or oid is None or oid <= 0:
            continue
        mid = to_int_or_none(ln.get("id_mpr_maquina")) or 0
        payload = {
            "id_articulo": aid,
            "id_operario": oid,
            "id_mpr_maquina": mid,
            "cant_semi": to_decimal_or_none(ln.get("cant_semi")) or Decimal("0"),
            "cant_2da": to_decimal_or_none(ln.get("cant_2da")) or Decimal("0"),
            "cant_scrap": to_decimal_or_none(ln.get("cant_scrap")) or Decimal("0"),
        }
        if _linea_tiene_cantidad(payload):
            lineas_validas.append(payload)

    if not lineas_validas:
        eliminar_borrador(base, fecha, tid)
        return

    with mysql_cursor(base) as cursor:
        cursor.execute(
            """
            INSERT INTO mpr_clasificacion_borrador (fecha_produccion, id_mpr_turno, id_usuario)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE
                id_usuario = VALUES(id_usuario),
                actualizado_en = CURRENT_TIMESTAMP
            """,
            [fecha, tid, uid],
        )
        cursor.execute(
            """
            SELECT id_mpr_clasificacion_borrador
            FROM mpr_clasificacion_borrador
            WHERE fecha_produccion = %s AND id_mpr_turno = %s
            LIMIT 1
            """,
            [fecha, tid],
        )
        row = cursor.fetchone()
        if not row:
            return
        id_borrador = int(row[0])
        cursor.execute(
            "DELETE FROM mpr_clasificacion_borrador_linea WHERE id_mpr_clasificacion_borrador = %s",
            [id_borrador],
        )
        for ln in lineas_validas:
            cursor.execute(
                """
                INSERT INTO mpr_clasificacion_borrador_linea (
                    id_mpr_clasificacion_borrador, id_articulo, id_operario, id_mpr_maquina,
                    cant_semi, cant_2da, cant_scrap
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                [
                    id_borrador,
                    ln["id_articulo"],
                    ln["id_operario"],
                    ln["id_mpr_maquina"],
                    ln["cant_semi"],
                    ln["cant_2da"],
                    ln["cant_scrap"],
                ],
            )


def listar_lineas_borrador(
    base_empresa: str,
    fecha: date,
    id_mpr_turno: Optional[int] = None,
) -> Dict[ClaveLineaBorrador, Dict[str, Decimal]]:
    """Líneas del borrador indexadas por (id_mpr_maquina, id_articulo, id_operario, id_mpr_turno)."""
    base = (base_empresa or "").strip()
    if not base:
        return {}

    params: List[Any] = [fecha]
    filtro_turno = ""
    tid = to_int_or_none(id_mpr_turno)
    if tid is not None:
        filtro_turno = " AND b.id_mpr_turno = %s"
        params.append(tid)

    out: Dict[ClaveLineaBorrador, Dict[str, Decimal]] = {}
    with mysql_cursor(base, dict_cursor=True) as cursor:
        cursor.execute(
            f"""
            SELECT b.id_mpr_turno, l.id_articulo, l.id_operario, l.id_mpr_maquina,
                   l.cant_semi, l.cant_2da, l.cant_scrap
            FROM mpr_clasificacion_borrador b
            INNER JOIN mpr_clasificacion_borrador_linea l
                ON l.id_mpr_clasificacion_borrador = b.id_mpr_clasificacion_borrador
            WHERE b.fecha_produccion = %s{filtro_turno}
            """,
            params,
        )
        for r in cursor.fetchall() or []:
            mid = to_int_or_none(r.get("id_mpr_maquina")) or 0
            aid = to_int_or_none(r.get("id_articulo"))
            oid = to_int_or_none(r.get("id_operario"))
            turno = to_int_or_none(r.get("id_mpr_turno"))
            if aid is None or oid is None or turno is None:
                continue
            out[(mid, aid, oid, turno)] = {
                "semi": to_decimal_or_none(r.get("cant_semi")) or Decimal("0"),
                "segunda": to_decimal_or_none(r.get("cant_2da")) or Decimal("0"),
                "scrap": to_decimal_or_none(r.get("cant_scrap")) or Decimal("0"),
            }
    return out


def eliminar_borrador(
    base_empresa: str,
    fecha: date,
    id_mpr_turno: int,
) -> None:
    """Elimina cabecera (cascade líneas) para fecha+turno."""
    base = (base_empresa or "").strip()
    tid = to_int_or_none(id_mpr_turno)
    if not base or tid is None:
        return
    with mysql_cursor(base) as cursor:
        cursor.execute(
            """
            DELETE FROM mpr_clasificacion_borrador
            WHERE fecha_produccion = %s AND id_mpr_turno = %s
            """,
            [fecha, tid],
        )


def migrar_borrador_operario_entre_turnos(
    base_empresa: str,
    fecha: date,
    id_operario: int,
    id_turno_origen: int,
    id_turno_destino: int,
    *,
    cursor=None,
) -> int:
    """Mueve el borrador CC de un operario sin confirmar a otro turno.

    Si el destino ya contiene la misma clave artículo/máquina, suma los tres
    destinos de clasificación y elimina la línea de origen. No toca
    ``mpr_transicion_lote`` ni genera movimientos de stock. El cursor opcional
    permite integrar esta migración a la transacción del ledger de partes.
    """
    base = (base_empresa or "").strip()
    oid = to_int_or_none(id_operario)
    origen = to_int_or_none(id_turno_origen)
    destino = to_int_or_none(id_turno_destino)
    if not base or oid is None or origen is None or destino is None or origen == destino:
        return 0

    def _migrar(cur) -> int:
        cur.execute(
            """
            SELECT id_mpr_clasificacion_borrador, id_usuario
            FROM mpr_clasificacion_borrador
            WHERE fecha_produccion = %s AND id_mpr_turno = %s
            LIMIT 1
            """,
            [fecha, origen],
        )
        cabecera_origen = cur.fetchone()
        if not cabecera_origen:
            return 0
        id_origen = to_int_or_none(cabecera_origen.get("id_mpr_clasificacion_borrador"))
        if id_origen is None:
            return 0
        cur.execute(
            """
            SELECT id_mpr_clasificacion_borrador
            FROM mpr_clasificacion_borrador
            WHERE fecha_produccion = %s AND id_mpr_turno = %s
            LIMIT 1
            """,
            [fecha, destino],
        )
        cabecera_destino = cur.fetchone()
        if cabecera_destino:
            id_destino = to_int_or_none(cabecera_destino.get("id_mpr_clasificacion_borrador"))
        else:
            cur.execute(
                """
                INSERT INTO mpr_clasificacion_borrador (fecha_produccion, id_mpr_turno, id_usuario)
                VALUES (%s, %s, %s)
                """,
                [fecha, destino, to_int_or_none(cabecera_origen.get("id_usuario")) or 0],
            )
            id_destino = to_int_or_none(cur.lastrowid)
        if id_destino is None:
            raise RuntimeError("No se pudo crear el borrador de clasificación destino.")

        cur.execute(
            """
            SELECT * FROM mpr_clasificacion_borrador_linea
            WHERE id_mpr_clasificacion_borrador = %s AND id_operario = %s
            """,
            [id_origen, oid],
        )
        movidas = 0
        for linea in cur.fetchall() or []:
            id_linea = to_int_or_none(linea.get("id_mpr_clasificacion_borrador_linea"))
            articulo = to_int_or_none(linea.get("id_articulo"))
            maquina = to_int_or_none(linea.get("id_mpr_maquina")) or 0
            if id_linea is None or articulo is None:
                continue
            cur.execute(
                """
                SELECT id_mpr_clasificacion_borrador_linea
                FROM mpr_clasificacion_borrador_linea
                WHERE id_mpr_clasificacion_borrador = %s AND id_articulo = %s
                  AND id_operario = %s AND id_mpr_maquina = %s
                LIMIT 1
                """,
                [id_destino, articulo, oid, maquina],
            )
            duplicada = cur.fetchone()
            if duplicada:
                cur.execute(
                    """
                    UPDATE mpr_clasificacion_borrador_linea
                    SET cant_semi = COALESCE(cant_semi, 0) + %s,
                        cant_2da = COALESCE(cant_2da, 0) + %s,
                        cant_scrap = COALESCE(cant_scrap, 0) + %s
                    WHERE id_mpr_clasificacion_borrador_linea = %s
                    """,
                    [
                        to_decimal_or_none(linea.get("cant_semi")) or Decimal("0"),
                        to_decimal_or_none(linea.get("cant_2da")) or Decimal("0"),
                        to_decimal_or_none(linea.get("cant_scrap")) or Decimal("0"),
                        to_int_or_none(duplicada.get("id_mpr_clasificacion_borrador_linea")),
                    ],
                )
                cur.execute(
                    "DELETE FROM mpr_clasificacion_borrador_linea WHERE id_mpr_clasificacion_borrador_linea = %s",
                    [id_linea],
                )
            else:
                cur.execute(
                    """
                    UPDATE mpr_clasificacion_borrador_linea
                    SET id_mpr_clasificacion_borrador = %s
                    WHERE id_mpr_clasificacion_borrador_linea = %s
                    """,
                    [id_destino, id_linea],
                )
            movidas += 1
        return movidas

    if cursor is not None:
        return _migrar(cursor)
    with mysql_cursor(base, dict_cursor=True) as propio_cursor:
        return _migrar(propio_cursor)


def tiene_borrador(
    base_empresa: str,
    fecha: date,
    id_mpr_turno: Optional[int] = None,
) -> bool:
    """Indica si existe borrador para la fecha (opcionalmente filtrado por turno)."""
    base = (base_empresa or "").strip()
    if not base:
        return False

    params: List[Any] = [fecha]
    filtro_turno = ""
    tid = to_int_or_none(id_mpr_turno)
    if tid is not None:
        filtro_turno = " AND id_mpr_turno = %s"
        params.append(tid)

    with mysql_cursor(base) as cursor:
        cursor.execute(
            f"""
            SELECT 1 FROM mpr_clasificacion_borrador
            WHERE fecha_produccion = %s{filtro_turno}
            LIMIT 1
            """,
            params,
        )
        return cursor.fetchone() is not None
