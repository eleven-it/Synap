from django.views.generic import TemplateView
from core.utils.permissions import CorePermissionRequiredMixin
from administraNET_integration.models import SyncLog
from django.db.models import Q
from django.utils.dateparse import parse_date

# Vista de historial de sincronización AdministraNET <-> Synap
class AdminetSyncHistoryView(CorePermissionRequiredMixin, TemplateView):
    template_name = "administraNET_integration/sync_history.html"
    permission_required = "core.can_manage_integrations"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        logs = SyncLog.objects.all()
        # Filtros
        sync_type = self.request.GET.get('type')
        status = self.request.GET.get('status')
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        search = self.request.GET.get('search')
        if sync_type:
            logs = logs.filter(sync_type=sync_type)
        if status:
            logs = logs.filter(status=status)
        if date_from:
            logs = logs.filter(started_at__date__gte=parse_date(date_from))
        if date_to:
            logs = logs.filter(started_at__date__lte=parse_date(date_to))
        if search:
            logs = logs.filter(
                Q(details__icontains=search) |
                Q(error_message__icontains=search)
            )
        logs = logs.order_by('-started_at')[:100]
        context['logs'] = logs
        context['filter_type'] = sync_type or ''
        context['filter_status'] = status or ''
        context['filter_date_from'] = date_from or ''
        context['filter_date_to'] = date_to or ''
        context['filter_search'] = search or ''
        context['status_choices'] = SyncLog._meta.get_field('status').choices
        context['type_choices'] = SyncLog._meta.get_field('sync_type').choices
        return context 