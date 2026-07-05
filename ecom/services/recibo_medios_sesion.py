"""
Medios de cobro del recibo en sesión (efectivo, cheques, tarjetas, transferencias, retenciones, descuentos).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, Dict

from core.utils.administranet_types import to_int_or_none, to_date_or_none, str_or_default
from ecom.services.recibo_totales_sesion import actualiza_total_array, sincronizar_totales_recibo_sesion


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


def alta_efectivo_sesion(session: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    recibo = _recibo(session)
    if not recibo:
        return {"msg": "error", "error": "No hay recibo iniciado."}

    moneda = str(payload.get("moneda") or "pesos").strip().lower()
    coti = _to_decimal(payload.get("coti") or payload.get("cotizacion") or "1")
    id_caja = to_int_or_none(payload.get("idcaja") or payload.get("idCaja"))
    if id_caja is None:
        return {"msg": "error", "error": "Caja requerida."}

    prev = recibo.get("efectivo") if isinstance(recibo.get("efectivo"), dict) else {}
    pesos = _to_decimal(prev.get("pesos"))
    dolar = _to_decimal(prev.get("dolar"))

    if moneda == "pesos":
        pesos = _to_decimal(payload.get("pesos"))
    elif moneda == "dolar":
        dolar = _to_decimal(payload.get("dolar"))
        coti = _to_decimal(payload.get("coti") or payload.get("cotizacion") or prev.get("cotizacion") or "1")
    else:
        return {"msg": "error", "error": "Moneda no soportada."}

    total = pesos + (dolar * coti)
    recibo["efectivo"] = {
        "idCaja": id_caja,
        "pesos": float(pesos),
        "dolar": float(dolar),
        "cotizacion": float(coti),
        "total": float(total),
    }
    session["recibo"] = recibo
    sincronizar_totales_recibo_sesion(session)
    return {"msg": "ok", "total": float(total)}


def borrar_efectivo_sesion(session: Dict[str, Any], tipo: str) -> Dict[str, Any]:
    recibo = _recibo(session) or {}
    efectivo = recibo.get("efectivo")
    if not isinstance(efectivo, dict):
        return {"msg": "ok"}

    pesos = _to_decimal(efectivo.get("pesos"))
    dolar = _to_decimal(efectivo.get("dolar"))
    coti = _to_decimal(efectivo.get("cotizacion") or "1")
    if tipo == "dolar":
        dolar = Decimal("0")
        efectivo["dolar"] = 0
    else:
        pesos = Decimal("0")
        efectivo["pesos"] = 0

    total = pesos + (dolar * coti)
    if total == Decimal("0"):
        recibo.pop("efectivo", None)
    else:
        efectivo["total"] = float(total)
        recibo["efectivo"] = efectivo
    session["recibo"] = recibo
    sincronizar_totales_recibo_sesion(session)
    return {"msg": "ok"}


def alta_cheque_sesion(session: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    recibo = _recibo(session)
    if not recibo:
        return {"msg": "error", "error": "No hay recibo iniciado."}

    importe = _to_decimal(payload.get("importe"))
    if importe <= Decimal("0"):
        return {"msg": "error", "error": "Importe inválido."}

    id_caja = to_int_or_none(payload.get("idCajaCheque") or payload.get("idCaja"))
    cheques = recibo.get("cheques") if isinstance(recibo.get("cheques"), dict) else {}
    listado = cheques.get("listado") if isinstance(cheques.get("listado"), dict) else {}

    codbanco = str_or_default(payload.get("codbanco"), "-")
    numero = str_or_default(payload.get("numero"), "-")
    clave = f"{codbanco}c{numero}"

    cobro = payload.get("cobro") or payload.get("emison")
    vencimiento = payload.get("vencimiento")
    if not vencimiento and cobro:
        try:
            dt = datetime.strptime(str(cobro)[:10], "%Y-%m-%d")
            vencimiento = (dt + timedelta(days=30)).strftime("%Y-%m-%d")
        except ValueError:
            vencimiento = str(cobro)

    listado[clave] = {
        "codbanco": codbanco,
        "banco": str_or_default(payload.get("banco")),
        "cuitbanco": str_or_default(payload.get("cuitbanco")),
        "librador": str_or_default(payload.get("librador")),
        "cuitlibrador": str_or_default(payload.get("cuitlibrador")),
        "numero": numero,
        "importe": float(importe),
        "emision": payload.get("emison") or payload.get("emision"),
        "vencimiento": vencimiento,
        "cobro": cobro,
        "tipo": str_or_default(payload.get("tipo"), "Físico"),
    }

    total = sum(_to_decimal(v.get("importe")) for v in listado.values())
    recibo["cheques"] = {
        "listado": listado,
        "total": float(total),
        "idCajaCheque": id_caja or cheques.get("idCajaCheque"),
    }
    session["recibo"] = recibo
    sincronizar_totales_recibo_sesion(session)
    return {"msg": "ok", "total": float(total)}


def borrar_cheque_sesion(session: Dict[str, Any], clave: str) -> Dict[str, Any]:
    recibo = _recibo(session) or {}
    cheques = recibo.get("cheques")
    if not isinstance(cheques, dict):
        return {"msg": "ok"}
    listado = cheques.get("listado") or {}
    listado.pop(str(clave), None)
    if not listado:
        recibo.pop("cheques", None)
    else:
        total = sum(_to_decimal(v.get("importe")) for v in listado.values())
        cheques["listado"] = listado
        cheques["total"] = float(total)
        recibo["cheques"] = cheques
    session["recibo"] = recibo
    sincronizar_totales_recibo_sesion(session)
    return {"msg": "ok"}


def alta_transferencia_sesion(session: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    recibo = _recibo(session)
    if not recibo:
        return {"msg": "error", "error": "Recibo vacío."}

    importe = _to_decimal(payload.get("importe"))
    if importe <= Decimal("0"):
        return {"msg": "error", "error": "Importe inválido."}

    transf = recibo.get("transferencia") if isinstance(recibo.get("transferencia"), dict) else {}
    items = list(transf.get("items") or [])

    raw_cuenta = str(payload.get("numeroCuenta") or "")
    raw_id = str(payload.get("idCuentaBancaria") or "")
    arr_banco = raw_cuenta.split("|", 1)
    arr_claves = raw_id.split("|", 1)
    nombre_banco = arr_banco[0] if arr_banco else ""
    nro_cuenta = arr_banco[1] if len(arr_banco) > 1 else raw_cuenta
    cod_banco = arr_claves[0] if arr_claves else ""
    id_cuenta = arr_claves[1] if len(arr_claves) > 1 else raw_id

    items.append(
        {
            "fecha": str_or_default(payload.get("fecha")),
            "numeroTransferencia": str_or_default(payload.get("nroTransferencia") or payload.get("numeroTransferencia")),
            "idCuentaBancaria": id_cuenta,
            "numeroCuenta": nro_cuenta,
            "detalle": str_or_default(payload.get("detalle")),
            "banco": nombre_banco,
            "codBanco": cod_banco,
            "total": float(importe),
        }
    )
    total = sum(_to_decimal(i.get("total")) for i in items)
    recibo["transferencia"] = {"items": items, "total": float(total)}
    session["recibo"] = recibo
    sincronizar_totales_recibo_sesion(session)
    return {"msg": "ok", "total": float(total)}


def borrar_transferencia_sesion(session: Dict[str, Any], indice: int) -> Dict[str, Any]:
    recibo = _recibo(session) or {}
    transf = recibo.get("transferencia")
    if not isinstance(transf, dict):
        return {"msg": "ok"}
    items = list(transf.get("items") or [])
    if 0 <= indice < len(items):
        items.pop(indice)
    if not items:
        recibo.pop("transferencia", None)
    else:
        total = sum(_to_decimal(i.get("total")) for i in items)
        recibo["transferencia"] = {"items": items, "total": float(total)}
    session["recibo"] = recibo
    sincronizar_totales_recibo_sesion(session)
    return {"msg": "ok"}


def alta_tarjeta_sesion(session: Dict[str, Any], payload: Dict[str, Any], id_caja_tarjeta: Any) -> Dict[str, Any]:
    recibo = _recibo(session)
    if not recibo:
        return {"msg": "error", "error": "Recibo vacío."}

    importe = _to_decimal(payload.get("importe"))
    numero = str_or_default(payload.get("numero"))
    if importe <= Decimal("0") or not numero:
        return {"msg": "error", "error": "Datos de tarjeta incompletos."}

    clase_raw = str(payload.get("clase") or "")
    partes = clase_raw.split("|", 1)
    clase = partes[0]
    id_pc = partes[1] if len(partes) > 1 else ""

    tarjeta = recibo.get("tarjeta") if isinstance(recibo.get("tarjeta"), dict) else {}
    listado = dict(tarjeta.get("listado") or {})
    listado[numero] = {
        "numero": numero,
        "importe": float(importe),
        "tipo": str_or_default(payload.get("tipo")),
        "clase": clase,
        "nombreClase": str_or_default(payload.get("nombreClase")),
        "idPc": id_pc,
        "plan": payload.get("plan"),
        "nombrePlan": str_or_default(payload.get("nombrePlan")),
        "cuotas": payload.get("cuotas"),
        "importeCuota": payload.get("importeCuota"),
        "cupon": str_or_default(payload.get("cupon")),
        "lote": str_or_default(payload.get("lote")),
    }
    total = sum(_to_decimal(v.get("importe")) for v in listado.values())
    recibo["tarjeta"] = {
        "listado": listado,
        "total": float(total),
        "idCajaTarjeta": to_int_or_none(id_caja_tarjeta) or tarjeta.get("idCajaTarjeta"),
    }
    session["recibo"] = recibo
    sincronizar_totales_recibo_sesion(session)
    return {"msg": "ok", "total": float(total)}


def borrar_tarjeta_sesion(session: Dict[str, Any], numero: str) -> Dict[str, Any]:
    recibo = _recibo(session) or {}
    tarjeta = recibo.get("tarjeta")
    if not isinstance(tarjeta, dict):
        return {"msg": "ok"}
    listado = dict(tarjeta.get("listado") or {})
    listado.pop(str(numero), None)
    if not listado:
        recibo.pop("tarjeta", None)
    else:
        total = sum(_to_decimal(v.get("importe")) for v in listado.values())
        tarjeta["listado"] = listado
        tarjeta["total"] = float(total)
        recibo["tarjeta"] = tarjeta
    session["recibo"] = recibo
    sincronizar_totales_recibo_sesion(session)
    return {"msg": "ok"}


def alta_retencion_sesion(session: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    recibo = _recibo(session)
    if not recibo:
        return {"msg": "error", "error": "Recibo vacío."}

    cod = str_or_default(payload.get("cod"))
    cert = str_or_default(payload.get("certificado"))
    key = f"{cod}-{cert}"
    ret = recibo.get("retencion") if isinstance(recibo.get("retencion"), dict) else {}
    lista = dict(ret.get("lista") or {})
    lista[key] = {
        "cod": cod,
        "tipo": str_or_default(payload.get("tipo")),
        "certificado": cert,
        "fecha": str_or_default(payload.get("fecha")),
        "porcentaje": payload.get("porcentaje"),
        "monto": float(_to_decimal(payload.get("monto"))),
    }
    total = sum(_to_decimal(r.get("monto")) for r in lista.values())
    recibo["retencion"] = {"lista": lista, "total": float(total)}
    session["recibo"] = recibo
    sincronizar_totales_recibo_sesion(session)
    return {"msg": "ok", "total": float(total)}


def borrar_retencion_sesion(session: Dict[str, Any], key: str) -> Dict[str, Any]:
    recibo = _recibo(session) or {}
    ret = recibo.get("retencion")
    if not isinstance(ret, dict):
        return {"msg": "ok"}
    lista = dict(ret.get("lista") or {})
    lista.pop(str(key), None)
    if not lista:
        recibo.pop("retencion", None)
    else:
        total = sum(_to_decimal(r.get("monto")) for r in lista.values())
        recibo["retencion"] = {"lista": lista, "total": float(total)}
    session["recibo"] = recibo
    sincronizar_totales_recibo_sesion(session)
    return {"msg": "ok"}


def alta_descuento_sesion(session: Dict[str, Any], porcentaje: Any) -> Dict[str, Any]:
    recibo = _recibo(session)
    if not recibo:
        return {"msg": "error", "error": "Recibo vacío."}

    pct = _to_decimal(porcentaje)
    impu = actualiza_total_array(session)
    total = _to_decimal(impu["saldo"]) * pct / Decimal("100")
    recibo["descuento"] = {"porcentaje": float(pct), "total": float(total)}
    session["recibo"] = recibo
    sincronizar_totales_recibo_sesion(session)
    return {"msg": "ok", "total": float(total)}


def borrar_descuento_sesion(session: Dict[str, Any]) -> Dict[str, Any]:
    recibo = _recibo(session) or {}
    recibo.pop("descuento", None)
    session["recibo"] = recibo
    sincronizar_totales_recibo_sesion(session)
    return {"msg": "ok"}
