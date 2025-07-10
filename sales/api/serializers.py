from rest_framework import serializers
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from sales.models import Client, SalesOrder, SalesOrderLine, PriceList, PriceListItem, PaymentTerm, PaymentTermLine, Invoice, InvoiceLine, Payment, DeliveryOrder, DeliveryOrderLine, ReturnDelivery, CreditNote, ApprovalLog
from inventory.models import ProductVariant, Warehouse
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from core.models import Contact, ContactRelationship

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Serializer para usuarios (vendedores)"""
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'full_name', 'email']
    
    def get_full_name(self, obj):
        return obj.get_full_name()


class ContactSerializer(serializers.ModelSerializer):
    """Serializer para contactos universales"""
    display_name = serializers.SerializerMethodField()
    full_address = serializers.SerializerMethodField()
    
    class Meta:
        model = Contact
        fields = [
            'id', 'name', 'type', 'first_name', 'last_name', 'company_name', 
            'position', 'department', 'email', 'phone', 'mobile', 'fax', 
            'website', 'address', 'postal_code', 'city', 'state', 'country',
            'latitude', 'longitude', 'notes', 'tags', 'photo', 'is_active', 
            'is_primary', 'display_name', 'full_address', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_display_name(self, obj):
        return obj.display_name
    
    def get_full_address(self, obj):
        return obj.full_address
    
    def validate_email(self, value):
        """Validar que el email sea único si se proporciona"""
        if value:
            contact_id = self.instance.id if self.instance else None
            if Contact.objects.filter(email=value).exclude(id=contact_id).exists():
                raise serializers.ValidationError("Este email ya está registrado.")
        return value
    
    def validate_phone(self, value):
        """Validar formato de teléfono"""
        if value and not value.replace('+', '').replace('-', '').replace(' ', '').replace('(', '').replace(')', '').isdigit():
            raise serializers.ValidationError("El número de teléfono debe contener solo dígitos, espacios, guiones y paréntesis.")
        return value


class ClientSerializer(serializers.ModelSerializer):
    """Serializer para clientes"""
    sales_person_name = serializers.CharField(source='sales_person.get_full_name', read_only=True)
    display_name = serializers.SerializerMethodField()
    contacts = ContactSerializer(many=True, read_only=True)
    contacts_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Client
        fields = [
            'id', 'name', 'code', 'tax_id', 'address', 'city', 'state', 'postal_code', 'country',
            'contact_person', 'email', 'phone', 'mobile', 'website', 'notes', 'is_active',
            'credit_limit', 'payment_terms', 'customer_category', 'fiscal_conditions',
            'default_price_list', 'sales_person', 'sales_person_name', 'default_delivery_location',
            'invoice_delivery_method', 'payment_method', 'default_discount',
            'is_customer', 'is_prospect', 'is_vip', 'display_name', 'contacts', 'contacts_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_display_name(self, obj):
        return str(obj)
    
    def get_contacts_count(self, obj):
        return obj.get_contacts().count()
    
    def validate_email(self, value):
        """Validar que el email sea único si se proporciona"""
        if value:
            client_id = self.instance.id if self.instance else None
            if Client.objects.filter(email=value).exclude(id=client_id).exists():
                raise serializers.ValidationError("Este email ya está registrado.")
        return value
    
    def validate_tax_id(self, value):
        """Validar formato de Tax ID"""
        if value:
            # Implementar validación específica por país si es necesario
            if len(value) < 3:
                raise serializers.ValidationError("El ID fiscal debe tener al menos 3 caracteres.")
        return value
    
    def validate_phone(self, value):
        """Validar formato de teléfono"""
        if value and not value.replace('+', '').replace('-', '').replace(' ', '').replace('(', '').replace(')', '').isdigit():
            raise serializers.ValidationError("El número de teléfono debe contener solo dígitos, espacios, guiones y paréntesis.")
        return value
    
    def validate(self, data):
        """Validaciones adicionales"""
        client_type = data.get('client_type')
        
        if client_type == 'individual':
            if not data.get('first_name') or not data.get('last_name'):
                raise serializers.ValidationError("Para clientes individuales, el nombre y apellido son obligatorios.")
            if data.get('company_name'):
                raise serializers.ValidationError("Los clientes individuales no pueden tener nombre de empresa.")
        
        elif client_type == 'company':
            if not data.get('company_name'):
                raise serializers.ValidationError("Para empresas, el nombre de la empresa es obligatorio.")
            if data.get('first_name') or data.get('last_name'):
                raise serializers.ValidationError("Las empresas no pueden tener nombre y apellido individuales.")
        
        return data


class ClientListSerializer(serializers.ModelSerializer):
    """Serializer simplificado para listar clientes"""
    display_name = serializers.SerializerMethodField()
    sales_representative_name = serializers.CharField(source='sales_representative.get_full_name', read_only=True)
    contacts_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Client
        fields = [
            'id', 'client_type', 'display_name', 'email', 'phone', 'country', 
            'city', 'customer_category', 'status', 'sales_representative_name',
            'contacts_count', 'created_at'
        ]
        read_only_fields = ['created_at']
    
    def get_display_name(self, obj):
        return obj.get_display_name()
    
    def get_contacts_count(self, obj):
        return obj.contacts.count()


class ContactListSerializer(serializers.ModelSerializer):
    """Serializer simplificado para listar contactos"""
    display_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Contact
        fields = [
            'id', 'name', 'type', 'first_name', 'last_name', 'company_name', 
            'position', 'department', 'email', 'phone', 'mobile', 'display_name', 
            'is_active', 'is_primary', 'created_at'
        ]
        read_only_fields = ['created_at']
    
    def get_display_name(self, obj):
        return obj.display_name


class ClientStatsSerializer(serializers.Serializer):
    """Serializer para estadísticas de clientes"""
    total_clients = serializers.IntegerField()
    active_clients = serializers.IntegerField()
    individual_clients = serializers.IntegerField()
    company_clients = serializers.IntegerField()
    clients_by_category = serializers.DictField()
    clients_by_status = serializers.DictField()
    recent_clients = serializers.IntegerField()
    total_contacts = serializers.IntegerField()


class ContactStatsSerializer(serializers.Serializer):
    """Serializer para estadísticas de contactos"""
    total_contacts = serializers.IntegerField()
    active_contacts = serializers.IntegerField()
    primary_contacts = serializers.IntegerField()
    contacts_by_role = serializers.DictField()
    contacts_by_department = serializers.DictField()
    recent_contacts = serializers.IntegerField()


class AutocompleteSerializer(serializers.Serializer):
    """Serializer para autocompletado"""
    id = serializers.IntegerField()
    name = serializers.CharField()
    code = serializers.CharField(required=False)
    additional_info = serializers.CharField(required=False)


class PriceListItemSerializer(serializers.ModelSerializer):
    """Serializer para items de lista de precios"""
    product_name = serializers.CharField(source='product_variant.product.name', read_only=True)
    variant_name = serializers.CharField(source='product_variant.name', read_only=True)
    
    class Meta:
        model = PriceListItem
        fields = [
            'id', 'price_list', 'product_variant', 'product_name', 'variant_name',
            'price', 'min_qty', 'max_qty', 'discount', 'promo_code', 'rule_type',
            'valid_from', 'valid_to'
        ]
        read_only_fields = ['id']


class PriceListSerializer(serializers.ModelSerializer):
    """Serializer para listas de precios con items anidados"""
    items = PriceListItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = PriceList
        fields = [
            'id', 'name', 'currency', 'valid_from', 'valid_to', 'is_active', 'items'
        ]
        read_only_fields = ['id']


class PaymentTermLineSerializer(serializers.ModelSerializer):
    """Serializer para líneas de condiciones de pago"""
    
    class Meta:
        model = PaymentTermLine
        fields = [
            'id', 'payment_term', 'percent', 'days', 'sequence'
        ]
        read_only_fields = ['id']


class PaymentTermSerializer(serializers.ModelSerializer):
    """Serializer para condiciones de pago con líneas anidadas"""
    lines = PaymentTermLineSerializer(many=True, read_only=True)
    
    class Meta:
        model = PaymentTerm
        fields = [
            'id', 'name', 'description', 'lines', 'is_active'
        ]
        read_only_fields = ['id']


class SalesOrderLineSerializer(serializers.ModelSerializer):
    """Serializer para líneas de pedido de venta"""
    product_name = serializers.CharField(source='product_variant.product.name', read_only=True)
    variant_name = serializers.CharField(source='product_variant.name', read_only=True)
    
    class Meta:
        model = SalesOrderLine
        fields = [
            'id', 'sales_order', 'product_variant', 'product_name', 'variant_name',
            'quantity', 'unit_price', 'discount', 'subtotal', 'description', 'state'
        ]
        read_only_fields = ['id', 'subtotal']
    
    def validate_quantity(self, value):
        """Validar que la cantidad sea positiva"""
        if value <= 0:
            raise serializers.ValidationError("La cantidad debe ser mayor a 0")
        return value
    
    def validate_unit_price(self, value):
        """Validar que el precio unitario sea positivo"""
        if value <= 0:
            raise serializers.ValidationError("El precio unitario debe ser mayor a 0")
        return value


class SalesOrderSerializer(serializers.ModelSerializer):
    """Serializer para pedidos de venta con líneas anidadas"""
    lines = SalesOrderLineSerializer(many=True, read_only=True)
    client_name = serializers.CharField(source='client.name', read_only=True)
    
    class Meta:
        model = SalesOrder
        fields = [
            'id', 'number', 'state', 'order_date', 'total', 'total_discount',
            'total_tax', 'currency', 'origin', 'external_id', 'client', 'client_name',
            'branch', 'payment_term', 'price_list', 'seller', 'manual_credit_override',
            'credit_override_reason', 'lines'
        ]
        read_only_fields = ['id', 'number']


class InvoiceLineSerializer(serializers.ModelSerializer):
    """Serializer para líneas de factura"""
    product_name = serializers.CharField(source='product_variant.product.name', read_only=True)
    variant_name = serializers.CharField(source='product_variant.name', read_only=True)
    
    class Meta:
        model = InvoiceLine
        fields = [
            'id', 'invoice', 'product_variant', 'product_name', 'variant_name',
            'quantity', 'unit_price', 'discount', 'subtotal', 'description'
        ]
        read_only_fields = ['id', 'subtotal']


class InvoiceSerializer(serializers.ModelSerializer):
    """Serializer para facturas con líneas anidadas"""
    lines = InvoiceLineSerializer(many=True, read_only=True)
    client_name = serializers.CharField(source='client.name', read_only=True)
    sales_order_number = serializers.CharField(source='sales_order.number', read_only=True)
    
    class Meta:
        model = Invoice
        fields = [
            'id', 'number', 'state', 'invoice_date', 'total', 'currency', 'client',
            'client_name', 'sales_order', 'sales_order_number', 'payment_term',
            'branch', 'origin', 'external_id', 'invoice_type', 'lines'
        ]
        read_only_fields = ['id', 'number']


class PaymentSerializer(serializers.ModelSerializer):
    """Serializer para pagos"""
    invoice_number = serializers.CharField(source='invoice.number', read_only=True)
    client_name = serializers.CharField(source='client.name', read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id', 'number', 'state', 'payment_date', 'amount', 'currency', 'client',
            'client_name', 'invoice', 'invoice_number', 'sales_order', 'payment_method',
            'external_id', 'origin'
        ]
        read_only_fields = ['id', 'number']
    
    def validate_amount(self, value):
        """Validar que el monto sea positivo"""
        if value <= 0:
            raise serializers.ValidationError("El monto debe ser mayor a 0")
        return value


class DeliveryOrderLineSerializer(serializers.ModelSerializer):
    """Serializer para líneas de orden de entrega"""
    product_name = serializers.CharField(source='product_variant.product.name', read_only=True)
    variant_name = serializers.CharField(source='product_variant.name', read_only=True)
    
    class Meta:
        model = DeliveryOrderLine
        fields = [
            'id', 'delivery_order', 'product_variant', 'product_name', 'variant_name',
            'quantity', 'state'
        ]
        read_only_fields = ['id']


class DeliveryOrderSerializer(serializers.ModelSerializer):
    """Serializer para órdenes de entrega"""
    lines = DeliveryOrderLineSerializer(many=True, read_only=True)
    client_name = serializers.CharField(source='sales_order.client.name', read_only=True)
    sales_order_number = serializers.CharField(source='sales_order.number', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    
    class Meta:
        model = DeliveryOrder
        fields = [
            'id', 'number', 'state', 'delivery_date', 'sales_order', 'sales_order_number',
            'branch', 'warehouse', 'warehouse_name', 'origin', 'external_id', 'lines'
        ]
        read_only_fields = ['id', 'number']


class ReturnDeliverySerializer(serializers.ModelSerializer):
    """Serializer para devoluciones"""
    client_name = serializers.CharField(source='sales_order.client.name', read_only=True)
    sales_order_number = serializers.CharField(source='sales_order.number', read_only=True)
    
    class Meta:
        model = ReturnDelivery
        fields = [
            'id', 'number', 'state', 'return_date', 'sales_order', 'sales_order_number',
            'delivery_order', 'warehouse', 'return_type', 'reason', 'origin', 'external_id'
        ]
        read_only_fields = ['id', 'number']


class CreditNoteSerializer(serializers.ModelSerializer):
    """Serializer para notas de crédito"""
    invoice_number = serializers.CharField(source='invoice.number', read_only=True)
    client_name = serializers.CharField(source='client.name', read_only=True)
    
    class Meta:
        model = CreditNote
        fields = [
            'id', 'number', 'state', 'credit_date', 'amount', 'currency', 'client',
            'client_name', 'invoice', 'invoice_number', 'sales_order', 'reason',
            'origin', 'external_id'
        ]
        read_only_fields = ['id', 'number']


class ApprovalLogSerializer(serializers.ModelSerializer):
    """Serializer para logs de aprobación"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = ApprovalLog
        fields = [
            'id', 'sales_order', 'user', 'user_name', 'action', 'reason', 'action_date'
        ]
        read_only_fields = ['id', 'action_date']


# Serializers para operaciones complejas
class SalesOrderCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear pedidos de venta con líneas"""
    lines = SalesOrderLineSerializer(many=True)
    
    class Meta:
        model = SalesOrder
        fields = [
            'client', 'order_date', 'currency', 'origin', 'branch', 'payment_term',
            'price_list', 'seller', 'lines'
        ]
    
    @transaction.atomic
    def create(self, validated_data):
        """Crear pedido con líneas en una transacción"""
        lines_data = validated_data.pop('lines')
        
        # Generar número de pedido
        validated_data['number'] = self.generate_order_number()
        validated_data['state'] = 'draft'
        validated_data['total'] = 0
        validated_data['total_discount'] = 0
        validated_data['total_tax'] = 0
        
        # Crear pedido
        sales_order = SalesOrder.objects.create(**validated_data)
        
        # Crear líneas
        total = 0
        total_discount = 0
        total_tax = 0
        
        for line_data in lines_data:
            line_data['sales_order'] = sales_order
            line_data['state'] = 'draft'
            
            # Calcular subtotal
            quantity = line_data['quantity']
            unit_price = line_data['unit_price']
            discount = line_data.get('discount', 0)
            
            subtotal = quantity * unit_price
            discount_amount = subtotal * (discount / 100)
            line_subtotal = subtotal - discount_amount
            
            line_data['subtotal'] = line_subtotal
            
            SalesOrderLine.objects.create(**line_data)
            
            total += subtotal
            total_discount += discount_amount
            # Aquí se calcularía el impuesto según la configuración
        
        # Actualizar totales del pedido
        sales_order.total = total
        sales_order.total_discount = total_discount
        sales_order.total_tax = total_tax
        sales_order.save()
        
        return sales_order
    
    def generate_order_number(self):
        """Generar número único de pedido"""
        from django.db.models import Max
        last_order = SalesOrder.objects.aggregate(
            max_number=Max('number')
        )['max_number']
        
        if last_order:
            # Extraer número y incrementar
            try:
                number = int(last_order.split('-')[-1]) + 1
            except (ValueError, IndexError):
                number = 1
        else:
            number = 1
        
        return f"SO-{timezone.now().strftime('%Y%m')}-{number:04d}"


class InvoiceCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear facturas desde pedidos"""
    lines = InvoiceLineSerializer(many=True)
    
    class Meta:
        model = Invoice
        fields = [
            'client', 'sales_order', 'invoice_date', 'payment_term', 'currency',
            'total', 'state', 'invoice_type', 'lines'
        ]
    
    @transaction.atomic
    def create(self, validated_data):
        """Crear factura con líneas en una transacción"""
        lines_data = validated_data.pop('lines')
        
        # Generar número de factura
        validated_data['number'] = self.generate_invoice_number()
        
        # Crear factura
        invoice = Invoice.objects.create(**validated_data)
        
        # Crear líneas
        for line_data in lines_data:
            line_data['invoice'] = invoice
            
            # Calcular subtotal
            quantity = line_data['quantity']
            unit_price = line_data['unit_price']
            discount = line_data.get('discount', 0)
            
            subtotal = quantity * unit_price
            discount_amount = subtotal * (discount / 100)
            line_subtotal = subtotal - discount_amount
            
            line_data['subtotal'] = line_subtotal
            
            InvoiceLine.objects.create(**line_data)
        
        return invoice
    
    def generate_invoice_number(self):
        """Generar número único de factura"""
        from django.db.models import Max
        last_invoice = Invoice.objects.aggregate(
            max_number=Max('number')
        )['max_number']
        
        if last_invoice:
            try:
                number = int(last_invoice.split('-')[-1]) + 1
            except (ValueError, IndexError):
                number = 1
        else:
            number = 1
        
        return f"INV-{timezone.now().strftime('%Y%m')}-{number:04d}" 