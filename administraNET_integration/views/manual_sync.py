from django.views.generic import TemplateView
from django.http import JsonResponse
from django.shortcuts import redirect
from django.contrib import messages
from django.utils.translation import gettext as _
from django.core.exceptions import ValidationError
from django.db import transaction
from core.utils.permissions import CorePermissionRequiredMixin
from core.constantes_permisos import CAN_MANAGE_INTEGRATIONS
from administraNET_integration.models import AdministraNETConfig, SyncLog, TableMapping
from administraNET_integration.services.sync_service import AdministraNETSyncService
from administraNET_integration.services.connection_service import AdministraNETConnectionService
import logging
import json
from datetime import datetime
import traceback

logger = logging.getLogger(__name__)

class AdminetManualSyncView(CorePermissionRequiredMixin, TemplateView):
    """
    Vista de sincronización manual AdministraNET <-> Synap
    Permite ejecutar sincronizaciones manuales con diferentes tipos y opciones
    """
    template_name = "administraNET_integration/manual_sync.html"
    permission_required = CAN_MANAGE_INTEGRATIONS

    def get_context_data(self, **kwargs):
        """Obtener contexto con configuración y opciones de sincronización"""
        context = super().get_context_data(**kwargs)
        
        # Obtener configuración activa
        config = AdministraNETConfig.objects.filter(is_active=True).first()
        context['config'] = config
        
        # Verificar estado de conexión
        if config:
            try:
                connection_service = AdministraNETConnectionService(config)
                test_result = connection_service.test_connection(test_tables=False)
                context['connection_status'] = test_result.get('success', False)
                context['connection_error'] = test_result.get('error')
            except Exception as e:
                context['connection_status'] = False
                context['connection_error'] = str(e)
        
        # Obtener mapeos activos
        context['mappings'] = TableMapping.objects.filter(is_active=True).order_by('mapping_type')
        
        # Obtener últimas sincronizaciones
        context['recent_syncs'] = SyncLog.objects.all()[:5]
        
        # Estadísticas de sincronización
        context['total_syncs'] = SyncLog.objects.count()
        context['successful_syncs'] = SyncLog.objects.filter(status='SUCCESS').count()
        context['failed_syncs'] = SyncLog.objects.filter(status='ERROR').count()
        
        # Resultado de sincronización anterior
        context['sync_result'] = self.request.session.pop('sync_result', None)
        
        return context

    def post(self, request, *args, **kwargs):
        logger.info('--- [SYNC] Inicio de sincronización manual ---')
        try:
            logger.info('[SYNC] Validando permisos del usuario...')
            if not request.user.has_perm(CAN_MANAGE_INTEGRATIONS):
                logger.warning('[SYNC] Permisos insuficientes para sincronización manual.')
                messages.error(request, _("You don't have permission to execute manual synchronization."))
                return redirect('adminet:adminet_manual_sync')
            logger.info('[SYNC] Permisos OK.')

            logger.info('[SYNC] Buscando configuración activa...')
            config = AdministraNETConfig.objects.filter(is_active=True).first()
            if not config:
                logger.warning('[SYNC] No se encontró configuración activa.')
                messages.error(request, _("No active AdministraNET configuration found."))
                return redirect('adminet:adminet_manual_sync')
            logger.info(f'[SYNC] Configuración activa encontrada: {config}')

            logger.info('[SYNC] Obteniendo parámetros del formulario...')
            sync_type = request.POST.get('sync_type', 'FULL')
            mapping_id = request.POST.get('mapping_id')
            force_sync = request.POST.get('force_sync') == 'on'
            logger.info(f'[SYNC] sync_type={sync_type}, mapping_id={mapping_id}, force_sync={force_sync}')

            valid_sync_types = ['FULL', 'PRODUCTS', 'STOCK', 'CUSTOMERS', 'ORDERS']
            if sync_type not in valid_sync_types:
                logger.warning(f'[SYNC] Tipo de sincronización inválido: {sync_type}')
                raise ValidationError(_("Invalid synchronization type"))
            logger.info('[SYNC] Tipo de sincronización válido.')

            logger.info('[SYNC] Creando SyncLog...')
            sync_log = SyncLog.objects.create(
                sync_type=sync_type,
                status='RUNNING',
                initiated_by=request.user,
                error_details={
                    'manual': True,
                    'mapping_id': mapping_id,
                    'force_sync': force_sync
                }
            )
            logger.info(f'[SYNC] SyncLog creado: {sync_log.id}')

            logger.info('[SYNC] Instanciando servicio de sincronización...')
            sync_service = AdministraNETSyncService(config)

            logger.info('[SYNC] Ejecutando sincronización...')
            if mapping_id:
                try:
                    logger.info(f'[SYNC] Sincronización específica por mapeo: {mapping_id}')
                    mapping = TableMapping.objects.get(id=mapping_id, is_active=True)
                    result = sync_service.sync_by_type(mapping.mapping_type, sync_log)
                except TableMapping.DoesNotExist:
                    logger.warning(f'[SYNC] Mapping no encontrado o inactivo: {mapping_id}')
                    raise ValidationError(_("Selected mapping not found or inactive"))
            else:
                if sync_type == 'FULL':
                    logger.info('[SYNC] Sincronización FULL')
                    result = sync_service.sync_all(sync_log)
                else:
                    logger.info(f'[SYNC] Sincronización por tipo: {sync_type}')
                    result = sync_service.sync_by_type(sync_type, sync_log)
            logger.info(f'[SYNC] Resultado de sincronización: {result}')

            logger.info('[SYNC] Actualizando SyncLog con resultado...')
            success = result.get('success', False)
            sync_log.mark_completed(
                success=success,
                error_message=result.get('error') if not success else None
            )
            logger.info(f'[SYNC] SyncLog actualizado: status={sync_log.status}')

            if success:
                sync_log.records_processed = result.get('processed', 0)
                sync_log.records_created = result.get('created', 0)
                sync_log.records_updated = result.get('updated', 0)
                sync_log.records_failed = result.get('failed', 0)
                sync_log.save()
                logger.info(f'[SYNC] Contadores de SyncLog actualizados.')
                config.last_sync = sync_log.completed_at
                config.save()
                logger.info(f'[SYNC] Configuración actualizada con last_sync.')

            logger.info('[SYNC] Guardando resultado en sesión y mostrando mensaje al usuario.')
            request.session['sync_result'] = result
            if success:
                messages.success(request, _("Synchronization completed successfully!"))
            else:
                messages.error(request, _("Synchronization failed: ") + result.get('error', _('Unknown error')))
            logger.info('--- [SYNC] Fin de sincronización manual ---')
        except ValidationError as e:
            logger.error(f"[SYNC] Validation error in manual sync: {e}")
            messages.error(request, str(e))
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"[SYNC] Unexpected error in manual sync: {e}")
            logger.error(f"[SYNC] Error details: {error_details}")
            messages.error(request, _("Unexpected error during synchronization. Please try again."))
            if 'sync_log' in locals():
                sync_log.error_details = {'traceback': error_details, 'exception': str(e)}
                sync_log.mark_completed(success=False, error_message=f"Unexpected error: {str(e)}")
                sync_log.save()
        return redirect('adminet:adminet_manual_sync')

    def test_connection(self, request):
        """Endpoint para test de conexión via AJAX"""
        if request.method != 'POST':
            return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
        
        try:
            config = AdministraNETConfig.objects.filter(is_active=True).first()
            if not config:
                return JsonResponse({
                    'success': False,
                    'error': _('No active configuration found')
                })
            
            connection_service = AdministraNETConnectionService(config)
            result = connection_service.test_connection(test_tables=True)
            
            return JsonResponse(result)
            
        except Exception as e:
            logger.error(f"Error testing connection: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            })

    def get_sync_status(self, request):
        """Endpoint para obtener estado de sincronización actual"""
        try:
            # Buscar sincronización en progreso
            running_sync = SyncLog.objects.filter(status='RUNNING').first()
            
            if running_sync:
                return JsonResponse({
                    'success': True,
                    'running': True,
                    'sync_id': running_sync.id,
                    'sync_type': running_sync.get_sync_type_display(),
                    'started_at': running_sync.started_at.isoformat(),
                    'duration': str(running_sync.started_at - datetime.now().replace(tzinfo=running_sync.started_at.tzinfo))
                })
            else:
                return JsonResponse({
                    'success': True,
                    'running': False
                })
                
        except Exception as e:
            logger.error(f"Error getting sync status: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            })

    def cancel_sync(self, request):
        """Endpoint para cancelar sincronización en progreso"""
        if request.method != 'POST':
            return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
        
        try:
            running_sync = SyncLog.objects.filter(status='RUNNING').first()
            if running_sync:
                running_sync.status = 'CANCELLED'
                running_sync.completed_at = datetime.now()
                running_sync.save()
                
                logger.info(f"[AUDITORÍA] Usuario {request.user} canceló sincronización {running_sync.id}")
                
                return JsonResponse({
                    'success': True,
                    'message': _('Synchronization cancelled successfully')
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': _('No running synchronization found')
                })
                
        except Exception as e:
            logger.error(f"Error cancelling sync: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            })

    def dispatch(self, request, *args, **kwargs):
        """Manejar diferentes tipos de requests"""
        if request.path.endswith('/test-connection/'):
            return self.test_connection(request)
        elif request.path.endswith('/sync-status/'):
            return self.get_sync_status(request)
        elif request.path.endswith('/cancel-sync/'):
            return self.cancel_sync(request)
        return super().dispatch(request, *args, **kwargs) 