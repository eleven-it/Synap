from django.views.generic.edit import FormView
from core.utils.permissions import CorePermissionRequiredMixin
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404
from administraNET_integration.models import TableMapping
from administraNET_integration.forms import TableMappingForm
import logging

logger = logging.getLogger(__name__)

class AdminetMappingEditView(CorePermissionRequiredMixin, FormView):
    template_name = "administraNET_integration/mapping_edit.html"
    form_class = TableMappingForm
    success_url = reverse_lazy('administraNET_integration:adminet_mappings')
    permission_required = "core.can_edit_mappings"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        pk = self.kwargs.get('pk')
        if pk:
            mapping = get_object_or_404(TableMapping, pk=pk)
            kwargs['instance'] = mapping
        return kwargs

    def form_valid(self, form):
        instance = form.save(commit=False)
        exists = TableMapping.objects.filter(
            administraNET_table=instance.administraNET_table,
            synap_model=instance.synap_model
        ).exclude(pk=instance.pk).exists()
        if exists:
            form.add_error('administraNET_table', 'Ya existe un mapeo para esta tabla y modelo.')
            return self.form_invalid(form)
        is_new = instance.pk is None
        instance.save()
        logger.info(f"[AUDITORÍA] Usuario {self.request.user} {'creó' if is_new else 'editó'} el mapeo {instance.pk} ({instance.administraNET_table} → {instance.synap_model})")
        return super().form_valid(form) 