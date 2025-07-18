from django.views.generic import TemplateView
from django.shortcuts import redirect
from django.http import JsonResponse
from django.contrib import messages
from django.utils.translation import gettext as _
from django.core.exceptions import ValidationError
from django.db import transaction
from administraNET_integration.models import AdministraNETConfig
from administraNET_integration.services.connection_service import AdministraNETConnectionService
from core.utils.permissions import CorePermissionRequiredMixin
from core.constantes_permisos import CAN_CONFIGURE_INTEGRATIONS
import logging
import json

logger = logging.getLogger(__name__)

class AdminetConnectionView(CorePermissionRequiredMixin, TemplateView):
    """
    Vista de configuración de conexión a AdministraNET
    Maneja la configuración de conexión, test de conectividad y validaciones
    """
    template_name = "administraNET_integration/connection.html"
    permission_required = CAN_CONFIGURE_INTEGRATIONS

    def get_context_data(self, **kwargs):
        """Obtener contexto con configuración actual y estadísticas"""
        context = super().get_context_data(**kwargs)
        
        # Obtener configuración activa
        config = AdministraNETConfig.objects.filter(is_active=True).first()
        context['config'] = config
        
        # Información de conexión si existe
        if config:
            try:
                service = AdministraNETConnectionService(config)
                test_result = service.test_connection(test_tables=False)
                context['connection_status'] = test_result.get('success', False)
                context['connection_error'] = test_result.get('error')
                context['database_info'] = test_result.get('database_info', {})
                context['version_info'] = test_result.get('version')
            except Exception as e:
                context['connection_status'] = False
                context['connection_error'] = str(e)
                logger.error(f"Error testing connection: {e}")
        
        # Estadísticas de configuración
        context['total_configs'] = AdministraNETConfig.objects.count()
        context['active_configs'] = AdministraNETConfig.objects.filter(is_active=True).count()
        
        return context

    def post(self, request, *args, **kwargs):
        """Procesar formulario de configuración de conexión"""
        try:
            with transaction.atomic():
                # Obtener o crear configuración
                config = AdministraNETConfig.objects.filter(is_active=True).first()
                if not config:
                    config = AdministraNETConfig(is_active=True)
                
                # Guardar valores anteriores para auditoría
                old_values = {
                    'host': config.host,
                    'port': config.port,
                    'database_name': config.database_name,
                    'username': config.username,
                }
                
                # Validar y actualizar campos
                host = request.POST.get('host', '').strip()
                port = request.POST.get('port', '3306').strip()
                database_name = request.POST.get('database_name', '').strip()
                username = request.POST.get('user', '').strip()
                password = request.POST.get('password', '')
                
                # Validaciones básicas
                if not host:
                    raise ValidationError(_("Host is required"))
                if not database_name:
                    raise ValidationError(_("Database name is required"))
                if not username:
                    raise ValidationError(_("Username is required"))
                
                try:
                    port = int(port)
                    if port < 1 or port > 65535:
                        raise ValueError()
                except ValueError:
                    raise ValidationError(_("Port must be a number between 1 and 65535"))
                
                # Actualizar configuración
                config.host = host
                config.port = port
                config.database_name = database_name
                config.username = username
                
                # Solo actualizar contraseña si se proporcionó una nueva
                if password:
                    config.password = password
                
                config.save()
                
                # Registrar auditoría
                new_values = {
                    'host': config.host,
                    'port': config.port,
                    'database_name': config.database_name,
                    'username': config.username,
                }
                
                logger.info(
                    f"[AUDITORÍA] Usuario {request.user} modificó configuración de conexión. "
                    f"Antes: {old_values} Después: {new_values}"
                )
                
                messages.success(request, _("Connection configuration saved successfully."))
                
        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            logger.error(f"Error saving connection configuration: {e}")
            messages.error(request, _("Error saving configuration. Please try again."))
        
        return redirect('adminet:adminet_connection')

    def test_connection(self, request):
        """Endpoint para test de conexión via AJAX"""
        if request.method != 'POST':
            return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
        
        try:
            # Obtener configuración actual
            config = AdministraNETConfig.objects.filter(is_active=True).first()
            if not config:
                return JsonResponse({
                    'success': False, 
                    'error': _('No active configuration found')
                })
            
            # Test de conexión
            service = AdministraNETConnectionService(config)
            result = service.test_connection(test_tables=True)
            
            if result['success']:
                return JsonResponse({
                    'success': True,
                    'message': _('Connection successful'),
                    'database_info': result.get('database_info', {}),
                    'version': result.get('version'),
                    'tables_count': result.get('tables_count', 0)
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': result.get('error', _('Connection failed'))
                })
                
        except Exception as e:
            logger.error(f"Error testing connection: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            })

    def get_connection_info(self, request):
        """Endpoint para obtener información de conexión"""
        try:
            config = AdministraNETConfig.objects.filter(is_active=True).first()
            if not config:
                return JsonResponse({
                    'success': False,
                    'error': _('No active configuration found')
                })
            
            # Obtener información de conexión
            service = AdministraNETConnectionService(config)
            result = service.test_connection(test_tables=False)
            
            return JsonResponse({
                'success': True,
                'connection_string': config.get_connection_string(),
                'database_info': result.get('database_info', {}),
                'version': result.get('version'),
                'last_sync': config.last_sync.isoformat() if config.last_sync else None,
                'is_active': config.is_active
            })
            
        except Exception as e:
            logger.error(f"Error getting connection info: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            })

    def dispatch(self, request, *args, **kwargs):
        """Manejar diferentes tipos de requests"""
        if request.path.endswith('/test-connection/'):
            return self.test_connection(request)
        elif request.path.endswith('/connection-info/'):
            return self.get_connection_info(request)
        return super().dispatch(request, *args, **kwargs) 