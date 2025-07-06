from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db.models import Q, Sum, Count
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from datetime import timedelta

from ..models import (
    Supplier, PurchaseRequest, PurchaseRequestLine, PurchaseQuotation, 
    PurchaseQuotationLine, PurchaseOrder, PurchaseOrderLine, PurchaseReceipt,
    PurchaseReceiptDocument, SupplierRating, SupplierPerformanceMetric,
    ApprovalWorkflow, ApprovalLevel, ApprovalRecord
)
from ..services import PurchaseService, SupplierService, ApprovalService, QuotationService
from .serializers import (
    SupplierSerializer, PurchaseRequestSerializer, PurchaseRequestLineSerializer,
    PurchaseQuotationSerializer, PurchaseQuotationLineSerializer,
    PurchaseOrderSerializer, PurchaseOrderLineSerializer, PurchaseReceiptSerializer,
    PurchaseReceiptDocumentSerializer, SupplierRatingSerializer,
    SupplierPerformanceSerializer, ApprovalWorkflowSerializer, ApprovalLevelSerializer,
    ApprovalRecordSerializer, PurchaseRequestSubmitSerializer, PurchaseRequestApproveSerializer,
    PurchaseRequestRejectSerializer, PurchaseOrderSendSerializer, PurchaseOrderConfirmSerializer,
    PurchaseReceiptApproveSerializer, QuotationCompareSerializer, QuotationSelectSerializer
)


class SupplierViewSet(viewsets.ModelViewSet):
    """ViewSet para gestión de proveedores"""
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'supplier_category', 'rating_class']
    search_fields = ['name', 'code', 'contact_person', 'email']
    ordering_fields = ['name', 'created_at', 'rating_class']
    ordering = ['name']
    
    def get_queryset(self):
        """Filtrar por empresa del usuario"""
        return self.queryset.filter(empresa=self.request.user.empresa)
    
    def perform_create(self, serializer):
        """Crear proveedor con empresa del usuario"""
        serializer.save(empresa=self.request.user.empresa, branch=self.request.user.branch)
    
    @action(detail=True, methods=['get'])
    def analytics(self, request, pk=None):
        """Obtener análisis del proveedor"""
        supplier = self.get_object()
        supplier_service = SupplierService().set_user(request.user)
        
        period_days = int(request.query_params.get('period_days', 90))
        analytics = supplier_service.get_supplier_analytics(supplier, period_days)
        
        return Response(analytics)
    
    @action(detail=True, methods=['get'])
    def performance(self, request, pk=None):
        """Obtener métricas de rendimiento"""
        supplier = self.get_object()
        supplier_service = SupplierService().set_user(request.user)
        
        period_days = int(request.query_params.get('period_days', 90))
        performance = supplier_service.get_supplier_performance(supplier, period_days)
        
        return Response(performance)
    
    @action(detail=True, methods=['get'])
    def ratings(self, request, pk=None):
        """Obtener evaluaciones del proveedor"""
        supplier = self.get_object()
        ratings = supplier.ratings.all().order_by('-rating_date')
        
        page = self.paginate_queryset(ratings)
        if page is not None:
            serializer = SupplierRatingSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = SupplierRatingSerializer(ratings, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def recommendations(self, request):
        """Obtener recomendaciones de proveedores"""
        supplier_service = SupplierService().set_user(request.user)
        category = request.query_params.get('category')
        
        recommendations = supplier_service.get_supplier_recommendations(
            request.user.empresa, category
        )
        
        return Response(recommendations)


class PurchaseRequestViewSet(viewsets.ModelViewSet):
    """ViewSet para gestión de solicitudes de compra"""
    queryset = PurchaseRequest.objects.all()
    serializer_class = PurchaseRequestSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'priority', 'supplier']
    search_fields = ['request_number', 'title', 'description']
    ordering_fields = ['request_date', 'required_date', 'total_amount']
    ordering = ['-request_date']
    
    def get_queryset(self):
        """Filtrar por empresa del usuario"""
        return self.queryset.filter(empresa=self.request.user.empresa)
    
    def get_serializer_class(self):
        """Retornar serializador apropiado según la acción"""
        if self.action == 'submit':
            return PurchaseRequestSubmitSerializer
        elif self.action == 'approve':
            return PurchaseRequestApproveSerializer
        elif self.action == 'reject':
            return PurchaseRequestRejectSerializer
        return PurchaseRequestSerializer
    
    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """Enviar solicitud a aprobación"""
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response({
            'status': 'success',
            'message': _('Request submitted for approval'),
            'data': PurchaseRequestSerializer(instance).data
        })
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Aprobar solicitud"""
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response({
            'status': 'success',
            'message': _('Request approved'),
            'data': PurchaseRequestSerializer(instance).data
        })
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Rechazar solicitud"""
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response({
            'status': 'success',
            'message': _('Request rejected'),
            'data': PurchaseRequestSerializer(instance).data
        })
    
    @action(detail=True, methods=['post'])
    def convert_to_order(self, request, pk=None):
        """Convertir solicitud a orden de compra"""
        instance = self.get_object()
        
        if instance.status != 'approved':
            return Response({
                'error': _('Only approved requests can be converted to orders')
            }, status=status.HTTP_400_BAD_REQUEST)
        
        purchase_service = PurchaseService().set_user(request.user)
        
        # Obtener datos de la orden
        supplier_id = request.data.get('supplier_id')
        expected_delivery_date = request.data.get('expected_delivery_date')
        payment_terms = request.data.get('payment_terms', '')
        delivery_terms = request.data.get('delivery_terms', '')
        notes = request.data.get('notes', '')
        
        if not supplier_id:
            return Response({
                'error': _('Supplier is required')
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            supplier = Supplier.objects.get(id=supplier_id, empresa=request.user.empresa)
        except Supplier.DoesNotExist:
            return Response({
                'error': _('Supplier not found')
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Crear orden
        order = purchase_service.create_purchase_order_from_request(
            request=instance,
            supplier=supplier,
            expected_delivery_date=expected_delivery_date,
            payment_terms=payment_terms,
            delivery_terms=delivery_terms,
            notes=notes
        )
        
        # Marcar solicitud como convertida
        instance.status = 'converted'
        instance.save()
        
        return Response({
            'status': 'success',
            'message': _('Request converted to order'),
            'order': PurchaseOrderSerializer(order).data
        })
    
    @action(detail=False, methods=['get'])
    def analytics(self, request):
        """Obtener análisis de solicitudes"""
        purchase_service = PurchaseService().set_user(request.user)
        
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if start_date:
            start_date = timezone.datetime.strptime(start_date, '%Y-%m-%d').date()
        if end_date:
            end_date = timezone.datetime.strptime(end_date, '%Y-%m-%d').date()
        
        analytics = purchase_service.get_purchase_analytics(
            request.user.empresa, start_date, end_date
        )
        
        return Response(analytics)
    
    @action(detail=False, methods=['get'])
    def pending_approvals(self, request):
        """Obtener solicitudes pendientes de aprobación"""
        approval_service = ApprovalService().set_user(request.user)
        pending = approval_service.get_pending_approvals(request.user, request.user.empresa)
        
        return Response(pending)


class PurchaseQuotationViewSet(viewsets.ModelViewSet):
    """ViewSet para gestión de cotizaciones"""
    queryset = PurchaseQuotation.objects.all()
    serializer_class = PurchaseQuotationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'supplier', 'purchase_request']
    search_fields = ['quotation_number', 'supplier__name']
    ordering_fields = ['quotation_date', 'total_amount', 'evaluation_score']
    ordering = ['-quotation_date']
    
    def get_queryset(self):
        """Filtrar por empresa del usuario"""
        return self.queryset.filter(empresa=self.request.user.empresa)
    
    def get_serializer_class(self):
        """Retornar serializador apropiado según la acción"""
        if self.action == 'compare':
            return QuotationCompareSerializer
        elif self.action == 'select':
            return QuotationSelectSerializer
        return PurchaseQuotationSerializer
    
    @action(detail=True, methods=['post'])
    def mark_received(self, request, pk=None):
        """Marcar cotización como recibida"""
        instance = self.get_object()
        instance.mark_received()
        
        return Response({
            'status': 'success',
            'message': _('Quotation marked as received'),
            'data': self.get_serializer(instance).data
        })
    
    @action(detail=True, methods=['post'])
    def evaluate(self, request, pk=None):
        """Evaluar cotización"""
        instance = self.get_object()
        
        quotation_service = QuotationService().set_user(request.user)
        
        # Obtener datos de evaluación
        quality_score = request.data.get('quality_score')
        delivery_score = request.data.get('delivery_score')
        communication_score = request.data.get('communication_score')
        price_score = request.data.get('price_score')
        service_score = request.data.get('service_score')
        
        # Comentarios
        quality_comments = request.data.get('quality_comments', '')
        delivery_comments = request.data.get('delivery_comments', '')
        communication_comments = request.data.get('communication_comments', '')
        price_comments = request.data.get('price_comments', '')
        service_comments = request.data.get('service_comments', '')
        general_comments = request.data.get('general_comments', '')
        recommendations = request.data.get('recommendations', '')
        would_recommend = request.data.get('would_recommend', True)
        
        # Crear evaluación
        rating = quotation_service.evaluate_quotation(
            quotation=instance,
            evaluator=request.user,
            quality_score=quality_score,
            delivery_score=delivery_score,
            communication_score=communication_score,
            price_score=price_score,
            service_score=service_score,
            quality_comments=quality_comments,
            delivery_comments=delivery_comments,
            communication_comments=communication_comments,
            price_comments=price_comments,
            service_comments=service_comments,
            general_comments=general_comments,
            recommendations=recommendations,
            would_recommend=would_recommend
        )
        
        return Response({
            'status': 'success',
            'message': _('Quotation evaluated'),
            'quotation': self.get_serializer(instance).data,
            'rating': SupplierRatingSerializer(rating['rating']).data
        })
    
    @action(detail=True, methods=['post'])
    def select(self, request, pk=None):
        """Seleccionar cotización"""
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response({
            'status': 'success',
            'message': _('Quotation selected'),
            'data': PurchaseQuotationSerializer(instance).data
        })
    
    @action(detail=False, methods=['get'])
    def compare(self, request):
        """Comparar cotizaciones de una solicitud"""
        request_id = request.query_params.get('request_id')
        include_expired = request.query_params.get('include_expired', 'false').lower() == 'true'
        
        if not request_id:
            return Response({
                'error': _('Request ID is required')
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            purchase_request = PurchaseRequest.objects.get(
                id=request_id, empresa=request.user.empresa
            )
        except PurchaseRequest.DoesNotExist:
            return Response({
                'error': _('Purchase request not found')
            }, status=status.HTTP_404_NOT_FOUND)
        
        quotation_service = QuotationService().set_user(request.user)
        comparison = quotation_service.compare_quotations(
            purchase_request, include_expired
        )
        
        return Response(comparison)
    
    @action(detail=False, methods=['get'])
    def analytics(self, request):
        """Obtener análisis de cotizaciones"""
        quotation_service = QuotationService().set_user(request.user)
        
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if start_date:
            start_date = timezone.datetime.strptime(start_date, '%Y-%m-%d').date()
        if end_date:
            end_date = timezone.datetime.strptime(end_date, '%Y-%m-%d').date()
        
        analytics = quotation_service.get_quotation_analytics(
            request.user.empresa, start_date, end_date
        )
        
        return Response(analytics)


class PurchaseOrderViewSet(viewsets.ModelViewSet):
    """ViewSet para gestión de órdenes de compra"""
    queryset = PurchaseOrder.objects.all()
    serializer_class = PurchaseOrderSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'supplier', 'purchase_request']
    search_fields = ['order_number', 'supplier__name']
    ordering_fields = ['order_date', 'expected_delivery_date', 'total_amount']
    ordering = ['-order_date']
    
    def get_queryset(self):
        """Filtrar por empresa del usuario"""
        return self.queryset.filter(empresa=self.request.user.empresa)
    
    def get_serializer_class(self):
        """Retornar serializador apropiado según la acción"""
        if self.action == 'send':
            return PurchaseOrderSendSerializer
        elif self.action == 'confirm':
            return PurchaseOrderConfirmSerializer
        return PurchaseOrderSerializer
    
    @action(detail=True, methods=['post'])
    def send(self, request, pk=None):
        """Enviar orden al proveedor"""
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response({
            'status': 'success',
            'message': _('Order sent to supplier'),
            'data': PurchaseOrderSerializer(instance).data
        })
    
    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """Confirmar orden"""
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response({
            'status': 'success',
            'message': _('Order confirmed'),
            'data': PurchaseOrderSerializer(instance).data
        })
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancelar orden"""
        instance = self.get_object()
        reason = request.data.get('reason', '')
        
        if not instance.can_cancel():
            return Response({
                'error': _('Order cannot be cancelled in current status')
            }, status=status.HTTP_400_BAD_REQUEST)
        
        instance.cancel(request.user, reason)
        
        return Response({
            'status': 'success',
            'message': _('Order cancelled'),
            'data': PurchaseOrderSerializer(instance).data
        })
    
    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """Duplicar orden"""
        instance = self.get_object()
        
        purchase_service = PurchaseService().set_user(request.user)
        new_order = purchase_service.duplicate_order(instance, request.user)
        
        return Response({
            'status': 'success',
            'message': _('Order duplicated'),
            'data': PurchaseOrderSerializer(new_order).data
        })
    
    @action(detail=True, methods=['get'])
    def receipt_progress(self, request, pk=None):
        """Obtener progreso de recepción"""
        instance = self.get_object()
        
        progress = {
            'total_ordered': sum(line.quantity for line in instance.lines.all()),
            'total_received': sum(line.received_quantity for line in instance.lines.all()),
            'progress_percentage': instance.get_receipt_progress(),
            'lines': []
        }
        
        for line in instance.lines.all():
            progress['lines'].append({
                'id': line.id,
                'product_name': line.product_variant.name,
                'ordered': line.quantity,
                'received': line.received_quantity,
                'remaining': line.remaining_quantity,
                'progress': line.receipt_progress
            })
        
        return Response(progress)
    
    @action(detail=False, methods=['get'])
    def analytics(self, request):
        """Obtener análisis de órdenes"""
        purchase_service = PurchaseService().set_user(request.user)
        
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if start_date:
            start_date = timezone.datetime.strptime(start_date, '%Y-%m-%d').date()
        if end_date:
            end_date = timezone.datetime.strptime(end_date, '%Y-%m-%d').date()
        
        analytics = purchase_service.get_purchase_analytics(
            request.user.empresa, start_date, end_date
        )
        
        return Response(analytics)


class PurchaseReceiptViewSet(viewsets.ModelViewSet):
    """ViewSet para gestión de recepciones"""
    queryset = PurchaseReceipt.objects.all()
    serializer_class = PurchaseReceiptSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'purchase_order_line__purchase_order__supplier']
    search_fields = ['receipt_number', 'lot_number']
    ordering_fields = ['receipt_date', 'received_at']
    ordering = ['-receipt_date']
    
    def get_queryset(self):
        """Filtrar por empresa del usuario"""
        return self.queryset.filter(empresa=self.request.user.empresa)
    
    def get_serializer_class(self):
        """Retornar serializador apropiado según la acción"""
        if self.action == 'approve':
            return PurchaseReceiptApproveSerializer
        return PurchaseReceiptSerializer
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Aprobar recepción"""
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response({
            'status': 'success',
            'message': _('Receipt approved'),
            'data': PurchaseReceiptSerializer(instance).data
        })
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Rechazar recepción"""
        instance = self.get_object()
        reason = request.data.get('reason', '')
        
        instance.reject(request.user, reason)
        
        return Response({
            'status': 'success',
            'message': _('Receipt rejected'),
            'data': PurchaseReceiptSerializer(instance).data
        })
    
    @action(detail=True, methods=['post'])
    def return_to_supplier(self, request, pk=None):
        """Devolver recepción al proveedor"""
        instance = self.get_object()
        reason = request.data.get('reason', '')
        
        instance.return_to_supplier(request.user, reason)
        
        return Response({
            'status': 'success',
            'message': _('Receipt returned to supplier'),
            'data': PurchaseReceiptSerializer(instance).data
        })


class SupplierRatingViewSet(viewsets.ModelViewSet):
    """ViewSet para gestión de evaluaciones de proveedores"""
    queryset = SupplierRating.objects.all()
    serializer_class = SupplierRatingSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['supplier', 'rating_class', 'status']
    search_fields = ['supplier__name']
    ordering_fields = ['rating_date', 'overall_score']
    ordering = ['-rating_date']
    
    def get_queryset(self):
        """Filtrar por empresa del usuario"""
        return self.queryset.filter(empresa=self.request.user.empresa)
    
    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """Enviar evaluación para revisión"""
        instance = self.get_object()
        instance.submit(request.user)
        
        return Response({
            'status': 'success',
            'message': _('Rating submitted for review'),
            'data': self.get_serializer(instance).data
        })
    
    @action(detail=True, methods=['post'])
    def review(self, request, pk=None):
        """Revisar evaluación"""
        instance = self.get_object()
        approved = request.data.get('approved', True)
        
        instance.review(request.user, approved)
        
        return Response({
            'status': 'success',
            'message': _('Rating reviewed'),
            'data': self.get_serializer(instance).data
        })


class ApprovalWorkflowViewSet(viewsets.ModelViewSet):
    """ViewSet para gestión de flujos de aprobación"""
    queryset = ApprovalWorkflow.objects.all()
    serializer_class = ApprovalWorkflowSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'min_amount']
    ordering = ['min_amount']
    
    def get_queryset(self):
        """Filtrar por empresa del usuario"""
        return self.queryset.filter(empresa=self.request.user.empresa)
    
    def perform_create(self, serializer):
        """Crear workflow con empresa del usuario"""
        serializer.save(empresa=self.request.user.empresa, branch=self.request.user.branch)


class ApprovalLevelViewSet(viewsets.ModelViewSet):
    """ViewSet para gestión de niveles de aprobación"""
    queryset = ApprovalLevel.objects.all()
    serializer_class = ApprovalLevelSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['workflow', 'is_active', 'approval_type']
    search_fields = ['name']
    ordering_fields = ['priority', 'name']
    ordering = ['priority']


class ApprovalRecordViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet para consulta de registros de aprobación"""
    queryset = ApprovalRecord.objects.all()
    serializer_class = ApprovalRecordSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['request', 'level', 'approver', 'action']
    ordering_fields = ['approved_at']
    ordering = ['-approved_at']
    
    def get_queryset(self):
        """Filtrar por empresa del usuario"""
        return self.queryset.filter(request__empresa=self.request.user.empresa)


class PurchaseDashboardView(APIView):
    """Vista para dashboard de compras"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Obtener datos del dashboard de compras"""
        empresa = request.user.empresa
        
        # Período de análisis (últimos 30 días)
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
        
        # Métricas principales
        total_requests = PurchaseRequest.objects.filter(
            empresa=empresa,
            request_date__range=[start_date, end_date]
        ).count()
        
        pending_requests = PurchaseRequest.objects.filter(
            empresa=empresa,
            status='pending_approval'
        ).count()
        
        total_orders = PurchaseOrder.objects.filter(
            empresa=empresa,
            order_date__range=[start_date, end_date]
        ).count()
        
        total_spent = PurchaseOrder.objects.filter(
            empresa=empresa,
            status__in=['confirmed', 'partially_received', 'received'],
            order_date__range=[start_date, end_date]
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        # Órdenes vencidas
        overdue_orders = PurchaseOrder.objects.filter(
            empresa=empresa,
            status__in=['sent', 'confirmed'],
            expected_delivery_date__lt=end_date
        ).count()
        
        # Recepciones pendientes
        pending_receipts = PurchaseReceipt.objects.filter(
            empresa=empresa,
            status='pending'
        ).count()
        
        # Proveedores activos
        active_suppliers = Supplier.objects.filter(
            empresa=empresa,
            is_active=True
        ).count()
        
        # Solicitudes por estado
        requests_by_status = PurchaseRequest.objects.filter(
            empresa=empresa,
            request_date__range=[start_date, end_date]
        ).values('status').annotate(count=Count('id'))
        
        # Órdenes por estado
        orders_by_status = PurchaseOrder.objects.filter(
            empresa=empresa,
            order_date__range=[start_date, end_date]
        ).values('status').annotate(count=Count('id'))
        
        # Top proveedores por monto
        top_suppliers = PurchaseOrder.objects.filter(
            empresa=empresa,
            order_date__range=[start_date, end_date]
        ).values('supplier__name').annotate(
            total=Sum('total_amount'),
            count=Count('id')
        ).order_by('-total')[:5]
        
        # Solicitudes recientes
        recent_requests = PurchaseRequest.objects.filter(
            empresa=empresa
        ).order_by('-request_date')[:5]
        
        # Órdenes recientes
        recent_orders = PurchaseOrder.objects.filter(
            empresa=empresa
        ).order_by('-order_date')[:5]
        
        return Response({
            'period': {
                'start_date': start_date,
                'end_date': end_date,
                'days': 30
            },
            'metrics': {
                'total_requests': total_requests,
                'pending_requests': pending_requests,
                'total_orders': total_orders,
                'total_spent': total_spent,
                'overdue_orders': overdue_orders,
                'pending_receipts': pending_receipts,
                'active_suppliers': active_suppliers
            },
            'requests_by_status': list(requests_by_status),
            'orders_by_status': list(orders_by_status),
            'top_suppliers': list(top_suppliers),
            'recent_requests': PurchaseRequestSerializer(recent_requests, many=True).data,
            'recent_orders': PurchaseOrderSerializer(recent_orders, many=True).data
        })


class PurchaseReportsView(APIView):
    """Vista para reportes de compras"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Obtener reportes de compras"""
        report_type = request.query_params.get('type', 'summary')
        empresa = request.user.empresa
        
        # Período de análisis
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if start_date:
            start_date = timezone.datetime.strptime(start_date, '%Y-%m-%d').date()
        else:
            start_date = timezone.now().date() - timedelta(days=90)
        
        if end_date:
            end_date = timezone.datetime.strptime(end_date, '%Y-%m-%d').date()
        else:
            end_date = timezone.now().date()
        
        if report_type == 'summary':
            return self._get_summary_report(empresa, start_date, end_date)
        elif report_type == 'supplier_performance':
            return self._get_supplier_performance_report(empresa, start_date, end_date)
        elif report_type == 'spending_analysis':
            return self._get_spending_analysis_report(empresa, start_date, end_date)
        elif report_type == 'delivery_performance':
            return self._get_delivery_performance_report(empresa, start_date, end_date)
        else:
            return Response({
                'error': _('Invalid report type')
            }, status=400)
    
    def _get_summary_report(self, empresa, start_date, end_date):
        """Reporte resumen de compras"""
        # Solicitudes
        total_requests = PurchaseRequest.objects.filter(
            empresa=empresa,
            request_date__range=[start_date, end_date]
        ).count()
        
        approved_requests = PurchaseRequest.objects.filter(
            empresa=empresa,
            status='approved',
            request_date__range=[start_date, end_date]
        ).count()
        
        # Órdenes
        total_orders = PurchaseOrder.objects.filter(
            empresa=empresa,
            order_date__range=[start_date, end_date]
        ).count()
        
        total_spent = PurchaseOrder.objects.filter(
            empresa=empresa,
            status__in=['confirmed', 'partially_received', 'received'],
            order_date__range=[start_date, end_date]
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        # Cotizaciones
        total_quotations = PurchaseQuotation.objects.filter(
            empresa=empresa,
            quotation_date__range=[start_date, end_date]
        ).count()
        
        # Recepciones
        total_receipts = PurchaseReceipt.objects.filter(
            empresa=empresa,
            receipt_date__range=[start_date, end_date]
        ).count()
        
        return Response({
            'report_type': 'summary',
            'period': {
                'start_date': start_date,
                'end_date': end_date
            },
            'requests': {
                'total': total_requests,
                'approved': approved_requests,
                'approval_rate': (approved_requests / total_requests * 100) if total_requests > 0 else 0
            },
            'orders': {
                'total': total_orders,
                'total_spent': total_spent,
                'average_order_value': total_spent / total_orders if total_orders > 0 else 0
            },
            'quotations': {
                'total': total_quotations
            },
            'receipts': {
                'total': total_receipts
            }
        })
    
    def _get_supplier_performance_report(self, empresa, start_date, end_date):
        """Reporte de rendimiento de proveedores"""
        # Obtener métricas de proveedores
        supplier_metrics = SupplierPerformanceMetric.objects.filter(
            empresa=empresa,
            period_start__gte=start_date,
            period_end__lte=end_date
        ).select_related('supplier')
        
        # Calcular promedios
        avg_delivery_rate = supplier_metrics.aggregate(
            avg=models.Avg('on_time_delivery_rate')
        )['avg'] or 0
        
        avg_quality_rate = supplier_metrics.aggregate(
            avg=models.Avg('quality_acceptance_rate')
        )['avg'] or 0
        
        # Top proveedores por rendimiento
        top_suppliers = supplier_metrics.order_by('-on_time_delivery_rate')[:10]
        
        return Response({
            'report_type': 'supplier_performance',
            'period': {
                'start_date': start_date,
                'end_date': end_date
            },
            'averages': {
                'delivery_rate': avg_delivery_rate,
                'quality_rate': avg_quality_rate
            },
            'top_suppliers': SupplierPerformanceSerializer(top_suppliers, many=True).data
        })
    
    def _get_spending_analysis_report(self, empresa, start_date, end_date):
        """Reporte de análisis de gastos"""
        # Gastos por mes
        monthly_spending = PurchaseOrder.objects.filter(
            empresa=empresa,
            status__in=['confirmed', 'partially_received', 'received'],
            order_date__range=[start_date, end_date]
        ).extra(
            select={'month': "EXTRACT(month FROM order_date)"}
        ).values('month').annotate(
            total=Sum('total_amount'),
            count=Count('id')
        ).order_by('month')
        
        # Gastos por proveedor
        spending_by_supplier = PurchaseOrder.objects.filter(
            empresa=empresa,
            status__in=['confirmed', 'partially_received', 'received'],
            order_date__range=[start_date, end_date]
        ).values('supplier__name').annotate(
            total=Sum('total_amount'),
            count=Count('id')
        ).order_by('-total')
        
        # Gastos por categoría (si aplica)
        spending_by_category = PurchaseOrder.objects.filter(
            empresa=empresa,
            status__in=['confirmed', 'partially_received', 'received'],
            order_date__range=[start_date, end_date]
        ).values('supplier__supplier_category__name').annotate(
            total=Sum('total_amount'),
            count=Count('id')
        ).order_by('-total')
        
        return Response({
            'report_type': 'spending_analysis',
            'period': {
                'start_date': start_date,
                'end_date': end_date
            },
            'monthly_spending': list(monthly_spending),
            'spending_by_supplier': list(spending_by_supplier),
            'spending_by_category': list(spending_by_category)
        })
    
    def _get_delivery_performance_report(self, empresa, start_date, end_date):
        """Reporte de rendimiento de entregas"""
        # Órdenes vencidas
        overdue_orders = PurchaseOrder.objects.filter(
            empresa=empresa,
            status__in=['sent', 'confirmed'],
            expected_delivery_date__lt=timezone.now().date(),
            order_date__range=[start_date, end_date]
        ).count()
        
        # Órdenes a tiempo
        on_time_orders = PurchaseOrder.objects.filter(
            empresa=empresa,
            status__in=['partially_received', 'received'],
            order_date__range=[start_date, end_date]
        ).filter(
            Q(last_receipt_date__lte=F('expected_delivery_date')) |
            Q(last_receipt_date__isnull=True, expected_delivery_date__gte=timezone.now().date())
        ).count()
        
        # Total de órdenes para cálculo
        total_orders = PurchaseOrder.objects.filter(
            empresa=empresa,
            order_date__range=[start_date, end_date]
        ).count()
        
        # Promedio de días de entrega
        delivery_times = []
        orders_with_delivery = PurchaseOrder.objects.filter(
            empresa=empresa,
            status__in=['partially_received', 'received'],
            last_receipt_date__isnull=False,
            order_date__range=[start_date, end_date]
        )
        
        for order in orders_with_delivery:
            if order.last_receipt_date and order.order_date:
                days = (order.last_receipt_date - order.order_date).days
                delivery_times.append(days)
        
        avg_delivery_time = sum(delivery_times) / len(delivery_times) if delivery_times else 0
        
        return Response({
            'report_type': 'delivery_performance',
            'period': {
                'start_date': start_date,
                'end_date': end_date
            },
            'overdue_orders': overdue_orders,
            'on_time_orders': on_time_orders,
            'total_orders': total_orders,
            'on_time_rate': (on_time_orders / total_orders * 100) if total_orders > 0 else 0,
            'avg_delivery_time': avg_delivery_time
        }) 