# -*- coding: utf-8 -*-
"""
Alta transaccional MVP de Presupuesto (PRE): numeración sistema, `comp_ped` + `stockp`.

Paridad orientativa con SPEC §4–§5 (sin temporales `cuerpostockpe` ni percepciones en esta iteración).
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from core.utils.administranet_types import str_or_default, to_decimal_or_none, to_int_or_none
from reports.services.connection_pool import get_mysql_pool

logger = logging.getLogger(__name__)


def _clamp_pct_descuento(raw: Any) -> Decimal:
    """Porcentaje de descuento entre 0 y 100."""
    d = to_decimal_or_none(raw)
    if d is None:
        return Decimal("0")
    if d < 0:
        return Decimal("0")
    if d > 100:
        return Decimal("100")
    return d


def _table_exists(cursor, name: str) -> bool:
    cursor.execute(
        """
        SELECT COUNT(*) FROM information_schema.tables
        WHERE table_schema = DATABASE() AND table_name = %s
        """,
        [name],
    )
    row = cursor.fetchone()
    return bool(row and int(row[0] or 0) > 0)


def _next_id(cursor, table: str, column: str) -> Decimal:
    cursor.execute(f"SELECT COALESCE(MAX(`{column}`), 0) FROM `{table}` FOR UPDATE")
    row = cursor.fetchone()
    base = row[0] if row and row[0] is not None else 0
    try:
        return Decimal(str(base)) + Decimal("1")
    except Exception:
        return Decimal("1")


def validar_lineas_mvp(lineas: Any) -> Tuple[bool, str, List[Dict[str, Any]]]:
    """Valida y normaliza `lineas` para MVP (≥1 renglón, cantidad > 0, importe > 0)."""
    if not isinstance(lineas, list) or len(lineas) < 1:
        return False, "Debe indicar al menos un renglón.", []

    out: List[Dict[str, Any]] = []
    total = Decimal("0")

    for i, raw in enumerate(lineas):
        if not isinstance(raw, dict):
            return False, f"Renglón {i + 1}: formato inválido.", []
        cod_art = str_or_default(raw.get("codigo_articulo"), "").strip()
        if not cod_art:
            return False, f"Renglón {i + 1}: código de artículo obligatorio.", []
        desc = str_or_default(raw.get("descripcion"), cod_art)
        cant = to_decimal_or_none(raw.get("cantidad"))
        if cant is None or cant <= 0:
            return False, f"Renglón {i + 1}: la cantidad debe ser mayor que cero.", []
        p_unit = to_decimal_or_none(raw.get("precio_unitario"))
        if p_unit is None or p_unit < 0:
            return False, f"Renglón {i + 1}: precio unitario inválido.", []
        por_desc = _clamp_pct_descuento(raw.get("por_desc_linea"))
        bruto = (cant * p_unit).quantize(Decimal("0.01"))
        factor = (Decimal("100") - por_desc) / Decimal("100")
        neto = (bruto * factor).quantize(Decimal("0.01"))
        desc_renglon_imp = (bruto - neto).quantize(Decimal("0.01"))
        if neto <= 0:
            return False, f"Renglón {i + 1}: importe de línea debe ser mayor que cero.", []
        dep = to_int_or_none(raw.get("cod_deposito"))
        det_ren = str_or_default(raw.get("detalle_renglon"), "-")
        id_art = to_int_or_none(raw.get("id_art"))
        out.append(
            {
                "codigo_articulo": cod_art[:80],
                "descripcion": desc[:255] if len(desc) > 255 else desc,
                "cantidad": cant,
                "precio_unitario": p_unit,
                "por_desc_linea": por_desc,
                "bruto_renglon": bruto,
                "desc_renglon_importe": desc_renglon_imp,
                "precio_neto_renglon": neto,
                "cod_deposito": dep if dep is not None else 1,
                "detalle_renglon": det_ren,
                "id_art": id_art,
            }
        )
        total += neto

    if total <= 0:
        return False, "El importe total debe ser mayor que cero.", []

    return True, "", out


def alta_presupuesto_mvp(
    base_empresa: str,
    *,
    id_usuario: int,
    cod_sucursal: int,
    id_punto_venta: int,
    codigo_cliente: int,
    fecha: date,
    detalle: str,
    id_condventa: Optional[int],
    cond_venta: str,
    cod_viajante: Optional[int],
    lineas: List[Dict[str, Any]],
    vencimiento: Optional[date] = None,
    desc_global_pct_1: Any = None,
    desc_global_pct_2: Any = None,
) -> Tuple[bool, str, Optional[int], Optional[str]]:
    """
    Alta PRE con numeración **sistema** (talonario `TipoComprobante='PRE'`).

    Returns:
        (ok, mensaje, codigo_movimiento, nro_comprobante)
    """
    base_empresa = (base_empresa or "").strip()
    if not base_empresa:
        return False, "Sin base empresa.", None, None

    try:
        cid = int(codigo_cliente)
    except (TypeError, ValueError):
        return False, "Código de cliente inválido.", None, None
    if cid <= 0:
        return False, "Debe seleccionar un cliente válido.", None, None

    ok_ln, err_ln, lineas_norm = validar_lineas_mvp(lineas)
    if not ok_ln:
        return False, err_ln, None, None

    suma_neto_items = sum((ln["precio_neto_renglon"] for ln in lineas_norm), Decimal("0"))
    g1 = _clamp_pct_descuento(desc_global_pct_1)
    g2 = _clamp_pct_descuento(desc_global_pct_2)
    n1 = (suma_neto_items * (Decimal("100") - g1) / Decimal("100")).quantize(Decimal("0.01"))
    total_importe = (n1 * (Decimal("100") - g2) / Decimal("100")).quantize(Decimal("0.01"))
    imp_desc1 = (suma_neto_items - n1).quantize(Decimal("0.01"))
    imp_desc2 = (n1 - total_importe).quantize(Decimal("0.01"))
    if total_importe <= 0:
        return False, "El importe total tras descuentos globales debe ser mayor que cero.", None, None

    ven = vencimiento or (fecha + timedelta(days=30))
    id_cv = id_condventa if id_condventa is not None else 1
    cv_txt = str_or_default(cond_venta, "Contado")
    cv_txt = cv_txt if cv_txt != "-" else "Contado"
    det_txt = str_or_default(detalle, "-")
    fecha_control = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    nro_presup = "-"
    tipo_pedido = "Sistema"
    anulado = "No"
    estado = "Pendiente"
    imp_letras = "-"
    cod_viajante_val = int(cod_viajante) if cod_viajante is not None else 0

    pool = get_mysql_pool()
    try:
        with pool.get_connection(base_empresa) as conn:
            conn.autocommit(False)
            cursor = conn.cursor()
            try:
                if not _table_exists(cursor, "comp_ped") or not _table_exists(cursor, "codmov"):
                    conn.rollback()
                    return False, "Faltan tablas necesarias en la base (comp_ped / codmov).", None, None
                if not _table_exists(cursor, "stockp"):
                    conn.rollback()
                    return False, "La tabla stockp no existe en esta base.", None, None
                if not _table_exists(cursor, "talonarios"):
                    conn.rollback()
                    return False, "La tabla talonarios no existe en esta base.", None, None

                cursor.execute(
                    "SELECT CodigoMovimiento FROM codmov WHERE codigo = 1 FOR UPDATE",
                )
                row_cm = cursor.fetchone()
                if not row_cm:
                    conn.rollback()
                    return False, "No se pudo obtener código de movimiento (codmov).", None, None
                codigo_mov = Decimal(str(row_cm[0] or 0)) + Decimal("1")
                cursor.execute(
                    "UPDATE codmov SET CodigoMovimiento = %s WHERE codigo = 1",
                    [codigo_mov],
                )

                id_pv = int(id_punto_venta) if id_punto_venta else 1
                cursor.execute(
                    """
                    SELECT Orden, Nro FROM talonarios
                    WHERE TipoComprobante = %s AND id_punto_venta = %s
                    FOR UPDATE
                    """,
                    ["PRE", id_pv],
                )
                tal = cursor.fetchone()
                if not tal:
                    conn.rollback()
                    return (
                        False,
                        "No existe talonario PRE para el punto de venta actual. Revise talonarios en AdministraNET.",
                        None,
                        None,
                    )
                orden_talon, nro_actual = tal[0], tal[1]
                nro_actual_int = int(nro_actual or 0)
                nro_nuevo = nro_actual_int + 1
                cursor.execute(
                    "UPDATE talonarios SET Nro = %s WHERE Orden = %s",
                    [nro_nuevo, orden_talon],
                )
                nro_comprobante = f"{id_pv:04d}-{nro_nuevo:08d}"

                id_comp_ped = _next_id(cursor, "comp_ped", "id_comp_ped")

                z = Decimal("0")
                cursor.execute(
                    """
                    INSERT INTO comp_ped (
                        id_comp_ped, Fecha, TipoComprobante, NroComprobante, NroCompBusq,
                        Codigo, CodigoMovimiento,
                        ImporteVenta, ImporteVentaL,
                        ImpDesc1, ImpDesc2, PorDesc1, PorDesc2,
                        SubTotal1, SubTotal2, SubTotalGral,
                        SubTotalDesc1, SubTotalDesc2, SubtotalDesc,
                        IVA1, IVA2, Alicuota1, Alicuota2, Exento,
                        Detalle, CondVenta, id_condventa, Anulado, Estado,
                        Vencimiento, CodViajante, TipoPedido,
                        CodSucursal, IdUsuario, id_pv,
                        fecha_control, NroPresup
                    ) VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s,
                        %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s,
                        %s, %s
                    )
                    """,
                    [
                        float(id_comp_ped),
                        fecha.strftime("%Y-%m-%d"),
                        "PRE",
                        nro_comprobante,
                        nro_nuevo,
                        cid,
                        codigo_mov,
                        float(total_importe),
                        imp_letras,
                        float(imp_desc1),
                        float(imp_desc2),
                        float(g1),
                        float(g2),
                        float(suma_neto_items),
                        z,
                        float(total_importe),
                        z,
                        z,
                        float(total_importe),
                        z,
                        z,
                        z,
                        z,
                        z,
                        det_txt,
                        cv_txt,
                        id_cv,
                        anulado,
                        estado,
                        ven.strftime("%Y-%m-%d"),
                        cod_viajante_val,
                        tipo_pedido,
                        int(cod_sucursal),
                        int(id_usuario),
                        id_pv,
                        fecha_control,
                        nro_presup,
                    ],
                )

                for orden, ln in enumerate(lineas_norm, start=1):
                    id_stock = _next_id(cursor, "stockp", "id_stock")
                    cant_f = float(ln["cantidad"])
                    pu_f = float(ln["precio_unitario"])
                    neto_f = float(ln["precio_neto_renglon"])
                    por_desc_f = float(ln.get("por_desc_linea") or 0)
                    desc_ren_f = float(ln.get("desc_renglon_importe") or 0)
                    cursor.execute(
                        """
                        INSERT INTO stockp (
                            id_stock, Fecha, CodigoArticulo, Descripcion,
                            Cantidad, Salida,
                            PrecioVentaxU, PrecioNetoxR, PrecioVentaxR,
                            PorDesc, DescRenglon,
                            CodigoMovimiento, CodDeposito, `orden`, detalle,
                            Comprobante, TipoComp, NroComprobante, Anulado,
                            CodigoCP, Tipo, CodSucursal, IdUsuario, FechaControl,
                            IDArt
                        ) VALUES (
                            %s, %s, %s, %s,
                            %s, %s,
                            %s, %s, %s,
                            %s, %s,
                            %s, %s, %s, %s,
                            %s, %s, %s, %s,
                            %s, %s, %s, %s, CURRENT_TIMESTAMP,
                            %s
                        )
                        """,
                        [
                            float(id_stock),
                            fecha.strftime("%Y-%m-%d"),
                            ln["codigo_articulo"],
                            ln["descripcion"],
                            cant_f,
                            cant_f,
                            pu_f,
                            neto_f,
                            neto_f,
                            por_desc_f,
                            desc_ren_f,
                            float(codigo_mov),
                            ln["cod_deposito"],
                            orden,
                            ln["detalle_renglon"],
                            "PRE",
                            "Presupuesto",
                            nro_comprobante,
                            anulado,
                            cid,
                            "Cliente",
                            int(cod_sucursal),
                            int(id_usuario),
                            ln.get("id_art"),
                        ],
                    )

                conn.commit()
                cm_int = int(codigo_mov)
                return True, "", cm_int, nro_comprobante
            except Exception as e:
                conn.rollback()
                logger.exception("alta_presupuesto_mvp: %s", e)
                return False, str(e) or "Error al guardar el presupuesto.", None, None
            finally:
                cursor.close()
    except Exception as e:
        logger.exception("alta_presupuesto_mvp pool: %s", e)
        return False, str(e) or "Error de conexión MySQL.", None, None
