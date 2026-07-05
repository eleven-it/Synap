"""
Persistencia completa del recibo mayoristapp en una transacción MySQL legacy.

Paridad ``guardar_recibo()`` en json_recibo.php: cuentacliente, cliente.saldo,
imputación, a cuenta, efectivo, cheques, tarjetas, transferencias, retenciones y descuentos.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Dict

from core.mysql_pool import get_mysql_pool
from core.utils.administranet_types import to_int_or_none, str_or_default
from ecom.services.recibo_asiento_contable_service import (
    debe_generar_asiento_contable,
    generar_asiento_contable_recibo,
)
from ecom.services.recibo_saldo_favor_service import persistir_consumo_saldo_favor
from tiendanube_administranet.services.adelanto_recibo_service import (
    allocate_codigo_movimiento,
    allocate_nro_recibo,
)


def _to_decimal(value: Any, default: str = "0") -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(default)


def _f(value: Decimal | float | int) -> float:
    return float(value)


def _load_cliente_saldo(cursor, cod_cliente: int) -> float:
    cursor.execute(
        "SELECT COALESCE(saldo, 0) AS saldo FROM cliente WHERE Codigo = %s LIMIT 1",
        [cod_cliente],
    )
    row = cursor.fetchone()
    if not row:
        raise ValueError(f"Cliente {cod_cliente} no encontrado.")
    return float(row["saldo"] or 0)


def _calcular_totales_guardar(recibo: Dict[str, Any]) -> Dict[str, float]:
    coti = 1.0
    total_ef_p = 0.0
    total_ef_d = 0.0
    total_pago = 0.0
    if isinstance(recibo.get("efectivo"), dict):
        ef = recibo["efectivo"]
        coti = float(ef.get("cotizacion") or 1)
        total_ef_p = float(ef.get("pesos") or 0)
        total_ef_d = float(ef.get("dolar") or 0)
        total_pago = float(ef.get("total") or 0)

    total_cheque = float((recibo.get("cheques") or {}).get("total") or 0)
    total_tarjeta = float((recibo.get("tarjeta") or {}).get("total") or 0)
    total_transf = float((recibo.get("transferencia") or {}).get("total") or 0)
    total_imputacion = float(recibo.get("totalImputado") or 0)
    total_descuento = float((recibo.get("descuento") or {}).get("total") or 0)
    total_retenciones = float((recibo.get("retencion") or {}).get("total") or 0)

    total_saldo_favor = float((recibo.get("saldoAFavor") or {}).get("total") or 0)
    total_pago_rec = total_pago + total_cheque + total_transf + total_tarjeta + total_saldo_favor
    total_recibo = total_pago_rec + total_retenciones
    if total_recibo <= 0 and total_imputacion > 0:
        total_recibo = total_imputacion

    return {
        "coti_dolar": coti,
        "total_efectivo_p": total_ef_p,
        "total_efectivo_d": total_ef_d,
        "total_pago": total_pago,
        "total_cheque": total_cheque,
        "total_tarjeta": total_tarjeta,
        "total_transferencia": total_transf,
        "total_imputacion_rec": total_imputacion,
        "total_descuento": total_descuento,
        "total_retenciones": total_retenciones,
        "total_pago_rec": total_pago_rec,
        "total_saldo_favor": total_saldo_favor,
        "total_recibo": total_recibo,
    }


def guardar_recibo_completo_legacy(
    *,
    base_empresa: str,
    session_user: Dict[str, Any],
    recibo: Dict[str, Any],
) -> Dict[str, Any]:
    if (recibo.get("clase") or "").strip().lower() != "imputacion":
        raise ValueError("Solo se soporta clase='imputacion' en esta etapa.")

    facturas = recibo.get("facturas") or {}
    if not isinstance(facturas, dict) or not facturas:
        raise ValueError("No hay facturas imputadas para guardar.")

    cod_cliente = int(recibo["codCliente"])
    id_usuario = int(session_user.get("id_usuario") or 0)
    cod_sucursal = int(session_user.get("id_sucursal") or 1)
    cod_viajante = int(recibo.get("codViajante") or session_user.get("CodViajante") or 0)
    id_pv = int(recibo.get("idPv") or session_user.get("id_punto_venta") or 0)

    tipo_rec = "Sistema" if str(recibo.get("tipo") or "").lower() == "sistema" else "Talonario"
    tot = _calcular_totales_guardar(recibo)
    total_recibo = tot["total_recibo"]

    pool = get_mysql_pool()
    with pool.get_connection(base_empresa) as conn:
        conn.autocommit(False)
        try:
            c = conn.cursor()
            saldo_cliente = _load_cliente_saldo(c, cod_cliente)
            saldo_cliente_nuevo = saldo_cliente - total_recibo

            if not recibo.get("codmov"):
                recibo["codmov"] = allocate_codigo_movimiento(c)

            if tipo_rec == "Sistema" and str(recibo.get("nroRecibo") or "") in ("0-0", "", "None"):
                nro_recibo, nro_comp = allocate_nro_recibo(c, id_pv)
                recibo["nroRecibo"] = nro_recibo
                recibo["nroCompBusq"] = nro_comp

            nro_recibo = str(recibo["nroRecibo"])
            nro_comp_busq = str(recibo.get("nroCompBusq") or nro_recibo)
            cod_mov = int(recibo["codmov"])

            total_transf_sql = ""
            transf_extra_vals: list = []
            if isinstance(recibo.get("transferencia"), dict):
                total_transf_sql = ", total_trans=%s"
                transf_extra_vals = [tot["total_transferencia"]]

            c.execute(
                f"""
                INSERT INTO cuentacliente (
                    Fecha, TipoComprobante, NroComprobante, NroCompBusq, id_pv, TipoREC,
                    Detalle, anulado, ReciboMov, ImporteCobro, CondVenta, idUsuario, codSucursal,
                    Codigo, CodigoMovimiento, TipoRecibo, CotiDolar, ReciboPesos, ReciboDolar,
                    TotalPago, TotalEfectivoP, TotalEfectivoD, TotalCheque, TotalImputacionRec,
                    NetoImputacionRec, TotalPagoRec, TotalRecibo, TotalDescRec, TotalRetencion,
                    Total_Tarjeta, Total_MC, Total_Ingreso, CodViajante, Saldo
                    {total_transf_sql}
                ) VALUES (
                    %s, 'REC', %s, %s, %s, %s,
                    'WEB', 'No', 0, %s, '-', %s, %s,
                    %s, %s, 'I', %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, 0, 0, %s, %s
                    {', %s' if total_transf_sql else ''}
                )
                """,
                [
                    date.today(),
                    nro_recibo,
                    nro_comp_busq,
                    id_pv,
                    tipo_rec,
                    total_recibo,
                    id_usuario,
                    cod_sucursal,
                    cod_cliente,
                    cod_mov,
                    tot["coti_dolar"],
                    tot["total_efectivo_p"],
                    tot["total_efectivo_d"],
                    tot["total_pago"],
                    tot["total_efectivo_p"],
                    tot["total_efectivo_d"],
                    tot["total_cheque"],
                    tot["total_imputacion_rec"],
                    tot["total_imputacion_rec"],
                    tot["total_pago_rec"],
                    total_recibo,
                    tot["total_descuento"],
                    tot["total_retenciones"],
                    tot["total_tarjeta"],
                    cod_viajante,
                    saldo_cliente_nuevo,
                    *transf_extra_vals,
                ],
            )

            c.execute(
                "UPDATE cliente SET saldo = %s WHERE Codigo = %s",
                [saldo_cliente_nuevo, cod_cliente],
            )

            _persistir_imputacion(c, recibo=recibo, cod_mov=cod_mov, nro_recibo=nro_recibo,
                                  cod_cliente=cod_cliente, cod_viajante=cod_viajante,
                                  id_usuario=id_usuario, total_recibo=total_recibo)

            if recibo.get("aCuenta"):
                _persistir_a_cuenta(
                    c,
                    recibo=recibo,
                    cod_mov=cod_mov,
                    nro_recibo=nro_recibo,
                    cod_cliente=cod_cliente,
                    cod_viajante=cod_viajante,
                )

            if isinstance(recibo.get("efectivo"), dict):
                _persistir_efectivo_caja(
                    c,
                    recibo=recibo,
                    cod_mov=cod_mov,
                    nro_recibo=nro_recibo,
                    nro_comp_busq=nro_comp_busq,
                    cod_cliente=cod_cliente,
                    id_usuario=id_usuario,
                    cod_sucursal=cod_sucursal,
                    tot=tot,
                )

            if isinstance(recibo.get("cheques"), dict) and recibo["cheques"].get("listado"):
                _persistir_cheques(
                    c,
                    recibo=recibo,
                    cod_mov=cod_mov,
                    nro_recibo=nro_recibo,
                    cod_cliente=cod_cliente,
                    id_usuario=id_usuario,
                    cod_sucursal=cod_sucursal,
                )

            if isinstance(recibo.get("tarjeta"), dict) and recibo["tarjeta"].get("listado"):
                _persistir_tarjetas(
                    c,
                    recibo=recibo,
                    cod_mov=cod_mov,
                    nro_recibo=nro_recibo,
                    cod_cliente=cod_cliente,
                    id_usuario=id_usuario,
                    cod_sucursal=cod_sucursal,
                )

            if isinstance(recibo.get("transferencia"), dict) and recibo["transferencia"].get("items"):
                _persistir_transferencias(
                    c,
                    recibo=recibo,
                    cod_mov=cod_mov,
                    cod_cliente=cod_cliente,
                    id_usuario=id_usuario,
                    cod_sucursal=cod_sucursal,
                )

            if isinstance(recibo.get("retencion"), dict) and recibo["retencion"].get("lista"):
                _persistir_retenciones(c, recibo=recibo, cod_mov=cod_mov, nro_recibo=nro_recibo, cod_cliente=cod_cliente)

            if isinstance(recibo.get("descuento"), dict) and _to_decimal(recibo["descuento"].get("total")) > 0:
                _persistir_descuento(c, recibo=recibo, cod_mov=cod_mov, nro_recibo=nro_recibo, cod_cliente=cod_cliente)

            if isinstance(recibo.get("saldoAFavor"), dict) and recibo["saldoAFavor"].get("lineas"):
                persistir_consumo_saldo_favor(
                    c,
                    recibo=recibo,
                    cod_mov=cod_mov,
                    nro_recibo=nro_recibo,
                    cod_cliente=cod_cliente,
                    cod_viajante=cod_viajante,
                    id_usuario=id_usuario,
                )

            asiento_nro = None
            if debe_generar_asiento_contable(c, id_pv=id_pv):
                asiento = generar_asiento_contable_recibo(
                    c,
                    recibo=recibo,
                    cod_mov=cod_mov,
                    id_usuario=id_usuario,
                )
                if asiento.get("estado") != "ok":
                    raise ValueError(
                        f"Error en asiento contable: {asiento.get('variable')} — {asiento.get('sql')}"
                    )
                asiento_nro = asiento.get("asiento")

            conn.commit()
            result = {
                "msg": "ok",
                "codigo_movimiento": cod_mov,
                "nro_recibo": nro_recibo,
                "saldo_cliente": saldo_cliente_nuevo,
                "asiento": asiento_nro if asiento_nro is not None else "no",
            }
            return result
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.autocommit(True)


def _persistir_imputacion(
    c,
    *,
    recibo: Dict[str, Any],
    cod_mov: int,
    nro_recibo: str,
    cod_cliente: int,
    cod_viajante: int,
    id_usuario: int,
    total_recibo: float,
) -> None:
    for f in (recibo.get("facturas") or {}).values():
        saldo_n = _to_decimal(f.get("saldoN"))
        aimputar = _to_decimal(f.get("aimputar"))
        cancelado_base = _to_decimal(f.get("cancelado"))
        cancelado_new = cancelado_base + aimputar
        estado = "Canc" if saldo_n == Decimal("0") else "N/Canc"
        codmov_fact = int(f.get("codmovFact"))
        id_rf = int(f.get("idrecibofactura"))

        if estado == "Canc":
            c.execute(
                """
                UPDATE cuentacliente SET estado='Canc', ReciboMov=%s, Recibo=%s
                WHERE CodigoMovimiento=%s
                """,
                [cod_mov, nro_recibo, codmov_fact],
            )

        c.execute(
            """
            UPDATE recibo_factura
            SET cancelado=%s, Saldo=%s, estado=%s, Imp='Si',
                ReciboMov=%s, Recibo=%s, CodViajante=%s
            WHERE id_recibo_factura=%s
            """,
            [_f(aimputar + cancelado_base), _f(saldo_n), estado, cod_mov, nro_recibo, cod_viajante, id_rf],
        )

        c.execute(
            """
            INSERT INTO imputacion (
                fecha_fac_nd, tipo_comp_fac_nd, nro_comp_fac_nd, codmov_fac_nd,
                fecha_nc_rec, tipo_comp_nc_rec, nro_comp_nc_rec, codmov_nc_rec, Tipo,
                importe_fac_nd, importe_cancelado_fac_nd, importe_saldo_fac_nd, estado_fac_nd,
                importe_nc_rec, importe_cancelado_nc_rec, importe_saldo_nc_rec, estado_nc_rec,
                id_usuario, id_cliente
            ) VALUES (%s, %s, %s, %s, %s, 'REC', %s, %s, 'Imputación', %s, %s, %s, %s, %s, %s, 0, 'Canc', %s, %s)
            """,
            [
                f.get("fecha"),
                f.get("tipocomprobante"),
                f.get("nrofactura"),
                codmov_fact,
                date.today(),
                nro_recibo,
                cod_mov,
                _f(_to_decimal(f.get("importe"))),
                _f(aimputar),
                _f(saldo_n),
                estado,
                total_recibo,
                _f(aimputar),
                id_usuario,
                cod_cliente,
            ],
        )

        c.execute(
            """
            INSERT INTO recibo_factura_par (
                cancelado, CanceladoActual, Saldo, estado, Imp, ReciboMov, Recibo,
                Fecha, TipoComprobante, Importe, NroComprobante, Vencimiento,
                CodigoMovimiento, Codigo, CondVenta, ImporteNC, seleccionado, ACuenta, anulado, Modificado
            ) VALUES (%s, %s, %s, %s, 'Si', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Si', NULL, 'No', %s)
            """,
            [
                _f(cancelado_new),
                _f(aimputar),
                _f(saldo_n),
                estado,
                cod_mov,
                nro_recibo,
                f.get("fecha"),
                f.get("tipocomprobante"),
                _f(_to_decimal(f.get("importe"))),
                f.get("nrofactura"),
                f.get("vencimiento"),
                codmov_fact,
                cod_cliente,
                f.get("condventa") or "-",
                _f(_to_decimal(f.get("importe"))),
                "Si" if estado == "Canc" else "No",
            ],
        )


def _persistir_a_cuenta(c, *, recibo, cod_mov, nro_recibo, cod_cliente, cod_viajante) -> None:
    monto = float(recibo["aCuenta"])
    c.execute(
        """
        INSERT INTO recibo_factura (
            Fecha, TipoComprobante, Importe, cancelado, Saldo, ImporteNC,
            NroComprobante, estado, CodigoMovimiento, Codigo, Imp, anulado, Modificado, Tipo, CodViajante
        ) VALUES (%s, 'REC', %s, 0, %s, %s, %s, 'N/Canc', %s, %s, 'No', 'No', 'No', 'Cliente', %s)
        """,
        [date.today(), monto, monto, monto, nro_recibo, cod_mov, cod_cliente, cod_viajante],
    )
    c.execute(
        """
        INSERT INTO recibo_factura_par (
            cancelado, CanceladoActual, Saldo, estado, Imp, ReciboMov, Recibo,
            Fecha, TipoComprobante, Importe, NroComprobante, CodigoMovimiento, Codigo,
            ImporteNC, anulado, Modificado, seleccionado
        ) VALUES (0, 0, %s, 'N/Canc', 'Si', %s, %s, %s, 'REC', %s, %s, %s, %s, %s, 'No', 'No', 'No')
        """,
        [monto, cod_mov, nro_recibo, date.today(), monto, nro_recibo, cod_mov, cod_cliente, monto],
    )


def _persistir_efectivo_caja(c, *, recibo, cod_mov, nro_recibo, nro_comp_busq, cod_cliente, id_usuario, cod_sucursal, tot) -> None:
    ef = recibo["efectivo"]
    id_caja = int(ef.get("idCaja") or 0)
    if id_caja <= 0:
        return

    c.execute("SELECT id_caja_saldo, moneda, saldo FROM caja_saldo WHERE id_caja = %s", [id_caja])
    cajas = {row["moneda"]: row for row in (c.fetchall() or [])}

    for moneda, monto in (("Pesos", tot["total_efectivo_p"]), ("Dolares", tot["total_efectivo_d"])):
        if monto <= 0:
            continue
        row = cajas.get(moneda) or cajas.get("Pesos")
        saldo_prev = float(row["saldo"] if row else 0)
        saldo_new = saldo_prev + monto
        c.execute(
            """
            INSERT INTO caja (
                Fecha, tipo_comprobante, Tipo, nro_comprobante, nro_comp_busq,
                egreso, id_usuario, cod_sucursal, Moneda, ingreso, Detalle,
                Codigo_Movimiento, Codigo_Cliente, codigo_prov, tipo_cp, anulado, Saldo, id_caja_abm_origen
            ) VALUES (%s, 'REC', 'Cobranza Efectivo', %s, %s, 0, %s, %s, %s, %s, '', %s, %s, 1, 'Cliente', 'No', %s, %s)
            """,
            [date.today(), nro_recibo, nro_comp_busq, id_usuario, cod_sucursal, moneda, monto, cod_mov, cod_cliente, saldo_new, id_caja],
        )
        if row:
            c.execute(
                "UPDATE caja_saldo SET saldo=%s, id_usuario=%s, cod_sucursal=%s WHERE id_caja_saldo=%s",
                [saldo_new, id_usuario, cod_sucursal, row["id_caja_saldo"]],
            )


def _persistir_cheques(c, *, recibo, cod_mov, nro_recibo, cod_cliente, id_usuario, cod_sucursal) -> None:
    ch = recibo["cheques"]
    id_caja = int(ch.get("idCajaCheque") or 0)
    c.execute("SELECT saldo FROM caja_saldo WHERE id_caja = %s LIMIT 1", [id_caja])
    row = c.fetchone()
    saldo_caja = float(row["saldo"] if row else 0)

    for item in (ch.get("listado") or {}).values():
        importe = float(item.get("importe") or 0)
        saldo_caja += importe
        c.execute(
            """
            INSERT INTO chequetercero (
                NroCheque, CodBanco, CodCliente, Librador, fechaEmision, fechaVto, fechaCobro,
                Importe, anulado, Encartera, Entregado, Rechazado, Depositado,
                NroCompREC, CodigoMovimientoREC, CUITLibrador, tipo_cheque
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'No','Si','No','No','No',%s,%s,%s,%s)
            """,
            [
                item.get("numero"), item.get("codbanco"), cod_cliente, item.get("librador"),
                item.get("emision"), item.get("vencimiento"), item.get("cobro"), importe,
                nro_recibo, cod_mov, item.get("cuitlibrador"), item.get("tipo"),
            ],
        )
        id_cheque = c.lastrowid
        detalle = (
            f"Cheque Nro: {item.get('numero')} - Banco: {item.get('banco')} - "
            f"Librador: {item.get('librador')} - CUIT: {item.get('cuitlibrador')} - Fecha Cob: {item.get('cobro')}"
        )
        c.execute(
            """
            INSERT INTO caja (
                fecha, tipo_comprobante, Tipo, nro_comprobante, nro_comp_busq, egreso,
                id_usuario, cod_sucursal, Moneda, ingreso, Detalle, Codigo_Movimiento,
                Codigo_Cliente, codigo_prov, tipo_cp, anulado, Saldo, id_caja_abm_origen,
                id_chequetercero, nro_comp_cheq, tipo_comp_cheq
            ) VALUES (%s,'CHEQ','Cheque',%s,%s,0,%s,%s,'No',%s,%s,%s,%s,1,'Cliente','No',%s,%s,%s,%s,'REC')
            """,
            [
                date.today(), item.get("numero"), item.get("numero"), id_usuario, cod_sucursal,
                importe, detalle[:500], cod_mov, cod_cliente, saldo_caja, id_caja, id_cheque, nro_recibo,
            ],
        )
        c.execute(
            """
            INSERT INTO chequeterc_rec (
                NroCheque, CodBanco, CodCliente, Librador, fechaEmision, fechaVto, fechaCobro,
                Importe, anulado, NroCompREC, CUITLibrador, CodigoMovimientoREC, tipo_cheque
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'No',%s,%s,%s,%s)
            """,
            [
                item.get("numero"), item.get("codbanco"), cod_cliente, item.get("librador"),
                item.get("emision"), item.get("vencimiento"), item.get("cobro"), importe,
                nro_recibo, item.get("cuitlibrador"), cod_mov, item.get("tipo"),
            ],
        )

    if id_caja:
        c.execute(
            "UPDATE caja_saldo SET saldo=%s, id_usuario=%s, cod_sucursal=%s WHERE id_caja=%s",
            [saldo_caja, id_usuario, cod_sucursal, id_caja],
        )


def _persistir_tarjetas(c, *, recibo, cod_mov, nro_recibo, cod_cliente, id_usuario, cod_sucursal) -> None:
    tj_block = recibo["tarjeta"]
    id_caja = int(tj_block.get("idCajaTarjeta") or 0)
    c.execute("SELECT saldo FROM caja_saldo WHERE id_caja = %s LIMIT 1", [id_caja])
    row = c.fetchone()
    saldo_caja = float(row["saldo"] if row else 0)

    for tj in (tj_block.get("listado") or {}).values():
        importe = float(tj.get("importe") or 0)
        c.execute(
            """
            INSERT INTO tc_comprobante (
                nombre_tc_comprobante, nombre_plan_tc_comprobante, id_tc, id_tc_plan,
                cuotas_tc_comprobante, interes_tc_comprobante, nro_tarjeta_tc_comprobante,
                nro_cupon_tc_comprobante, importe_tc_comprobante, importe_cuota,
                importe_con_interes, codigo_movimiento, nro_lote_tc
            ) VALUES (%s,%s,%s,%s,%s,0,%s,%s,%s,%s,%s,%s,%s)
            """,
            [
                tj.get("nombreClase"), tj.get("nombrePlan"), tj.get("clase"), tj.get("plan"),
                tj.get("cuotas"), tj.get("numero"), tj.get("cupon"), importe,
                tj.get("importeCuota"), importe, cod_mov, tj.get("lote"),
            ],
        )
        id_tc = c.lastrowid
        saldo_caja += importe
        detalle = (
            f"Tarjeta: {tj.get('nombreClase')} - Plan: {tj.get('nombrePlan')} - "
            f"Cupon: {tj.get('cupon')} - Importe: {importe}"
        )
        c.execute(
            """
            INSERT INTO caja (
                fecha, tipo_comprobante, tipo, nro_comprobante, nro_comp_busq, egreso,
                id_usuario, cod_sucursal, moneda, ingreso, Detalle, Codigo_Movimiento,
                Codigo_Cliente, codigo_prov, tipo_cp, anulado, Saldo, id_caja_abm_origen,
                id_tc_comprobante, id_tc, nro_comp_cheq, tipo_comp_cheq
            ) VALUES (%s,'TARJ','Tarjeta',%s,%s,0,%s,%s,'No',%s,%s,%s,%s,1,'Cliente','No',%s,%s,%s,%s,%s,'REC')
            """,
            [
                date.today(), tj.get("numero"), tj.get("numero"), id_usuario, cod_sucursal,
                importe, detalle[:500], cod_mov, cod_cliente, saldo_caja, id_caja, id_tc,
                tj.get("clase"), nro_recibo,
            ],
        )

    if id_caja:
        c.execute(
            "UPDATE caja_saldo SET saldo=%s, id_usuario=%s, cod_sucursal=%s WHERE id_caja=%s",
            [saldo_caja, id_usuario, cod_sucursal, id_caja],
        )


def _persistir_transferencias(c, *, recibo, cod_mov, cod_cliente, id_usuario, cod_sucursal) -> None:
    for tra in recibo["transferencia"].get("items") or []:
        importe = float(tra.get("total") or 0)
        fecha_fmt = tra.get("fecha")
        c.execute(
            """
            INSERT INTO transferencia (
                fecha_transf, nro_referencia, id_cuentabancaria, importe_transf, tipo,
                detalle_transf, codigo_movimiento, anulado, detalle_transf_global
            ) VALUES (%s,%s,%s,%s,'Cobranza',%s,%s,'No',%s)
            """,
            [
                fecha_fmt,
                tra.get("numeroTransferencia"),
                tra.get("idCuentaBancaria"),
                importe,
                tra.get("detalle") or tra.get("numeroTransferencia"),
                cod_mov,
                f"Fecha: {fecha_fmt} - Banco: {tra.get('banco')} - Cuenta: {tra.get('numeroCuenta')} - Importe: $ {importe}",
            ],
        )


def _persistir_retenciones(c, *, recibo, cod_mov, nro_recibo, cod_cliente) -> None:
    for rt in (recibo["retencion"].get("lista") or {}).values():
        c.execute(
            """
            INSERT INTO retenciones (
                NroCertificado, CodCliente, Fecha, Porcentaje, Importe, NroRec,
                CodRetencion, CodAgentRet, anulado, Codigo_Movimiento, CodBanco
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,1,'No',%s,1)
            """,
            [
                rt.get("certificado"), cod_cliente, rt.get("fecha"), rt.get("porcentaje"),
                rt.get("monto"), nro_recibo, rt.get("cod"), cod_mov,
            ],
        )


def _persistir_descuento(c, *, recibo, cod_mov, nro_recibo, cod_cliente) -> None:
    desc = recibo["descuento"]
    c.execute(
        """
        INSERT INTO descuento_rec_nc (
            CodDescuento, Fecha, NroRec, CodigoMovimiento, Importe, Porcentaje,
            CodCliente, Computado, anulado
        ) VALUES (1,%s,%s,%s,%s,%s,%s,'No','No')
        """,
        [date.today(), nro_recibo, cod_mov, desc.get("total"), desc.get("porcentaje"), cod_cliente],
    )
