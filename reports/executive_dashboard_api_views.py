"""
API dashboard gerencial — solo lectura legacy AdministraNET.
"""
from __future__ import annotations

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.permissions import user_has_full_access

from .permissions import ManagerialReportsPermission
from .services.executive_dashboard.area_visibility import (
    AREA_DISABLED_PAYLOAD,
    areas_catalog,
    is_cc_area_enabled,
    set_cc_areas,
)
from .services.executive_dashboard.base import (
    base_empresa_from_request,
    build_meta,
    legacy_cursor,
    mpr_modulo_activo,
    resolve_filters_from_query_params,
)
from .services.executive_dashboard.command_center import run_command_center
from .services.executive_dashboard.cross_metrics import (
    fetch_cruzados_resumen,
    list_backorder_detalle,
)
from .services.executive_dashboard.exceptions import InvalidDashboardFilters, LegacyReadError, is_legacy_db_error
from .services.executive_dashboard.inventory_metrics import (
    fetch_inventario_resumen,
    list_existencias,
)
from .services.executive_dashboard.manufacturing_metrics import fetch_manufactura_resumen
from .services.executive_dashboard.purchase_metrics import fetch_compras_resumen
from .services.executive_dashboard.banco_metrics import fetch_tesoreria_banco_resumen
from .services.executive_dashboard.tesoreria_metrics import (
    fetch_tesoreria_resumen,
    list_movimientos_caja,
)
from .services.executive_dashboard.ventas_cobros_metrics import (
    fetch_ventas_cobros_resumen,
    list_cobros_detalle,
)
from .services.executive_dashboard.ventas_metrics import (
    fetch_ventas_resumen,
    list_pedidos_pendientes,
    list_remitos_no_facturados,
)


class ExecutiveDashboardMixin:
    permission_classes = [ManagerialReportsPermission]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        from reports.services.report_visibility import command_center_visible_for_user

        empresa = getattr(request.user, "empresa_activa", None)
        empresa_id = empresa.id if empresa else None
        if not command_center_visible_for_user(request.user, empresa_id=empresa_id):
            from rest_framework.exceptions import NotFound

            raise NotFound("Informe no disponible")

    def _area_disabled_response(self, area_key: str):
        """None si el área está habilitada; Response de degradación si no."""
        if is_cc_area_enabled(area_key):
            return None
        payload = dict(AREA_DISABLED_PAYLOAD)
        payload["motivo"] = f"Área «{area_key}» deshabilitada en la configuración del Command Center."
        return Response(payload)

    def _filters_or_error(self, request):
        base = base_empresa_from_request(request)
        if not base:
            return None, Response(
                {
                    "detail": "No se pudo determinar la base de datos de la empresa.",
                    "error_type": "invalid_data",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            filters = resolve_filters_from_query_params(
                request.query_params, base_empresa=base
            )
        except InvalidDashboardFilters as exc:
            return None, Response(
                {"detail": str(exc), "error_type": "invalid_data"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return filters, None

    def _legacy_error_response(self, exc: Exception) -> Response:
        return Response(
            {
                "detail": f"Error al consultar datos legacy: {exc}",
                "error_type": "legacy_transient_failure",
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    def _legacy_read_error(self, exc: Exception) -> LegacyReadError:
        if isinstance(exc, LegacyReadError):
            return exc
        return LegacyReadError(str(exc))


class ExecutiveDashboardAreasAPIView(ExecutiveDashboardMixin, APIView):
    """GET catálogo de áreas; PATCH (solo supervisor) persiste config global."""

    def get(self, request, *args, **kwargs):
        mpr_active = mpr_modulo_activo()
        payload = areas_catalog(mpr_active=mpr_active)
        payload["can_edit"] = user_has_full_access(request.user)
        return Response(payload)

    def patch(self, request, *args, **kwargs):
        if not user_has_full_access(request.user):
            return Response(
                {
                    "detail": "Solo el usuario supervisor puede cambiar las áreas del Command Center.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        areas = request.data.get("areas")
        if areas is None:
            return Response(
                {"detail": "Se requiere el objeto «areas»."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            stored = set_cc_areas(areas, user=request.user)
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        mpr_active = mpr_modulo_activo()
        payload = areas_catalog(mpr_active=mpr_active)
        payload["areas_config"] = stored
        payload["can_edit"] = True
        payload["message"] = "Áreas del Command Center actualizadas."
        return Response(payload)


class ExecutiveDashboardAPIView(ExecutiveDashboardMixin, APIView):
    """GET orquestador command center."""

    def get(self, request, *args, **kwargs):
        filters, err = self._filters_or_error(request)
        if err:
            return err
        try:
            payload = run_command_center(filters)
        except LegacyReadError as exc:
            return self._legacy_error_response(exc)
        except Exception as exc:
            if is_legacy_db_error(exc):
                return self._legacy_error_response(self._legacy_read_error(exc))
            raise
        return Response(payload)


class ExecutiveDashboardVentasResumenAPIView(ExecutiveDashboardMixin, APIView):
    def get(self, request, *args, **kwargs):
        disabled = self._area_disabled_response("ventas")
        if disabled:
            return disabled
        filters, err = self._filters_or_error(request)
        if err:
            return err
        try:
            with legacy_cursor(filters.base_empresa) as cursor:
                payload = fetch_ventas_resumen(cursor, filters)
        except LegacyReadError as exc:
            return self._legacy_error_response(exc)
        return Response(payload)


class ExecutiveDashboardInventarioResumenAPIView(ExecutiveDashboardMixin, APIView):
    def get(self, request, *args, **kwargs):
        disabled = self._area_disabled_response("inventario")
        if disabled:
            return disabled
        filters, err = self._filters_or_error(request)
        if err:
            return err
        try:
            with legacy_cursor(filters.base_empresa) as cursor:
                payload = fetch_inventario_resumen(cursor, filters)
        except LegacyReadError as exc:
            return self._legacy_error_response(exc)
        return Response(payload)


class ExecutiveDashboardComprasResumenAPIView(ExecutiveDashboardMixin, APIView):
    def get(self, request, *args, **kwargs):
        disabled = self._area_disabled_response("compras")
        if disabled:
            return disabled
        filters, err = self._filters_or_error(request)
        if err:
            return err
        try:
            with legacy_cursor(filters.base_empresa) as cursor:
                payload = fetch_compras_resumen(cursor, filters)
        except LegacyReadError as exc:
            return self._legacy_error_response(exc)
        return Response(payload)


class ExecutiveDashboardManufacturaResumenAPIView(ExecutiveDashboardMixin, APIView):
    def get(self, request, *args, **kwargs):
        disabled = self._area_disabled_response("manufactura")
        if disabled:
            return disabled
        filters, err = self._filters_or_error(request)
        if err:
            return err
        if not mpr_modulo_activo():
            return Response(
                {
                    "pedidos_fabrica_pendientes": 0,
                    "opt_atrasadas": 0,
                    "unidades_pendientes_produccion": 0.0,
                    "items_urgentes": 0,
                    "disponible": False,
                    "motivo": "Módulo MPR no activo.",
                    "meta": build_meta(
                        filters,
                        notas_semanticas=["Área manufactura oculta: módulo MPR inactivo."],
                    ),
                }
            )
        payload = fetch_manufactura_resumen(filters.base_empresa, filters)
        return Response(payload)


class ExecutiveDashboardCruzadosResumenAPIView(ExecutiveDashboardMixin, APIView):
    def get(self, request, *args, **kwargs):
        disabled = self._area_disabled_response("cruzados")
        if disabled:
            return disabled
        filters, err = self._filters_or_error(request)
        if err:
            return err
        try:
            with legacy_cursor(filters.base_empresa) as cursor:
                payload = fetch_cruzados_resumen(cursor, filters)
        except LegacyReadError as exc:
            return self._legacy_error_response(exc)
        return Response(payload)


class ExecutiveDashboardVentasPedidosPendientesAPIView(ExecutiveDashboardMixin, APIView):
    def get(self, request, *args, **kwargs):
        disabled = self._area_disabled_response("ventas")
        if disabled:
            return disabled
        filters, err = self._filters_or_error(request)
        if err:
            return err
        try:
            with legacy_cursor(filters.base_empresa) as cursor:
                payload = list_pedidos_pendientes(cursor, filters)
        except LegacyReadError as exc:
            return self._legacy_error_response(exc)
        return Response(payload)


class ExecutiveDashboardVentasRemitosNoFacturadosAPIView(ExecutiveDashboardMixin, APIView):
    def get(self, request, *args, **kwargs):
        disabled = self._area_disabled_response("ventas")
        if disabled:
            return disabled
        filters, err = self._filters_or_error(request)
        if err:
            return err
        try:
            with legacy_cursor(filters.base_empresa) as cursor:
                payload = list_remitos_no_facturados(cursor, filters)
        except LegacyReadError as exc:
            return self._legacy_error_response(exc)
        return Response(payload)


class ExecutiveDashboardCruzadosBackorderAPIView(ExecutiveDashboardMixin, APIView):
    def get(self, request, *args, **kwargs):
        disabled = self._area_disabled_response("cruzados")
        if disabled:
            return disabled
        filters, err = self._filters_or_error(request)
        if err:
            return err
        try:
            with legacy_cursor(filters.base_empresa) as cursor:
                payload = list_backorder_detalle(cursor, filters)
        except LegacyReadError as exc:
            return self._legacy_error_response(exc)
        return Response(payload)


class ExecutiveDashboardInventarioExistenciasAPIView(ExecutiveDashboardMixin, APIView):
    def get(self, request, *args, **kwargs):
        disabled = self._area_disabled_response("inventario")
        if disabled:
            return disabled
        filters, err = self._filters_or_error(request)
        if err:
            return err
        try:
            with legacy_cursor(filters.base_empresa) as cursor:
                payload = list_existencias(cursor, filters)
        except LegacyReadError as exc:
            return self._legacy_error_response(exc)
        return Response(payload)


class ExecutiveDashboardTesoreriaResumenAPIView(ExecutiveDashboardMixin, APIView):
    def get(self, request, *args, **kwargs):
        disabled = self._area_disabled_response("tesoreria")
        if disabled:
            return disabled
        filters, err = self._filters_or_error(request)
        if err:
            return err
        try:
            with legacy_cursor(filters.base_empresa) as cursor:
                payload = fetch_tesoreria_resumen(cursor, filters)
        except LegacyReadError as exc:
            return self._legacy_error_response(exc)
        return Response(payload)


class ExecutiveDashboardVentasCobrosResumenAPIView(ExecutiveDashboardMixin, APIView):
    def get(self, request, *args, **kwargs):
        disabled = self._area_disabled_response("ventas_cobros")
        if disabled:
            return disabled
        filters, err = self._filters_or_error(request)
        if err:
            return err
        try:
            with legacy_cursor(filters.base_empresa) as cursor:
                payload = fetch_ventas_cobros_resumen(cursor, filters)
        except LegacyReadError as exc:
            return self._legacy_error_response(exc)
        return Response(payload)


class ExecutiveDashboardTesoreriaBancoResumenAPIView(ExecutiveDashboardMixin, APIView):
    def get(self, request, *args, **kwargs):
        disabled = self._area_disabled_response("tesoreria")
        if disabled:
            return disabled
        filters, err = self._filters_or_error(request)
        if err:
            return err
        try:
            with legacy_cursor(filters.base_empresa) as cursor:
                payload = fetch_tesoreria_banco_resumen(cursor, filters)
        except LegacyReadError as exc:
            return self._legacy_error_response(exc)
        return Response(payload)


class ExecutiveDashboardVentasCobrosDetalleAPIView(ExecutiveDashboardMixin, APIView):
    def get(self, request, *args, **kwargs):
        disabled = self._area_disabled_response("ventas_cobros")
        if disabled:
            return disabled
        filters, err = self._filters_or_error(request)
        if err:
            return err
        try:
            with legacy_cursor(filters.base_empresa) as cursor:
                payload = list_cobros_detalle(cursor, filters)
        except LegacyReadError as exc:
            return self._legacy_error_response(exc)
        return Response(payload)


class ExecutiveDashboardTesoreriaMovimientosCajaAPIView(ExecutiveDashboardMixin, APIView):
    def get(self, request, *args, **kwargs):
        disabled = self._area_disabled_response("tesoreria")
        if disabled:
            return disabled
        filters, err = self._filters_or_error(request)
        if err:
            return err
        try:
            with legacy_cursor(filters.base_empresa) as cursor:
                payload = list_movimientos_caja(cursor, filters)
        except LegacyReadError as exc:
            return self._legacy_error_response(exc)
        return Response(payload)
