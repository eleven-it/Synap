from django.views.generic.detail import DetailView
from core.utils.permissions import CorePermissionRequiredMixin
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages
from administraNET_integration.models import SyncLog, AdministraNETConfig
from administraNET_integration.services.sync_service import AdministraNETSyncService
import logging

logger = logging.getLogger(__name__)

class AdminetSyncLogDetailView(CorePermissionRequiredMixin, DetailView):
    model = SyncLog
    template_name = "administraNET_integration/sync_log_detail.html"
    context_object_name = "log"
    permission_required = "core.can_manage_integrations"

    def post(self, request, *args, **kwargs):
        if not request.user.has_perm('core.can_manage_integrations'):
            messages.error(request, "No tienes permisos para esta acción.")
            return HttpResponseRedirect(request.path)
        log = self.get_object()
        action = request.POST.get('action')
        if action == 'retry':
            config = AdministraNETConfig.objects.filter(is_active=True).first()
            if not config:
                messages.error(request, "No hay configuración activa de AdministraNET.")
                return HttpResponseRedirect(request.path)
            sync_service = AdministraNETSyncService(config)
            result = sync_service.sync_all(log)
            log.status = 'SUCCESS' if result.get('success') else 'ERROR'
            log.details = result.get('message', '')
            log.save()
            logger.info(f"[AUDITORÍA] Usuario {request.user} reintentó sincronización desde log {log.pk}. Resultado: {'Éxito' if result.get('success') else 'Error'} - {result.get('message','')} ")
            messages.success(request, "Sincronización reintentada.")
            return HttpResponseRedirect(request.path)
        elif action == 'download':
            content = f"Fecha: {log.created_at}\nTipo: {log.sync_type}\nEstado: {log.status}\nDetalles: {log.details}\nMensaje: {log.message}\nProcesados: {log.processed}\nCreados: {log.created}\nActualizados: {log.updated}\nFallidos: {log.failed}\nError: {log.error}"
            response = HttpResponse(content, content_type='text/plain')
            response['Content-Disposition'] = f'attachment; filename=sync_log_{log.pk}.txt'
            return response
        return HttpResponseRedirect(request.path) 