"""
Consumo de saldo a favor existente (recibo_factura REC/NCA/…) como medio de cobro.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List

from core.mysql_pool import get_mysql_pool
from core.utils.administranet_types import to_int_or_none
from ecom.services.recibo_totales_sesion import sincronizar_totales_recibo_sesion


_TIPOS_ACUENTA = ("REC", "NCA", "NCM", "NCE", "NCC", "NCB", "AJC", "INIC")


def _to_decimal(value: Any, default: str = "0") -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(default)


def _recibo(session: Dict[str, Any]) -> Dict[str, Any] | None:
    r = session.get("recibo")
    if not isinstance(r, dict) or not r.get("codCliente"):
        return None
    return r


def listar_lineas_saldo_favor(base_empresa: str, cod_cliente: int) -> List[Dict[str, Any]]:
    """Líneas con saldo a favor del cliente (FIFO por fecha y nro comprobante)."""
    pool = get_mysql_pool()
    with pool.get_connection(base_empresa) as conn:
        c = conn.cursor()
        placeholders = ", ".join(["%s"] * len(_TIPOS_ACUENTA))
        c.execute(
            f"""
            SELECT
                id_recibo_factura,
                TipoComprobante,
                NroComprobante,
                Fecha,
                Importe,
                COALESCE(cancelado, 0) AS cancelado,
                Saldo,
                CodigoMovimiento
            FROM recibo_factura
            WHERE Codigo = %s
              AND Estado = 'N/Canc'
              AND Saldo <> 0
              AND TipoComprobante IN ({placeholders})
              AND Anulado = 'No'
            ORDER BY Fecha ASC, NroComprobante ASC
            """,
            [cod_cliente, *_TIPOS_ACUENTA],
        )
        rows = c.fetchall() or []
    return [
        {
            "id_recibo_factura": int(r["id_recibo_factura"]),
            "tipocomprobante": r.get("TipoComprobante"),
            "nrocomprobante": r.get("NroComprobante"),
            "fecha": r.get("Fecha"),
            "importe": float(r.get("Importe") or 0),
            "cancelado": float(r.get("cancelado") or 0),
            "saldo": float(r.get("Saldo") or 0),
            "codmov": int(r.get("CodigoMovimiento") or 0),
        }
        for r in rows
    ]


def _asignar_fifo(lineas: List[Dict[str, Any]], monto: Decimal) -> List[Dict[str, Any]]:
    restante = monto
    asignadas: List[Dict[str, Any]] = []
    for ln in lineas:
        if restante <= Decimal("0"):
            break
        saldo_ln = _to_decimal(ln.get("saldo"))
        if saldo_ln <= Decimal("0"):
            continue
        consumir = min(saldo_ln, restante)
        asignadas.append(
            {
                "id_recibo_factura": ln["id_recibo_factura"],
                "tipocomprobante": ln.get("tipocomprobante"),
                "nrocomprobante": ln.get("nrocomprobante"),
                "fecha": ln.get("fecha"),
                "importe": ln.get("importe"),
                "codmov": ln.get("codmov"),
                "saldo_previo": float(saldo_ln),
                "consumido": float(consumir),
                "saldo_nuevo": float(saldo_ln - consumir),
            }
        )
        restante -= consumir
    if restante > Decimal("0.01"):
        raise ValueError("El monto supera el saldo a favor disponible.")
    return asignadas


def aplicar_saldo_favor_sesion(
    session: Dict[str, Any],
    *,
    base_empresa: str,
    monto: Any,
) -> Dict[str, Any]:
    recibo = _recibo(session)
    if not recibo:
        return {"msg": "error", "error": "No hay recibo iniciado."}

    importe = _to_decimal(monto)
    if importe <= Decimal("0"):
        recibo.pop("saldoAFavor", None)
        session["recibo"] = recibo
        sincronizar_totales_recibo_sesion(session)
        return {"msg": "ok", "total": 0.0, "lineas": []}

    lineas = listar_lineas_saldo_favor(base_empresa, int(recibo["codCliente"]))
    if not lineas:
        return {"msg": "error", "error": "El cliente no tiene saldo a favor disponible."}

    try:
        asignadas = _asignar_fifo(lineas, importe)
    except ValueError as exc:
        return {"msg": "error", "error": str(exc)}

    recibo["saldoAFavor"] = {
        "total": float(importe),
        "lineas": asignadas,
    }
    session["recibo"] = recibo
    sincronizar_totales_recibo_sesion(session)
    return {"msg": "ok", "total": float(importe), "lineas": asignadas}


def borrar_saldo_favor_sesion(session: Dict[str, Any]) -> Dict[str, Any]:
    recibo = _recibo(session) or {}
    recibo.pop("saldoAFavor", None)
    session["recibo"] = recibo
    sincronizar_totales_recibo_sesion(session)
    return {"msg": "ok"}


def persistir_consumo_saldo_favor(
    c,
    *,
    recibo: Dict[str, Any],
    cod_mov: int,
    nro_recibo: str,
    cod_cliente: int,
    cod_viajante: int,
    id_usuario: int,
) -> None:
    bloque = recibo.get("saldoAFavor")
    if not isinstance(bloque, dict):
        return
    lineas = bloque.get("lineas") or []
    if not lineas:
        return

    for ln in lineas:
        id_rf = to_int_or_none(ln.get("id_recibo_factura"))
        consumido = _to_decimal(ln.get("consumido"))
        if id_rf is None or consumido <= Decimal("0"):
            continue

        c.execute(
            """
            SELECT cancelado, Saldo, Importe, TipoComprobante, NroComprobante, Fecha, CodigoMovimiento
            FROM recibo_factura WHERE id_recibo_factura = %s LIMIT 1
            """,
            [id_rf],
        )
        row = c.fetchone()
        if not row:
            raise ValueError(f"Línea de saldo a favor {id_rf} no encontrada.")

        saldo_prev = _to_decimal(row.get("Saldo"))
        if consumido > saldo_prev + Decimal("0.01"):
            raise ValueError(f"Saldo a favor insuficiente en comprobante {row.get('NroComprobante')}.")

        cancelado_new = _to_decimal(row.get("cancelado")) + consumido
        saldo_new = saldo_prev - consumido
        estado = "Canc" if saldo_new <= Decimal("0.01") else "N/Canc"

        c.execute(
            """
            UPDATE recibo_factura
            SET cancelado = %s, Saldo = %s, estado = %s, Imp = 'Si',
                ReciboMov = %s, Recibo = %s, CodViajante = %s
            WHERE id_recibo_factura = %s
            """,
            [
                float(cancelado_new),
                float(saldo_new),
                estado,
                cod_mov,
                nro_recibo,
                cod_viajante,
                id_rf,
            ],
        )

        c.execute(
            """
            INSERT INTO recibo_factura_par (
                cancelado, CanceladoActual, Saldo, estado, Imp, ReciboMov, Recibo,
                Fecha, TipoComprobante, Importe, NroComprobante, CodigoMovimiento, Codigo,
                ImporteNC, seleccionado, ACuenta, anulado, Modificado
            ) VALUES (%s, %s, %s, %s, 'Si', %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Si', 'Si', 'No', 'No')
            """,
            [
                float(cancelado_new),
                float(consumido),
                float(saldo_new),
                estado,
                cod_mov,
                nro_recibo,
                ln.get("fecha") or row.get("Fecha"),
                row.get("TipoComprobante"),
                float(row.get("Importe") or 0),
                row.get("NroComprobante"),
                int(row.get("CodigoMovimiento") or ln.get("codmov") or 0),
                cod_cliente,
                float(consumido),
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
            ) VALUES (%s, %s, %s, %s, %s, 'REC', %s, %s, 'A cuenta', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            [
                ln.get("fecha") or row.get("Fecha"),
                row.get("TipoComprobante"),
                row.get("NroComprobante"),
                int(row.get("CodigoMovimiento") or ln.get("codmov") or 0),
                ln.get("fecha") or row.get("Fecha"),
                nro_recibo,
                cod_mov,
                float(row.get("Importe") or 0),
                float(consumido),
                float(saldo_new),
                estado,
                float(consumido),
                float(consumido),
                float(saldo_new),
                estado,
                id_usuario,
                cod_cliente,
            ],
        )
