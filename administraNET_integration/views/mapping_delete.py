from django.views.generic.edit import DeleteView
from core.utils.permissions import CorePermissionRequiredMixin
from django.urls import reverse_lazy
from administraNET_integration.models import TableMapping
import logging

logger = logging.getLogger(__name__)

class AdminetMappingDeleteView(CorePermissionRequiredMixin, DeleteView):
    model = TableMapping
    template_name = "administraNET_integration/mapping_confirm_delete.html"
    success_url = reverse_lazy('administraNET_integration:adminet_mappings')
    permission_required = "core.can_edit_mappings"

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        logger.info(f"[AUDITORÍA] Usuario {request.user} eliminó el mapeo {obj.pk} ({obj.administraNET_table} → {obj.synap_model})")
        return super().delete(request, *args, **kwargs) 