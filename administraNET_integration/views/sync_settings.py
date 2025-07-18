from django.views.generic import TemplateView
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.utils import timezone
from django.db.models import Avg, Count, Q
from django.utils.translation import gettext as _
from core.utils.permissions import CorePermissionRequiredMixin
from administraNET_integration.models import AdministraNETConfig, SyncLog
from administraNET_integration.services.connection_service import AdministraNETConnectionService
import json
import logging

logger = logging.getLogger(__name__)

class SyncSettingsView(CorePermissionRequiredMixin, TemplateView):
    template_name = "administraNET_integration/sync_settings.html"
    permission_required = "core.can_manage_integrations"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener configuración activa o crear una por defecto
        config = AdministraNETConfig.objects.filter(is_active=True).first()
        if not config:
            config = AdministraNETConfig.objects.create(
                host='localhost',
                port=3306,
                database_name='administranet',
                username='root',
                password='',
                is_active=False,
                sync_interval=30,
                enable_logging=True,
                log_level='INFO'
            )
        
        context['config'] = config
        
        # Calcular métricas reales
        context.update(self._calculate_metrics())
        
        # Calcular estado del sistema
        context.update(self._get_system_status())
        
        return context

    def post(self, request, *args, **kwargs):
        """Manejar guardado de configuración"""
        if not request.user.has_perm('core.can_manage_integrations'):
            messages.error(request, _("No tienes permisos para esta acción."))
            return self.get(request, *args, **kwargs)
        
        config = AdministraNETConfig.objects.filter(is_active=True).first()
        if not config:
            config = AdministraNETConfig()
        
        try:
            # Actualizar configuración básica
            config.sync_interval = int(request.POST.get('sync_interval', 30))
            config.is_active = request.POST.get('is_active') == 'true'
            config.enable_logging = request.POST.get('enable_logging') == 'true'
            config.log_level = request.POST.get('log_level', 'INFO')
            
            # Actualizar configuración de conexión si se proporciona
            if request.POST.get('host'):
                config.host = request.POST.get('host')
            if request.POST.get('port'):
                config.port = int(request.POST.get('port', 3306))
            if request.POST.get('database_name'):
                config.database_name = request.POST.get('database_name')
            if request.POST.get('username'):
                config.username = request.POST.get('username')
            if request.POST.get('password'):
                config.password = request.POST.get('password')
            
            # Validaciones
            if config.sync_interval < 1 or config.sync_interval > 1440:
                messages.error(request, _("El intervalo de sincronización debe estar entre 1 y 1440 minutos."))
                return self.get(request, *args, **kwargs)
            
            config.save()
            
            # Log de auditoría
            logger.info(f"[AUDITORÍA] Usuario {request.user} actualizó configuración de sincronización. "
                       f"Intervalo: {config.sync_interval}min, Activo: {config.is_active}, "
                       f"Logging: {config.enable_logging}, Nivel: {config.log_level}")
            
            messages.success(request, _("Configuración guardada exitosamente."))
            
        except (ValueError, TypeError) as e:
            messages.error(request, _("Error en los datos de entrada. Verifica los valores."))
            logger.error(f"Error guardando configuración: {e}")
        except Exception as e:
            messages.error(request, _("Error interno al guardar la configuración."))
            logger.error(f"Error inesperado guardando configuración: {e}")
        
        return self.get(request, *args, **kwargs)

    def _calculate_metrics(self):
        """Calcular métricas reales de sincronización"""
        try:
            # Obtener logs de los últimos 30 días
            thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
            recent_logs = SyncLog.objects.filter(started_at__gte=thirty_days_ago)
            
            # Estadísticas básicas
            total_logs = recent_logs.count()
            success_logs = recent_logs.filter(status='SUCCESS').count()
            error_logs = recent_logs.filter(status='ERROR').count()
            running_logs = recent_logs.filter(status='RUNNING').count()
            
            # Calcular tasa de éxito
            success_rate = (success_logs / total_logs * 100) if total_logs > 0 else 0
            
            # Calcular duración promedio
            completed_logs = recent_logs.filter(status__in=['SUCCESS', 'ERROR']).exclude(duration__isnull=True)
            avg_duration = completed_logs.aggregate(Avg('duration'))['duration__avg']
            avg_duration_seconds = avg_duration.total_seconds() if avg_duration else 0
            
            # Datos para el gráfico (últimos 7 días)
            performance_data = []
            for i in range(7):
                day_start = timezone.now() - timezone.timedelta(days=i)
                day_end = day_start + timezone.timedelta(days=1)
                day_logs = recent_logs.filter(started_at__gte=day_start, started_at__lt=day_end)
                day_success = day_logs.filter(status='SUCCESS').count()
                day_total = day_logs.count()
                day_performance = (day_success / day_total * 100) if day_total > 0 else 0
                performance_data.insert(0, round(day_performance, 1))
            
            return {
                'stats': {
                    'success_count': success_logs,
                    'error_count': error_logs,
                    'running_count': running_logs,
                    'total_count': total_logs,
                    'success_rate': round(success_rate, 1),
                    'avg_duration': round(avg_duration_seconds, 1),
                },
                'performance_data': performance_data
            }
            
        except Exception as e:
            logger.error(f"Error calculando métricas: {e}")
            return {
                'stats': {
                    'success_count': 0,
                    'error_count': 0,
                    'running_count': 0,
                    'total_count': 0,
                    'success_rate': 0,
                    'avg_duration': 0,
                },
                'performance_data': [0, 0, 0, 0, 0, 0, 0]
            }

    def _get_system_status(self):
        """Obtener estado real del sistema"""
        try:
            config = AdministraNETConfig.objects.filter(is_active=True).first()
            
            # Test de conexión básico
            connection_status = False
            if config:
                try:
                    connection_service = AdministraNETConnectionService(config)
                    connection_status = connection_service.test_connection()
                except Exception as e:
                    logger.warning(f"Error testeando conexión: {e}")
            
            # Estado del servicio (simplificado - en producción podría verificar procesos reales)
            sync_service_running = config and config.is_active if config else False
            
            # Estado del logging
            logging_active = config and config.enable_logging if config else False
            
            return {
                'system_status': {
                    'database_connected': connection_status,
                    'sync_service_running': sync_service_running,
                    'logging_active': logging_active,
                }
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo estado del sistema: {e}")
            return {
                'system_status': {
                    'database_connected': False,
                    'sync_service_running': False,
                    'logging_active': False,
                }
            }


class TestConnectionView(CorePermissionRequiredMixin, TemplateView):
    """Vista para test de conexión AJAX"""
    permission_required = "core.can_manage_integrations"
    
    def post(self, request, *args, **kwargs):
        try:
            # Obtener datos de conexión del request
            host = request.POST.get('host')
            port = int(request.POST.get('port', 3306))
            database = request.POST.get('database')
            username = request.POST.get('username')
            password = request.POST.get('password')
            
            if not all([host, database, username, password]):
                return JsonResponse({
                    'success': False,
                    'message': _('Todos los campos de conexión son requeridos.')
                })
            
            # Crear configuración temporal para test
            temp_config = AdministraNETConfig(
                host=host,
                port=port,
                database_name=database,
                username=username,
                password=password
            )
            
            # Test de conexión
            connection_service = AdministraNETConnectionService(temp_config)
            connection_result = connection_service.test_connection()
            
            if connection_result:
                return JsonResponse({
                    'success': True,
                    'message': _('Conexión exitosa a la base de datos.')
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': _('No se pudo conectar a la base de datos.')
                })
                
        except Exception as e:
            logger.error(f"Error en test de conexión: {e}")
            return JsonResponse({
                'success': False,
                'message': _('Error interno durante el test de conexión.')
            })


class ExportConfigView(CorePermissionRequiredMixin, TemplateView):
    """Vista para exportar configuración"""
    permission_required = "core.can_manage_integrations"
    
    def get(self, request, *args, **kwargs):
        try:
            config = AdministraNETConfig.objects.filter(is_active=True).first()
            if not config:
                return JsonResponse({
                    'success': False,
                    'message': _('No hay configuración activa para exportar.')
                })
            
            # Preparar datos para exportación (sin contraseña por seguridad)
            export_data = {
                'host': config.host,
                'port': config.port,
                'database_name': config.database_name,
                'username': config.username,
                'is_active': config.is_active,
                'sync_interval': config.sync_interval,
                'enable_logging': config.enable_logging,
                'log_level': config.log_level,
                'max_retries': config.max_retries,
                'timeout_seconds': config.timeout_seconds,
                'batch_size': config.batch_size,
                'created_at': config.created_at.isoformat() if config.created_at else None,
                'updated_at': config.updated_at.isoformat() if config.updated_at else None,
                'last_sync': config.last_sync.isoformat() if config.last_sync else None,
            }
            
            # Crear respuesta JSON para descarga
            response = HttpResponse(
                json.dumps(export_data, indent=2, default=str),
                content_type='application/json'
            )
            response['Content-Disposition'] = f'attachment; filename="adminet_config_{timezone.now().strftime("%Y%m%d_%H%M%S")}.json"'
            
            return response
            
        except Exception as e:
            logger.error(f"Error exportando configuración: {e}")
            return JsonResponse({
                'success': False,
                'message': _('Error interno al exportar la configuración.')
            })


class ResetDefaultsView(CorePermissionRequiredMixin, TemplateView):
    """Vista para resetear a valores por defecto"""
    permission_required = "core.can_manage_integrations"
    
    def post(self, request, *args, **kwargs):
        try:
            config = AdministraNETConfig.objects.filter(is_active=True).first()
            if not config:
                config = AdministraNETConfig()
            
            # Resetear a valores por defecto
            config.sync_interval = 30
            config.is_active = False
            config.enable_logging = True
            config.log_level = 'INFO'
            config.max_retries = 3
            config.timeout_seconds = 300
            config.batch_size = 1000
            
            config.save()
            
            # Log de auditoría
            logger.info(f"[AUDITORÍA] Usuario {request.user} reseteó configuración a valores por defecto.")
            
            return JsonResponse({
                'success': True,
                'message': _('Configuración reseteada a valores por defecto.'),
                'config': {
                    'sync_interval': config.sync_interval,
                    'is_active': config.is_active,
                    'enable_logging': config.enable_logging,
                    'log_level': config.log_level,
                    'max_retries': config.max_retries,
                    'timeout_seconds': config.timeout_seconds,
                    'batch_size': config.batch_size,
                }
            })
            
        except Exception as e:
            logger.error(f"Error reseteando configuración: {e}")
            return JsonResponse({
                'success': False,
                'message': _('Error interno al resetear la configuración.')
            }) 