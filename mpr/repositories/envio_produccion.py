"""Ledger envíos tablero → producción (mpr_envio_produccion)."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence, Tuple

from core.utils.administranet_types import str_or_default, str_codigo_manual_articulo, to_decimal_or_none, to_int_or_none

from mpr.db import mysql_cursor


def _lote_key(row: Dict[str, Any]) -> str:
    """Clave de agrupación: uuid_lote o heurística legacy (usuario + segundo)."""
    ul = str_or_default(row.get("uuid_lote"), "").strip()
    if ul:
        return ul
    uid = to_int_or_none(row.get("id_usuario")) or 0
    ce = row.get("creado_en")
    if isinstance(ce, datetime):
        ts = ce.strftime("%Y%m%d%H%M%S")
    else:
        ts = str_or_default(ce, "0")
    return f"legacy-{uid}-{ts}"


def sumar_envios_por_componente(
    base_empresa: str,
    comp_ids: Optional[List[int]] = None,
) -> Dict[int, Decimal]:
    """Suma cantidades no anuladas. comp_ids=None → todos los componentes."""
    base = (base_empresa or "").strip()
    if not base:
        return {}

    ids = []
    if comp_ids is not None:
        if not comp_ids:
            return {}
        ids = [to_int_or_none(i) for i in comp_ids]
        ids = [i for i in ids if i is not None]
        if not ids:
            return {}

    with mysql_cursor(base, dict_cursor=True) as cursor:
        if ids:
            placeholders = ",".join(["%s"] * len(ids))
            cursor.execute(
                f"""
                SELECT id_articulo, SUM(cantidad) AS total
                FROM mpr_envio_produccion
                WHERE anulado = 0 AND id_articulo IN ({placeholders})
                GROUP BY id_articulo
                """,
                ids,
            )
        else:
            cursor.execute(
                """
                SELECT id_articulo, SUM(cantidad) AS total
                FROM mpr_envio_produccion
                WHERE anulado = 0
                GROUP BY id_articulo
                """
            )
        out: Dict[int, Decimal] = {}
        for row in cursor.fetchall() or []:
            art = to_int_or_none(row.get("id_articulo"))
            total = to_decimal_or_none(row.get("total"))
            if art is not None and total is not None:
                out[art] = total
        return out


def crear_envios_lote(
    base_empresa: str,
    id_usuario: int,
    items: List[Tuple[int, Decimal]],
) -> int:
    """Inserta filas en mpr_envio_produccion. Retorna cantidad insertada."""
    base = (base_empresa or "").strip()
    if not base or not items:
        return 0

    uid = to_int_or_none(id_usuario) or 0
    lote_uuid = str(uuid.uuid4())
    with mysql_cursor(base) as cursor:
        n = 0
        for id_art, cantidad in items:
            id_art_int = to_int_or_none(id_art)
            qty = to_decimal_or_none(cantidad)
            if id_art_int is None or qty is None:
                continue
            cursor.execute(
                """
                INSERT INTO mpr_envio_produccion
                    (id_articulo, cantidad, id_usuario, anulado, uuid_lote)
                VALUES (%s, %s, %s, 0, %s)
                """,
                [id_art_int, qty, uid, lote_uuid],
            )
            n += 1
        return n


def calcular_saldo_anulable_fifo(
    envios_ordenados: Sequence[Dict[str, Any]],
    total_parte: Decimal,
) -> Dict[int, Decimal]:
    """
    Asigna partes a envíos más antiguos primero (FIFO por componente).

    Retorna {id_mpr_envio_produccion: saldo_anulable} donde saldo_anulable es la
    cantidad de la fila que aún no fue consumida por partes registradas.
    """
    remaining = float(total_parte or Decimal("0"))
    out: Dict[int, Decimal] = {}
    for env in envios_ordenados:
        env_id = to_int_or_none(env.get("id_mpr_envio_produccion"))
        qty = to_decimal_or_none(env.get("cantidad"))
        if env_id is None or qty is None:
            continue
        qty_f = float(qty)
        consumed = min(qty_f, max(0.0, remaining))
        saldo = max(0.0, qty_f - consumed)
        out[env_id] = Decimal(str(saldo))
        remaining = max(0.0, remaining - consumed)
    return out


def listar_envios_activos_por_articulos(
    base_empresa: str,
    articulo_ids: List[int],
) -> Dict[int, List[Dict[str, Any]]]:
    """Envíos activos por id_articulo, ordenados por creado_en ASC (FIFO)."""
    base = (base_empresa or "").strip()
    if not base or not articulo_ids:
        return {}

    ids = [to_int_or_none(i) for i in articulo_ids]
    ids = [i for i in ids if i is not None]
    if not ids:
        return {}

    placeholders = ",".join(["%s"] * len(ids))
    with mysql_cursor(base, dict_cursor=True) as cursor:
        cursor.execute(
            f"""
            SELECT id_mpr_envio_produccion, id_articulo, cantidad, id_usuario,
                   anulado, codigo_movimiento_mstock, creado_en
            FROM mpr_envio_produccion
            WHERE anulado = 0 AND id_articulo IN ({placeholders})
            ORDER BY id_articulo, creado_en ASC, id_mpr_envio_produccion ASC
            """,
            ids,
        )
        por_art: Dict[int, List[Dict[str, Any]]] = {aid: [] for aid in ids}
        for row in cursor.fetchall() or []:
            aid = to_int_or_none(row.get("id_articulo"))
            if aid is not None:
                por_art.setdefault(aid, []).append(dict(row))
        return por_art


def listar_envios_por_fecha(
    base_empresa: str,
    fecha: date,
    *,
    id_articulo: Optional[int] = None,
    incluir_anulados: bool = False,
) -> List[Dict[str, Any]]:
    """Envíos del tablero en una fecha calendario (DATE(creado_en))."""
    base = (base_empresa or "").strip()
    if not base or fecha is None:
        return []

    filtros = ["DATE(e.creado_en) = %s"]
    params: List[Any] = [fecha]
    if not incluir_anulados:
        filtros.append("e.anulado = 0")
    art = to_int_or_none(id_articulo)
    if art is not None:
        filtros.append("e.id_articulo = %s")
        params.append(art)

    where_sql = " AND ".join(filtros)
    with mysql_cursor(base, dict_cursor=True) as cursor:
        cursor.execute(
            f"""
            SELECT
                e.id_mpr_envio_produccion,
                e.id_articulo,
                e.cantidad,
                e.id_usuario,
                e.anulado,
                e.anulado_en,
                e.id_usuario_anula,
                e.uuid_lote,
                e.codigo_movimiento_mstock,
                e.creado_en,
                COALESCE(a.id_manual, '') AS codigo_manual,
                COALESCE(a.CodigoArticuloT, CAST(a.CodigoArticulo AS CHAR), '') AS codigo_articulo,
                COALESCE(a.NombreArticulo, '') AS descripcion_articulo
            FROM mpr_envio_produccion e
            LEFT JOIN articulo a ON a.IDArt = e.id_articulo
            WHERE {where_sql}
            ORDER BY e.creado_en DESC, e.id_mpr_envio_produccion DESC
            """,
            params,
        )
        return [_normalizar_fila_envio(dict(r)) for r in (cursor.fetchall() or [])]


def _normalizar_fila_envio(row: Dict[str, Any]) -> Dict[str, Any]:
    d = dict(row)
    d["codigo_manual"] = str_codigo_manual_articulo(d.get("codigo_manual"))
    return d


def agrupar_filas_en_lotes(filas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Agrupa líneas de envío en lotes (uuid_lote o clave legacy)."""
    if not filas:
        return []

    buckets: Dict[str, Dict[str, Any]] = {}
    orden_keys: List[str] = []
    for row in filas:
        key = _lote_key(row)
        if key not in buckets:
            buckets[key] = {
                "lote_key": key,
                "uuid_lote": (row.get("uuid_lote") or "").strip() or None,
                "creado_en": row.get("creado_en"),
                "id_usuario": to_int_or_none(row.get("id_usuario")) or 0,
                "lineas": [],
            }
            orden_keys.append(key)
        lot = buckets[key]
        ce = row.get("creado_en")
        lot_ce = lot.get("creado_en")
        if isinstance(ce, datetime) and (
            lot_ce is None or (isinstance(lot_ce, datetime) and ce < lot_ce)
        ):
            lot["creado_en"] = ce
        lot["lineas"].append(row)

    lotes: List[Dict[str, Any]] = []
    for key in orden_keys:
        lot = buckets[key]
        lineas = lot["lineas"]
        lineas.sort(
            key=lambda r: (
                r.get("creado_en") or datetime.min,
                to_int_or_none(r.get("id_mpr_envio_produccion")) or 0,
            )
        )
        lot["n_lineas"] = len(lineas)
        lot["n_anulables"] = sum(1 for ln in lineas if ln.get("anulable"))
        lot["total_cantidad"] = sum(
            to_decimal_or_none(ln.get("cantidad")) or Decimal("0") for ln in lineas
        )
        lot["todo_anulado"] = all(bool(ln.get("anulado")) for ln in lineas)
        lot["alguno_anulado"] = any(bool(ln.get("anulado")) for ln in lineas)
        lotes.append(lot)

    lotes.sort(
        key=lambda x: x.get("creado_en") or datetime.min,
        reverse=True,
    )
    return lotes


def listar_envios_recientes(
    base_empresa: str,
    *,
    limit: int = 200,
    id_articulo: Optional[int] = None,
    incluir_anulados: bool = False,
) -> List[Dict[str, Any]]:
    """Lista envíos del tablero con datos de artículo para UI de anulación."""
    base = (base_empresa or "").strip()
    if not base:
        return []

    lim = max(1, min(int(limit or 200), 500))
    filtros = ["1=1"]
    params: List[Any] = []
    if not incluir_anulados:
        filtros.append("e.anulado = 0")
    art = to_int_or_none(id_articulo)
    if art is not None:
        filtros.append("e.id_articulo = %s")
        params.append(art)

    where_sql = " AND ".join(filtros)
    params.append(lim)
    with mysql_cursor(base, dict_cursor=True) as cursor:
        cursor.execute(
            f"""
            SELECT
                e.id_mpr_envio_produccion,
                e.id_articulo,
                e.cantidad,
                e.id_usuario,
                e.anulado,
                e.anulado_en,
                e.id_usuario_anula,
                e.uuid_lote,
                e.codigo_movimiento_mstock,
                e.creado_en,
                COALESCE(a.id_manual, '') AS codigo_manual,
                COALESCE(a.CodigoArticuloT, CAST(a.CodigoArticulo AS CHAR), '') AS codigo_articulo,
                COALESCE(a.NombreArticulo, '') AS descripcion_articulo
            FROM mpr_envio_produccion e
            LEFT JOIN articulo a ON a.IDArt = e.id_articulo
            WHERE {where_sql}
            ORDER BY e.creado_en DESC, e.id_mpr_envio_produccion DESC
            LIMIT %s
            """,
            params,
        )
        return [_normalizar_fila_envio(dict(r)) for r in (cursor.fetchall() or [])]


def obtener_envios_por_ids(
    base_empresa: str,
    envio_ids: List[int],
) -> List[Dict[str, Any]]:
    base = (base_empresa or "").strip()
    if not base or not envio_ids:
        return []

    ids = [to_int_or_none(i) for i in envio_ids]
    ids = [i for i in ids if i is not None]
    if not ids:
        return []

    placeholders = ",".join(["%s"] * len(ids))
    with mysql_cursor(base, dict_cursor=True) as cursor:
        cursor.execute(
            f"""
            SELECT id_mpr_envio_produccion, id_articulo, cantidad, id_usuario,
                   anulado, codigo_movimiento_mstock, creado_en
            FROM mpr_envio_produccion
            WHERE id_mpr_envio_produccion IN ({placeholders})
            """,
            ids,
        )
        return [_normalizar_fila_envio(dict(r)) for r in (cursor.fetchall() or [])]


def anular_envios_por_ids(
    base_empresa: str,
    envio_ids: List[int],
    id_usuario_anula: int,
) -> int:
    """Marca envíos como anulados. Retorna filas actualizadas."""
    base = (base_empresa or "").strip()
    if not base or not envio_ids:
        return 0

    ids = [to_int_or_none(i) for i in envio_ids]
    ids = [i for i in ids if i is not None]
    if not ids:
        return 0

    uid = to_int_or_none(id_usuario_anula) or 0
    placeholders = ",".join(["%s"] * len(ids))
    params: List[Any] = [uid]
    params.extend(ids)
    with mysql_cursor(base) as cursor:
        cursor.execute(
            f"""
            UPDATE mpr_envio_produccion
            SET anulado = 1,
                anulado_en = NOW(),
                id_usuario_anula = %s
            WHERE id_mpr_envio_produccion IN ({placeholders})
              AND anulado = 0
              AND codigo_movimiento_mstock IS NULL
            """,
            params,
        )
        return int(cursor.rowcount or 0)


def motivo_no_anulable(
    row: Dict[str, Any],
    saldo_anulable: Optional[Decimal],
) -> str:
    """Texto en español para filas no seleccionables en la UI."""
    if bool(row.get("anulado")):
        return "Ya anulado"
    if to_int_or_none(row.get("codigo_movimiento_mstock")) is not None:
        return "Vinculado a movimiento de stock"
    cantidad = to_decimal_or_none(row.get("cantidad")) or Decimal("0")
    saldo = saldo_anulable if saldo_anulable is not None else Decimal("0")
    if saldo <= Decimal("0"):
        return "Consumido por partes de producción"
    if saldo < cantidad:
        return "Parcialmente consumido (anulación parcial no disponible)"
    return ""
