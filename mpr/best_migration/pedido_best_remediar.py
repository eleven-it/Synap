"""Remediación de PED BEST ya migrados: renumeración Synap, condición venta e IVA P2."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

import MySQLdb

from core.mysql_pool import get_connection
from core.utils.administranet_types import (
    to_date_or_none,
    to_decimal_or_none,
    to_int_or_none,
    str_or_default,
)
from ecom.services.numero_a_letras import numero_a_letras

logger = logging.getLogger(__name__)

Q2 = Decimal("0.01")
_DETALLE_MAX = 20
_MAPEO_MAX = 20

_SQL_PEDIDOS_PENDIENTES = """
    SELECT
        cp.CodigoMovimiento AS cod_mov,
        cp.NroComprobante AS nro_comprobante,
        cp.Codigo AS id_cliente,
        cp.Fecha AS fecha,
        cp.Detalle AS detalle,
        cp.ImporteVenta AS importe_venta,
        COALESCE(c.CodViajante, 0) AS cod_viajante_cliente
    FROM comp_ped cp
    LEFT JOIN cliente c ON c.Codigo = cp.Codigo
    WHERE cp.TipoComprobante = 'PED'
      AND COALESCE(cp.Anulado, 'No') = 'No'
      AND (
        cp.NroComprobante LIKE 'BEST-%'
        OR (
          (
            cp.Detalle LIKE '%%Cutover BEST%%'
            OR cp.Detalle LIKE '%%BEST orden%%'
          )
          AND TRIM(COALESCE(cp.TipoPedido, '')) = 'Migracion BEST'
        )
      )
    ORDER BY cp.CodigoMovimiento ASC
"""

_SQL_MAX_NRO_COMP_BUSQ = """
    SELECT COALESCE(MAX(NroCompBusq), 0) AS max_nro
    FROM comp_ped
    WHERE TipoComprobante = 'PED'
      AND NroComprobante NOT LIKE 'BEST-%%'
      AND id_pv = %s
"""

_SQL_STOCKP_LINEAS = """
    SELECT
        sp.id_stock AS id_stock,
        sp.IDArt AS id_art,
        sp.Salida AS salida,
        sp.Cantidad AS cantidad,
        sp.PrecioBrutoxU AS precio_bruto_u,
        sp.PrecioVentaxU AS precio_venta_u,
        COALESCE(a.Alicuota, 1) AS alic_id
    FROM stockp sp
    LEFT JOIN articulo a ON a.IDArt = sp.IDArt
    WHERE sp.CodigoMovimiento = %s
      AND COALESCE(sp.Anulado, 'No') = 'No'
    ORDER BY sp.Orden ASC, sp.id_stock ASC
"""

_SQL_UPDATE_COMP_PED = """
    UPDATE comp_ped SET
        NroComprobante = %s,
        NroCompBusq = %s,
        TipoPedido = 'Sistema',
        id_condventa = 6,
        CondVenta = 'Cta/Cte 30',
        Vencimiento = %s,
        SubTotal1 = %s,
        IVA1 = %s,
        IVA2 = 0,
        Exento = 0,
        SubTotal2 = 0,
        SubTotalGral = %s,
        SubTotalDesc1 = %s,
        SubTotalDesc2 = 0,
        SubtotalDesc = %s,
        Alicuota1 = 21,
        CodViajante = %s,
        autorizacion_sistema = 'Autorizado',
        ImporteVentaL = %s,
        cod_mov_ped_orginal = %s,
        Nro_Comp_PED_orginal = %s,
        Detalle = %s,
        observacion_interna = ''
    WHERE CodigoMovimiento = %s
"""

_SQL_UPDATE_STOCKP = """
    UPDATE stockp SET
        NroComprobante = %s,
        CodigoMovimiento = %s,
        CodViajante = %s,
        lista_precio = 1,
        tipo_art = 'Articulo',
        CodLaboratorio = 0,
        saldo = %s,
        cantidad_entregada = %s,
        PrecioBrutoxU = %s,
        PrecioNetoxU = %s,
        PrecioIVAxU = %s,
        PrecioVentaxU = %s,
        PrecioBrutoxR = %s,
        PrecioNetoxR = %s,
        PrecioIVAxR = %s,
        PrecioVentaxR = %s,
        imp_alicuota_iva = %s,
        Alicuota = %s
    WHERE id_stock = %s
"""

_SQL_TALONARIO = """
    SELECT Nro FROM talonarios
    WHERE id_punto_venta = %s AND TipoComprobante = 'PED'
    LIMIT 1
"""

_SQL_UPDATE_TALONARIO = """
    UPDATE talonarios SET Nro = %s
    WHERE id_punto_venta = %s AND TipoComprobante = 'PED'
"""


def _q2(val: Any) -> Decimal:
    d = to_decimal_or_none(val)
    if d is None:
        return Decimal("0.00")
    return d.quantize(Q2)


def format_nro_comprobante_synap(*, id_pv: int, nro_comp_busq: int) -> str:
    """Formato Synap PV-número: ``0001-00000003``."""
    pv = to_int_or_none(id_pv) or 1
    nro = to_int_or_none(nro_comp_busq) or 0
    return f"{pv:04d}-{nro:08d}"


def calc_cabecera_p2(
    importe_venta: Decimal,
    *,
    alicuota_iva: Decimal = Decimal("21"),
) -> dict[str, Decimal]:
    """
    Recalcula neto/IVA cabecera asumiendo ``importe_venta`` bruto (IVA incluido).

    Paridad checkout Synap gravado 21 %: ImporteVenta no cambia.
    """
    bruto = _q2(importe_venta)
    factor = Decimal("1") + (alicuota_iva / Decimal("100"))
    subtotal1 = _q2(bruto / factor)
    iva1 = _q2(bruto - subtotal1)
    return {
        "importe_venta": bruto,
        "subtotal1": subtotal1,
        "iva1": iva1,
        "subtotal_gral": subtotal1,
        "subtotal_desc": subtotal1,
    }


def calc_linea_p2(
    bruto_u: Decimal,
    cantidad: Decimal,
    *,
    alicuota_iva: Decimal = Decimal("21"),
) -> dict[str, Decimal]:
    """Recalcula precios unitarios y por renglón desde bruto (IVA incluido)."""
    bruto_unit = _q2(bruto_u)
    cant = _q2(cantidad)
    if cant <= 0:
        cant = Decimal("1")
    factor = Decimal("1") + (alicuota_iva / Decimal("100"))
    neto_u = _q2(bruto_unit / factor)
    iva_u = _q2(bruto_unit - neto_u)
    bruto_r = _q2(bruto_unit * cant)
    neto_r = _q2(neto_u * cant)
    iva_r = _q2(iva_u * cant)
    return {
        "precio_bruto_u": bruto_unit,
        "precio_neto_u": neto_u,
        "precio_iva_u": iva_u,
        "precio_venta_u": neto_u,
        "precio_bruto_r": bruto_r,
        "precio_neto_r": neto_r,
        "precio_iva_r": iva_r,
        "precio_venta_r": neto_r,
    }


def _resolver_detalle(detalle: str | None, old_nro: str) -> str:
    d = str_or_default(detalle, "").strip()
    low = d.lower()
    if "cutover best" in low or "best orden" in low:
        return d[:255]
    orden = old_nro
    if old_nro.upper().startswith("BEST-"):
        orden = old_nro.split("-", 1)[1]
    return f"Cutover BEST orden {orden}"[:255]


def _parse_fecha_ped(value: Any) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    iso = to_date_or_none(value)
    if iso:
        return date.fromisoformat(iso)
    return date.today()


def _vencimiento_cta_cte_30(fecha_ped: Any) -> date:
    return _parse_fecha_ped(fecha_ped) + timedelta(days=30)


def _bruto_unitario_linea(row: dict[str, Any]) -> Decimal:
    bruto = to_decimal_or_none(row.get("precio_bruto_u"))
    if bruto is not None and bruto > 0:
        return bruto
    venta = to_decimal_or_none(row.get("precio_venta_u"))
    return venta or Decimal("0")


def _cantidad_linea(row: dict[str, Any]) -> Decimal:
    salida = to_decimal_or_none(row.get("salida"))
    if salida is not None and salida > 0:
        return salida
    return to_decimal_or_none(row.get("cantidad")) or Decimal("0")


def _ajustar_talonario_si_necesario(
    cur,
    *,
    id_pv: int,
    max_nro_comp_busq: int,
    dry_run: bool,
) -> None:
    cur.execute(_SQL_TALONARIO, [id_pv])
    tal_row = cur.fetchone()
    if not tal_row:
        return
    talonario_nro = to_int_or_none(tal_row.get("Nro")) or 0
    if max_nro_comp_busq >= talonario_nro:
        nuevo = max_nro_comp_busq + 1
        if not dry_run:
            cur.execute(_SQL_UPDATE_TALONARIO, [nuevo, id_pv])


def remediar_pedidos_best(
    base_empresa: str,
    *,
    dry_run: bool = True,
    id_pv: int = 1,
    alicuota_iva: Decimal = Decimal("21"),
) -> dict[str, Any]:
    """
    Remedia PED migrados desde BEST: renumeración Synap, condición venta e IVA P2.

    Idempotente: solo procesa PED con ``NroComprobante`` tipo ``BEST-*`` o cutover
    BEST aún con ``TipoPedido='Migracion BEST'``. Tras remediar no quedan ``BEST-*`` activos.
    """
    pv = to_int_or_none(id_pv) or 1
    alic = to_decimal_or_none(alicuota_iva) or Decimal("21")

    resultado: dict[str, Any] = {
        "dry_run": dry_run,
        "revisados": 0,
        "remediados": 0,
        "omitidos": 0,
        "errores": [],
        "detalle_muestra": [],
        "mapeo_nro": {},
    }

    with get_connection(base_empresa) as conn:
        try:
            conn.autocommit(False)
            cur = conn.cursor(MySQLdb.cursors.DictCursor)

            cur.execute(_SQL_MAX_NRO_COMP_BUSQ, [pv])
            max_row = cur.fetchone() or {}
            siguiente_nro = (to_int_or_none(max_row.get("max_nro")) or 0) + 1

            cur.execute(_SQL_PEDIDOS_PENDIENTES)
            pedidos = list(cur.fetchall())

            max_nro_asignado = siguiente_nro - 1

            for row in pedidos:
                resultado["revisados"] += 1
                cod_mov = to_int_or_none(row.get("cod_mov"))
                old_nro = str_or_default(row.get("nro_comprobante"), "").strip()
                id_cliente = to_int_or_none(row.get("id_cliente"))

                if cod_mov is None or not old_nro:
                    resultado["omitidos"] += 1
                    resultado["errores"].append(
                        f"{old_nro or '?'}: CodigoMovimiento o NroComprobante inválido."
                    )
                    continue

                if not old_nro.upper().startswith("BEST-"):
                    resultado["omitidos"] += 1
                    if len(resultado["detalle_muestra"]) < _DETALLE_MAX:
                        resultado["detalle_muestra"].append(
                            {
                                "nro_anterior": old_nro,
                                "motivo": "sin prefijo BEST (ya renumerado)",
                            }
                        )
                    continue

                try:
                    nro_comp_busq = siguiente_nro
                    new_nro = format_nro_comprobante_synap(
                        id_pv=pv, nro_comp_busq=nro_comp_busq
                    )
                    siguiente_nro += 1
                    max_nro_asignado = nro_comp_busq

                    vencimiento = _vencimiento_cta_cte_30(row.get("fecha"))

                    importe_venta = _q2(
                        to_decimal_or_none(row.get("importe_venta")) or Decimal("0")
                    )
                    totales = calc_cabecera_p2(importe_venta, alicuota_iva=alic)
                    cod_viajante = to_int_or_none(row.get("cod_viajante_cliente")) or 0
                    detalle = _resolver_detalle(row.get("detalle"), old_nro)
                    importe_letras = numero_a_letras(float(importe_venta))

                    cur.execute(_SQL_STOCKP_LINEAS, [cod_mov])
                    lineas = list(cur.fetchall())

                    item_detalle: dict[str, Any] = {
                        "cod_mov": cod_mov,
                        "nro_anterior": old_nro,
                        "nro_nuevo": new_nro,
                        "nro_comp_busq": nro_comp_busq,
                        "lineas_stockp": len(lineas),
                    }

                    if dry_run:
                        resultado["remediados"] += 1
                        if len(resultado["mapeo_nro"]) < _MAPEO_MAX:
                            resultado["mapeo_nro"][old_nro] = new_nro
                        if len(resultado["detalle_muestra"]) < _DETALLE_MAX:
                            resultado["detalle_muestra"].append(item_detalle)
                        continue

                    cur.execute(
                        _SQL_UPDATE_COMP_PED,
                        (
                            new_nro,
                            nro_comp_busq,
                            vencimiento,
                            totales["subtotal1"],
                            totales["iva1"],
                            totales["subtotal_gral"],
                            totales["subtotal1"],
                            totales["subtotal_desc"],
                            cod_viajante,
                            importe_letras,
                            cod_mov,
                            new_nro,
                            detalle,
                            cod_mov,
                        ),
                    )

                    for ln in lineas:
                        id_stock = to_int_or_none(ln.get("id_stock"))
                        if id_stock is None:
                            continue
                        bruto_u = _bruto_unitario_linea(ln)
                        cant = _cantidad_linea(ln)
                        precios = calc_linea_p2(bruto_u, cant, alicuota_iva=alic)
                        alic_id = to_decimal_or_none(ln.get("alic_id")) or Decimal("1")
                        # Paridad Admin: saldo y cantidad_entregada = Salida; CM = cabecera.
                        cur.execute(
                            _SQL_UPDATE_STOCKP,
                            (
                                new_nro,
                                cod_mov,
                                cod_viajante,
                                cant,
                                cant,
                                precios["precio_bruto_u"],
                                precios["precio_neto_u"],
                                precios["precio_iva_u"],
                                precios["precio_venta_u"],
                                precios["precio_bruto_r"],
                                precios["precio_neto_r"],
                                precios["precio_iva_r"],
                                precios["precio_venta_r"],
                                alic,
                                alic_id,
                                id_stock,
                            ),
                        )

                    resultado["remediados"] += 1
                    if len(resultado["mapeo_nro"]) < _MAPEO_MAX:
                        resultado["mapeo_nro"][old_nro] = new_nro
                    if len(resultado["detalle_muestra"]) < _DETALLE_MAX:
                        resultado["detalle_muestra"].append(item_detalle)

                except Exception as exc:
                    logger.exception(
                        "Error remediando PED BEST %s (cod_mov=%s)",
                        old_nro,
                        cod_mov,
                    )
                    resultado["errores"].append(f"{old_nro}: {exc}")

            if resultado["remediados"] > 0:
                _ajustar_talonario_si_necesario(
                    cur,
                    id_pv=pv,
                    max_nro_comp_busq=max_nro_asignado,
                    dry_run=dry_run,
                )

            if dry_run:
                conn.rollback()
            else:
                conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            try:
                conn.autocommit(True)
            except Exception:
                pass

    return resultado
