# -*- coding: utf-8 -*-
"""Cálculo y persistencia legacy de precios en articulo + precios_historial."""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Mapping, Optional, Sequence

from core.mysql_pool import mysql_cursor
from core.utils.administranet_types import to_decimal_or_none, to_int_or_none

logger = logging.getLogger(__name__)

Q2 = Decimal("0.01")
LISTAS_VALIDAS = frozenset({1, 2, 3, 4, 5})

_CAMPOS_NETO = {1: "Precio1V", 2: "Precio2V", 3: "Precio3V", 4: "Precio4V", 5: "Precio5V"}
_CAMPOS_FINAL = {1: "Precio1VI", 2: "Precio2VI", 3: "Precio3VI", 4: "Precio4VI", 5: "Precio5VI"}
_CAMPOS_UTIL = {1: "Util1", 2: "Util2", 3: "Util3", 4: "Util4", 5: "Util5"}


def q2(value: Decimal) -> Decimal:
    return value.quantize(Q2, rounding=ROUND_HALF_UP)


def calcular_final_desde_neto(
    neto: Decimal,
    *,
    alicuota_iva: Decimal,
    impuesto_interno_pct: Decimal,
) -> Decimal:
    iva = neto * alicuota_iva / Decimal("100")
    interno = neto * impuesto_interno_pct / Decimal("100")
    return q2(neto + iva + interno)


def calcular_neto_desde_final(
    final: Decimal,
    *,
    alicuota_iva: Decimal,
    impuesto_interno_pct: Decimal,
) -> Decimal:
    factor = Decimal("1") + (alicuota_iva + impuesto_interno_pct) / Decimal("100")
    if factor <= 0:
        return Decimal("0.00")
    return q2(final / factor)


def calcular_util_desde_neto(precio_costo: Decimal, precio_neto: Decimal) -> Decimal:
    if precio_costo <= 0:
        return Decimal("0")
    return q2((precio_neto - precio_costo) * Decimal("100") / precio_costo)


def _nombre_tabla(cursor, nombre_lower: str) -> Optional[str]:
    cursor.execute("SHOW TABLES")
    for row in cursor.fetchall():
        nombre = (row[0] if not isinstance(row, dict) else list(row.values())[0]) or ""
        nombre = str(nombre).strip()
        if nombre.lower() == nombre_lower:
            return nombre
    return None


def _leer_articulo_precios(cursor, tbl_art: str, id_articulo: int) -> Optional[Dict[str, Any]]:
    cols = [
        "IDArt",
        "NombreArticulo",
        "PrecioCosto",
        "impuesto_interno",
        "Alicuota",
        "CodigoProveedor",
        "stock_reserva",
    ]
    for i in range(1, 6):
        cols.append(_CAMPOS_NETO[i])
        cols.append(_CAMPOS_FINAL[i])
        cols.append(_CAMPOS_UTIL[i])
    cols.append("PNOficial")
    cols.append("PFOficial")
    cols_sql = ", ".join(f"a.`{c}`" for c in cols)
    tart = tbl_art.replace("`", "``")
    cursor.execute(
        f"""
        SELECT {cols_sql}, COALESCE(i.Alicuota, 21) AS alicuota_iva_pct
        FROM `{tart}` a
        LEFT JOIN iva i ON i.ID = a.Alicuota
        WHERE a.IDArt = %s
        LIMIT 1
        """,
        (id_articulo,),
    )
    row = cursor.fetchone()
    return dict(row) if row else None


def insertar_precios_historial(
    cursor,
    *,
    tbl_hist: str,
    articulo: Mapping[str, Any],
    id_usuario: Optional[int],
    tipo_modificacion: str = "Synap precios terminados",
) -> None:
    th = tbl_hist.replace("`", "``")
    cursor.execute(
        f"""
        INSERT INTO `{th}` (
            fecha, tipo_modificacion, id_articulo,
            util1, util2, util3, util4, util5,
            precio_neto1, precio_neto2, precio_neto3, precio_neto4, precio_neto5,
            precio_neto_of, alicuota_iva,
            precio_iva1, precio_iva2, precio_iva3, precio_iva4, precio_iva5,
            precio_iva_of, nombre_articulo, precio_costo, id_usuario, id_proveedor
        ) VALUES (
            %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s
        )
        """,
        (
            date.today(),
            tipo_modificacion,
            articulo.get("IDArt"),
            articulo.get("Util1"),
            articulo.get("Util2"),
            articulo.get("Util3"),
            articulo.get("Util4"),
            articulo.get("Util5"),
            articulo.get("Precio1V"),
            articulo.get("Precio2V"),
            articulo.get("Precio3V"),
            articulo.get("Precio4V"),
            articulo.get("Precio5V"),
            articulo.get("PNOficial"),
            articulo.get("alicuota_iva_pct") or articulo.get("Alicuota"),
            articulo.get("Precio1VI"),
            articulo.get("Precio2VI"),
            articulo.get("Precio3VI"),
            articulo.get("Precio4VI"),
            articulo.get("Precio5VI"),
            articulo.get("PFOficial"),
            articulo.get("NombreArticulo"),
            articulo.get("PrecioCosto"),
            id_usuario,
            articulo.get("CodigoProveedor"),
        ),
    )


def aplicar_cambios_articulo(
    base_empresa: str,
    id_articulo: int,
    cambios: Dict[str, Any],
    *,
    id_usuario: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Aplica cambios de precios y/o reserva a un artículo.
    cambios: {precios: {lista: {neto, final}}, stock_reserva?: number}
    """
    listas_precios: Dict[int, Dict[str, Any]] = cambios.get("precios") or {}
    nueva_reserva = cambios.get("stock_reserva")

    with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
        tbl_art = _nombre_tabla(cursor, "articulo")
        tbl_hist = _nombre_tabla(cursor, "precios_historial")
        if not tbl_art:
            return {"ok": False, "error": "tabla_articulo_no_encontrada"}

        art = _leer_articulo_precios(cursor, tbl_art, id_articulo)
        if not art:
            return {"ok": False, "error": "articulo_no_encontrado"}

        alic = Decimal(str(art.get("alicuota_iva_pct") or 21))
        imp_int = Decimal(str(art.get("impuesto_interno") or 0))
        costo = Decimal(str(art.get("PrecioCosto") or 0))

        sets: List[str] = []
        params: List[Any] = []

        for lista_id, vals in listas_precios.items():
            lista = to_int_or_none(lista_id)
            if lista not in LISTAS_VALIDAS:
                continue
            neto_raw = vals.get("neto")
            final_raw = vals.get("final")
            neto = to_decimal_or_none(neto_raw)
            final = to_decimal_or_none(final_raw)
            if neto is None and final is None:
                continue
            if neto is None and final is not None:
                neto = calcular_neto_desde_final(
                    Decimal(str(final)), alicuota_iva=alic, impuesto_interno_pct=imp_int
                )
            elif final is None and neto is not None:
                final = calcular_final_desde_neto(
                    Decimal(str(neto)), alicuota_iva=alic, impuesto_interno_pct=imp_int
                )
            else:
                neto = Decimal(str(neto))
                final = Decimal(str(final))

            neto = q2(neto)
            final = q2(final)
            util = calcular_util_desde_neto(costo, neto)

            art[_CAMPOS_NETO[lista]] = neto
            art[_CAMPOS_FINAL[lista]] = final
            art[_CAMPOS_UTIL[lista]] = util

            sets.append(f"`{_CAMPOS_NETO[lista]}` = %s")
            params.append(float(neto))
            sets.append(f"`{_CAMPOS_FINAL[lista]}` = %s")
            params.append(float(final))
            sets.append(f"`{_CAMPOS_UTIL[lista]}` = %s")
            params.append(float(util))

        if nueva_reserva is not None:
            reserva = to_decimal_or_none(nueva_reserva)
            if reserva is not None and reserva < 0:
                reserva = Decimal("0")
            if reserva is not None:
                sets.append("`stock_reserva` = %s")
                params.append(float(reserva))
                art["stock_reserva"] = reserva

        if not sets:
            return {"ok": True, "actualizado": False}

        tart = tbl_art.replace("`", "``")
        params.append(id_articulo)
        cursor.execute(
            f"UPDATE `{tart}` SET {', '.join(sets)} WHERE IDArt = %s",
            tuple(params),
        )

        if tbl_hist:
            try:
                insertar_precios_historial(
                    cursor,
                    tbl_hist=tbl_hist,
                    articulo=art,
                    id_usuario=id_usuario,
                )
            except Exception as exc:
                logger.warning(
                    "insertar_precios_historial %s id=%s: %s",
                    base_empresa,
                    id_articulo,
                    exc,
                    exc_info=True,
                )

    return {"ok": True, "actualizado": True, "id_articulo": id_articulo}


def guardar_lote(
    base_empresa: str,
    items: Sequence[Dict[str, Any]],
    *,
    id_usuario: Optional[int] = None,
) -> Dict[str, Any]:
    ok_ids: List[int] = []
    errores: List[Dict[str, Any]] = []
    for item in items:
        aid = to_int_or_none(item.get("id_articulo"))
        if aid is None:
            errores.append({"item": item, "error": "id_articulo_invalido"})
            continue
        res = aplicar_cambios_articulo(
            base_empresa, aid, item, id_usuario=id_usuario
        )
        if res.get("ok") and res.get("actualizado"):
            ok_ids.append(aid)
        elif not res.get("ok"):
            errores.append({"id_articulo": aid, "error": res.get("error")})

    return {
        "ok": len(errores) == 0,
        "actualizados": len(ok_ids),
        "ids": ok_ids,
        "errores": errores,
    }
