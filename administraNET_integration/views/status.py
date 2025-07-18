from django.views.generic import TemplateView
from administraNET_integration.models import AdministraNETConfig
from administraNET_integration.services.connection_service import AdministraNETConnectionService

# Vista de estado de integración AdministraNET
class AdminetStatusView(TemplateView):
    template_name = "administraNET_integration/status.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        config = AdministraNETConfig.objects.filter(is_active=True).first()
        context['config'] = config
        context['connection_status'] = None
        context['connection_error'] = None
        context['db_version'] = None
        context['db_name'] = None
        context['db_tables'] = None
        context['db_size'] = None
        if config:
            try:
                service = AdministraNETConnectionService(config)
                test_result = service.test_connection(test_tables=True)
                context['connection_status'] = test_result['success']
                context['connection_error'] = test_result['error'] if not test_result['success'] else None
                context['db_version'] = test_result['version']
                context['db_name'] = test_result['database_info'].get('name')
                context['db_tables'] = test_result['database_info'].get('total_tables')
                context['db_size'] = test_result['database_info'].get('size_mb')
            except Exception as e:
                context['connection_status'] = False
                context['connection_error'] = str(e)
        else:
            context['connection_status'] = False
            context['connection_error'] = 'No hay configuración activa.'
        return context 