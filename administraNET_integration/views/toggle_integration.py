from django.views.generic import TemplateView
from django.http import JsonResponse
from django.contrib import messages
from django.utils import timezone
from django.utils.translation import gettext as _
from core.utils.permissions import CorePermissionRequiredMixin
from administraNET_integration.models import AdministraNETConfig
from administraNET_integration.services.connection_service import AdministraNETConnectionService
import logging

logger = logging.getLogger(__name__)

class ToggleIntegrationView(CorePermissionRequiredMixin, TemplateView):
    """
    Vista para activar/desactivar la integración con administraNET
    Incluye validaciones, confirmaciones y logging completo
    """
    template_name = "administraNET_integration/toggle_integration.html"
    permission_required = "core.can_manage_integrations"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener configuración actual
        config = AdministraNETConfig.objects.filter(is_active=True).first()
        context['config'] = config
        
        # Estado actual de la integración
        context['integration_status'] = {
            'is_active': config.is_active if config else False,
            'last_sync': config.last_sync if config else None,
            'sync_interval': config.sync_interval if config else 30,
            'enable_logging': config.enable_logging if config else True,
            'log_level': config.log_level if config else 'INFO'
        }
        
        # Estadísticas de sincronización
        context['sync_stats'] = self._get_sync_statistics()
        
        # Estado del sistema
        context['system_status'] = self._get_system_status()
        
        # Historial de cambios de estado
        context['status_history'] = self._get_status_history()
        
        return context

    def post(self, request, *args, **kwargs):
        """Manejar activación/desactivación de integración"""
        if not request.user.has_perm('core.can_manage_integrations'):
            return JsonResponse({
                'success': False,
                'message': _("No tienes permisos para esta acción.")
            })
        
        action = request.POST.get('action')
        force = request.POST.get('force', 'false').lower() == 'true'
        
        if action not in ['activate', 'deactivate']:
            return JsonResponse({
                'success': False,
                'message': _("Acción no válida.")
            })
        
        try:
            config = AdministraNETConfig.objects.filter(is_active=True).first()
            
            if action == 'activate':
                result = self._activate_integration(config, force)
            else:
                result = self._deactivate_integration(config, force)
            
            # Log de auditoría
            logger.info(f"[AUDITORÍA] Usuario {request.user} {action}d integración administraNET. "
                       f"Forzado: {force}, Resultado: {'Exitoso' if result['success'] else 'Fallido'}")
            
            return JsonResponse(result)
            
        except Exception as e:
            logger.error(f"Error en toggle de integración: {e}")
            return JsonResponse({
                'success': False,
                'message': _("Error interno durante la operación."),
                'error': str(e)
            })

    def _activate_integration(self, config, force=False):
        """Activar la integración"""
        try:
            # Verificar si ya hay una configuración activa
            if config and config.is_active and not force:
                return {
                    'success': False,
                    'message': _("La integración ya está activa."),
                    'current_status': True
                }
            
            # Si no hay configuración, crear una por defecto
            if not config:
                config = AdministraNETConfig.objects.create(
                    host='localhost',
                    port=3306,
                    database_name='administranet',
                    username='root',
                    password='',
                    is_active=True,
                    sync_interval=30,
                    enable_logging=True,
                    log_level='INFO'
                )
            else:
                config.is_active = True
                config.save()
            
            # Test de conexión antes de activar (si no es forzado)
            if not force:
                connection_service = AdministraNETConnectionService(config)
                test_result = connection_service.test_connection()
                
                if not test_result.get('success', False):
                    config.is_active = False
                    config.save()
                    
                    return {
                        'success': False,
                        'message': _("No se pudo activar la integración. Error de conexión: ") + test_result.get('message', ''),
                        'connection_error': True,
                        'test_result': test_result
                    }
            
            return {
                'success': True,
                'message': _("Integración activada exitosamente."),
                'new_status': True,
                'config_id': config.id
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': _("Error al activar la integración."),
                'error': str(e)
            }

    def _deactivate_integration(self, config, force=False):
        """Desactivar la integración"""
        try:
            if not config:
                return {
                    'success': False,
                    'message': _("No hay configuración de integración activa."),
                    'current_status': False
                }
            
            if not config.is_active and not force:
                return {
                    'success': False,
                    'message': _("La integración ya está desactivada."),
                    'current_status': False
                }
            
            # Verificar si hay sincronizaciones en curso
            if not force:
                from administraNET_integration.models import SyncLog
                running_syncs = SyncLog.objects.filter(status='RUNNING').count()
                
                if running_syncs > 0:
                    return {
                        'success': False,
                        'message': _("No se puede desactivar. Hay {} sincronizaciones en curso.").format(running_syncs),
                        'running_syncs': running_syncs
                    }
            
            # Desactivar integración
            config.is_active = False
            config.save()
            
            return {
                'success': True,
                'message': _("Integración desactivada exitosamente."),
                'new_status': False
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': _("Error al desactivar la integración."),
                'error': str(e)
            }

    def _get_sync_statistics(self):
        """Obtener estadísticas de sincronización"""
        try:
            from administraNET_integration.models import SyncLog
            
            # Estadísticas de los últimos 30 días
            thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
            recent_logs = SyncLog.objects.filter(started_at__gte=thirty_days_ago)
            
            total_syncs = recent_logs.count()
            successful_syncs = recent_logs.filter(status='SUCCESS').count()
            failed_syncs = recent_logs.filter(status='ERROR').count()
            running_syncs = recent_logs.filter(status='RUNNING').count()
            
            # Calcular tasa de éxito
            success_rate = (successful_syncs / total_syncs * 100) if total_syncs > 0 else 0
            
            # Última sincronización
            last_sync = recent_logs.order_by('-started_at').first()
            
            return {
                'total_syncs': total_syncs,
                'successful_syncs': successful_syncs,
                'failed_syncs': failed_syncs,
                'running_syncs': running_syncs,
                'success_rate': round(success_rate, 1),
                'last_sync': last_sync,
                'period_days': 30
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {e}")
            return {
                'total_syncs': 0,
                'successful_syncs': 0,
                'failed_syncs': 0,
                'running_syncs': 0,
                'success_rate': 0,
                'last_sync': None,
                'period_days': 30
            }

    def _get_system_status(self):
        """Obtener estado del sistema"""
        try:
            config = AdministraNETConfig.objects.filter(is_active=True).first()
            
            # Test de conexión
            connection_status = False
            if config:
                try:
                    connection_service = AdministraNETConnectionService(config)
                    connection_status = connection_service.test_connection()
                except Exception as e:
                    logger.warning(f"Error testeando conexión: {e}")
            
            return {
                'database_connected': connection_status,
                'sync_service_running': config and config.is_active if config else False,
                'logging_active': config and config.enable_logging if config else False,
                'config_exists': config is not None
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo estado del sistema: {e}")
            return {
                'database_connected': False,
                'sync_service_running': False,
                'logging_active': False,
                'config_exists': False
            }

    def _get_status_history(self):
        """Obtener historial de cambios de estado"""
        # En una implementación real, esto vendría de un modelo de logs
        # Por ahora retornamos datos de ejemplo
        return [
            {
                'timestamp': '2024-01-15 14:30:00',
                'action': 'activated',
                'user': 'admin',
                'reason': 'Manual activation'
            },
            {
                'timestamp': '2024-01-15 10:15:00',
                'action': 'deactivated',
                'user': 'admin',
                'reason': 'Maintenance'
            },
            {
                'timestamp': '2024-01-14 16:45:00',
                'action': 'activated',
                'user': 'admin',
                'reason': 'Configuration updated'
            }
        ]


class IntegrationStatusView(CorePermissionRequiredMixin, TemplateView):
    """Vista para obtener estado actual de la integración"""
    permission_required = "core.can_manage_integrations"
    
    def get(self, request, *args, **kwargs):
        try:
            config = AdministraNETConfig.objects.filter(is_active=True).first()
            
            status_data = {
                'is_active': config.is_active if config else False,
                'config_exists': config is not None,
                'last_sync': config.last_sync.isoformat() if config and config.last_sync else None,
                'sync_interval': config.sync_interval if config else 30,
                'enable_logging': config.enable_logging if config else False,
                'log_level': config.log_level if config else 'INFO'
            }
            
            return JsonResponse({
                'success': True,
                'status': status_data
            })
            
        except Exception as e:
            logger.error(f"Error obteniendo estado: {e}")
            return JsonResponse({
                'success': False,
                'message': _("Error obteniendo estado de la integración."),
                'error': str(e)
            })


class ForceToggleView(CorePermissionRequiredMixin, TemplateView):
    """Vista para forzar activación/desactivación"""
    permission_required = "core.can_manage_integrations"
    
    def post(self, request, *args, **kwargs):
        if not request.user.has_perm('core.can_manage_integrations'):
            return JsonResponse({
                'success': False,
                'message': _("No tienes permisos para esta acción.")
            })
        
        action = request.POST.get('action')
        
        try:
            config = AdministraNETConfig.objects.filter(is_active=True).first()
            
            if action == 'activate':
                result = self._activate_integration(config, force=True)
            elif action == 'deactivate':
                result = self._deactivate_integration(config, force=True)
            else:
                return JsonResponse({
                    'success': False,
                    'message': _("Acción no válida.")
                })
            
            # Log de auditoría
            logger.warning(f"[AUDITORÍA] Usuario {request.user} forzó {action} de integración administraNET.")
            
            return JsonResponse(result)
            
        except Exception as e:
            logger.error(f"Error en force toggle: {e}")
            return JsonResponse({
                'success': False,
                'message': _("Error interno durante la operación forzada."),
                'error': str(e)
            })

    def _activate_integration(self, config, force=True):
        """Activar integración forzadamente"""
        try:
            if not config:
                config = AdministraNETConfig.objects.create(
                    host='localhost',
                    port=3306,
                    database_name='administranet',
                    username='root',
                    password='',
                    is_active=True,
                    sync_interval=30,
                    enable_logging=True,
                    log_level='INFO'
                )
            else:
                config.is_active = True
                config.save()
            
            return {
                'success': True,
                'message': _("Integración activada forzadamente."),
                'new_status': True,
                'forced': True
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': _("Error al activar la integración."),
                'error': str(e)
            }

    def _deactivate_integration(self, config, force=True):
        """Desactivar integración forzadamente"""
        try:
            if not config:
                return {
                    'success': False,
                    'message': _("No hay configuración de integración."),
                    'current_status': False
                }
            
            config.is_active = False
            config.save()
            
            return {
                'success': True,
                'message': _("Integración desactivada forzadamente."),
                'new_status': False,
                'forced': True
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': _("Error al desactivar la integración."),
                'error': str(e)
            } 