from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy
from ..models import Currency, ExchangeRate
from ..forms import CurrencyForm, ExchangeRateForm
from django.utils.translation import gettext_lazy as _

class CurrencyListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Currency
    template_name = 'core/currency/currency_list.html'
    context_object_name = 'currencies'
    permission_required = 'configuracion.moneda'
    paginate_by = 20

class CurrencyCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Currency
    form_class = CurrencyForm
    template_name = 'core/currency/currency_form.html'
    permission_required = 'configuracion.moneda'
    success_url = reverse_lazy('core:currency_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = _("Create Currency")
        return context

class CurrencyUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Currency
    form_class = CurrencyForm
    template_name = 'core/currency/currency_form.html'
    permission_required = 'configuracion.moneda'
    success_url = reverse_lazy('core:currency_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = _("Edit Currency")
        return context

class CurrencyDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Currency
    template_name = 'core/currency/currency_confirm_delete.html'
    success_url = reverse_lazy('core:currency_list')
    permission_required = 'configuracion.moneda'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = _("Confirm Currency Deletion")
        return context

# Vistas para ExchangeRate

class ExchangeRateListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = ExchangeRate
    template_name = 'core/currency/exchange_rate_list.html'
    context_object_name = 'rates'
    permission_required = 'configuracion.moneda'
    paginate_by = 20

    def get_queryset(self):
        return ExchangeRate.objects.select_related('from_currency', 'to_currency').order_by('-date', 'from_currency__code')

class ExchangeRateCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = ExchangeRate
    form_class = ExchangeRateForm
    template_name = 'core/currency/exchange_rate_form.html'
    permission_required = 'configuracion.moneda'
    success_url = reverse_lazy('core:exchange_rate_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = _("Create Exchange Rate")
        return context

class ExchangeRateUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = ExchangeRate
    form_class = ExchangeRateForm
    template_name = 'core/currency/exchange_rate_form.html'
    permission_required = 'configuracion.moneda'
    success_url = reverse_lazy('core:exchange_rate_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = _("Edit Exchange Rate")
        return context

class ExchangeRateDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = ExchangeRate
    template_name = 'core/currency/exchange_rate_confirm_delete.html'
    success_url = reverse_lazy('core:exchange_rate_list')
    permission_required = 'configuracion.moneda'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = _("Confirm Exchange Rate Deletion")
        return context 