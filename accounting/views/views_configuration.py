from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib import messages
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django.contrib.messages.views import SuccessMessageMixin

from core.models import Currency
from core.utils import get_user_empresa
from accounting.models import AccountTypes


@login_required
def currency_list(request):
    """Lista de monedas disponibles en el sistema"""
    empresa = get_user_empresa(request)
    
    # Obtener todas las monedas activas
    currencies = Currency.objects.filter(is_active=True).order_by('code')
    
    context = {
        'currencies': currencies,
        'empresa': empresa,
        'title': _('Currencies'),
        'breadcrumb': [
            {'name': _('Accounting'), 'url': reverse('accounting:dashboard')},
            {'name': _('Currencies'), 'url': '#'}
        ]
    }
    
    return render(request, 'accounting/currency_list.html', context)


@login_required
def account_type_list(request):
    """Lista de tipos de cuenta contable"""
    empresa = get_user_empresa(request)
    
    # Obtener todos los tipos de cuenta definidos
    account_types = [
        {
            'code': AccountTypes.ASSETS,
            'name': _('Assets'),
            'description': _('Assets represent what the company owns'),
            'color': 'text-green-600',
            'icon': 'account_balance'
        },
        {
            'code': AccountTypes.LIABILITIES,
            'name': _('Liabilities'),
            'description': _('Liabilities represent what the company owes'),
            'color': 'text-red-600',
            'icon': 'credit_card'
        },
        {
            'code': AccountTypes.EQUITY,
            'name': _('Equity'),
            'description': _('Equity represents the owner\'s investment'),
            'color': 'text-blue-600',
            'icon': 'person'
        },
        {
            'code': AccountTypes.INCOME,
            'name': _('Income'),
            'description': _('Income represents revenue earned'),
            'color': 'text-emerald-600',
            'icon': 'trending_up'
        },
        {
            'code': AccountTypes.EXPENSES,
            'name': _('Expenses'),
            'description': _('Expenses represent costs incurred'),
            'color': 'text-orange-600',
            'icon': 'trending_down'
        }
    ]
    
    context = {
        'account_types': account_types,
        'empresa': empresa,
        'title': _('Account Types'),
        'breadcrumb': [
            {'name': _('Accounting'), 'url': reverse('accounting:dashboard')},
            {'name': _('Account Types'), 'url': '#'}
        ]
    }
    
    return render(request, 'accounting/account_type_list.html', context)


class CurrencyListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Vista de clase para listar monedas"""
    model = Currency
    template_name = 'accounting/currency_list.html'
    context_object_name = 'currencies'
    permission_required = 'core.view_currency'
    
    def get_queryset(self):
        return Currency.objects.filter(is_active=True).order_by('code')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['empresa'] = get_user_empresa(self.request)
        context['title'] = _('Currencies')
        context['breadcrumb'] = [
            {'name': _('Accounting'), 'url': reverse('accounting:dashboard')},
            {'name': _('Currencies'), 'url': '#'}
        ]
        return context


class AccountTypeListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Vista de clase para listar tipos de cuenta"""
    template_name = 'accounting/account_type_list.html'
    context_object_name = 'account_types'
    permission_required = 'accounting.view_chartofaccounts'
    
    def get_queryset(self):
        # Retornar los tipos de cuenta como queryset simulado
        return [
            {
                'code': AccountTypes.ASSETS,
                'name': _('Assets'),
                'description': _('Assets represent what the company owns'),
                'color': 'text-green-600',
                'icon': 'account_balance'
            },
            {
                'code': AccountTypes.LIABILITIES,
                'name': _('Liabilities'),
                'description': _('Liabilities represent what the company owes'),
                'color': 'text-red-600',
                'icon': 'credit_card'
            },
            {
                'code': AccountTypes.EQUITY,
                'name': _('Equity'),
                'description': _('Equity represents the owner\'s investment'),
                'color': 'text-blue-600',
                'icon': 'person'
            },
            {
                'code': AccountTypes.INCOME,
                'name': _('Income'),
                'description': _('Income represents revenue earned'),
                'color': 'text-emerald-600',
                'icon': 'trending_up'
            },
            {
                'code': AccountTypes.EXPENSES,
                'name': _('Expenses'),
                'description': _('Expenses represent costs incurred'),
                'color': 'text-orange-600',
                'icon': 'trending_down'
            }
        ]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['empresa'] = get_user_empresa(self.request)
        context['title'] = _('Account Types')
        context['breadcrumb'] = [
            {'name': _('Accounting'), 'url': reverse('accounting:dashboard')},
            {'name': _('Account Types'), 'url': '#'}
        ]
        return context 