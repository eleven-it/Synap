from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Sum, Count
from django.utils import timezone
from django.db import transaction
from datetime import datetime, timedelta

from ..models import (
    Client, Contact, SalesOrder, SalesOrderLine, PriceList, PriceListItem,
    PaymentTerm, PaymentTermLine, Invoice, InvoiceLine, Payment,
    DeliveryOrder, DeliveryOrderLine, ReturnDelivery, CreditNote, ApprovalLog
)
from .serializers import (
    ClientSerializer, ContactSerializer, SalesOrderSerializer, SalesOrderLineSerializer,
    PriceListSerializer, PriceListItemSerializer, PaymentTermSerializer, PaymentTermLineSerializer,
    InvoiceSerializer, InvoiceLineSerializer, PaymentSerializer, DeliveryOrderSerializer,
    DeliveryOrderLineSerializer, ReturnDeliverySerializer, CreditNoteSerializer,
    ApprovalLogSerializer, SalesOrderCreateSerializer, InvoiceCreateSerializer
)
from inventory.models import ProductVariant, Warehouse


class ClientViewSet(viewsets.ModelViewSet):
    """API para gestión de clientes"""
    queryset = Client.objects.all().order_by('name')
    serializer_class = ClientSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'type', 'origin']
    search_fields = ['name', 'vat', 'email', 'phone']
    ordering_fields = ['name', 'credit_limit']
    ordering = ['name']

    @action(detail=True, methods=['get'])
    def sales_summary(self, request, pk=None):
        """Obtener resumen de ventas del cliente"""
        client = self.get_object()
        
        # Estadísticas de pedidos
        orders = SalesOrder.objects.filter(client=client)
        total_orders = orders.count()
        total_amount = orders.aggregate(total=Sum('total'))['total'] or 0
        
        # Estadísticas de facturas
        invoices = Invoice.objects.filter(client=client)
        total_invoices = invoices.count()
        total_billed = invoices.aggregate(total=Sum('total'))['total'] or 0
        
        # Pagos
        payments = Payment.objects.filter(client=client)
        total_paid = payments.aggregate(total=Sum('amount'))['total'] or 0
        
        # Saldo pendiente
        pending_balance = total_billed - total_paid
        
        return Response({
            'client_id': client.id,
            'client_name': client.name,
            'total_orders': total_orders,
            'total_amount_orders': total_amount,
            'total_invoices': total_invoices,
            'total_billed': total_billed,
            'total_paid': total_paid,
            'pending_balance': pending_balance,
            'credit_limit': client.credit_limit,
            'available_credit': client.credit_limit - pending_balance
        })

    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """Activar/desactivar cliente"""
        client = self.get_object()
        client.is_active = not client.is_active
        client.save()
        
        return Response({
            'id': client.id,
            'is_active': client.is_active,
            'message': f'Cliente {"activado" if client.is_active else "desactivado"} correctamente'
        })


class ContactViewSet(viewsets.ModelViewSet):
    """API para gestión de contactos"""
    queryset = Contact.objects.all().order_by('name')
    serializer_class = ContactSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['client', 'is_primary']
    search_fields = ['name', 'email', 'phone']

    @action(detail=True, methods=['post'])
    def set_primary(self, request, pk=None):
        """Establecer contacto como principal"""
        contact = self.get_object()
        
        # Quitar otros contactos principales del mismo cliente
        Contact.objects.filter(
            client=contact.client, 
            is_primary=True
        ).exclude(id=contact.id).update(is_primary=False)
        
        # Establecer este contacto como principal
        contact.is_primary = True
        contact.save()
        
        return Response({
            'id': contact.id,
            'is_primary': contact.is_primary,
            'message': 'Contacto establecido como principal'
        })


class SalesOrderViewSet(viewsets.ModelViewSet):
    """API para gestión de pedidos de venta"""
    queryset = SalesOrder.objects.all().order_by('-order_date')
    serializer_class = SalesOrderSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['state', 'client', 'currency', 'origin']
    search_fields = ['number', 'client__name']
    ordering_fields = ['order_date', 'total', 'number']
    ordering = ['-order_date']

    def get_serializer_class(self):
        """Usar serializer específico para crear"""
        if self.action == 'create':
            return SalesOrderCreateSerializer
        return SalesOrderSerializer

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Aprobar pedido de venta"""
        order = self.get_object()
        
        if order.state != 'draft':
            return Response(
                {'error': 'Solo se pueden aprobar pedidos en borrador'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        order.state = 'approved'
        order.save()
        
        # Crear log de aprobación
        ApprovalLog.objects.create(
            sales_order=order,
            user=request.user,
            action='approved',
            reason=request.data.get('comments', '')
        )
        
        return Response({
            'id': order.id,
            'state': order.state,
            'message': 'Pedido aprobado correctamente'
        })

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancelar pedido de venta"""
        order = self.get_object()
        
        if order.state in ['cancelled', 'completed']:
            return Response(
                {'error': 'No se puede cancelar un pedido ya cancelado o completado'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        order.state = 'cancelled'
        order.save()
        
        # Crear log de cancelación
        ApprovalLog.objects.create(
            sales_order=order,
            user=request.user,
            action='cancelled',
            reason=request.data.get('comments', '')
        )
        
        return Response({
            'id': order.id,
            'state': order.state,
            'message': 'Pedido cancelado correctamente'
        })

    @action(detail=True, methods=['post'])
    def create_invoice(self, request, pk=None):
        """Crear factura desde pedido"""
        order = self.get_object()
        
        if order.state != 'approved':
            return Response(
                {'error': 'Solo se pueden facturar pedidos aprobados'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verificar si ya existe una factura para este pedido
        if Invoice.objects.filter(sales_order=order).exists():
            return Response(
                {'error': 'Ya existe una factura para este pedido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Crear factura con las líneas del pedido
        invoice_data = {
            'client': order.client,
            'sales_order': order,
            'invoice_date': timezone.now().date(),
            'payment_term': order.payment_term,
            'currency': order.currency,
            'total': order.total,
            'state': 'draft',
            'invoice_type': 'sale'
        }
        
        invoice_lines = []
        for line in order.lines.all():
            invoice_lines.append({
                'product_variant': line.product_variant,
                'quantity': line.quantity,
                'unit_price': line.unit_price,
                'discount': line.discount,
                'subtotal': line.subtotal,
                'description': line.description
            })
        
        # Crear factura usando el serializer
        serializer = InvoiceCreateSerializer(data={
            **invoice_data,
            'lines': invoice_lines
        })
        
        if serializer.is_valid():
            invoice = serializer.save()
            return Response({
                'invoice_id': invoice.id,
                'invoice_number': invoice.number,
                'message': 'Factura creada correctamente'
            })
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def dashboard_stats(self, request):
        """Estadísticas del dashboard de ventas"""
        # Pedidos por estado
        orders_by_state = SalesOrder.objects.values('state').annotate(
            count=Count('id'),
            total_amount=Sum('total')
        )
        
        # Pedidos del mes actual
        current_month = timezone.now().month
        current_year = timezone.now().year
        monthly_orders = SalesOrder.objects.filter(
            order_date__month=current_month,
            order_date__year=current_year
        ).aggregate(
            count=Count('id'),
            total_amount=Sum('total')
        )
        
        # Top clientes
        top_clients = SalesOrder.objects.values(
            'client__name'
        ).annotate(
            total_orders=Count('id'),
            total_amount=Sum('total')
        ).order_by('-total_amount')[:5]
        
        return Response({
            'orders_by_state': list(orders_by_state),
            'monthly_orders': monthly_orders,
            'top_clients': list(top_clients)
        })


class InvoiceViewSet(viewsets.ModelViewSet):
    """API para gestión de facturas"""
    queryset = Invoice.objects.all().order_by('-invoice_date')
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['state', 'client', 'currency', 'payment_term', 'invoice_type']
    search_fields = ['number', 'client__name']
    ordering_fields = ['invoice_date', 'total', 'number']
    ordering = ['-invoice_date']

    def get_serializer_class(self):
        """Usar serializer específico para crear"""
        if self.action == 'create':
            return InvoiceCreateSerializer
        return InvoiceSerializer

    @action(detail=True, methods=['post'])
    def mark_paid(self, request, pk=None):
        """Marcar factura como pagada"""
        invoice = self.get_object()
        
        if invoice.state == 'paid':
            return Response(
                {'error': 'La factura ya está marcada como pagada'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        invoice.state = 'paid'
        invoice.save()
        
        return Response({
            'id': invoice.id,
            'state': invoice.state,
            'message': 'Factura marcada como pagada'
        })

    @action(detail=True, methods=['post'])
    def create_payment(self, request, pk=None):
        """Crear pago para la factura"""
        invoice = self.get_object()
        
        payment_data = {
            'invoice': invoice.id,
            'client': invoice.client.id,
            'payment_date': request.data.get('payment_date', timezone.now().date()),
            'amount': request.data.get('amount'),
            'currency': request.data.get('currency', invoice.currency),
            'payment_method': request.data.get('payment_method'),
            'state': 'confirmed'
        }
        
        serializer = PaymentSerializer(data=payment_data)
        if serializer.is_valid():
            payment = serializer.save()
            
            # Verificar si la factura está completamente pagada
            total_paid = Payment.objects.filter(invoice=invoice).aggregate(
                total=Sum('amount')
            )['total'] or 0
            
            if total_paid >= invoice.total:
                invoice.state = 'paid'
                invoice.save()
            
            return Response({
                'payment_id': payment.id,
                'invoice_state': invoice.state,
                'message': 'Pago registrado correctamente'
            })
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PaymentViewSet(viewsets.ModelViewSet):
    """API para gestión de pagos"""
    queryset = Payment.objects.all().order_by('-payment_date')
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['client', 'payment_method', 'currency', 'state']
    search_fields = ['number', 'client__name']
    ordering_fields = ['payment_date', 'amount', 'number']
    ordering = ['-payment_date']


class DeliveryOrderViewSet(viewsets.ModelViewSet):
    """API para gestión de órdenes de entrega"""
    queryset = DeliveryOrder.objects.all().order_by('-delivery_date')
    serializer_class = DeliveryOrderSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['state', 'client', 'warehouse', 'sales_order']
    search_fields = ['number', 'client__name']
    ordering_fields = ['delivery_date', 'number']
    ordering = ['-delivery_date']

    @action(detail=True, methods=['post'])
    def process_delivery(self, request, pk=None):
        """Procesar entrega (confirmar cantidades entregadas)"""
        delivery = self.get_object()
        
        if delivery.state != 'pending':
            return Response(
                {'error': 'Solo se pueden procesar entregas pendientes'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Actualizar cantidades entregadas
        lines_data = request.data.get('lines', [])
        
        with transaction.atomic():
            for line_data in lines_data:
                line_id = line_data.get('id')
                delivered_qty = line_data.get('delivered_quantity', 0)
                
                try:
                    line = DeliveryOrderLine.objects.get(id=line_id, delivery_order=delivery)
                    line.quantity = delivered_qty
                    line.state = 'delivered'
                    line.save()
                    
                except DeliveryOrderLine.DoesNotExist:
                    continue
            
            # Marcar entrega como completada
            delivery.state = 'completed'
            delivery.save()
        
        return Response({
            'id': delivery.id,
            'state': delivery.state,
            'message': 'Entrega procesada correctamente'
        })


class ReturnDeliveryViewSet(viewsets.ModelViewSet):
    """API para gestión de devoluciones"""
    queryset = ReturnDelivery.objects.all().order_by('-return_date')
    serializer_class = ReturnDeliverySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['state', 'client', 'sales_order', 'return_type']
    search_fields = ['number', 'client__name', 'reason']
    ordering_fields = ['return_date', 'number']
    ordering = ['-return_date']

    @action(detail=True, methods=['post'])
    def approve_return(self, request, pk=None):
        """Aprobar devolución"""
        return_delivery = self.get_object()
        
        if return_delivery.state != 'pending':
            return Response(
                {'error': 'Solo se pueden aprobar devoluciones pendientes'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return_delivery.state = 'approved'
        return_delivery.save()
        
        return Response({
            'id': return_delivery.id,
            'state': return_delivery.state,
            'message': 'Devolución aprobada correctamente'
        })


class CreditNoteViewSet(viewsets.ModelViewSet):
    """API para gestión de notas de crédito"""
    queryset = CreditNote.objects.all().order_by('-credit_date')
    serializer_class = CreditNoteSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['state', 'client', 'invoice']
    search_fields = ['number', 'client__name', 'reason']
    ordering_fields = ['credit_date', 'amount', 'number']
    ordering = ['-credit_date']

    @action(detail=True, methods=['post'])
    def apply_credit(self, request, pk=None):
        """Aplicar nota de crédito"""
        credit_note = self.get_object()
        
        if credit_note.state != 'pending':
            return Response(
                {'error': 'Solo se pueden aplicar notas de crédito pendientes'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        credit_note.state = 'applied'
        credit_note.save()
        
        return Response({
            'id': credit_note.id,
            'state': credit_note.state,
            'message': 'Nota de crédito aplicada correctamente'
        })


class PriceListViewSet(viewsets.ModelViewSet):
    """API para gestión de listas de precios"""
    queryset = PriceList.objects.all().order_by('name')
    serializer_class = PriceListSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'currency']
    search_fields = ['name']
    ordering_fields = ['name', 'valid_from', 'valid_to']
    ordering = ['name']

    @action(detail=True, methods=['post'])
    def add_product(self, request, pk=None):
        """Agregar producto a la lista de precios"""
        price_list = self.get_object()
        
        product_variant_id = request.data.get('product_variant_id')
        price = request.data.get('price')
        
        if not product_variant_id or not price:
            return Response(
                {'error': 'Se requiere product_variant_id y price'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            product_variant = ProductVariant.objects.get(id=product_variant_id)
        except ProductVariant.DoesNotExist:
            return Response(
                {'error': 'Variante de producto no encontrada'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Crear o actualizar item de lista de precios
        item, created = PriceListItem.objects.update_or_create(
            price_list=price_list,
            product_variant=product_variant,
            defaults={
                'price': price,
                'min_qty': request.data.get('min_qty', 1),
                'max_qty': request.data.get('max_qty'),
                'discount': request.data.get('discount', 0)
            }
        )
        
        return Response({
            'id': item.id,
            'created': created,
            'message': f'Producto {"agregado" if created else "actualizado"} correctamente'
        })


class PaymentTermViewSet(viewsets.ModelViewSet):
    """API para gestión de condiciones de pago"""
    queryset = PaymentTerm.objects.all().order_by('name')
    serializer_class = PaymentTermSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name']
    ordering = ['name']


class ApprovalLogViewSet(viewsets.ReadOnlyModelViewSet):
    """API para consulta de logs de aprobación"""
    queryset = ApprovalLog.objects.all().order_by('-action_date')
    serializer_class = ApprovalLogSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['action', 'user', 'sales_order']
    search_fields = ['reason']
    ordering_fields = ['action_date']
    ordering = ['-action_date'] 