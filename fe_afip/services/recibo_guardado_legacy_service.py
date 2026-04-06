"""
Persistencia legacy de recibo (rama imputación) con transacción.

Diseñado para paridad progresiva con json_recibo.php sin impactar TPV/Self-checkout.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Dict

from core.mysql_pool import get_mysql_pool


def _to_decimal(value: Any, default: str = "0") -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(default)


def _required(recibo: Dict[str, Any], key: str) -> Any:
    val = recibo.get(key)
    if val in (None, ""):
        raise ValueError(f"Falta dato obligatorio en sesión recibo: {key}")
    return val


def guardar_recibo_imputacion_legacy(
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

    nro_recibo = str(_required(recibo, "nroRecibo"))
    nro_comp_busq = str(recibo.get("nroCompBusq") or nro_recibo)
    cod_mov = int(_required(recibo, "codmov"))
    cod_cliente = int(_required(recibo, "codCliente"))
    total_recibo = _to_decimal(_required(recibo, "total"))
    cod_viajante = int(recibo.get("codViajante") or 0)
    id_usuario = int(session_user.get("id_usuario") or 0)
    id_sucursal = int(session_user.get("id_sucursal") or 0)

    pool = get_mysql_pool()
    with pool.get_connection(base_empresa) as conn:
        conn.autocommit(False)
        try:
            c = conn.cursor()

            c.execute(
                """
                INSERT INTO cuentacliente (
                    Fecha, TipoComprobante, NroComprobante, NroCompBusq, CondVenta, anulado,
                    Codigo, CodigoMovimiento, idUsuario, codSucursal, TipoRecibo,
                    ImporteCobro, TotalImputacionRec, TotalPagoRec, TotalRecibo, CodViajante, Detalle
                ) VALUES (%s, 'REC', %s, %s, '-', 'No', %s, %s, %s, %s, 'I', %s, %s, %s, %s, %s, 'WEB')
                """,
                [
                    date.today(),
                    nro_recibo,
                    nro_comp_busq,
                    cod_cliente,
                    cod_mov,
                    id_usuario,
                    id_sucursal,
                    float(total_recibo),
                    float(total_recibo),
                    float(total_recibo),
                    float(total_recibo),
                    cod_viajante,
                ],
            )

            for f in facturas.values():
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
                        UPDATE cuentacliente
                        SET estado='Canc', ReciboMov=%s, Recibo=%s
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
                    [
                        float(cancelado_new),
                        float(saldo_n),
                        estado,
                        cod_mov,
                        nro_recibo,
                        cod_viajante,
                        id_rf,
                    ],
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
                        float(_to_decimal(f.get("importe"))),
                        float(aimputar),
                        float(saldo_n),
                        estado,
                        float(total_recibo),
                        float(aimputar),
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
                        float(cancelado_new),
                        float(aimputar),
                        float(saldo_n),
                        estado,
                        cod_mov,
                        nro_recibo,
                        f.get("fecha"),
                        f.get("tipocomprobante"),
                        float(_to_decimal(f.get("importe"))),
                        f.get("nrofactura"),
                        f.get("vencimiento"),
                        codmov_fact,
                        cod_cliente,
                        f.get("condventa") or "-",
                        float(_to_decimal(f.get("importe"))),
                        "Si" if estado == "Canc" else "No",
                    ],
                )

            conn.commit()
            return {"msg": "ok", "codigo_movimiento": cod_mov, "nro_recibo": nro_recibo}
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.autocommit(True)

