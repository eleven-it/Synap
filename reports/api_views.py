from typing import Dict, Any, Optional, List
from datetime import datetime
from django.shortcuts import get_object_or_404
from django.db import models
from core.utils.permissions import user_has_full_access
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .domain import build_catalog_for_user
from .models import ReportDefinition, ReportWorkspace, ReportWidget, ReportDefinitionVersion, ReportTemplate
from .permissions import (
    OperationalReportsPermission,
    ManagerialReportsPermission,
    BuilderReportsPermission,
    InventarioDepositoCatalogPermission,
    INVENTARIO_DEPOSITO_SLUG,
    user_can_access_inventario_deposito,
)
from .services.semantic_service import SemanticService


def get_user_for_foreignkey(user, request=None):
    """
    Helper para obtener un usuario válido para ForeignKeys.
    Si es AdministraNETUser, intenta obtener el UsuarioExtendido desde la sesión.
    Si es UsuarioExtendido, retorna el usuario directamente.
    Si no se puede obtener, retorna None.
    """
    from core.models import UsuarioExtendido
    
    if isinstance(user, UsuarioExtendido):
        return user
    
    # Para AdministraNETUser, intentar obtener UsuarioExtendido desde la sesión
    if hasattr(user, 'id_usuario') or hasattr(user, 'cod_usuario'):
        if request and hasattr(request, 'session') and request.session:
            session_user = request.session.get('user', {})
            id_usuario = session_user.get('id_usuario') or getattr(user, 'id_usuario', None)
            cod_usuario = session_user.get('cod_usuario') or getattr(user, 'cod_usuario', None)
            
            # Intentar obtener por id_usuario primero
            if id_usuario:
                try:
                    return UsuarioExtendido.objects.get(id=id_usuario)
                except UsuarioExtendido.DoesNotExist:
                    pass
            
            # Nota: UsuarioExtendido no tiene un campo cod_usuario directo
            # Si no encontramos por id_usuario, retornamos None
            # Esto es aceptable ya que created_by acepta null=True
    
    # Si no se puede obtener, retornar None
    return None
from .serializers import (
    CatalogEntrySerializer,
    ReportQueryRequestSerializer,
    ReportQueryResponseSerializer,
    KPIResponseSerializer,
    ReportSchemaSerializer,
)
from .services.query_runner import QueryRunnerService
from .services.export_service import ExportService
from .services.schema_service import ReportSchemaService
from .services.config_serializer import serialize_report_config, validate_report_config, normalize_report_config
from .services.execution_engine import ReportExecutionEngine, ReportConfig as ExecutionReportConfig
from .services.connection_pool import get_mysql_pool
# Import opcional de ExportImportService (puede no existir en todas las instalaciones)
try:
    from .services.export_import_service import ExportImportService
except ImportError:
    ExportImportService = None


class ReportCatalogAPIView(APIView):
    """API del catálogo de reportes."""

    def get(self, request, *args, **kwargs):
        empresa = getattr(request.user, "empresa_activa", None)
        empresa_id = empresa.id if empresa else None
        catalog = build_catalog_for_user(request.user, empresa_id)
        serializer = CatalogEntrySerializer([CatalogEntrySerializer.from_catalog_entry(item) for item in catalog], many=True)
        return Response(serializer.data)


class ReportQueryAPIView(APIView):
    """API para ejecutar consultas de reportes."""

    permission_classes = [InventarioDepositoCatalogPermission]

    def post(self, request, *args, **kwargs):
        serializer = ReportQueryRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        report = get_object_or_404(ReportDefinition, slug=payload["slug"], is_active=True)
        if report.slug == INVENTARIO_DEPOSITO_SLUG:
            if not user_can_access_inventario_deposito(request.user):
                return Response(
                    {"detail": "Inventario por depósito no permitido."},
                    status=status.HTTP_403_FORBIDDEN,
                )
        elif report.is_operational() and not OperationalReportsPermission().has_permission(request, self):
            return Response({"detail": "Operational reports not allowed."}, status=status.HTTP_403_FORBIDDEN)
        elif report.is_managerial() and not ManagerialReportsPermission().has_permission(request, self):
            return Response({"detail": "Managerial reports not allowed."}, status=status.HTTP_403_FORBIDDEN)

        # Agregar base_empresa al payload si está disponible en la sesión
        if hasattr(request, 'session') and request.session:
            session_user = request.session.get('user', {})
            if session_user and 'base_empresa' in session_user:
                if 'filters' not in payload:
                    payload['filters'] = {}
                payload['filters']['base_empresa'] = session_user['base_empresa']
                try:
                    from ventas.services.objetivos_mysql import ctx_desde_session_user

                    payload['filters']['_alcance_ctx'] = ctx_desde_session_user(session_user)
                except Exception:
                    pass

        try:
            result = QueryRunnerService(request.user).run(report, payload)
            if result is None:
                return Response(
                    {
                        "detail": "El servicio de consulta retornó None. Verifique los logs del servidor.",
                        "error_type": "NoneResultError",
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Para reportes declarativos, incluir schema y query_result en la respuesta
            response_data = ReportQueryResponseSerializer(result.__dict__).data
            
            # Verificar si es un reporte declarativo
            config = report.config or {}
            if config.get("version") == "declarative-v1":
                # Obtener schema y query_result para reportes declarativos
                schema_service = ReportSchemaService()
                
                # Construir schema
                schema = schema_service.build_schema(report)
                
                # Serializar schema
                from .serializers import ReportSchemaSerializer
                schema_serializer = ReportSchemaSerializer(schema)
                
                # Agregar schema y query_result a la respuesta
                response_data["schema"] = schema_serializer.data
                response_data["query_result"] = {
                    "data": result.data,
                    "meta": result.meta,
                    "totals": result.totals if hasattr(result, 'totals') else {}
                }
            
            return Response(response_data)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error ejecutando reporte {payload.get('slug')}: {e}", exc_info=True)
            return Response(
                {
                    "detail": f"Error al ejecutar el reporte: {str(e)}",
                    "error_type": type(e).__name__,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class WorkspaceSelectionAPIView(APIView):
    """Gestiona el workspace de dashboards seleccionados por el usuario."""

    permission_classes = [IsAuthenticated]

    MAX_ITEMS = 16

    def _get_workspace(self, request):
        """
        Obtiene el workspace del usuario.
        Para AdministraNETUser retorna un objeto mock ya que no podemos usar ForeignKey.
        """
        user = request.user
        empresa = getattr(user, "empresa_activa", None)
        
        # Para AdministraNETUser, no podemos usar ForeignKey directamente
        # Retornar un objeto mock con la misma interfaz
        owner_user = get_user_for_foreignkey(user)
        if owner_user is None:
            # Para usuarios de administraNET, crear objeto mock
            # Los items se pueden almacenar en sesión en el futuro
            from .models import ReportWorkspace
            # Crear instancia sin guardar (no tiene owner válido)
            class MockWorkspace:
                def __init__(self):
                    self.items = request.session.get('report_workspace_items', [])
                    self.empresa = empresa
                
                def save(self, update_fields=None):
                    # Guardar items en sesión en lugar de base de datos
                    request.session['report_workspace_items'] = self.items
                    request.session.modified = True
            
            return MockWorkspace()
        
        workspace, _ = ReportWorkspace.objects.get_or_create(
            owner=owner_user,
            empresa=empresa,
            defaults={"items": []},
        )
        return workspace

    @staticmethod
    def _item_to_slug(item):
        """item puede ser 'slug' (legacy) o 'slug::instance_id'. Devuelve slug."""
        if not item or not isinstance(item, str):
            return item
        return item.split("::")[0] if "::" in item else item

    @staticmethod
    def _item_to_instance_id(item):
        """item puede ser 'slug' o 'slug::instance_id'. Devuelve instance_id o None."""
        if not item or not isinstance(item, str) or "::" not in item:
            return None
        return item.split("::", 1)[1]

    def get(self, request, *args, **kwargs):
        workspace = self._get_workspace(request)
        raw_items = list(workspace.items or [])

        if not raw_items:
            return Response({"slots": [], "count": 0})

        slugs_seen = [self._item_to_slug(it) for it in raw_items]
        reports = (
            ReportDefinition.objects.filter(slug__in=slugs_seen, is_active=True)
            .prefetch_related("widgets")
        )
        report_map = {report.slug: report for report in reports}

        slots = []
        valid_items = []
        for item in raw_items:
            slug = self._item_to_slug(item)
            report = report_map.get(slug)
            if not report:
                continue
            is_declarative = report.config.get("version") == "declarative-v1" if report.config else False
            if not is_declarative:
                widget = report.widgets.order_by("order", "id").first()
                if not widget:
                    continue
            else:
                widget = type('MockWidget', (), {
                    'id': None, 'name': 'Auto', 'widget_type': 'declarative', 'configuration': {}
                })()

            item_key = item if isinstance(item, str) else slug
            instance_id = self._item_to_instance_id(item_key)
            valid_items.append(item_key)
            display_name = report.name
            if instance_id:
                display_name = f"{report.name} ({instance_id[:8]})"

            slots.append({
                "item_key": item_key,
                "slug": report.slug,
                "instance_id": instance_id,
                "display_name": display_name,
                "name": report.name,
                "category": report.category,
                "is_declarative": is_declarative,
                "widget": {
                    "id": getattr(widget, "id", None),
                    "name": widget.name,
                    "widget_type": widget.widget_type,
                    "configuration": widget.configuration or {},
                },
            })

        if valid_items != raw_items:
            workspace.items = valid_items
            workspace.save(update_fields=["items", "updated_at"])

        return Response({"slots": slots, "count": len(slots)})

    def post(self, request, *args, **kwargs):
        slug = request.data.get("slug")
        if not slug:
            return Response({"detail": "Slug requerido."}, status=status.HTTP_400_BAD_REQUEST)

        report = ReportDefinition.objects.filter(slug=slug, is_active=True).first()
        if not report:
            return Response({"detail": "Reporte no encontrado."}, status=status.HTTP_404_NOT_FOUND)

        workspace = self._get_workspace(request)
        current = list(workspace.items or [])
        allow_duplicate = request.data.get("allow_duplicate") is True

        if allow_duplicate:
            import uuid
            instance_id = str(uuid.uuid4())[:12]
            item_key = f"{slug}::{instance_id}"
        else:
            # Sin duplicados: si ya existe cualquier item con este slug, devolver exists
            existing = [it for it in current if self._item_to_slug(it) == slug]
            if existing:
                return Response({"status": "exists", "count": len(current)})
            item_key = slug

        if len(current) >= self.MAX_ITEMS:
            return Response(
                {"detail": "Se alcanzó el máximo de elementos en el workspace.", "count": len(current)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        current.append(item_key)
        workspace.items = current
        workspace.save(update_fields=["items", "updated_at"])
        return Response({
            "status": "added",
            "count": len(current),
            "item_key": item_key,
            "slug": slug,
            "instance_id": self._item_to_instance_id(item_key),
        })

    def delete(self, request, *args, **kwargs):
        import logging
        logger = logging.getLogger(__name__)
        
        item_key = request.data.get("item_key") or request.data.get("slug")
        logger.info(f"[Workspace DELETE] request.data: {request.data}")
        logger.info(f"[Workspace DELETE] item_key extraído: '{item_key}'")
        
        if not item_key:
            return Response({"detail": "item_key o slug requerido."}, status=status.HTTP_400_BAD_REQUEST)

        workspace = self._get_workspace(request)
        current = list(workspace.items or [])
        logger.info(f"[Workspace DELETE] Items actuales en workspace: {current}")
        
        if item_key not in current:
            logger.warning(f"[Workspace DELETE] item_key '{item_key}' NO encontrado en workspace")
            return Response({"status": "missing", "count": len(current)})

        current = [item for item in current if item != item_key]
        workspace.items = current
        workspace.save(update_fields=["items", "updated_at"])
        logger.info(f"[Workspace DELETE] Item '{item_key}' eliminado. Nuevos items: {current}")
        return Response({"status": "removed", "count": len(current)})

    def patch(self, request, *args, **kwargs):
        """Actualiza el orden de los items en el workspace. items = lista de item_key (slug o slug::instance_id)."""
        order = request.data.get("items") or request.data.get("order")
        if not order or not isinstance(order, list):
            return Response(
                {"detail": "Se requiere una lista 'items' u 'order' de item_key."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if len(order) > self.MAX_ITEMS:
            return Response(
                {"detail": f"Se excedió el máximo de {self.MAX_ITEMS} elementos."},
                status=status.HTTP_400_BAD_REQUEST
            )

        workspace = self._get_workspace(request)
        current = set(workspace.items or [])
        slugs_in_order = [self._item_to_slug(it) for it in order]
        valid_reports = ReportDefinition.objects.filter(
            slug__in=slugs_in_order, is_active=True
        ).values_list("slug", flat=True)
        valid_slugs = set(valid_reports)
        # Mantener solo item_keys que existan en el workspace y cuyo slug sea válido
        valid_order = [it for it in order if it in current and self._item_to_slug(it) in valid_slugs]
        # Añadir al final los current que no estén en valid_order (retrocompatibilidad)
        for it in (workspace.items or []):
            if it not in valid_order:
                valid_order.append(it)

        workspace.items = valid_order
        workspace.save(update_fields=["items", "updated_at"])
        return Response({"status": "updated", "count": len(valid_order)})


class KPIAPIView(APIView):
    """API para KPIs puntuales."""

    permission_classes = [OperationalReportsPermission | ManagerialReportsPermission]

    def get(self, request, *args, **kwargs):
        slug = request.query_params.get("slug")
        report = get_object_or_404(ReportDefinition, slug=slug, is_active=True)
        if report.is_operational() and not OperationalReportsPermission().has_permission(request, self):
            return Response({"detail": "Operational reports not allowed."}, status=status.HTTP_403_FORBIDDEN)
        if report.is_managerial() and not ManagerialReportsPermission().has_permission(request, self):
            return Response({"detail": "Managerial reports not allowed."}, status=status.HTTP_403_FORBIDDEN)

        payload = {
            "kpi": slug,
            "value": 0,
            "unit": request.query_params.get("unit", ""),
            "breakdown": {},
        }
        serializer = KPIResponseSerializer(payload)
        return Response(serializer.data)


class ReportExportAPIView(APIView):
    """API para exportaciones PDF/XLSX."""

    permission_classes = [InventarioDepositoCatalogPermission]

    def post(self, request, *args, **kwargs):
        serializer = ReportQueryRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        export_type = request.query_params.get("type", "xlsx")

        report = get_object_or_404(ReportDefinition, slug=payload["slug"], is_active=True)
        if report.slug == INVENTARIO_DEPOSITO_SLUG:
            if not user_can_access_inventario_deposito(request.user):
                return Response(
                    {"detail": "Inventario por depósito no permitido."},
                    status=status.HTTP_403_FORBIDDEN,
                )
        elif report.is_operational() and not OperationalReportsPermission().has_permission(request, self):
            return Response({"detail": "Operational reports not allowed."}, status=status.HTTP_403_FORBIDDEN)
        elif report.is_managerial() and not ManagerialReportsPermission().has_permission(request, self):
            return Response({"detail": "Managerial reports not allowed."}, status=status.HTTP_403_FORBIDDEN)

        try:
            export_service = ExportService(request.user)
            export_result = export_service.export(report.slug, payload, export_type)
            
            # Retornar el archivo directamente para descarga
            return export_service.get_file_response(export_result)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error exportando reporte: {e}", exc_info=True)
            return Response(
                {"detail": f"Error al exportar el reporte: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ReportVisibilityAPIView(APIView):
    """API para cambiar la visibilidad de reportes (solo para usuario supervisor)."""

    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        """Cambia la visibilidad de un reporte."""
        if not user_has_full_access(request.user):
            return Response(
                {"detail": "Solo el usuario supervisor puede cambiar la visibilidad de reportes."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        slug = request.data.get("slug")
        is_visible = request.data.get("is_visible", True)
        
        if not slug:
            return Response(
                {"detail": "Slug requerido."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            report = ReportDefinition.objects.get(slug=slug)
            old_visible = report.is_visible
            report.is_visible = bool(is_visible)
            report.save(update_fields=["is_visible", "updated_at"])
            
            # Log para debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Visibilidad de reporte '{report.slug}' cambiada de {old_visible} a {report.is_visible} por usuario {request.user.cod_usuario}")
            
            return Response({
                "status": "success",
                "slug": report.slug,
                "is_visible": report.is_visible,
                "message": f"Reporte {'visible' if report.is_visible else 'oculto'} para el resto de usuarios (excepto usuario supervisor)"
            })
        except ReportDefinition.DoesNotExist:
            return Response(
                {"detail": "Reporte no encontrado."},
                status=status.HTTP_404_NOT_FOUND
            )


class ReportSchemaAPIView(APIView):
    """API para obtener el schema de un reporte declarativo."""

    permission_classes = [OperationalReportsPermission | ManagerialReportsPermission]

    def get(self, request, slug, *args, **kwargs):
        """Obtiene el schema de un reporte."""
        report = get_object_or_404(ReportDefinition, slug=slug, is_active=True)
        
        # Verificar permisos
        if report.is_operational() and not OperationalReportsPermission().has_permission(request, self):
            return Response({"detail": "Operational reports not allowed."}, status=status.HTTP_403_FORBIDDEN)
        if report.is_managerial() and not ManagerialReportsPermission().has_permission(request, self):
            return Response({"detail": "Managerial reports not allowed."}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            schema_service = ReportSchemaService()
            schema = schema_service.build_schema(report)
            # Convertir dataclass a dict para el serializer
            schema_dict = {
                "slug": schema.slug,
                "name": schema.name,
                "category": schema.category,
                "is_declarative": schema.is_declarative,
                "metrics": [
                    {
                        "name": m.name,
                        "label": m.label,
                        "expression": m.expression,
                        "data_type": m.data_type,
                        "role": m.role,
                        "format": m.format,
                        "show_in_kpi": getattr(m, "show_in_kpi", True),
                    }
                    for m in schema.metrics
                ],
                "dimensions": [
                    {
                        "name": d.name,
                        "label": d.label,
                        "expression": d.expression,
                        "data_type": d.data_type,
                        "role": d.role,
                        "format": d.format,
                    }
                    for d in schema.dimensions
                ],
                "default_widgets": [
                    {
                        "id": w.id,
                        "kind": w.kind,
                        "title": w.title,
                        "description": w.description,
                        "x_dimension": w.x_dimension,
                        "y_metrics": w.y_metrics,
                        "series_dimension": w.series_dimension,
                        "options": w.options,
                    }
                    for w in schema.default_widgets
                ],
                "options": schema.options,
            }
            serializer = ReportSchemaSerializer(schema_dict)
            return Response(serializer.data)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error obteniendo schema para {slug}: {e}", exc_info=True)
            return Response(
                {
                    "detail": f"Error al obtener schema: {str(e)}",
                    "error_type": type(e).__name__,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ReportFiltersAPIView(APIView):
    """API para obtener opciones de filtros (puntos de venta, sucursales, etc.)."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        """Obtiene las opciones disponibles para los filtros de reportes."""
        # Obtener base_empresa de la sesión
        base_empresa = None
        if hasattr(request, 'session') and request.session:
            session_user = request.session.get('user', {})
            if session_user and 'base_empresa' in session_user:
                base_empresa = session_user['base_empresa']
        
        if not base_empresa:
            return Response(
                {"detail": "No se pudo determinar la base de datos de la empresa."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        filter_type = request.query_params.get("type")
        
        try:
            from django.conf import settings
            import MySQLdb
            
            mysql_config = settings.DATABASES['mysql']
            conn = MySQLdb.connect(
                host=mysql_config['HOST'],
                port=int(mysql_config['PORT']),
                user=mysql_config['USER'],
                passwd=mysql_config['PASSWORD'],
                db=base_empresa,
                charset='latin1'
            )
            cursor = conn.cursor()
            
            if filter_type == "puntos_venta":
                cursor.execute("""
                    SELECT id_punto_venta, nro_punto_venta, id_sucursal
                    FROM punto_venta
                    WHERE anulado = 'No' OR anulado IS NULL
                    ORDER BY nro_punto_venta
                """)
                columns = [desc[0] for desc in cursor.description]
                results = []
                for row in cursor.fetchall():
                    row_dict = dict(zip(columns, row))
                    results.append({
                        "id": row_dict.get("id_punto_venta"),
                        "label": f"PV {row_dict.get('nro_punto_venta', row_dict.get('id_punto_venta'))}",
                        "value": row_dict.get("id_punto_venta"),
                        "sucursal_id": row_dict.get("id_sucursal"),
                    })
                cursor.close()
                conn.close()
                return Response({"puntos_venta": results})
            
            elif filter_type == "sucursales":
                cursor.execute("""
                    SELECT id_sucursal, nombre_sucursal
                    FROM sucursales
                    WHERE anulado = 'No' OR anulado IS NULL
                    ORDER BY nombre_sucursal
                """)
                columns = [desc[0] for desc in cursor.description]
                results = []
                for row in cursor.fetchall():
                    row_dict = dict(zip(columns, row))
                    results.append({
                        "id": row_dict.get("id_sucursal"),
                        "label": row_dict.get("nombre_sucursal", f"Sucursal {row_dict.get('id_sucursal')}"),
                        "value": row_dict.get("id_sucursal"),
                    })
                cursor.close()
                conn.close()
                return Response({"sucursales": results})
            
            elif filter_type == "cajas":
                # Obtener TODAS las cajas activas de caja_abm
                # Se muestran todas para un mejor control, incluso si no tienen movimientos
                cursor.execute("""
                    SELECT id_caja, nombre_caja, tipo_caja
                    FROM caja_abm
                    WHERE anulado = 'No' OR anulado IS NULL
                    ORDER BY nombre_caja
                """)
                columns = [desc[0] for desc in cursor.description]
                results = []
                for row in cursor.fetchall():
                    row_dict = dict(zip(columns, row))
                    nombre_caja = row_dict.get('nombre_caja', '')
                    tipo_caja = row_dict.get('tipo_caja', '')
                    # Formatear label: solo nombre si no hay tipo, o nombre (tipo) si hay tipo
                    if tipo_caja:
                        label = f"{nombre_caja} ({tipo_caja})"
                    else:
                        label = nombre_caja if nombre_caja else f"Caja {row_dict.get('id_caja')}"
                    results.append({
                        "id": row_dict.get("id_caja"),
                        "label": label,
                        "value": row_dict.get("id_caja"),
                        "tipo_caja": tipo_caja,
                    })
                cursor.close()
                conn.close()
                return Response({"cajas": results})
            
            elif filter_type == "clientes":
                # Clientes para filtro "excluir" (NOT IN) en Ventas Netas
                cursor.execute("""
                    SELECT Codigo, nombre_cliente
                    FROM cliente
                    ORDER BY nombre_cliente
                """)
                columns = [desc[0] for desc in cursor.description]
                results = []
                for row in cursor.fetchall():
                    row_dict = dict(zip(columns, row))
                    codigo = row_dict.get("Codigo")
                    nombre = (row_dict.get("nombre_cliente") or "").strip() or f"Cliente {codigo}"
                    results.append({
                        "id": codigo,
                        "label": nombre,
                        "value": codigo,
                    })
                cursor.close()
                conn.close()
                return Response({"clientes": results})
            
            elif filter_type == "depositos":
                # Depósitos para filtro "excluir" en BO (stock disponible)
                cursor.execute("""
                    SELECT CodDeposito, NombreDeposito
                    FROM deposito
                    WHERE (anulado IS NULL OR anulado = 'No')
                    ORDER BY NombreDeposito
                """)
                columns = [desc[0] for desc in cursor.description]
                results = []
                for row in cursor.fetchall():
                    row_dict = dict(zip(columns, row))
                    cod = row_dict.get("CodDeposito")
                    nombre = (row_dict.get("NombreDeposito") or "").strip() or f"Depósito {cod}"
                    results.append({
                        "id": cod,
                        "label": nombre,
                        "value": cod,
                    })
                cursor.close()
                conn.close()
                return Response({"depositos": results})

            elif filter_type == "marcas":
                cursor.execute("""
                    SELECT CodMarca, NombreMarca
                    FROM marca
                    WHERE (anulado IS NULL OR anulado = 'No')
                    ORDER BY NombreMarca
                """)
                columns = [desc[0] for desc in cursor.description]
                results = []
                for row in cursor.fetchall():
                    row_dict = dict(zip(columns, row))
                    cod = row_dict.get("CodMarca")
                    nombre = (row_dict.get("NombreMarca") or "").strip() or f"Marca {cod}"
                    results.append({
                        "id": cod,
                        "label": nombre,
                        "value": cod,
                    })
                cursor.close()
                conn.close()
                return Response({"marcas": results})

            elif filter_type == "rubros":
                cursor.execute("""
                    SELECT CodigoRubro, NombreRubro
                    FROM rubro
                    WHERE (anulado IS NULL OR anulado = 'No')
                    ORDER BY NombreRubro
                """)
                columns = [desc[0] for desc in cursor.description]
                results = []
                for row in cursor.fetchall():
                    row_dict = dict(zip(columns, row))
                    cod = row_dict.get("CodigoRubro")
                    nombre = (row_dict.get("NombreRubro") or "").strip() or f"Rubro {cod}"
                    results.append({
                        "id": cod,
                        "label": nombre,
                        "value": cod,
                    })
                cursor.close()
                conn.close()
                return Response({"rubros": results})

            elif filter_type == "subrubros":
                cursor.execute("""
                    SELECT IDSubRubro, NombreSubRubro, CodigoRubro
                    FROM subrubro
                    WHERE (anulado IS NULL OR anulado = 'No')
                    ORDER BY NombreSubRubro
                """)
                columns = [desc[0] for desc in cursor.description]
                results = []
                for row in cursor.fetchall():
                    row_dict = dict(zip(columns, row))
                    cod = row_dict.get("IDSubRubro")
                    nombre = (row_dict.get("NombreSubRubro") or "").strip() or f"Subrubro {cod}"
                    results.append({
                        "id": cod,
                        "label": nombre,
                        "value": cod,
                    })
                cursor.close()
                conn.close()
                return Response({"subrubros": results})
            
            elif filter_type in ("superarts", "id_manuales"):
                marcas_param = request.query_params.get("marcas") or request.query_params.get("marcas_incluidos")
                marca_ids: list = []
                if marcas_param:
                    for part in str(marcas_param).split(","):
                        part = part.strip()
                        if not part:
                            continue
                        try:
                            marca_ids.append(int(part))
                        except ValueError:
                            continue
                sql = """
                    SELECT DISTINCT art.id_manual
                    FROM articulo art
                    WHERE art.id_manual IS NOT NULL
                      AND TRIM(art.id_manual) <> ''
                """
                params_sa: list = []
                if marca_ids:
                    ph = ",".join(["%s"] * len(marca_ids))
                    sql += f" AND art.CodigoMarca IN ({ph})"
                    params_sa.extend(marca_ids)
                sql += " ORDER BY art.id_manual"
                cursor.execute(sql, params_sa)
                results = []
                for row in cursor.fetchall():
                    val = (row[0] or "").strip()
                    if not val:
                        continue
                    results.append({
                        "id": val,
                        "label": val,
                        "value": val,
                    })
                cursor.close()
                conn.close()
                key = "superarts" if filter_type == "superarts" else "id_manuales"
                return Response({key: results})

            elif filter_type == "viajantes":
                cursor.execute("""
                    SELECT CodViajante, Nombre
                    FROM viajantes
                    WHERE COALESCE(anulado, 'No') = 'No'
                    ORDER BY Nombre
                """)
                columns = [desc[0] for desc in cursor.description]
                results = []
                for row in cursor.fetchall():
                    row_dict = dict(zip(columns, row))
                    cv = row_dict.get("CodViajante")
                    nombre = (row_dict.get("Nombre") or "").strip() or f"Vendedor {cv}"
                    results.append({
                        "id": cv,
                        "label": nombre,
                        "value": cv,
                    })
                cursor.close()
                conn.close()
                return Response({"viajantes": results})
            
            else:
                cursor.close()
                conn.close()
                return Response(
                    {
                        "detail": "Tipo de filtro no válido. Use 'puntos_venta', 'sucursales', 'cajas', "
                        "'clientes', 'depositos', 'marcas', 'rubros', 'subrubros', 'viajantes', "
                        "'superarts' o 'id_manuales'."
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error obteniendo filtros: {e}", exc_info=True)
            return Response(
                {"detail": f"Error al obtener filtros: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ReportBuilderConfigAPIView(APIView):
    """API para obtener y actualizar configuración de reportes en el Builder."""

    permission_classes = [BuilderReportsPermission]

    def get(self, request, slug, *args, **kwargs):
        """Obtiene la configuración de un reporte para edición."""
        # Si el slug es "new", retornar configuración vacía para nuevo reporte
        if slug == "new":
            empresa = getattr(request.user, "empresa_activa", None)
            return Response({
                "name": "Nuevo Reporte",
                "slug": "",
                "category": "operational",
                "description": "",
                "refresh_interval": "daily",
                "show_in_catalog": True,
                "is_visible": True,
                "config": {
                    "version": "declarative-v1",
                    "metrics": [],
                    "dimensions": [],
                    "datasource": "",
                },
                "is_new": True,
                "empresa_id": empresa.id if empresa else None,
            })
        
        report = get_object_or_404(ReportDefinition, slug=slug, is_active=True)
        
        # Verificar que sea declarativo
        config = report.config or {}
        if config.get("version") != "declarative-v1":
            return Response(
                {"detail": "Este reporte no es declarativo. Solo se pueden editar reportes declarativos."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            serialized = serialize_report_config(report)
            return Response(serialized)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error obteniendo config para builder {slug}: {e}", exc_info=True)
            return Response(
                {"detail": f"Error al obtener configuración: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @classmethod
    def _learn_relationships_from_config(
        cls,
        empresa,
        config: Dict[str, Any],
        base_table: str,
        success: bool = True
    ):
        """
        Extrae y registra relaciones de JOINs desde la configuración del reporte.
        
        Args:
            empresa: Instancia de Empresa o None
            config: Configuración normalizada del reporte
            base_table: Tabla principal del reporte
            success: Si el uso fue exitoso
        """
        from .services.relationship_learning import RelationshipLearningService
        
        if not base_table:
            return
        
        joins = config.get("joins", [])
        if not joins or not isinstance(joins, list):
            return
        
        # Construir mapa de alias -> tabla
        alias_to_table = {}
        # Alias por defecto de la tabla base
        # IMPORTANTE: Usar la misma lógica que execution_engine.py para consistencia
        # execution_engine.py usa: table_name[0].lower() (primera letra)
        base_alias = base_table[0].lower() if base_table else "c"
        if base_alias:
            alias_to_table[base_alias] = base_table
        
        # Procesar cada join
        for join_def in joins:
            if not isinstance(join_def, dict):
                continue
            
            # Extraer tabla destino
            target_table = join_def.get("table", "")
            if not target_table:
                continue
            
            # Extraer alias (puede venir en formato "tabla alias" o en campo separado)
            alias = join_def.get("alias", "")
            if not alias:
                # Intentar extraer de "tabla alias"
                parts = target_table.split()
                if len(parts) > 1:
                    target_table = parts[0]
                    alias = parts[-1]
                else:
                    # Generar alias por defecto
                    # IMPORTANTE: Para la tabla base usamos solo la primera letra
                    # Para JOINs, podemos usar lógica más compleja si es necesario
                    # pero por consistencia, también usamos primera letra
                    alias = target_table[0].lower() if target_table else ""
            
            alias_to_table[alias] = target_table
            
            # Extraer relación del ON
            on = join_def.get("on", "")
            if not on:
                continue
            
            # Determinar tabla origen (puede ser base o un join anterior)
            source_table = base_table
            source_alias = base_alias
            
            # Parsear ON para obtener campos
            if isinstance(on, list) and len(on) > 0:
                # Formato estructurado: [{"left": "alias.col", "op": "=", "right": "alias.col"}]
                first_condition = on[0]
                if isinstance(first_condition, dict):
                    left = first_condition.get("left", "")
                    right = first_condition.get("right", "")
                    
                    # Parsear left para obtener tabla origen
                    if '.' in left:
                        left_parts = left.split('.')
                        left_alias = left_parts[0].strip()
                        left_col = left_parts[1].strip() if len(left_parts) > 1 else ""
                        
                        # Mapear alias a tabla
                        source_table = alias_to_table.get(left_alias, base_table)
                        source_alias = left_alias
                    else:
                        left_col = left.strip()
                    
                    # Parsear right para obtener tabla destino y columna
                    if '.' in right:
                        right_parts = right.split('.')
                        right_alias = right_parts[0].strip()
                        right_col = right_parts[1].strip() if len(right_parts) > 1 else ""
                        
                        # Verificar que el alias coincida con el join actual
                        if right_alias == alias and right_col and left_col:
                            # Registrar relación
                            RelationshipLearningService.record_join_usage(
                                empresa=empresa,
                                from_table=source_table,
                                from_column=left_col,
                                to_table=target_table,
                                to_column=right_col,
                                success=success
                            )
            
            elif isinstance(on, str):
                # Formato string: "alias1.col1 = alias2.col2"
                # Parsear básico (solo primera condición si hay AND)
                on_parts = on.split(' AND ')[0].strip()
                
                # Buscar operador
                operators = ['!=', '<=', '>=', '=', '<', '>']
                op_found = None
                op_index = -1
                
                for op in operators:
                    idx = on_parts.find(f' {op} ')
                    if idx != -1:
                        op_found = op
                        op_index = idx
                        break
                
                if op_found and op_index != -1:
                    left_str = on_parts[:op_index].strip()
                    right_str = on_parts[op_index + len(op_found) + 1:].strip()
                    
                    # Parsear left
                    left_col = ""
                    if '.' in left_str:
                        left_parts = left_str.split('.')
                        left_alias = left_parts[0].strip()
                        left_col = left_parts[1].strip() if len(left_parts) > 1 else ""
                        
                        source_table = alias_to_table.get(left_alias, base_table)
                        source_alias = left_alias
                    else:
                        left_col = left_str
                    
                    # Parsear right
                    if '.' in right_str:
                        right_parts = right_str.split('.')
                        right_alias = right_parts[0].strip()
                        right_col = right_parts[1].strip() if len(right_parts) > 1 else ""
                        
                        # Verificar que el alias coincida
                        if right_alias == alias and right_col and left_col:
                            RelationshipLearningService.record_join_usage(
                                empresa=empresa,
                                from_table=source_table,
                                from_column=left_col,
                                to_table=target_table,
                                to_column=right_col,
                                success=success
                            )

    def post(self, request, slug, *args, **kwargs):
        """Actualiza la configuración de un reporte o crea uno nuevo si slug es 'new'."""
        # Si el slug es "new", crear un nuevo reporte
        if slug == "new":
            # Obtener datos del request
            name = request.data.get("name", "Nuevo Reporte")
            new_slug = request.data.get("slug")
            if not new_slug:
                return Response(
                    {"detail": "El campo 'slug' es requerido para crear un nuevo reporte"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Verificar que el slug no exista
            if ReportDefinition.objects.filter(slug=new_slug).exists():
                return Response(
                    {"detail": f"Ya existe un reporte con el slug '{new_slug}'"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Obtener empresa del usuario
            empresa = getattr(request.user, "empresa_activa", None)
            
            # Crear nuevo reporte
            report = ReportDefinition(
                name=name,
                slug=new_slug,
                category=request.data.get("category", "operational"),
                config={
                    "version": "declarative-v1",
                    "metrics": [],
                    "dimensions": [],
                    "datasource": "",
                },
                refresh_interval=request.data.get("refresh_interval", "daily"),
                is_active=True,
                show_in_catalog=request.data.get("show_in_catalog", True),
                is_visible=request.data.get("is_visible", True),
                empresa=empresa,
                created_by=get_user_for_foreignkey(request.user, request),
            )
            report.save()
        else:
            report = get_object_or_404(ReportDefinition, slug=slug, is_active=True)
            # Actualizar nombre si se proporciona
            if "name" in request.data:
                report.name = request.data.get("name")
            # Actualizar slug si se proporciona (para mantener integridad referencial con el nombre)
            if "slug" in request.data:
                new_slug = request.data.get("slug")
                # Verificar que el nuevo slug no esté en uso por otro reporte
                if new_slug != slug and ReportDefinition.objects.filter(slug=new_slug, is_active=True).exclude(id=report.id).exists():
                    return Response(
                        {"detail": f"Ya existe un reporte con el slug '{new_slug}'"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                report.slug = new_slug
        
        config_dict = request.data.get("config")
        if not config_dict:
            return Response(
                {"detail": "Campo 'config' es requerido"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Obtener base_empresa para validación SQL
        base_empresa = None
        if hasattr(request, 'session') and request.session:
            session_user = request.session.get('user', {})
            if session_user and 'base_empresa' in session_user:
                base_empresa = session_user['base_empresa']
        
        # También intentar obtener desde el usuario si está disponible
        if not base_empresa and hasattr(request.user, 'base_empresa'):
            base_empresa = request.user.base_empresa
        
        # Validar configuración
        try:
            is_valid, errors, warnings = validate_report_config(
                config_dict,
                base_empresa=base_empresa,
                validate_sql=True
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error en validación de configuración para {slug}: {e}", exc_info=True)
            return Response(
                {
                    "detail": "Error al validar configuración",
                    "error": str(e),
                    "error_type": type(e).__name__
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        if not is_valid:
            return Response(
                {
                    "detail": "Configuración inválida",
                    "errors": errors,
                    "warnings": warnings
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Normalizar configuración
            normalized_config = normalize_report_config(config_dict)
            
            # Obtener número de versión siguiente
            max_version = ReportDefinitionVersion.objects.filter(
                report=report
            ).aggregate(max_v=models.Max('version_number'))['max_v'] or 0
            next_version = max_version + 1
            
            # Crear versión en historial
            change_summary = request.data.get("change_summary", "")
            # Obtener usuario válido para ForeignKey
            user_for_fk = get_user_for_foreignkey(request.user, request)
            ReportDefinitionVersion.objects.create(
                report=report,
                version_number=next_version,
                created_by=user_for_fk,  # Puede ser None si no se encuentra UsuarioExtendido
                config=normalized_config,
                change_summary=change_summary
            )
            
            # Guardar en ReportDefinition
            report.config = normalized_config
            # Actualizar otros campos si vienen en el request (especialmente para reportes nuevos)
            if "name" in request.data:
                report.name = request.data["name"]
            if "slug" in request.data:
                new_slug = request.data["slug"]
                # Verificar que el nuevo slug no esté en uso por otro reporte
                if new_slug != report.slug and ReportDefinition.objects.filter(slug=new_slug, is_active=True).exclude(id=report.id).exists():
                    return Response(
                        {"detail": f"Ya existe un reporte con el slug '{new_slug}'"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                report.slug = new_slug
            if "description" in request.data:
                report.description = request.data["description"]
            if "category" in request.data:
                report.category = request.data["category"]
            if "refresh_interval" in request.data:
                report.refresh_interval = request.data["refresh_interval"]
            if "show_in_catalog" in request.data:
                report.show_in_catalog = bool(request.data["show_in_catalog"])
            if "is_visible" in request.data:
                report.is_visible = bool(request.data["is_visible"])
            
            # Obtener usuario válido para ForeignKey (reutilizar el ya obtenido arriba)
            report.updated_by = user_for_fk  # Puede ser None si no se encuentra UsuarioExtendido
            report.save(update_fields=["config", "name", "slug", "description", "category", "refresh_interval", "show_in_catalog", "is_visible", "updated_at", "updated_by"])
            
            # Invalidar caché (opcional pero recomendado)
            from .cache import invalidate_report_cache
            invalidate_report_cache(report.slug)
            
            # L1: Aprendizaje por uso - Registrar relaciones de JOINs
            try:
                ReportBuilderConfigAPIView._learn_relationships_from_config(
                    empresa=report.empresa,
                    config=normalized_config,
                    base_table=normalized_config.get("datasource", ""),
                    success=True  # Si llegó aquí, la validación pasó
                )
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"⚠️ Error registrando aprendizaje de relaciones: {e}")
                # No fallar el guardado si el aprendizaje falla
            
            response_data = {
                "status": "success",
                "message": "Configuración guardada exitosamente",
                "config": normalized_config,
                "version_number": next_version,
                "warnings": warnings if warnings else [],
                "slug": report.slug,
            }
            
            # Si es un reporte nuevo, incluir información adicional
            if slug == "new":
                response_data["is_new"] = True
                response_data["redirect_url"] = f"/reports/builder/{report.slug}/"
            # Si el slug cambió, incluir redirect_url para actualizar la URL
            elif slug != report.slug:
                response_data["redirect_url"] = f"/reports/builder/{report.slug}/"
                response_data["slug_changed"] = True
            
            return Response(response_data)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error guardando config para builder {slug}: {e}", exc_info=True)
            return Response(
                {"detail": f"Error al guardar configuración: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def delete(self, request, slug, *args, **kwargs):
        """Elimina un reporte completamente de la base de datos."""
        if slug == "new":
            return Response(
                {"detail": "No se puede eliminar un reporte nuevo que no existe."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            report = get_object_or_404(ReportDefinition, slug=slug, is_active=True)
            
            # Verificar permisos adicionales (opcional: solo el creador puede eliminar)
            # Por ahora, cualquier usuario con BuilderReportsPermission puede eliminar
            
            # Obtener información antes de eliminar para el log
            report_name = report.name
            report_slug = report.slug
            
            # Eliminar reporte (CASCADE eliminará widgets, versiones, logs automáticamente)
            report.delete()
            
            # Invalidar caché
            from .cache import invalidate_report_cache
            invalidate_report_cache(report_slug)
            
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"✅ Reporte eliminado: {report_name} ({report_slug})")
            
            return Response({
                "status": "success",
                "message": f"Reporte '{report_name}' eliminado exitosamente",
                "slug": report_slug
            })
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error eliminando reporte {slug}: {e}", exc_info=True)
            return Response(
                {"detail": f"Error al eliminar reporte: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ReportBuilderPreviewAPIView(APIView):
    """API para preview de reportes con configuración temporal."""

    permission_classes = [BuilderReportsPermission]

    def post(self, request, slug, *args, **kwargs):
        """Ejecuta un preview del reporte con configuración temporal."""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # Manejar reportes nuevos (slug="new" o "nuevo_reporte")
            if slug == "new" or slug == "nuevo_reporte":
                # Para reportes nuevos, crear un objeto temporal sin guardar
                # Obtener empresa del usuario si está disponible
                empresa = None
                try:
                    # empresa_activa es una instancia de Empresa
                    if hasattr(request.user, 'empresa_activa') and request.user.empresa_activa:
                        empresa = request.user.empresa_activa
                    # Si no hay empresa_activa, intentar obtener desde base_empresa (string)
                    # Necesitamos buscar la instancia de Empresa correspondiente
                    elif hasattr(request.user, 'base_empresa') and request.user.base_empresa:
                        from core.models import Empresa
                        # base_empresa es un string (nombre de BD), necesitamos buscar la Empresa
                        # Por ahora, simplemente no asignamos empresa si no hay empresa_activa
                        # ya que no tenemos una forma directa de mapear base_empresa a Empresa
                        empresa = None
                except Exception as e:
                    logger.warning(f"No se pudo obtener empresa del usuario: {e}")
                
                report = ReportDefinition(
                    slug=slug,
                    name="Nuevo Reporte",
                    category="operational",
                    is_active=True,
                    config={},
                    empresa=empresa
                )
            else:
                try:
                    report = get_object_or_404(ReportDefinition, slug=slug, is_active=True)
                except Exception as e:
                    logger.error(f"Error obteniendo reporte {slug}: {e}", exc_info=True)
                    return Response(
                        {
                            "detail": f"Reporte no encontrado: {slug}",
                            "error": str(e),
                            "error_type": type(e).__name__
                        },
                        status=status.HTTP_404_NOT_FOUND
                    )
            
            config_dict = request.data.get("config")
            payload = request.data.get("payload", {})
            
            if not config_dict:
                return Response(
                    {"detail": "Campo 'config' es requerido"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Logging para debug: ver qué expresiones llegan desde el frontend
            if config_dict.get("metrics"):
                for metric_name, metric_data in config_dict.get("metrics", {}).items():
                    if isinstance(metric_data, dict):
                        expr = metric_data.get("expression", "")
                        logger.debug(f"🔍 Preview - Métrica {metric_name}: expresión recibida desde frontend = '{expr}'")
                    else:
                        logger.debug(f"🔍 Preview - Métrica {metric_name}: expresión recibida desde frontend = '{str(metric_data)}'")
            
            # Obtener base_empresa para validación SQL
            base_empresa = None
            try:
                if hasattr(request, 'session') and request.session:
                    session_user = request.session.get('user', {})
                    if session_user and 'base_empresa' in session_user:
                        base_empresa = session_user['base_empresa']
                
                # También intentar obtener desde el usuario si está disponible
                if not base_empresa and hasattr(request.user, 'base_empresa'):
                    base_empresa = request.user.base_empresa
            except Exception as e:
                logger.warning(f"No se pudo obtener base_empresa: {e}")
            
            # Validar configuración
            try:
                is_valid, errors, warnings = validate_report_config(
                    config_dict,
                    base_empresa=base_empresa,
                    validate_sql=True
                )
                # Logging detallado de errores de validación
                if not is_valid:
                    logger.error(f"❌ Validación falló para preview {slug}: {len(errors)} errores, {len(warnings)} warnings")
                    for error in errors:
                        logger.error(f"  - Error: {error}")
                    for warning in warnings:
                        logger.warning(f"  - Warning: {warning}")
            except Exception as e:
                logger.error(f"Error en validación de configuración para preview {slug}: {e}", exc_info=True)
                return Response(
                    {
                        "detail": "Error al validar configuración",
                        "error": str(e),
                        "error_type": type(e).__name__
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            if not is_valid:
                logger.error(f"❌ Preview {slug}: Configuración inválida. Errores: {errors}")
                return Response(
                    {
                        "detail": "Configuración inválida",
                        "errors": errors,
                        "warnings": warnings
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                # Normalizar configuración
                normalized_config = normalize_report_config(config_dict)
                
                # Logging después de normalización
                if normalized_config.get("metrics"):
                    for metric_name, metric_data in normalized_config.get("metrics", {}).items():
                        if isinstance(metric_data, dict):
                            expr = metric_data.get("expression", "")
                            logger.debug(f"🔍 Preview - Métrica {metric_name}: expresión después de normalizar = '{expr}'")
                
                # Ejecutar preview usando el motor
                pool = get_mysql_pool()
                engine = ReportExecutionEngine(connection_pool=pool)
                
                # Parsear a ReportConfig usando el método interno del engine
                # Esto convierte correctamente los diccionarios a MetricDefinition y DimensionDefinition
                report_config = engine._parse_config(normalized_config)
                
                # IMPORTANTE: Agregar métricas y dimensiones personalizadas de widgets
                # Esto es necesario para que las métricas personalizadas se ejecuten en la consulta SQL del preview
                from reports.services.execution_engine import MetricDefinition, DimensionDefinition
                manual_widgets = list(report.widgets.all().order_by("order", "id"))
                for widget in manual_widgets:
                    widget_config = widget.configuration or {}
                    if widget_config.get('use_custom_fields', False):
                        # Agregar métricas personalizadas
                        custom_metrics = widget_config.get('custom_metrics', [])
                        if custom_metrics and isinstance(custom_metrics, list):
                            for metric in custom_metrics:
                                metric_name = metric.get('name')
                                metric_expression = metric.get('expression')
                                if metric_name and metric_expression:
                                    # Agregar métrica personalizada al config
                                    report_config.metrics[metric_name] = MetricDefinition(
                                        name=metric_name,
                                        expression=metric_expression,
                                        depends_on=[]
                                    )
                                    # Guardar información de formato personalizada en las opciones del report_config
                                    if 'custom_metrics_format' not in report_config.options:
                                        report_config.options['custom_metrics_format'] = {}
                                    report_config.options['custom_metrics_format'][metric_name] = {
                                        'format_type': metric.get('format_type', 'number'),
                                        'decimals': metric.get('decimals', 2)
                                    }
                                    logger.debug(f"Preview API: Agregando métrica personalizada '{metric_name}' con expresión '{metric_expression}' y formato '{metric.get('format_type', 'number')}' del widget '{widget.name}'")
                        
                        # Agregar dimensiones personalizadas
                        custom_dimensions = widget_config.get('custom_dimensions', [])
                        if custom_dimensions and isinstance(custom_dimensions, list):
                            for dimension in custom_dimensions:
                                dim_name = dimension.get('name')
                                dim_expression = dimension.get('expression')
                                if dim_name and dim_expression:
                                    # Agregar dimensión personalizada al config
                                    report_config.dimensions[dim_name] = DimensionDefinition(
                                        name=dim_name,
                                        expression=dim_expression
                                    )
                                    logger.debug(f"Preview API: Agregando dimensión personalizada '{dim_name}' con expresión '{dim_expression}' del widget '{widget.name}'")
                
                if manual_widgets:
                    custom_metrics_count = sum(1 for w in manual_widgets if w.configuration and w.configuration.get('use_custom_fields') and w.configuration.get('custom_metrics'))
                    if custom_metrics_count > 0:
                        logger.info(f"Preview API: Agregadas métricas personalizadas de {custom_metrics_count} widget(s) al config")
                
                # Logging después de parsear
                if report_config.metrics:
                    for metric_name, metric_def in report_config.metrics.items():
                        logger.debug(f"🔍 Preview - Métrica {metric_name}: expresión después de parsear = '{metric_def.expression}'")
                
                # Agregar base_empresa al payload si está disponible
                if hasattr(request, 'session') and request.session:
                    session_user = request.session.get('user', {})
                    if session_user and 'base_empresa' in session_user:
                        if 'filters' not in payload:
                            payload['filters'] = {}
                        payload['filters']['base_empresa'] = session_user['base_empresa']
                
                # Ejecutar con bypass_cache=True para preview
                query_result = engine.run_from_config(
                    report=report,
                    config=report_config,
                    payload=payload,
                    user=request.user,
                    bypass_cache=True
                )
                
                # Generar schema desde el config temporal
                schema_service = ReportSchemaService()
                schema = schema_service.build_schema_from_config(report, normalized_config)
                
                # Serializar resultados
                from .serializers import ReportQueryResponseSerializer, ReportSchemaSerializer
                
                # Convertir schema a dict para serialización
                schema_dict = {
                    "slug": schema.slug,
                    "name": schema.name,
                    "category": schema.category,
                    "is_declarative": schema.is_declarative,
                    "metrics": [
                        {
                            "name": m.name,
                            "label": m.label,
                            "expression": m.expression,
                            "data_type": m.data_type,
                            "role": m.role,
                            "format": m.format,
                            "show_in_kpi": getattr(m, "show_in_kpi", True),
                        }
                        for m in schema.metrics
                    ],
                    "dimensions": [
                        {
                            "name": d.name,
                            "label": d.label,
                            "expression": d.expression,
                            "data_type": d.data_type,
                            "role": d.role,
                            "format": d.format,
                        }
                        for d in schema.dimensions
                    ],
                    "default_widgets": [
                        {
                            "id": w.id,
                            "kind": w.kind,
                            "title": w.title,
                            "description": w.description,
                            "x_dimension": w.x_dimension,
                            "y_metrics": w.y_metrics,
                            "series_dimension": w.series_dimension,
                            "options": w.options,
                        }
                        for w in schema.default_widgets
                    ],
                    "options": schema.options,
                }
                
                query_serializer = ReportQueryResponseSerializer(query_result.__dict__)
                schema_serializer = ReportSchemaSerializer(schema_dict)
                
                # L1: Aprendizaje por uso - Registrar relaciones exitosas
                try:
                    base_table = normalized_config.get("datasource", "")
                    ReportBuilderConfigAPIView._learn_relationships_from_config(
                        empresa=report.empresa,
                        config=normalized_config,
                        base_table=base_table,
                        success=True
                    )
                except Exception as learn_error:
                    logger.warning(f"⚠️ Error registrando aprendizaje en preview exitoso: {learn_error}")
                
                return Response({
                    "query_result": query_serializer.data,
                    "schema": schema_serializer.data,
                    "warnings": warnings if warnings else []
                })
                
            except Exception as e:
                logger.error(f"Error ejecutando preview para {slug}: {e}", exc_info=True)
                
                # L1: Aprendizaje por uso - Registrar fallo si es relacionado a JOINs
                try:
                    error_message = str(e).lower()
                    # Detectar si el error es relacionado a JOINs/columnas
                    is_join_related = (
                        "unknown column" in error_message or
                        "column" in error_message and ("on" in error_message or "join" in error_message) or
                        "table" in error_message and "doesn't exist" in error_message
                    )
                    
                    if is_join_related:
                        base_table = normalized_config.get("datasource", "")
                        ReportBuilderConfigAPIView._learn_relationships_from_config(
                            empresa=report.empresa,
                            config=normalized_config,
                            base_table=base_table,
                            success=False
                        )
                except Exception as learn_error:
                    logger.warning(f"⚠️ Error registrando aprendizaje en preview fallido: {learn_error}")
                
                # Sanitizar mensaje de error (no exponer SQL ni credenciales)
                error_message = str(e)
                if "SQL" in error_message or "password" in error_message.lower():
                    error_message = "Error al ejecutar la consulta. Verifique la configuración del reporte."
                
                return Response(
                    {
                        "detail": "Error al ejecutar preview",
                        "error": error_message,
                        "error_type": type(e).__name__
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        except Exception as e:
            # Capturar cualquier error no manejado anteriormente
            logger.error(f"Error inesperado en preview para {slug}: {e}", exc_info=True)
            
            # Sanitizar mensaje de error
            error_message = str(e)
            if "SQL" in error_message or "password" in error_message.lower():
                error_message = "Error al procesar la solicitud. Verifique la configuración."
            
            return Response(
                {
                    "detail": "Error inesperado al ejecutar preview",
                    "error": error_message,
                    "error_type": type(e).__name__
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ReportBuilderWidgetsAPIView(APIView):
    """API para gestionar widgets de reportes en el Builder."""

    permission_classes = [BuilderReportsPermission]

    def get(self, request, slug, *args, **kwargs):
        """Obtiene los widgets de un reporte."""
        # Si el slug es "new", retornar widgets vacíos
        if slug == "new":
            return Response({
                "widgets": [],
                "total": 0
            })
        
        report = get_object_or_404(ReportDefinition, slug=slug, is_active=True)
        
        widgets = report.widgets.all().order_by("order", "id")
        widgets_data = [
            {
                "id": w.id,
                "name": w.name,
                "widget_type": w.widget_type,
                "order": w.order,
                "layout": w.layout,
                "configuration": w.configuration,
            }
            for w in widgets
        ]
        
        return Response({"widgets": widgets_data})

    def post(self, request, slug, *args, **kwargs):
        """Crea o actualiza widgets de un reporte."""
        report = get_object_or_404(ReportDefinition, slug=slug, is_active=True)
        
        widgets_data = request.data.get("widgets", [])
        if not isinstance(widgets_data, list):
            return Response(
                {"detail": "Campo 'widgets' debe ser una lista"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            created_count = 0
            updated_count = 0
            deleted_count = 0
            
            # Obtener IDs de widgets que se están enviando (para eliminar los que no están en la lista)
            sent_widget_ids = set()
            for widget_data in widgets_data:
                widget_id = widget_data.get("id")
                if widget_id:
                    sent_widget_ids.add(widget_id)
            
            # Eliminar widgets que no están en la lista enviada (solo si se envía una lista no vacía)
            # Si se envía una lista vacía, significa que el usuario quiere eliminar todos los widgets
            if widgets_data or len(sent_widget_ids) == 0:
                existing_widget_ids = set(report.widgets.values_list('id', flat=True))
                widgets_to_delete = existing_widget_ids - sent_widget_ids
                for widget_id in widgets_to_delete:
                    try:
                        widget = report.widgets.get(id=widget_id)
                        widget.delete()
                        deleted_count += 1
                    except ReportWidget.DoesNotExist:
                        pass
            
            for widget_data in widgets_data:
                widget_id = widget_data.get("id")
                delete_flag = widget_data.get("delete", False)
                
                if delete_flag and widget_id:
                    # Eliminar widget
                    try:
                        widget = report.widgets.get(id=widget_id)
                        widget.delete()
                        deleted_count += 1
                    except ReportWidget.DoesNotExist:
                        pass
                elif widget_id:
                    # Actualizar widget existente
                    try:
                        widget = report.widgets.get(id=widget_id)
                        widget.name = widget_data.get("name", widget.name)
                        widget.widget_type = widget_data.get("widget_type", widget.widget_type)
                        widget.order = widget_data.get("order", widget.order)
                        widget.layout = widget_data.get("layout", widget.layout)
                        widget.configuration = widget_data.get("configuration", widget.configuration)
                        widget.save()
                        updated_count += 1
                    except ReportWidget.DoesNotExist:
                        # Si no existe, crear nuevo
                        ReportWidget.objects.create(
                            report=report,
                            name=widget_data.get("name", "Widget"),
                            widget_type=widget_data.get("widget_type", "table"),
                            order=widget_data.get("order", 0),
                            layout=widget_data.get("layout", {}),
                            configuration=widget_data.get("configuration", {})
                        )
                        created_count += 1
                else:
                    # Crear nuevo widget
                    ReportWidget.objects.create(
                        report=report,
                        name=widget_data.get("name", "Widget"),
                        widget_type=widget_data.get("widget_type", "table"),
                        order=widget_data.get("order", 0),
                        layout=widget_data.get("layout", {}),
                        configuration=widget_data.get("configuration", {})
                    )
                    created_count += 1
            
            return Response({
                "status": "success",
                "message": f"Widgets procesados: {created_count} creados, {updated_count} actualizados, {deleted_count} eliminados",
                "created": created_count,
                "updated": updated_count,
                "deleted": deleted_count
            })
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error gestionando widgets para {slug}: {e}", exc_info=True)
            return Response(
                {"detail": f"Error al gestionar widgets: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# Endpoints adicionales del Builder - agregar al final de api_views.py

class ReportBuilderHistoryAPIView(APIView):
    """API para obtener historial de versiones de un reporte."""

    permission_classes = [BuilderReportsPermission]

    def get(self, request, slug, *args, **kwargs):
        """Obtiene el historial de versiones de un reporte."""
        report = get_object_or_404(ReportDefinition, slug=slug, is_active=True)
        
        versions = report.versions.all().order_by("-version_number")
        versions_data = [
            {
                "version_number": v.version_number,
                "created_at": v.created_at.isoformat(),
                "created_by": v.created_by.username if v.created_by else None,
                "created_by_id": v.created_by.id if v.created_by else None,
                "change_summary": v.change_summary,
            }
            for v in versions
        ]
        
        return Response({
            "slug": report.slug,
            "name": report.name,
            "versions": versions_data,
            "total_versions": len(versions_data)
        })


class ReportBuilderRollbackAPIView(APIView):
    """API para hacer rollback a una versión anterior de un reporte."""

    permission_classes = [BuilderReportsPermission]

    def post(self, request, slug, *args, **kwargs):
        """Hace rollback a una versión específica."""
        report = get_object_or_404(ReportDefinition, slug=slug, is_active=True)
        
        version_number = request.data.get("version_number")
        if not version_number or not isinstance(version_number, int):
            return Response(
                {"detail": "Campo 'version_number' (int) es requerido"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Buscar versión
            version = report.versions.get(version_number=version_number)
            
            # Obtener número de versión siguiente
            max_version = report.versions.aggregate(max_v=models.Max('version_number'))['max_v'] or 0
            next_version = max_version + 1
            
            # Obtener comentario de rollback
            change_summary = request.data.get("change_summary", "")
            if not change_summary:
                change_summary = f"Rollback to version {version_number}"
            
            # Crear nueva versión con la configuración del rollback
            rollback_config = version.config.copy()
            # Obtener usuario válido para ForeignKey
            user_for_fk = get_user_for_foreignkey(request.user, request)
            ReportDefinitionVersion.objects.create(
                report=report,
                version_number=next_version,
                created_by=user_for_fk,  # Puede ser None si no se encuentra UsuarioExtendido
                config=rollback_config,
                change_summary=change_summary
            )
            
            # Restaurar configuración en ReportDefinition
            report.config = rollback_config
            # updated_by también necesita ser UsuarioExtendido, pero como es opcional, podemos usar None
            # o intentar obtener el usuario extendido
            report.updated_by = user_for_fk
            report.save(update_fields=["config", "updated_at", "updated_by"])
            
            # Invalidar caché
            from .cache import invalidate_report_cache
            invalidate_report_cache(report.slug)
            
            return Response({
                "status": "success",
                "message": f"Rollback realizado a versión {version_number}",
                "config": rollback_config,
                "version_number": next_version,
                "rolled_back_from": version_number
            })
            
        except ReportDefinitionVersion.DoesNotExist:
            return Response(
                {"detail": f"Versión {version_number} no encontrada para este reporte"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error haciendo rollback para {slug}: {e}", exc_info=True)
            return Response(
                {"detail": f"Error al hacer rollback: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ============================================================================
# FASE BV-1: Semantic Datasources API
# ============================================================================

class BuilderDatasourcesAPIView(APIView):
    """API para listar fuentes de datos disponibles para el Builder Visual."""

    permission_classes = [BuilderReportsPermission]

    def get(self, request, *args, **kwargs):
        """
        Lista todas las tablas disponibles como fuentes de datos.
        
        Query params:
            base_empresa: Base de datos MySQL (opcional)
        """
        # Obtener base_empresa del query param o de la sesión
        base_empresa = request.query_params.get("base_empresa")
        if not base_empresa:
            if hasattr(request, 'session') and request.session:
                session_user = request.session.get('user', {})
                if session_user and 'base_empresa' in session_user:
                    base_empresa = session_user['base_empresa']
        
        # También intentar obtener desde el usuario si está disponible
        if not base_empresa and hasattr(request.user, 'base_empresa'):
            base_empresa = request.user.base_empresa
        
        try:
            datasources = SemanticService.list_datasources(base_empresa=base_empresa)
            
            # Serializar a formato JSON
            datasources_data = [
                {
                    "name": ds.name,
                    "description": ds.description,
                    "estimated_rows": ds.estimated_rows,
                    "fields_count": len(ds.fields) if ds.fields else None,
                    "relationships_count": len(ds.relationships) if ds.relationships else None,
                }
                for ds in datasources
            ]
            
            return Response({
                "datasources": datasources_data,
                "total": len(datasources_data),
                "base_empresa": base_empresa or "default"
            })
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error obteniendo datasources: {e}", exc_info=True)
            return Response(
                {"detail": f"Error al obtener fuentes de datos: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class BuilderDatasourceFieldsAPIView(APIView):
    """API para obtener campos de una fuente de datos específica."""

    permission_classes = [BuilderReportsPermission]

    def get(self, request, name, *args, **kwargs):
        """
        Obtiene los campos de una tabla con metadata completa.
        
        Query params:
            base_empresa: Base de datos MySQL (opcional)
        """
        # Obtener base_empresa del query param o de la sesión
        base_empresa = request.query_params.get("base_empresa")
        if not base_empresa:
            if hasattr(request, 'session') and request.session:
                session_user = request.session.get('user', {})
                if session_user and 'base_empresa' in session_user:
                    base_empresa = session_user['base_empresa']
        
        # También intentar obtener desde el usuario si está disponible
        if not base_empresa and hasattr(request.user, 'base_empresa'):
            base_empresa = request.user.base_empresa
        
        try:
            fields = SemanticService.get_fields(datasource_name=name, base_empresa=base_empresa)
            
            # Serializar a formato JSON
            fields_data = [
                {
                    "name": f.name,
                    "data_type": f.data_type,
                    "is_nullable": f.is_nullable,
                    "is_primary_key": f.is_primary_key,
                    "is_foreign_key": f.is_foreign_key,
                    "referenced_table": f.referenced_table,
                    "referenced_field": f.referenced_field,
                    "description": f.description,
                    "valid_aggregations": f.valid_aggregations,
                }
                for f in fields
            ]
            
            return Response({
                "datasource": name,
                "fields": fields_data,
                "total": len(fields_data),
                "base_empresa": base_empresa or "default"
            })
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error obteniendo campos de {name}: {e}", exc_info=True)
            return Response(
                {"detail": f"Error al obtener campos: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class BuilderDatasourceRelationshipsAPIView(APIView):
    """API para obtener relaciones (JOINs posibles) de una fuente de datos."""

    permission_classes = [BuilderReportsPermission]

    def get(self, request, name, *args, **kwargs):
        """
        Obtiene las relaciones (JOINs posibles) de una tabla.
        
        Query params:
            base_empresa: Base de datos MySQL (opcional)
        """
        # Obtener base_empresa del query param o de la sesión
        base_empresa = request.query_params.get("base_empresa")
        if not base_empresa:
            if hasattr(request, 'session') and request.session:
                session_user = request.session.get('user', {})
                if session_user and 'base_empresa' in session_user:
                    base_empresa = session_user['base_empresa']
        
        # También intentar obtener desde el usuario si está disponible
        if not base_empresa and hasattr(request.user, 'base_empresa'):
            base_empresa = request.user.base_empresa
        
        try:
            # Obtener empresa del usuario si está disponible
            empresa = getattr(request.user, "empresa_activa", None)
            relationships = SemanticService.get_relationships(
                datasource_name=name,
                base_empresa=base_empresa,
                empresa=empresa
            )
            
            # Serializar a formato JSON
            relationships_data = [
                {
                    "from_table": rel.from_table,
                    "from_field": rel.from_field,
                    "to_table": rel.to_table,
                    "to_field": rel.to_field,
                    "relationship_type": rel.relationship_type,
                    "description": rel.description,
                    "confidence": rel.confidence,
                    "source": rel.source,
                    "badge": getattr(rel, 'badge', 'Sugerido'),  # Badge del merge (Recomendado/Detectado/Sugerido)
                    "label": rel.label,
                    "cardinality": rel.cardinality,
                }
                for rel in relationships
            ]
            
            return Response({
                "datasource": name,
                "relationships": relationships_data,
                "total": len(relationships_data),
                "base_empresa": base_empresa or "default"
            })
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error obteniendo relaciones de {name}: {e}", exc_info=True)
            return Response(
                {"detail": f"Error al obtener relaciones: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class BuilderJoinsSuggestAPIView(APIView):
    """API para sugerir JOINs basándose en tabla base y tablas seleccionadas."""

    permission_classes = [BuilderReportsPermission]

    def get(self, request, *args, **kwargs):
        """
        Sugiere JOINs basándose en la tabla base y tablas de campos seleccionados.
        
        Query params:
            base: Tabla principal del reporte (requerido)
            tables: Lista de nombres de tablas separadas por coma (opcional)
            base_empresa: Base de datos MySQL (opcional)
        """
        base_table = request.query_params.get("base")
        if not base_table:
            return Response(
                {"detail": "Parámetro 'base' es requerido"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        tables_param = request.query_params.get("tables", "")
        selected_tables = [t.strip() for t in tables_param.split(",") if t.strip()] if tables_param else []
        
        # Obtener base_empresa del query param o de la sesión
        base_empresa = request.query_params.get("base_empresa")
        if not base_empresa:
            if hasattr(request, 'session') and request.session:
                session_user = request.session.get('user', {})
                if session_user and 'base_empresa' in session_user:
                    base_empresa = session_user['base_empresa']
        
        # También intentar obtener desde el usuario si está disponible
        if not base_empresa and hasattr(request.user, 'base_empresa'):
            base_empresa = request.user.base_empresa
        
        try:
            suggestions = SemanticService.suggest_joins(
                base_table=base_table,
                selected_fields_tables=selected_tables,
                base_empresa=base_empresa
            )
            
            # Serializar relaciones (incluir badge y status si están disponibles)
            suggestions_data = []
            for rel in suggestions:
                rel_data = {
                    "from_table": rel.from_table,
                    "from_field": rel.from_field,
                    "to_table": rel.to_table,
                    "to_field": rel.to_field,
                    "relationship_type": rel.relationship_type,
                    "description": rel.description,
                    "confidence": rel.confidence,
                }
                # Agregar badge si está disponible (atributo dinámico)
                if hasattr(rel, 'badge'):
                    rel_data['badge'] = rel.badge
                # Agregar status si está disponible
                if hasattr(rel, 'status'):
                    rel_data['status'] = rel.status
                suggestions_data.append(rel_data)
            
            return Response({
                "base_table": base_table,
                "selected_tables": selected_tables,
                "suggestions": suggestions_data,
                "total": len(suggestions_data),
                "base_empresa": base_empresa or "default"
            })
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error sugiriendo JOINs: {e}", exc_info=True)
            return Response(
                {"detail": f"Error al sugerir JOINs: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class BuilderJoinsCandidatesAPIView(APIView):
    """API para obtener candidatas de JOIN basándose en el grafo actual de tablas."""

    permission_classes = [BuilderReportsPermission]

    def post(self, request, *args, **kwargs):
        """
        Obtiene candidatas de JOIN para cada tabla en el grafo actual.
        
        Body:
            base: Tabla principal (requerido)
            current_joins: Lista de JOINs actuales, cada uno con 'table' y 'alias' (opcional)
            base_empresa: Base de datos MySQL (opcional)
            
        Ejemplo:
            {
                "base": "cuentacliente",
                "current_joins": [
                    {"table": "sucursales", "alias": "s"}
                ]
            }
        """
        base_table = request.data.get("base") or request.data.get("base_table")
        if not base_table:
            return Response(
                {"detail": "El campo 'base' es requerido"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        current_joins = request.data.get("current_joins") or request.data.get("joins", [])
        
        # Obtener base_empresa
        base_empresa = request.data.get("base_empresa")
        if not base_empresa:
            if hasattr(request, 'session') and request.session:
                session_user = request.session.get('user', {})
                if session_user and 'base_empresa' in session_user:
                    base_empresa = session_user['base_empresa']
        
        if not base_empresa and hasattr(request.user, 'base_empresa'):
            base_empresa = request.user.base_empresa
        
        try:
            # Normalizar joins: extraer tabla y alias
            normalized_joins = []
            for join in current_joins:
                if isinstance(join, dict):
                    table = join.get("table", "")
                    alias = join.get("alias", "")
                    
                    # Si la tabla tiene alias en el formato "tabla alias", extraerlo
                    if not alias and " " in table:
                        parts = table.split()
                        table = parts[0]
                        alias = parts[-1] if len(parts) > 1 else SemanticService._get_default_alias(table)
                    elif not alias:
                        alias = SemanticService._get_default_alias(table)
                    
                    if table:
                        normalized_joins.append({"table": table, "alias": alias})
            
            # Obtener candidatas usando el nuevo método
            candidates_data = SemanticService.get_join_candidates_for_graph(
                base_table=base_table,
                current_joins=normalized_joins,
                base_empresa=base_empresa
            )
            
            # Serializar respuesta
            result = []
            for item in candidates_data:
                result.append({
                    "source_table": item["source_table"],
                    "source_alias": item["source_alias"],
                    "candidates": [
                        {
                            "from_table": c["from_table"],
                            "from_column": c["from_field"],
                            "to_table": c["to_table"],
                            "to_column": c["to_field"],
                            "label": c.get("label", c["to_table"]),
                            "description": c.get("description", ""),
                            "confidence": c.get("confidence", 1.0),
                            "source": c.get("source", "foreign_key"),
                            "badge": c.get("badge", "Sugerido"),  # Recomendado | Detectado | Sugerido
                            "cardinality": c.get("cardinality", "N:1")
                        }
                        for c in item["candidates"]
                    ]
                })
            
            return Response({
                "candidates_by_source": result,
                "total_candidates": sum(len(r["candidates"]) for r in result)
            })
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error obteniendo candidatas de JOIN: {e}", exc_info=True)
            return Response(
                {"detail": f"Error al obtener candidatas: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class BuilderRelationshipBlockAPIView(APIView):
    """API para bloquear relaciones aprendidas (admin-only)."""
    
    permission_classes = [BuilderReportsPermission]
    
    def post(self, request, *args, **kwargs):
        """
        Bloquea una relación aprendida.
        
        Body:
            empresa_id: ID de empresa (opcional, None para global)
            from_table: Tabla origen
            from_column: Columna origen
            to_table: Tabla destino
            to_column: Columna destino
        """
        from .services.relationship_learning import RelationshipLearningService
        
        empresa_id = request.data.get("empresa_id")
        empresa = None
        if empresa_id:
            from core.models import Empresa
            try:
                empresa = Empresa.objects.get(id=empresa_id)
            except Empresa.DoesNotExist:
                return Response(
                    {"detail": f"Empresa con ID {empresa_id} no encontrada"},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        from_table = request.data.get("from_table")
        from_column = request.data.get("from_column")
        to_table = request.data.get("to_table")
        to_column = request.data.get("to_column")
        
        if not all([from_table, from_column, to_table, to_column]):
            return Response(
                {"detail": "Todos los campos son requeridos: from_table, from_column, to_table, to_column"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        success = RelationshipLearningService.block_relationship(
            empresa=empresa,
            from_table=from_table,
            from_column=from_column,
            to_table=to_table,
            to_column=to_column
        )
        
        if success:
            return Response({
                "status": "success",
                "message": "Relación bloqueada exitosamente"
            })
        else:
            return Response(
                {"detail": "No se pudo bloquear la relación. Verifique que exista."},
                status=status.HTTP_404_NOT_FOUND
            )


class BuilderTemplatesAPIView(APIView):
    """API para gestionar plantillas de reportes."""

    permission_classes = [BuilderReportsPermission]

    def get(self, request, *args, **kwargs):
        """
        Lista todas las plantillas disponibles.
        
        Query params:
            category: Filtrar por categoría (operational, managerial)
            system_only: Si es True, solo retorna plantillas del sistema
        """
        try:
            category = request.query_params.get("category")
            system_only = request.query_params.get("system_only", "false").lower() == "true"
            
            queryset = ReportTemplate.objects.all()
            
            if system_only:
                queryset = queryset.filter(is_system=True)
            
            if category:
                queryset = queryset.filter(category=category)
            
            queryset = queryset.order_by("is_system", "-created_at", "name")
            
            templates_data = []
            for template in queryset:
                # Manejar created_by de forma segura
                created_by_name = None
                if template.created_by:
                    try:
                        # Intentar obtener username o nombre del usuario
                        if hasattr(template.created_by, 'username'):
                            created_by_name = template.created_by.username
                        elif hasattr(template.created_by, 'get_full_name'):
                            created_by_name = template.created_by.get_full_name()
                        elif hasattr(template.created_by, 'name'):
                            created_by_name = template.created_by.name
                    except Exception:
                        pass
                
                # Manejar created_at de forma segura
                created_at_str = None
                if template.created_at:
                    try:
                        created_at_str = template.created_at.isoformat()
                    except Exception:
                        pass
                
                templates_data.append({
                    "id": template.id,
                    "name": template.name or "",
                    "description": template.description or "",
                    "category": template.category or "operational",
                    "is_system": bool(template.is_system),
                    "created_at": created_at_str,
                    "created_by": created_by_name,
                })
            
            return Response({
                "templates": templates_data,
                "total": len(templates_data)
            })
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error obteniendo plantillas: {e}", exc_info=True)
            return Response(
                {"detail": f"Error al obtener plantillas: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def post(self, request, *args, **kwargs):
        """
        Crea una nueva plantilla desde un reporte actual o desde cero.
        
        Body:
            name: Nombre de la plantilla (requerido)
            description: Descripción (opcional)
            category: Categoría (opcional, default: operational)
            config: Configuración del reporte (requerido)
            widgets: Lista de widgets (opcional)
            from_report_slug: Si se proporciona, copia config y widgets de ese reporte
        """
        name = request.data.get("name")
        if not name:
            return Response(
                {"detail": "El campo 'name' es requerido"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Si viene from_report_slug, obtener config y widgets de ese reporte
        from_report_slug = request.data.get("from_report_slug")
        if from_report_slug:
            try:
                report = ReportDefinition.objects.get(slug=from_report_slug, is_active=True)
                config = report.config or {}
                widgets = [{
                    "name": w.name,
                    "widget_type": w.widget_type,
                    "order": w.order,
                    "layout": w.layout,
                    "configuration": w.configuration
                } for w in report.widgets.all()]
            except ReportDefinition.DoesNotExist:
                return Response(
                    {"detail": f"Reporte '{from_report_slug}' no encontrado"},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            config = request.data.get("config", {})
            widgets = request.data.get("widgets", [])
        
        # Validar que config tenga version declarative-v1
        if config.get("version") != "declarative-v1":
            return Response(
                {"detail": "La configuración debe ser declarative-v1"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        template = ReportTemplate(
            name=name,
            description=request.data.get("description", ""),
            category=request.data.get("category", "operational"),
            config=config,
            widgets=widgets,
            is_system=False,
            created_by=get_user_for_foreignkey(request.user, request),
        )
        template.save()
        
        return Response({
            "id": template.id,
            "name": template.name,
            "message": "Plantilla creada exitosamente"
        }, status=status.HTTP_201_CREATED)


class BuilderTemplateApplyAPIView(APIView):
    """API para aplicar una plantilla y crear un nuevo reporte."""

    permission_classes = [BuilderReportsPermission]

    def post(self, request, template_id, *args, **kwargs):
        """
        Crea un nuevo reporte desde una plantilla.
        
        Body:
            name: Nombre del nuevo reporte (requerido)
            slug: Slug del nuevo reporte (requerido)
            category: Categoría (opcional, usa la de la plantilla si no se proporciona)
        """
        try:
            template = ReportTemplate.objects.get(id=template_id)
        except ReportTemplate.DoesNotExist:
            return Response(
                {"detail": "Plantilla no encontrada"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        name = request.data.get("name")
        slug = request.data.get("slug")
        
        if not name or not slug:
            return Response(
                {"detail": "Los campos 'name' y 'slug' son requeridos"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verificar que el slug no exista
        if ReportDefinition.objects.filter(slug=slug).exists():
            return Response(
                {"detail": f"Ya existe un reporte con el slug '{slug}'"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Obtener empresa del usuario
        empresa = getattr(request.user, "empresa_activa", None)
        
        # Crear nuevo reporte desde la plantilla
        report = ReportDefinition(
            name=name,
            slug=slug,
            category=request.data.get("category", template.category),
            description=request.data.get("description", template.description),
            config=template.config.copy(),
            refresh_interval=request.data.get("refresh_interval", "daily"),
            is_active=True,
            show_in_catalog=request.data.get("show_in_catalog", True),
            is_visible=request.data.get("is_visible", True),
            empresa=empresa,
            created_by=get_user_for_foreignkey(request.user, request),
        )
        report.save()
        
        # Crear widgets desde la plantilla
        for widget_data in template.widgets:
            ReportWidget.objects.create(
                report=report,
                name=widget_data.get("name", f"Widget {len(report.widgets.all()) + 1}"),
                widget_type=widget_data.get("widget_type", "table"),
                order=widget_data.get("order", len(report.widgets.all())),
                layout=widget_data.get("layout", {}),
                configuration=widget_data.get("configuration", {})
            )
        
        return Response({
            "id": report.id,
            "slug": report.slug,
            "name": report.name,
            "redirect_url": f"/reports/builder/{report.slug}/",
            "message": "Reporte creado desde plantilla exitosamente"
        }, status=status.HTTP_201_CREATED)


class LearnedRelationshipsAPIView(APIView):
    """API para obtener todas las relaciones aprendidas (solo lectura, para exportación frontend)."""
    
    permission_classes = [BuilderReportsPermission]
    
    def get(self, request, *args, **kwargs):
        """Obtiene todas las relaciones aprendidas en formato JSON."""
        empresa = getattr(request.user, "empresa_activa", None)
        empresa_id = empresa.id if empresa else None
        
        try:
            from .services.relationship_learning import RelationshipLearningService
            from .models import LearnedRelationship
            from django.db.models import Q
            
            # Obtener todas las relaciones (empresa específicas y globales)
            filters = Q(is_blocked=False)
            if empresa_id:
                # Incluir relaciones de la empresa y globales
                filters = Q(empresa_id=empresa_id, is_blocked=False) | Q(empresa_id__isnull=True, is_blocked=False)
            
            relationships = LearnedRelationship.objects.filter(filters).order_by('-confidence', '-last_used_at')
            
            relationships_data = [
                {
                    "from_table": rel.from_table,
                    "from_column": rel.from_column,
                    "to_table": rel.to_table,
                    "to_column": rel.to_column,
                    "usage_count": rel.usage_count,
                    "success_count": rel.success_count,
                    "confidence": float(rel.confidence),
                    "source": rel.source,
                    "is_blocked": rel.is_blocked,
                    "last_used_at": rel.last_used_at.isoformat() if rel.last_used_at else None,
                }
                for rel in relationships
            ]
            
            return Response({
                "relationships": relationships_data,
                "total": len(relationships_data)
            })
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error obteniendo relaciones aprendidas: {e}", exc_info=True)
            return Response(
                {"detail": f"Error al obtener relaciones: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SchemaMetadataAPIView(APIView):
    """API para obtener metadata del schema de todas las tablas (solo lectura, para exportación frontend)."""
    
    permission_classes = [BuilderReportsPermission]
    
    def get(self, request, *args, **kwargs):
        """Obtiene metadata del schema de todas las tablas disponibles."""
        # Intentar obtener base_empresa del query param primero
        base_empresa = request.GET.get("base_empresa")
        
        # Si no está en el query param, intentar obtenerlo de la sesión
        if not base_empresa:
            if hasattr(request, 'session') and request.session:
                session_user = request.session.get('user', {})
                if session_user and 'base_empresa' in session_user:
                    base_empresa = session_user['base_empresa']
        
        # También intentar obtener desde el usuario si está disponible
        if not base_empresa and hasattr(request.user, 'base_empresa'):
            base_empresa = request.user.base_empresa
        
        # Intentar obtener desde empresa_activa si existe
        if not base_empresa:
            empresa = getattr(request.user, "empresa_activa", None)
            if empresa and hasattr(empresa, 'base_empresa'):
                base_empresa = empresa.base_empresa
        
        if not base_empresa:
            return Response(
                {"detail": "No se pudo determinar la base de datos de la empresa. Por favor, asegúrate de tener una empresa activa seleccionada."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from .services.semantic_service import SemanticService
            
            # Obtener todas las tablas disponibles
            datasources = SemanticService.list_datasources(base_empresa=base_empresa)
            table_names = [ds.name for ds in datasources]
            
            schema_data = {
                "base_empresa": base_empresa,
                "tables": {}
            }
            
            # Obtener campos de cada tabla
            for table_name in table_names:
                try:
                    fields = SemanticService.get_fields(datasource_name=table_name, base_empresa=base_empresa)
                    schema_data["tables"][table_name] = {
                        "fields": [
                            {
                                "name": f.name,
                                "data_type": f.data_type,
                                "is_nullable": f.is_nullable,
                                "is_primary_key": f.is_primary_key,
                                "is_foreign_key": f.is_foreign_key,
                                "referenced_table": f.referenced_table,
                                "referenced_field": f.referenced_field,
                            }
                            for f in fields
                        ]
                    }
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Error obteniendo campos de tabla {table_name}: {e}")
                    continue
            
            return Response(schema_data)
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error obteniendo schema metadata: {e}", exc_info=True)
            return Response(
                {"detail": f"Error al obtener schema: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DataMapAPIView(APIView):
    """API para obtener el mapa completo de datos (tablas y relaciones) para visualización."""
    
    permission_classes = [BuilderReportsPermission]
    
    # Cache TTL/LRU (reemplaza el dict anterior)
    _cache = None
    
    @classmethod
    def _get_cache(cls):
        """Obtiene o inicializa el cache TTL/LRU."""
        if cls._cache is None:
            from .services.cache_service import TTLCacheLRU
            cls._cache = TTLCacheLRU(maxsize=200, ttl_seconds=1800)  # 30 min TTL, 200 entradas max
        return cls._cache
    
    def _get_base_empresa(self, request):
        """Helper para obtener base_empresa de múltiples fuentes."""
        base_empresa = request.GET.get("base_empresa")
        if not base_empresa:
            if hasattr(request, 'session') and request.session:
                session_user = request.session.get('user', {})
                if session_user and 'base_empresa' in session_user:
                    base_empresa = session_user['base_empresa']
        
        if not base_empresa and hasattr(request.user, 'base_empresa'):
            base_empresa = request.user.base_empresa
        
        if not base_empresa:
            empresa = getattr(request.user, "empresa_activa", None)
            if empresa and hasattr(empresa, 'base_empresa'):
                base_empresa = empresa.base_empresa
        
        return base_empresa
    
    def _parse_filters(self, request):
        """Parsea los filtros de la request."""
        return {
            "type": request.GET.get("type", "both"),
            "direction": request.GET.get("direction", "both"),
            "depth": int(request.GET.get("depth", 1)),
            "min_conf": float(request.GET.get("min_conf", 0.8)),
            "status": request.GET.get("status", "approved"),  # approved, proposed, all
            "hide_temp": request.GET.get("hide_temp", "true").lower() == "true",
        }
    
    def _filters_hash(self, filters):
        """Genera un hash corto para los filtros."""
        import json
        import hashlib
        # Asegurarse de que el diccionario sea ordenado para un hash consistente
        sorted_filters = json.dumps(filters, sort_keys=True)
        return hashlib.sha1(sorted_filters.encode('utf-8')).hexdigest()[:10]  # 10 caracteres es suficiente
    
    def get(self, request, *args, **kwargs):
        """
        Obtiene el mapa de datos según la vista solicitada.
        
        Vistas soportadas:
        - overview: Clusters y estadísticas (default)
        - cluster: Grafo de un cluster específico
        - table: Ego network de una tabla
        
        Parámetros:
        - view: overview, cluster, table (default: overview)
        - cluster_id: Requerido si view=cluster
        - table: Requerido si view=table
        - depth: Profundidad para view=table (default: 1)
        - type: fk, learned, both (default: both)
        - direction: in, out, both (default: both)
        - min_conf: Confianza mínima para learned (default: 0.8)
        - status: approved, proposed, all (default: approved)
        - hide_temp: true/false (default: true)
        - force_refresh: true/false (default: false)
        - count_only: true/false (legacy, solo para conteo rápido)
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # Verificar si se solicita solo el conteo (legacy)
        count_only = request.GET.get("count_only", "false").lower() == "true"
        
        # Verificar si se fuerza recarga
        force_refresh = request.GET.get("force_refresh", "false").lower() == "true"
        
        # Obtener base_empresa
        base_empresa = self._get_base_empresa(request)
        
        if not base_empresa:
            return Response(
                {"detail": "No se pudo determinar la base de datos de la empresa."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Si solo se solicita el conteo, retornar rápidamente (legacy)
        if count_only:
            try:
                from .services.semantic_service import SemanticService
                datasources = SemanticService.list_datasources(base_empresa=base_empresa)
                return Response({
                    "total_tables": len(datasources),
                    "base_empresa": base_empresa
                })
            except Exception as e:
                logger.error(f"Error obteniendo conteo de tablas: {e}", exc_info=True)
                return Response(
                    {"detail": f"Error al obtener conteo: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        # Determinar vista
        view = request.GET.get("view", "overview")
        
        # Obtener empresa_id
        empresa = getattr(request.user, "empresa_activa", None)
        empresa_id = empresa.id if empresa else None
        
        # Obtener cache
        cache = self._get_cache()
        
        try:
            # Vista: overview
            if view == "overview":
                cache_key = f"data_map_overview_{base_empresa}"
                
                # Verificar cache
                if not force_refresh:
                    cached_data = cache.get(cache_key)
                    if cached_data:
                        logger.debug(f"📦 Cache hit para overview: {base_empresa}")
                        return Response(cached_data)
                
                # Obtener overview
                from .services.clustering_service import ClusteringService
                filters = self._parse_filters(request)
                data = ClusteringService.get_overview(base_empresa, empresa_id, filters)
                
                # Guardar en cache
                cache.set(cache_key, data)
                
                return Response(data)
            
            # Vista: cluster
            elif view == "cluster":
                cluster_id = request.GET.get("cluster_id")
                if not cluster_id:
                    return Response(
                        {"detail": "cluster_id es requerido para view=cluster"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                filters = self._parse_filters(request)
                filters_hash = self._filters_hash(filters)
                cache_key = f"data_map_cluster_{base_empresa}_{cluster_id}_{filters_hash}"
                
                # Verificar cache
                if not force_refresh:
                    cached_data = cache.get(cache_key)
                    if cached_data:
                        logger.debug(f"📦 Cache hit para cluster: {cluster_id}")
                        return Response(cached_data)
                
                # Obtener cluster graph
                from .services.clustering_service import ClusteringService
                data = ClusteringService.get_cluster_graph(base_empresa, empresa_id, cluster_id, filters)
                
                # Guardar en cache
                cache.set(cache_key, data)
                
                return Response(data)
            
            # Vista: table
            elif view == "table":
                table = request.GET.get("table")
                if not table:
                    return Response(
                        {"detail": "table es requerido para view=table"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                filters = self._parse_filters(request)
                depth = filters.get("depth", 1)
                filters_hash = self._filters_hash(filters)
                cache_key = f"data_map_table_{base_empresa}_{table}_{depth}_{filters_hash}"
                
                # Verificar cache
                if not force_refresh:
                    cached_data = cache.get(cache_key)
                    if cached_data:
                        logger.debug(f"📦 Cache hit para table: {table}")
                        return Response(cached_data)
                
                # Obtener table network
                from .services.table_network_service import TableNetworkService
                data = TableNetworkService.get_table_network(base_empresa, empresa_id, table, depth, filters)
                
                # Guardar en cache
                cache.set(cache_key, data)
                
                return Response(data)
            
            else:
                return Response(
                    {"detail": f"Vista '{view}' no soportada. Use: overview, cluster, table"},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Exception as e:
            logger.error(f"❌ Error obteniendo mapa de datos (view={view}): {e}", exc_info=True)
            return Response(
                {"detail": f"Error al obtener mapa de datos: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def post(self, request, *args, **kwargs):
        """Crea una nueva relación aprendida manualmente desde el mapa de datos."""
        try:
            from .models import LearnedRelationship
            from .services.semantic_service import SemanticService
            from django.utils import timezone
            
            # Obtener base_empresa para invalidar cache
            base_empresa = request.data.get("base_empresa")
            if not base_empresa:
                if hasattr(request, 'session') and request.session:
                    session_user = request.session.get('user', {})
                    if session_user and 'base_empresa' in session_user:
                        base_empresa = session_user['base_empresa']
            
            if not base_empresa and hasattr(request.user, 'base_empresa'):
                base_empresa = request.user.base_empresa
            
            if not base_empresa:
                empresa = getattr(request.user, "empresa_activa", None)
                if empresa and hasattr(empresa, 'base_empresa'):
                    base_empresa = empresa.base_empresa
            
            # Obtener cache para invalidación
            cache = self._get_cache()
            
            data = request.data
            
            # Validar datos requeridos
            required_fields = ['from_table', 'from_column', 'to_table', 'to_column']
            for field in required_fields:
                if field not in data:
                    return Response(
                        {"detail": f"Campo requerido faltante: {field}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            from_table = data['from_table']
            from_column = data['from_column']
            to_table = data['to_table']
            to_column = data['to_column']
            
            # Obtener empresa
            empresa = getattr(request.user, "empresa_activa", None)
            empresa_id = empresa.id if empresa else None
            
            # Verificar que las tablas existan (obtener base_empresa)
            base_empresa = request.data.get("base_empresa") or request.GET.get("base_empresa")
            if not base_empresa:
                if hasattr(request, 'session') and request.session:
                    session_user = request.session.get('user', {})
                    if session_user and 'base_empresa' in session_user:
                        base_empresa = session_user['base_empresa']
            
            if not base_empresa and hasattr(request.user, 'base_empresa'):
                base_empresa = request.user.base_empresa
            
            if not base_empresa:
                empresa = getattr(request.user, "empresa_activa", None)
                if empresa and hasattr(empresa, 'base_empresa'):
                    base_empresa = empresa.base_empresa
            
            if base_empresa:
                # Verificar que las tablas existan
                datasources = SemanticService.list_datasources(base_empresa=base_empresa)
                table_names = [ds.name for ds in datasources]
                
                if from_table not in table_names:
                    return Response(
                        {"detail": f"Tabla origen '{from_table}' no existe en la base de datos"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                if to_table not in table_names:
                    return Response(
                        {"detail": f"Tabla destino '{to_table}' no existe en la base de datos"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Verificar que los campos existan
                from_fields = SemanticService.get_fields(datasource_name=from_table, base_empresa=base_empresa)
                from_field_names = [f.name for f in from_fields]
                
                if from_column not in from_field_names:
                    return Response(
                        {"detail": f"Campo '{from_column}' no existe en la tabla '{from_table}'"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                to_fields = SemanticService.get_fields(datasource_name=to_table, base_empresa=base_empresa)
                to_field_names = [f.name for f in to_fields]
                
                if to_column not in to_field_names:
                    return Response(
                        {"detail": f"Campo '{to_column}' no existe en la tabla '{to_table}'"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Verificar si ya existe una relación FK para esta combinación
            from django.db.models import Q
            existing_fk = LearnedRelationship.objects.filter(
                from_table=from_table,
                from_column=from_column,
                to_table=to_table,
                to_column=to_column,
                source='foreign_key'
            ).exists()
            
            if existing_fk:
                return Response(
                    {"detail": "Ya existe una relación de clave foránea para esta combinación"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Crear o actualizar relación aprendida
            defaults = {
                'confidence': float(data.get('confidence', 0.7)),
                'source': 'manual',
                'usage_count': 0,
                'success_count': 0,
                'is_blocked': False,
                'status': LearnedRelationship.RelationshipStatus.PROPOSED,  # Por defecto proposed para manuales
            }
            
            # Agregar campos opcionales si vienen en el request
            if 'match_rule_json' in data:
                defaults['match_rule_json'] = data['match_rule_json']
            if 'validation_metrics_json' in data:
                defaults['validation_metrics_json'] = data['validation_metrics_json']
            if 'confidence_override' in data:
                defaults['confidence_override'] = float(data['confidence_override'])
            if 'status' in data:
                defaults['status'] = data['status']
            
            learned_rel, created = LearnedRelationship.objects.get_or_create(
                empresa_id=empresa_id,
                from_table=from_table,
                from_column=from_column,
                to_table=to_table,
                to_column=to_column,
                defaults=defaults
            )
            
            if not created:
                # Si ya existe, actualizar campos si vienen en el request
                updated = False
                if data.get('confidence') and float(data['confidence']) > learned_rel.confidence:
                    learned_rel.confidence = float(data['confidence'])
                    updated = True
                if 'match_rule_json' in data:
                    learned_rel.match_rule_json = data['match_rule_json']
                    updated = True
                if 'validation_metrics_json' in data:
                    learned_rel.validation_metrics_json = data['validation_metrics_json']
                    updated = True
                if 'confidence_override' in data:
                    learned_rel.confidence_override = float(data['confidence_override'])
                    updated = True
                if 'status' in data:
                    learned_rel.status = data['status']
                    learned_rel.version += 1  # Incrementar versión al cambiar status
                    updated = True
                
                if updated:
                    learned_rel.source = 'manual'
                    learned_rel.save()
            
            # Invalidar cache del mapa de datos después de crear relación
            if base_empresa:
                cache = self._get_cache()
                # Invalidar todas las vistas relacionadas con esta base_empresa
                cache.clear_prefix(f"data_map_overview_{base_empresa}")
                cache.clear_prefix(f"data_map_cluster_{base_empresa}_")
                cache.clear_prefix(f"data_map_table_{base_empresa}_")
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"🗑️ Cache invalidado para mapa de datos: {base_empresa}")
            
            return Response({
                "detail": "Relación aprendida creada exitosamente" if created else "Relación aprendida actualizada",
                "relationship": {
                    "id": learned_rel.id,
                    "from_table": learned_rel.from_table,
                    "from_column": learned_rel.from_column,
                    "to_table": learned_rel.to_table,
                    "to_column": learned_rel.to_column,
                    "confidence": float(learned_rel.confidence),
                    "source": learned_rel.source,
                }
            }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error creando relación aprendida: {e}", exc_info=True)
            return Response(
                {"detail": f"Error al crear relación: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ReportExportImportAPIView(APIView):
    """API para exportar e importar reportes, relaciones aprendidas desde JSON."""
    
    permission_classes = [BuilderReportsPermission]
    
    def get(self, request, *args, **kwargs):
        """Exporta reportes, relaciones o schema según type."""
        export_type = request.GET.get("type", "reports")  # reports, relationships, schema, all
        slugs_param = request.GET.get("slugs", "")
        slugs_filter = [s.strip() for s in slugs_param.split(",") if s.strip()] if slugs_param else None
        
        empresa = getattr(request.user, "empresa_activa", None)
        empresa_id = empresa.id if empresa else None
        
        if ExportImportService is None:
            return Response(
                {"detail": "ExportImportService no está disponible."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        try:
            result = {}
            
            if export_type in ("reports", "all"):
                from django.db.models import Q
                filters = Q(is_active=True)
                if empresa_id:
                    filters &= Q(empresa_id=empresa_id) | Q(empresa_id__isnull=True)
                else:
                    filters &= Q(empresa_id__isnull=True)
                
                reports = list(ReportDefinition.objects.filter(filters))
                if slugs_filter:
                    reports = [r for r in reports if r.slug in slugs_filter]
                
                if export_type == "reports" and not reports:
                    return Response(
                        {"detail": "No hay reportes para exportar."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                reports_export = ExportImportService.export_reports(reports, include_widgets=True)
                result["reports"] = reports_export.get("reports", [])
                result["widgets"] = reports_export.get("widgets", {})
            
            if export_type in ("relationships", "all"):
                rels_export = ExportImportService.export_learned_relationships(
                    empresa_id=empresa_id, include_global=True
                )
                result["learned_relationships"] = rels_export.get("relationships", [])
            
            if export_type in ("schema", "all"):
                base_empresa = None
                if empresa and hasattr(empresa, "base_empresa"):
                    base_empresa = empresa.base_empresa
                if not base_empresa and hasattr(request.user, "base_empresa"):
                    base_empresa = request.user.base_empresa
                
                if base_empresa:
                    schema_export = ExportImportService.export_schema_metadata(base_empresa)
                    result["schema_metadata"] = schema_export.get("tables", {})
                    result["base_empresa"] = base_empresa
                elif export_type == "schema":
                    return Response(
                        {"detail": "No se pudo determinar base_empresa para exportar schema."},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            from django.utils import timezone
            result["version"] = getattr(ExportImportService, "VERSION", "1.0.0")
            result["export_type"] = "full_export" if export_type == "all" else export_type
            result["exported_at"] = timezone.now().isoformat()
            
            return Response(result)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error exportando {export_type}: {e}", exc_info=True)
            return Response(
                {"detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def post(self, request, *args, **kwargs):
        """Importa reportes, relaciones aprendidas desde JSON."""
        import_type = request.data.get("type", "reports")  # reports, relationships, all
        empresa_id = getattr(request.user, "empresa_activa", None)
        empresa_id = empresa_id.id if empresa_id else None
        overwrite_val = request.data.get("overwrite", False)
        overwrite = overwrite_val in (True, "true", "1", 1, "yes")
        merge_strategy = request.data.get("merge_strategy", "merge")
        
        try:
            # Obtener datos del request (puede venir como JSON string o dict)
            if isinstance(request.data.get("data"), str):
                import json
                data = json.loads(request.data["data"])
            else:
                data = request.data.get("data") or request.data
            
            if not data:
                return Response(
                    {"detail": "Datos de importación no encontrados"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            results = {}
            
            if import_type == "reports" or import_type == "all":
                if import_type == "all":
                    reports_data = data.get("reports", [])
                    widgets_data = data.get("widgets", {})
                else:
                    # Formato single report o batch
                    if data.get("export_type") == "report":
                        reports_data = [data.get("report", {})]
                        widgets_data = {reports_data[0].get("slug"): data.get("report", {}).get("widgets", [])}
                    else:
                        reports_data = data.get("reports", [])
                        widgets_data = data.get("widgets", {})
                
                imported_reports = []
                for report_data in reports_data:
                    try:
                        # Crear estructura de export single para usar import_report
                        export_data = {
                            "version": data.get("version", "1.0.0"),
                            "export_type": "report",
                            "report": report_data
                        }
                        
                        # Agregar widgets si existen
                        slug = report_data.get("slug")
                        if slug and slug in widgets_data:
                            export_data["report"]["widgets"] = widgets_data[slug]
                        
                        if ExportImportService is None:
                            raise ValueError("ExportImportService no está disponible. El módulo export_import_service no está instalado.")
                        report = ExportImportService.import_report(
                            data=export_data,
                            empresa_id=empresa_id,
                            overwrite=overwrite
                        )
                        imported_reports.append({
                            "slug": report.slug,
                            "name": report.name,
                            "status": "imported"
                        })
                    except Exception as e:
                        imported_reports.append({
                            "slug": report_data.get("slug", "unknown"),
                            "status": "error",
                            "error": str(e)
                        })
                
                results["reports"] = imported_reports
            
            if import_type == "relationships" or import_type == "all":
                if import_type == "all":
                    rels_data = {
                        "version": data.get("version", "1.0.0"),
                        "export_type": "learned_relationships",
                        "relationships": data.get("learned_relationships", [])
                    }
                else:
                    rels_data = data
                
                if ExportImportService is None:
                    raise ValueError("ExportImportService no está disponible. El módulo export_import_service no está instalado.")
                count = ExportImportService.import_learned_relationships(
                    data=rels_data,
                    empresa_id=empresa_id,
                    merge_strategy=merge_strategy
                )
                results["relationships"] = {"imported_count": count}
            
            return Response({
                "status": "success",
                "message": "Importación completada",
                "results": results
            })
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error importando {import_type}: {e}", exc_info=True)
            return Response(
                {"detail": f"Error al importar: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RelationshipValidationAPIView(APIView):
    """API para validar relaciones aprendidas antes de crearlas."""
    
    permission_classes = [BuilderReportsPermission]
    
    def post(self, request, *args, **kwargs):
        """
        Valida una relación aprendida calculando métricas en MySQL.
        
        Request Body:
        {
            "from_table": "tabla1",
            "from_column": "campo1",
            "to_table": "tabla2",
            "to_column": "campo2",
            "match_rule": {
                "transformations": [
                    {"type": "TRIM", "field": "from"},
                    {"type": "UPPER", "field": "both"}
                ]
            }
        }
        """
        try:
            from .services.relationship_validation_service import RelationshipValidationService
            
            data = request.data
            required_fields = ['from_table', 'from_column', 'to_table', 'to_column']
            for field in required_fields:
                if field not in data:
                    return Response(
                        {"detail": f"Campo requerido faltante: {field}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Obtener base_empresa
            base_empresa = self._get_base_empresa(request)
            if not base_empresa:
                return Response(
                    {"detail": "No se pudo determinar la base de datos de la empresa."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validar relación
            result = RelationshipValidationService.validate(
                base_empresa=base_empresa,
                from_table=data['from_table'],
                from_column=data['from_column'],
                to_table=data['to_table'],
                to_column=data['to_column'],
                match_rule_json=data.get('match_rule', {})
            )
            
            return Response(result, status=status.HTTP_200_OK)
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"❌ Error validando relación: {e}", exc_info=True)
            return Response(
                {"detail": f"Error al validar relación: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _get_base_empresa(self, request):
        """Helper para obtener base_empresa (reutilizado de DataMapAPIView)."""
        base_empresa = request.data.get("base_empresa") or request.GET.get("base_empresa")
        if not base_empresa:
            if hasattr(request, 'session') and request.session:
                session_user = request.session.get('user', {})
                if session_user and 'base_empresa' in session_user:
                    base_empresa = session_user['base_empresa']
        
        if not base_empresa and hasattr(request.user, 'base_empresa'):
            base_empresa = request.user.base_empresa
        
        if not base_empresa:
            empresa = getattr(request.user, "empresa_activa", None)
            if empresa and hasattr(empresa, 'base_empresa'):
                base_empresa = empresa.base_empresa
        
        return base_empresa


class ClusterManagementAPIView(APIView):
    """API para gestionar clusters personalizados (crear, editar, mover tablas)."""
    permission_classes = [BuilderReportsPermission]
    
    def _get_base_empresa(self, request):
        """Helper para obtener base_empresa."""
        base_empresa = request.GET.get("base_empresa") or request.data.get("base_empresa")
        if not base_empresa:
            if hasattr(request, 'session') and request.session:
                session_user = request.session.get('user', {})
                if session_user and 'base_empresa' in session_user:
                    base_empresa = session_user['base_empresa']
        if not base_empresa and hasattr(request.user, 'base_empresa'):
            base_empresa = request.user.base_empresa
        if not base_empresa:
            empresa = getattr(request.user, "empresa_activa", None)
            if empresa and hasattr(empresa, 'base_empresa'):
                base_empresa = empresa.base_empresa
        return base_empresa
    
    def get(self, request, *args, **kwargs):
        """Obtiene todos los clusters personalizados para una base_empresa."""
        from .models import TableClusterAssignment
        from django.db.models import Q
        
        base_empresa = self._get_base_empresa(request)
        if not base_empresa:
            return Response(
                {"detail": "No se pudo determinar la base de datos de la empresa."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        empresa = getattr(request.user, "empresa_activa", None)
        empresa_id = empresa.id if empresa else None
        
        # Buscar asignaciones
        filters = Q(base_empresa=base_empresa)
        if empresa_id:
            filters = Q(base_empresa=base_empresa, empresa_id=empresa_id) | Q(base_empresa=base_empresa, empresa_id__isnull=True)
        else:
            filters = Q(base_empresa=base_empresa, empresa_id__isnull=True)
        
        assignments = TableClusterAssignment.objects.filter(filters).order_by('cluster_id', 'order', 'table_name')
        
        # Agrupar por cluster
        clusters = {}
        for assignment in assignments:
            cluster_id = assignment.cluster_id
            if cluster_id not in clusters:
                clusters[cluster_id] = {
                    "id": cluster_id,
                    "label": assignment.cluster_label,
                    "tables": []
                }
            clusters[cluster_id]["tables"].append({
                "table_name": assignment.table_name,
                "order": assignment.order
            })
        
        return Response({
            "clusters": list(clusters.values()),
            "base_empresa": base_empresa
        })
    
    def post(self, request, *args, **kwargs):
        """Crea o actualiza asignaciones de tablas a clusters."""
        from .models import TableClusterAssignment
        from django.db import transaction
        from django.utils import timezone
        
        base_empresa = self._get_base_empresa(request)
        if not base_empresa:
            return Response(
                {"detail": "No se pudo determinar la base de datos de la empresa."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        empresa = getattr(request.user, "empresa_activa", None)
        empresa_id = empresa.id if empresa else None
        
        data = request.data
        cluster_id = data.get("cluster_id")
        cluster_label = data.get("cluster_label")
        tables = data.get("tables", [])  # Lista de {table_name, order}
        
        if not cluster_id or not cluster_label:
            return Response(
                {"detail": "cluster_id y cluster_label son requeridos."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic():
                # Eliminar asignaciones existentes para estas tablas en esta base_empresa
                table_names = [t.get("table_name") for t in tables if t.get("table_name")]
                if table_names:
                    filters = Q(base_empresa=base_empresa, table_name__in=table_names)
                    if empresa_id:
                        filters = (Q(base_empresa=base_empresa, empresa_id=empresa_id) | Q(base_empresa=base_empresa, empresa_id__isnull=True)) & Q(table_name__in=table_names)
                    TableClusterAssignment.objects.filter(filters).delete()
                
                # Crear nuevas asignaciones
                created = []
                for idx, table_data in enumerate(tables):
                    table_name = table_data.get("table_name")
                    if not table_name:
                        continue
                    
                    assignment, _ = TableClusterAssignment.objects.update_or_create(
                        base_empresa=base_empresa,
                        table_name=table_name,
                        defaults={
                            "empresa_id": empresa_id,
                            "cluster_id": cluster_id,
                            "cluster_label": cluster_label,
                            "order": table_data.get("order", idx),
                            "created_by": get_user_for_foreignkey(request.user, request) if hasattr(request, 'user') else None,
                        }
                    )
                    created.append({
                        "table_name": assignment.table_name,
                        "cluster_id": assignment.cluster_id,
                        "order": assignment.order
                    })
                
                # Invalidar cache del data map
                DataMapAPIView._get_cache().clear_prefix(f"data_map_overview_{base_empresa}")
                DataMapAPIView._get_cache().clear_prefix(f"data_map_cluster_{base_empresa}_")
                
                return Response({
                    "detail": f"Cluster '{cluster_label}' actualizado con {len(created)} tablas.",
                    "cluster": {
                        "id": cluster_id,
                        "label": cluster_label,
                        "tables": created
                    }
                }, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            logger.error(f"Error gestionando cluster: {e}", exc_info=True)
            return Response(
                {"detail": f"Error al gestionar cluster: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def delete(self, request, cluster_id, *args, **kwargs):
        """Elimina un cluster completo o tablas específicas de un cluster."""
        from .models import TableClusterAssignment
        from django.db.models import Q
        
        base_empresa = self._get_base_empresa(request)
        if not base_empresa:
            return Response(
                {"detail": "No se pudo determinar la base de datos de la empresa."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        empresa = getattr(request.user, "empresa_activa", None)
        empresa_id = empresa.id if empresa else None
        
        # Si se especifican tablas, eliminar solo esas; sino, eliminar todo el cluster
        table_names = request.data.get("tables", [])
        
        filters = Q(base_empresa=base_empresa, cluster_id=cluster_id)
        if empresa_id:
            filters = (Q(base_empresa=base_empresa, empresa_id=empresa_id) | Q(base_empresa=base_empresa, empresa_id__isnull=True)) & Q(cluster_id=cluster_id)
        
        if table_names:
            filters = filters & Q(table_name__in=table_names)
        
        deleted_count = TableClusterAssignment.objects.filter(filters).delete()[0]
        
        # Invalidar cache
        DataMapAPIView._get_cache().clear_prefix(f"data_map_overview_{base_empresa}")
        DataMapAPIView._get_cache().clear_prefix(f"data_map_cluster_{base_empresa}_")
        
        return Response({
            "detail": f"{deleted_count} asignación(es) eliminada(s)."
        }, status=status.HTTP_204_NO_CONTENT)


class RelationshipGovernanceAPIView(APIView):
    """API para gobernanza de relaciones aprendidas (approve, deprecate, edit)."""
    
    permission_classes = [BuilderReportsPermission]
    
    def _get_base_empresa(self, request):
        """Helper para obtener base_empresa."""
        base_empresa = request.data.get("base_empresa") or request.GET.get("base_empresa")
        if not base_empresa:
            if hasattr(request, 'session') and request.session:
                session_user = request.session.get('user', {})
                if session_user and 'base_empresa' in session_user:
                    base_empresa = session_user['base_empresa']
        
        if not base_empresa and hasattr(request.user, 'base_empresa'):
            base_empresa = request.user.base_empresa
        
        if not base_empresa:
            empresa = getattr(request.user, "empresa_activa", None)
            if empresa and hasattr(empresa, 'base_empresa'):
                base_empresa = empresa.base_empresa
        
        return base_empresa
    
    def _invalidate_cache(self, base_empresa: str):
        """Invalida cache del mapa de datos."""
        if base_empresa:
            from .api_views import DataMapAPIView
            cache = DataMapAPIView._get_cache()
            cache.clear_prefix(f"data_map_overview_{base_empresa}")
            cache.clear_prefix(f"data_map_cluster_{base_empresa}_")
            cache.clear_prefix(f"data_map_table_{base_empresa}_")
    
    def _create_audit_log(self, relationship, action: str, actor, diff_json: Dict, notes: str = ""):
        """Crea un log de auditoría."""
        from .models import RelationshipAuditLog
        RelationshipAuditLog.objects.create(
            relationship=relationship,
            action=action,
            actor=actor,
            diff_json=diff_json,
            notes=notes
        )
    
    def patch(self, request, relationship_id: int, *args, **kwargs):
        """
        Acciones de gobernanza: approve, deprecate, edit.
        
        URLs:
        - /api/reports/builder/data-map/relationships/<id>/approve/
        - /api/reports/builder/data-map/relationships/<id>/deprecate/
        - /api/reports/builder/data-map/relationships/<id>/ (edit)
        
        Determina la acción desde la URL path.
        """
        try:
            from .models import LearnedRelationship
            import logging
            logger = logging.getLogger(__name__)
            
            # Obtener relación
            relationship = get_object_or_404(
                LearnedRelationship,
                id=relationship_id,
                is_blocked=False  # No permitir acciones sobre relaciones bloqueadas
            )
            
            # Determinar acción desde la URL
            path = request.path
            if '/approve/' in path:
                action = 'approve'
            elif '/deprecate/' in path:
                action = 'deprecate'
            else:
                action = 'edit'
            
            base_empresa = self._get_base_empresa(request)
            
            # Guardar estado anterior para audit log
            old_state = {
                "status": relationship.status,
                "confidence": float(relationship.confidence),
                "confidence_override": float(relationship.confidence_override) if relationship.confidence_override else None,
                "match_rule_json": relationship.match_rule_json,
                "validation_metrics_json": relationship.validation_metrics_json,
                "version": relationship.version
            }
            
            if action == "approve":
                relationship.status = LearnedRelationship.RelationshipStatus.APPROVED
                relationship.version += 1
                relationship.save()
                
                # Audit log
                self._create_audit_log(
                    relationship=relationship,
                    action="approved",
                    actor=request.user,
                    diff_json={"before": old_state, "after": {
                        "status": relationship.status,
                        "version": relationship.version
                    }},
                    notes=request.data.get("notes", "")
                )
                
                logger.info(f"✅ Relación {relationship_id} aprobada por {request.user.username}")
                
                # Invalidar cache
                self._invalidate_cache(base_empresa)
                
                return Response({
                    "detail": "Relación aprobada exitosamente",
                    "relationship": {
                        "id": relationship.id,
                        "status": relationship.status,
                        "version": relationship.version
                    }
                }, status=status.HTTP_200_OK)
            
            elif action == "deprecate":
                deprecated_reason = request.data.get("deprecated_reason", "")
                if not deprecated_reason:
                    return Response(
                        {"detail": "deprecated_reason es requerido para deprecar una relación"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                relationship.status = LearnedRelationship.RelationshipStatus.DEPRECATED
                relationship.deprecated_reason = deprecated_reason
                relationship.version += 1
                relationship.save()
                
                # Audit log
                self._create_audit_log(
                    relationship=relationship,
                    action="deprecated",
                    actor=request.user,
                    diff_json={"before": old_state, "after": {
                        "status": relationship.status,
                        "deprecated_reason": deprecated_reason,
                        "version": relationship.version
                    }},
                    notes=request.data.get("notes", "")
                )
                
                logger.info(f"⚠️ Relación {relationship_id} deprecada por {request.user.username}")
                
                # Invalidar cache
                self._invalidate_cache(base_empresa)
                
                return Response({
                    "detail": "Relación deprecada exitosamente",
                    "relationship": {
                        "id": relationship.id,
                        "status": relationship.status,
                        "deprecated_reason": deprecated_reason,
                        "version": relationship.version
                    }
                }, status=status.HTTP_200_OK)
            
            elif action == "edit" or action == "":
                # Editar campos permitidos
                updated = False
                
                if "match_rule_json" in request.data:
                    relationship.match_rule_json = request.data["match_rule_json"]
                    updated = True
                
                if "validation_metrics_json" in request.data:
                    relationship.validation_metrics_json = request.data["validation_metrics_json"]
                    updated = True
                
                if "confidence_override" in request.data:
                    relationship.confidence_override = float(request.data["confidence_override"])
                    updated = True
                
                if "status" in request.data:
                    # Solo permitir cambiar status si el usuario tiene permisos (por ahora todos)
                    new_status = request.data["status"]
                    if new_status in [s[0] for s in LearnedRelationship.RelationshipStatus.choices]:
                        relationship.status = new_status
                        updated = True
                
                if "deprecated_reason" in request.data:
                    relationship.deprecated_reason = request.data["deprecated_reason"]
                    updated = True
                
                if updated:
                    relationship.version += 1
                    relationship.save()
                    
                    # Audit log
                    new_state = {
                        "status": relationship.status,
                        "confidence": float(relationship.confidence),
                        "confidence_override": float(relationship.confidence_override) if relationship.confidence_override else None,
                        "match_rule_json": relationship.match_rule_json,
                        "validation_metrics_json": relationship.validation_metrics_json,
                        "version": relationship.version
                    }
                    
                    self._create_audit_log(
                        relationship=relationship,
                        action="edited",
                        actor=request.user,
                        diff_json={"before": old_state, "after": new_state},
                        notes=request.data.get("notes", "")
                    )
                    
                    logger.info(f"✏️ Relación {relationship_id} editada por {request.user.username}")
                    
                    # Invalidar cache
                    self._invalidate_cache(base_empresa)
                    
                    return Response({
                        "detail": "Relación actualizada exitosamente",
                        "relationship": {
                            "id": relationship.id,
                            "status": relationship.status,
                            "version": relationship.version,
                            "match_rule_json": relationship.match_rule_json,
                            "validation_metrics_json": relationship.validation_metrics_json,
                            "confidence_override": float(relationship.confidence_override) if relationship.confidence_override else None
                        }
                    }, status=status.HTTP_200_OK)
                else:
                    return Response(
                        {"detail": "No se proporcionaron campos para actualizar"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            else:
                return Response(
                    {"detail": f"Acción '{action}' no soportada. Use: approve, deprecate, edit"},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"❌ Error en gobernanza de relación {relationship_id}: {e}", exc_info=True)
            return Response(
                {"detail": f"Error al procesar acción: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ReferenceValuesAPIView(APIView):
    """
    API para obtener valores únicos de una tabla de referencia.
    Usado por filtros dinámicos para cargar opciones (sucursales, puntos de venta, etc.).
    """
    permission_classes = [OperationalReportsPermission | ManagerialReportsPermission | BuilderReportsPermission]
    
    def _get_base_empresa(self, request):
        """Helper para obtener base_empresa de múltiples fuentes."""
        base_empresa = request.GET.get("base_empresa")
        if not base_empresa:
            if hasattr(request, 'session') and request.session:
                session_user = request.session.get('user', {})
                if session_user and 'base_empresa' in session_user:
                    base_empresa = session_user['base_empresa']
        if not base_empresa and hasattr(request.user, 'base_empresa'):
            base_empresa = request.user.base_empresa
        if not base_empresa:
            empresa = getattr(request.user, "empresa_activa", None)
            if empresa and hasattr(empresa, 'base_empresa'):
                base_empresa = empresa.base_empresa
        return base_empresa
    
    def get(self, request, *args, **kwargs):
        """
        Obtiene valores únicos de una tabla de referencia.
        
        Parámetros:
        - table: Nombre de la tabla (ej: 'sucursales', 'punto_venta')
        - value_field: Campo que contiene el valor (ej: 'CodSucursal', 'id_punto_venta')
        - display_field: Campo que contiene la etiqueta (ej: 'Nombre', 'Nombre')
        - search: (opcional) Término de búsqueda para filtrar resultados
        """
        table = request.GET.get('table')
        value_field = request.GET.get('value_field', 'id')
        display_field = request.GET.get('display_field', 'nombre')
        search = request.GET.get('search', '').strip()
        
        if not table:
            return Response(
                {"detail": "El parámetro 'table' es requerido"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        base_empresa = self._get_base_empresa(request)
        if not base_empresa:
            return Response(
                {"detail": "No se pudo determinar la base de datos de la empresa."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            from .services.connection_pool import get_mysql_pool
            
            from .services.connection_pool import get_mysql_pool
            
            pool = get_mysql_pool()
            if not pool:
                return Response(
                    {"detail": f"No se pudo obtener conexión a la base de datos {base_empresa}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # get_connection devuelve un context manager, debe usarse con 'with'
            with pool.get_connection(base_empresa) as connection:
                cursor = connection.cursor()
                
                # Construir query para obtener valores únicos
                # Escapar nombres de tabla y campos para prevenir SQL injection
                table_escaped = f"`{table}`"
                value_field_escaped = f"`{value_field}`"
                display_field_escaped = f"`{display_field}`"
                
                # Query base: obtener valores únicos
                if search:
                    # Si hay búsqueda, filtrar por el campo de display
                    query = f"""
                        SELECT DISTINCT {value_field_escaped} as value, {display_field_escaped} as label
                        FROM {table_escaped}
                        WHERE {display_field_escaped} LIKE %s
                        ORDER BY {display_field_escaped}
                        LIMIT 50
                    """
                    cursor.execute(query, (f'%{search}%',))
                else:
                    # Sin búsqueda, obtener todos (limitado a 100)
                    query = f"""
                        SELECT DISTINCT {value_field_escaped} as value, {display_field_escaped} as label
                        FROM {table_escaped}
                        WHERE {value_field_escaped} IS NOT NULL
                        AND {display_field_escaped} IS NOT NULL
                        ORDER BY {display_field_escaped}
                        LIMIT 100
                    """
                    cursor.execute(query)
                
                results = cursor.fetchall()
                
                # Convertir a formato JSON
                values = []
                for row in results:
                    values.append({
                        'value': str(row[0]) if row[0] is not None else '',
                        'label': str(row[1]) if row[1] is not None else str(row[0])
                    })
                
                return Response({
                    'values': values,
                    'table': table,
                    'count': len(values)
                })
                
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error obteniendo valores de referencia para {table}: {e}", exc_info=True)
            return Response(
                {"detail": f"Error al obtener valores de referencia: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ReconciliacionMovimientoDetalleAPIView(APIView):
    """
    API para obtener el detalle de movimientos (OC, Rem, FactOC, Anul) por artículo.
    Usado en validación OC pendiente para mostrar nro_comprobante, fecha, cantidad al hacer clic en un chip.
    """
    permission_classes = [OperationalReportsPermission | ManagerialReportsPermission]

    def get(self, request, *args, **kwargs):
        id_art = request.query_params.get("id_art")
        tipo = request.query_params.get("tipo", "").lower()
        fecha_desde = request.query_params.get("fecha_desde") or None
        fecha_hasta = request.query_params.get("fecha_hasta") or None

        if not id_art:
            return Response(
                {"detail": "El parámetro 'id_art' es requerido"},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            id_art = int(id_art)
        except (TypeError, ValueError):
            return Response(
                {"detail": "id_art debe ser un número entero"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if tipo not in ("oc", "rem", "factoc", "anul"):
            return Response(
                {"detail": "El parámetro 'tipo' debe ser: oc, rem, factoc o anul"},
                status=status.HTTP_400_BAD_REQUEST
            )

        base_empresa = None
        if hasattr(request, "session") and request.session:
            session_user = request.session.get("user", {})
            if session_user and "base_empresa" in session_user:
                base_empresa = session_user["base_empresa"]
        if not base_empresa and hasattr(request.user, "base_empresa"):
            base_empresa = request.user.base_empresa

        if not base_empresa:
            return Response(
                {"detail": "No se pudo determinar la base de datos de la empresa."},
                status=status.HTTP_400_BAD_REQUEST
            )

        from .services.reconciliation_saldo_pedido_proveedor import get_movimiento_detalle

        items = get_movimiento_detalle(
            base_empresa=base_empresa,
            id_art=id_art,
            tipo=tipo,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
        )
        return Response({"items": items, "tipo": tipo, "id_art": id_art})

