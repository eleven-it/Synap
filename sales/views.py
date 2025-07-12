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
from inventory.models import ProductVariant
from .forms import ClientForm, ClientSearchForm, PaymentMethodForm, PaymentProcessorForm
from core.models import UsuarioExtendido



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
def client_create(request):
    """Crear nuevo cliente"""
    if request.method == 'POST':
        # Lógica para crear cliente
        name = request.POST.get('name')
        tax_id = request.POST.get('tax_id')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        type = request.POST.get('type')
        credit_limit = request.POST.get('credit_limit', 0)
        origin = request.POST.get('origin')
        tiendanube_customer_id = request.POST.get('tiendanube_customer_id')
        is_active = request.POST.get('is_active') == 'on'
        
        try:
            client = Client.objects.create(
                name=name,
                tax_id=tax_id,
                email=email,
                phone=phone,
                type=type,
                credit_limit=Decimal(credit_limit) if credit_limit else Decimal('0.00'),
                origin=origin,
                tiendanube_customer_id=tiendanube_customer_id,
                is_active=is_active
            )
            messages.success(request, f'Cliente "{client.name}" creado correctamente.')
            return redirect('sales:client_detail', pk=client.pk)
        except Exception as e:
            messages.error(request, f'Error al crear cliente: {str(e)}')
    
    context = {
        'payment_terms': PaymentTerm.objects.filter(is_active=True),
        'price_lists': PriceList.objects.filter(is_active=True),
    }
    
    return render(request, 'sales/clients/client_form.html', context)


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
def client_edit(request, pk):
    """Editar cliente"""
    client = get_object_or_404(Client, pk=pk)
    
    if request.method == 'POST':
        # Lógica para actualizar cliente
        client.name = request.POST.get('name')
        client.tax_id = request.POST.get('tax_id')
        client.email = request.POST.get('email')
        client.phone = request.POST.get('phone')
        client.type = request.POST.get('type')
        client.credit_limit = Decimal(request.POST.get('credit_limit', 0))
        client.origin = request.POST.get('origin')
        client.tiendanube_customer_id = request.POST.get('tiendanube_customer_id')
        client.is_active = request.POST.get('is_active') == 'on'
        
        try:
            client.save()
            messages.success(request, f'Cliente "{client.name}" actualizado correctamente.')
            return redirect('sales:client_detail', pk=client.pk)
        except Exception as e:
            messages.error(request, f'Error al actualizar cliente: {str(e)}')
    
    context = {
        'client': client,
        'payment_terms': PaymentTerm.objects.filter(is_active=True),
        'price_lists': PriceList.objects.filter(is_active=True),
    }
    
    return render(request, 'sales/clients/client_form.html', context)


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

def payment_term_create(request):
    return render(request, 'sales/config/payment_terms_list.html')

def payment_term_detail(request, pk):
    return render(request, 'sales/config/payment_terms_detail.html')

def payment_term_edit(request, pk):
    return render(request, 'sales/config/payment_terms_list.html')

def payment_term_delete(request, pk):
    return render(request, 'sales/config/payment_terms_list.html')


class ClientListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Vista para listar clientes"""
    model = Client
    template_name = 'sales/clients/client_list.html'
    context_object_name = 'clients'
    permission_required = 'sales.view_client'
    paginate_by = 20
    
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
        return context


class ClientDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
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


class ClientCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Vista para crear cliente"""
    model = Client
    form_class = ClientForm
    template_name = 'sales/clients/client_form.html'
    permission_required = 'sales.add_client'
    success_url = reverse_lazy('sales:client_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['payment_terms'] = PaymentTerm.objects.filter(is_active=True)
        context['price_lists'] = PriceList.objects.filter(is_active=True)
        return context
    
    def form_valid(self, form):
        messages.success(self.request, _('Client created successfully.'))
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, _('Error creating client. Please check the form.'))
        return super().form_invalid(form)


class ClientUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Vista para editar cliente"""
    model = Client
    form_class = ClientForm
    template_name = 'sales/clients/client_form.html'
    permission_required = 'sales.change_client'
    
    def get_success_url(self):
        return reverse('sales:client_detail', kwargs={'pk': self.object.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['payment_terms'] = PaymentTerm.objects.filter(is_active=True)
        context['price_lists'] = PriceList.objects.filter(is_active=True)
        return context
    
    def form_valid(self, form):
        messages.success(self.request, _('Client updated successfully.'))
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, _('Error updating client. Please check the form.'))
        return super().form_invalid(form)


class ClientDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
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
        'text': f"{seller.nombre} ({seller.email})",
        'email': seller.email
    } for seller in sellers]
    
    return JsonResponse({'results': results})


def get_states_by_country(request):
    """Obtener estados por país"""
    country_id = request.GET.get('country_id')
    
    if not country_id:
        return JsonResponse({'states': []})
    
    try:
        from core.models import State
        states = State.objects.filter(
            country_id=country_id,
            is_active=True
        ).order_by('name')
        
        results = [{
            'id': state.id,
            'text': state.name,
            'code': state.code
        } for state in states]
        
        return JsonResponse({'states': results})
    except Exception as e:
        # Si hay algún error, devolver lista vacía
        return JsonResponse({'states': []})

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
from .forms import ClientForm, ClientSearchForm



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
        branch=request.user.branch,
        is_active=True
    )
    
    context = {
        'active_session': active_session,
        'terminals': terminals,
        'user_branch': request.user.branch,
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
            pos_service = POSService(request.user, request.user.branch, terminal)
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
            pos_service = POSService(request.user, request.user.branch, session.pos_terminal)
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
    
    context = {
        'sale': sale,
        'session': active_session,
        'price_list': active_session.branch.default_price_list,
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
    """
    Búsqueda de clientes para TPV
    """
    query = request.GET.get('q', '')
    
    if query:
        clients = Client.objects.filter(
            name__icontains=query,
            is_customer=True
        )[:10]
    else:
        clients = []
    
    context = {
        'clients': clients,
        'query': query,
    }
    
    return render(request, 'sales/pos/client_search.html', context)

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
    terminals = POSTerminal.objects.filter(branch=request.user.branch)
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
