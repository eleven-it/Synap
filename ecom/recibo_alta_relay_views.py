"""
API alta de recibo mayoristapp (wizard móvil — paridad json_recibo.php).
"""

from __future__ import annotations

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from ecom.permissions import EcomCobranzasWritePermission, EcomMayoristappSessionPermission
from ecom.services.ecom_module_settings import ecom_cobranzas_write_enabled
from ecom.services.mayoristapp_session import leer_cliente_seleccionado, leer_idcliente_mayoristapp
from ecom.services.recibo_alta_service import (
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
    aplicar_saldo_favor_sesion,
    borrar_saldo_favor_sesion,
    cancelar_recibo_sesion,
    control_final_recibo_sesion,
    control_fact_temporal_libre,
    guardar_recibo_mayoristapp,
    iniciar_recibo_sesion,
    resumen_recibo_sesion,
)


def _session_base_empresa(request: Request) -> str | None:
    data = (getattr(request, "session", None) or {}).get("user") or {}
    be = data.get("base_empresa")
    return str(be).strip() if be else None


def _write_blocked_response() -> Response:
    return Response(
        {
            "msg": "error",
            "error": "Escritura de cobranzas/recibos deshabilitada (configuración del módulo ecom).",
        },
        status=409,
    )


class ReciboAltaRelayAPIView(APIView):
    """
    POST ``/ecom/api/mayoristapp/recibos/alta/accion/?ajax=1``

    Acciones: iniciar, efectivo, borrarEfectivo, resumen, controlFinal, guardar, cancelar.
    """

    permission_classes = [EcomMayoristappSessionPermission, EcomCobranzasWritePermission]

    def post(self, request: Request) -> Response:
        if "ajax" not in request.query_params:
            return Response({"detail": "Parámetro ajax requerido."}, status=400)
        if not ecom_cobranzas_write_enabled():
            return _write_blocked_response()

        base = _session_base_empresa(request)
        if not base:
            return Response({"detail": "No se encontró base_empresa en la sesión."}, status=400)

        idc = leer_idcliente_mayoristapp(request)
        if idc is None:
            return Response({"detail": "No hay idcliente en sesión."}, status=400)

        body = dict(request.data)
        session_user = dict(request.session.get("user") or {})
        session_user["base_empresa"] = base

        if str(body.get("iniciar") or body.get("altaRecibo") or "") == "1":
            ok_temp, msg = control_fact_temporal_libre(base, idc)
            if not ok_temp:
                return Response({"msg": "fallo", "desc": msg}, status=409)
            cliente = leer_cliente_seleccionado(request)
            cliente_datos = cliente[0] if isinstance(cliente, (list, tuple)) and cliente else cliente
            if isinstance(cliente_datos, dict):
                body.setdefault("saldoCliente", cliente_datos.get("saldo") or cliente_datos.get("Saldo"))
                body.setdefault("idPcCliente", cliente_datos.get("id_pc_cliente") or cliente_datos.get("idPcCliente"))
            data = iniciar_recibo_sesion(
                request.session,
                idcliente=idc,
                payload=body,
                session_user=session_user,
            )
            request.session.modified = True
            return Response(data, status=200 if data.get("msg") == "ok" else 400)

        if str(body.get("efectivo") or body.get("altaEfectivo") or "") == "1":
            data = alta_efectivo_sesion(request.session, body)
            request.session.modified = True
            return Response(data, status=200 if data.get("msg") == "ok" else 400)

        if str(body.get("borrarEfectivo") or "") == "1":
            tipo = str(body.get("tipo") or "pesos")
            data = borrar_efectivo_sesion(request.session, tipo)
            request.session.modified = True
            return Response(data)

        if str(body.get("cheque") or body.get("altaCheque") or "") == "1":
            data = alta_cheque_sesion(request.session, body)
            request.session.modified = True
            return Response(data, status=200 if data.get("msg") == "ok" else 400)

        if str(body.get("borrarCheque") or "") == "1":
            data = borrar_cheque_sesion(request.session, str(body.get("clave") or body.get("cod") or ""))
            request.session.modified = True
            return Response(data)

        if str(body.get("transferencia") or body.get("altaTransferencia") or "") == "1":
            data = alta_transferencia_sesion(request.session, body)
            request.session.modified = True
            return Response(data, status=200 if data.get("msg") == "ok" else 400)

        if str(body.get("borrarTransferencia") or "") == "1":
            data = borrar_transferencia_sesion(request.session, int(body.get("indice") or 0))
            request.session.modified = True
            return Response(data)

        if str(body.get("tarjeta") or body.get("altaTarjeta") or "") == "1":
            id_caja_tj = session_user.get("id_caja_tarjeta") or session_user.get("id_caja_tarjeta_usr")
            data = alta_tarjeta_sesion(request.session, body, id_caja_tj)
            request.session.modified = True
            return Response(data, status=200 if data.get("msg") == "ok" else 400)

        if str(body.get("borrarTarjeta") or "") == "1":
            data = borrar_tarjeta_sesion(request.session, str(body.get("numero") or ""))
            request.session.modified = True
            return Response(data)

        if str(body.get("retencion") or body.get("altaRetencion") or "") == "1":
            data = alta_retencion_sesion(request.session, body)
            request.session.modified = True
            return Response(data, status=200 if data.get("msg") == "ok" else 400)

        if str(body.get("borrarRetencion") or "") == "1":
            data = borrar_retencion_sesion(request.session, str(body.get("key") or ""))
            request.session.modified = True
            return Response(data)

        if str(body.get("descuento") or body.get("altaDescuento") or "") == "1":
            data = alta_descuento_sesion(request.session, body.get("porcentaje"))
            request.session.modified = True
            return Response(data, status=200 if data.get("msg") == "ok" else 400)

        if str(body.get("borrarDescuento") or "") == "1":
            data = borrar_descuento_sesion(request.session)
            request.session.modified = True
            return Response(data)

        if str(body.get("saldoAFavor") or body.get("aplicarSaldoAFavor") or "") == "1":
            monto = body.get("monto") or body.get("importe")
            data = aplicar_saldo_favor_sesion(
                request.session,
                base_empresa=base,
                monto=monto,
            )
            request.session.modified = True
            return Response(data, status=200 if data.get("msg") == "ok" else 400)

        if str(body.get("borrarSaldoAFavor") or "") == "1":
            data = borrar_saldo_favor_sesion(request.session)
            request.session.modified = True
            return Response(data)

        if str(body.get("resumen") or body.get("traeResumenRecibo") or "") == "1":
            return Response(resumen_recibo_sesion(request.session))

        if str(body.get("controlFinal") or body.get("controlFinalRecibo") or "") == "1":
            return Response(control_final_recibo_sesion(request.session))

        if str(body.get("guardar") or body.get("guardarRecibo") or "") == "1":
            try:
                data = guardar_recibo_mayoristapp(
                    base_empresa=base,
                    session_user=session_user,
                    session=request.session,
                )
            except Exception as exc:
                return Response({"msg": "error", "desc": str(exc)}, status=400)
            request.session.modified = True
            return Response(data)

        if str(body.get("cancelar") or "") == "1":
            cancelar_recibo_sesion(request.session)
            request.session.modified = True
            return Response({"msg": "ok"})

        return Response({"detail": "Acción no soportada."}, status=400)
