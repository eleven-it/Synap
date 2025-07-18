from django.views.generic import TemplateView
from core.utils.permissions import CorePermissionRequiredMixin
from administraNET_integration.models import TableMapping
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
import logging

logger = logging.getLogger(__name__)

# Vista de mapeos de tablas AdministraNET <-> Synap
class AdminetMappingsView(CorePermissionRequiredMixin, TemplateView):
    template_name = "administraNET_integration/mappings.html"
    permission_required = "core.can_edit_mappings"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        mappings = TableMapping.objects.filter(is_active=True).order_by('mapping_type')
        context['mappings'] = mappings
        return context

    def post(self, request, *args, **kwargs):
        if not request.user.has_perm('core.can_edit_mappings'):
            messages.error(request, "No tienes permisos para modificar mapeos.")
            return redirect(reverse('administraNET_integration:adminet_mappings'))
        if 'toggle_active' in request.POST:
            mapping_id = request.POST.get('mapping_id')
            mapping = TableMapping.objects.filter(pk=mapping_id).first()
            if mapping:
                mapping.is_active = not mapping.is_active
                mapping.save()
                logger.info(f"[AUDITORÍA] Usuario {request.user} {'activó' if mapping.is_active else 'desactivó'} el mapeo {mapping.pk} ({mapping.administraNET_table} → {mapping.synap_model})")
                messages.success(request, f"El mapeo {'activado' if mapping.is_active else 'desactivado'} correctamente.")
        return redirect(reverse('administraNET_integration:adminet_mappings')) 