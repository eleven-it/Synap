"""
Alta de recibo mayoristapp (paridad json_recibo.php — inicio, medios, guardar).

Reexporta totales/medios y orquesta el guardado completo legacy.
"""

from __future__ import annotations

from typing import Any, Dict

from core.mysql_pool import get_mysql_pool
from core.utils.administranet_types import to_int_or_none
from ecom.services.recibo_guardado_completo_service import guardar_recibo_completo_legacy
from ecom.services.recibo_medios_sesion import (
    alta_cheque_sesion,
    alta_descuento_sesion,
    alta_efectivo_sesion,
    alta_retencion_sesion,
    alta_tarjeta_sesion,
    alta_transferencia_sesion,
    borrar_cheque_sesion,
    borrar_descuento_sesion,
    borrar_efectivo_sesion,
    borrar_retencion_sesion,
    borrar_tarjeta_sesion,
    borrar_transferencia_sesion,
)
from ecom.services.recibo_totales_sesion import (
    control_final_recibo_sesion,
    resumen_recibo_sesion,
    sincronizar_totales_recibo_sesion,
)
from ecom.services.recibo_saldo_favor_service import (
    aplicar_saldo_favor_sesion,
    borrar_saldo_favor_sesion,
)
from fe_afip.services.recibo_imputacion_service import fin_imputacion_sesion, resumen_imputacion_sesion


def control_fact_temporal_libre(base_empresa: str, cod_cliente: int) -> tuple[bool, str]:
    pool = get_mysql_pool()
    with pool.get_connection(base_empresa) as conn:
        c = conn.cursor()
        c.execute(
            "SELECT id_fact_temporal FROM fact_temporal WHERE Codigo = %s LIMIT 1",
            [cod_cliente],
        )
        if c.fetchone():
            return (
                False,
                "Otro usuario está generando recibos para ese cliente. Inténtelo más tarde.",
            )
    return True, ""


def verifica_nro_talonario(base_empresa: str, nro_pv: int, nro_form: int) -> bool:
    nro_rec = f"{str(nro_pv).zfill(4)}-{str(nro_form).zfill(8)}"
    pool = get_mysql_pool()
    with pool.get_connection(base_empresa) as conn:
        c = conn.cursor()
        c.execute(
            """
            SELECT CodigoMovimiento FROM cuentacliente
            WHERE tiporec = 'Talonario' AND TipoComprobante = 'REC' AND Anulado = 'No'
              AND NroComprobante = %s AND NroCompBusq = %s LIMIT 1
            """,
            [nro_rec, str(nro_form)],
        )
        return c.fetchone() is None


def iniciar_recibo_sesion(
    session: Dict[str, Any],
    *,
    idcliente: int,
    payload: Dict[str, Any],
    session_user: Dict[str, Any],
) -> Dict[str, Any]:
    if session.get("recibo"):
        rec = session["recibo"]
        if rec.get("nroRecibo"):
            return {"msg": "ok", "numero": rec.get("nroRecibo"), "reanudado": True}

    tipo = str(payload.get("tipoNro") or payload.get("tipo") or "sistema").strip().lower()
    if tipo not in ("sistema", "talonario"):
        return {"msg": "fallo", "desc": "Tipo de numeración no válido."}

    raw_pv = str(payload.get("nroPv") or payload.get("puntoVenta") or "").strip()
    id_pv = to_int_or_none(payload.get("idPv"))
    pv_nro = to_int_or_none(payload.get("pv"))
    pv_cont = str(payload.get("puntoVentaContable") or "no")
    if raw_pv and "|" in raw_pv:
        parts = raw_pv.split("|")
        if len(parts) >= 3:
            id_pv = to_int_or_none(parts[0]) or id_pv
            pv_nro = to_int_or_none(parts[1]) or pv_nro
            pv_cont = parts[2] or pv_cont

    if id_pv is None:
        id_pv = to_int_or_none(session_user.get("id_punto_venta"))
    if id_pv is None:
        return {"msg": "fallo", "desc": "No hay punto de venta asignado al usuario."}

    cod_viajante = to_int_or_none(session_user.get("CodViajante") or session_user.get("cod_viajante")) or 0
    recibo: Dict[str, Any] = {
        "tipo": tipo,
        "nroCompBusq": 0,
        "codCliente": int(idcliente),
        "saldoCliente": payload.get("saldoCliente"),
        "idPcCliente": payload.get("idPcCliente"),
        "total": "",
        "idPv": int(id_pv),
        "puntoVentaContable": pv_cont,
        "codViajante": cod_viajante,
        "clase": "imputacion",
    }

    if tipo == "talonario":
        nro = to_int_or_none(payload.get("nroRec") or payload.get("nro"))
        if pv_nro is None or nro is None:
            return {"msg": "fallo", "desc": "Faltan PV y número de talonario."}
        base = str(session_user.get("base_empresa") or "").strip()
        if not base:
            return {"msg": "fallo", "desc": "Falta base_empresa en sesión."}
        if not verifica_nro_talonario(base, int(pv_nro), int(nro)):
            return {"msg": "fallo", "desc": "Ya existe un recibo con ese punto de venta y talonario."}
        recibo["nroRecibo"] = f"{str(pv_nro).zfill(4)}-{str(nro).zfill(8)}"
        recibo["nroCompBusq"] = int(nro)
    else:
        recibo["nroRecibo"] = "0-0"
        recibo["nroCompBusq"] = 0

    session["recibo"] = recibo
    return {"msg": "ok", "numero": recibo["nroRecibo"]}


def cancelar_recibo_sesion(session: Dict[str, Any]) -> None:
    session.pop("recibo", None)


def guardar_recibo_mayoristapp(
    *,
    base_empresa: str,
    session_user: Dict[str, Any],
    session: Dict[str, Any],
) -> Dict[str, Any]:
    recibo = session.get("recibo")
    if not isinstance(recibo, dict) or not recibo.get("codCliente"):
        raise ValueError("Sin datos del recibo. Inténtelo nuevamente.")

    cod_cliente = int(recibo["codCliente"])
    ok_temp, msg_temp = control_fact_temporal_libre(base_empresa, cod_cliente)
    if not ok_temp:
        raise ValueError(msg_temp)

    ctrl = control_final_recibo_sesion(session)
    if ctrl.get("msg") != "ok":
        raise ValueError(f"El recibo no cubre el total imputado. Falta: {ctrl.get('deuda', 0)}")

    sincronizar_totales_recibo_sesion(session)
    recibo = dict(session.get("recibo") or {})

    data = guardar_recibo_completo_legacy(
        base_empresa=base_empresa,
        session_user=session_user,
        recibo=recibo,
    )
    cancelar_recibo_sesion(session)
    return data


__all__ = [
    "alta_cheque_sesion",
    "alta_descuento_sesion",
    "alta_efectivo_sesion",
    "alta_retencion_sesion",
    "alta_tarjeta_sesion",
    "alta_transferencia_sesion",
    "aplicar_saldo_favor_sesion",
    "borrar_cheque_sesion",
    "borrar_descuento_sesion",
    "borrar_efectivo_sesion",
    "borrar_retencion_sesion",
    "borrar_saldo_favor_sesion",
    "borrar_tarjeta_sesion",
    "borrar_transferencia_sesion",
    "cancelar_recibo_sesion",
    "control_fact_temporal_libre",
    "control_final_recibo_sesion",
    "fin_imputacion_sesion",
    "guardar_recibo_mayoristapp",
    "iniciar_recibo_sesion",
    "resumen_imputacion_sesion",
    "resumen_recibo_sesion",
    "sincronizar_totales_recibo_sesion",
    "verifica_nro_talonario",
]
