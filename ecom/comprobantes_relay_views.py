"""
APIs listados comprobantes mayoristapp (``relay-pedidos`` / ``relay-presupuestos`` / ``relay-remitos``).
"""

from __future__ import annotations

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from ecom.permissions import EcomMayoristappSessionPermission
from ecom.models import EcomMailQueue
from ecom.services.comprobantes_anulacion import anular_pedido_relay
from ecom.services.comprobante_mail_relay import (
    obtener_comprobante_para_mail,
    parsear_parametros_mail,
)
from ecom.services.comprobante_mail_async import encolar_comprobante_mail
from ecom.services.comprobantes_no_cancelados_relay import (
    listar_no_cancelados_relay,
    listar_no_cancelados_resumen_relay,
)
from ecom.services.comprobantes_relay import (
    listar_pedidos_relay,
    listar_presupuestos_relay,
    listar_remitos_relay,
    sugerencias_nro_comp_relay,
)
from ecom.services.mayoristapp_session import leer_idcliente_mayoristapp
from core.utils.administranet_types import to_int_or_none


def _session_base_empresa(request: Request) -> str | None:
    data = (getattr(request, "session", None) or {}).get("user") or {}
    be = data.get("base_empresa")
    return str(be).strip() if be else None


def _session_user(request: Request) -> dict:
    return (getattr(request, "session", None) or {}).get("user") or {}


class ComprobantesPedidosRelayAPIView(APIView):
    """
    POST ``/ecom/api/mayoristapp/comprobantes/pedidos/?ajax=1``

    Paridad listado JSON (PHP devolvía HTML de tabla). Cuerpo: mismos campos que ``relay-pedidos.php`` (``vendedor``, ``campoBusca``, etc.).
    """

    permission_classes = [EcomMayoristappSessionPermission]

    def post(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"detail": "No se encontró base_empresa en la sesión."}, status=400)
        if "ajax" not in request.query_params:
            return Response({"detail": "Parámetro ajax requerido."}, status=400)
        lim = to_int_or_none(request.data.get("limit")) or 500
        idc = leer_idcliente_mayoristapp(request)
        rows = listar_pedidos_relay(
            base,
            dict(request.data),
            _session_user(request),
            idc,
            limit=lim,
        )
        return Response({"total": len(rows), "filas": rows})


class ComprobantesPresupuestosRelayAPIView(APIView):
    """POST ``/ecom/api/mayoristapp/comprobantes/presupuestos/?ajax=1``"""

    permission_classes = [EcomMayoristappSessionPermission]

    def post(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"detail": "No se encontró base_empresa en la sesión."}, status=400)
        if "ajax" not in request.query_params:
            return Response({"detail": "Parámetro ajax requerido."}, status=400)
        lim = to_int_or_none(request.data.get("limit")) or 500
        idc = leer_idcliente_mayoristapp(request)
        rows = listar_presupuestos_relay(
            base,
            dict(request.data),
            _session_user(request),
            idc,
            limit=lim,
        )
        return Response({"total": len(rows), "filas": rows})


class ComprobantesRemitosRelayAPIView(APIView):
    """POST ``/ecom/api/mayoristapp/comprobantes/remitos/?ajax=1``"""

    permission_classes = [EcomMayoristappSessionPermission]

    def post(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"detail": "No se encontró base_empresa en la sesión."}, status=400)
        if "ajax" not in request.query_params:
            return Response({"detail": "Parámetro ajax requerido."}, status=400)
        lim = to_int_or_none(request.data.get("limit")) or 500
        idc = leer_idcliente_mayoristapp(request)
        rows = listar_remitos_relay(
            base,
            dict(request.data),
            _session_user(request),
            idc,
            limit=lim,
        )
        return Response({"total": len(rows), "filas": rows})


class ComprobantesSugerenciasNroRelayAPIView(APIView):
    """
    GET ``/ecom/api/mayoristapp/comprobantes/sugerencias-nro/?ajax=1&q=…&tipo=PED|PRE|REM``

    Paridad ``queryString`` en relays (autocomplete ``NroCompBusq``).
    """

    permission_classes = [EcomMayoristappSessionPermission]

    def get(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"detail": "No se encontró base_empresa en la sesión."}, status=400)
        if "ajax" not in request.query_params:
            return Response({"detail": "Parámetro ajax requerido."}, status=400)
        q = request.query_params.get("q") or request.query_params.get("queryString") or ""
        tc = (request.query_params.get("tipo") or "PED").strip().upper()
        idc = leer_idcliente_mayoristapp(request)
        nums = sugerencias_nro_comp_relay(
            base,
            tc,
            q,
            _session_user(request),
            idc,
        )
        return Response({"sugerencias": nums, "total": len(nums)})


class ComprobanteAMailRelayAPIView(APIView):
    """
    GET ``/ecom/api/mayoristapp/comprobantes/comprobante-a-mail/?codMov=...&tipocomprobante=...``

    Paridad ``relay-comprobante-a-mail.php``: resuelve comprobante y genera payload/token
    para redirección a ``fin-comprobante``. No envía mail en v1.
    """

    permission_classes = [EcomMayoristappSessionPermission]

    def get(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"detail": "No se encontró base_empresa en la sesión."}, status=400)
        parsed = parsear_parametros_mail(request.query_params)
        if not parsed:
            return Response({"detail": "Parámetros codMov y tipocomprobante son requeridos."}, status=400)
        cod_mov, tipo = parsed
        idc = leer_idcliente_mayoristapp(request)
        data = obtener_comprobante_para_mail(base, cod_mov, tipo, idcliente=idc)
        if not data:
            return Response({"detail": "No se encontró el comprobante solicitado."}, status=404)
        return Response(data)


class ComprobanteAMailEnqueueRelayAPIView(APIView):
    """
    POST ``/ecom/api/mayoristapp/comprobantes/comprobante-a-mail/enqueue/?ajax=1``

    Encola envío async del comprobante por mail.
    """

    permission_classes = [EcomMayoristappSessionPermission]

    def post(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"detail": "No se encontró base_empresa en la sesión."}, status=400)
        if "ajax" not in request.query_params:
            return Response({"detail": "Parámetro ajax requerido."}, status=400)
        parsed = parsear_parametros_mail(request.data)
        if not parsed:
            return Response({"detail": "Parámetros codMov y tipocomprobante son requeridos."}, status=400)
        to_email = str(request.data.get("email") or "").strip()
        if not to_email or "@" not in to_email:
            return Response({"detail": "Email destino inválido."}, status=400)
        cod_mov, tipo = parsed
        idc = leer_idcliente_mayoristapp(request)
        item = encolar_comprobante_mail(
            base_empresa=base,
            cod_mov=cod_mov,
            tipo_comp=tipo,
            to_email=to_email,
            idcliente=idc,
        )
        if item is None:
            return Response({"detail": "No se encontró el comprobante solicitado."}, status=404)
        return Response({"msg": "ok", "queue_id": item.id, "status": item.status}, status=202)


class ComprobanteAMailQueueStatusRelayAPIView(APIView):
    """GET ``/ecom/api/mayoristapp/comprobantes/comprobante-a-mail/queue-status/?ajax=1&queue_id=...``"""

    permission_classes = [EcomMayoristappSessionPermission]

    def get(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"detail": "No se encontró base_empresa en la sesión."}, status=400)
        if "ajax" not in request.query_params:
            return Response({"detail": "Parámetro ajax requerido."}, status=400)
        qid = to_int_or_none(request.query_params.get("queue_id"))
        if qid is None:
            return Response({"detail": "queue_id requerido."}, status=400)
        item = EcomMailQueue.objects.filter(id=qid, base_empresa=base).first()
        if item is None:
            return Response({"detail": "No se encontró el item de cola."}, status=404)
        return Response(
            {
                "queue_id": item.id,
                "status": item.status,
                "attempts": item.attempts,
                "last_error": item.last_error,
                "to_email": item.to_email,
                "subject": item.subject,
            }
        )


class ComprobantesNoCanceladosRelayAPIView(APIView):
    """POST ``/ecom/api/mayoristapp/comprobantes/no-cancelados/?ajax=1``"""

    permission_classes = [EcomMayoristappSessionPermission]

    def post(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"detail": "No se encontró base_empresa en la sesión."}, status=400)
        if "ajax" not in request.query_params:
            return Response({"detail": "Parámetro ajax requerido."}, status=400)
        idc = leer_idcliente_mayoristapp(request)
        if idc is None:
            return Response({"detail": "No hay idcliente en sesión."}, status=400)
        lim = to_int_or_none(request.data.get("limit")) or 1000
        data = listar_no_cancelados_relay(base, dict(request.data), idc, limit=lim)
        filas = data.get("filas", [])
        return Response({"total": len(filas), "filas": filas, "saldo_al_dia": data.get("saldo_al_dia", 0)})


class ComprobantesNoCanceladosResumenRelayAPIView(APIView):
    """POST ``/ecom/api/mayoristapp/comprobantes/no-cancelados-resumen/?ajax=1``"""

    permission_classes = [EcomMayoristappSessionPermission]

    def post(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"detail": "No se encontró base_empresa en la sesión."}, status=400)
        if "ajax" not in request.query_params:
            return Response({"detail": "Parámetro ajax requerido."}, status=400)
        idc = leer_idcliente_mayoristapp(request)
        if idc is None:
            return Response({"detail": "No hay idcliente en sesión."}, status=400)
        lim = to_int_or_none(request.data.get("limit")) or 1000
        data = listar_no_cancelados_resumen_relay(base, dict(request.data), idc, limit=lim)
        filas = data.get("filas", [])
        return Response({"total": len(filas), "filas": filas, "saldo_al_dia": data.get("saldo_al_dia", 0)})


class ComprobantesAnularPedidoRelayAPIView(APIView):
    """POST ``/ecom/api/mayoristapp/comprobantes/anular-pedido/?ajax=1``"""

    permission_classes = [EcomMayoristappSessionPermission]

    def post(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"detail": "No se encontró base_empresa en la sesión."}, status=400)
        if "ajax" not in request.query_params:
            return Response({"detail": "Parámetro ajax requerido."}, status=400)
        if str(request.data.get("anularPedido") or "") != "1":
            return Response({"detail": "Parámetro anularPedido=1 requerido."}, status=400)
        data = anular_pedido_relay(base, request.data.get("codMovPedido"))
        status_code = 200 if data.get("msg") == "ok" else 400
        return Response(data, status=status_code)
