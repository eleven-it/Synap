from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy
from django.shortcuts import redirect, render
from django.contrib import messages
from django.db.models import Q, Count, Sum
from django.utils.translation import gettext_lazy as _
from django.http import JsonResponse

from ..models import Journal, JournalTypes
from ..forms import JournalForm
from core.decorators import tiene_permiso


class JournalListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Lista de diarios contables con filtros y búsqueda"""
    model = Journal
    template_name = 'accounting/journals/journal_list.html'
    context_object_name = 'journals'
    permission_required = 'accounting.view_journal'
    paginate_by = 20

    def get_queryset(self):
        """Filtrar por empresa del usuario y aplicar búsqueda"""
        queryset = Journal.objects.filter(
            empresa=self.request.user.empresa_activa
        ).select_related('default_account', 'tax_account')
        
        # Búsqueda
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(code__icontains=search) |
                Q(default_account__name__icontains=search)
            )
        
        # Filtro por tipo de diario
        journal_type = self.request.GET.get('journal_type', '')
        if journal_type:
            queryset = queryset.filter(journal_type=journal_type)
        
        # Filtro por estado
        is_active = self.request.GET.get('is_active', '')
        if is_active != '':
            queryset = queryset.filter(is_active=is_active == 'true')
        
        return queryset.order_by('code')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        empresa = self.request.user.empresa_activa
        
        # Estadísticas
        total_journals = Journal.objects.filter(empresa=empresa).count()
        active_journals = Journal.objects.filter(empresa=empresa, is_active=True).count()
        inactive_journals = Journal.objects.filter(empresa=empresa, is_active=False).count()
        
        # Diarios por tipo
        journals_by_type = Journal.objects.filter(empresa=empresa).values(
            'journal_type'
        ).annotate(
            count=Count('id')
        ).order_by('journal_type')
        
        # Contar entradas por diario
        for journal in context['journals']:
            journal.entries_count = journal.entries.count()
            journal.posted_entries_count = journal.entries.filter(state='posted').count()
        
        context.update({
            'search': self.request.GET.get('search', ''),
            'journal_type_filter': self.request.GET.get('journal_type', ''),
            'is_active_filter': self.request.GET.get('is_active', ''),
            'total_journals': total_journals,
            'active_journals': active_journals,
            'inactive_journals': inactive_journals,
            'journals_by_type': journals_by_type,
            'journal_types': JournalTypes.CHOICES,
        })
        return context


class JournalCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Crear nuevo diario contable"""
    model = Journal
    form_class = JournalForm
    template_name = 'accounting/journals/journal_form.html'
    permission_required = 'accounting.add_journal'
    success_url = reverse_lazy('accounting:journal_list')

    def form_valid(self, form):
        """Asignar empresa automáticamente"""
        form.instance.empresa = self.request.user.empresa_activa
        response = super().form_valid(form)
        messages.success(self.request, _('Journal created successfully.'))
        return response

    def get_form_kwargs(self):
        """Pasar empresa al formulario"""
        kwargs = super().get_form_kwargs()
        kwargs['empresa'] = self.request.user.empresa_activa
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = _('Create Journal')
        context['submit_text'] = _('Create Journal')
        return context


class JournalUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Editar diario contable"""
    model = Journal
    form_class = JournalForm
    template_name = 'accounting/journals/journal_form.html'
    permission_required = 'accounting.change_journal'
    success_url = reverse_lazy('accounting:journal_list')

    def get_queryset(self):
        """Filtrar por empresa del usuario"""
        return Journal.objects.filter(empresa=self.request.user.empresa_activa)

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _('Journal updated successfully.'))
        return response

    def get_form_kwargs(self):
        """Pasar empresa al formulario"""
        kwargs = super().get_form_kwargs()
        kwargs['empresa'] = self.request.user.empresa_activa
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = _('Edit Journal')
        context['submit_text'] = _('Update Journal')
        return context


class JournalDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """Eliminar diario contable"""
    model = Journal
    template_name = 'accounting/journals/journal_confirm_delete.html'
    permission_required = 'accounting.delete_journal'
    success_url = reverse_lazy('accounting:journal_list')

    def get_queryset(self):
        """Filtrar por empresa del usuario"""
        return Journal.objects.filter(empresa=self.request.user.empresa_activa)

    def delete(self, request, *args, **kwargs):
        """Verificar que no tenga entradas"""
        journal = self.get_object()
        
        # Verificar entradas
        if journal.entries.exists():
            messages.error(
                request, 
                _('Cannot delete journal. It has journal entries.')
            )
            return redirect('accounting:journal_list')
        
        response = super().delete(request, *args, **kwargs)
        messages.success(request, _('Journal deleted successfully.'))
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = _('Confirm Journal Deletion')
        return context


class JournalDetailView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Detalle de diario contable con entradas"""
    model = Journal
    template_name = 'accounting/journals/journal_detail.html'
    context_object_name = 'journal'
    permission_required = 'accounting.view_journal'
    paginate_by = 20

    def get_queryset(self):
        """Obtener el diario específico"""
        return Journal.objects.filter(
            pk=self.kwargs['pk'],
            empresa=self.request.user.empresa_activa
        ).select_related('default_account', 'tax_account')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        journal = self.get_queryset().first()
        
        if not journal:
            messages.error(self.request, _('Journal not found.'))
            return context
        
        # Obtener entradas del diario
        entries = journal.entries.select_related(
            'created_by', 'posted_by'
        ).order_by('-date', '-created_at')
        
        # Paginar entradas
        from django.core.paginator import Paginator
        paginator = Paginator(entries, self.paginate_by)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        # Estadísticas del diario
        total_entries = entries.count()
        draft_entries = entries.filter(state='draft').count()
        posted_entries = entries.filter(state='posted').count()
        cancelled_entries = entries.filter(state='cancelled').count()
        
        # Totales de débito y crédito
        total_debit = entries.aggregate(
            total=Sum('lines__debit')
        )['total'] or 0
        total_credit = entries.aggregate(
            total=Sum('lines__credit')
        )['total'] or 0
        
        context.update({
            'journal': journal,
            'entries': page_obj,
            'total_entries': total_entries,
            'draft_entries': draft_entries,
            'posted_entries': posted_entries,
            'cancelled_entries': cancelled_entries,
            'total_debit': total_debit,
            'total_credit': total_credit,
            'balance': total_debit - total_credit,
        })
        return context


@tiene_permiso('accounting.change_journal')
def toggle_journal_status(request, pk):
    """Activar/desactivar diario contable"""
    try:
        journal = Journal.objects.get(
            pk=pk, 
            empresa=request.user.empresa_activa
        )
        journal.is_active = not journal.is_active
        journal.save()
        
        status = 'activated' if journal.is_active else 'deactivated'
        messages.success(
            request, 
            _('Journal {} successfully.').format(status)
        )
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'is_active': journal.is_active,
                'message': _('Journal {} successfully.').format(status)
            })
        
    except Journal.DoesNotExist:
        messages.error(request, _('Journal not found.'))
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': _('Journal not found.')
            })
    
    return redirect('accounting:journal_list')


@tiene_permiso('accounting.view_journal')
def journal_dashboard(request):
    """Dashboard de diarios contables"""
    empresa = request.user.empresa_activa
    
    # Obtener todos los diarios con estadísticas
    journals = Journal.objects.filter(empresa=empresa).select_related(
        'default_account', 'tax_account'
    ).annotate(
        total_entries=Count('entries'),
        draft_entries=Count('entries', filter=Q(entries__state='draft')),
        posted_entries=Count('entries', filter=Q(entries__state='posted')),
        cancelled_entries=Count('entries', filter=Q(entries__state='cancelled')),
    ).order_by('code')
    
    # Estadísticas generales
    total_journals = journals.count()
    active_journals = journals.filter(is_active=True).count()
    total_entries = sum(j.total_entries for j in journals)
    total_posted_entries = sum(j.posted_entries for j in journals)
    
    # Diarios por tipo
    journals_by_type = {}
    for journal_type, label in JournalTypes.CHOICES:
        type_journals = journals.filter(journal_type=journal_type)
        journals_by_type[journal_type] = {
            'label': label,
            'journals': type_journals,
            'count': type_journals.count(),
            'total_entries': sum(j.total_entries for j in type_journals),
        }
    
    context = {
        'journals': journals,
        'total_journals': total_journals,
        'active_journals': active_journals,
        'total_entries': total_entries,
        'total_posted_entries': total_posted_entries,
        'journals_by_type': journals_by_type,
        'journal_types': JournalTypes.CHOICES,
    }
    
    return render(request, 'accounting/journals/journal_dashboard.html', context) 