"""
Servicio de imputación de facturas en sesión (paridad con json_recibo.php).

No escribe en tablas legacy en esta etapa; solo administra session['recibo'].
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Dict


def _to_decimal(value: Any, default: str = "0") -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(default)


def _ensure_recibo(session: Dict[str, Any], idcliente: int) -> Dict[str, Any]:
    recibo = session.get("recibo")
    if not isinstance(recibo, dict):
        recibo = {}
        session["recibo"] = recibo
    if not recibo.get("codCliente"):
        recibo["codCliente"] = int(idcliente)
    return recibo


def imputar_factura_en_sesion(
    session: Dict[str, Any],
    *,
    idcliente: int,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    recibo = _ensure_recibo(session, idcliente)
    recibo["clase"] = "imputacion"
    facturas = recibo.get("facturas")
    if not isinstance(facturas, dict):
        facturas = {}
        recibo["facturas"] = facturas

    id_rf = str(payload.get("idrecibofactura") or "").strip()
    if not id_rf:
        return {"msg": "error", "error": "idrecibofactura requerido."}

    saldo = _to_decimal(payload.get("saldo"))
    aimputar = _to_decimal(payload.get("aimputar"))
    if aimputar <= Decimal("0"):
        return {"msg": "error", "error": "El monto a imputar debe ser mayor a cero."}
    if aimputar > saldo:
        return {"msg": "error", "error": "El monto a imputar supera el saldo."}

    saldo_n = saldo - aimputar
    facturas[id_rf] = {
        "idrecibofactura": payload.get("idrecibofactura"),
        "codmovFact": payload.get("codmodfact"),
        "fecha": payload.get("fecha"),
        "nrofactura": payload.get("nrofactura"),
        "importe": float(_to_decimal(payload.get("importe"))),
        "cancelado": float(_to_decimal(payload.get("cancelado"))),
        "saldo": float(saldo),
        "aimputar": float(aimputar),
        "tipocomprobante": payload.get("tipocomprobante"),
        "vencimiento": payload.get("vencimiento"),
        "condventa": payload.get("condventa"),
        "saldoN": float(saldo_n),
    }
    return {"msg": "ok"}


def desimputar_factura_en_sesion(session: Dict[str, Any], *, idrecibofactura: Any) -> Dict[str, Any]:
    recibo = session.get("recibo") or {}
    facturas = recibo.get("facturas") or {}
    key = str(idrecibofactura or "").strip()
    item = facturas.get(key)
    if not item:
        return {"msg": "error", "error": "No existe la factura imputada."}
    saldo = _to_decimal(item.get("saldo"))
    del facturas[key]
    return {"msg": "ok", "saldoNuevo": float(saldo)}


def resumen_imputacion_sesion(session: Dict[str, Any]) -> Dict[str, Any]:
    recibo = session.get("recibo") or {}
    facturas = recibo.get("facturas") or {}
    total = Decimal("0")
    resumen = []
    for item in facturas.values():
        imp = _to_decimal(item.get("aimputar"))
        total += imp
        resumen.append(
            {
                "factura": item.get("nrofactura"),
                "imputado": float(imp),
                "saldo": float(_to_decimal(item.get("saldoN"))),
            }
        )
    if not resumen:
        return {"msg": "fallo", "total": 0.0, "resumen": []}
    return {"msg": "ok", "total": float(total), "resumen": resumen}


def fin_imputacion_sesion(session: Dict[str, Any]) -> Dict[str, Any]:
    """Cierra paso imputación y persiste ``totalImputado`` en sesión."""
    data = resumen_imputacion_sesion(session)
    if data.get("msg") == "ok":
        recibo = session.get("recibo")
        if not isinstance(recibo, dict):
            recibo = {}
            session["recibo"] = recibo
        recibo["totalImputado"] = data["total"]
    return data

