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
from core.models import BusinessEntity, Country, State, Empresa, UsuarioExtendido

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
    
    # Campo interno para integración administraNET
    id_administraNET = models.IntegerField(
        null=True, blank=True, db_index=True, unique=True, editable=False,
        help_text='ID original de administraNET para sincronización'
    )
    
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
    
    # Responsabilidad fiscal
    fiscal_responsibility = models.ForeignKey(
        'core.FiscalResponsibility',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('Responsabilidad Fiscal'),
        help_text=_('Tipo de responsabilidad fiscal del cliente')
    )
    
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
    
    country = models.CharField(_('Country'), max_length=100, blank=True, null=True)
    state = models.CharField(_('State/Province'), max_length=100, blank=True, null=True)
    
    country_temp = models.ForeignKey(Country, on_delete=models.SET_NULL, null=True, blank=True, related_name='+', verbose_name=_('Country (temp)'))
    state_temp = models.ForeignKey(State, on_delete=models.SET_NULL, null=True, blank=True, related_name='+', verbose_name=_('State/Province (temp)'))
    
    tags = models.ManyToManyField('ClientTag', blank=True, related_name='clients', verbose_name=_('Tags'))
    
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
    
    def save(self, *args, **kwargs):
        # Auto-generar código si no existe
        if not self.code:
            self.code = self.generate_client_code()
        super().save(*args, **kwargs)
    
    def generate_client_code(self):
        """Genera un código único para el cliente siguiendo el formato CLI-XXXXX, incremental global"""
        from django.db.models import Max
        last_code = Client.objects.filter(code__startswith='CLI-').aggregate(
            max_code=Max('code')
        )['max_code']
        if last_code:
            try:
                last_number = int(last_code.split('-')[-1])
                new_number = last_number + 1
            except (ValueError, IndexError):
                new_number = 1
        else:
            new_number = 1
        return f'CLI-{new_number}'
    
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
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='payment_terms')
    code = models.CharField(max_length=32)
    name = models.CharField(max_length=128)
    type = models.CharField(max_length=16, choices=[('standard', 'Estándar'), ('installment', 'Cuotas'), ('custom', 'Personalizada')], default='standard')
    payment_days = models.IntegerField(default=0, help_text="Días totales de vencimiento")
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(UsuarioExtendido, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    updated_by = models.ForeignKey(UsuarioExtendido, on_delete=models.SET_NULL, null=True, blank=True, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('empresa', 'code')
        ordering = ['empresa', 'name']

    def __str__(self):
        return f"{self.code} - {self.name}"

class PaymentTermLine(models.Model):
    payment_term = models.ForeignKey(PaymentTerm, on_delete=models.CASCADE, related_name='lines')
    sequence = models.IntegerField(default=1)
    days = models.IntegerField()
    percent = models.DecimalField(max_digits=5, decimal_places=2)
    description = models.CharField(max_length=128, blank=True, null=True)

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

# --- MODELOS PARA PUNTO DE VENTA (TPV) ---

class POSSession(models.Model):
    """
    Sesión de punto de venta - control de caja y operador
    """
    POS_SESSION_STATES = [
        ('open', _('Open')),
        ('closed', _('Closed')),
        ('suspended', _('Suspended')),
    ]
    
    number = models.CharField(_("Session Number"), max_length=32, unique=True)
    state = models.CharField(_("State"), max_length=16, choices=POS_SESSION_STATES, default='open')
    
    # Operador y ubicación
    operator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, verbose_name=_("Operator"))
    branch = models.ForeignKey('core.Branch', on_delete=models.PROTECT, verbose_name=_("Branch"))
    pos_terminal = models.ForeignKey('POSTerminal', on_delete=models.PROTECT, verbose_name=_("POS Terminal"))
    
    # Control de caja
    opening_amount = models.DecimalField(_("Opening Amount"), max_digits=12, decimal_places=2, default=0)
    closing_amount = models.DecimalField(_("Closing Amount"), max_digits=12, decimal_places=2, null=True, blank=True)
    expected_amount = models.DecimalField(_("Expected Amount"), max_digits=12, decimal_places=2, null=True, blank=True)
    difference_amount = models.DecimalField(_("Difference Amount"), max_digits=12, decimal_places=2, null=True, blank=True)
    
    # Fechas
    opened_at = models.DateTimeField(_("Opened At"), auto_now_add=True)
    closed_at = models.DateTimeField(_("Closed At"), null=True, blank=True)
    
    # Auditoría
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('POS Session')
        verbose_name_plural = _('POS Sessions')
        ordering = ['-opened_at']
    
    def __str__(self):
        return f"Session {self.number} - {self.operator} - {self.state}"
    
    def close_session(self, closing_amount, user):
        """Cerrar sesión de TPV"""
        self.state = 'closed'
        self.closing_amount = closing_amount
        self.closed_at = dj_timezone.now()
        self.expected_amount = self.calculate_expected_amount()
        self.difference_amount = closing_amount - self.expected_amount
        self.save()
        
        # Crear registro de auditoría
        POSSessionLog.objects.create(
            session=self,
            user=user,
            action='close',
            amount=closing_amount,
            notes=f"Session closed. Expected: {self.expected_amount}, Actual: {closing_amount}"
        )
    
    def calculate_expected_amount(self):
        """Calcular monto esperado basado en transacciones"""
        total_sales = self.sales.filter(state='completed').aggregate(
            total=models.Sum('total_paid')
        )['total'] or 0
        
        total_refunds = self.sales.filter(state='refunded').aggregate(
            total=models.Sum('total_paid')
        )['total'] or 0
        
        return self.opening_amount + total_sales - total_refunds

class POSTerminal(models.Model):
    """
    Terminal de punto de venta
    """
    name = models.CharField(_("Terminal Name"), max_length=100)
    code = models.CharField(_("Terminal Code"), max_length=20, unique=True)
    branch = models.ForeignKey('core.Branch', on_delete=models.PROTECT, verbose_name=_("Branch"))
    
    # Configuración fiscal
    fiscal_printer = models.CharField(_("Fiscal Printer"), max_length=100, blank=True, null=True)
    fiscal_number = models.CharField(_("Fiscal Number"), max_length=20, blank=True, null=True)
    electronic_invoice = models.BooleanField(_("Electronic Invoice"), default=False)
    
    # Configuración de impresión
    receipt_printer = models.CharField(_("Receipt Printer"), max_length=100, blank=True, null=True)
    ticket_width = models.IntegerField(_("Ticket Width"), default=80)
    
    # Configuración de búsqueda
    barcode_scanner = models.BooleanField(_("Barcode Scanner"), default=True)
    scale_integration = models.BooleanField(_("Scale Integration"), default=False)
    scale_port = models.CharField(_("Scale Port"), max_length=20, blank=True, null=True)
    
    # Estado
    is_active = models.BooleanField(_("Active"), default=True)
    
    # Auditoría
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('POS Terminal')
        verbose_name_plural = _('POS Terminals')
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.code})"

class POSSale(models.Model):
    """
    Venta de punto de venta
    """
    POSSALE_STATES = [
        ('draft', _('Draft')),
        ('confirmed', _('Confirmed')),
        ('completed', _('Completed')),
        ('cancelled', _('Cancelled')),
        ('refunded', _('Refunded')),
    ]
    
    number = models.CharField(_("Sale Number"), max_length=32, unique=True)
    state = models.CharField(_("State"), max_length=16, choices=POSSALE_STATES, default='draft')
    
    # Relaciones con empresa y sucursal (multiempresa/multisucursal)
    empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT, verbose_name=_("Company"), null=True, blank=True)
    branch = models.ForeignKey('core.Branch', on_delete=models.PROTECT, verbose_name=_("Branch"), null=True, blank=True)
    
    # Sesión y operador
    session = models.ForeignKey(POSSession, on_delete=models.PROTECT, related_name='sales', verbose_name=_("Session"))
    operator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, verbose_name=_("Operator"))
    
    # Cliente
    client = models.ForeignKey(Client, on_delete=models.PROTECT, null=True, blank=True, verbose_name=_("Client"))
    is_occasional_client = models.BooleanField(_("Occasional Client"), default=False)
    occasional_client_data = models.JSONField(_("Occasional Client Data"), null=True, blank=True)
    
    # Totales
    subtotal = models.DecimalField(_("Subtotal"), max_digits=12, decimal_places=2, default=0)
    total_discount = models.DecimalField(_("Total Discount"), max_digits=12, decimal_places=2, default=0)
    total_tax = models.DecimalField(_("Total Tax"), max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(_("Total"), max_digits=12, decimal_places=2, default=0)
    total_paid = models.DecimalField(_("Total Paid"), max_digits=12, decimal_places=2, default=0)
    
    # Configuración
    price_list = models.ForeignKey(PriceList, on_delete=models.PROTECT, verbose_name=_("Price List"))
    currency = models.CharField(_("Currency"), max_length=3, default='ARS')
    
    # Comprobante fiscal
    invoice_number = models.CharField(_("Invoice Number"), max_length=32, blank=True, null=True)
    invoice_type = models.CharField(_("Invoice Type"), max_length=10, blank=True, null=True)
    fiscal_data = models.JSONField(_("Fiscal Data"), null=True, blank=True)
    
    # Fechas
    sale_date = models.DateTimeField(_("Sale Date"), auto_now_add=True)
    completed_at = models.DateTimeField(_("Completed At"), null=True, blank=True)
    
    # Auditoría
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('POS Sale')
        verbose_name_plural = _('POS Sales')
        ordering = ['-sale_date']
        indexes = [
            models.Index(fields=['empresa', 'branch']),
            models.Index(fields=['session']),
            models.Index(fields=['state']),
        ]
    
    def __str__(self):
        return f"Sale {self.number} - {self.total}"
    
    def save(self, *args, **kwargs):
        if not self.number:
            self.number = self.generate_sale_number()
        
        # Auto-asignar empresa y branch desde la sesión si no están definidos
        if not self.empresa_id and self.session:
            self.empresa = self.session.branch.empresa
        if not self.branch_id and self.session:
            self.branch = self.session.branch
            
        super().save(*args, **kwargs)
    
    def generate_sale_number(self):
        """Generar número de venta único"""
        prefix = f"POS{self.session.branch.code}{self.session.pos_terminal.code}"
        last_sale = POSSale.objects.filter(
            session__branch=self.session.branch,
            session__pos_terminal=self.session.pos_terminal
        ).order_by('-number').first()
        
        if last_sale:
            last_number = int(last_sale.number.replace(prefix, ''))
            new_number = last_number + 1
        else:
            new_number = 1
        
        return f"{prefix}{new_number:06d}"
    
    def recalculate_totals(self):
        """Recalcular totales de la venta"""
        lines = self.lines.all()
        
        self.subtotal = sum(line.subtotal for line in lines)
        self.total_discount = sum(line.discount_amount for line in lines)
        self.total_tax = sum(line.tax_amount for line in lines)
        self.total = self.subtotal - self.total_discount + self.total_tax
        
        self.save()
    
    def complete_sale(self, payments_data):
        """Completar venta con pagos"""
        self.state = 'completed'
        self.completed_at = dj_timezone.now()
        
        # Crear pagos
        for payment_data in payments_data:
            POSPayment.objects.create(
                sale=self,
                payment_method=payment_data['method'],
                amount=payment_data['amount'],
                reference=payment_data.get('reference', ''),
                notes=payment_data.get('notes', '')
            )
        
        self.total_paid = sum(payment_data['amount'] for payment_data in payments_data)
        self.save()
        
        return self

class POSSaleLine(models.Model):
    """
    Línea de venta de punto de venta
    """
    sale = models.ForeignKey(POSSale, on_delete=models.CASCADE, related_name='lines', verbose_name=_("Sale"))
    product_variant = models.ForeignKey('inventory.ProductVariant', on_delete=models.PROTECT, verbose_name=_("Product"))
    
    # Relaciones con empresa y sucursal (multiempresa/multisucursal)
    empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT, verbose_name=_("Company"), null=True, blank=True)
    branch = models.ForeignKey('core.Branch', on_delete=models.PROTECT, verbose_name=_("Branch"), null=True, blank=True)
    
    # Cantidad y precio
    quantity = models.DecimalField(_("Quantity"), max_digits=12, decimal_places=3)
    unit_price = models.DecimalField(_("Unit Price"), max_digits=12, decimal_places=2)
    subtotal = models.DecimalField(_("Subtotal"), max_digits=12, decimal_places=2)
    
    # Descuentos
    discount_percentage = models.DecimalField(_("Discount Percentage"), max_digits=5, decimal_places=2, default=0)
    discount_amount = models.DecimalField(_("Discount Amount"), max_digits=12, decimal_places=2, default=0)
    
    # Impuestos
    tax_percentage = models.DecimalField(_("Tax Percentage"), max_digits=5, decimal_places=2, default=0)
    tax_amount = models.DecimalField(_("Tax Amount"), max_digits=12, decimal_places=2, default=0)
    
    # Información adicional
    description = models.CharField(_("Description"), max_length=255, blank=True, null=True)
    barcode = models.CharField(_("Barcode"), max_length=50, blank=True, null=True)
    lot_number = models.CharField(_("Lot Number"), max_length=50, blank=True, null=True)
    
    # Auditoría
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('POS Sale Line')
        verbose_name_plural = _('POS Sale Lines')
        ordering = ['id']
        indexes = [
            models.Index(fields=['empresa', 'branch']),
            models.Index(fields=['sale']),
        ]
    
    def __str__(self):
        return f"{self.product_variant} x {self.quantity}"
    
    def save(self, *args, **kwargs):
        # Auto-asignar empresa y branch desde la venta si no están definidos
        if not self.empresa_id and self.sale:
            self.empresa = self.sale.empresa
        if not self.branch_id and self.sale:
            self.branch = self.sale.branch
            
        self.calculate_totals()
        super().save(*args, **kwargs)
    
    def calculate_totals(self):
        """Calcular totales de la línea"""
        self.subtotal = self.quantity * self.unit_price
        self.discount_amount = self.subtotal * (self.discount_percentage / 100)
        self.tax_amount = (self.subtotal - self.discount_amount) * (self.tax_percentage / 100)

class POSPayment(models.Model):
    """
    Pago de punto de venta
    """
    PAYMENT_METHODS = [
        ('cash', _('Cash')),
        ('credit_card', _('Credit Card')),
        ('debit_card', _('Debit Card')),
        ('check', _('Check')),
        ('bank_transfer', _('Bank Transfer')),
        ('account_credit', _('Account Credit')),
        ('gift_card', _('Gift Card')),
        ('other', _('Other')),
    ]
    
    sale = models.ForeignKey(POSSale, on_delete=models.CASCADE, related_name='payments', verbose_name=_("Sale"))
    
    # Relaciones con empresa y sucursal (multiempresa/multisucursal)
    empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT, verbose_name=_("Company"), null=True, blank=True)
    branch = models.ForeignKey('core.Branch', on_delete=models.PROTECT, verbose_name=_("Branch"), null=True, blank=True)
    
    payment_method = models.CharField(_("Payment Method"), max_length=20, choices=PAYMENT_METHODS)
    amount = models.DecimalField(_("Amount"), max_digits=12, decimal_places=2)
    
    # Información adicional según método
    reference = models.CharField(_("Reference"), max_length=100, blank=True, null=True)
    card_type = models.CharField(_("Card Type"), max_length=50, blank=True, null=True)
    card_number = models.CharField(_("Card Number"), max_length=20, blank=True, null=True)
    installments = models.IntegerField(_("Installments"), default=1)
    check_number = models.CharField(_("Check Number"), max_length=50, blank=True, null=True)
    
    # Notas
    notes = models.TextField(_("Notes"), blank=True, null=True)
    
    # Auditoría
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('POS Payment')
        verbose_name_plural = _('POS Payments')
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['empresa', 'branch']),
            models.Index(fields=['sale']),
            models.Index(fields=['payment_method']),
        ]
    
    def __str__(self):
        return f"{self.get_payment_method_display()} - {self.amount}"
    
    def save(self, *args, **kwargs):
        # Auto-asignar empresa y branch desde la venta si no están definidos
        if not self.empresa_id and self.sale:
            self.empresa = self.sale.empresa
        if not self.branch_id and self.sale:
            self.branch = self.sale.branch
            
        super().save(*args, **kwargs)

class POSSessionLog(models.Model):
    """
    Log de sesiones de punto de venta
    """
    session = models.ForeignKey(POSSession, on_delete=models.CASCADE, related_name='logs', verbose_name=_("Session"))
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, verbose_name=_("User"))
    
    action = models.CharField(_("Action"), max_length=50)
    amount = models.DecimalField(_("Amount"), max_digits=12, decimal_places=2, null=True, blank=True)
    notes = models.TextField(_("Notes"), blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('POS Session Log')
        verbose_name_plural = _('POS Session Logs')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.session} - {self.action} - {self.user}"

class POSPromotion(models.Model):
    """
    Promociones para punto de venta
    """
    PROMOTION_TYPES = [
        ('discount_percentage', _('Discount Percentage')),
        ('discount_amount', _('Discount Amount')),
        ('buy_x_get_y', _('Buy X Get Y')),
        ('bundle', _('Bundle')),
        ('loyalty_points', _('Loyalty Points')),
    ]
    
    name = models.CharField(_("Name"), max_length=100)
    code = models.CharField(_("Code"), max_length=50, unique=True)
    promotion_type = models.CharField(_("Promotion Type"), max_length=20, choices=PROMOTION_TYPES)
    
    # Relaciones con empresa y sucursal (multiempresa/multisucursal)
    empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT, verbose_name=_("Company"), null=True, blank=True)
    branch = models.ForeignKey('core.Branch', on_delete=models.PROTECT, verbose_name=_("Branch"), null=True, blank=True)
    
    # Configuración
    is_active = models.BooleanField(_("Active"), default=True)
    valid_from = models.DateTimeField(_("Valid From"), null=True, blank=True)
    valid_to = models.DateTimeField(_("Valid To"), null=True, blank=True)
    
    # Condiciones
    minimum_amount = models.DecimalField(_("Minimum Amount"), max_digits=12, decimal_places=2, null=True, blank=True)
    maximum_discount = models.DecimalField(_("Maximum Discount"), max_digits=12, decimal_places=2, null=True, blank=True)
    
    # Productos aplicables
    applicable_products = models.ManyToManyField('inventory.ProductVariant', blank=True, verbose_name=_("Applicable Products"))
    applicable_categories = models.ManyToManyField('inventory.Category', blank=True, verbose_name=_("Applicable Categories"))
    
    # Configuración específica por tipo
    configuration = models.JSONField(_("Configuration"), default=dict)
    
    # Auditoría
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('POS Promotion')
        verbose_name_plural = _('POS Promotions')
        ordering = ['name']
        indexes = [
            models.Index(fields=['empresa', 'branch']),
            models.Index(fields=['is_active']),
            models.Index(fields=['code']),
        ]
    
    def __str__(self):
        return self.name
    
    def is_valid(self, sale_data):
        """Verificar si la promoción es válida para la venta"""
        now = dj_timezone.now()
        
        if not self.is_active:
            return False
        
        if self.valid_from and now < self.valid_from:
            return False
        
        if self.valid_to and now > self.valid_to:
            return False
        
        if self.minimum_amount and sale_data['subtotal'] < self.minimum_amount:
            return False
        
        return True
    
    def calculate_discount(self, sale_data):
        """Calcular descuento aplicable"""
        if not self.is_valid(sale_data):
            return 0
        
        if self.promotion_type == 'discount_percentage':
            discount = sale_data['subtotal'] * (self.configuration.get('percentage', 0) / 100)
        elif self.promotion_type == 'discount_amount':
            discount = self.configuration.get('amount', 0)
        else:
            discount = 0
        
        if self.maximum_discount:
            discount = min(discount, self.maximum_discount)
        
        return discount

# --- MEDIOS DE PAGO DINÁMICOS ---
class PaymentMethod(models.Model):
    """
    Modelo para administración dinámica de medios de pago
    Sigue mejores prácticas internacionales y soporta medios electrónicos modernos
    """
    
    # Tipos de medios de pago
    PAYMENT_TYPE_CHOICES = [
        ('cash', _('Cash')),
        ('card', _('Card')),
        ('bank_transfer', _('Bank Transfer')),
        ('digital_wallet', _('Digital Wallet')),
        ('check', _('Check')),
        ('crypto', _('Cryptocurrency')),
        ('buy_now_pay_later', _('Buy Now Pay Later')),
        ('other', _('Other')),
    ]
    
    # Categorías de tarjetas
    CARD_TYPE_CHOICES = [
        ('visa', 'Visa'),
        ('mastercard', 'Mastercard'),
        ('amex', 'American Express'),
        ('discover', 'Discover'),
        ('diners', 'Diners Club'),
        ('jcb', 'JCB'),
        ('unionpay', 'UnionPay'),
        ('other', _('Other')),
    ]
    
    # Estados de procesamiento
    PROCESSING_STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('processing', _('Processing')),
        ('completed', _('Completed')),
        ('failed', _('Failed')),
        ('cancelled', _('Cancelled')),
        ('refunded', _('Refunded')),
    ]
    
    # Información básica
    name = models.CharField(_("Name"), max_length=100, help_text=_("Display name for the payment method"))
    code = models.CharField(_("Code"), max_length=20, unique=True, help_text=_("Unique identifier for the payment method"))
    description = models.TextField(_("Description"), blank=True, help_text=_("Detailed description of the payment method"))
    
    # Categorización
    payment_type = models.CharField(_("Payment Type"), max_length=20, choices=PAYMENT_TYPE_CHOICES)
    card_type = models.CharField(_("Card Type"), max_length=20, choices=CARD_TYPE_CHOICES, blank=True, null=True)
    
    # Configuración visual
    icon = models.CharField(_("Icon"), max_length=50, default="credit_card", help_text=_("Material Design icon name"))
    color = models.CharField(_("Color"), max_length=7, default="#3B82F6", help_text=_("Hex color for UI display"))
    logo_url = models.URLField(_("Logo URL"), blank=True, help_text=_("URL to payment method logo"))
    
    # Configuración de negocio
    is_active = models.BooleanField(_("Active"), default=True)
    is_default = models.BooleanField(_("Default"), default=False, help_text=_("Default payment method for new transactions"))
    order = models.IntegerField(_("Display Order"), default=0, help_text=_("Order in which to display this payment method"))
    
    # Configuración de comisiones
    commission_percentage = models.DecimalField(_("Commission %"), max_digits=5, decimal_places=2, default=0, help_text=_("Commission percentage charged by the payment processor"))
    fixed_commission = models.DecimalField(_("Fixed Commission"), max_digits=10, decimal_places=2, default=0, help_text=_("Fixed commission amount"))
    minimum_amount = models.DecimalField(_("Minimum Amount"), max_digits=12, decimal_places=2, default=0, help_text=_("Minimum transaction amount"))
    maximum_amount = models.DecimalField(_("Maximum Amount"), max_digits=12, decimal_places=2, default=0, help_text=_("Maximum transaction amount (0 = no limit)"))
    
    # Configuración de campos requeridos
    requires_reference = models.BooleanField(_("Requires Reference"), default=False)
    requires_card_number = models.BooleanField(_("Requires Card Number"), default=False)
    requires_expiry = models.BooleanField(_("Requires Expiry Date"), default=False)
    requires_cvv = models.BooleanField(_("Requires CVV"), default=False)
    requires_installments = models.BooleanField(_("Supports Installments"), default=False)
    max_installments = models.IntegerField(_("Max Installments"), default=1)
    
    # Configuración de procesamiento
    processing_time_hours = models.IntegerField(_("Processing Time (Hours)"), default=0, help_text=_("Time to process payment in hours"))
    supports_refunds = models.BooleanField(_("Supports Refunds"), default=True)
    supports_partial_refunds = models.BooleanField(_("Supports Partial Refunds"), default=True)
    
    # Integración con procesadores
    processor_name = models.CharField(_("Processor Name"), max_length=50, blank=True, help_text=_("Payment processor name (e.g., Stripe, PayPal, MercadoPago)"))
    processor_config = models.JSONField(_("Processor Configuration"), default=dict, blank=True, help_text=_("Configuration for payment processor"))
    
    # Configuración de seguridad
    requires_3d_secure = models.BooleanField(_("Requires 3D Secure"), default=False)
    supports_tokenization = models.BooleanField(_("Supports Tokenization"), default=False)
    
    # Configuración regional
    supported_currencies = models.JSONField(_("Supported Currencies"), default=list, blank=True, help_text=_("List of supported currency codes"))
    supported_countries = models.JSONField(_("Supported Countries"), default=list, blank=True, help_text=_("List of supported country codes"))
    
    # Relaciones multiempresa/multisucursal
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, verbose_name=_("Company"))
    branches = models.ManyToManyField('core.Branch', blank=True, verbose_name=_("Branches"), help_text=_("Branches where this payment method is available"))
    
    # Auditoría
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(UsuarioExtendido, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_payment_methods')
    updated_by = models.ForeignKey(UsuarioExtendido, on_delete=models.SET_NULL, null=True, blank=True, related_name='updated_payment_methods')
    
    class Meta:
        verbose_name = _('Payment Method')
        verbose_name_plural = _('Payment Methods')
        ordering = ['order', 'name']
        indexes = [
            models.Index(fields=['empresa', 'is_active']),
            models.Index(fields=['payment_type']),
            models.Index(fields=['code']),
        ]
        unique_together = [['empresa', 'code']]
    
    def __str__(self):
        return f"{self.name} ({self.empresa.name})"
    
    def clean(self):
        """Validaciones del modelo"""
        from django.core.exceptions import ValidationError
        
        # Validar que solo un método sea default por empresa
        if self.is_default:
            PaymentMethod.objects.filter(
                empresa=self.empresa,
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        
        # Validar configuración de tarjetas
        if self.payment_type == 'card' and not self.card_type:
            raise ValidationError(_("Card type is required for card payment methods"))
        
        # Validar montos
        if self.minimum_amount > self.maximum_amount and self.maximum_amount > 0:
            raise ValidationError(_("Minimum amount cannot be greater than maximum amount"))
    
    def get_commission_amount(self, transaction_amount):
        """Calcular comisión para un monto dado"""
        commission = self.fixed_commission
        if self.commission_percentage > 0:
            commission += (transaction_amount * self.commission_percentage / 100)
        return commission
    
    def is_available_for_amount(self, amount):
        """Verificar si el método está disponible para un monto"""
        if amount < self.minimum_amount:
            return False
        if self.maximum_amount > 0 and amount > self.maximum_amount:
            return False
        return True
    
    def is_available_for_currency(self, currency_code):
        """Verificar si el método está disponible para una moneda"""
        if not self.supported_currencies:
            return True  # Si no hay restricciones, está disponible
        return currency_code.upper() in [c.upper() for c in self.supported_currencies]
    
    def is_available_for_country(self, country_code):
        """Verificar si el método está disponible para un país"""
        if not self.supported_countries:
            return True  # Si no hay restricciones, está disponible
        return country_code.upper() in [c.upper() for c in self.supported_countries]
    
    def get_required_fields(self):
        """Obtener campos requeridos para este método de pago"""
        fields = []
        if self.requires_reference:
            fields.append('reference')
        if self.requires_card_number:
            fields.append('card_number')
        if self.requires_expiry:
            fields.append('expiry_date')
        if self.requires_cvv:
            fields.append('cvv')
        if self.requires_installments:
            fields.append('installments')
        return fields
    
    def get_processor_config(self):
        """Obtener configuración del procesador"""
        return self.processor_config or {}
    
    def set_processor_config(self, config):
        """Establecer configuración del procesador"""
        self.processor_config = config
        self.save(update_fields=['processor_config'])


# --- CONFIGURACIÓN DE PROCESADORES DE PAGO ---
class PaymentProcessor(models.Model):
    """
    Configuración de procesadores de pago
    """
    
    PROCESSOR_TYPES = [
        ('stripe', 'Stripe'),
        ('paypal', 'PayPal'),
        ('mercadopago', 'MercadoPago'),
        ('modo', 'Modo'),
        ('clover', 'Clover'),
        ('square', 'Square'),
        ('adyen', 'Adyen'),
        ('braintree', 'Braintree'),
        ('custom', _('Custom')),
    ]
    
    name = models.CharField(_("Name"), max_length=100)
    processor_type = models.CharField(_("Processor Type"), max_length=20, choices=PROCESSOR_TYPES)
    is_active = models.BooleanField(_("Active"), default=True)
    
    # Configuración de API
    api_key = models.CharField(_("API Key"), max_length=255, blank=True)
    api_secret = models.CharField(_("API Secret"), max_length=255, blank=True)
    webhook_url = models.URLField(_("Webhook URL"), blank=True)
    webhook_secret = models.CharField(_("Webhook Secret"), max_length=255, blank=True)
    
    # Configuración adicional
    config = models.JSONField(_("Configuration"), default=dict, blank=True)
    
    # Relaciones
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, verbose_name=_("Company"))
    
    # Auditoría
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Payment Processor')
        verbose_name_plural = _('Payment Processors')
        ordering = ['name']
        unique_together = [['empresa', 'processor_type']]
    
    def __str__(self):
        return f"{self.name} ({self.empresa.name})"
    
    def get_config(self, key, default=None):
        """Obtener valor de configuración"""
        return self.config.get(key, default)
    
    def set_config(self, key, value):
        """Establecer valor de configuración"""
        self.config[key] = value
        self.save(update_fields=['config'])

class ClientAttachment(models.Model):
    """
    Adjuntos de cliente (documentos, archivos, imágenes, etc.)
    Permite asociar múltiples archivos a un cliente, con soporte multiempresa
    """
    empresa = models.ForeignKey('core.Empresa', on_delete=models.CASCADE, related_name='client_attachments', verbose_name=_('Company'))
    client = models.ForeignKey('Client', on_delete=models.CASCADE, related_name='attachments', verbose_name=_('Client'))
    file = models.FileField(_('File'), upload_to='clients/attachments/')
    file_name = models.CharField(_('File Name'), max_length=255)
    file_size = models.PositiveIntegerField(_('File Size (bytes)'), null=True, blank=True)
    description = models.TextField(_('Description'), blank=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name=_('Uploaded By'))
    uploaded_at = models.DateTimeField(_('Uploaded At'), auto_now_add=True)
    is_active = models.BooleanField(_('Active'), default=True)

    class Meta:
        verbose_name = _('Client Attachment')
        verbose_name_plural = _('Client Attachments')
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['empresa', 'client', 'is_active']),
        ]

    def __str__(self):
        return f"{self.client} - {self.file_name}"

    def save(self, *args, **kwargs):
        # Calcula automáticamente el tamaño del archivo
        if self.file and not self.file_size:
            try:
                self.file_size = self.file.size
            except Exception:
                pass
        super().save(*args, **kwargs)

    @property
    def file_size_mb(self):
        if self.file_size:
            return round(self.file_size / (1024 * 1024), 2)
        return 0

class ClientTag(models.Model):
    empresa = models.ForeignKey('core.Empresa', on_delete=models.CASCADE, related_name='client_tags', verbose_name=_('Company'))
    name = models.CharField(_('Tag Name'), max_length=64)
    color = models.CharField(_('Color'), max_length=16, blank=True, default='#f97316', help_text=_('Color for visual badge'))
    is_active = models.BooleanField(_('Active'), default=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        unique_together = ('empresa', 'name')
        verbose_name = _('Client Tag')
        verbose_name_plural = _('Client Tags')
        ordering = ['name']

    def __str__(self):
        return self.name

class ClientActivity(models.Model):
    """
    Actividad y historial de clientes
    Registra todas las acciones y eventos relacionados con un cliente
    """
    ACTIVITY_TYPES = [
        ('order_created', _('Order Created')),
        ('order_updated', _('Order Updated')),
        ('order_cancelled', _('Order Cancelled')),
        ('invoice_created', _('Invoice Created')),
        ('payment_received', _('Payment Received')),
        ('contact_added', _('Contact Added')),
        ('contact_updated', _('Contact Updated')),
        ('attachment_uploaded', _('Attachment Uploaded')),
        ('note_added', _('Note Added')),
        ('status_changed', _('Status Changed')),
        ('credit_limit_updated', _('Credit Limit Updated')),
        ('discount_updated', _('Discount Updated')),
        ('tag_added', _('Tag Added')),
        ('tag_removed', _('Tag Removed')),
        ('visit_scheduled', _('Visit Scheduled')),
        ('call_logged', _('Call Logged')),
        ('email_sent', _('Email Sent')),
        ('quote_sent', _('Quote Sent')),
        ('complaint_logged', _('Complaint Logged')),
        ('other', _('Other')),
    ]
    
    empresa = models.ForeignKey('core.Empresa', on_delete=models.CASCADE, related_name='client_activities', verbose_name=_('Company'))
    client = models.ForeignKey('Client', on_delete=models.CASCADE, related_name='activities', verbose_name=_('Client'))
    activity_type = models.CharField(_('Activity Type'), max_length=32, choices=ACTIVITY_TYPES)
    title = models.CharField(_('Title'), max_length=255)
    description = models.TextField(_('Description'), blank=True)
    
    # Datos relacionados (JSON para flexibilidad)
    related_data = models.JSONField(_('Related Data'), default=dict, blank=True)
    
    # Usuario que realizó la actividad
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name=_('User'))
    
    # Fecha y hora
    activity_date = models.DateTimeField(_('Activity Date'), auto_now_add=True)
    
    # Prioridad y estado
    priority = models.CharField(_('Priority'), max_length=16, choices=[
        ('low', _('Low')),
        ('medium', _('Medium')),
        ('high', _('High')),
        ('urgent', _('Urgent')),
    ], default='medium')
    
    is_private = models.BooleanField(_('Private'), default=False, help_text=_('Only visible to assigned user'))
    is_completed = models.BooleanField(_('Completed'), default=True)
    
    # Auditoría
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Client Activity')
        verbose_name_plural = _('Client Activities')
        ordering = ['-activity_date']
        indexes = [
            models.Index(fields=['empresa', 'client']),
            models.Index(fields=['activity_type']),
            models.Index(fields=['activity_date']),
            models.Index(fields=['user']),
        ]
    
    def __str__(self):
        return f"{self.client.name} - {self.get_activity_type_display()} - {self.title}"
    
    def get_activity_icon(self):
        """Retorna el ícono correspondiente al tipo de actividad"""
        icon_map = {
            'order_created': 'shopping_cart',
            'order_updated': 'edit',
            'order_cancelled': 'cancel',
            'invoice_created': 'receipt',
            'payment_received': 'payment',
            'contact_added': 'person_add',
            'contact_updated': 'person',
            'attachment_uploaded': 'attach_file',
            'note_added': 'note',
            'status_changed': 'update',
            'credit_limit_updated': 'credit_card',
            'discount_updated': 'local_offer',
            'tag_added': 'label',
            'tag_removed': 'label_off',
            'visit_scheduled': 'event',
            'call_logged': 'phone',
            'email_sent': 'email',
            'quote_sent': 'description',
            'complaint_logged': 'report_problem',
            'other': 'info',
        }
        return icon_map.get(self.activity_type, 'info')
    
    def get_activity_color(self):
        """Retorna el color correspondiente al tipo de actividad"""
        color_map = {
            'order_created': 'text-green-600',
            'order_updated': 'text-blue-600',
            'order_cancelled': 'text-red-600',
            'invoice_created': 'text-purple-600',
            'payment_received': 'text-green-600',
            'contact_added': 'text-blue-600',
            'contact_updated': 'text-blue-600',
            'attachment_uploaded': 'text-orange-600',
            'note_added': 'text-gray-600',
            'status_changed': 'text-yellow-600',
            'credit_limit_updated': 'text-indigo-600',
            'discount_updated': 'text-pink-600',
            'tag_added': 'text-green-600',
            'tag_removed': 'text-red-600',
            'visit_scheduled': 'text-blue-600',
            'call_logged': 'text-green-600',
            'email_sent': 'text-blue-600',
            'quote_sent': 'text-purple-600',
            'complaint_logged': 'text-red-600',
            'other': 'text-gray-600',
        }
        return color_map.get(self.activity_type, 'text-gray-600')
