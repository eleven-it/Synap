from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Sum, Count
from django.utils import timezone
from django.db import transaction
from datetime import datetime, timedelta
from django.contrib.auth import get_user_model
from sales.models import (
    Client, SalesOrder, SalesOrderLine, PriceList, PriceListItem,
    PaymentTerm, PaymentTermLine, Invoice, InvoiceLine, Payment,
    DeliveryOrder, DeliveryOrderLine, ReturnDelivery, CreditNote, ApprovalLog,
    POSSale, POSSaleLine
)
from core.models import Contact
from inventory.models import ProductVariant, Warehouse
from .serializers import (
    ClientSerializer, ClientListSerializer, ClientStatsSerializer,
    ContactSerializer, ContactListSerializer, ContactStatsSerializer,
    UserSerializer, AutocompleteSerializer, SalesOrderSerializer, SalesOrderLineSerializer,
    PriceListSerializer, PriceListItemSerializer, PaymentTermSerializer, PaymentTermLineSerializer,
    InvoiceSerializer, InvoiceLineSerializer, PaymentSerializer, DeliveryOrderSerializer,
    DeliveryOrderLineSerializer, ReturnDeliverySerializer, CreditNoteSerializer,
    ApprovalLogSerializer, SalesOrderCreateSerializer, InvoiceCreateSerializer
)

User = get_user_model()


class ClientViewSet(viewsets.ModelViewSet):
    """ViewSet para clientes"""
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['client_type', 'status', 'customer_category', 'country', 'state', 'city']
    search_fields = ['first_name', 'last_name', 'company_name', 'email', 'phone', 'tax_id']
    ordering_fields = ['created_at', 'updated_at', 'first_name', 'last_name', 'company_name']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return Client.objects.select_related('country', 'state', 'city', 'sales_representative').prefetch_related('contacts')
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ClientListSerializer
        return ClientSerializer
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Obtener estadísticas de clientes"""
        queryset = self.get_queryset()
        
        # Estadísticas básicas
        total_clients = queryset.count()
        active_clients = queryset.filter(status='active').count()
        individual_clients = queryset.filter(client_type='individual').count()
        company_clients = queryset.filter(client_type='company').count()
        
        # Clientes por categoría
        clients_by_category = queryset.values('customer_category').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Clientes por estado
        clients_by_status = queryset.values('status').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Clientes recientes (último mes)
        recent_clients = queryset.filter(
            created_at__gte=timezone.now() - timedelta(days=30)
        ).count()
        
        # Total de contactos
        total_contacts = Contact.objects.count()
        
        stats = {
            'total_clients': total_clients,
            'active_clients': active_clients,
            'individual_clients': individual_clients,
            'company_clients': company_clients,
            'clients_by_category': {item['customer_category']: item['count'] for item in clients_by_category},
            'clients_by_status': {item['status']: item['count'] for item in clients_by_status},
            'recent_clients': recent_clients,
            'total_contacts': total_contacts,
        }
        
        serializer = ClientStatsSerializer(stats)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def autocomplete(self, request):
        """Autocompletado de clientes"""
        query = request.query_params.get('q', '')
        if not query:
            return Response([])
        
        queryset = self.get_queryset().filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(company_name__icontains=query) |
            Q(email__icontains=query)
        )[:10]
        
        results = []
        for client in queryset:
            results.append({
                'id': client.id,
                'name': client.get_display_name(),
                'additional_info': f"{client.email or ''} - {client.get_client_type_display()}"
            })
        
        serializer = AutocompleteSerializer(results, many=True)
        return Response(serializer.data)


class ContactViewSet(viewsets.ModelViewSet):
    """ViewSet para contactos"""
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['role', 'department', 'status', 'client']
    search_fields = ['first_name', 'last_name', 'email', 'phone', 'mobile', 'position', 'company']
    ordering_fields = ['created_at', 'updated_at', 'first_name', 'last_name']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return Contact.objects.select_related('client')
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ContactListSerializer
        return ContactSerializer
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Obtener estadísticas de contactos"""
        queryset = self.get_queryset()
        
        # Estadísticas básicas
        total_contacts = queryset.count()
        active_contacts = queryset.filter(status='active').count()
        primary_contacts = queryset.filter(role='primary').count()
        
        # Contactos por rol
        contacts_by_role = queryset.values('role').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Contactos por departamento
        contacts_by_department = queryset.values('department').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Contactos recientes (último mes)
        recent_contacts = queryset.filter(
            created_at__gte=timezone.now() - timedelta(days=30)
        ).count()
        
        stats = {
            'total_contacts': total_contacts,
            'active_contacts': active_contacts,
            'primary_contacts': primary_contacts,
            'contacts_by_role': {item['role']: item['count'] for item in contacts_by_role},
            'contacts_by_department': {item['department']: item['count'] for item in contacts_by_department},
            'recent_contacts': recent_contacts,
        }
        
        serializer = ContactStatsSerializer(stats)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def autocomplete(self, request):
        """Autocompletado de contactos"""
        query = request.query_params.get('q', '')
        if not query:
            return Response([])
        
        queryset = self.get_queryset().filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query) |
            Q(phone__icontains=query)
        )[:10]
        
        results = []
        for contact in queryset:
            results.append({
                'id': contact.id,
                'name': contact.get_full_name(),
                'additional_info': f"{contact.email or ''} - {contact.position or ''}"
            })
        
        serializer = AutocompleteSerializer(results, many=True)
        return Response(serializer.data)


# class CountryViewSet(viewsets.ReadOnlyModelViewSet):
#     """ViewSet para países"""
#     permission_classes = [IsAuthenticated]
#     serializer_class = CountrySerializer
#     filter_backends = [filters.SearchFilter]
#     search_fields = ['name', 'code']
#     
#     def get_queryset(self):
#         return Country.objects.all()
#     
#     @action(detail=False, methods=['get'])
#     def autocomplete(self, request):
#         """Autocompletado de países"""
#         query = request.query_params.get('q', '')
#         if not query:
#             return Response([])
#         
#         countries = Country.objects.filter(
#             Q(name__icontains=query) |
#             Q(name_es__icontains=query) |
#             Q(name_en__icontains=query) |
#             Q(name_pt__icontains=query),
#             is_active=True
#         )[:10]
#         
#         results = []
#         for country in countries:
#             results.append({
#                 'id': country.id,
#                 'name': country.name,
#                 'code': country.code,
#                 'phone_code': country.phone_code,
#                 'currency_code': country.currency_code,
#                 'timezone': country.timezone
#             })
#         
#         return Response(results)


# class StateViewSet(viewsets.ReadOnlyModelViewSet):
#     """ViewSet para estados/provincias"""
#     permission_classes = [IsAuthenticated]
#     serializer_class = StateSerializer
#     filter_backends = [DjangoFilterBackend, filters.SearchFilter]
#     filterset_fields = ['country']
#     search_fields = ['name', 'code']
#     
#     def get_queryset(self):
#         return State.objects.select_related('country')
#     
#     @action(detail=False, methods=['get'])
#     def autocomplete(self, request):
#         """Autocompletado de estados/provincias"""
#         query = request.query_params.get('q', '')
#         country_id = request.query_params.get('country_id')
#         
#         if not query:
#             return Response([])
#         
#         states = State.objects.filter(
#             Q(name__icontains=query) |
#             Q(name_es__icontains=query) |
#             Q(name_en__icontains=query) |
#             Q(name_pt__icontains=query),
#             is_active=True
#         )
#         
#         if country_id:
#             states = states.filter(country_id=country_id)
#         
#         states = states.select_related('country')[:10]
#         
#         results = []
#         for state in states:
#             results.append({
#                 'id': state.id,
#                 'name': state.name,
#                 'code': state.code,
#                 'country_id': state.country.id,
#                 'country_name': state.country.name
#             })
#         
#         return Response(results)


# class CityViewSet(viewsets.ReadOnlyModelViewSet):
#     """ViewSet para ciudades"""
#     permission_classes = [IsAuthenticated]
#     serializer_class = CitySerializer
#     filter_backends = [DjangoFilterBackend, filters.SearchFilter]
#     filterset_fields = ['state']
#     search_fields = ['name']
#     
#     def get_queryset(self):
#         return City.objects.select_related('state')
#     
#     @action(detail=False, methods=['get'])
#     def autocomplete(self, request):
#         """Autocompletado de ciudades"""
#         query = request.query_params.get('q', '')
#         state_id = request.query_params.get('state_id')
#         
#         if not query:
#             return Response([])
#         
#         cities = City.objects.filter(
#             Q(name__icontains=query) |
#             Q(name_es__icontains=query) |
#             Q(name_en__icontains=query) |
#             Q(name_pt__icontains=query),
#             is_active=True
#         )
#         
#         if state_id:
#             cities = cities.filter(state_id=state_id)
#         
#         cities = cities.select_related('state')[:10]
#         
#         results = []
#         for city in cities:
#             results.append({
#                 'id': city.id,
#                 'name': city.name,
#                 'state_id': city.state.id,
#                 'state_name': city.state.name,
#                 'country_id': city.state.country.id,
#                 'country_name': city.state.country.name
#             })
#         
#         return Response(results)


class SalesRepresentativeViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet para representantes de ventas"""
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer
    
    def get_queryset(self):
        # Filtrar solo usuarios que pueden ser representantes de ventas
        return User.objects.filter(is_active=True)
    
    @action(detail=False, methods=['get'])
    def autocomplete(self, request):
        """Autocompletado de representantes de ventas"""
        query = request.query_params.get('q', '')
        if not query:
            return Response([])
        
        queryset = self.get_queryset().filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(username__icontains=query) |
            Q(email__icontains=query)
        )[:10]
        
        results = []
        for user in queryset:
            results.append({
                'id': user.id,
                'name': user.get_full_name(),
                'additional_info': f"{user.email} ({user.username})"
            })
        
        serializer = AutocompleteSerializer(results, many=True)
        return Response(serializer.data)


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


# ============================================================================
# TPV (Point of Sale) API Endpoints
# ============================================================================

class TPVProductViewSet(viewsets.ReadOnlyModelViewSet):
    """API para búsqueda de productos en el TPV"""
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Obtener productos del inventario si está disponible
        try:
            from inventory.models import ProductVariant
            return ProductVariant.objects.filter(
                is_active=True,
                product__is_active=True
            ).select_related('product', 'product__category')
        except ImportError:
            # Si no hay módulo de inventario, devolver lista vacía
            return ProductVariant.objects.none()
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Búsqueda de productos para el TPV"""
        query = request.query_params.get('q', '')
        if not query or len(query) < 2:
            return Response([])
        
        queryset = self.get_queryset().filter(
            Q(product__name__icontains=query) |
            Q(product__sku__icontains=query) |
            Q(sku__icontains=query)
        )[:20]
        
        results = []
        for variant in queryset:
            # Obtener stock si está disponible
            stock = 0
            try:
                # Intentar obtener stock del inventario si está disponible
                if hasattr(variant, 'stock_quantity'):
                    stock = variant.stock_quantity
                elif hasattr(variant.product, 'stock_quantity'):
                    stock = variant.product.stock_quantity
            except:
                pass
            
            # Obtener precio
            price = 0
            if hasattr(variant, 'sale_price') and variant.sale_price:
                price = float(variant.sale_price)
            elif hasattr(variant.product, 'sale_price') and variant.product.sale_price:
                price = float(variant.product.sale_price)
            
            results.append({
                'id': variant.id,
                'name': variant.product.name,
                'sku': variant.sku or variant.product.sku,
                'price': price,
                'stock': stock,
                'category': variant.product.category.name if variant.product.category else None
            })
        
        return Response(results)
    
    def list(self, request):
        """Lista de productos para el TPV"""
        queryset = self.get_queryset()[:50]  # Limitar a 50 productos
        
        results = []
        for variant in queryset:
            # Obtener stock si está disponible
            stock = 0
            try:
                # Intentar obtener stock del inventario si está disponible
                if hasattr(variant, 'stock_quantity'):
                    stock = variant.stock_quantity
                elif hasattr(variant.product, 'stock_quantity'):
                    stock = variant.product.stock_quantity
            except:
                pass
            
            # Obtener precio
            price = 0
            if hasattr(variant, 'sale_price') and variant.sale_price:
                price = float(variant.sale_price)
            elif hasattr(variant.product, 'sale_price') and variant.product.sale_price:
                price = float(variant.product.sale_price)
            
            results.append({
                'id': variant.id,
                'name': variant.product.name,
                'sku': variant.sku or variant.product.sku,
                'price': price,
                'stock': stock,
                'category': variant.product.category.name if variant.product.category else None
            })
        
        return Response(results)


class TPVPaymentViewSet(viewsets.ViewSet):
    """API para procesamiento de pagos del TPV"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def process_payment(self, request):
        """Procesar pago del TPV"""
        try:
            from sales.services.tpv_service import TPVService
            from sales.services.sale_service import SaleService
            
            data = request.data
            items = data.get('items', [])
            payment_method = data.get('payment_method', 'cash')
            total = data.get('total', 0)
            extra_data = data.get('extra_data', {})
            
            if not items:
                return Response(
                    {'error': 'No items in cart'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Obtener sesión activa del TPV
            tpv_service = TPVService()
            session = tpv_service.get_active_session(request.user)
            
            if not session:
                return Response(
                    {'error': 'No active TPV session'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Crear la venta
            sale_service = SaleService()
            sale_data = {
                'session': session,
                'items': items,
                'payment_method': payment_method,
                'total': total,
                'extra_data': extra_data
            }
            
            sale = sale_service.create_tpv_sale(sale_data)
            
            # Procesar pago
            payment_result = sale_service.process_tpv_payment(sale, payment_method, extra_data)
            
            return Response({
                'success': True,
                'sale_number': sale.number,
                'total': float(sale.total),
                'payment_method': payment_method,
                'change': payment_result.get('change', 0)
            })
            
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            ) 