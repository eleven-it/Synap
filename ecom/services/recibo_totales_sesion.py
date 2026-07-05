"""
Cálculo de totales del recibo en sesión (paridad actualiza_total_array / total_recibo_resumen).
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Dict

from fe_afip.services.recibo_imputacion_service import resumen_imputacion_sesion


def _to_decimal(value: Any, default: str = "0") -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(default)


def actualiza_total_array(session: Dict[str, Any]) -> Dict[str, Any]:
    """Paridad ``actualiza_total_array()`` en json_recibo.php."""
    recibo = session.get("recibo") or {}
    total = Decimal("0")
    for item in (recibo.get("facturas") or {}).values():
        total += _to_decimal(item.get("aimputar"))

    descuento = Decimal("0")
    if isinstance(recibo.get("descuento"), dict):
        descuento = _to_decimal(recibo["descuento"].get("total"))

    retencion = Decimal("0")
    if isinstance(recibo.get("retencion"), dict):
        retencion = _to_decimal(recibo["retencion"].get("total"))

    saldo = total - descuento - retencion
    return {
        "msg": "ok",
        "total": float(total),
        "descuento": float(descuento),
        "retencion": float(retencion),
        "saldo": float(saldo),
    }


def sincronizar_totales_recibo_sesion(session: Dict[str, Any]) -> Dict[str, Any]:
    """Paridad ``total_recibo_resumen()`` — fija totalImputado, total y aCuenta."""
    recibo = session.get("recibo")
    if not isinstance(recibo, dict):
        return {"msg": "error", "error": "Sin recibo en sesión."}

    impu = actualiza_total_array(session)
    recibo["totalImputado"] = impu["total"]
    recibo["totalAcobrar"] = impu["saldo"]

    total_recibo = Decimal("0")
    a_cuenta_base = _to_decimal(impu["saldo"])

    for key, campo in (
        ("efectivo", "total"),
        ("cheques", "total"),
        ("transferencia", "total"),
        ("tarjeta", "total"),
        ("saldoAFavor", "total"),
    ):
        bloque = recibo.get(key)
        if isinstance(bloque, dict):
            monto = _to_decimal(bloque.get(campo))
            if monto > Decimal("0"):
                a_cuenta_base -= monto
                total_recibo += monto

    if a_cuenta_base < Decimal("0"):
        recibo["aCuenta"] = float(abs(a_cuenta_base))
    else:
        recibo.pop("aCuenta", None)

    if isinstance(recibo.get("retencion"), dict):
        total_recibo += _to_decimal(recibo["retencion"].get("total"))

    if total_recibo == Decimal("0") and _to_decimal(impu["saldo"]) > Decimal("0"):
        total_recibo = _to_decimal(impu["saldo"])

    recibo["total"] = float(total_recibo)
    session["recibo"] = recibo
    return {
        "msg": "ok",
        "total": float(total_recibo),
        "totalImputado": float(impu["total"]),
        "aCuenta": recibo.get("aCuenta"),
    }


def control_final_recibo_sesion(session: Dict[str, Any]) -> Dict[str, Any]:
    sincronizar_totales_recibo_sesion(session)
    recibo = session.get("recibo") or {}
    total_recibo = _to_decimal(recibo.get("total"))
    total_cobrar = _to_decimal(recibo.get("totalImputado"))
    if isinstance(recibo.get("descuento"), dict):
        total_cobrar -= _to_decimal(recibo["descuento"].get("total"))
    diferencia = total_cobrar - total_recibo
    if diferencia > Decimal("0.01"):
        return {"msg": "error", "deuda": float(diferencia)}
    return {"msg": "ok", "saldo": float(diferencia)}


def resumen_recibo_sesion(session: Dict[str, Any]) -> Dict[str, Any]:
    sincronizar_totales_recibo_sesion(session)
    recibo = session.get("recibo") or {}
    imputacion = resumen_imputacion_sesion(session)
    medios = []

    def _add(label: str, bloque: Any, key: str = "total"):
        if isinstance(bloque, dict) and _to_decimal(bloque.get(key)) > Decimal("0"):
            medios.append({"campo": label, "valor": float(_to_decimal(bloque.get(key)))})

    _add("Efectivo", recibo.get("efectivo"))
    _add("Cheques", recibo.get("cheques"))
    _add("Transferencias", recibo.get("transferencia"))
    _add("Tarjetas", recibo.get("tarjeta"))
    _add("Retenciones", recibo.get("retencion"))
    _add("Saldo a favor", recibo.get("saldoAFavor"))

    return {
        "msg": "ok",
        "nroRecibo": recibo.get("nroRecibo"),
        "total": recibo.get("total"),
        "totalImputado": recibo.get("totalImputado"),
        "aCuenta": recibo.get("aCuenta"),
        "imputacion": imputacion,
        "medios": medios,
        "retenciones": list((recibo.get("retencion") or {}).get("lista") or {}).values(),
        "cheques": list((recibo.get("cheques") or {}).get("listado") or {}).values(),
        "tarjetas": list((recibo.get("tarjeta") or {}).get("listado") or {}).values(),
        "transferencias": list((recibo.get("transferencia") or {}).get("items") or []),
    }
