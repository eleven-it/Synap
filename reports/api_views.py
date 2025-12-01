from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .domain import build_catalog_for_user
from .models import ReportDefinition, ReportWorkspace
from .permissions import OperationalReportsPermission, ManagerialReportsPermission


def get_user_for_foreignkey(user):
    """
    Helper para obtener un usuario válido para ForeignKeys.
    Si es AdministraNETUser, retorna None (no se puede usar en ForeignKeys).
    Si es UsuarioExtendido, retorna el usuario directamente.
    """
    from core.models import UsuarioExtendido
    if isinstance(user, UsuarioExtendido):
        return user
    # Para AdministraNETUser, retornar None ya que no es un modelo de Django
    return None
from .serializers import (
    CatalogEntrySerializer,
    ReportQueryRequestSerializer,
    ReportQueryResponseSerializer,
    KPIResponseSerializer,
)
from .services.query_runner import QueryRunnerService
from .services.export_service import ExportService


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

    permission_classes = [OperationalReportsPermission | ManagerialReportsPermission]

    def post(self, request, *args, **kwargs):
        serializer = ReportQueryRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        report = get_object_or_404(ReportDefinition, slug=payload["slug"], is_active=True)
        if report.is_operational() and not OperationalReportsPermission().has_permission(request, self):
            return Response({"detail": "Operational reports not allowed."}, status=status.HTTP_403_FORBIDDEN)
        if report.is_managerial() and not ManagerialReportsPermission().has_permission(request, self):
            return Response({"detail": "Managerial reports not allowed."}, status=status.HTTP_403_FORBIDDEN)

        # Agregar base_empresa al payload si está disponible en la sesión
        if hasattr(request, 'session') and request.session:
            session_user = request.session.get('user', {})
            if session_user and 'base_empresa' in session_user:
                if 'filters' not in payload:
                    payload['filters'] = {}
                payload['filters']['base_empresa'] = session_user['base_empresa']

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
            response_serializer = ReportQueryResponseSerializer(result.__dict__)
            return Response(response_serializer.data)
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

    def get(self, request, *args, **kwargs):
        workspace = self._get_workspace(request)
        slugs = list(workspace.items or [])

        if not slugs:
            return Response({"slots": [], "count": 0})

        reports = (
            ReportDefinition.objects.filter(slug__in=slugs, is_active=True)
            .prefetch_related("widgets")
        )
        report_map = {report.slug: report for report in reports}

        slots = []
        valid_slugs = []
        for slug in slugs:
            report = report_map.get(slug)
            if not report:
                continue
            widget = report.widgets.order_by("order", "id").first()
            if not widget:
                continue
            valid_slugs.append(slug)
            slots.append(
                {
                    "slug": report.slug,
                    "name": report.name,
                    "category": report.category,
                    "widget": {
                        "id": widget.id,
                        "name": widget.name,
                        "widget_type": widget.widget_type,
                        "configuration": widget.configuration or {},
                    },
                }
            )

        if valid_slugs != slugs:
            workspace.items = valid_slugs
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
        if slug in current:
            return Response({"status": "exists", "count": len(current)})

        if len(current) >= self.MAX_ITEMS:
            return Response(
                {
                    "detail": "Se alcanzó el máximo de elementos en el workspace.",
                    "count": len(current),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        current.append(slug)
        workspace.items = current
        workspace.save(update_fields=["items", "updated_at"])
        return Response({"status": "added", "count": len(current)})

    def delete(self, request, *args, **kwargs):
        slug = request.data.get("slug")
        if not slug:
            return Response({"detail": "Slug requerido."}, status=status.HTTP_400_BAD_REQUEST)

        workspace = self._get_workspace(request)
        current = list(workspace.items or [])
        if slug not in current:
            return Response({"status": "missing", "count": len(current)})

        current = [item for item in current if item != slug]
        workspace.items = current
        workspace.save(update_fields=["items", "updated_at"])
        return Response({"status": "removed", "count": len(current)})


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

    permission_classes = [OperationalReportsPermission | ManagerialReportsPermission]

    def post(self, request, *args, **kwargs):
        serializer = ReportQueryRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        export_type = request.query_params.get("type", "xlsx")

        report = get_object_or_404(ReportDefinition, slug=payload["slug"], is_active=True)
        if report.is_operational() and not OperationalReportsPermission().has_permission(request, self):
            return Response({"detail": "Operational reports not allowed."}, status=status.HTTP_403_FORBIDDEN)
        if report.is_managerial() and not ManagerialReportsPermission().has_permission(request, self):
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
        # Solo el usuario 'supervisor' (por cod_usuario) puede cambiar la visibilidad
        is_supervisor_user = False
        if hasattr(request.user, 'cod_usuario') and (request.user.cod_usuario or '').lower() == 'supervisor':
            is_supervisor_user = True
        
        if not is_supervisor_user:
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
                "message": f"Reporte {'visible' if report.is_visible else 'oculto'} para usuarios con puesto Supervisor"
            })
        except ReportDefinition.DoesNotExist:
            return Response(
                {"detail": "Reporte no encontrado."},
                status=status.HTTP_404_NOT_FOUND
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
            
            else:
                cursor.close()
                conn.close()
                return Response(
                    {"detail": "Tipo de filtro no válido. Use 'puntos_venta', 'sucursales' o 'cajas'."},
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


