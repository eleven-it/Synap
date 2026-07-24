"""Carga stock de seguridad BEST (MC.MCSS) → articulo.stock_reserva AdministraNET."""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from core.services.legacy_mysql_schema.helpers import columna_existe
from core.utils.administranet_types import to_decimal_or_none, to_int_or_none
from mpr.best_migration.connection import connect_best, fetch_dict
from mpr.best_migration.models import BestArticuloMap
from mpr.db import mysql_cursor

logger = logging.getLogger(__name__)

_SQL_MCSS = """
SELECT LTRIM(RTRIM(MCMMID)) AS best_id,
       CAST(ISNULL(MCSS, 0) AS DECIMAL(18, 4)) AS mcss
FROM MC
WHERE MCCCID = %s
"""


def _cargar_mapa_articulos(base_empresa: str) -> dict[str, int]:
    """best_id_articulo → admin IDArt (solo VALIDADO con admin_idart)."""
    qs = BestArticuloMap.objects.filter(
        base_empresa=base_empresa,
        estado=BestArticuloMap.Estado.VALIDADO,
        validado=True,
        admin_idart__isnull=False,
    )
    out: dict[str, int] = {}
    for obj in qs:
        bid = (obj.best_id_articulo or "").strip()
        idart = to_int_or_none(obj.admin_idart)
        if bid and idart is not None:
            out[bid] = idart
    return out


def _leer_stock_reserva_actual(
    base_empresa: str, idarts: list[int]
) -> dict[int, Decimal]:
    if not idarts:
        return {}
    placeholders = ",".join(["%s"] * len(idarts))
    sql = (
        f"SELECT IDArt, COALESCE(stock_reserva, 0) AS stock_reserva "
        f"FROM articulo WHERE IDArt IN ({placeholders})"
    )
    out: dict[int, Decimal] = {}
    with mysql_cursor(base_empresa, dict_cursor=True) as cur:
        cur.execute(sql, tuple(idarts))
        for row in cur.fetchall() or []:
            aid = to_int_or_none(row.get("IDArt"))
            if aid is None:
                continue
            out[aid] = to_decimal_or_none(row.get("stock_reserva")) or Decimal("0")
    return out


def _idarts_tipo_terminado(base_empresa: str, idarts: list[int]) -> set[int]:
    """IDArt con tipo_art_fab Terminado (solo ellos reciben stock_reserva desde BEST)."""
    if not idarts:
        return set()
    placeholders = ",".join(["%s"] * len(idarts))
    sql = f"""
        SELECT IDArt
        FROM articulo
        WHERE IDArt IN ({placeholders})
          AND LOWER(COALESCE(TRIM(tipo_art_fab), '')) = 'terminado'
    """
    out: set[int] = set()
    with mysql_cursor(base_empresa, dict_cursor=True) as cur:
        cur.execute(sql, tuple(idarts))
        for row in cur.fetchall() or []:
            aid = to_int_or_none(row.get("IDArt"))
            if aid is not None:
                out.add(aid)
    return out


def _verificar_columna_stock_reserva(base_empresa: str) -> None:
    with mysql_cursor(base_empresa, dict_cursor=False) as cur:
        if not columna_existe(cur, "articulo", "stock_reserva"):
            raise ValueError(
                "La columna articulo.stock_reserva no existe en la base "
                f"{base_empresa!r}. Ejecutá la migración de esquema MPR "
                "(core/services/legacy_mysql_schema/catalog.py) antes de cargar."
            )


def migrar_stock_reserva_best(
    base_empresa: str,
    *,
    dry_run: bool = True,
    mcccid: int = 4003,
    solo_mapeados: bool = True,
    incluir_ceros: bool = False,
    id_usuario: int | None = None,
) -> dict[str, Any]:
    """
    Migra MCSS (pares) desde MC (centro de costo terminado por defecto 4003)
    hacia articulo.stock_reserva en AdministraNET.

    Solo escribe en artículos con ``tipo_art_fab = Terminado`` (el colchón de
    reserva alimenta demanda pack; no aplica a fabricados/componentes BOM).

    Por defecto (v1) solo actualiza filas con MCSS>0 para no pisar reservas
    manuales a cero. Con incluir_ceros=True también escribe 0 en mapeados sin SS.
    """
    base = (base_empresa or "").strip()
    if not base:
        raise ValueError("Indique base_empresa.")

    conn = connect_best()
    try:
        rows = fetch_dict(conn, _SQL_MCSS, (mcccid,))
    finally:
        conn.close()

    leidos = len(rows)
    con_mcss = sum(
        1 for r in rows if (to_decimal_or_none(r.get("mcss")) or Decimal("0")) > 0
    )

    mapa = _cargar_mapa_articulos(base)
    mapeados = 0
    huerfanos: list[dict[str, Any]] = []
    candidatos: list[dict[str, Any]] = []

    for row in rows:
        best_id = (row.get("best_id") or "").strip()
        mcss = to_decimal_or_none(row.get("mcss")) or Decimal("0")
        if mcss <= 0 and not incluir_ceros:
            continue
        idart = mapa.get(best_id)
        if idart is None:
            if mcss > 0:
                huerfanos.append({"best_id": best_id, "mcss": float(mcss)})
            if solo_mapeados:
                continue
            continue
        mapeados += 1
        candidatos.append(
            {"best_id": best_id, "idart": idart, "mcss": mcss}
        )

    result: dict[str, Any] = {
        "dry_run": dry_run,
        "mcccid": mcccid,
        "leidos": leidos,
        "con_mcss": con_mcss,
        "mapeados": mapeados,
        "omitidos_no_terminado": 0,
        "actualizados": 0,
        "sin_cambio": 0,
        "huerfanos": len(huerfanos),
        "huerfanos_muestra": huerfanos[:20],
        "errores": [],
        "muestra": [],
        "post_actualizar_ok": None,
        "post_actualizar_mensaje": None,
    }

    if not candidatos:
        result["muestra"] = []
        return result

    idarts = [c["idart"] for c in candidatos]
    terminados = _idarts_tipo_terminado(base, idarts)
    if terminados:
        omitidos = [c for c in candidatos if c["idart"] not in terminados]
        result["omitidos_no_terminado"] = len(omitidos)
        candidatos = [c for c in candidatos if c["idart"] in terminados]
    else:
        result["omitidos_no_terminado"] = len(candidatos)
        candidatos = []

    if not candidatos:
        result["muestra"] = []
        return result

    idarts = [c["idart"] for c in candidatos]
    actuales = _leer_stock_reserva_actual(base, idarts)

    pendientes: list[dict[str, Any]] = []
    for c in candidatos:
        idart = c["idart"]
        nuevo = c["mcss"]
        actual = actuales.get(idart, Decimal("0"))
        if actual == nuevo:
            result["sin_cambio"] += 1
            continue
        pendientes.append({**c, "actual": actual})

    result["muestra"] = [
        {
            "best_id": p["best_id"],
            "idart": p["idart"],
            "mcss": float(p["mcss"]),
            "actual": float(p["actual"]),
        }
        for p in pendientes[:15]
    ]

    if dry_run:
        result["actualizados"] = len(pendientes)
        return result

    _verificar_columna_stock_reserva(base)

    actualizados = 0
    errores: list[str] = []
    with mysql_cursor(base_empresa, dict_cursor=False) as cur:
        for p in pendientes:
            idart = p["idart"]
            nuevo = to_decimal_or_none(p["mcss"])
            try:
                cur.execute(
                    """
                    UPDATE articulo
                    SET stock_reserva = %s
                    WHERE IDArt = %s
                      AND LOWER(COALESCE(TRIM(tipo_art_fab), '')) = 'terminado'
                    """,
                    (nuevo, idart),
                )
                if cur.rowcount:
                    actualizados += 1
            except Exception as exc:
                msg = f"IDArt {idart} (BEST {p['best_id']}): {exc}"
                errores.append(msg)
                logger.error("migrar_stock_reserva_best: %s", msg)

    result["actualizados"] = actualizados
    result["errores"] = errores

    if actualizados > 0 and id_usuario is not None:
        from mpr.services import actualizar_pedidos_produccion

        uid = to_int_or_none(id_usuario)
        try:
            ok, msg = actualizar_pedidos_produccion(base, uid)
            result["post_actualizar_ok"] = ok
            result["post_actualizar_mensaje"] = msg or ""
            if not ok:
                result["errores"].append(
                    f"Post actualizar_pedidos_produccion: {msg or 'error desconocido'}"
                )
        except Exception as exc:
            logger.exception("post actualizar_pedidos_produccion tras stock_reserva")
            result["post_actualizar_ok"] = False
            result["post_actualizar_mensaje"] = str(exc)
            result["errores"].append(f"Post actualizar_pedidos_produccion: {exc}")

    return result
