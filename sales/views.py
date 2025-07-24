from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy, reverse
from django.core.paginator import Paginator
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST
import json

from .models import (
    Client, SalesOrder, SalesOrderLine, PriceList, PriceListItem,
    PaymentTerm, PaymentTermLine, Invoice, InvoiceLine, Payment,
    DeliveryOrder, DeliveryOrderLine, ReturnDelivery, CreditNote, ApprovalLog,
    POSSession, POSTerminal, POSSale, POSPayment, POSPromotion,
    PaymentMethod, PaymentProcessor, ClientTag
)
from inventory.models import Brand, Subcategory, Product, ProductVariant, Warehouse, Category, StockQuant, StockMove
from .api.serializers import (
    ClientSerializer, SalesOrderSerializer, InvoiceSerializer,
    PaymentSerializer, DeliveryOrderSerializer
)
from core.models import Currency, State, FiscalResponsibility, Country
from inventory.models import ProductVariant, Warehouse, Category, StockQuant, StockMove
from .forms import (
    ClientWizardStep1Form, ClientWizardStep2Form, ClientWizardStep3Form,
    ContactSearchForm, ContactRelationshipForm,
    PaymentMethodForm, PaymentProcessorForm, POSClientSelectionForm,
    ContactManagementForm, PaymentTermForm, PaymentTermLineForm,
    ClientTagForm, ClientForm, ClientAttachmentFormSet
)
from core.models import UsuarioExtendido
from django.contrib.contenttypes.models import ContentType
from core.models import Contact, ContactRelationship
from django.contrib.messages.views import SuccessMessageMixin
from .services import POSService, POSSaleService, POSIntegrationService


# Mixin para manejar permisos de superusuarios y administradores
class SuperuserOrPermissionRequiredMixin(PermissionRequiredMixin):
    def has_permission(self):
        # Superusuarios y administradores tienen acceso total
        if self.request.user.is_superuser or (hasattr(self.request.user, 'is_admin') and self.request.user.is_admin()):
            return True
        # Para otros usuarios, verificar permisos específicos
        return super().has_permission()



@login_required
def sales_dashboard(request):
    """Dashboard principal del módulo de ventas"""
    
    # Estadísticas generales
    total_clients = Client.objects.filter(is_active=True).count()
    total_orders = SalesOrder.objects.count()
    total_invoices = Invoice.objects.count()
    total_payments = Payment.objects.count()
    
    # Pedidos por estado
    orders_by_state = SalesOrder.objects.values('state').annotate(
        count=Count('id'),
        total_amount=Sum('total')
    )
    
    # Facturas por estado
    invoices_by_state = Invoice.objects.values('state').annotate(
        count=Count('id'),
        total_amount=Sum('total')
    )
    
    # Ventas del mes actual
    current_month = timezone.now().month
    current_year = timezone.now().year
    monthly_sales = SalesOrder.objects.filter(
        order_date__month=current_month,
        order_date__year=current_year
    ).aggregate(
        total_orders=Count('id'),
        total_amount=Sum('total')
    )
    
    # Top clientes
    top_clients = SalesOrder.objects.values(
        'client__name'
    ).annotate(
        total_orders=Count('id'),
        total_amount=Sum('total')
    ).order_by('-total_amount')[:5]
    
    # Pedidos recientes
    recent_orders = SalesOrder.objects.select_related('client').order_by('-order_date')[:10]
    
    # Facturas recientes
    recent_invoices = Invoice.objects.select_related('client').order_by('-invoice_date')[:10]
    
    context = {
        'total_clients': total_clients,
        'total_orders': total_orders,
        'total_invoices': total_invoices,
        'total_payments': total_payments,
        'orders_by_status': list(orders_by_state),
        'invoices_by_status': list(invoices_by_state),
        'monthly_sales': monthly_sales,
        'top_clients': list(top_clients),
        'recent_orders': recent_orders,
        'recent_invoices': recent_invoices,
    }
    
    return render(request, 'sales/dashboard.html', context)


# Vistas de Clientes
@login_required
def client_list(request):
    """Lista de clientes"""
    clients = Client.objects.all().order_by('-id')
    
    # Filtros
    search = request.GET.get('search', '')
    if search:
        clients = clients.filter(
            Q(name__icontains=search) |
            Q(tax_id__icontains=search) |
            Q(email__icontains=search)
        )
    
    status_filter = request.GET.get('status', '')
    if status_filter:
        clients = clients.filter(is_active=status_filter == 'active')
    
    context = {
        'clients': clients,
        'search': search,
        'status_filter': status_filter,
    }
    
    return render(request, 'sales/clients/client_list.html', context)


@login_required
def client_detail(request, pk):
    """Detalle del cliente"""
    client = get_object_or_404(Client, pk=pk)
    
    # Estadísticas del cliente
    orders = SalesOrder.objects.filter(client=client)
    invoices = Invoice.objects.filter(client=client)
    payments = Payment.objects.filter(client=client)
    
    total_orders = orders.count()
    total_amount_orders = orders.aggregate(total=Sum('total'))['total'] or 0
    total_invoices = invoices.count()
    total_billed = invoices.aggregate(total=Sum('total'))['total'] or 0
    total_paid = payments.aggregate(total=Sum('amount'))['total'] or 0
    pending_balance = total_billed - total_paid
    
    # Pedidos recientes
    recent_orders = orders.order_by('-order_date')[:5]
    
    # Facturas recientes
    recent_invoices = invoices.order_by('-invoice_date')[:5]
    
    # Pagos recientes
    recent_payments = payments.order_by('-payment_date')[:5]
    
    context = {
        'client': client,
        'total_orders': total_orders,
        'total_amount_orders': total_amount_orders,
        'total_invoices': total_invoices,
        'total_billed': total_billed,
        'total_paid': total_paid,
        'pending_balance': pending_balance,
        'recent_orders': recent_orders,
        'recent_invoices': recent_invoices,
        'recent_payments': recent_payments,
    }
    
    return render(request, 'sales/clients/client_detail.html', context)


@login_required
def client_delete(request, pk):
    """Eliminar cliente"""
    client = get_object_or_404(Client, pk=pk)
    
    if request.method == 'POST':
        try:
            client_name = client.name
            client.delete()
            messages.success(request, f'Cliente "{client_name}" eliminado correctamente.')
            return redirect('sales:client_list')
        except Exception as e:
            messages.error(request, f'Error al eliminar cliente: {str(e)}')
    
    context = {'client': client}
    return render(request, 'sales/clients/client_list.html', context)


# Vistas de Pedidos de Venta
@login_required
def sales_order_list(request):
    """Lista de pedidos de venta"""
    orders = SalesOrder.objects.select_related('client').order_by('-id')
    
    # Filtros
    search = request.GET.get('search', '')
    if search:
        orders = orders.filter(
            Q(order_number__icontains=search) |
            Q(client__name__icontains=search)
        )
    
    status_filter = request.GET.get('status', '')
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    client_filter = request.GET.get('client', '')
    if client_filter:
        orders = orders.filter(client_id=client_filter)
    
    context = {
        'orders': orders,
        'search': search,
        'status_filter': status_filter,
        'client_filter': client_filter,
        'clients': Client.objects.filter(is_active=True),
    }
    
    return render(request, 'sales/orders/sales_order_list.html', context)


@login_required
def sales_order_create(request):
    """Crear nuevo pedido de venta"""
    if request.method == 'POST':
        # Lógica para crear pedido
        client_id = request.POST.get('client')
        order_date = request.POST.get('order_date')
        delivery_date = request.POST.get('delivery_date')
        payment_term_id = request.POST.get('payment_term')
        price_list_id = request.POST.get('price_list')
        currency = request.POST.get('currency', 'USD')
        notes = request.POST.get('notes', '')
        
        try:
            client = Client.objects.get(id=client_id)
            payment_term = PaymentTerm.objects.get(id=payment_term_id) if payment_term_id else None
            price_list = PriceList.objects.get(id=price_list_id) if price_list_id else None
            
            order = SalesOrder.objects.create(
                client=client,
                order_date=datetime.strptime(order_date, '%Y-%m-%d').date() if order_date else timezone.now().date(),
                delivery_date=datetime.strptime(delivery_date, '%Y-%m-%d').date() if delivery_date else None,
                payment_term=payment_term,
                price_list=price_list,
                currency=currency,
                notes=notes,
                status='draft'
            )
            
            messages.success(request, f'Pedido "{order.order_number}" creado correctamente.')
            return redirect('sales:sales_order_detail', pk=order.pk)
        except Exception as e:
            messages.error(request, f'Error al crear pedido: {str(e)}')
    
    context = {
        'clients': Client.objects.filter(is_active=True),
        'payment_terms': PaymentTerm.objects.filter(is_active=True),
        'price_lists': PriceList.objects.filter(is_active=True),
        'currencies': Currency.objects.filter(is_active=True),
        'products': ProductVariant.objects.filter(is_active=True).select_related('product'),
        'today': timezone.now().date(),
    }
    
    return render(request, 'sales/orders/sales_order_form.html', context)


@login_required
def sales_order_detail(request, pk):
    """Detalle del pedido de venta y gestión de acciones de workflow"""
    order = get_object_or_404(SalesOrder.objects.select_related('client', 'payment_term', 'price_list'), pk=pk)
    logs = order.approvallog_set.select_related('user').order_by('-action_date')
    
    # Obtener información de stock para el pedido
    from .services import SalesInventoryValidator
    stock_summary = SalesInventoryValidator.get_stock_summary(order)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        reason = request.POST.get('reason', '').strip()
        user = request.user
        error = None
        try:
            if not reason:
                raise ValidationError('El motivo es obligatorio para esta acción.')
            
            # Validaciones específicas según la acción
            if action == 'confirm_order':
                if not stock_summary['can_confirm']:
                    raise ValidationError('No se puede confirmar el pedido: stock insuficiente.')
            
            if action == 'mark_delivered':
                if not stock_summary['can_deliver']:
                    raise ValidationError('No se puede entregar el pedido: no hay stock reservado.')
            
            # Ejecutar acciones
            if action == 'send_quotation':
                order.send_quotation(user, reason)
                messages.success(request, 'Cotización enviada correctamente.')
            elif action == 'confirm_order':
                order.confirm_order(user, reason)
                messages.success(request, 'Pedido confirmado correctamente.')
            elif action == 'start_processing':
                order.start_processing(user, reason)
                messages.success(request, 'Procesamiento iniciado correctamente.')
            elif action == 'mark_ready_to_deliver':
                order.mark_ready_to_deliver(user, reason)
                messages.success(request, 'Pedido marcado como listo para entregar.')
            elif action == 'mark_delivered':
                order.mark_delivered(user, reason)
                messages.success(request, 'Pedido marcado como entregado.')
            elif action == 'mark_invoiced':
                order.mark_invoiced(user, reason)
                messages.success(request, 'Pedido marcado como facturado.')
            elif action == 'mark_paid':
                order.mark_paid(user, reason)
                messages.success(request, 'Pedido marcado como pagado.')
            elif action == 'mark_completed':
                order.mark_completed(user, reason)
                messages.success(request, 'Pedido marcado como completado.')
            elif action == 'cancel_order':
                order.cancel_order(user, reason)
                messages.success(request, 'Pedido cancelado correctamente.')
            else:
                error = 'Acción no reconocida.'
        except ValidationError as ve:
            error = str(ve)
        except Exception as e:
            error = str(e)
        if error:
            messages.error(request, error)
        return redirect('sales:sales_order_detail', pk=order.pk)

    context = {
        'order': order,
        'lines': order.lines.select_related('product_variant__product').all(),
        'logs': logs,
        'stock_summary': stock_summary,
    }
    return render(request, 'sales/orders/sales_order_detail.html', context)


@login_required
def sales_order_edit(request, pk):
    """Editar pedido de venta"""
    order = get_object_or_404(SalesOrder, pk=pk)
    
    if request.method == 'POST':
        # Lógica para actualizar pedido
        order.client_id = request.POST.get('client')
        order.order_date = datetime.strptime(request.POST.get('order_date'), '%Y-%m-%d').date()
        order.delivery_date = datetime.strptime(request.POST.get('delivery_date'), '%Y-%m-%d').date() if request.POST.get('delivery_date') else None
        order.payment_term_id = request.POST.get('payment_term')
        order.price_list_id = request.POST.get('price_list')
        order.currency = request.POST.get('currency', 'USD')
        order.notes = request.POST.get('notes', '')
        
        try:
            order.save()
            messages.success(request, f'Pedido "{order.order_number}" actualizado correctamente.')
            return redirect('sales:sales_order_detail', pk=order.pk)
        except Exception as e:
            messages.error(request, f'Error al actualizar pedido: {str(e)}')
    
    context = {
        'order': order,
        'clients': Client.objects.filter(is_active=True),
        'payment_terms': PaymentTerm.objects.filter(is_active=True),
        'price_lists': PriceList.objects.filter(is_active=True),
        'currencies': Currency.objects.filter(is_active=True),
        'products': ProductVariant.objects.filter(is_active=True).select_related('product'),
        'today': timezone.now().date(),
    }
    
    return render(request, 'sales/orders/sales_order_form.html', context)


@login_required
def sales_order_delete(request, pk):
    """Eliminar pedido de venta"""
    order = get_object_or_404(SalesOrder, pk=pk)
    
    if request.method == 'POST':
        try:
            order_number = order.order_number
            order.delete()
            messages.success(request, f'Pedido "{order_number}" eliminado correctamente.')
            return redirect('sales:sales_order_list')
        except Exception as e:
            messages.error(request, f'Error al eliminar pedido: {str(e)}')
    
    context = {'order': order}
    return render(request, 'sales/orders/sales_order_list.html', context)


@login_required
def sales_order_approve(request, pk):
    """Aprobar pedido de venta"""
    order = get_object_or_404(SalesOrder, pk=pk)
    
    if request.method == 'POST':
        if order.status != 'draft':
            messages.error(request, 'Solo se pueden aprobar pedidos en borrador.')
        else:
            order.status = 'approved'
            order.approved_by = request.user
            order.approved_at = timezone.now()
            order.save()
            
            # Crear log de aprobación
            ApprovalLog.objects.create(
                content_type_id=order.get_content_type_id(),
                object_id=order.id,
                approver=request.user,
                action='approved',
                comments=request.POST.get('comments', '')
            )
            
            messages.success(request, f'Pedido "{order.order_number}" aprobado correctamente.')
        
        return redirect('sales:sales_order_detail', pk=order.pk)
    
    context = {'order': order}
    return render(request, 'sales/orders/sales_order_list.html', context)


@login_required
def sales_order_cancel(request, pk):
    """Cancelar pedido de venta"""
    order = get_object_or_404(SalesOrder, pk=pk)
    
    if request.method == 'POST':
        if order.status in ['cancelled', 'completed']:
            messages.error(request, 'No se puede cancelar un pedido ya cancelado o completado.')
        else:
            order.status = 'cancelled'
            order.save()
            
            # Crear log de cancelación
            ApprovalLog.objects.create(
                content_type_id=order.get_content_type_id(),
                object_id=order.id,
                approver=request.user,
                action='cancelled',
                comments=request.POST.get('comments', '')
            )
            
            messages.success(request, f'Pedido "{order.order_number}" cancelado correctamente.')
        
        return redirect('sales:sales_order_detail', pk=order.pk)
    
    context = {'order': order}
    return render(request, 'sales/orders/sales_order_list.html', context)


@login_required
def sales_order_create_invoice(request, pk):
    """Crear factura desde pedido"""
    order = get_object_or_404(SalesOrder, pk=pk)
    
    if request.method == 'POST':
        if order.status != 'approved':
            messages.error(request, 'Solo se pueden facturar pedidos aprobados.')
        elif Invoice.objects.filter(sales_order=order).exists():
            messages.error(request, 'Ya existe una factura para este pedido.')
        else:
            try:
                # Crear factura con las líneas del pedido
                invoice = Invoice.objects.create(
                    client=order.client,
                    sales_order=order,
                    invoice_date=timezone.now().date(),
                    due_date=timezone.now().date() + timedelta(days=30),
                    payment_term=order.payment_term,
                    currency=order.currency,
                    notes=f'Factura generada desde pedido {order.order_number}',
                    status='draft'
                )
                
                # Crear líneas de factura
                for line in order.lines.all():
                    InvoiceLine.objects.create(
                        invoice=invoice,
                        product_variant=line.product_variant,
                        quantity=line.quantity,
                        unit_price=line.unit_price,
                        discount_percentage=line.discount_percentage,
                        discount_amount=line.discount_amount,
                        tax_percentage=line.tax_percentage,
                        tax_amount=line.tax_amount,
                        total=line.total
                    )
                
                messages.success(request, f'Factura creada correctamente desde pedido "{order.order_number}".')
                return redirect('sales:invoice_detail', pk=invoice.pk)
            except Exception as e:
                messages.error(request, f'Error al crear factura: {str(e)}')
    
    context = {'order': order}
    return render(request, 'sales/orders/sales_order_list.html', context)


# Vistas de Facturas (básicas)
@login_required
def invoice_list(request):
    """Lista de facturas"""
    invoices = Invoice.objects.select_related('client').order_by('-invoice_date')
    
    # Filtros
    search = request.GET.get('search', '')
    if search:
        invoices = invoices.filter(
            Q(invoice_number__icontains=search) |
            Q(client__name__icontains=search)
        )
    
    status_filter = request.GET.get('status', '')
    if status_filter:
        invoices = invoices.filter(status=status_filter)
    
    context = {
        'invoices': invoices,
        'search': search,
        'status_filter': status_filter,
    }
    
    return render(request, 'sales/invoices/invoice_list.html', context)


@login_required
def invoice_detail(request, pk):
    """Detalle de factura"""
    invoice = get_object_or_404(Invoice.objects.select_related('client', 'sales_order'), pk=pk)
    
    context = {
        'invoice': invoice,
        'lines': invoice.lines.select_related('product_variant__product').all(),
        'payments': Payment.objects.filter(invoice=invoice).order_by('-payment_date'),
    }
    
    return render(request, 'sales/invoices/invoice_detail.html', context)


# Vistas de Pagos (básicas)
@login_required
def payment_list(request):
    """Lista de pagos"""
    payments = Payment.objects.select_related('client', 'invoice').order_by('-payment_date')
    
    context = {
        'payments': payments,
    }
    
    return render(request, 'sales/payments/payment_list.html', context)


# Vistas de Entregas (básicas)
@login_required
def delivery_order_list(request):
    """Lista de órdenes de entrega"""
    deliveries = DeliveryOrder.objects.select_related('sales_order', 'branch', 'warehouse').order_by('-delivery_date')
    
    context = {
        'deliveries': deliveries,
    }
    
    return render(request, 'sales/deliveries/delivery_list.html', context)


# Vistas de Devoluciones (básicas)
@login_required
def return_delivery_list(request):
    """Lista de devoluciones"""
    returns = ReturnDelivery.objects.select_related('sales_order').order_by('-return_date')
    
    context = {
        'returns': returns,
    }
    
    return render(request, 'sales/returns/return_list.html', context)


# Vistas de Notas de Crédito (básicas)
@login_required
def credit_note_list(request):
    """Lista de notas de crédito"""
    credit_notes = CreditNote.objects.select_related('invoice').order_by('-credit_date')
    
    context = {
        'credit_notes': credit_notes,
    }
    
    return render(request, 'sales/credit_notes/credit_note_list.html', context)


# Vistas de Configuración (básicas)
@login_required
def price_list_list(request):
    """Lista de listas de precios"""
    price_lists = PriceList.objects.all().order_by('-id')
    
    context = {
        'price_lists': price_lists,
    }
    
    return render(request, 'sales/config/price_list_list.html', context)


@login_required
def payment_term_list(request):
    """Lista de condiciones de pago"""
    payment_terms = PaymentTerm.objects.all().order_by('-id')
    
    context = {
        'payment_terms': payment_terms,
    }
    
    return render(request, 'sales/config/payment_term_list.html', context)


# Vistas de Reportes (básicas)
@login_required
def reports_dashboard(request):
    """Dashboard de reportes"""
    return render(request, 'sales/reports/reports.html')


@login_required
def sales_summary_report(request):
    """Reporte de resumen de ventas"""
    return render(request, 'sales/reports/reports_detail.html')


@login_required
def client_analysis_report(request):
    """Reporte de análisis de clientes"""
    return render(request, 'sales/reports/reports_detail.html')


@login_required
def product_performance_report(request):
    """Reporte de rendimiento de productos"""
    return render(request, 'sales/reports/reports_detail.html')


# Vistas placeholder para el resto de funcionalidades
def invoice_create(request):
    context = {'today': timezone.now().date()}
    return render(request, 'sales/invoices/invoice_form.html', context)

def invoice_edit(request, pk):
    context = {'today': timezone.now().date()}
    return render(request, 'sales/invoices/invoice_form.html', context)

def invoice_delete(request, pk):
    return render(request, 'sales/invoices/invoice_list.html')

def invoice_mark_paid(request, pk):
    return render(request, 'sales/invoices/invoice_detail.html')

def invoice_create_payment(request, pk):
    return render(request, 'sales/invoices/invoice_detail.html')

def payment_create(request):
    context = {'today': timezone.now().date()}
    return render(request, 'sales/payments/payment_form.html', context)

def payment_detail(request, pk):
    return render(request, 'sales/payments/payment_detail.html')

def payment_edit(request, pk):
    context = {'today': timezone.now().date()}
    return render(request, 'sales/payments/payment_form.html', context)

def payment_delete(request, pk):
    return render(request, 'sales/payments/payment_list.html')

def delivery_order_create(request):
    return render(request, 'sales/deliveries/delivery_list.html')

def delivery_order_detail(request, pk):
    return render(request, 'sales/deliveries/delivery_detail.html')

def delivery_order_edit(request, pk):
    return render(request, 'sales/deliveries/delivery_list.html')

def delivery_order_delete(request, pk):
    return render(request, 'sales/deliveries/delivery_list.html')

def delivery_order_process(request, pk):
    return render(request, 'sales/deliveries/delivery_detail.html')

def return_delivery_create(request):
    return render(request, 'sales/returns/return_list.html')

def return_delivery_detail(request, pk):
    return render(request, 'sales/returns/return_detail.html')

def return_delivery_edit(request, pk):
    return render(request, 'sales/returns/return_list.html')

def return_delivery_delete(request, pk):
    return render(request, 'sales/returns/return_list.html')

def return_delivery_approve(request, pk):
    return render(request, 'sales/returns/return_detail.html')

def credit_note_create(request):
    return render(request, 'sales/credit_notes/credit_note_list.html')

def credit_note_detail(request, pk):
    return render(request, 'sales/credit_notes/credit_note_detail.html')

def credit_note_edit(request, pk):
    return render(request, 'sales/credit_notes/credit_note_list.html')

def credit_note_delete(request, pk):
    return render(request, 'sales/credit_notes/credit_note_list.html')

def credit_note_apply(request, pk):
    return render(request, 'sales/credit_notes/credit_note_detail.html')

def price_list_create(request):
    return render(request, 'sales/config/price_list_list.html')

def price_list_detail(request, pk):
    return render(request, 'sales/config/price_list_detail.html')

def price_list_edit(request, pk):
    return render(request, 'sales/config/price_list_list.html')

def price_list_delete(request, pk):
    return render(request, 'sales/config/price_list_list.html')

def price_list_deactivate(request, pk):
    return render(request, 'sales/config/price_list_detail.html')

def price_list_activate(request, pk):
    return render(request, 'sales/config/price_list_detail.html')

def price_list_item_add(request, pk):
    return render(request, 'sales/config/price_list_detail.html')

def price_list_item_edit(request, pk):
    return render(request, 'sales/config/price_list_detail.html')

def price_list_item_delete(request, pk):
    return render(request, 'sales/config/price_list_detail.html')

@login_required
def payment_term_create(request):
    if request.method == 'POST':
        form = PaymentTermForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _('Condición de pago creada correctamente.'))
            return redirect('sales:payment_term_list')
    else:
        form = PaymentTermForm()
    return render(request, 'sales/config/payment_terms_form.html', {'form': form, 'is_create': True})

@login_required
def payment_term_edit(request, pk):
    payment_term = get_object_or_404(PaymentTerm, pk=pk)
    if request.method == 'POST':
        form = PaymentTermForm(request.POST, instance=payment_term)
        if form.is_valid():
            form.save()
            messages.success(request, _('Condición de pago actualizada correctamente.'))
            return redirect('sales:payment_term_list')
    else:
        form = PaymentTermForm(instance=payment_term)
    return render(request, 'sales/config/payment_terms_form.html', {'form': form, 'payment_term': payment_term, 'is_create': False})

@login_required
def payment_term_delete(request, pk):
    payment_term = get_object_or_404(PaymentTerm, pk=pk)
    if request.method == 'POST':
        payment_term.delete()
        messages.success(request, _('Condición de pago eliminada correctamente.'))
        return redirect('sales:payment_term_list')
    return render(request, 'sales/config/payment_terms_confirm_delete.html', {'payment_term': payment_term})

@login_required
def payment_term_detail(request, pk):
    payment_term = get_object_or_404(PaymentTerm, pk=pk)
    return render(request, 'sales/config/payment_terms_detail.html', {'payment_term': payment_term})

@login_required
def payment_terms_activate(request, pk):
    payment_term = get_object_or_404(PaymentTerm, pk=pk)
    payment_term.is_active = True
    payment_term.save()
    messages.success(request, _('Condición de pago activada correctamente.'))
    return redirect(reverse('sales:payment_term_detail', args=[pk]))

@login_required
def payment_terms_deactivate(request, pk):
    payment_term = get_object_or_404(PaymentTerm, pk=pk)
    payment_term.is_active = False
    payment_term.save()
    messages.success(request, _('Condición de pago desactivada correctamente.'))
    return redirect(reverse('sales:payment_term_detail', args=[pk]))

@login_required
def payment_term_line_create(request, payment_term_id):
    payment_term = get_object_or_404(PaymentTerm, pk=payment_term_id)
    if request.method == 'POST':
        form = PaymentTermLineForm(request.POST)
        if form.is_valid():
            line = form.save(commit=False)
            line.payment_term = payment_term
            line.save()
            messages.success(request, _('Línea agregada correctamente.'))
            return redirect('sales:payment_term_detail', pk=payment_term_id)
    else:
        form = PaymentTermLineForm()
    return render(request, 'sales/config/payment_term_line_form.html', {'form': form, 'payment_term': payment_term, 'is_create': True})

@login_required
def payment_term_line_edit(request, pk):
    line = get_object_or_404(PaymentTermLine, pk=pk)
    payment_term = line.payment_term
    if request.method == 'POST':
        form = PaymentTermLineForm(request.POST, instance=line)
        if form.is_valid():
            form.save()
            messages.success(request, _('Línea actualizada correctamente.'))
            return redirect('sales:payment_term_detail', pk=payment_term.pk)
    else:
        form = PaymentTermLineForm(instance=line)
    return render(request, 'sales/config/payment_term_line_form.html', {'form': form, 'payment_term': payment_term, 'is_create': False})

@login_required
def payment_term_line_delete(request, pk):
    line = get_object_or_404(PaymentTermLine, pk=pk)
    payment_term = line.payment_term
    if request.method == 'POST':
        line.delete()
        messages.success(request, _('Línea eliminada correctamente.'))
        return redirect('sales:payment_term_detail', pk=payment_term.pk)
    return render(request, 'sales/config/payment_term_line_confirm_delete.html', {'line': line, 'payment_term': payment_term})


class ClientListView(LoginRequiredMixin, SuperuserOrPermissionRequiredMixin, ListView):
    """Vista para listar clientes"""
    model = Client
    template_name = 'sales/clients/client_list.html'
    context_object_name = 'clients'
    permission_required = 'sales.view_client'
    paginate_by = 50
    
    def get_queryset(self):
        queryset = Client.objects.all()
        
        # Aplicar filtros de búsqueda
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(email__icontains=search) |
                Q(tax_id__icontains=search) |
                Q(phone__icontains=search)
            )
        
        # Filtro por tipo
        type_filter = self.request.GET.get('type', '')
        if type_filter:
            queryset = queryset.filter(type=type_filter)
        
        # Filtro por país
        country_filter = self.request.GET.get('country', '')
        if country_filter:
            queryset = queryset.filter(country=country_filter)
        
        # Filtro por estado/provincia
        state_filter = self.request.GET.get('state', '')
        if state_filter:
            queryset = queryset.filter(state=state_filter)
        
        # Filtro por cliente
        is_customer_filter = self.request.GET.get('is_customer', '')
        if is_customer_filter == 'True':
            queryset = queryset.filter(is_customer=True)
        elif is_customer_filter == 'False':
            queryset = queryset.filter(is_customer=False)
        
        # Filtro por proveedor
        is_supplier_filter = self.request.GET.get('is_supplier', '')
        if is_supplier_filter == 'True':
            queryset = queryset.filter(is_supplier=True)
        elif is_supplier_filter == 'False':
            queryset = queryset.filter(is_supplier=False)
        
        # Filtro por estado activo
        is_active_filter = self.request.GET.get('is_active', '')
        if is_active_filter == 'True':
            queryset = queryset.filter(is_active=True)
        elif is_active_filter == 'False':
            queryset = queryset.filter(is_active=False)
        
        # Filtro por vendedor asignado
        assigned_seller_filter = self.request.GET.get('assigned_seller', '')
        if assigned_seller_filter:
            queryset = queryset.filter(
                Q(assigned_seller__nombre__icontains=assigned_seller_filter) |
                Q(assigned_seller__email__icontains=assigned_seller_filter)
            )
        
        return queryset.order_by('-id')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', '')
        context['type_filter'] = self.request.GET.get('type', '')
        context['is_customer_filter'] = self.request.GET.get('is_customer', '')
        context['is_active_filter'] = self.request.GET.get('is_active', '')
        context['total_clients'] = self.get_queryset().count()
        context['active_clients'] = self.get_queryset().filter(is_active=True).count()
        context['customer_clients'] = self.get_queryset().filter(is_customer=True).count()
        context['supplier_clients'] = 0  # Los clientes no son proveedores, eso está en el módulo de compras
        from .forms import ClientSearchForm
        # Solo pasar los campos válidos
        context['search_form'] = ClientSearchForm(self.request.GET)
        
        # Agregar información de permisos para superusuarios y administradores
        user = self.request.user
        is_admin_user = user.is_superuser or (hasattr(user, 'is_admin') and user.is_admin())
        context['is_superuser'] = user.is_superuser
        context['is_admin_user'] = is_admin_user
        context['puede_sales_ver_client'] = is_admin_user or user.has_perm('sales.view_client')
        context['puede_sales_add_client'] = is_admin_user or user.has_perm('sales.add_client')
        context['puede_sales_change_client'] = is_admin_user or user.has_perm('sales.change_client')
        context['puede_sales_delete_client'] = is_admin_user or user.has_perm('sales.delete_client')
        
        return context
    
    def render_to_response(self, context, **response_kwargs):
        """Soporte para formato JSON para búsqueda predictiva"""
        if self.request.GET.get('format') == 'json':
            clients_data = []
            for client in context['clients']:
                if hasattr(client.country, 'name'):
                    country_name = client.country.name
                elif isinstance(client.country, str):
                    country_name = client.country
                else:
                    country_name = None
                assigned_seller_id = getattr(client, 'assigned_seller_id', None)
                assigned_seller_name = None
                if hasattr(client, 'assigned_seller') and getattr(client, 'assigned_seller', None):
                    assigned_seller_name = getattr(client.assigned_seller, 'nombre', None)
                clients_data.append({
                    'id': client.id,
                    'name': client.name,
                    'email': client.email,
                    'phone': client.phone,
                    'tax_id': client.tax_id,
                    'type': client.type,
                    'type_display': client.get_type_display(),
                    'is_active': client.is_active,
                    'is_customer': client.is_customer,
                    'city': client.city,
                    'country_name': country_name,
                    'assigned_seller': assigned_seller_id,
                    'assigned_seller_name': assigned_seller_name,
                })
            
            return JsonResponse({
                'clients': clients_data,
                'total': context['total_clients'],
                'active': context['active_clients'],
                'customers': context['customer_clients'],
                'suppliers': context['supplier_clients'],
            })
        
        return super().render_to_response(context, **response_kwargs)


class ClientDetailView(LoginRequiredMixin, SuperuserOrPermissionRequiredMixin, DetailView):
    """Vista para mostrar detalles de cliente"""
    model = Client
    template_name = 'sales/clients/client_detail.html'
    context_object_name = 'client'
    permission_required = 'sales.view_client'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Obtener contactos usando el sistema de relaciones genéricas
        # TODO: Implement when Contact model is available
        # context['contacts'] = self.object.get_contacts(active_only=True)
        # context['primary_contact'] = self.object.get_primary_contact_object()
        # Obtener pedidos recientes
        context['orders'] = self.object.orders.all().order_by('-created_at')[:10]
        # Estadísticas del cliente
        context['total_orders'] = self.object.orders.count()
        # Obtener facturas y pagos usando consultas directas
        context['total_invoices'] = Invoice.objects.filter(client=self.object).count()
        context['total_payments'] = Payment.objects.filter(client=self.object).count()
        return context


class ClientDeleteView(LoginRequiredMixin, SuperuserOrPermissionRequiredMixin, DeleteView):
    """Vista para eliminar cliente"""
    model = Client
    template_name = 'sales/clients/client_confirm_delete.html'
    permission_required = 'sales.delete_client'
    success_url = reverse_lazy('sales:client_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, _('Client deleted successfully.'))
        return super().delete(request, *args, **kwargs)


# TODO: Implement Contact views when Contact model is available
# class ContactListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
#     """Vista para listar contactos de un cliente"""
#     pass

# class ContactDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
#     """Vista para mostrar detalles de contacto"""
#     pass

# class ContactCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
#     """Vista para crear contacto"""
#     pass

# class ContactUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
#     """Vista para editar contacto"""
#     pass

# class ContactDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
#     """Vista para eliminar contacto"""
#     pass


# Vistas de autocompletado
# def autocomplete_country(request):
#     """Autocompletado de países"""
#     query = request.GET.get('q', '')
#     if len(query) < 2:
#         return JsonResponse({'results': []})
#     
#     countries = Country.objects.filter(
#         Q(name__icontains=query) |
#         Q(name_es__icontains=query) |
#         Q(name_en__icontains=query) |
#         Q(name_pt__icontains=query),
#         is_active=True
#     )[:10]
#     
#     results = [{
#         'id': country.id,
#         'text': country.name,
#         'code': country.code,
#         'phone_code': country.phone_code,
#         'currency_code': country.currency_code,
#         'timezone': country.timezone
#     } for country in countries]
#     
#     return JsonResponse({'results': results})


# def autocomplete_state(request):
#     """Autocompletado de estados/provincias"""
#     query = request.GET.get('q', '')
#     country_id = request.GET.get('country_id')
#     
#     if len(query) < 2:
#         return JsonResponse({'results': []})
#     
#     states = State.objects.filter(
#         Q(name__icontains=query) |
#         Q(name_es__icontains=query) |
#         Q(name_en__icontains=query) |
#         Q(name_pt__icontains=query),
#         is_active=True
#     )
#     
#     if country_id:
#         states = states.filter(country_id=country_id)
#     
#     states = states[:10]
#     
#     results = [{
#         'id': state.id,
#         'text': state.name,
#         'code': state.code,
#         'country_id': state.country.id,
#         'country_name': state.country.name
#     } for state in states]
#     
#     return JsonResponse({'results': results})


def autocomplete_city(request):
    """Autocompletado de ciudades"""
    query = request.GET.get('q', '')
    state_id = request.GET.get('state_id')
    
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    # Buscar en clientes existentes
    clients = Client.objects.filter(
        city__icontains=query,
        city__isnull=False
    ).exclude(city='')
    
    if state_id:
        clients = clients.filter(state_id=state_id)
    
    cities = clients.values_list('city', flat=True).distinct()[:10]
    
    results = [{'id': city, 'text': city} for city in cities]
    
    return JsonResponse({'results': results})


def autocomplete_seller(request):
    """Autocompletado de vendedores"""
    query = request.GET.get('q', '')
    
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    sellers = User.objects.filter(
        Q(nombre__icontains=query) |
        Q(email__icontains=query),
        is_active=True
    )[:10]
    
    results = [{
        'id': seller.id,
        'text': f"{seller.name} ({seller.email})",
        'email': seller.email
    } for seller in sellers]
    
    return JsonResponse({'results': results})


# --- VISTAS PARA PUNTO DE VENTA (TPV) ---

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView, ListView, DetailView
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
import json

from .models import (
    Client, SalesOrder, SalesOrderLine, PriceList, PriceListItem,
    PaymentTerm, PaymentTermLine, Invoice, InvoiceLine, Payment,
    DeliveryOrder, DeliveryOrderLine, ReturnDelivery, CreditNote, ApprovalLog,
    POSSession, POSTerminal, POSSale, POSPayment, POSPromotion,
    PaymentMethod, PaymentProcessor
)
from .api.serializers import (
    ClientSerializer, SalesOrderSerializer, InvoiceSerializer,
    PaymentSerializer, DeliveryOrderSerializer
)
from core.models import Currency
from inventory.models import ProductVariant, Warehouse



@login_required
def pos_dashboard(request):
    """
    Dashboard principal del punto de venta
    """
    # Obtener sesión activa del usuario
    active_session = POSSession.objects.filter(
        operator=request.user,
        state='open'
    ).first()
    
    # Obtener terminales disponibles
    terminals = POSTerminal.objects.filter(
        branch=request.user.branch_activa,
        is_active=True
    )

    # Estadísticas de ventas
    if active_session:
        completed_sales = active_session.sales.filter(state='completed')
        completed_count = completed_sales.count()
        completed_total = completed_sales.aggregate(total=models.Sum('total'))['total'] or 0
        draft_count = active_session.sales.filter(state='draft').count()
    else:
        completed_count = 0
        completed_total = 0
        draft_count = 0

    context = {
        'active_session': active_session,
        'terminals': terminals,
        'user_branch': request.user.branch_activa,
        'completed_count': completed_count,
        'completed_total': completed_total,
        'draft_count': draft_count,
    }
    
    return render(request, 'sales/pos/dashboard.html', context)

@login_required
def pos_session_open(request):
    """
    Abrir sesión de TPV
    """
    if request.method == 'POST':
        terminal_id = request.POST.get('terminal_id')
        opening_amount = float(request.POST.get('opening_amount', 0))
        
        terminal = get_object_or_404(POSTerminal, id=terminal_id)
        
        try:
            pos_service = POSService(request.user, request.user.branch_activa, terminal)
            session = pos_service.open_session(opening_amount)
            
            messages.success(request, f'Sesión {session.number} abierta correctamente')
            return redirect('pos_sale_new')
            
        except ValueError as e:
            messages.error(request, str(e))
            return redirect('pos_dashboard')
    
    return redirect('pos_dashboard')

@login_required
def pos_session_close(request):
    """
    Cerrar sesión de TPV
    """
    if request.method == 'POST':
        session_id = request.POST.get('session_id')
        closing_amount = float(request.POST.get('closing_amount', 0))
        
        session = get_object_or_404(POSSession, id=session_id, operator=request.user)
        
        try:
            pos_service = POSService(request.user, request.user.branch_activa, session.pos_terminal)
            pos_service.current_session = session
            closed_session = pos_service.close_session(closing_amount)
            
            messages.success(request, f'Sesión {closed_session.number} cerrada correctamente')
            return redirect('pos_dashboard')
            
        except ValueError as e:
            messages.error(request, str(e))
            return redirect('pos_dashboard')
    
    return redirect('pos_dashboard')

@login_required
def pos_sale_new(request):
    """
    Nueva venta en TPV
    """
    # Verificar sesión activa
    active_session = POSSession.objects.filter(
        operator=request.user,
        state='open'
    ).first()
    
    if not active_session:
        messages.error(request, 'No hay sesión activa. Abra una sesión primero.')
        return redirect('pos_dashboard')
    
    # Crear nueva venta
    sale_service = POSSaleService(active_session)
    sale = sale_service.create_sale()

    from .models import PriceList
    price_list = PriceList.objects.filter(is_active=True).first()

    context = {
        'sale': sale,
        'session': active_session,
        'price_list': price_list,
    }
    
    return render(request, 'sales/pos/sale_new.html', context)

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def pos_product_search(request):
    """
    API para búsqueda de productos en TPV
    """
    try:
        data = json.loads(request.body)
        search_term = data.get('search_term', '')
        search_type = data.get('search_type', 'barcode')
        price_list_id = data.get('price_list_id')
        
        if not search_term:
            return JsonResponse({'error': 'Término de búsqueda requerido'}, status=400)
        
        price_list = get_object_or_404(PriceList, id=price_list_id)
        product_service = POSProductService(price_list)
        
        if search_type == 'name':
            # Búsqueda por nombre retorna múltiples resultados
            products = product_service.search_product(search_term, search_type)
            return JsonResponse({'products': products})
        else:
            # Búsqueda específica retorna un producto
            product = product_service.search_product(search_term, search_type)
            if product:
                return JsonResponse({'product': product})
            else:
                return JsonResponse({'error': 'Producto no encontrado'}, status=404)
                
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def pos_sale_add_product(request, sale_id):
    """
    API para agregar producto a la venta
    """
    try:
        sale = get_object_or_404(POSSale, id=sale_id, session__operator=request.user)
        data = json.loads(request.body)
        
        product_data = data.get('product')
        quantity = float(data.get('quantity', 1))
        discount_percentage = float(data.get('discount_percentage', 0))
        
        sale_service = POSSaleService(sale.session)
        line = sale_service.add_product(sale, product_data, quantity, discount_percentage)
        
        # Retornar datos actualizados de la venta
        sale.refresh_from_db()
        
        return JsonResponse({
            'success': True,
            'line': {
                'id': line.id,
                'product_name': line.description,
                'quantity': line.quantity,
                'unit_price': line.unit_price,
                'subtotal': line.subtotal,
                'discount_amount': line.discount_amount,
                'tax_amount': line.tax_amount,
            },
            'sale_totals': {
                'subtotal': sale.subtotal,
                'total_discount': sale.total_discount,
                'total_tax': sale.total_tax,
                'total': sale.total,
            }
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@csrf_exempt
@require_http_methods(["DELETE"])
def pos_sale_remove_product(request, sale_id, line_id):
    """
    API para remover producto de la venta
    """
    try:
        sale = get_object_or_404(POSSale, id=sale_id, session__operator=request.user)
        sale_service = POSSaleService(sale.session)
        
        sale_service.remove_product(sale, line_id)
        
        # Retornar datos actualizados de la venta
        sale.refresh_from_db()
        
        return JsonResponse({
            'success': True,
            'sale_totals': {
                'subtotal': sale.subtotal,
                'total_discount': sale.total_discount,
                'total_tax': sale.total_tax,
                'total': sale.total,
            }
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def pos_sale_apply_promotion(request, sale_id):
    """
    API para aplicar promoción a la venta
    """
    try:
        sale = get_object_or_404(POSSale, id=sale_id, session__operator=request.user)
        data = json.loads(request.body)
        
        promotion_code = data.get('promotion_code')
        
        sale_service = POSSaleService(sale.session)
        discount = sale_service.apply_promotion(sale, promotion_code)
        
        # Retornar datos actualizados de la venta
        sale.refresh_from_db()
        
        return JsonResponse({
            'success': True,
            'discount_applied': discount,
            'sale_totals': {
                'subtotal': sale.subtotal,
                'total_discount': sale.total_discount,
                'total_tax': sale.total_tax,
                'total': sale.total,
            }
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def pos_sale_complete(request, sale_id):
    """
    API para completar venta
    """
    try:
        sale = get_object_or_404(POSSale, id=sale_id, session__operator=request.user)
        data = json.loads(request.body)
        
        payments_data = data.get('payments', [])
        client_data = data.get('client', {})
        
        # Actualizar datos del cliente si es ocasional
        if sale.is_occasional_client and client_data:
            sale.occasional_client_data.update(client_data)
            sale.save()
        
        sale_service = POSSaleService(sale.session)
        completed_sale = sale_service.complete_sale(sale, payments_data)
        
        # Imprimir ticket si está configurado
        integration_service = POSIntegrationService(sale.session.pos_terminal)
        receipt_data = integration_service.print_receipt(completed_sale)
        
        return JsonResponse({
            'success': True,
            'sale_number': completed_sale.number,
            'total_paid': completed_sale.total_paid,
            'receipt_data': receipt_data,
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def pos_sale_detail(request, sale_id):
    """
    Detalle de venta de TPV
    """
    sale = get_object_or_404(POSSale, id=sale_id, session__operator=request.user)
    
    context = {
        'sale': sale,
        'lines': sale.lines.all(),
        'payments': sale.payments.all(),
    }
    
    return render(request, 'sales/pos/sale_detail.html', context)

@login_required
def pos_session_report(request, session_id):
    """
    Reporte de sesión de TPV
    """
    session = get_object_or_404(POSSession, id=session_id, operator=request.user)
    report_service = POSReportService(session)
    
    summary = report_service.get_session_summary()
    
    context = {
        'session': session,
        'summary': summary,
        'sales': session.sales.filter(state='completed').order_by('-sale_date'),
    }
    
    return render(request, 'sales/pos/session_report.html', context)

@login_required
def pos_client_search(request):
    """Búsqueda de clientes para TPV"""
    query = request.GET.get('q', '')
    search_type = request.GET.get('type', 'document')
    
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    clients = Client.objects.filter(is_active=True)
    
    if search_type == 'document':
        clients = clients.filter(document_number__icontains=query)
    elif search_type == 'name':
        clients = clients.filter(name__icontains=query)
    elif search_type == 'email':
        clients = clients.filter(email__icontains=query)
    elif search_type == 'phone':
        clients = clients.filter(phone__icontains=query)
    
    results = []
    for client in clients[:10]:  # Limitar a 10 resultados
        results.append({
            'id': client.id,
            'name': client.name,
            'document_number': client.document_number,
            'email': client.email,
            'phone': client.phone,
            'type': client.type,
            'fiscal_responsibility': client.fiscal_responsibility.name if client.fiscal_responsibility else None,
            'display_text': f"{client.name} - {client.document_number}"
        })
    
    return JsonResponse({'results': results})

@login_required
def pos_client_selection(request, sale_id):
    """
    Vista para selección de cliente en TPV
    Permite seleccionar cliente existente o crear cliente ocasional
    """
    try:
        sale = get_object_or_404(POSSale, id=sale_id, session__operator=request.user)
        
        if request.method == 'POST':
            form = POSClientSelectionForm(request.POST)
            if form.is_valid():
                client_data = form.get_client_data()
                
                if client_data['type'] == 'existing':
                    # Cliente existente
                    sale.client = client_data['client']
                    sale.is_occasional_client = False
                    sale.occasional_client_data = None
                else:
                    # Cliente ocasional
                    sale.client = None
                    sale.is_occasional_client = True
                    sale.occasional_client_data = client_data['client_data']
                
                sale.save()
                messages.success(request, _('Cliente asignado correctamente.'))
                return JsonResponse({'success': True, 'redirect': reverse('sales:pos_sale_detail', kwargs={'sale_id': sale.id})})
            else:
                return JsonResponse({'success': False, 'errors': form.errors})
        else:
            form = POSClientSelectionForm()
        
        context = {
            'form': form,
            'sale': sale,
            'clients': Client.objects.filter(is_active=True).order_by('name')[:50]  # Primeros 50 para el dropdown
        }
        
        return render(request, 'sales/pos/client_selection.html', context)
        
    except Exception as e:
        messages.error(request, f'Error al seleccionar cliente: {str(e)}')
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def pos_quick_client_create(request, sale_id):
    """
    Creación rápida de cliente desde TPV
    """
    try:
        sale = get_object_or_404(POSSale, id=sale_id, session__operator=request.user)
        
        if request.method == 'POST':
            # Crear cliente con datos mínimos
            name = request.POST.get('name')
            document_number = request.POST.get('document_number')
            email = request.POST.get('email', '')
            phone = request.POST.get('phone', '')
            
            if not name or not document_number:
                return JsonResponse({'success': False, 'error': 'Nombre y documento son requeridos'})
            
            # Verificar si ya existe un cliente con ese documento
            existing_client = Client.objects.filter(document_number=document_number).first()
            if existing_client:
                return JsonResponse({
                    'success': False, 
                    'error': 'Ya existe un cliente con ese documento',
                    'existing_client': {
                        'id': existing_client.id,
                        'name': existing_client.name,
                        'document_number': existing_client.document_number
                    }
                })
            
            # Crear cliente
            client = Client.objects.create(
                name=name,
                document_number=document_number,
                email=email,
                phone=phone,
                type='individual',  # Por defecto persona
                is_active=True
            )
            
            # Asignar a la venta
            sale.client = client
            sale.is_occasional_client = False
            sale.occasional_client_data = None
            sale.save()
            
            return JsonResponse({
                'success': True,
                'client': {
                    'id': client.id,
                    'name': client.name,
                    'document_number': client.document_number,
                    'email': client.email,
                    'phone': client.phone
                },
                'message': f'Cliente "{client.name}" creado y asignado correctamente.'
            })
        
        return JsonResponse({'success': False, 'error': 'Método no permitido'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def pos_scale_weight(request):
    """
    API para obtener peso de balanza
    """
    try:
        data = json.loads(request.body)
        terminal_id = data.get('terminal_id')
        
        terminal = get_object_or_404(POSTerminal, id=terminal_id)
        integration_service = POSIntegrationService(terminal)
        
        weight_data = integration_service.send_to_scale('get_weight')
        
        return JsonResponse(weight_data)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

class POSSessionListView(LoginRequiredMixin, ListView):
    """
    Lista de sesiones de TPV
    """
    model = POSSession
    template_name = 'sales/pos/session_list.html'
    context_object_name = 'sessions'
    paginate_by = 20
    
    def get_queryset(self):
        return POSSession.objects.filter(
            operator=self.request.user
        ).order_by('-opened_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_session'] = POSSession.objects.filter(
            operator=self.request.user,
            state='open'
        ).first()
        return context

class POSSaleListView(LoginRequiredMixin, ListView):
    """
    Lista de ventas de TPV
    """
    model = POSSale
    template_name = 'sales/pos/sale_list.html'
    context_object_name = 'sales'
    paginate_by = 20
    
    def get_queryset(self):
        return POSSale.objects.filter(
            session__operator=self.request.user
        ).order_by('-sale_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_sales'] = self.get_queryset().count()
        context['total_amount'] = self.get_queryset().aggregate(
            total=models.Sum('total')
        )['total'] or 0
        return context

@login_required
def pos_configuration(request):
    """
    Configuración del TPV
    """
    terminals = POSTerminal.objects.filter(branch=request.user.branch_activa)
    promotions = POSPromotion.objects.filter(is_active=True)
    
    context = {
        'terminals': terminals,
        'promotions': promotions,
    }
    
    return render(request, 'sales/pos/configuration.html', context)

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def pos_validate_stock(request):
    """
    API para validar stock en tiempo real
    """
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        quantity = float(data.get('quantity', 1))
        warehouse_id = data.get('warehouse_id')
        
        # Verificar si el módulo de inventory está disponible
        from django.apps import apps
        inventory_available = apps.is_installed('inventory')
        
        if not inventory_available:
            return JsonResponse({
                'is_valid': True,
                'available_stock': 999999,
                'requested_quantity': quantity,
                'message': "Stock no validado (módulo inventory no activo)"
            })
        
        from inventory.models import ProductVariant, Warehouse
        
        product = get_object_or_404(ProductVariant, id=product_id)
        warehouse = get_object_or_404(Warehouse, id=warehouse_id) if warehouse_id else None
        
        available_stock = product.get_available_stock(warehouse)
        is_valid = available_stock >= quantity
        
        return JsonResponse({
            'is_valid': is_valid,
            'available_stock': available_stock,
            'requested_quantity': quantity,
            'message': f"Stock disponible: {available_stock}" if is_valid else f"Stock insuficiente. Disponible: {available_stock}"
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def pos_calculate_totals(request):
    """
    API para calcular totales de la venta
    """
    try:
        data = json.loads(request.body)
        lines = data.get('lines', [])
        discount_percentage = float(data.get('discount_percentage', 0))
        
        subtotal = sum(line['subtotal'] for line in lines)
        discount_amount = subtotal * (discount_percentage / 100)
        tax_amount = (subtotal - discount_amount) * 0.21  # IVA 21%
        total = subtotal - discount_amount + tax_amount
        
        return JsonResponse({
            'subtotal': subtotal,
            'discount_amount': discount_amount,
            'tax_amount': tax_amount,
            'total': total,
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# --- VISTAS PARA ADMINISTRACIÓN DE MEDIOS DE PAGO ---

@login_required
def payment_method_list(request):
    """Lista de medios de pago"""
    try:
        user_extended = UsuarioExtendido.objects.get(user=request.user)
        empresa = user_extended.empresa_activa
        
        if not empresa:
            messages.error(request, "No se pudo determinar la empresa activa")
            return redirect('core:dashboard')
        
        payment_methods = PaymentMethod.objects.filter(
            empresa=empresa
        ).order_by('order', 'name')
        
        context = {
            'payment_methods': payment_methods,
            'empresa': empresa,
        }
        
        return render(request, 'sales/payment_methods/payment_method_list.html', context)
        
    except Exception as e:
        messages.error(request, f"Error al cargar medios de pago: {str(e)}")
        return redirect('sales:dashboard')


@login_required
def payment_method_create(request):
    """Crear nuevo medio de pago"""
    try:
        user_extended = UsuarioExtendido.objects.get(user=request.user)
        empresa = user_extended.empresa_activa
        
        if not empresa:
            messages.error(request, "No se pudo determinar la empresa activa")
            return redirect('payment_method_list')
        
        if request.method == 'POST':
            form = PaymentMethodForm(request.POST)
            if form.is_valid():
                payment_method = form.save(commit=False)
                payment_method.empresa = empresa
                payment_method.created_by = user_extended
                payment_method.updated_by = user_extended
                payment_method.save()
                form.save_m2m()  # Guardar relaciones many-to-many
                
                messages.success(request, f"Medio de pago '{payment_method.name}' creado exitosamente")
                return redirect('sales:payment_method_list')
        else:
            form = PaymentMethodForm(initial={'empresa': empresa})
        
        context = {
            'form': form,
            'empresa': empresa,
            'action': 'create'
        }
        
        return render(request, 'sales/payment_methods/payment_method_form.html', context)
        
    except Exception as e:
        messages.error(request, f"Error al crear medio de pago: {str(e)}")
        return redirect('sales:payment_method_list')


@login_required
def payment_method_edit(request, pk):
    """Editar medio de pago"""
    try:
        user_extended = UsuarioExtendido.objects.get(user=request.user)
        empresa = user_extended.empresa_activa
        
        if not empresa:
            messages.error(request, "No se pudo determinar la empresa activa")
            return redirect('sales:payment_method_list')
        
        payment_method = get_object_or_404(
            PaymentMethod,
            pk=pk,
            empresa=empresa
        )
        
        if request.method == 'POST':
            form = PaymentMethodForm(request.POST, instance=payment_method)
            if form.is_valid():
                payment_method = form.save(commit=False)
                payment_method.updated_by = user_extended
                payment_method.save()
                form.save_m2m()
                
                messages.success(request, f"Medio de pago '{payment_method.name}' actualizado exitosamente")
                return redirect('sales:payment_method_list')
        else:
            form = PaymentMethodForm(instance=payment_method)
        
        context = {
            'form': form,
            'payment_method': payment_method,
            'empresa': empresa,
            'action': 'edit'
        }
        
        return render(request, 'sales/payment_methods/payment_method_form.html', context)
        
    except Exception as e:
        messages.error(request, f"Error al editar medio de pago: {str(e)}")
        return redirect('sales:payment_method_list')


@login_required
def payment_method_delete(request, pk):
    """Eliminar medio de pago"""
    try:
        user_extended = UsuarioExtendido.objects.get(user=request.user)
        empresa = user_extended.empresa_activa
        
        if not empresa:
            messages.error(request, "No se pudo determinar la empresa activa")
            return redirect('sales:payment_method_list')
        
        payment_method = get_object_or_404(
            PaymentMethod,
            pk=pk,
            empresa=empresa
        )
        
        if request.method == 'POST':
            name = payment_method.name
            payment_method.delete()
            messages.success(request, f"Medio de pago '{name}' eliminado exitosamente")
            return redirect('sales:payment_method_list')
        
        context = {
            'payment_method': payment_method,
            'empresa': empresa,
        }
        
        return render(request, 'sales/payment_methods/payment_method_confirm_delete.html', context)
        
    except Exception as e:
        messages.error(request, f"Error al eliminar medio de pago: {str(e)}")
        return redirect('sales:payment_method_list')


@login_required
def payment_method_detail(request, pk):
    """Detalle de medio de pago"""
    try:
        user_extended = UsuarioExtendido.objects.get(user=request.user)
        empresa = user_extended.empresa_activa
        
        if not empresa:
            messages.error(request, "No se pudo determinar la empresa activa")
            return redirect('sales:payment_method_list')
        
        payment_method = get_object_or_404(
            PaymentMethod,
            pk=pk,
            empresa=empresa
        )
        
        # Obtener estadísticas de uso
        usage_stats = {
            'total_transactions': POSPayment.objects.filter(
                payment_method=payment_method.code
            ).count(),
            'total_amount': POSPayment.objects.filter(
                payment_method=payment_method.code
            ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00'),
        }
        
        context = {
            'payment_method': payment_method,
            'empresa': empresa,
            'usage_stats': usage_stats,
        }
        
        return render(request, 'sales/payment_methods/payment_method_detail.html', context)
        
    except Exception as e:
        messages.error(request, f"Error al cargar detalle: {str(e)}")
        return redirect('sales:payment_method_list')


@login_required
def payment_processor_list(request):
    """Lista de procesadores de pago"""
    try:
        user_extended = UsuarioExtendido.objects.get(user=request.user)
        empresa = user_extended.empresa_activa
        
        if not empresa:
            messages.error(request, "No se pudo determinar la empresa activa")
            return redirect('core:dashboard')
        
        processors = PaymentProcessor.objects.filter(
            empresa=empresa
        ).order_by('name')
        
        context = {
            'processors': processors,
            'empresa': empresa,
        }
        
        return render(request, 'sales/payment_processors/processor_list.html', context)
        
    except Exception as e:
        messages.error(request, f"Error al cargar procesadores: {str(e)}")
        return redirect('sales:dashboard')


@login_required
def payment_processor_create(request):
    """Crear nuevo procesador de pago"""
    try:
        user_extended = UsuarioExtendido.objects.get(user=request.user)
        empresa = user_extended.empresa_activa
        
        if not empresa:
            messages.error(request, "No se pudo determinar la empresa activa")
            return redirect('sales:payment_processor_list')
        
        if request.method == 'POST':
            form = PaymentProcessorForm(request.POST)
            if form.is_valid():
                processor = form.save(commit=False)
                processor.empresa = empresa
                processor.save()
                
                messages.success(request, f"Procesador '{processor.name}' creado exitosamente")
                return redirect('sales:payment_processor_list')
        else:
            form = PaymentProcessorForm(initial={'empresa': empresa})
        
        context = {
            'form': form,
            'empresa': empresa,
            'action': 'create'
        }
        
        return render(request, 'sales/payment_processors/processor_form.html', context)
        
    except Exception as e:
        messages.error(request, f"Error al crear procesador: {str(e)}")
        return redirect('sales:payment_processor_list')


@login_required
def payment_processor_edit(request, pk):
    """Editar procesador de pago"""
    try:
        user_extended = UsuarioExtendido.objects.get(user=request.user)
        empresa = user_extended.empresa_activa
        
        if not empresa:
            messages.error(request, "No se pudo determinar la empresa activa")
            return redirect('sales:payment_processor_list')
        
        processor = get_object_or_404(
            PaymentProcessor,
            pk=pk,
            empresa=empresa
        )
        
        if request.method == 'POST':
            form = PaymentProcessorForm(request.POST, instance=processor)
            if form.is_valid():
                processor = form.save()
                messages.success(request, f"Procesador '{processor.name}' actualizado exitosamente")
                return redirect('sales:payment_processor_list')
        else:
            form = PaymentProcessorForm(instance=processor)
        
        context = {
            'form': form,
            'processor': processor,
            'empresa': empresa,
            'action': 'edit'
        }
        
        return render(request, 'sales/payment_processors/processor_form.html', context)
        
    except Exception as e:
        messages.error(request, f"Error al editar procesador: {str(e)}")
        return redirect('sales:payment_processor_list')


@login_required
def payment_processor_delete(request, pk):
    """Eliminar procesador de pago"""
    try:
        user_extended = UsuarioExtendido.objects.get(user=request.user)
        empresa = user_extended.empresa_activa
        
        if not empresa:
            messages.error(request, "No se pudo determinar la empresa activa")
            return redirect('sales:payment_processor_list')
        
        processor = get_object_or_404(
            PaymentProcessor,
            pk=pk,
            empresa=empresa
        )
        
        if request.method == 'POST':
            name = processor.name
            processor.delete()
            messages.success(request, f"Procesador '{name}' eliminado exitosamente")
            return redirect('sales:payment_processor_list')
        
        context = {
            'processor': processor,
            'empresa': empresa,
        }
        
        return render(request, 'sales/payment_processors/processor_confirm_delete.html', context)
        
    except Exception as e:
        messages.error(request, f"Error al eliminar procesador: {str(e)}")
        return redirect('sales:payment_processor_list')


def client_contacts_step(request, client_id=None):
    """Vista para el paso de gestión de contactos en el wizard"""
    if request.method == 'POST':
        form = ContactManagementForm(request.POST)
        if form.is_valid():
            # Obtener el cliente (si existe)
            client = None
            if client_id:
                try:
                    client = Client.objects.get(id=client_id)
                except Client.DoesNotExist:
                    return JsonResponse({'error': 'Cliente no encontrado'}, status=404)
            
            # Crear el contacto y la relación
            try:
                contact, relationship = form.save_contact(client)
                return JsonResponse({
                    'success': True,
                    'contact': {
                        'id': contact.id,
                        'name': contact.display_name,
                        'email': contact.email,
                        'phone': contact.phone,
                        'position': contact.position,
                        'relationship_type': relationship.relationship_type,
                        'relationship_id': relationship.id,
                    }
                })
            except Exception as e:
                return JsonResponse({'error': str(e)}, status=500)
        else:
            return JsonResponse({'error': 'Datos inválidos', 'errors': form.errors}, status=400)
    else:
        form = ContactManagementForm()
    
    # Obtener contactos existentes si es edición
    existing_contacts = []
    if client_id:
        try:
            client = Client.objects.get(id=client_id)
            existing_contacts = client.get_contacts()
        except Client.DoesNotExist:
            pass
    
    context = {
        'form': form,
        'existing_contacts': existing_contacts,
        'client_id': client_id,
    }
    
    return render(request, 'sales/clients/contacts_step.html', context)


def search_contacts_api(request):
    """API para buscar contactos existentes"""
    query = request.GET.get('q', '')
    if not query or len(query) < 2:
        return JsonResponse({'results': []})
    
    contacts = Contact.objects.filter(
        models.Q(name__icontains=query) |
        models.Q(first_name__icontains=query) |
        models.Q(last_name__icontains=query) |
        models.Q(email__icontains=query) |
        models.Q(company_name__icontains=query)
    ).filter(is_active=True)[:10]
    
    results = []
    for contact in contacts:
        results.append({
            'id': contact.id,
            'name': contact.display_name,
            'email': contact.email,
            'phone': contact.phone,
            'position': contact.position,
            'company_name': contact.company_name,
        })
    
    return JsonResponse({'results': results})


def add_contact_to_client(request, client_id):
    """API para agregar un contacto a un cliente"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        client = Client.objects.get(id=client_id)
    except Client.DoesNotExist:
        return JsonResponse({'error': 'Client not found'}, status=404)
    
    contact_id = request.POST.get('contact_id')
    relationship_type = request.POST.get('relationship_type', 'secondary')
    
    if not contact_id:
        return JsonResponse({'error': 'Contact ID is required'}, status=400)
    
    try:
        contact = Contact.objects.get(id=contact_id)
    except Contact.DoesNotExist:
        return JsonResponse({'error': 'Contact not found'}, status=404)
    
    # Verificar que no exista ya la relación
    if client.has_contact(contact, relationship_type):
        return JsonResponse({'error': 'Contact already has this relationship type'}, status=400)
    
    # Agregar la relación
    relationship = client.add_contact(contact, relationship_type)
    
    return JsonResponse({
        'success': True,
        'relationship_id': relationship.id,
        'contact': {
            'id': contact.id,
            'name': contact.display_name,
            'email': contact.email,
            'phone': contact.phone,
            'position': contact.position,
            'relationship_type': relationship_type,
        }
    })


def remove_contact_from_client(request, client_id, relationship_id):
    """API para remover un contacto de un cliente"""
    if request.method != 'DELETE':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        client = Client.objects.get(id=client_id)
    except Client.DoesNotExist:
        return JsonResponse({'error': 'Client not found'}, status=404)
    
    try:
        relationship = ContactRelationship.objects.get(
            id=relationship_id,
            content_type=ContentType.objects.get_for_model(Client),
            object_id=client_id
        )
        relationship.delete()
        return JsonResponse({'success': True})
    except ContactRelationship.DoesNotExist:
        return JsonResponse({'error': 'Relationship not found'}, status=404)


def create_contact_for_client(request, client_id):
    """API para crear un nuevo contacto y agregarlo al cliente"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        client = Client.objects.get(id=client_id)
    except Client.DoesNotExist:
        return JsonResponse({'error': 'Client not found'}, status=404)
    
    # Crear el nuevo contacto
    contact_data = {
        'name': request.POST.get('name'),
        'email': request.POST.get('email'),
        'phone': request.POST.get('phone'),
        'position': request.POST.get('position'),
        'company_name': client.name if client.type == 'company' else '',
        'empresa': client.empresa,
    }
    
    # Validar datos requeridos
    if not contact_data['name']:
        return JsonResponse({'error': 'Contact name is required'}, status=400)
    if not contact_data['email'] and not contact_data['phone']:
        return JsonResponse({'error': 'Contact must have email or phone'}, status=400)
    
    # Crear el contacto
    contact = Contact.objects.create(**contact_data)
    
    # Agregar la relación
    relationship_type = request.POST.get('relationship_type', 'secondary')
    relationship = client.add_contact(contact, relationship_type)
    
    return JsonResponse({
        'success': True,
        'contact': {
            'id': contact.id,
            'name': contact.display_name,
            'email': contact.email,
            'phone': contact.phone,
            'position': contact.position,
            'relationship_type': relationship_type,
        }
    })


# --- WIZARD DE CLIENTES MULTI-STEP (NUEVO FLUJO) ---

@login_required
def client_wizard_view(request):
    """Vista principal del wizard multi-step de creación de clientes (nuevo flujo)"""
    if request.method == 'POST':
        step = request.POST.get('step', '1')
        if step == '1':
            return process_wizard_step1(request)
        elif step == '2':
            return process_wizard_step2(request)
        elif step == '3':
            return process_wizard_step3(request)
        elif step == '4':
            return process_wizard_step4(request)
        elif step == '5':
            return process_wizard_step5(request)
    return show_wizard_step1(request)


def show_wizard_step1(request):
    """Paso 1: Selección de tipo de cliente"""
    form = ClientWizardStep1Form()
    context = {
        'form': form,
        'step': 1,
        'total_steps': 5,
        'step_title': _('Tipo de Cliente'),
        'step_description': _('Selecciona el tipo de cliente'),
    }
    return render(request, 'sales/clients/wizard/step1_client_type.html', context)


def process_wizard_step1(request):
    """Procesar paso 1: Solo tipo de cliente"""
    form = ClientWizardStep1Form(request.POST)
    if form.is_valid():
        # Guardar solo el tipo de cliente
        request.session['wizard_data'] = {'step1': {'client_type': form.cleaned_data['client_type']}}
        return redirect('sales:wizard_step', step=2)
    else:
        context = {
            'form': form,
            'step': 1,
            'total_steps': 5,
            'step_title': _('Tipo de Cliente'),
            'step_description': _('Selecciona el tipo de cliente'),
        }
        return render(request, 'sales/clients/wizard/step1_client_type.html', context)


def show_wizard_step2(request):
    """Paso 2: Datos principales según tipo"""
    wizard_data = request.session.get('wizard_data', {})
    step1_data = wizard_data.get('step1', {})
    client_type = step1_data.get('client_type', 'individual')
    
    # Pre-llenar con datos del paso anterior si existen
    initial_data = {'client_type': client_type}
    if step1_data:
        initial_data.update(step1_data)
    
    # Pre-llenar país y estado según la empresa activa del usuario
    if hasattr(request.user, 'empresa_activa') and request.user.empresa_activa:
        empresa = request.user.empresa_activa
        if empresa.pais:
            initial_data['country'] = empresa.pais
        if empresa.ciudad:
            initial_data['state'] = empresa.ciudad
    
    form = ClientWizardStep2Form(initial=initial_data)
    form.request = request  # Pasar el request al formulario
    
    context = {
        'form': form,
        'step': 2,
        'total_steps': 5,
        'step_title': _('Datos del Cliente'),
        'step_description': _('Completa los datos fundamentales del cliente según el tipo seleccionado.'),
        'client_type': client_type,
    }
    return render(request, 'sales/clients/wizard/step2_basic_info.html', context)


def process_wizard_step2(request):
    """Procesar paso 2: Datos principales"""
    wizard_data = request.session.get('wizard_data', {})
    step1_data = wizard_data.get('step1', {})
    client_type = step1_data.get('client_type', 'individual')
    
    # Pre-llenar con datos del paso anterior
    initial_data = {'client_type': client_type}
    if step1_data:
        initial_data.update(step1_data)
    
    form = ClientWizardStep2Form(request.POST, initial=initial_data)
    form.request = request  # Pasar el request al formulario
    
    # Debug: Imprimir información del formulario
    print(f"POST data: {request.POST}")
    print(f"Form is valid: {form.is_valid()}")
    if not form.is_valid():
        print(f"Form errors: {form.errors}")
        print(f"Form non_field_errors: {form.non_field_errors()}")
    
    if form.is_valid():
        wizard_data['step2'] = form.cleaned_data
        request.session['wizard_data'] = wizard_data
        print(f"Wizard data saved: {wizard_data}")
        return redirect('sales:wizard_step', step=3)
    else:
        context = {
            'form': form,
            'step': 2,
            'total_steps': 5,
            'step_title': _('Datos del Cliente'),
            'step_description': _('Completa los datos fundamentales del cliente según el tipo seleccionado.'),
            'client_type': client_type,
        }
        return render(request, 'sales/clients/wizard/step2_basic_info.html', context)


def show_wizard_step3(request):
    """Paso 3: Configuración comercial y contacto"""
    wizard_data = request.session.get('wizard_data', {})
    step1_data = wizard_data.get('step1', {})
    step2_data = wizard_data.get('step2', {})
    client_type = step1_data.get('client_type', 'individual')
    form = ClientWizardStep3Form(initial=step2_data)
    context = {
        'form': form,
        'step': 3,
        'total_steps': 5,
        'step_title': _('Configuración Comercial y Contacto'),
        'step_description': _('Completa la configuración comercial y datos de contacto.'),
        'client_type': client_type,
    }
    return render(request, 'sales/clients/wizard/step3_contact_info.html', context)


def process_wizard_step3(request):
    """Procesar paso 3: Configuración comercial y contacto"""
    wizard_data = request.session.get('wizard_data', {})
    step1_data = wizard_data.get('step1', {})
    client_type = step1_data.get('client_type', 'individual')
    form = ClientWizardStep3Form(request.POST)
    if form.is_valid():
        wizard_data['step3'] = form.cleaned_data
        request.session['wizard_data'] = wizard_data
        return redirect('sales:wizard_step', step=4)
    else:
        context = {
            'form': form,
            'step': 3,
            'total_steps': 5,
            'step_title': _('Configuración Comercial y Contacto'),
            'step_description': _('Completa la configuración comercial y datos de contacto.'),
            'client_type': client_type,
        }
        return render(request, 'sales/clients/wizard/step3_contact_info.html', context)


def show_wizard_step4(request):
    """Paso 4: Contactos relacionados"""
    wizard_data = request.session.get('wizard_data', {})
    step1_data = wizard_data.get('step1', {})
    client_type = step1_data.get('client_type', 'individual')
    # Obtener contactos relacionados (si el cliente ya existe)
    client_id = request.session.get('wizard_client_id')
    related_contacts = []
    if client_id:
        try:
            client = Client.objects.get(id=client_id)
            related_contacts = client.get_contacts_by_type()
        except Client.DoesNotExist:
            pass
    contact_form = ContactManagementForm()
    search_form = ContactSearchForm()
    relationship_form = ContactRelationshipForm()
    requires_primary_contact = client_type == 'company'
    has_primary_contact = any(
        contact.get('relationship_type') == 'primary' 
        for contact in related_contacts
    )
    context = {
        'step': 4,
        'total_steps': 5,
        'step_title': _('Contactos Relacionados'),
        'step_description': _('Agrega contactos relacionados al cliente'),
        'client_type': client_type,
        'contact_form': contact_form,
        'search_form': search_form,
        'relationship_form': relationship_form,
        'related_contacts': related_contacts,
        'requires_primary_contact': requires_primary_contact,
        'has_primary_contact': has_primary_contact,
        'can_proceed': not requires_primary_contact or has_primary_contact,
    }
    return render(request, 'sales/clients/wizard/step4_contacts.html', context)


def process_wizard_step4(request):
    """Procesar paso 4: Contactos relacionados"""
    wizard_data = request.session.get('wizard_data', {})
    step1_data = wizard_data.get('step1', {})
    client_type = step1_data.get('client_type', 'individual')
    requires_primary_contact = client_type == 'company'
    if requires_primary_contact:
        client_id = request.session.get('wizard_client_id')
        has_primary_contact = False
        if client_id:
            try:
                client = Client.objects.get(id=client_id)
                has_primary_contact = client.get_contacts_by_type().filter(
                    relationship_type='primary'
                ).exists()
            except Client.DoesNotExist:
                pass
        if not has_primary_contact:
            messages.error(request, _('Las empresas deben tener al menos un contacto principal.'))
            return redirect('sales:wizard_step', step=4)
    return redirect('sales:wizard_step', step=5)


def show_wizard_step5(request):
    """Paso 5: Resumen y confirmación"""
    wizard_data = request.session.get('wizard_data', {})
    step1_data = wizard_data.get('step1', {})
    step2_data = wizard_data.get('step2', {})
    step3_data = wizard_data.get('step3', {})
    context = {
        'step': 5,
        'total_steps': 5,
        'step_title': _('Resumen y Confirmación'),
        'step_description': _('Revisa la información y confirma la creación'),
        'client_type': step1_data.get('client_type', 'individual'),
        'step1_data': step1_data,
        'step2_data': step2_data,
        'step3_data': step3_data,
    }
    return render(request, 'sales/clients/wizard/step5_summary.html', context)


def process_wizard_step5(request):
    """Procesar paso 5: Crear cliente final"""
    wizard_data = request.session.get('wizard_data', {})
    if not wizard_data:
        messages.error(request, _('No hay datos del wizard. Por favor, comienza de nuevo.'))
        return redirect('sales:client_wizard')
    try:
        all_data = {}
        for step_data in wizard_data.values():
            all_data.update(step_data)
        # Usar el form adecuado para crear el cliente
        form = ClientWizardStep2Form(all_data)
        if form.is_valid():
            client = form.save(commit=False)
            if hasattr(request.user, 'empresa_activa') and request.user.empresa_activa:
                client.empresa = request.user.empresa_activa
            client.save()
            if 'wizard_data' in request.session:
                del request.session['wizard_data']
            messages.success(request, _('Cliente creado exitosamente.'))
            return redirect('sales:client_detail', pk=client.pk)
        else:
            messages.error(request, _('Error al crear el cliente. Por favor, revisa los datos.'))
            return redirect('sales:client_wizard')
    except Exception as e:
        messages.error(request, f'Error inesperado: {str(e)}')
        return redirect('sales:client_wizard')


@login_required
def wizard_step_navigation(request, step):
    if step == 1:
        return show_wizard_step1(request)
    elif step == 2:
        return show_wizard_step2(request)
    elif step == 3:
        return show_wizard_step3(request)
    elif step == 4:
        return show_wizard_step4(request)
    elif step == 5:
        return show_wizard_step5(request)
    else:
        return redirect('sales:client_wizard')


# APIs para carga dinámica de datos
@login_required
@require_http_methods(['GET'])
def get_states_by_country(request):
    """API para obtener estados por país"""
    country_id = request.GET.get('country_id')
    
    if not country_id:
        return JsonResponse({'states': []})
    
    try:
        states = State.objects.filter(
            country_id=country_id,
            is_active=True
        ).values('id', 'name')
        
        return JsonResponse({'states': list(states)})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_http_methods(['GET'])
def get_fiscal_responsibilities_by_country(request):
    """API para obtener responsabilidades fiscales por país"""
    country_id = request.GET.get('country_id')
    country_name = request.GET.get('country_name')
    
    if not country_id and not country_name:
        return JsonResponse({'responsibilities': []})
    
    try:
        if country_id:
            # Búsqueda por ID
            responsibilities = FiscalResponsibility.objects.filter(
                country_id=country_id,
                is_active=True
            ).values('id', 'name', 'code', 'description')
        elif country_name:
            # Búsqueda por nombre de país
            responsibilities = FiscalResponsibility.objects.filter(
                country__name__icontains=country_name,
                is_active=True
            ).values('id', 'name', 'code', 'description')
        else:
            responsibilities = []
        
        return JsonResponse({'responsibilities': list(responsibilities)})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_http_methods(['GET'])
def countries_autocomplete(request):
    """API para autocomplete de países"""
    query = request.GET.get('q', '').strip()
    
    try:
        if query:
            # Búsqueda más flexible: por nombre, código o nombre en español
            countries = Country.objects.filter(
                models.Q(name__icontains=query) |
                models.Q(name_es__icontains=query) |
                models.Q(code__icontains=query),
                is_active=True
            ).values('id', 'name', 'code', 'name_es')[:10]  # Limitar a 10 resultados
        else:
            # Si no hay consulta, devolver todos los países activos
            countries = Country.objects.filter(
                is_active=True
            ).values('id', 'name', 'code', 'name_es')[:20]  # Limitar a 20 resultados para la lista completa
        
        results = []
        for country in countries:
            # Priorizar el nombre en español si está disponible
            display_name = country.get('name_es') or country['name']
            results.append({
                'id': country['id'],
                'text': display_name,
                'code': country['code'],
                'original_name': country['name']
            })
        
        return JsonResponse({'results': results})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_http_methods(['GET'])
def states_autocomplete(request):
    """API para autocomplete de estados/provincias"""
    query = request.GET.get('q', '').strip()
    country_name = request.GET.get('country', '').strip()
    
    try:
        states_query = State.objects.filter(is_active=True)
        
        # Si se especifica un país, filtrar por él
        if country_name:
            states_query = states_query.filter(
                models.Q(country__name__icontains=country_name) |
                models.Q(country__name_es__icontains=country_name) |
                models.Q(country__code__icontains=country_name)
            )
        
        if query:
            # Si hay consulta, filtrar por ella
            states_query = states_query.filter(
                models.Q(name__icontains=query) |
                models.Q(name_es__icontains=query) |
                models.Q(code__icontains=query)
            )
            limit = 10
        else:
            # Si no hay consulta, devolver todos los estados del país (si se especificó)
            limit = 20
        
        states = states_query.values('id', 'name', 'code', 'name_es', 'country__name', 'country__name_es')[:limit]
        
        results = []
        for state in states:
            # Priorizar nombres en español si están disponibles
            state_name = state.get('name_es') or state['name']
            country_name_display = state.get('country__name_es') or state['country__name']
            
            results.append({
                'id': state['id'],
                'text': f"{state_name}, {country_name_display}",
                'name': state_name,
                'code': state['code'],
                'country': country_name_display,
                'original_name': state['name']
            })
        
        return JsonResponse({'results': results})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_http_methods(['GET'])
def fiscal_responsibilities_autocomplete(request):
    """API para autocomplete de responsabilidades fiscales"""
    query = request.GET.get('q', '').strip()
    country_name = request.GET.get('country', '').strip()
    
    try:
        responsibilities_query = FiscalResponsibility.objects.filter(is_active=True)
        
        # Si se especifica un país, filtrar por él
        if country_name:
            responsibilities_query = responsibilities_query.filter(
                models.Q(country__name__icontains=country_name) |
                models.Q(country__name_es__icontains=country_name) |
                models.Q(country__code__icontains=country_name)
            )
        
        if query:
            # Si hay consulta, filtrar por ella
            responsibilities_query = responsibilities_query.filter(
                models.Q(name__icontains=query) |
                models.Q(code__icontains=query) |
                models.Q(description__icontains=query)
            )
            limit = 10
        else:
            # Si no hay consulta, devolver todas las responsabilidades del país (si se especificó)
            limit = 20
        
        responsibilities = responsibilities_query.values(
            'id', 'name', 'code', 'description', 
            'country__name', 'country__name_es'
        )[:limit]
        
        results = []
        for resp in responsibilities:
            country_name_display = resp.get('country__name_es') or resp['country__name']
            
            results.append({
                'id': resp['id'],
                'text': f"{resp['name']} ({resp['code']})",
                'name': resp['name'],
                'code': resp['code'],
                'description': resp['description'],
                'country': country_name_display
            })
        
        return JsonResponse({'results': results})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


class ClientCreateView(LoginRequiredMixin, SuperuserOrPermissionRequiredMixin, CreateView):
    model = Client
    form_class = ClientWizardStep1Form  # Puedes ajustar el formulario según corresponda
    template_name = 'sales/clients/client_form.html'
    permission_required = 'sales.add_client'
    success_url = reverse_lazy('sales:client_list')

    def form_valid(self, form):
        messages.success(self.request, _('Cliente creado correctamente.'))
        return super().form_valid(form)

class ClientUpdateView(LoginRequiredMixin, SuperuserOrPermissionRequiredMixin, UpdateView):
    model = Client
    form_class = ClientWizardStep1Form  # Puedes ajustar el formulario según corresponda
    template_name = 'sales/clients/client_form.html'
    permission_required = 'sales.change_client'
    success_url = reverse_lazy('sales:client_list')

    def form_valid(self, form):
        messages.success(self.request, _('Cliente actualizado correctamente.'))
        return super().form_valid(form)

@login_required
@require_http_methods(['GET'])
def payment_terms_autocomplete(request):
    """API para autocomplete de condiciones de pago"""
    query = request.GET.get('q', '').strip()
    try:
        if query:
            payment_terms = PaymentTerm.objects.filter(
                models.Q(name__icontains=query) | models.Q(description__icontains=query),
                is_active=True
            ).values('id', 'name')[:10]
        else:
            payment_terms = PaymentTerm.objects.filter(is_active=True).values('id', 'name')[:20]
        results = [
            {'id': pt['id'], 'text': pt['name']} for pt in payment_terms
        ]
        return JsonResponse({'results': results})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

class ClientTagListView(LoginRequiredMixin, SuperuserOrPermissionRequiredMixin, ListView):
    model = ClientTag
    template_name = 'sales/clients/tags/tag_list.html'
    context_object_name = 'tags'
    permission_required = 'sales.view_clienttag'
    paginate_by = 50

    def get_queryset(self):
        empresa = self.request.user.empresa_activa
        return ClientTag.objects.filter(empresa=empresa).order_by('name')

class ClientTagCreateView(LoginRequiredMixin, SuperuserOrPermissionRequiredMixin, CreateView):
    model = ClientTag
    form_class = ClientTagForm
    template_name = 'sales/clients/tags/tag_form.html'
    permission_required = 'sales.add_clienttag'
    success_url = reverse_lazy('sales:client_tag_list')

    def form_valid(self, form):
        form.instance.empresa = self.request.user.empresa_activa
        return super().form_valid(form)

class ClientTagUpdateView(LoginRequiredMixin, SuperuserOrPermissionRequiredMixin, UpdateView):
    model = ClientTag
    form_class = ClientTagForm
    template_name = 'sales/clients/tags/tag_form.html'
    permission_required = 'sales.change_clienttag'
    success_url = reverse_lazy('sales:client_tag_list')

class ClientTagDeleteView(LoginRequiredMixin, SuperuserOrPermissionRequiredMixin, DeleteView):
    model = ClientTag
    template_name = 'sales/clients/tags/tag_confirm_delete.html'
    permission_required = 'sales.delete_clienttag'
    success_url = reverse_lazy('sales:client_tag_list')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.is_active = False
        self.object.save()
        return super().delete(request, *args, **kwargs)

class ClientFormTabsView(LoginRequiredMixin, SuperuserOrPermissionRequiredMixin, CreateView):
    model = Client
    form_class = ClientForm
    template_name = 'sales/clients/client_form_tabs.html'
    permission_required = 'sales.add_client'
    success_url = reverse_lazy('sales:client_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['empresa'] = getattr(self.request.user, 'empresa_activa', None)
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['client'] = self.object if hasattr(self, 'object') and self.object else None
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        if form.is_valid():
            self.object = form.save()
            return super().form_valid(form)
        else:
            return self.render_to_response(self.get_context_data(form=form))

class ClientEditFormTabsView(LoginRequiredMixin, SuperuserOrPermissionRequiredMixin, UpdateView):
    model = Client
    form_class = ClientForm
    template_name = 'sales/clients/client_form_tabs.html'
    permission_required = 'sales.change_client'
    success_url = reverse_lazy('sales:client_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['empresa'] = getattr(self.request.user, 'empresa_activa', None)
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['client'] = self.object
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        if form.is_valid():
            self.object = form.save()
            return super().form_valid(form)
        else:
            return self.render_to_response(self.get_context_data(form=form))

@require_GET
def client_tags_autocomplete(request):
    empresa = getattr(request.user, 'empresa_activa', None)
    q = request.GET.get('q', '').strip()
    if not empresa:
        return JsonResponse({'results': []})
    tags_qs = ClientTag.objects.filter(empresa=empresa, is_active=True)
    if q:
        tags_qs = tags_qs.filter(name__icontains=q)
    tags = tags_qs.order_by('name')[:10]
    results = [
        {'id': tag.id, 'text': tag.name, 'color': tag.color} for tag in tags
    ]
    return JsonResponse({'results': results})

@csrf_exempt
@require_POST
def client_tags_create(request):
    empresa = getattr(request.user, 'empresa_activa', None)
    if not empresa:
        return JsonResponse({'success': False, 'error': 'No company'})
    try:
        data = json.loads(request.body.decode('utf-8'))
        name = data.get('name', '').strip()
        if not name:
            return JsonResponse({'success': False, 'error': 'No name'})
        tag, created = ClientTag.objects.get_or_create(empresa=empresa, name=name, defaults={'color': '#f97316', 'is_active': True})
        return JsonResponse({'success': True, 'tag': {'id': tag.id, 'name': tag.name, 'color': tag.color}})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

class TerminalListView(SuperuserOrPermissionRequiredMixin, ListView):
    model = POSTerminal
    template_name = 'sales/terminals/terminal_list.html'
    context_object_name = 'terminals'
    permission_required = 'sales.view_posterminal'
    paginate_by = 20

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['show_config_button'] = (
            user.is_superuser or 
            (hasattr(user, 'is_admin') and user.is_admin()) or
            user.roles.filter(nombre__in=['Administrador', 'Supervisor de Ventas'], activo=True).exists()
        )
        return context

class TerminalCreateView(SuperuserOrPermissionRequiredMixin, SuccessMessageMixin, CreateView):
    model = POSTerminal
    template_name = 'sales/terminals/terminal_form.html'
    fields = ['name', 'code', 'branch', 'fiscal_printer', 'fiscal_number', 'electronic_invoice', 'receipt_printer', 'ticket_width', 'barcode_scanner', 'scale_integration', 'scale_port', 'is_active']
    permission_required = 'sales.add_posterminal'
    success_url = reverse_lazy('sales:terminal_list')
    success_message = 'Terminal creada correctamente.'

class TerminalUpdateView(SuperuserOrPermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    model = POSTerminal
    template_name = 'sales/terminals/terminal_form.html'
    fields = ['name', 'code', 'branch', 'fiscal_printer', 'fiscal_number', 'electronic_invoice', 'receipt_printer', 'ticket_width', 'barcode_scanner', 'scale_integration', 'scale_port', 'is_active']
    permission_required = 'sales.change_posterminal'
    success_url = reverse_lazy('sales:terminal_list')
    success_message = 'Terminal actualizada correctamente.'

class TerminalDeleteView(SuperuserOrPermissionRequiredMixin, SuccessMessageMixin, DeleteView):
    model = POSTerminal
    template_name = 'sales/terminals/terminal_confirm_delete.html'
    permission_required = 'sales.delete_posterminal'
    success_url = reverse_lazy('sales:terminal_list')
    success_message = 'Terminal eliminada correctamente.'

@login_required
def pos_main(request):
    # Obtener sesión activa
    session = POSSession.objects.filter(operator=request.user, state='open').first()
    if not session:
        return redirect('sales:pos_dashboard')

    # Filtros seleccionados
    selected_category_id = request.GET.get('category')
    selected_subcategory_id = request.GET.get('subcategory')
    selected_brand_id = request.GET.get('brand')

    # Obtener filtros activos
    categories = Category.objects.filter(is_active=True)
    brands = Brand.objects.filter(is_active=True)
    # Subcategorías: solo de la categoría seleccionada, o todas si no hay filtro
    if selected_category_id:
        subcategories = Subcategory.objects.filter(is_active=True, category_id=selected_category_id)
    else:
        subcategories = Subcategory.objects.filter(is_active=True)

    # Filtrar productos padres según los filtros
    products_qs = Product.objects.filter(is_published=True)
    if selected_category_id:
        products_qs = products_qs.filter(category_id=selected_category_id)
    if selected_subcategory_id:
        products_qs = products_qs.filter(subcategory_id=selected_subcategory_id)
    if selected_brand_id:
        products_qs = products_qs.filter(brand_id=selected_brand_id)

    # Carrito (venta en borrador de la sesión)
    draft_sale = POSSale.objects.filter(session=session, state='draft').first()
    cart_lines = draft_sale.lines.all() if draft_sale else []
    cart_subtotal = sum(line.subtotal for line in cart_lines)
    cart_discount = sum(getattr(line, 'discount_amount', 0) for line in cart_lines)
    cart_total = cart_subtotal - cart_discount

    # Métodos de pago
    payment_methods = PaymentMethod.objects.filter(is_active=True)

    def decimal_to_float(obj):
        if isinstance(obj, list):
            return [decimal_to_float(i) for i in obj]
        elif isinstance(obj, dict):
            return {k: decimal_to_float(v) for k, v in obj.items()}
        elif isinstance(obj, Decimal):
            return float(obj)
        return obj

    # Productos para el grid
    product_list = []
    for p in products_qs:
        # Variantes activas con stock > 0
        variants_qs = p.variants.filter(is_active=True)
        variants_with_stock = []
        for v in variants_qs:
            stock_v = StockQuant.objects.filter(product=v.product, location__branch=session.branch).first()
            stock_qty = float(stock_v.available_quantity) if stock_v else 0
            if stock_qty > 0:
                variants_with_stock.append({
                    'id': v.id,
                    'sku': v.sku,
                    'price': float(v.price),
                    'stock': stock_qty,
                    'attributes': list(v.attributes.values('attribute__name', 'value')),
                })
        has_variants = len(variants_with_stock) > 0
        # Stock del producto padre (si no tiene variantes)
        stock_total = 0
        if not has_variants:
            stock_p = StockQuant.objects.filter(product=p, location__branch=session.branch).first()
            stock_total = float(stock_p.available_quantity) if stock_p else 0
        else:
            stock_total = sum(v['stock'] for v in variants_with_stock)
        # Imagen principal
        image_url = p.images.first().image.url if hasattr(p, 'images') and p.images.exists() else ''
        # Diccionario para el grid
        product_list.append({
            'id': p.id,
            'name': p.name,
            'code': p.sku,
            'price': float(p.price),
            'image_url': image_url,
            'stock': stock_total,
            'category_id': p.category_id,
            'subcategory_id': p.subcategory_id,
            'brand_id': p.brand_id,
            'has_multiple_variants': has_variants,
            'variants': variants_with_stock,
            'attributes': [],  # Se puede poblar si se requiere
        })

    context = {
        'user': request.user,
        'session': session,
        'categories': categories,
        'subcategories': subcategories,
        'brands': brands,
        'selected_category_id': selected_category_id,
        'selected_subcategory_id': selected_subcategory_id,
        'selected_brand_id': selected_brand_id,
        'products': json.dumps(decimal_to_float(product_list)),
        'cart_lines': cart_lines,
        'cart_subtotal': cart_subtotal,
        'cart_discount': cart_discount,
        'cart_total': cart_total,
        'payment_methods': payment_methods,
    }
    return render(request, 'sales/pos/base_pos.html', context)

@login_required
@require_GET
def pos_api_products(request):
    search = request.GET.get('search', '')
    category = request.GET.get('category')
    qs = ProductVariant.objects.filter(is_active=True)
    if search:
        qs = qs.filter(
            Q(product__name__icontains=search) |
            Q(sku__icontains=search) |
            Q(product__description__icontains=search)
        )
    if category:
        qs = qs.filter(product__category_id=category)
    products = [{
        'id': p.id,
        'name': p.product.name,
        'code': p.sku,
        'price': float(getattr(p, 'price', 0)),
        'image_url': p.product.images.first().image.url if hasattr(p.product, 'images') and p.product.images.exists() else '',
    } for p in qs[:30]]
    return JsonResponse({'products': products})

@login_required
@require_POST
def pos_api_cart_add(request):
    import json as pyjson
    session = POSSession.objects.filter(operator=request.user, state='open').first()
    if not session:
        return JsonResponse({'error': 'No hay sesión activa'}, status=400)
    draft_sale = POSSale.objects.filter(session=session, state='draft').first()
    if not draft_sale:
        from .models import PriceList
        price_list = PriceList.objects.filter(is_active=True).first()
        draft_sale = POSSale.objects.create(session=session, operator=request.user, price_list=price_list, state='draft')
    data = pyjson.loads(request.body)
    product_id = data.get('product_id')
    quantity = data.get('quantity', 1)
    is_variant = data.get('is_variant', False)
    from inventory.models import Product, ProductVariant, StockQuant
    if is_variant:
        product = ProductVariant.objects.filter(id=product_id, is_active=True).first()
        if not product:
            return JsonResponse({'error': 'Variante no encontrada'}, status=404)
        # Validar stock disponible (en la sucursal de la sesión)
        stock_quant = StockQuant.objects.filter(product=product, location__branch=session.branch).first()
        available = float(stock_quant.available_quantity) if stock_quant else 0
        # Sumar cantidad ya en carrito
        line = draft_sale.lines.filter(product_variant=product).first()
        qty_in_cart = line.quantity if line else 0
        if available < quantity + qty_in_cart:
            return JsonResponse({'error': f'Stock insuficiente. Disponible: {available}, en carrito: {qty_in_cart}'}, status=400)
        # Agregar o actualizar línea
        if line:
            line.quantity += quantity
            line.save()
        else:
            draft_sale.lines.create(product_variant=product, quantity=quantity, unit_price=float(product.price), subtotal=quantity * float(product.price))
    else:
        # Producto padre sin variantes
        product = Product.objects.filter(id=product_id, is_published=True).first()
        if not product:
            return JsonResponse({'error': 'Producto no encontrado'}, status=404)
        # Buscar o crear variante default
        variant = product.variants.filter(is_active=True).first()
        if not variant:
            # Crear variante default
            from inventory.models import ProductVariant
            variant = ProductVariant.objects.create(
                product=product,
                sku=product.sku or f"{product.id}-default",
                price=product.price,
                is_active=True
            )
        # Validar stock disponible (en la sucursal de la sesión)
        stock_quant = StockQuant.objects.filter(product=variant.product, location__branch=session.branch).first()
        available = float(stock_quant.available_quantity) if stock_quant else 0
        # Sumar cantidad ya en carrito
        line = draft_sale.lines.filter(product_variant=variant).first()
        qty_in_cart = line.quantity if line else 0
        if available < quantity + qty_in_cart:
            return JsonResponse({'error': f'Stock insuficiente. Disponible: {available}, en carrito: {qty_in_cart}'}, status=400)
        # Agregar o actualizar línea
        if line:
            line.quantity += quantity
            line.save()
        else:
            draft_sale.lines.create(product_variant=variant, quantity=quantity, unit_price=float(variant.price), subtotal=quantity * float(variant.price))
    draft_sale.recalculate_totals()
    cart_lines = draft_sale.lines.all()
    cart = [{
        'id': l.id,
        'product': l.product_variant.product.name if l.product_variant else l.description,
        'quantity': l.quantity,
        'subtotal': float(l.subtotal),
    } for l in cart_lines]
    return JsonResponse({
        'success': True,
        'cart': cart,
        'cart_subtotal': float(cart_subtotal) if 'cart_subtotal' in locals() else 0,
        'cart_discount': float(cart_discount) if 'cart_discount' in locals() else 0,
        'cart_total': float(cart_total) if 'cart_total' in locals() else 0,
    })

@require_POST
def pos_api_cart_update(request):
    import json
    session = POSSession.objects.filter(operator=request.user, state='open').first()
    if not session:
        return JsonResponse({'error': 'No hay sesión activa'}, status=400)
    draft_sale = POSSale.objects.filter(session=session, state='draft').first()
    if not draft_sale:
        return JsonResponse({'error': 'No hay venta en borrador'}, status=400)
    data = json.loads(request.body)
    line_id = data.get('line_id')
    quantity = data.get('quantity')
    discount = data.get('discount')
    price = data.get('price')
    note = data.get('note')
    line = draft_sale.lines.filter(id=line_id).first()
    if not line:
        return JsonResponse({'error': 'Línea no encontrada'}, status=404)
    if quantity is not None:
        line.quantity = quantity
    if discount is not None:
        line.discount_percentage = discount
    if price is not None:
        line.unit_price = price
    if note is not None:
        line.note = note
    line.subtotal = line.quantity * line.unit_price * (1 - (line.discount_percentage or 0) / 100)
    line.save()
    draft_sale.recalculate_totals()
    cart_lines = draft_sale.lines.all()
    cart = [{
        'id': l.id,
        'product': l.product_variant.product.name,
        'quantity': l.quantity,
        'subtotal': float(l.subtotal),
    } for l in cart_lines]
    return JsonResponse({'success': True, 'cart': cart})

@require_POST
def pos_api_cart_remove(request):
    import json
    session = POSSession.objects.filter(operator=request.user, state='open').first()
    if not session:
        return JsonResponse({'error': 'No hay sesión activa'}, status=400)
    draft_sale = POSSale.objects.filter(session=session, state='draft').first()
    if not draft_sale:
        return JsonResponse({'error': 'No hay venta en borrador'}, status=400)
    data = json.loads(request.body)
    line_id = data.get('line_id')
    line = draft_sale.lines.filter(id=line_id).first()
    if not line:
        return JsonResponse({'error': 'Línea no encontrada'}, status=404)
    line.delete()
    draft_sale.recalculate_totals()
    cart_lines = draft_sale.lines.all()
    cart = [{
        'id': l.id,
        'product': l.product_variant.product.name,
        'quantity': l.quantity,
        'subtotal': float(l.subtotal),
    } for l in cart_lines]
    return JsonResponse({'success': True, 'cart': cart})

@require_POST
def pos_api_payment(request):
    import json
    from inventory.models import StockQuant, StockMove
    session = POSSession.objects.filter(operator=request.user, state='open').first()
    if not session:
        return JsonResponse({'error': 'No hay sesión activa'}, status=400)
    draft_sale = POSSale.objects.filter(session=session, state='draft').first()
    if not draft_sale:
        return JsonResponse({'error': 'No hay venta en borrador'}, status=400)
    data = json.loads(request.body)
    payments = data.get('payments', [])
    total_paid = sum(float(p.get('amount', 0)) for p in payments)
    if abs(total_paid - draft_sale.total) > 0.01:
        return JsonResponse({'error': 'El monto pagado no coincide con el total de la venta'}, status=400)
    # Validar stock antes de completar la venta
    for line in draft_sale.lines.all():
        stock_quant = StockQuant.objects.filter(product=line.product_variant, location__branch=session.branch).first()
        available = stock_quant.available_quantity if stock_quant else 0
        if available < line.quantity:
            return JsonResponse({'error': f'Stock insuficiente para {line.product_variant.name}. Disponible: {available}'}, status=400)
    # Registrar pagos
    for p in payments:
        draft_sale.payments.create(
            payment_method=p.get('method'),
            amount=p.get('amount'),
            reference=p.get('reference', ''),
            notes=p.get('notes', '')
        )
    # Descontar stock y crear movimientos
    for line in draft_sale.lines.all():
        stock_quant = StockQuant.objects.filter(product=line.product_variant, location__branch=session.branch).first()
        if stock_quant:
            stock_quant.available_quantity -= line.quantity
            stock_quant.save()
        StockMove.objects.create(
            product=line.product_variant,
            quantity=-line.quantity,
            location=stock_quant.location if stock_quant else None,
            origin='POS',
            sale=draft_sale
        )
    draft_sale.state = 'completed'
    draft_sale.completed_at = timezone.now()
    draft_sale.save()
    return JsonResponse({'success': True, 'sale_number': draft_sale.number, 'total_paid': float(draft_sale.total)})
