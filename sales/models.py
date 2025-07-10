from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone as dj_timezone
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
import uuid
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.core.cache import cache
import re
from core.mixins import ContactableMixin
from core.models import BusinessEntity

# --- CONSTANTES DE ESTADOS ---
class SalesOrderStates:
    """Estados del pedido de venta"""
    DRAFT = 'draft'                    # Borrador/Cotización
    QUOTATION_SENT = 'quotation_sent'  # Cotización enviada al cliente
    CONFIRMED = 'confirmed'            # Pedido confirmado por el cliente
    IN_PROCESS = 'in_process'          # En proceso de preparación
    READY_TO_DELIVER = 'ready_to_deliver'  # Listo para entregar
    PARTIALLY_DELIVERED = 'partially_delivered'  # Parcialmente entregado
    DELIVERED = 'delivered'            # Completamente entregado
    INVOICED = 'invoiced'              # Facturado
    PAID = 'paid'                      # Pagado
    CANCELLED = 'cancelled'            # Cancelado
    COMPLETED = 'completed'            # Cerrado/Completado

    CHOICES = [
        (DRAFT, 'Draft'),
        (QUOTATION_SENT, 'Quotation Sent'),
        (CONFIRMED, 'Confirmed'),
        (IN_PROCESS, 'In Process'),
        (READY_TO_DELIVER, 'Ready to Deliver'),
        (PARTIALLY_DELIVERED, 'Partially Delivered'),
        (DELIVERED, 'Delivered'),
        (INVOICED, 'Invoiced'),
        (PAID, 'Paid'),
        (CANCELLED, 'Cancelled'),
        (COMPLETED, 'Completed'),
    ]

    # Transiciones válidas de estado
    VALID_TRANSITIONS = {
        DRAFT: [QUOTATION_SENT, CONFIRMED, CANCELLED],
        QUOTATION_SENT: [CONFIRMED, DRAFT, CANCELLED],
        CONFIRMED: [IN_PROCESS, CANCELLED],
        IN_PROCESS: [READY_TO_DELIVER, CANCELLED],
        READY_TO_DELIVER: [PARTIALLY_DELIVERED, DELIVERED, CANCELLED],
        PARTIALLY_DELIVERED: [DELIVERED, CANCELLED],
        DELIVERED: [INVOICED, CANCELLED],
        INVOICED: [PAID, CANCELLED],
        PAID: [COMPLETED],
        CANCELLED: [],  # Estado final
        COMPLETED: [],  # Estado final
    }

class SalesOrderLineStates:
    """Estados de las líneas de pedido"""
    DRAFT = 'draft'
    CONFIRMED = 'confirmed'
    IN_PROCESS = 'in_process'
    PARTIALLY_DELIVERED = 'partially_delivered'
    DELIVERED = 'delivered'
    CANCELLED = 'cancelled'

    CHOICES = [
        (DRAFT, 'Draft'),
        (CONFIRMED, 'Confirmed'),
        (IN_PROCESS, 'In Process'),
        (PARTIALLY_DELIVERED, 'Partially Delivered'),
        (DELIVERED, 'Delivered'),
        (CANCELLED, 'Cancelled'),
    ]

# --- VALIDADORES Y UTILIDADES ---
class VATValidator:
    """Validador de números de identificación fiscal (Tax ID) por país"""
    
    @staticmethod
    def validate_argentina_cuit(cuit):
        """Validar CUIT argentino"""
        if not cuit or len(cuit) != 11:
            return False
        
        # Implementar algoritmo de validación de CUIT
        # Por ahora, validación básica
        return cuit.isdigit()
    
    @staticmethod
    def validate_brazil_cnpj(cnpj):
        """Validar CNPJ brasileño"""
        if not cnpj or len(cnpj) != 14:
            return False
        
        # Implementar algoritmo de validación de CNPJ
        return cnpj.isdigit()
    
    @staticmethod
    def validate_mexico_rfc(rfc):
        """Validar RFC mexicano"""
        if not rfc or len(rfc) < 10:
            return False
        
        # Implementar validación de RFC
        return True
    
    @staticmethod
    def validate_spain_nif(nif):
        """Validar NIF español"""
        if not nif or len(nif) != 9:
            return False
        
        # Implementar validación de NIF
        return True
    
    @staticmethod
    def validate_usa_ein(ein):
        """Validar EIN estadounidense"""
        if not ein or len(ein) != 9:
            return False
        
        # Implementar validación de EIN
        return ein.isdigit()
    
    @staticmethod
    def validate_tax_id(tax_id, country_code):
        """Validar Tax ID según el país"""
        if not tax_id or not country_code:
            return False
        
        country_code = country_code.upper()
        
        if country_code == 'AR':
            return VATValidator.validate_argentina_cuit(tax_id)
        elif country_code == 'BR':
            return VATValidator.validate_brazil_cnpj(tax_id)
        elif country_code == 'MX':
            return VATValidator.validate_mexico_rfc(tax_id)
        elif country_code == 'ES':
            return VATValidator.validate_spain_nif(tax_id)
        elif country_code == 'US':
            return VATValidator.validate_usa_ein(tax_id)
        
        # Para otros países, validación básica
        return len(tax_id) >= 5

# --- CLIENTES Y CONTACTOS ACTUALIZADOS ---
class Client(BusinessEntity):
    """
    Cliente específico con funcionalidad de ventas
    Hereda de BusinessEntity para funcionalidad común
    """
    
    # Tipo de cliente
    type = models.CharField(
        max_length=16,
        choices=[
            ('individual', _('Individual')),
            ('company', _('Company')),
        ],
        default='individual',
        verbose_name=_('Client Type')
    )
    
    # Número de documento de identidad (DNI, CUIT, etc.)
    document_number = models.CharField(_("Document Number"), max_length=50, blank=True, help_text=_("DNI, CUIT, or other identification document"))
    
    # Alias para compatibilidad con código existente (VAT = Tax ID)
    @property
    def vat(self):
        """Alias para tax_id - mantener compatibilidad"""
        return self.tax_id
    
    @vat.setter
    def vat(self, value):
        """Setter para vat - mantener compatibilidad"""
        self.tax_id = value
    
    # Información específica de cliente
    credit_limit = models.DecimalField(_("Credit Limit"), max_digits=15, decimal_places=2, null=True, blank=True)
    payment_terms = models.CharField(_("Payment Terms"), max_length=100, blank=True, null=True)
    customer_category = models.CharField(_("Category"), max_length=50, blank=True, null=True)
    
    # Información fiscal específica
    fiscal_conditions = models.CharField(_("Fiscal Conditions"), max_length=100, blank=True, null=True)
    
    # Configuración de ventas
    default_price_list = models.ForeignKey('PriceList', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Default Price List"))
    sales_person = models.ForeignKey('core.UsuarioExtendido', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Sales Person"))
    
    # Configuración de entrega
    default_delivery_location = models.ForeignKey('core.DeliveryLocation', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Default Delivery Location"))
    
    # Configuración de facturación
    invoice_delivery_method = models.CharField(
        _("Invoice Delivery Method"),
        max_length=20,
        choices=[
            ('email', _('Email')),
            ('postal', _('Postal Mail')),
            ('digital', _('Digital Portal')),
        ],
        default='email'
    )
    
    # Configuración de pagos
    payment_method = models.CharField(
        _("Payment Method"),
        max_length=20,
        choices=[
            ('bank_transfer', _('Bank Transfer')),
            ('check', _('Check')),
            ('cash', _('Cash')),
            ('credit_card', _('Credit Card')),
            ('other', _('Other')),
        ],
        default='bank_transfer'
    )
    
    # Configuración de descuentos
    default_discount = models.DecimalField(_("Default Discount"), max_digits=5, decimal_places=2, null=True, blank=True, help_text=_("Default discount percentage"))
    
    # Estado específico de cliente
    is_customer = models.BooleanField(default=True, verbose_name=_('Is Customer'))
    is_prospect = models.BooleanField(default=False, verbose_name=_('Is Prospect'))
    is_vip = models.BooleanField(default=False, verbose_name=_('VIP Customer'))
    
    class Meta:
        verbose_name = _('Client')
        verbose_name_plural = _('Clients')
        ordering = ['name']
        indexes = [
            models.Index(fields=['customer_category']),
            models.Index(fields=['is_customer']),
            models.Index(fields=['is_vip']),
            models.Index(fields=['sales_person']),
        ]
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    def clean(self):
        """Validaciones específicas del cliente"""
        from django.core.exceptions import ValidationError
        
        # Validar límite de crédito
        if self.credit_limit and self.credit_limit < 0:
            raise ValidationError(_('Credit limit cannot be negative.'))
        
        # Validar descuento por defecto
        if self.default_discount:
            if self.default_discount < 0 or self.default_discount > 100:
                raise ValidationError(_('Default discount must be between 0 and 100.'))
        
        # Validar Tax ID según el país (si se implementa)
        if self.tax_id and self.country:
            # Aquí se podría agregar validación específica por país
            pass
    
    @property
    def total_orders(self):
        """Retorna el total de órdenes del cliente"""
        return self.orders.count()
    
    @property
    def total_sales(self):
        """Retorna el total de ventas del cliente"""
        return self.orders.filter(state='completed').aggregate(
            total=models.Sum('total')
        )['total'] or 0
    
    @property
    def outstanding_balance(self):
        """Retorna el saldo pendiente del cliente"""
        return self.invoices.filter(state='open').aggregate(
            total=models.Sum('total')
        )['total'] or 0
    
    @property
    def credit_available(self):
        """Retorna el crédito disponible"""
        if not self.credit_limit:
            return 0
        return self.credit_limit - self.outstanding_balance
    
    def can_place_order(self, amount):
        """Verifica si el cliente puede realizar una orden por el monto especificado"""
        if not self.credit_limit:
            return True
        return self.credit_available >= amount
    
    def get_sales_history(self, days=30):
        """Retorna el historial de ventas de los últimos días"""
        from django.utils import timezone
        from datetime import timedelta
        
        start_date = timezone.now() - timedelta(days=days)
        return self.orders.filter(
            created_at__gte=start_date,
            state='completed'
        ).order_by('-created_at')
    
    def get_primary_contact_info(self):
        """
        Obtiene la información del contacto principal (compatibilidad)
        """
        primary_contact = self.get_primary_contact()
        if primary_contact:
            return {
                'name': primary_contact.full_name,
                'email': primary_contact.email,
                'phone': primary_contact.phone,
                'position': primary_contact.position,
            }
        return None

# El modelo Contact se eliminó - ahora usamos el sistema universal de contactos en core.models

# --- LISTAS DE PRECIOS ---
class PriceList(models.Model):
    name = models.CharField(max_length=128)
    currency = models.CharField(max_length=8)
    valid_from = models.DateField(blank=True, null=True)
    valid_to = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class PriceListItem(models.Model):
    price_list = models.ForeignKey(PriceList, on_delete=models.CASCADE, related_name='items')
    product_variant = models.ForeignKey('inventory.ProductVariant', on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    min_qty = models.DecimalField(max_digits=12, decimal_places=2, default=1)
    max_qty = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    discount = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    promo_code = models.CharField(max_length=32, blank=True, null=True)
    rule_type = models.CharField(max_length=32, blank=True, null=True)
    valid_from = models.DateField(blank=True, null=True)
    valid_to = models.DateField(blank=True, null=True)

# --- CONDICIONES DE PAGO ---
class PaymentTerm(models.Model):
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class PaymentTermLine(models.Model):
    payment_term = models.ForeignKey(PaymentTerm, on_delete=models.CASCADE, related_name='lines')
    percent = models.DecimalField(max_digits=5, decimal_places=2)
    days = models.IntegerField()
    sequence = models.IntegerField(default=1)

# --- SALES ORDER Y LÍNEAS ---
class SalesOrder(models.Model):
    number = models.CharField(max_length=32, unique=True)
    state = models.CharField(
        max_length=32, 
        choices=SalesOrderStates.CHOICES,
        default=SalesOrderStates.DRAFT
    )
    order_date = models.DateField()
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=8)
    origin = models.CharField(max_length=32, blank=True, null=True)
    external_id = models.CharField(max_length=64, blank=True, null=True)
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name='orders')
    branch = models.ForeignKey('core.Branch', on_delete=models.PROTECT)
    payment_term = models.ForeignKey(PaymentTerm, on_delete=models.PROTECT)
    price_list = models.ForeignKey(PriceList, on_delete=models.PROTECT)
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    manual_credit_override = models.BooleanField(default=False)
    credit_override_reason = models.TextField(blank=True, null=True)
    
    # Campos de auditoría
    created_at = models.DateTimeField(default=dj_timezone.now, verbose_name=_('Created at'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated at'))
    confirmed_at = models.DateTimeField(blank=True, null=True)
    delivered_at = models.DateTimeField(blank=True, null=True)
    invoiced_at = models.DateTimeField(blank=True, null=True)
    paid_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-order_date', '-created_at']
        verbose_name = 'Sales Order'
        verbose_name_plural = 'Sales Orders'

    def __str__(self):
        return self.number

    def clean(self):
        """Validaciones del modelo"""
        super().clean()
        
        # Validar que el cliente esté activo
        if self.client and not self.client.is_active:
            raise ValidationError('Cannot assign inactive client to sales order')
        
        # Validar límite de crédito si no hay override manual
        if not self.manual_credit_override and self.client:
            if self.total > self.client.credit_limit:
                raise ValidationError(
                    f'Order total ({self.total}) exceeds client credit limit ({self.client.credit_limit})'
                )

    def save(self, *args, **kwargs):
        """Override save para generar número automáticamente"""
        if not self.number:
            self.number = self.generate_order_number()
        super().save(*args, **kwargs)

    def generate_order_number(self):
        """Generar número único de pedido"""
        from django.db.models import Max
        last_order = SalesOrder.objects.aggregate(
            max_number=Max('number')
        )['max_number']
        
        if last_order:
            try:
                number = int(last_order.split('-')[-1]) + 1
            except (ValueError, IndexError):
                number = 1
        else:
            number = 1
        
        return f"SO-{dj_timezone.now().strftime('%Y%m')}-{number:04d}"

    # --- MÉTODOS DE NEGOCIO ---
    
    def can_transition_to(self, new_state):
        """Verificar si la transición de estado es válida"""
        return new_state in SalesOrderStates.VALID_TRANSITIONS.get(self.state, [])

    def transition_to(self, new_state, user, reason=None):
        """Transición de estado con validación y logging"""
        if not self.can_transition_to(new_state):
            raise ValidationError(
                f'Invalid state transition from {self.state} to {new_state}'
            )
        
        if not reason:
            raise ValidationError('Reason is required for state transitions')
        
        old_state = self.state
        
        # Establecer contexto del usuario para las señales
        self._current_user = user
        
        self.state = new_state
        
        # Actualizar timestamps según el estado
        if new_state == SalesOrderStates.CONFIRMED:
            self.confirmed_at = dj_timezone.now()
        elif new_state == SalesOrderStates.DELIVERED:
            self.delivered_at = dj_timezone.now()
        elif new_state == SalesOrderStates.INVOICED:
            self.invoiced_at = dj_timezone.now()
        elif new_state == SalesOrderStates.PAID:
            self.paid_at = dj_timezone.now()
        elif new_state == SalesOrderStates.COMPLETED:
            self.completed_at = dj_timezone.now()
        
        self.save()
        
        # Limpiar contexto del usuario
        if hasattr(self, '_current_user'):
            delattr(self, '_current_user')
        
        # Crear log de transición
        ApprovalLog.objects.create(
            sales_order=self,
            user=user,
            action='state_change',
            reason=reason
        )

    def send_quotation(self, user, reason):
        """Enviar cotización al cliente"""
        self.transition_to(SalesOrderStates.QUOTATION_SENT, user, reason)

    def confirm_order(self, user, reason):
        """Confirmar pedido por el cliente"""
        self.transition_to(SalesOrderStates.CONFIRMED, user, reason)

    def start_processing(self, user, reason):
        """Iniciar procesamiento del pedido"""
        self.transition_to(SalesOrderStates.IN_PROCESS, user, reason)

    def mark_ready_to_deliver(self, user, reason):
        """Marcar como listo para entregar"""
        self.transition_to(SalesOrderStates.READY_TO_DELIVER, user, reason)

    def mark_partially_delivered(self, user, reason):
        """Marcar como parcialmente entregado"""
        self.transition_to(SalesOrderStates.PARTIALLY_DELIVERED, user, reason)

    def mark_delivered(self, user, reason):
        """Marcar como completamente entregado"""
        self.transition_to(SalesOrderStates.DELIVERED, user, reason)

    def mark_invoiced(self, user, reason):
        """Marcar como facturado"""
        self.transition_to(SalesOrderStates.INVOICED, user, reason)

    def mark_paid(self, user, reason):
        """Marcar como pagado"""
        self.transition_to(SalesOrderStates.PAID, user, reason)

    def mark_completed(self, user, reason):
        """Marcar como completado"""
        self.transition_to(SalesOrderStates.COMPLETED, user, reason)

    def cancel_order(self, user, reason):
        """Cancelar pedido"""
        self.transition_to(SalesOrderStates.CANCELLED, user, reason)

    # --- MÉTODOS DE CÁLCULO ---

    def recalculate_totals(self):
        """Recalcular totales del pedido"""
        total = Decimal('0.00')
        total_discount = Decimal('0.00')
        total_tax = Decimal('0.00')
        
        for line in self.lines.all():
            line_total = line.quantity * line.unit_price
            line_discount = line_total * (line.discount / Decimal('100'))
            line_subtotal = line_total - line_discount
            
            total += line_total
            total_discount += line_discount
            # TODO: Calcular impuestos según configuración fiscal
        
        self.total = total
        self.total_discount = total_discount
        self.total_tax = total_tax
        self.save(update_fields=['total', 'total_discount', 'total_tax'])

    def get_subtotal(self):
        """Obtener subtotal (sin descuentos ni impuestos)"""
        return sum(line.quantity * line.unit_price for line in self.lines.all())

    def get_total_with_tax(self):
        """Obtener total con impuestos"""
        return self.total - self.total_discount + self.total_tax

    def get_remaining_amount(self):
        """Obtener monto pendiente de pago"""
        if self.state in [SalesOrderStates.PAID, SalesOrderStates.COMPLETED]:
            return Decimal('0.00')
        return self.get_total_with_tax()

    # --- MÉTODOS DE VALIDACIÓN ---

    def can_be_edited(self):
        """Verificar si el pedido puede ser editado"""
        return self.state in [
            SalesOrderStates.DRAFT,
            SalesOrderStates.QUOTATION_SENT
        ]

    def can_be_cancelled(self):
        """Verificar si el pedido puede ser cancelado"""
        return self.state not in [
            SalesOrderStates.CANCELLED,
            SalesOrderStates.COMPLETED
        ]

    def can_create_invoice(self):
        """Verificar si se puede crear factura"""
        return self.state in [
            SalesOrderStates.DELIVERED,
            SalesOrderStates.INVOICED
        ]

    def can_create_delivery(self):
        """Verificar si se puede crear orden de entrega"""
        return self.state in [
            SalesOrderStates.CONFIRMED,
            SalesOrderStates.IN_PROCESS,
            SalesOrderStates.READY_TO_DELIVER
        ]

    # --- MÉTODOS DE INFORMACIÓN ---

    def get_status_display_name(self):
        """Obtener nombre legible del estado"""
        return dict(SalesOrderStates.CHOICES).get(self.state, self.state)

    def get_delivery_progress(self):
        """Obtener progreso de entrega"""
        if not self.lines.exists():
            return 0
        
        delivered_lines = self.lines.filter(state=SalesOrderLineStates.DELIVERED)
        return (delivered_lines.count() / self.lines.count()) * 100

    def get_payment_progress(self):
        """Obtener progreso de pago"""
        if self.state in [SalesOrderStates.PAID, SalesOrderStates.COMPLETED]:
            return 100
        elif self.state == SalesOrderStates.INVOICED:
            return 75
        elif self.state == SalesOrderStates.DELIVERED:
            return 50
        elif self.state in [SalesOrderStates.CONFIRMED, SalesOrderStates.IN_PROCESS]:
            return 25
        else:
            return 0

class SalesOrderLine(models.Model):
    sales_order = models.ForeignKey(SalesOrder, on_delete=models.CASCADE, related_name='lines')
    product_variant = models.ForeignKey('inventory.ProductVariant', on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    discount = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=255, blank=True, null=True)
    state = models.CharField(
        max_length=32,
        choices=SalesOrderLineStates.CHOICES,
        default=SalesOrderLineStates.DRAFT
    )
    
    # Campos de impuestos (mantener compatibilidad)
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Nuevos campos de impuestos
    taxes = models.ManyToManyField('accounting.Tax', blank=True, related_name='sales_order_lines', verbose_name=_('Taxes'))
    tax_lines = models.ManyToManyField('accounting.TaxLine', blank=True, related_name='sales_order_lines', verbose_name=_('Tax Lines'))
    fiscal_position = models.ForeignKey('accounting.FiscalPosition', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('Fiscal Position'))
    
    # Campos de auditoría
    created_at = models.DateTimeField(default=dj_timezone.now, verbose_name=_('Created at'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated at'))

    class Meta:
        ordering = ['id']
        verbose_name = 'Sales Order Line'
        verbose_name_plural = 'Sales Order Lines'

    def __str__(self):
        return f"{self.sales_order.number} - {self.product_variant}"

    def clean(self):
        """Validaciones del modelo"""
        super().clean()
        
        if self.quantity <= 0:
            raise ValidationError('Quantity must be greater than 0')
        
        if self.unit_price <= 0:
            raise ValidationError('Unit price must be greater than 0')
        
        if self.discount < 0 or self.discount > 100:
            raise ValidationError('Discount must be between 0 and 100')

    def save(self, *args, **kwargs):
        """Override save para recalcular subtotal"""
        self.recalculate_subtotal()
        super().save(*args, **kwargs)

    def recalculate_subtotal(self):
        """Recalcular subtotal de la línea"""
        total = self.quantity * self.unit_price
        discount_amount = total * (self.discount / Decimal('100'))
        self.subtotal = total - discount_amount

    def get_total_with_tax(self):
        """Obtener total con impuestos"""
        # TODO: Implementar cálculo de impuestos
        return self.subtotal

    def can_be_edited(self):
        """Verificar si la línea puede ser editada"""
        return self.sales_order.can_be_edited()

    def can_be_cancelled(self):
        """Verificar si la línea puede ser cancelada"""
        return self.state != SalesOrderLineStates.CANCELLED

    def mark_as_delivered(self, delivered_quantity=None):
        """Marcar línea como entregada"""
        if delivered_quantity is None:
            delivered_quantity = self.quantity
        
        if delivered_quantity > self.quantity:
            raise ValidationError('Delivered quantity cannot exceed order quantity')
        
        if delivered_quantity == self.quantity:
            self.state = SalesOrderLineStates.DELIVERED
        elif delivered_quantity > 0:
            self.state = SalesOrderLineStates.PARTIALLY_DELIVERED
        else:
            self.state = SalesOrderLineStates.CANCELLED
        
        self.save()

# --- INVOICES Y LÍNEAS ---
class Invoice(models.Model):
    number = models.CharField(max_length=32, unique=True)
    state = models.CharField(max_length=32)
    invoice_date = models.DateField()
    total = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=8)
    client = models.ForeignKey(Client, on_delete=models.PROTECT)
    sales_order = models.ForeignKey(SalesOrder, on_delete=models.PROTECT)
    payment_term = models.ForeignKey(PaymentTerm, on_delete=models.PROTECT)
    branch = models.ForeignKey('core.Branch', on_delete=models.PROTECT)
    origin = models.CharField(max_length=32, blank=True, null=True)
    external_id = models.CharField(max_length=64, blank=True, null=True)
    invoice_type = models.CharField(max_length=16)

    def __str__(self):
        return self.number

class InvoiceLine(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='lines')
    product_variant = models.ForeignKey('inventory.ProductVariant', on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    discount = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=255, blank=True, null=True)

# --- PAGOS ---
class Payment(models.Model):
    number = models.CharField(max_length=32, unique=True)
    state = models.CharField(max_length=32)
    payment_date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=8)
    client = models.ForeignKey(Client, on_delete=models.PROTECT)
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, blank=True, null=True)
    sales_order = models.ForeignKey(SalesOrder, on_delete=models.PROTECT, blank=True, null=True)
    payment_method = models.CharField(max_length=32)
    external_id = models.CharField(max_length=64, blank=True, null=True)
    origin = models.CharField(max_length=32, blank=True, null=True)

# --- DELIVERY ORDERS ---
class DeliveryOrder(models.Model):
    number = models.CharField(max_length=32, unique=True)
    state = models.CharField(max_length=32)
    delivery_date = models.DateField()
    sales_order = models.ForeignKey(SalesOrder, on_delete=models.PROTECT)
    branch = models.ForeignKey('core.Branch', on_delete=models.PROTECT)
    warehouse = models.ForeignKey('inventory.Warehouse', on_delete=models.PROTECT)
    origin = models.CharField(max_length=32, blank=True, null=True)
    external_id = models.CharField(max_length=64, blank=True, null=True)

class DeliveryOrderLine(models.Model):
    delivery_order = models.ForeignKey(DeliveryOrder, on_delete=models.CASCADE, related_name='lines')
    product_variant = models.ForeignKey('inventory.ProductVariant', on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    state = models.CharField(max_length=32)

# --- CREDIT NOTES ---
class CreditNote(models.Model):
    number = models.CharField(max_length=32, unique=True)
    state = models.CharField(max_length=32)
    credit_date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=8)
    client = models.ForeignKey(Client, on_delete=models.PROTECT)
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT)
    sales_order = models.ForeignKey(SalesOrder, on_delete=models.PROTECT)
    reason = models.CharField(max_length=255, blank=True, null=True)
    origin = models.CharField(max_length=32, blank=True, null=True)
    external_id = models.CharField(max_length=64, blank=True, null=True)

# --- APROBACIONES ---
class ApprovalLog(models.Model):
    sales_order = models.ForeignKey(SalesOrder, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    action = models.CharField(max_length=32)
    reason = models.TextField(blank=True, null=True)
    action_date = models.DateTimeField(auto_now_add=True)

# --- DEVOLUCIONES ---
class ReturnDelivery(models.Model):
    number = models.CharField(max_length=32, unique=True)
    state = models.CharField(max_length=32)
    return_date = models.DateField()
    sales_order = models.ForeignKey(SalesOrder, on_delete=models.PROTECT)
    delivery_order = models.ForeignKey(DeliveryOrder, on_delete=models.PROTECT)
    warehouse = models.ForeignKey('inventory.Warehouse', on_delete=models.PROTECT)
    return_type = models.CharField(max_length=32)
    reason = models.CharField(max_length=255, blank=True, null=True)
    origin = models.CharField(max_length=32, blank=True, null=True)
    external_id = models.CharField(max_length=64, blank=True, null=True)
