"""Descarga de informes comerciales de la cartera del cliente seleccionado."""

from django.http import HttpResponse
from rest_framework.views import APIView

from ecom.permissions import EcomMayoristappSessionPermission
from ecom.services.cartera_report_pdf import generar_reporte_cartera_pdf
from ecom.services.cliente_relay import cliente_accesible_por_sesion
from ecom.services.comprobantes_no_cancelados_relay import listar_no_cancelados_relay
from ecom.services.ctacte_relay import listar_movimientos_ctacte_relay
from ecom.services.mayoristapp_session import leer_cliente_seleccionado, leer_idcliente_mayoristapp


class CarteraReportPDFAPIView(APIView):
    permission_classes = [EcomMayoristappSessionPermission]

    def post(self, request, tipo):
        if tipo not in ("cuenta-corriente", "no-cancelados"):
            return HttpResponse("Reporte inexistente.", status=404)
        session_user = request.session.get("user") or {}
        base = str(session_user.get("base_empresa") or "").strip()
        cliente_id = leer_idcliente_mayoristapp(request)
        if not base or cliente_id is None:
            return HttpResponse("Seleccioná un cliente.", status=400)
        if not cliente_accesible_por_sesion(base, cliente_id, session_user, solo_cartera=True):
            return HttpResponse("Cliente no disponible para esta sesión.", status=403)
        filters = {key: str(request.data.get(key) or "") for key in ("campoBusca", "fechaDesde", "fechaHasta", "numeroComp")}
        if tipo == "cuenta-corriente":
            rows = listar_movimientos_ctacte_relay(base, filters, cliente_id, limit=2000)
            saldo = None
        else:
            data = listar_no_cancelados_relay(base, {**filters, "solo_cobranzas": True}, cliente_id, limit=5000)
            rows = data["filas"]
            saldo = data["saldo_al_dia"]
        selected = leer_cliente_seleccionado(request)
        selected = selected[0] if isinstance(selected, list) and selected else selected
        selected = selected if isinstance(selected, dict) else {}
        nombre = selected.get("cliente") or selected.get("nombre_cliente") or f"Cliente {cliente_id}"
        pdf = generar_reporte_cartera_pdf(
            base_empresa=base, tipo=tipo, cliente_nombre=nombre, cliente_codigo=cliente_id,
            filas=rows, saldo_al_dia=saldo, filtros=filters,
        )
        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{tipo}-cliente-{cliente_id}.pdf"'
        return response
