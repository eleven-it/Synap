from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse_lazy, reverse
from django.utils.translation import gettext_lazy as _
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import datetime, timedelta

from .models import CloverDevice, CloverTransaction, CloverConfiguration
from .services.clover_service import CloverService
from .forms import CloverDeviceForm, CloverConfigurationForm


@login_required
def clover_dashboard(request):
    """Dashboard principal de Clover"""
    try:
        # Obtener empresa y sucursal del usuario
        from core.models import Empresa, Branch
        
        empresa = Empresa.objects.filter(is_active=True).first()
        branch = Branch.objects.filter(is_active=True).first()
        
        if not empresa or not branch:
            messages.error(request, "No se pudo determinar la empresa o sucursal activa")
            return redirect('core:dashboard')
        
        # Estadísticas generales
        devices = CloverDevice.objects.filter(empresa=empresa, branch=branch)
        transactions = CloverTransaction.objects.filter(empresa=empresa, branch=branch)
        
        # Estadísticas del día
        today = timezone.now().date()
        today_transactions = transactions.filter(created_at__date=today)
        
        stats = {
            'total_devices': devices.count(),
            'active_devices': devices.filter(is_active=True).count(),
            'total_transactions': transactions.count(),
            'today_transactions': today_transactions.count(),
            'today_amount': today_transactions.filter(status='approved').aggregate(
                total=Sum('total_amount')
            )['total'] or 0,
            'pending_transactions': transactions.filter(status='pending').count(),
        }
        
        # Dispositivos recientes
        recent_devices = devices.order_by('-created_at')[:5]
        
        # Transacciones recientes
        recent_transactions = transactions.order_by('-created_at')[:10]
        
        context = {
            'empresa': empresa,
            'branch': branch,
            'stats': stats,
            'recent_devices': recent_devices,
            'recent_transactions': recent_transactions,
        }
        
        return render(request, 'clover/dashboard.html', context)
        
    except Exception as e:
        messages.error(request, f"Error al cargar el dashboard: {str(e)}")
        return redirect('core:dashboard')


class CloverDeviceListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Lista de dispositivos Clover"""
    model = CloverDevice
    template_name = 'clover/device_list.html'
    context_object_name = 'devices'
    permission_required = 'clover.view_cloverdevice'
    paginate_by = 20
    
    def get_queryset(self):
        # Obtener empresa y sucursal del usuario
        from core.models import Empresa, Branch
        
        empresa = Empresa.objects.filter(is_active=True).first()
        branch = Branch.objects.filter(is_active=True).first()
        
        if not empresa or not branch:
            return CloverDevice.objects.none()
        
        return CloverDevice.objects.filter(
            empresa=empresa,
            branch=branch
        ).order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_devices'] = self.get_queryset().count()
        context['active_devices'] = self.get_queryset().filter(is_active=True).count()
        return context


class CloverDeviceDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Detalle de dispositivo Clover"""
    model = CloverDevice
    template_name = 'clover/device_detail.html'
    context_object_name = 'device'
    permission_required = 'clover.view_cloverdevice'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener transacciones del dispositivo
        device_transactions = CloverTransaction.objects.filter(
            device=self.object
        ).order_by('-created_at')[:20]
        
        # Estadísticas del dispositivo
        device_stats = {
            'total_transactions': CloverTransaction.objects.filter(device=self.object).count(),
            'approved_transactions': CloverTransaction.objects.filter(
                device=self.object, status='approved'
            ).count(),
            'total_amount': CloverTransaction.objects.filter(
                device=self.object, status='approved'
            ).aggregate(total=Sum('total_amount'))['total'] or 0,
        }
        
        context['device_transactions'] = device_transactions
        context['device_stats'] = device_stats
        
        return context


class CloverDeviceCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Crear dispositivo Clover"""
    model = CloverDevice
    form_class = CloverDeviceForm
    template_name = 'clover/device_form.html'
    permission_required = 'clover.add_cloverdevice'
    success_url = reverse_lazy('clover:device_list')
    
    def form_valid(self, form):
        # Asignar empresa y sucursal
        from core.models import Empresa, Branch
        
        empresa = Empresa.objects.filter(is_active=True).first()
        branch = Branch.objects.filter(is_active=True).first()
        
        if not empresa or not branch:
            messages.error(self.request, "No se pudo determinar la empresa o sucursal activa")
            return self.form_invalid(form)
        
        form.instance.empresa = empresa
        form.instance.branch = branch
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        
        messages.success(self.request, _('Clover device created successfully.'))
        return super().form_valid(form)


class CloverDeviceUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Editar dispositivo Clover"""
    model = CloverDevice
    form_class = CloverDeviceForm
    template_name = 'clover/device_form.html'
    permission_required = 'clover.change_cloverdevice'
    
    def get_success_url(self):
        return reverse('clover:device_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        messages.success(self.request, _('Clover device updated successfully.'))
        return super().form_valid(form)


class CloverDeviceDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """Eliminar dispositivo Clover"""
    model = CloverDevice
    template_name = 'clover/device_confirm_delete.html'
    permission_required = 'clover.delete_cloverdevice'
    success_url = reverse_lazy('clover:device_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, _('Clover device deleted successfully.'))
        return super().delete(request, *args, **kwargs)


class CloverTransactionListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Lista de transacciones Clover"""
    model = CloverTransaction
    template_name = 'clover/transaction_list.html'
    context_object_name = 'transactions'
    permission_required = 'clover.view_clovertransaction'
    paginate_by = 20
    
    def get_queryset(self):
        # Obtener empresa y sucursal del usuario
        from core.models import Empresa, Branch
        
        empresa = Empresa.objects.filter(is_active=True).first()
        branch = Branch.objects.filter(is_active=True).first()
        
        if not empresa or not branch:
            return CloverTransaction.objects.none()
        
        queryset = CloverTransaction.objects.filter(
            empresa=empresa,
            branch=branch
        ).select_related('device', 'operator').order_by('-created_at')
        
        # Filtros
        status_filter = self.request.GET.get('status', '')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        device_filter = self.request.GET.get('device', '')
        if device_filter:
            queryset = queryset.filter(device_id=device_filter)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener filtros disponibles
        from core.models import Empresa, Branch
        
        empresa = Empresa.objects.filter(is_active=True).first()
        branch = Branch.objects.filter(is_active=True).first()
        
        if empresa and branch:
            context['devices'] = CloverDevice.objects.filter(
                empresa=empresa, branch=branch, is_active=True
            )
        
        context['status_filter'] = self.request.GET.get('status', '')
        context['device_filter'] = self.request.GET.get('device', '')
        
        return context


class CloverTransactionDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Detalle de transacción Clover"""
    model = CloverTransaction
    template_name = 'clover/transaction_detail.html'
    context_object_name = 'transaction'
    permission_required = 'clover.view_clovertransaction'


@login_required
def test_device_connection(request, device_id):
    """Probar conexión de dispositivo Clover"""
    try:
        device = get_object_or_404(CloverDevice, id=device_id)
        
        # Probar conexión
        clover_service = CloverService(device=device)
        result = clover_service.test_connection()
        
        if result['success']:
            messages.success(request, result['message'])
        else:
            messages.error(request, f"Error: {result['error']}")
        
        return redirect('clover:device_detail', pk=device_id)
        
    except Exception as e:
        messages.error(request, f"Error al probar conexión: {str(e)}")
        return redirect('clover:device_detail', pk=device_id)


@login_required
def process_payment(request, transaction_id):
    """Procesar pago pendiente"""
    try:
        transaction = get_object_or_404(CloverTransaction, id=transaction_id)
        
        if transaction.status != 'pending':
            messages.error(request, "Solo se pueden procesar transacciones pendientes")
            return redirect('clover:transaction_detail', pk=transaction_id)
        
        # Procesar pago
        clover_service = CloverService(device=transaction.device)
        updated_transaction = clover_service.process_payment(
            transaction.clover_transaction_id
        )
        
        if updated_transaction.status == 'approved':
            messages.success(request, "Pago procesado exitosamente")
        else:
            messages.error(request, "Error al procesar el pago")
        
        return redirect('clover:transaction_detail', pk=transaction_id)
        
    except Exception as e:
        messages.error(request, f"Error al procesar pago: {str(e)}")
        return redirect('clover:transaction_detail', pk=transaction_id)


@login_required
def refund_transaction(request, transaction_id):
    """Reembolsar transacción"""
    try:
        transaction = get_object_or_404(CloverTransaction, id=transaction_id)
        
        if not transaction.can_be_refunded:
            messages.error(request, "Esta transacción no puede ser reembolsada")
            return redirect('clover:transaction_detail', pk=transaction_id)
        
        # Reembolsar transacción
        clover_service = CloverService(device=transaction.device)
        refund_transaction = clover_service.refund_payment(transaction)
        
        messages.success(request, f"Reembolso procesado: {refund_transaction.transaction_id}")
        return redirect('clover:transaction_detail', pk=transaction_id)
        
    except Exception as e:
        messages.error(request, f"Error al procesar reembolso: {str(e)}")
        return redirect('clover:transaction_detail', pk=transaction_id)


@login_required
def clover_configuration(request):
    """Configuración de Clover"""
    try:
        # Obtener empresa
        from core.models import Empresa
        
        empresa = Empresa.objects.filter(is_active=True).first()
        
        if not empresa:
            messages.error(request, "No se pudo determinar la empresa activa")
            return redirect('core:dashboard')
        
        # Obtener o crear configuración
        config, created = CloverConfiguration.objects.get_or_create(empresa=empresa)
        
        if request.method == 'POST':
            form = CloverConfigurationForm(request.POST, instance=config)
            if form.is_valid():
                form.save()
                messages.success(request, _('Clover configuration updated successfully.'))
                return redirect('clover:configuration')
        else:
            form = CloverConfigurationForm(instance=config)
        
        context = {
            'empresa': empresa,
            'form': form,
        }
        
        return render(request, 'clover/configuration.html', context)
        
    except Exception as e:
        messages.error(request, f"Error al cargar configuración: {str(e)}")
        return redirect('clover:dashboard') 