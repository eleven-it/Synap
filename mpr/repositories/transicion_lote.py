"""Transiciones entre etapas MPR (mpr_transicion_lote)."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from core.utils.administranet_types import str_or_default, to_date_or_none, to_decimal_or_none, to_int_or_none

from mpr.db import mysql_cursor

TIPOS_DESTINO_CLASIFICACION = frozenset({"SemiElaborado", "2daSeleccion", "Scrap"})


def crear_transicion_lote(
    base_empresa: str,
    id_articulo: int,
    tipo_origen: str,
    tipo_destino: str,
    cantidad: Decimal,
    codigo_movimiento: Optional[int],
    id_usuario: int,
    *,
    id_operario: Optional[int] = None,
    operario_nombre: Optional[str] = None,
    fecha_produccion: Optional[date] = None,
    id_mpr_turno: Optional[int] = None,
    cantidad_extra: Decimal = Decimal("0"),
) -> int:
    base = (base_empresa or "").strip()
    qty = to_decimal_or_none(cantidad) or Decimal("0")
    qty_extra = to_decimal_or_none(cantidad_extra) or Decimal("0")
    id_op = to_int_or_none(id_operario)
    nombre_op = str_or_default(operario_nombre, "-") if id_op is not None else "-"
    f_prod = to_date_or_none(fecha_produccion)
    id_turno = to_int_or_none(id_mpr_turno)
    with mysql_cursor(base) as cursor:
        cursor.execute(
            """
            INSERT INTO mpr_transicion_lote
                (id_articulo, tipo_origen, tipo_destino, cantidad, cantidad_extra,
                 codigo_movimiento, id_usuario, id_operario, operario_nombre,
                 fecha_produccion, id_mpr_turno)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            [
                int(id_articulo),
                str(tipo_origen),
                str(tipo_destino),
                qty,
                qty_extra,
                to_int_or_none(codigo_movimiento),
                int(id_usuario),
                id_op,
                nombre_op,
                f_prod,
                id_turno,
            ],
        )
        return int(cursor.lastrowid)


def listar_por_articulo(
    base_empresa: str,
    id_articulo: int,
) -> List[Dict[str, Any]]:
    base = (base_empresa or "").strip()
    with mysql_cursor(base, dict_cursor=True) as cursor:
        cursor.execute(
            """
            SELECT id_mpr_transicion_lote, id_articulo, tipo_origen, tipo_destino,
                   cantidad, codigo_movimiento, id_usuario, id_operario, operario_nombre,
                   fecha_produccion, id_mpr_turno, creado_en
            FROM mpr_transicion_lote
            WHERE id_articulo = %s
            ORDER BY creado_en
            """,
            [int(id_articulo)],
        )
        rows = cursor.fetchall() or []
    out: List[Dict[str, Any]] = []
    for row in rows:
        creado = row.get("creado_en")
        if isinstance(creado, str):
            try:
                creado = datetime.fromisoformat(creado.replace("Z", "+00:00"))
            except ValueError:
                creado = datetime.now()
        out.append({
            "id": int(row["id_mpr_transicion_lote"]),
            "id_articulo": int(row["id_articulo"]),
            "tipo_origen": str(row.get("tipo_origen") or ""),
            "tipo_destino": str(row.get("tipo_destino") or ""),
            "cantidad": to_decimal_or_none(row.get("cantidad")) or Decimal("0"),
            "codigo_movimiento": to_int_or_none(row.get("codigo_movimiento")),
            "id_usuario": int(row.get("id_usuario") or 0),
            "id_operario": to_int_or_none(row.get("id_operario")),
            "operario_nombre": str_or_default(row.get("operario_nombre"), "-"),
            "fecha_produccion": to_date_or_none(row.get("fecha_produccion")),
            "id_mpr_turno": to_int_or_none(row.get("id_mpr_turno")),
            "creado_en": creado or datetime.now(),
        })
    return out


def sumar_clasificado_por_operario_fecha_turno(
    base_empresa: str,
    fecha: date,
    id_mpr_turno: int,
    *,
    id_articulos: Optional[List[int]] = None,
) -> Dict[Tuple[int, int], Decimal]:
    """Suma semi+2da+scrap clasificado por (id_articulo, id_operario) en fecha+turno."""
    base = (base_empresa or "").strip()
    if not base:
        return {}
    params: List[Any] = [fecha, int(id_mpr_turno)]
    filtro_art = ""
    if id_articulos is not None:
        if not id_articulos:
            return {}
        clean = [int(a) for a in id_articulos]
        filtro_art = f" AND id_articulo IN ({','.join(['%s'] * len(clean))})"
        params.extend(clean)
    destinos = tuple(TIPOS_DESTINO_CLASIFICACION)
    ph_dest = ",".join(["%s"] * len(destinos))
    params.extend(destinos)
    acum: Dict[Tuple[int, int], Decimal] = {}
    with mysql_cursor(base, dict_cursor=True) as cursor:
        cursor.execute(
            f"""
            SELECT id_articulo, id_operario, COALESCE(SUM(cantidad), 0) AS total
            FROM mpr_transicion_lote
            WHERE fecha_produccion = %s
              AND id_mpr_turno = %s
              AND id_operario IS NOT NULL
              AND tipo_destino IN ({ph_dest})
              {filtro_art}
            GROUP BY id_articulo, id_operario
            """,
            params,
        )
        for row in cursor.fetchall() or []:
            aid = to_int_or_none(row.get("id_articulo"))
            oid = to_int_or_none(row.get("id_operario"))
            total = to_decimal_or_none(row.get("total")) or Decimal("0")
            if aid is not None and oid is not None:
                acum[(aid, oid)] = acum.get((aid, oid), Decimal("0")) + total
    return acum


def sumar_salidas_desde_produccion_por_articulo(
    base_empresa: str,
    id_articulos: Optional[List[int]] = None,
) -> Dict[int, Decimal]:
    """Suma clasificación registrada con origen Producción por id_articulo.

    Incluye unidades ya movidas a Semi/2da/Scrap aunque el stock físico haya salido
    del pipeline (p. ej. consumidas en armado del pack BOM).
    """
    base = (base_empresa or "").strip()
    if not base:
        return {}
    params: List[Any] = ["Produccion"]
    filtro_art = ""
    if id_articulos is not None:
        if not id_articulos:
            return {}
        clean = [int(a) for a in id_articulos]
        filtro_art = f" AND id_articulo IN ({','.join(['%s'] * len(clean))})"
        params.extend(clean)
    acum: Dict[int, Decimal] = {}
    with mysql_cursor(base, dict_cursor=True) as cursor:
        cursor.execute(
            f"""
            SELECT id_articulo, COALESCE(SUM(cantidad), 0) AS total
            FROM mpr_transicion_lote
            WHERE tipo_origen = %s
              {filtro_art}
            GROUP BY id_articulo
            """,
            params,
        )
        for row in cursor.fetchall() or []:
            aid = to_int_or_none(row.get("id_articulo"))
            if aid is None:
                continue
            acum[aid] = to_decimal_or_none(row.get("total")) or Decimal("0")
    return acum


def sumar_clasificado_rendimiento_operario(
    base_empresa: str,
    fecha_desde: date,
    fecha_hasta: date,
) -> Dict[int, Dict[str, Any]]:
    """Totales semi / 2da / scrap por operario fabricante en el período."""
    base = (base_empresa or "").strip()
    if not base:
        return {}
    destinos = tuple(TIPOS_DESTINO_CLASIFICACION)
    ph_dest = ",".join(["%s"] * len(destinos))
    por_operario: Dict[int, Dict[str, Any]] = {}
    with mysql_cursor(base, dict_cursor=True) as cursor:
        cursor.execute(
            f"""
            SELECT id_operario,
                   MAX(NULLIF(TRIM(operario_nombre), '')) AS operario_nombre,
                   tipo_destino,
                   COALESCE(SUM(cantidad), 0) AS total
            FROM mpr_transicion_lote
            WHERE fecha_produccion BETWEEN %s AND %s
              AND id_operario IS NOT NULL
              AND tipo_destino IN ({ph_dest})
            GROUP BY id_operario, tipo_destino
            """,
            [fecha_desde, fecha_hasta, *destinos],
        )
        for row in cursor.fetchall() or []:
            oid = to_int_or_none(row.get("id_operario"))
            if oid is None:
                continue
            dest = str(row.get("tipo_destino") or "")
            total = to_decimal_or_none(row.get("total")) or Decimal("0")
            entry = por_operario.setdefault(
                oid,
                {
                    "operario_nombre": str_or_default(row.get("operario_nombre"), "-"),
                    "semi": Decimal("0"),
                    "segunda": Decimal("0"),
                    "scrap": Decimal("0"),
                },
            )
            nombre = str_or_default(row.get("operario_nombre"), "").strip()
            if nombre:
                entry["operario_nombre"] = nombre
            if dest == "SemiElaborado":
                entry["semi"] += total
            elif dest == "2daSeleccion":
                entry["segunda"] += total
            elif dest == "Scrap":
                entry["scrap"] += total
    return por_operario


def turnos_con_control_calidad(base_empresa: str, fecha: date) -> set[int]:
    """Turnos de ``fecha`` con al menos una clasificación CC (semi/2da/scrap) con operario."""
    base = (base_empresa or "").strip()
    if not base:
        return set()
    destinos = tuple(TIPOS_DESTINO_CLASIFICACION)
    ph_dest = ",".join(["%s"] * len(destinos))
    turnos: set[int] = set()
    with mysql_cursor(base, dict_cursor=True) as cursor:
        cursor.execute(
            f"""
            SELECT DISTINCT id_mpr_turno
            FROM mpr_transicion_lote
            WHERE fecha_produccion = %s
              AND id_operario IS NOT NULL
              AND id_mpr_turno IS NOT NULL
              AND tipo_destino IN ({ph_dest})
            """,
            [fecha, *destinos],
        )
        for row in cursor.fetchall() or []:
            tid = to_int_or_none(row.get("id_mpr_turno"))
            if tid is not None:
                turnos.add(tid)
    return turnos


def fecha_tiene_control_calidad(base_empresa: str, fecha: date) -> bool:
    """True si existe al menos un registro en mpr_transicion_lote para la fecha."""
    base = (base_empresa or "").strip()
    if not base or fecha is None:
        return False
    with mysql_cursor(base, dict_cursor=True) as cursor:
        cursor.execute(
            """
            SELECT 1 FROM mpr_transicion_lote
            WHERE fecha_produccion = %s
            LIMIT 1
            """,
            [fecha],
        )
        return cursor.fetchone() is not None


def turno_tiene_control_calidad(
    base_empresa: str,
    fecha: date,
    id_mpr_turno: int,
) -> bool:
    """True si existe clasificación CC registrada para fecha+turno."""
    tid = to_int_or_none(id_mpr_turno)
    if tid is None:
        return False
    return tid in turnos_con_control_calidad(base_empresa, fecha)


def sumar_clasificado_desglose_por_operario_fecha_turno(
    base_empresa: str,
    fecha: date,
    id_mpr_turno: int,
    *,
    id_articulos: Optional[List[int]] = None,
) -> Dict[Tuple[int, int], Dict[str, Decimal]]:
    """Desglose semi / 2da / scrap por (id_articulo, id_operario) en fecha+turno."""
    base = (base_empresa or "").strip()
    if not base:
        return {}
    params: List[Any] = [fecha, int(id_mpr_turno)]
    filtro_art = ""
    if id_articulos is not None:
        if not id_articulos:
            return {}
        clean = [int(a) for a in id_articulos]
        filtro_art = f" AND id_articulo IN ({','.join(['%s'] * len(clean))})"
        params.extend(clean)
    destinos = tuple(TIPOS_DESTINO_CLASIFICACION)
    ph_dest = ",".join(["%s"] * len(destinos))
    params.extend(destinos)
    acum: Dict[Tuple[int, int], Dict[str, Decimal]] = {}
    with mysql_cursor(base, dict_cursor=True) as cursor:
        cursor.execute(
            f"""
            SELECT id_articulo, id_operario, tipo_destino,
                   COALESCE(SUM(cantidad), 0) AS total
            FROM mpr_transicion_lote
            WHERE fecha_produccion = %s
              AND id_mpr_turno = %s
              AND id_operario IS NOT NULL
              AND tipo_destino IN ({ph_dest})
              {filtro_art}
            GROUP BY id_articulo, id_operario, tipo_destino
            """,
            params,
        )
        for row in cursor.fetchall() or []:
            aid = to_int_or_none(row.get("id_articulo"))
            oid = to_int_or_none(row.get("id_operario"))
            if aid is None or oid is None:
                continue
            dest = str(row.get("tipo_destino") or "")
            total = to_decimal_or_none(row.get("total")) or Decimal("0")
            entry = acum.setdefault(
                (aid, oid),
                {"semi": Decimal("0"), "segunda": Decimal("0"), "scrap": Decimal("0")},
            )
            if dest == "SemiElaborado":
                entry["semi"] += total
            elif dest == "2daSeleccion":
                entry["segunda"] += total
            elif dest == "Scrap":
                entry["scrap"] += total
    return acum


def operario_tiene_control_calidad_fecha_turno(
    base_empresa: str,
    fecha: date,
    id_operario: int,
    id_mpr_turno: int,
) -> bool:
    """True si existe al menos una fila de control de calidad para operario+fecha+turno."""
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
            FROM mpr_transicion_lote
            WHERE fecha_produccion = %s
              AND id_mpr_turno = %s
              AND id_operario = %s
            LIMIT 1
            """,
            [f_prod, tid, oid],
        )
        return cursor.fetchone() is not None


def set_operarios_con_cc_en_rango(
    base_empresa: str,
    fecha_desde: date,
    fecha_hasta: date,
) -> set:
    """Conjunto de (id_operario, fecha_iso, id_mpr_turno) con CC en el rango."""
    base = (base_empresa or "").strip()
    f_desde = to_date_or_none(fecha_desde)
    f_hasta = to_date_or_none(fecha_hasta)
    if not base or f_desde is None or f_hasta is None:
        return set()
    resultado: set = set()
    with mysql_cursor(base, dict_cursor=True) as cursor:
        cursor.execute(
            """
            SELECT DISTINCT id_operario, fecha_produccion, id_mpr_turno
            FROM mpr_transicion_lote
            WHERE fecha_produccion >= %s
              AND fecha_produccion <= %s
              AND id_operario IS NOT NULL
              AND id_mpr_turno IS NOT NULL
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
