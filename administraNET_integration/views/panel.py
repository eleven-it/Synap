from django.views.generic import TemplateView
from core.utils.permissions import CorePermissionRequiredMixin
from administraNET_integration.models import AdministraNETConfig
from administraNET_integration.services.connection_service import AdministraNETConnectionService
from inventory.models import Product
from sales.models import Client
from django.utils import timezone

# Vista principal del panel de integración AdministraNET
class AdminetPanelView(CorePermissionRequiredMixin, TemplateView):
    template_name = "administraNET_integration/panel.html"
    permission_required = "core.can_manage_integrations"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Obtener configuración activa
        config = AdministraNETConfig.objects.filter(is_active=True).first()
        context['config'] = config
        context['connection_status'] = None
        context['connection_error'] = None
        context['last_sync'] = config.last_sync if config else None
        # Métricas Synap
        context['products_count'] = Product.objects.count()
        context['clients_count'] = Client.objects.count()
        # Probar conexión a AdministraNET
        if config:
            try:
                service = AdministraNETConnectionService(config)
                test_result = service.test_connection(test_tables=False)
                context['connection_status'] = test_result['success']
                context['connection_error'] = test_result['error'] if not test_result['success'] else None
                context['adminet_db_name'] = test_result['database_info'].get('name')
                context['adminet_db_version'] = test_result['version']
            except Exception as e:
                context['connection_status'] = False
                context['connection_error'] = str(e)
        else:
            context['connection_status'] = False
            context['connection_error'] = 'No hay configuración activa.'
        return context 