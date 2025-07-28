from django.views.generic import TemplateView
from django.shortcuts import redirect
from django.http import JsonResponse
from django.contrib import messages
from django.utils.translation import gettext as _
from django.core.exceptions import ValidationError
from django.db import transaction
from core.utils.permissions import CorePermissionRequiredMixin
from core.constantes_permisos import CAN_CONFIGURE_INTEGRATIONS
from .services.connection_service import MySQLConnectionService
from tiendanube.models_adminet import TiendaNubeAdminetConfig
import logging

logger = logging.getLogger(__name__)

# Puedes definir un modelo TiendaNubeAdminetConfig o usar settings para la config
class TiendaNubeAdminetConnectionView(CorePermissionRequiredMixin, TemplateView):
    template_name = "tiendanube_adminet/connection.html"
    permission_required = CAN_CONFIGURE_INTEGRATIONS

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        config = self.get_active_config()
        context['config'] = config
        if config:
            try:
                service = MySQLConnectionService(config)
                test_result = service.test_connection(test_tables=False)
                context['connection_status'] = test_result.get('success', False)
                context['connection_error'] = test_result.get('error')
                context['database_info'] = test_result.get('database_info', {})
                context['version_info'] = test_result.get('version')
            except Exception as e:
                context['connection_status'] = False
                context['connection_error'] = str(e)
                logger.error(f"Error testing connection: {e}")
        return context

    def post(self, request, *args, **kwargs):
        try:
            with transaction.atomic():
                # Desactivar otras configuraciones activas
                TiendaNubeAdminetConfig.objects.filter(is_active=True).update(is_active=False)
                # Guardar nueva configuración
                config = TiendaNubeAdminetConfig(
                    host=request.POST.get('host', '').strip(),
                    port=int(request.POST.get('port', 3306)),
                    database=request.POST.get('database_name', '').strip(),
                    user=request.POST.get('user', '').strip(),
                    password=request.POST.get('password', ''),
                    is_active=True
                )
                config.save()
                messages.success(request, _("Connection configuration saved successfully."))
        except ValidationError as e:
            messages.error(request, str(e))
        except Exception as e:
            logger.error(f"Error saving connection configuration: {e}")
            messages.error(request, _( "Error saving configuration. Please try again."))
        return redirect('tiendanube:adminet_connection')

    def test_connection(self, request):
        if request.method != 'POST':
            return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
        try:
            config = self.get_active_config()
            if not config:
                return JsonResponse({'success': False, 'error': _('No active configuration found')})
            service = MySQLConnectionService(config)
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
                return JsonResponse({'success': False, 'error': result.get('error', _('Connection failed'))})
        except Exception as e:
            logger.error(f"Error testing connection: {e}")
            return JsonResponse({'success': False, 'error': str(e)})

    def dispatch(self, request, *args, **kwargs):
        if request.path.endswith('/test-connection/'):
            return self.test_connection(request)
        return super().dispatch(request, *args, **kwargs)

    def get_active_config(self):
        config = TiendaNubeAdminetConfig.objects.filter(is_active=True).first()
        if config:
            return {
                'host': config.host,
                'port': config.port,
                'database': config.database,
                'user': config.user,
                'password': config.password,
            }
        return None 