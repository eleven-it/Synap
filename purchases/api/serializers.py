from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from decimal import Decimal

from ..models import (
    Supplier, PurchaseRequest, PurchaseRequestLine, PurchaseQuotation, 
    PurchaseQuotationLine, PurchaseOrder, PurchaseOrderLine, PurchaseReceipt,
    PurchaseReceiptDocument, SupplierRating, SupplierPerformanceMetric,
    ApprovalWorkflow, ApprovalLevel, ApprovalRecord
)
from ..services import PurchaseService, SupplierService, ApprovalService, QuotationService

User = get_user_model()


class SupplierSerializer(serializers.ModelSerializer):
    """Serializador para proveedores"""
    contact_info = serializers.SerializerMethodField()
    full_address = serializers.SerializerMethodField()
    rating_average = serializers.SerializerMethodField()
    
    class Meta:
        model = Supplier
        fields = [
            'id', 'name', 'code', 'tax_id', 'contact_person', 'email', 'phone', 'mobile',
            'address', 'city', 'state', 'postal_code', 'country', 'payment_terms', 
            'credit_limit', 'currency', 'supplier_category', 'supplier_type', 
            'tax_category', 'is_tax_exempt', 'is_active', 'is_approved', 'approval_date',
            'approved_by', 'notes', 'website', 'created_by', 'created_at', 'updated_at',
            'contact_info', 'full_address', 'rating_average'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def validate_code(self, value):
        """Validar que el código sea único por empresa"""
        empresa = self.context['request'].user.empresa_activa
        if Supplier.objects.filter(empresa=empresa, code=value).exists():
            raise serializers.ValidationError(_("A supplier with this code already exists in your company."))
        return value

    def get_contact_info(self, obj):
        return {
            'contact_person': obj.contact_person,
            'email': obj.email,
            'phone': obj.phone,
            'mobile': obj.mobile
        }

    def get_full_address(self, obj):
        return obj.get_full_address()

    def get_rating_average(self, obj):
        return obj.get_rating_average()


class PurchaseRequestLineSerializer(serializers.ModelSerializer):
    """Serializador para líneas de solicitud de compra"""
    product_name = serializers.ReadOnlyField(source='product_variant.name')
    product_sku = serializers.ReadOnlyField(source='product_variant.sku')
    total_amount = serializers.ReadOnlyField()
    stock_deficit = serializers.ReadOnlyField(source='get_stock_deficit')
    is_stock_critical = serializers.ReadOnlyField(source='is_stock_critical')
    
    class Meta:
        model = PurchaseRequestLine
        fields = [
            'id', 'product_variant', 'product_name', 'product_sku', 'quantity',
            'unit_of_measure', 'estimated_unit_price', 'currency', 'description',
            'specifications', 'status', 'current_stock', 'minimum_stock',
            'total_amount', 'stock_deficit', 'is_stock_critical', 'created_at'
        ]
        read_only_fields = ['id', 'status', 'current_stock', 'total_amount', 'created_at']


class PurchaseRequestSerializer(serializers.ModelSerializer):
    """Serializador para solicitudes de compra"""
    lines = PurchaseRequestLineSerializer(many=True, read_only=True)
    lines_data = serializers.ListField(write_only=True, required=False)
    total_amount = serializers.ReadOnlyField()
    status_display = serializers.ReadOnlyField(source='get_status_display')
    priority_display = serializers.ReadOnlyField(source='get_priority_display')
    requested_by_name = serializers.ReadOnlyField(source='requested_by.get_full_name')
    approval_status = serializers.SerializerMethodField()
    
    class Meta:
        model = PurchaseRequest
        fields = [
            'id', 'request_number', 'title', 'description', 'status', 'status_display',
            'priority', 'priority_display', 'request_date', 'required_date',
            'approved_date', 'approved_by', 'rejection_reason',
            'currency', 'total_amount', 'lines', 'lines_data', 'requested_by_name',
            'approval_status', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'request_number', 'status', 'request_date', 'approved_date',
            'approved_by', 'total_amount', 'created_at', 'updated_at'
        ]
    
    def get_approval_status(self, obj):
        """Obtener estado de aprobación"""
        if obj.status == 'pending_approval':
            return {
                'current_level': obj.current_approval_level,
                'approvals_received': obj.approvals_received,
                'workflow': obj.approval_workflow.name if obj.approval_workflow else None
            }
        return None
    
    def create(self, validated_data):
        """Crear solicitud con líneas"""
        lines_data = validated_data.pop('lines', [])
        with transaction.atomic():
            validated_data['empresa'] = self.context['request'].user.empresa_activa
            validated_data['branch'] = self.context['request'].user.branch_activa
            validated_data['requested_by'] = self.context['request'].user
            instance = super().create(validated_data)
            for line_data in lines_data:
                line_data['purchase_request'] = instance
                PurchaseRequestLine.objects.create(**line_data)
            return instance
    
    def update(self, instance, validated_data):
        """Actualizar solicitud"""
        if 'status' in validated_data:
            new_status = validated_data['status']
            
            if new_status == 'submitted':
                # Crear workflow de aprobación si no existe
                if not instance.approval_workflow:
                    approval_service = ApprovalService()
                    workflow = approval_service.create_approval_workflow(
                        empresa=instance.empresa,
                        branch=instance.branch,
                        name="Aprobación única",
                        levels=[
                            {
                                'name': 'Aprobación única',
                                'approval_type': 'any_role',
                                'min_approvals': 1
                            }
                        ]
                    )
                    instance.approval_workflow = workflow
                    instance.save()
                
                # Iniciar proceso de aprobación
                approval_service.initiate_approval_process(instance)
                validated_data['status'] = 'pending_approval'
            
            elif new_status == 'approved':
                # Aprobar solicitud
                approval_service = ApprovalService()
                result = approval_service.approve_request(
                    request=instance,
                    user=self.context['request'].user
                )
                if result:
                    validated_data['status'] = 'approved'
            
            elif new_status == 'rejected':
                # Rechazar solicitud
                approval_service = ApprovalService()
                result = approval_service.reject_request(
                    request=instance,
                    user=self.context['request'].user,
                    reason=validated_data.get('rejection_reason', '')
                )
                if result:
                    validated_data['status'] = 'rejected'
        
        return super().update(instance, validated_data)


class PurchaseQuotationLineSerializer(serializers.ModelSerializer):
    """Serializador para líneas de cotización"""
    product_name = serializers.ReadOnlyField(source='product_variant.name')
    product_sku = serializers.ReadOnlyField(source='product_variant.sku')
    unit_price_with_discount = serializers.ReadOnlyField()
    effective_unit_price = serializers.ReadOnlyField()
    
    class Meta:
        model = PurchaseQuotationLine
        fields = [
            'id', 'request_line', 'product_variant', 'product_name', 'product_sku',
            'quantity', 'unit_price', 'unit_of_measure', 'discount_percentage',
            'discount_amount', 'tax_percentage', 'tax_amount', 'subtotal', 'total',
            'description', 'specifications', 'delivery_time', 'minimum_order_quantity',
            'unit_price_with_discount', 'effective_unit_price', 'created_at'
        ]
        read_only_fields = ['id', 'discount_amount', 'tax_amount', 'subtotal', 'total', 'created_at']


class PurchaseQuotationSerializer(serializers.ModelSerializer):
    """Serializador para cotizaciones"""
    lines = PurchaseQuotationLineSerializer(many=True, read_only=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    total_amount = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    
    class Meta:
        model = PurchaseQuotation
        fields = [
            'id', 'quotation_number', 'supplier', 'supplier_name', 'status', 
            'quotation_date', 'valid_until', 'currency', 'exchange_rate',
            'subtotal', 'tax_amount', 'discount_amount', 'total_amount', 
            'notes', 'supplier_notes', 'lines', 'created_at', 'updated_at'
        ]
        read_only_fields = ['quotation_number', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        """Crear cotización con líneas"""
        lines_data = validated_data.pop('lines_data', [])
        
        with transaction.atomic():
            # Establecer empresa y usuario
            validated_data['empresa'] = self.context['request'].user.empresa_activa
            validated_data['branch'] = self.context['request'].user.branch_activa
            validated_data['created_by'] = self.context['request'].user
            
            # Crear la cotización
            instance = super().create(validated_data)
            
            # Crear las líneas si se proporcionaron
            if lines_data:
                for line_data in lines_data:
                    line_data['purchase_quotation'] = instance
                    PurchaseQuotationLine.objects.create(**line_data)
            
            return instance
    
    def update(self, instance, validated_data):
        """Actualizar cotización"""
        lines_data = validated_data.pop('lines_data', None)
        
        with transaction.atomic():
            # Actualizar cotización
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()
            
            # Actualizar líneas si se proporcionan
            if lines_data is not None:
                # Eliminar líneas existentes
                instance.lines.all().delete()
                
                # Crear nuevas líneas
                for line_data in lines_data:
                    line_data['purchase_quotation'] = instance
                    PurchaseQuotationLine.objects.create(**line_data)
            
            return instance


class PurchaseOrderLineSerializer(serializers.ModelSerializer):
    """Serializador para líneas de orden de compra"""
    product_name = serializers.ReadOnlyField(source='product_variant.name')
    product_sku = serializers.ReadOnlyField(source='product_variant.sku')
    remaining_quantity = serializers.ReadOnlyField()
    receipt_progress = serializers.ReadOnlyField()
    effective_unit_price = serializers.ReadOnlyField()
    
    class Meta:
        model = PurchaseOrderLine
        fields = [
            'id', 'request_line', 'quotation_line', 'product_variant', 'product_name',
            'product_sku', 'quantity', 'received_quantity', 'remaining_quantity',
            'unit_of_measure', 'unit_price', 'discount_percentage', 'discount_amount',
            'tax_percentage', 'tax_amount', 'shipping_amount', 'subtotal', 'total',
            'description', 'specifications', 'status', 'receipt_progress',
            'effective_unit_price', 'created_at'
        ]
        read_only_fields = [
            'id', 'received_quantity', 'remaining_quantity', 'discount_amount',
            'tax_amount', 'subtotal', 'total', 'receipt_progress', 'effective_unit_price',
            'created_at'
        ]


class PurchaseOrderSerializer(serializers.ModelSerializer):
    """Serializador para órdenes de compra"""
    lines = PurchaseOrderLineSerializer(many=True, read_only=True)
    lines_data = serializers.ListField(write_only=True, required=False)
    supplier_name = serializers.ReadOnlyField(source='supplier.name')
    status_display = serializers.ReadOnlyField(source='get_status_display')
    is_overdue = serializers.ReadOnlyField()
    receipt_progress = serializers.ReadOnlyField(source='get_receipt_progress')
    total_in_base_currency = serializers.ReadOnlyField(source='get_total_in_base_currency')
    
    class Meta:
        model = PurchaseOrder
        fields = [
            'id', 'order_number', 'supplier', 'supplier_name', 'purchase_request',
            'quotation', 'status', 'status_display', 'order_date', 'expected_delivery_date',
            'confirmed_date', 'first_receipt_date', 'last_receipt_date', 'currency',
            'exchange_rate', 'payment_terms', 'delivery_terms', 'delivery_address',
            'subtotal', 'tax_amount', 'discount_amount', 'shipping_amount', 'total_amount',
            'total_in_base_currency', 'notes', 'supplier_notes', 'lines', 'lines_data',
            'is_overdue', 'receipt_progress', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'order_number', 'order_date', 'confirmed_date', 'first_receipt_date',
            'last_receipt_date', 'subtotal', 'tax_amount', 'discount_amount',
            'shipping_amount', 'total_amount', 'is_overdue', 'receipt_progress',
            'created_at', 'updated_at'
        ]
    
    def create(self, validated_data):
        """Crear orden con líneas"""
        lines_data = validated_data.pop('lines', [])
        with transaction.atomic():
            validated_data['empresa'] = self.context['request'].user.empresa_activa
            validated_data['branch'] = self.context['request'].user.branch_activa
            validated_data['created_by'] = self.context['request'].user
            instance = super().create(validated_data)
            for line_data in lines_data:
                line_data['purchase_order'] = instance
                PurchaseOrderLine.objects.create(**line_data)
            return instance
    
    def update(self, instance, validated_data):
        """Actualizar orden"""
        lines_data = validated_data.pop('lines_data', None)
        
        with transaction.atomic():
            # Actualizar orden
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()
            
            # Actualizar líneas si se proporcionan
            if lines_data is not None:
                # Eliminar líneas existentes
                instance.lines.all().delete()
                
                # Crear nuevas líneas
                for line_data in lines_data:
                    line_data['purchase_order'] = instance
                    PurchaseOrderLine.objects.create(**line_data)
            
            return instance


class PurchaseReceiptSerializer(serializers.ModelSerializer):
    """Serializador para recepciones"""
    product_name = serializers.ReadOnlyField(source='purchase_order_line.product_variant.name')
    product_sku = serializers.ReadOnlyField(source='purchase_order_line.product_variant.sku')
    supplier_name = serializers.ReadOnlyField(source='supplier.name')
    status_display = serializers.ReadOnlyField(source='get_status_display')
    quality_status = serializers.ReadOnlyField(source='get_quality_status')
    is_expired = serializers.ReadOnlyField()
    days_until_expiration = serializers.ReadOnlyField(source='get_days_until_expiration')
    expiration_status = serializers.ReadOnlyField(source='get_expiration_status')
    
    class Meta:
        model = PurchaseReceipt
        fields = [
            'id', 'receipt_number', 'purchase_order_line', 'product_name', 'product_sku',
            'quantity', 'receipt_date', 'received_at', 'lot_number', 'expiration_date',
            'manufacturing_date', 'status', 'status_display', 'quality_score',
            'quality_notes', 'packaging_condition', 'notes', 'supplier_notes',
            'received_by', 'inspected_by', 'supplier_name', 'quality_status',
            'is_expired', 'days_until_expiration', 'expiration_status', 'created_at'
        ]
        read_only_fields = [
            'id', 'receipt_number', 'receipt_date', 'received_at', 'supplier_name',
            'quality_status', 'is_expired', 'days_until_expiration', 'expiration_status',
            'created_at'
        ]
    
    def create(self, validated_data):
        """Crear recepción con líneas"""
        lines_data = validated_data.pop('lines_data', [])
        
        with transaction.atomic():
            # Establecer empresa y usuario
            validated_data['empresa'] = self.context['request'].user.empresa_activa
            validated_data['branch'] = self.context['request'].user.branch_activa
            validated_data['received_by'] = self.context['request'].user
            
            # Crear la recepción
            instance = super().create(validated_data)
            
            # Crear las líneas si se proporcionaron
            if lines_data:
                for line_data in lines_data:
                    line_data['purchase_receipt'] = instance
                    PurchaseReceiptLine.objects.create(**line_data)
            
            return instance


class SupplierRatingSerializer(serializers.ModelSerializer):
    """Serializador para evaluaciones de proveedores"""
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    order_number = serializers.CharField(source='purchase_order.order_number', read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.username', read_only=True)
    rating_class_display = serializers.CharField(source='get_rating_class_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    trend_analysis = serializers.SerializerMethodField()
    
    class Meta:
        model = SupplierRating
        fields = [
            'id', 'supplier', 'supplier_name', 'purchase_order', 'order_number',
            'rating_date', 'period_start', 'period_end', 'quality_score', 'delivery_score', 
            'communication_score', 'price_score', 'service_score', 'overall_score',
            'rating_class', 'rating_class_display', 'quality_comments', 'delivery_comments',
            'communication_comments', 'price_comments', 'service_comments', 'general_comments',
            'recommendations', 'would_recommend', 'status', 'status_display',
            'evaluated_by', 'reviewed_by', 'reviewed_by_name', 'trend_analysis', 
            'created_at', 'updated_at'
        ]
        read_only_fields = ['rating_date', 'evaluated_by', 'created_at', 'updated_at']
    
    def get_trend_analysis(self, obj):
        return {
            'trend': 'stable',
            'previous_score': None,
            'change': 0
        }
    
    def create(self, validated_data):
        """Crear evaluación"""
        validated_data['empresa'] = self.context['request'].user.empresa_activa
        validated_data['branch'] = self.context['request'].user.branch_activa
        validated_data['evaluated_by'] = self.context['request'].user
        
        return super().create(validated_data)


class ApprovalWorkflowSerializer(serializers.ModelSerializer):
    """Serializador para flujos de aprobación"""
    levels_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ApprovalWorkflow
        fields = [
            'id', 'name', 'description', 'is_active', 'requires_all_approvals',
            'min_amount', 'max_amount', 'levels_count', 'created_by', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_levels_count(self, obj):
        """Obtener número de niveles"""
        return obj.levels.count()


class ApprovalLevelSerializer(serializers.ModelSerializer):
    """Serializador para niveles de aprobación"""
    workflow_name = serializers.ReadOnlyField(source='workflow.name')
    
    class Meta:
        model = ApprovalLevel
        fields = [
            'id', 'workflow', 'workflow_name', 'name', 'priority', 'approval_type',
            'approvers', 'roles', 'groups', 'is_active', 'requires_all_approvers',
            'max_approval_time', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ApprovalRecordSerializer(serializers.ModelSerializer):
    """Serializador para registros de aprobación"""
    level_name = serializers.ReadOnlyField(source='level.name')
    approver_name = serializers.ReadOnlyField(source='approver.get_full_name')
    action_display = serializers.ReadOnlyField(source='get_action_display')
    action_color = serializers.ReadOnlyField()
    action_icon = serializers.ReadOnlyField()
    duration_hours = serializers.ReadOnlyField()
    
    class Meta:
        model = ApprovalRecord
        fields = [
            'id', 'request', 'level', 'level_name', 'approver', 'approver_name',
            'action', 'action_display', 'comments', 'approved_at', 'action_color',
            'action_icon', 'duration_hours', 'created_at'
        ]
        read_only_fields = ['id', 'approved_at', 'created_at']


# Serializadores para acciones específicas
class PurchaseRequestSubmitSerializer(serializers.Serializer):
    """Serializador para enviar solicitud a aprobación"""
    
    def validate(self, attrs):
        return attrs
    
    def update(self, instance, validated_data):
        """Enviar solicitud a aprobación"""
        from ..services import ApprovalService
        
        # Asegurar que tenga un workflow asignado
        if not instance.approval_workflow:
            approval_service = ApprovalService()
            approval_service.set_user(self.context['request'].user)
            
            # Buscar workflow aplicable
            workflow = approval_service.get_applicable_workflow(
                empresa=instance.empresa,
                amount=instance.total_amount_value,
                category=None
            )
            
            # Si no hay workflow aplicable, crear uno por defecto
            if not workflow:
                workflow = approval_service.create_approval_workflow(
                    empresa=instance.empresa,
                    name="Workflow por defecto",
                    description="Workflow automático para solicitudes sin flujo asignado",
                    min_amount=0,
                    max_amount=999999999,
                    levels_data=[
                        {
                            'name': 'Aprobación única',
                            'approval_type': 'any',
                            'min_approvals': 1,
                            'auto_approve': True
                        }
                    ]
                )
            
            instance.approval_workflow = workflow
            instance.save()
        
        # Iniciar proceso de aprobación
        approval_service = ApprovalService()
        approval_service.set_user(self.context['request'].user)
        result = approval_service.initiate_approval_process(instance)
        
        return instance


class PurchaseRequestApproveSerializer(serializers.Serializer):
    """Serializador para aprobar solicitud"""
    comments = serializers.CharField(required=False, allow_blank=True)
    
    def update(self, instance, validated_data):
        """Aprobar solicitud"""
        approval_service = ApprovalService().set_user(self.context['request'].user)
        result = approval_service.approve_request(
            instance, 
            self.context['request'].user, 
            validated_data.get('comments', '')
        )
        
        if result['status'] == 'approved':
            instance.status = 'approved'
            instance.approved_by = self.context['request'].user
            instance.approved_date = timezone.now().date()
            instance.save()
        
        return instance


class PurchaseRequestRejectSerializer(serializers.Serializer):
    """Serializador para rechazar solicitud"""
    reason = serializers.CharField()
    
    def update(self, instance, validated_data):
        """Rechazar solicitud"""
        approval_service = ApprovalService().set_user(self.context['request'].user)
        result = approval_service.reject_request(
            instance, 
            self.context['request'].user, 
            validated_data['reason']
        )
        
        instance.status = 'rejected'
        instance.rejection_reason = validated_data['reason']
        instance.save()
        
        return instance


class PurchaseOrderSendSerializer(serializers.Serializer):
    """Serializador para enviar orden al proveedor"""
    
    def update(self, instance, validated_data):
        """Enviar orden al proveedor"""
        instance.send_to_supplier()
        return instance


class PurchaseOrderConfirmSerializer(serializers.Serializer):
    """Serializador para confirmar orden"""
    
    def update(self, instance, validated_data):
        """Confirmar orden"""
        instance.confirm(self.context['request'].user)
        return instance


class PurchaseReceiptApproveSerializer(serializers.Serializer):
    """Serializador para aprobar recepción"""
    quality_score = serializers.IntegerField(min_value=1, max_value=10, required=False)
    quality_notes = serializers.CharField(required=False, allow_blank=True)
    
    def update(self, instance, validated_data):
        """Aprobar recepción"""
        instance.approve(
            self.context['request'].user,
            validated_data.get('quality_score'),
            validated_data.get('quality_notes', '')
        )
        return instance


class QuotationCompareSerializer(serializers.Serializer):
    """Serializador para comparar cotizaciones"""
    include_expired = serializers.BooleanField(default=False)
    
    def to_representation(self, instance):
        """Comparar cotizaciones de una solicitud"""
        quotation_service = QuotationService().set_user(self.context['request'].user)
        return quotation_service.compare_quotations(instance, self.validated_data.get('include_expired', False))


class QuotationSelectSerializer(serializers.Serializer):
    """Serializador para seleccionar cotización"""
    reason = serializers.CharField(required=False, allow_blank=True)
    
    def update(self, instance, validated_data):
        """Seleccionar cotización"""
        quotation_service = QuotationService().set_user(self.context['request'].user)
        result = quotation_service.select_quotation(
            instance, 
            self.context['request'].user, 
            validated_data.get('reason', '')
        )
        return instance


class SupplierPerformanceSerializer(serializers.ModelSerializer):
    """Serializador para métricas de rendimiento de proveedores"""
    
    class Meta:
        model = SupplierPerformanceMetric
        fields = '__all__'
        read_only_fields = ['id', 'calculated_at', 'updated_at']


class PurchaseReceiptDocumentSerializer(serializers.ModelSerializer):
    """Serializador para documentos de recepción"""
    
    class Meta:
        model = PurchaseReceiptDocument
        fields = [
            'id', 'receipt', 'document_type', 'file', 'description', 'uploaded_at'
        ]
        read_only_fields = ['id', 'uploaded_at']
    
    def create(self, validated_data):
        """Crear documento con usuario"""
        validated_data['uploaded_by'] = self.context['request'].user
        return super().create(validated_data) 