"""
API dashboard gerencial — solo lectura legacy AdministraNET.
"""
from __future__ import annotations

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.permissions import user_has_full_access, user_has_permission

from .permissions import CommandCenterPermission
from .services.executive_dashboard.area_visibility import (
    areas_catalog,
    resolve_cc_areas_for_user,
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
from .services.executive_dashboard.comercial_v45 import (
    COMERCIAL_V45_DETAIL_KEYS,
    fetch_comercial_ventas_v45,
    list_comercial_v45_detail,
)
from .services.executive_dashboard.cross_metrics import (
    fetch_cruzados_resumen,
    list_backorder_detalle,
)
from .services.executive_dashboard.exceptions import InvalidDashboardFilters, LegacyReadError, is_legacy_db_error
from .services.executive_dashboard.inventory_metrics import (
    fetch_inventario_resumen,
    list_existencias,
)
from .services.executive_dashboard.stock_v45 import STOCK_V45_KEYS, fetch_stock_v45
from .services.executive_dashboard.stock_v45_detail import list_stock_v45_detail
from .services.executive_dashboard.resumen_v45 import fetch_resumen_v45
from .services.executive_dashboard.preparacion_v45 import fetch_preparacion_v45
from .services.executive_dashboard.manufacturing_metrics import fetch_manufactura_resumen
from .services.executive_dashboard.compras_v45 import fetch_compras_v45
from .services.executive_dashboard.financiero_v45 import fetch_financiero_v45
from .services.executive_dashboard.contable_v45 import fetch_contable_v45
from .services.executive_dashboard.impositivo_v45 import fetch_impositivo_v45
from .services.executive_dashboard.libros_v45 import fetch_libros_v45
from .services.executive_dashboard.logistica_v45 import fetch_logistica_v45
from .services.executive_dashboard.gastos_v45 import fetch_gastos_v45
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
from .services.executive_dashboard.territory import (
    TerritoryAccessDenied,
    constrain_filters_to_user,
    list_filter_options,
)


class ExecutiveDashboardMixin:
    permission_classes = [CommandCenterPermission]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        from reports.services.report_visibility import command_center_visible_for_user

        empresa = getattr(request.user, "empresa_activa", None)
        empresa_id = empresa.id if empresa else None
        if not command_center_visible_for_user(request.user, empresa_id=empresa_id):
            from rest_framework.exceptions import NotFound

            raise NotFound("Informe no disponible")

    def _area_disabled_response(self, area_key: str):
        """El gate del servidor se aplica también a cada detalle."""
        self._cc_area_key = area_key
        allowed = resolve_cc_areas_for_user(
            self.request.user, mpr_active=mpr_modulo_activo()
        )
        if allowed.get(area_key):
            return None
        return Response(
            {"detail": "Tablero no autorizado o deshabilitado."},
            status=status.HTTP_403_FORBIDDEN,
        )

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
            filters = constrain_filters_to_user(
                request.user, filters, area_key=getattr(self, "_cc_area_key", "")
            )
        except InvalidDashboardFilters as exc:
            return None, Response(
                {"detail": str(exc), "error_type": "invalid_data"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except TerritoryAccessDenied as exc:
            return None, Response(
                {"detail": str(exc), "error_type": "territory_denied"},
                status=status.HTTP_403_FORBIDDEN,
            )
        except LegacyReadError as exc:
            return None, self._legacy_error_response(exc)
        except Exception as exc:
            if is_legacy_db_error(exc):
                return None, self._legacy_error_response(self._legacy_read_error(exc))
            raise
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
        can_edit = user_has_full_access(request.user)
        effective = resolve_cc_areas_for_user(request.user, mpr_active=mpr_active)
        payload["areas"] = effective
        if not can_edit:
            payload.pop("areas_config", None)
            payload["keys"] = [key for key in payload["keys"] if effective.get(key)]
            payload["labels"] = {key: label for key, label in payload["labels"].items() if effective.get(key)}
        payload["can_edit"] = can_edit
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


class ExecutiveDashboardFilterOptionsAPIView(ExecutiveDashboardMixin, APIView):
    """Opciones de PV, sucursal y depósito bajo los permisos del usuario."""

    def get(self, request, *args, **kwargs):
        filter_type = request.query_params.get("type", "")
        if filter_type not in {"puntos_venta", "sucursales", "depositos"}:
            return Response({"detail": "Filtro desconocido."}, status=status.HTTP_400_BAD_REQUEST)
        base = base_empresa_from_request(request)
        if not base:
            return Response({"detail": "Empresa no disponible."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            options = list_filter_options(request.user, base, filter_type)
        except LegacyReadError as exc:
            return self._legacy_error_response(exc)
        except Exception as exc:
            if is_legacy_db_error(exc):
                return self._legacy_error_response(self._legacy_read_error(exc))
            raise
        return Response({filter_type: options})


class ExecutiveDashboardAPIView(ExecutiveDashboardMixin, APIView):
    """GET orquestador command center."""

    def get(self, request, *args, **kwargs):
        area_key = (request.query_params.get("tablero") or "").strip()
        if not area_key:
            return Response(
                {"detail": "Seleccioná un tablero antes de consultar."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        disabled = self._area_disabled_response(area_key)
        if disabled:
            return disabled
        filters, err = self._filters_or_error(request)
        if err:
            return err
        presentation = request.query_params.get("presentacion", "unidad")
        if area_key == "inventario" and presentation not in {"unidad", "display", "bulto"}:
            return Response({"detail": "Presentación desconocida."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            payload = run_command_center(
                filters,
                allowed_areas={area_key: True},
                show_stock_costs=user_has_permission(request.user, "reports.view_managerial"),
                v45_sales=area_key == "ventas",
                gross_sales=str(request.query_params.get("incluir_impuestos", "")).lower() in {"1", "true", "si"},
                compare_sales=request.query_params.get("comparar") == "anterior",
                v45_stock=area_key == "inventario",
                stock_presentation=presentation,
                compare_stock=request.query_params.get("comparar") == "anterior",
            )
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


class ExecutiveDashboardResumenV45APIView(ExecutiveDashboardMixin, APIView):
    """Resumen gerencial V45, con los mismos filtros y permisos del orquestador."""

    def get(self, request, *args, **kwargs):
        disabled = self._area_disabled_response("resumen_general")
        if disabled:
            return disabled
        filters, err = self._filters_or_error(request)
        if err:
            return err
        gross = str(request.query_params.get("incluir_impuestos", "")).lower() in {"1", "true", "si"}
        try:
            with legacy_cursor(filters.base_empresa) as cursor:
                payload = fetch_resumen_v45(cursor, filters, gross=gross)
        except LegacyReadError as exc:
            return self._legacy_error_response(exc)
        except Exception as exc:
            if is_legacy_db_error(exc):
                return self._legacy_error_response(self._legacy_read_error(exc))
            raise
        return Response(payload)


class ExecutiveDashboardPreparacionV45APIView(ExecutiveDashboardMixin, APIView):
    """Preparación de pedidos; cruza documentos por vínculos operativos."""

    def get(self, request, *args, **kwargs):
        disabled = self._area_disabled_response("preparacion_pedidos")
        if disabled:
            return disabled
        filters, err = self._filters_or_error(request)
        if err:
            return err
        try:
            with legacy_cursor(filters.base_empresa) as cursor:
                payload = fetch_preparacion_v45(cursor, filters)
        except LegacyReadError as exc:
            return self._legacy_error_response(exc)
        except Exception as exc:
            if is_legacy_db_error(exc):
                return self._legacy_error_response(self._legacy_read_error(exc))
            raise
        return Response(payload)


class ExecutiveDashboardComercialVentasV45APIView(ExecutiveDashboardMixin, APIView):
    """Los 16 KPI de Comercial/Ventas, con permiso de costos independiente."""

    def get(self, request, *args, **kwargs):
        disabled = self._area_disabled_response("ventas")
        if disabled:
            return disabled
        filters, err = self._filters_or_error(request)
        if err:
            return err
        gross = str(request.query_params.get("incluir_impuestos", "")).lower() in {"1", "true", "si"}
        compare_previous = request.query_params.get("comparar") == "anterior"
        try:
            with legacy_cursor(filters.base_empresa) as cursor:
                payload = fetch_comercial_ventas_v45(
                    cursor, filters, gross=gross,
                    include_profit=user_has_permission(request.user, "reports.view_managerial"),
                    compare_previous=compare_previous,
                )
        except LegacyReadError as exc:
            return self._legacy_error_response(exc)
        except Exception as exc:
            if is_legacy_db_error(exc):
                return self._legacy_error_response(self._legacy_read_error(exc))
            raise
        return Response(payload)


class ExecutiveDashboardComercialVentasV45DetailAPIView(ExecutiveDashboardMixin, APIView):
    """Detalle protegido de cada KPI de Comercial/Ventas V45."""

    def get(self, request, *args, **kwargs):
        disabled = self._area_disabled_response("ventas")
        if disabled:
            return disabled
        kpi = request.query_params.get("kpi", "")
        if kpi not in COMERCIAL_V45_DETAIL_KEYS:
            return Response({"detail": "Indicador desconocido."}, status=status.HTTP_400_BAD_REQUEST)
        filters, err = self._filters_or_error(request)
        if err:
            return err
        gross = str(request.query_params.get("incluir_impuestos", "")).lower() in {"1", "true", "si"}
        try:
            with legacy_cursor(filters.base_empresa) as cursor:
                payload = list_comercial_v45_detail(
                    cursor, filters, kpi=kpi, gross=gross,
                    allow_cost=user_has_permission(request.user, "reports.view_managerial"),
                    order=request.query_params.get("orden", "fecha_desc"),
                )
        except PermissionError:
            return Response({"detail": "Sin permiso de costos."}, status=status.HTTP_403_FORBIDDEN)
        except LegacyReadError as exc:
            return self._legacy_error_response(exc)
        except Exception as exc:
            if is_legacy_db_error(exc):
                return self._legacy_error_response(self._legacy_read_error(exc))
            raise
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
            if not user_has_permission(request.user, "reports.view_managerial"):
                payload["valor_stock"] = None
        except LegacyReadError as exc:
            return self._legacy_error_response(exc)
        return Response(payload)


class ExecutiveDashboardStockV45APIView(ExecutiveDashboardMixin, APIView):
    """Los 14 KPI de Abastecimiento/Stock V45."""

    def get(self, request, *args, **kwargs):
        disabled = self._area_disabled_response("inventario")
        if disabled:
            return disabled
        presentation = request.query_params.get("presentacion", "unidad")
        if presentation not in {"unidad", "display", "bulto"}:
            return Response({"detail": "Presentación desconocida."}, status=status.HTTP_400_BAD_REQUEST)
        filters, err = self._filters_or_error(request)
        if err:
            return err
        try:
            with legacy_cursor(filters.base_empresa) as cursor:
                payload = fetch_stock_v45(
                    cursor, filters, presentation=presentation,
                    show_costs=user_has_permission(request.user, "reports.view_managerial"),
                    compare_previous=request.query_params.get("comparar") == "anterior",
                )
        except LegacyReadError as exc:
            return self._legacy_error_response(exc)
        except Exception as exc:
            if is_legacy_db_error(exc):
                return self._legacy_error_response(self._legacy_read_error(exc))
            raise
        return Response(payload)


class ExecutiveDashboardStockV45DetailAPIView(ExecutiveDashboardMixin, APIView):
    """Detalle de Stock; aplica los mismos filtros y permisos del KPI padre."""

    def get(self, request, *args, **kwargs):
        disabled = self._area_disabled_response("inventario")
        if disabled:
            return disabled
        kpi = request.query_params.get("kpi", "")
        presentation = request.query_params.get("presentacion", "unidad")
        if kpi not in STOCK_V45_KEYS or presentation not in {"unidad", "display", "bulto"}:
            return Response({"detail": "Indicador o presentación desconocida."}, status=status.HTTP_400_BAD_REQUEST)
        filters, err = self._filters_or_error(request)
        if err:
            return err
        try:
            with legacy_cursor(filters.base_empresa) as cursor:
                payload = list_stock_v45_detail(
                    cursor, filters, kpi=kpi, presentation=presentation,
                    allow_cost=user_has_permission(request.user, "reports.view_managerial"),
                    order=request.query_params.get("orden", "fecha_desc"),
                )
        except PermissionError:
            return Response({"detail": "Sin permiso de costos."}, status=status.HTTP_403_FORBIDDEN)
        except LegacyReadError as exc:
            return self._legacy_error_response(exc)
        except Exception as exc:
            if is_legacy_db_error(exc):
                return self._legacy_error_response(self._legacy_read_error(exc))
            raise
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
                payload = fetch_compras_v45(cursor, filters)
        except LegacyReadError as exc:
            return self._legacy_error_response(exc)
        except Exception as exc:
            if is_legacy_db_error(exc):
                return self._legacy_error_response(self._legacy_read_error(exc))
            raise
        return Response(payload)


class ExecutiveDashboardFinancieroV45APIView(ExecutiveDashboardMixin, APIView):
    """Análisis financiero V45; saldos, aging y flujo sin mutaciones."""

    def get(self, request, *args, **kwargs):
        disabled = self._area_disabled_response("financiero")
        if disabled:
            return disabled
        filters, err = self._filters_or_error(request)
        if err:
            return err
        try:
            with legacy_cursor(filters.base_empresa) as cursor:
                payload = fetch_financiero_v45(cursor, filters)
        except LegacyReadError as exc:
            return self._legacy_error_response(exc)
        except Exception as exc:
            if is_legacy_db_error(exc):
                return self._legacy_error_response(self._legacy_read_error(exc))
            raise
        return Response(payload)


class ExecutiveDashboardGestionContableV45APIView(ExecutiveDashboardMixin, APIView):
    """Gestión contable V45, con filtro histórico del asiento."""

    def get(self, request, *args, **kwargs):
        disabled = self._area_disabled_response("gestion_contable")
        if disabled:
            return disabled
        filters, err = self._filters_or_error(request)
        if err:
            return err
        group_raw = request.query_params.get("grupo_contable", "")
        try:
            group = int(group_raw) if group_raw else None
            if group is not None and group <= 0:
                raise ValueError
        except ValueError:
            return Response({"detail": "Grupo contable inválido."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            with legacy_cursor(filters.base_empresa) as cursor:
                payload = fetch_contable_v45(cursor, filters, grupo_contable=group)
        except LegacyReadError as exc:
            return self._legacy_error_response(exc)
        except Exception as exc:
            if is_legacy_db_error(exc):
                return self._legacy_error_response(self._legacy_read_error(exc))
            raise
        return Response(payload)


class ExecutiveDashboardImpositivoV45APIView(ExecutiveDashboardMixin, APIView):
    """Posiciones fiscales V45; importes globales sin clave territorial se ocultan."""

    def get(self, request, *args, **kwargs):
        disabled = self._area_disabled_response("impositivo")
        if disabled:
            return disabled
        filters, err = self._filters_or_error(request)
        if err:
            return err
        try:
            with legacy_cursor(filters.base_empresa) as cursor:
                payload = fetch_impositivo_v45(cursor, filters)
        except LegacyReadError as exc:
            return self._legacy_error_response(exc)
        except Exception as exc:
            if is_legacy_db_error(exc):
                return self._legacy_error_response(self._legacy_read_error(exc))
            raise
        return Response(payload)


class ExecutiveDashboardLibrosV45APIView(ExecutiveDashboardMixin, APIView):
    """Libros y estados V45; el filtro actúa sobre la sucursal del asiento."""

    def get(self, request, *args, **kwargs):
        disabled = self._area_disabled_response("libros_contables")
        if disabled:
            return disabled
        filters, err = self._filters_or_error(request)
        if err:
            return err
        group_raw = request.query_params.get("grupo_contable", "")
        try:
            group = int(group_raw) if group_raw else None
            if group is not None and group <= 0:
                raise ValueError
        except ValueError:
            return Response({"detail": "Grupo contable inválido."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            with legacy_cursor(filters.base_empresa) as cursor:
                payload = fetch_libros_v45(cursor, filters, grupo_contable=group)
        except LegacyReadError as exc:
            return self._legacy_error_response(exc)
        except Exception as exc:
            if is_legacy_db_error(exc):
                return self._legacy_error_response(self._legacy_read_error(exc))
            raise
        return Response(payload)


class ExecutiveDashboardLogisticaV45APIView(ExecutiveDashboardMixin, APIView):
    """Hojas de ruta V45 y documentos vinculados."""

    def get(self, request, *args, **kwargs):
        disabled = self._area_disabled_response("logistica")
        if disabled:
            return disabled
        filters, err = self._filters_or_error(request)
        if err:
            return err
        try:
            with legacy_cursor(filters.base_empresa) as cursor:
                payload = fetch_logistica_v45(cursor, filters)
        except LegacyReadError as exc:
            return self._legacy_error_response(exc)
        except Exception as exc:
            if is_legacy_db_error(exc):
                return self._legacy_error_response(self._legacy_read_error(exc))
            raise
        return Response(payload)


class ExecutiveDashboardGastosV45APIView(ExecutiveDashboardMixin, APIView):
    """Análisis de gastos V45 con fuente seleccionable."""

    def get(self, request, *args, **kwargs):
        disabled = self._area_disabled_response("gastos")
        if disabled:
            return disabled
        filters, err = self._filters_or_error(request)
        if err:
            return err
        raw = request.query_params.get("fuente", "0")
        try:
            source = int(raw)
            if source not in (0, 1, 2, 3):
                raise ValueError
        except ValueError:
            return Response({"detail": "Fuente de gastos inválida."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            with legacy_cursor(filters.base_empresa) as cursor:
                payload = fetch_gastos_v45(cursor, filters, fuente=source)
        except LegacyReadError as exc:
            return self._legacy_error_response(exc)
        except Exception as exc:
            if is_legacy_db_error(exc):
                return self._legacy_error_response(self._legacy_read_error(exc))
            raise
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
