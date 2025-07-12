from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib import messages
from django.db.models import Q, Count, Sum, F
from django.utils.translation import gettext_lazy as _
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from decimal import Decimal
import json

from ..models import JournalEntry, JournalEntryLine, Journal, ChartOfAccounts, EntryStates
from ..forms import JournalEntryForm, JournalEntryLineFormSet
from core.decorators import tiene_permiso


class JournalEntryListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Lista de asientos contables con filtros y búsqueda"""
    model = JournalEntry
    template_name = 'accounting/entries/entry_list.html'
    context_object_name = 'entries'
    permission_required = 'accounting.view_journalentry'
    paginate_by = 20

    def get_queryset(self):
        """Filtrar por empresa del usuario y aplicar búsqueda"""
        queryset = JournalEntry.objects.filter(
            empresa=self.request.user.empresa_activa
        ).select_related('journal', 'created_by', 'posted_by')
        
        # Búsqueda
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(number__icontains=search) |
                Q(reference__icontains=search) |
                Q(narration__icontains=search) |
                Q(journal__name__icontains=search)
            )
        
        # Filtro por estado
        state = self.request.GET.get('state', '')
        if state:
            queryset = queryset.filter(state=state)
        
        # Filtro por diario
        journal_id = self.request.GET.get('journal', '')
        if journal_id:
            queryset = queryset.filter(journal_id=journal_id)
        
        # Filtro por fecha
        date_from = self.request.GET.get('date_from', '')
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        
        date_to = self.request.GET.get('date_to', '')
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
        
        return queryset.order_by('-date', '-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        empresa = self.request.user.empresa_activa
        
        # Estadísticas
        total_entries = JournalEntry.objects.filter(empresa=empresa).count()
        draft_entries = JournalEntry.objects.filter(empresa=empresa, state=EntryStates.DRAFT).count()
        posted_entries = JournalEntry.objects.filter(empresa=empresa, state=EntryStates.POSTED).count()
        cancelled_entries = JournalEntry.objects.filter(empresa=empresa, state=EntryStates.CANCELLED).count()
        
        # Asientos por diario
        entries_by_journal = JournalEntry.objects.filter(empresa=empresa).values(
            'journal__name'
        ).annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Totales de débito y crédito
        total_debit = JournalEntryLine.objects.filter(
            entry__empresa=empresa,
            entry__state=EntryStates.POSTED
        ).aggregate(total=Sum('debit'))['total'] or 0
        
        total_credit = JournalEntryLine.objects.filter(
            entry__empresa=empresa,
            entry__state=EntryStates.POSTED
        ).aggregate(total=Sum('credit'))['total'] or 0
        
        context.update({
            'search': self.request.GET.get('search', ''),
            'state_filter': self.request.GET.get('state', ''),
            'journal_filter': self.request.GET.get('journal', ''),
            'date_from_filter': self.request.GET.get('date_from', ''),
            'date_to_filter': self.request.GET.get('date_to', ''),
            'total_entries': total_entries,
            'draft_entries': draft_entries,
            'posted_entries': posted_entries,
            'cancelled_entries': cancelled_entries,
            'entries_by_journal': entries_by_journal,
            'total_debit': total_debit,
            'total_credit': total_credit,
            'journals': Journal.objects.filter(empresa=empresa, is_active=True),
            'entry_states': EntryStates.CHOICES,
        })
        return context


class JournalEntryCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Crear nuevo asiento contable"""
    model = JournalEntry
    form_class = JournalEntryForm
    template_name = 'accounting/entries/entry_form.html'
    permission_required = 'accounting.add_journalentry'
    success_url = reverse_lazy('accounting:entry_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['lines'] = JournalEntryLineFormSet(self.request.POST, instance=self.object)
        else:
            context['lines'] = JournalEntryLineFormSet(instance=self.object)
        
        context['titulo'] = _('Create Journal Entry')
        context['submit_text'] = _('Create Entry')
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        lines = context['lines']
        
        if form.is_valid() and lines.is_valid():
            with transaction.atomic():
                form.instance.empresa = self.request.user.empresa_activa
                form.instance.created_by = self.request.user
                self.object = form.save()
                lines.instance = self.object
                lines.save()
                
                # Validar balance
                total_debit = sum(line.debit for line in lines.forms if line.cleaned_data and not line.cleaned_data.get('DELETE'))
                total_credit = sum(line.credit for line in lines.forms if line.cleaned_data and not line.cleaned_data.get('DELETE'))
                
                if abs(total_debit - total_credit) > Decimal('0.01'):
                    messages.error(self.request, _('Journal entry must be balanced. Debit: {}, Credit: {}').format(total_debit, total_credit))
                    return self.form_invalid(form)
                
                messages.success(self.request, _('Journal entry created successfully.'))
                return super().form_valid(form)
        
        return self.form_invalid(form)

    def get_form_kwargs(self):
        """Pasar empresa al formulario"""
        kwargs = super().get_form_kwargs()
        kwargs['empresa'] = self.request.user.empresa_activa
        return kwargs


class JournalEntryUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Editar asiento contable"""
    model = JournalEntry
    form_class = JournalEntryForm
    template_name = 'accounting/entries/entry_form.html'
    permission_required = 'accounting.change_journalentry'
    success_url = reverse_lazy('accounting:entry_list')

    def get_queryset(self):
        """Filtrar por empresa del usuario"""
        return JournalEntry.objects.filter(empresa=self.request.user.empresa_activa)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['lines'] = JournalEntryLineFormSet(self.request.POST, instance=self.object)
        else:
            context['lines'] = JournalEntryLineFormSet(instance=self.object)
        
        context['titulo'] = _('Edit Journal Entry')
        context['submit_text'] = _('Update Entry')
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        lines = context['lines']
        
        if form.is_valid() and lines.is_valid():
            with transaction.atomic():
                # Verificar que no esté publicado
                if self.object.state == EntryStates.POSTED:
                    messages.error(self.request, _('Cannot edit posted entries.'))
                    return redirect('accounting:entry_list')
                
                self.object = form.save()
                lines.instance = self.object
                lines.save()
                
                # Validar balance
                total_debit = sum(line.debit for line in lines.forms if line.cleaned_data and not line.cleaned_data.get('DELETE'))
                total_credit = sum(line.credit for line in lines.forms if line.cleaned_data and not line.cleaned_data.get('DELETE'))
                
                if abs(total_debit - total_credit) > Decimal('0.01'):
                    messages.error(self.request, _('Journal entry must be balanced. Debit: {}, Credit: {}').format(total_debit, total_credit))
                    return self.form_invalid(form)
                
                messages.success(self.request, _('Journal entry updated successfully.'))
                return super().form_valid(form)
        
        return self.form_invalid(form)

    def get_form_kwargs(self):
        """Pasar empresa al formulario"""
        kwargs = super().get_form_kwargs()
        kwargs['empresa'] = self.request.user.empresa_activa
        return kwargs


class JournalEntryDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """Eliminar asiento contable"""
    model = JournalEntry
    template_name = 'accounting/entries/entry_confirm_delete.html'
    permission_required = 'accounting.delete_journalentry'
    success_url = reverse_lazy('accounting:entry_list')

    def get_queryset(self):
        """Filtrar por empresa del usuario"""
        return JournalEntry.objects.filter(empresa=self.request.user.empresa_activa)

    def delete(self, request, *args, **kwargs):
        """Verificar que no esté publicado"""
        entry = self.get_object()
        
        if entry.state == EntryStates.POSTED:
            messages.error(request, _('Cannot delete posted entries.'))
            return redirect('accounting:entry_list')
        
        response = super().delete(request, *args, **kwargs)
        messages.success(request, _('Journal entry deleted successfully.'))
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = _('Confirm Journal Entry Deletion')
        return context


class JournalEntryDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Detalle de asiento contable"""
    model = JournalEntry
    template_name = 'accounting/entries/entry_detail.html'
    context_object_name = 'entry'
    permission_required = 'accounting.view_journalentry'

    def get_queryset(self):
        """Filtrar por empresa del usuario"""
        return JournalEntry.objects.filter(
            empresa=self.request.user.empresa_activa
        ).select_related('journal', 'created_by', 'posted_by')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        entry = self.object
        
        # Obtener líneas del asiento
        lines = entry.lines.select_related('account', 'partner', 'currency').order_by('id')
        
        # Calcular totales
        total_debit = sum(line.debit for line in lines)
        total_credit = sum(line.credit for line in lines)
        is_balanced = abs(total_debit - total_credit) <= Decimal('0.01')
        
        context.update({
            'lines': lines,
            'total_debit': total_debit,
            'total_credit': total_credit,
            'is_balanced': is_balanced,
            'balance_difference': total_debit - total_credit,
        })
        return context


@method_decorator(csrf_exempt, name='dispatch')
class JournalEntryPostView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Publicar asiento contable"""
    model = JournalEntry
    permission_required = 'accounting.change_journalentry'
    http_method_names = ['post']

    def get_queryset(self):
        """Filtrar por empresa del usuario"""
        return JournalEntry.objects.filter(empresa=self.request.user.empresa_activa)

    def post(self, request, *args, **kwargs):
        entry = self.get_object()
        
        try:
            entry.post(request.user)
            messages.success(request, _('Journal entry posted successfully.'))
        except Exception as e:
            messages.error(request, str(e))
        
        return redirect('accounting:entry_detail', pk=entry.pk)


@method_decorator(csrf_exempt, name='dispatch')
class JournalEntryCancelView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Cancelar asiento contable"""
    model = JournalEntry
    permission_required = 'accounting.change_journalentry'
    http_method_names = ['post']

    def get_queryset(self):
        """Filtrar por empresa del usuario"""
        return JournalEntry.objects.filter(empresa=self.request.user.empresa_activa)

    def post(self, request, *args, **kwargs):
        entry = self.get_object()
        
        try:
            entry.cancel(request.user)
            messages.success(request, _('Journal entry cancelled successfully.'))
        except Exception as e:
            messages.error(request, str(e))
        
        return redirect('accounting:entry_detail', pk=entry.pk)


@tiene_permiso('accounting.view_journalentry')
def entry_dashboard(request):
    """Dashboard de asientos contables"""
    empresa = request.user.empresa_activa
    
    # Estadísticas generales
    total_entries = JournalEntry.objects.filter(empresa=empresa).count()
    draft_entries = JournalEntry.objects.filter(empresa=empresa, state=EntryStates.DRAFT).count()
    posted_entries = JournalEntry.objects.filter(empresa=empresa, state=EntryStates.POSTED).count()
    cancelled_entries = JournalEntry.objects.filter(empresa=empresa, state=EntryStates.CANCELLED).count()
    
    # Totales de débito y crédito
    total_debit = JournalEntryLine.objects.filter(
        entry__empresa=empresa,
        entry__state=EntryStates.POSTED
    ).aggregate(total=Sum('debit'))['total'] or 0
    
    total_credit = JournalEntryLine.objects.filter(
        entry__empresa=empresa,
        entry__state=EntryStates.POSTED
    ).aggregate(total=Sum('credit'))['total'] or 0
    
    # Asientos por mes (últimos 12 meses)
    from django.utils import timezone
    from datetime import timedelta
    
    monthly_entries = []
    for i in range(12):
        date = timezone.now().date() - timedelta(days=30*i)
        month_start = date.replace(day=1)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        count = JournalEntry.objects.filter(
            empresa=empresa,
            date__range=[month_start, month_end]
        ).count()
        
        monthly_entries.append({
            'month': month_start.strftime('%B %Y'),
            'count': count
        })
    
    # Asientos recientes
    recent_entries = JournalEntry.objects.filter(
        empresa=empresa
    ).select_related('journal', 'created_by').order_by('-created_at')[:10]
    
    # Diarios más utilizados
    popular_journals = JournalEntry.objects.filter(
        empresa=empresa
    ).values('journal__name').annotate(
        count=Count('id')
    ).order_by('-count')[:5]
    
    context = {
        'total_entries': total_entries,
        'draft_entries': draft_entries,
        'posted_entries': posted_entries,
        'cancelled_entries': cancelled_entries,
        'total_debit': total_debit,
        'total_credit': total_credit,
        'monthly_entries': monthly_entries,
        'recent_entries': recent_entries,
        'popular_journals': popular_journals,
    }
    
    return render(request, 'accounting/entries/entry_dashboard.html', context)


@require_POST
@tiene_permiso('accounting.add_journalentry')
def quick_entry_create(request):
    """Crear asiento rápido desde AJAX"""
    try:
        data = json.loads(request.body)
        
        with transaction.atomic():
            # Crear asiento
            entry = JournalEntry.objects.create(
                empresa=request.user.empresa_activa,
                journal_id=data['journal_id'],
                number=data['number'],
                date=data['date'],
                reference=data.get('reference', ''),
                narration=data.get('narration', ''),
                created_by=request.user
            )
            
            # Crear líneas
            for line_data in data['lines']:
                JournalEntryLine.objects.create(
                    entry=entry,
                    account_id=line_data['account_id'],
                    debit=Decimal(line_data.get('debit', 0)),
                    credit=Decimal(line_data.get('credit', 0)),
                    name=line_data.get('name', '')
                )
            
            return JsonResponse({
                'success': True,
                'entry_id': entry.id,
                'message': _('Journal entry created successfully.')
            })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)


@tiene_permiso('accounting.view_journalentry')
def entry_balance_check(request, pk):
    """Verificar balance de un asiento"""
    entry = get_object_or_404(JournalEntry, pk=pk, empresa=request.user.empresa_activa)
    
    lines = entry.lines.all()
    total_debit = sum(line.debit for line in lines)
    total_credit = sum(line.credit for line in lines)
    is_balanced = abs(total_debit - total_credit) <= Decimal('0.01')
    
    return JsonResponse({
        'is_balanced': is_balanced,
        'total_debit': float(total_debit),
        'total_credit': float(total_credit),
        'difference': float(total_debit - total_credit)
    }) 