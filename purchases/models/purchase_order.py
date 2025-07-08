from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from django.contrib.auth import get_user_model
from core.models import Empresa, Branch, Currency
from .supplier import Supplier
from .purchase_request import PurchaseRequest

User = get_user_model()


class PurchaseOrder(models.Model):
    """
    Modelo principal para gestionar órdenes de compra
    Soporta múltiples líneas, estados, aprobaciones y recepciones
    """
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='purchase_orders', verbose_name=_('Company'))
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='purchase_orders', verbose_name=_('Branch'))
    
    # Información básica
    order_number = models.CharField(_("Order Number"), max_length=50, unique=True, help_text=_("Auto-generated order number"))
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='purchase_orders', verbose_name=_("Supplier"))
    
    # Relación con solicitud y cotización
    purchase_request = models.ForeignKey(PurchaseRequest, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders', verbose_name=_("Purchase Request"))
    quotation = models.ForeignKey('PurchaseQuotation', on_delete=models.SET_NULL, null=True, blank=True, related_name='orders', verbose_name=_("Quotation"))
    
    # Estado de la orden
    status = models.CharField(_("Status"), max_length=20, choices=[
        ('draft', _('Draft')),
        ('sent', _('Sent to Supplier')),
        ('confirmed', _('Confirmed by Supplier')),
        ('partially_received', _('Partially Received')),
        ('received', _('Fully Received')),
        ('cancelled', _('Cancelled')),
    ], default='draft')
    
    # Fechas
    order_date = models.DateField(_("Order Date"), auto_now_add=True)
    expected_delivery_date = models.DateField(_("Expected Delivery Date"))
    confirmed_date = models.DateField(_("Confirmed Date"), null=True, blank=True)
    first_receipt_date = models.DateField(_("First Receipt Date"), null=True, blank=True)
    last_receipt_date = models.DateField(_("Last Receipt Date"), null=True, blank=True)
    
    # Información comercial
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, verbose_name=_("Currency"))
    exchange_rate = models.DecimalField(_("Exchange Rate"), max_digits=10, decimal_places=6, default=1.0)
    
    # Condiciones comerciales
    payment_terms = models.CharField(_("Payment Terms"), max_length=100, blank=True)
    delivery_terms = models.CharField(_("Delivery Terms"), max_length=100, blank=True)
    delivery_address = models.TextField(_("Delivery Address"), blank=True)
    
    # Totales
    subtotal = models.DecimalField(_("Subtotal"), max_digits=15, decimal_places=2, default=0)
    tax_amount = models.DecimalField(_("Tax Amount"), max_digits=15, decimal_places=2, default=0)
    discount_amount = models.DecimalField(_("Discount Amount"), max_digits=15, decimal_places=2, default=0)
    shipping_amount = models.DecimalField(_("Shipping Amount"), max_digits=15, decimal_places=2, default=0)
    total_amount = models.DecimalField(_("Total Amount"), max_digits=15, decimal_places=2, default=0)
    
    # Información adicional
    notes = models.TextField(_("Notes"), blank=True)
    supplier_notes = models.TextField(_("Supplier Notes"), blank=True)
    
    # Usuarios involucrados
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_purchase_orders', verbose_name=_("Created By"))
    confirmed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='confirmed_purchase_orders', verbose_name=_("Confirmed By"))
    
    # Auditoría
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Purchase Order")
        verbose_name_plural = _("Purchase Orders")
        ordering = ['-order_date', '-created_at']
        indexes = [
            models.Index(fields=['empresa', 'status']),
            models.Index(fields=['supplier', 'status']),
            models.Index(fields=['order_date']),
            models.Index(fields=['expected_delivery_date']),
            models.Index(fields=['purchase_request']),
        ]
    
    def __str__(self):
        return f"{self.order_number} - {self.supplier.name} ({self.get_status_display()})"
    
    def save(self, *args, **kwargs):
        """Genera automáticamente el número de orden si no existe"""
        if not self.order_number:
            self.order_number = self._generate_order_number()
        super().save(*args, **kwargs)
    
    def _generate_order_number(self):
        """Genera un número único de orden"""
        from django.utils import timezone
        
        year = timezone.now().year
        month = timezone.now().month
        
        # Contar órdenes del mes actual
        count = PurchaseOrder.objects.filter(
            order_date__year=year,
            order_date__month=month
        ).count() + 1
        
        return f"PO-{year}{month:02d}-{count:04d}"
    
    def calculate_totals(self):
        """Calcula los totales de la orden"""
        lines = self.lines.all()
        
        self.subtotal = sum(line.subtotal for line in lines)
        self.tax_amount = sum(line.tax_amount for line in lines)
        self.discount_amount = sum(line.discount_amount for line in lines)
        self.shipping_amount = sum(line.shipping_amount for line in lines)
        self.total_amount = self.subtotal + self.tax_amount - self.discount_amount + self.shipping_amount
        
        # Evitar recursión infinita usando update_fields y skip_signal
        super().save(update_fields=['subtotal', 'tax_amount', 'discount_amount', 'shipping_amount', 'total_amount'])
    
    def get_total_in_base_currency(self):
        """Retorna el total en moneda base"""
        return self.total_amount * self.exchange_rate
    
    def get_receipt_progress(self):
        """Calcula el progreso de recepción"""
        total_ordered = sum(line.quantity for line in self.lines.all())
        total_received = sum(line.received_quantity for line in self.lines.all())
        
        if total_ordered == 0:
            return 0
        
        return (total_received / total_ordered) * 100
    
    def is_overdue(self):
        """Verifica si la orden está vencida"""
        from django.utils import timezone
        
        return timezone.now().date() > self.expected_delivery_date
    
    def can_cancel(self):
        """Verifica si la orden puede ser cancelada"""
        return self.status in ['draft', 'sent']
    
    def can_confirm(self):
        """Verifica si la orden puede ser confirmada"""
        return self.status == 'sent'
    
    def can_receive(self):
        """Verifica si la orden puede recibir productos"""
        return self.status in ['confirmed', 'partially_received']
    
    def send_to_supplier(self):
        """Envía la orden al proveedor"""
        self.status = 'sent'
        self.save()
    
    def confirm(self, user):
        """Confirma la orden por parte del proveedor"""
        from django.utils import timezone
        
        self.status = 'confirmed'
        self.confirmed_by = user
        self.confirmed_date = timezone.now().date()
        self.save()
    
    def cancel(self, user, reason=""):
        """Cancela la orden"""
        if not self.can_cancel():
            raise ValueError(_("Cannot cancel order in current status"))
        
        self.status = 'cancelled'
        self.notes = f"Cancelled by {user.username}. Reason: {reason}"
        self.save()
    
    def update_status(self):
        """Actualiza el estado basado en las recepciones"""
        progress = self.get_receipt_progress()
        
        if progress == 0:
            if self.status == 'confirmed':
                pass  # Mantener confirmed
        elif progress < 100:
            self.status = 'partially_received'
        else:
            self.status = 'received'
        
        self.save()
    
    def duplicate(self, user):
        """Duplica la orden con sugerencias de cantidades actualizadas"""
        from .services import PurchaseOrderService
        
        service = PurchaseOrderService()
        return service.duplicate_order(self, user)


class PurchaseOrderLine(models.Model):
    """
    Modelo para las líneas individuales de una orden de compra
    """
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='lines', verbose_name=_("Purchase Order"))
    
    # Referencia a la línea de solicitud y cotización
    request_line = models.ForeignKey('PurchaseRequestLine', on_delete=models.SET_NULL, null=True, blank=True, related_name='order_lines', verbose_name=_("Request Line"))
    quotation_line = models.ForeignKey('PurchaseQuotationLine', on_delete=models.SET_NULL, null=True, blank=True, related_name='order_lines', verbose_name=_("Quotation Line"))
    
    # Información del producto
    product_variant = models.ForeignKey('inventory.ProductVariant', on_delete=models.CASCADE, verbose_name=_("Product"))
    
    # Cantidades
    quantity = models.DecimalField(_("Ordered Quantity"), max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    received_quantity = models.DecimalField(_("Received Quantity"), max_digits=10, decimal_places=2, default=0)
    unit_of_measure = models.ForeignKey('core.UnitOfMeasure', on_delete=models.CASCADE, verbose_name=_("Unit of Measure"))
    
    # Precios
    unit_price = models.DecimalField(_("Unit Price"), max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    
    # Descuentos
    discount_percentage = models.DecimalField(_("Discount %"), max_digits=5, decimal_places=2, default=0)
    discount_amount = models.DecimalField(_("Discount Amount"), max_digits=10, decimal_places=2, default=0)
    
    # Impuestos
    tax_percentage = models.DecimalField(_("Tax %"), max_digits=5, decimal_places=2, default=0)
    tax_amount = models.DecimalField(_("Tax Amount"), max_digits=10, decimal_places=2, default=0)
    
    # Envío
    shipping_amount = models.DecimalField(_("Shipping Amount"), max_digits=10, decimal_places=2, default=0)
    
    # Totales
    subtotal = models.DecimalField(_("Subtotal"), max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(_("Total"), max_digits=10, decimal_places=2, default=0)
    
    # Información adicional
    description = models.TextField(_("Description"), blank=True)
    specifications = models.JSONField(_("Specifications"), default=dict, blank=True)
    
    # Estado de la línea
    status = models.CharField(_("Status"), max_length=20, choices=[
        ('pending', _('Pending')),
        ('confirmed', _('Confirmed')),
        ('partially_received', _('Partially Received')),
        ('received', _('Fully Received')),
        ('cancelled', _('Cancelled')),
    ], default='pending')
    
    # Auditoría
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Purchase Order Line")
        verbose_name_plural = _("Purchase Order Lines")
        ordering = ['purchase_order', 'created_at']
    
    def __str__(self):
        return f"{self.purchase_order.order_number} - {self.product_variant} ({self.quantity})"
    
    def save(self, *args, **kwargs):
        """Calcula automáticamente los totales al guardar"""
        self._calculate_totals()
        self._update_status()
        super().save(*args, **kwargs)
    
    def _calculate_totals(self):
        """Calcula los totales de la línea"""
        # Subtotal sin descuentos
        self.subtotal = self.quantity * self.unit_price
        
        # Descuentos
        if self.discount_percentage > 0:
            self.discount_amount = self.subtotal * (self.discount_percentage / 100)
        else:
            self.discount_amount = 0
        
        # Base imponible
        taxable_base = self.subtotal - self.discount_amount
        
        # Impuestos
        if self.tax_percentage > 0:
            self.tax_amount = taxable_base * (self.tax_percentage / 100)
        else:
            self.tax_amount = 0
        
        # Total
        self.total = taxable_base + self.tax_amount + self.shipping_amount
    
    def _update_status(self):
        """Actualiza el estado de la línea basado en las cantidades recibidas"""
        if self.received_quantity == 0:
            self.status = 'pending'
        elif self.received_quantity < self.quantity:
            self.status = 'partially_received'
        else:
            self.status = 'received'
    
    @property
    def remaining_quantity(self):
        """Calcula la cantidad restante por recibir"""
        return max(0, self.quantity - self.received_quantity)
    
    @property
    def receipt_progress(self):
        """Calcula el progreso de recepción en porcentaje"""
        if self.quantity == 0:
            return 0
        return (self.received_quantity / self.quantity) * 100
    
    @property
    def effective_unit_price(self):
        """Retorna el precio unitario efectivo (con impuestos incluidos)"""
        return self.total / self.quantity if self.quantity > 0 else 0
    
    def receive_quantity(self, quantity, lot_number=None, expiration_date=None):
        """Registra la recepción de una cantidad específica"""
        from .models import PurchaseReceipt
        
        if quantity > self.remaining_quantity:
            raise ValueError(_("Cannot receive more than ordered quantity"))
        
        # Crear registro de recepción
        receipt = PurchaseReceipt.objects.create(
            purchase_order_line=self,
            quantity=quantity,
            lot_number=lot_number,
            expiration_date=expiration_date,
            received_by=self.purchase_order.created_by
        )
        
        # Actualizar cantidad recibida
        self.received_quantity += quantity
        self.save()
        
        # Actualizar estado de la orden
        self.purchase_order.update_status()
        
        return receipt
    
    def can_receive(self):
        """Verifica si la línea puede recibir más productos"""
        return self.remaining_quantity > 0 and self.status != 'cancelled'
    
    @property
    def total_amount(self):
        """Calcula el total de la línea (igual que el campo total, para compatibilidad de tests)"""
        return self.total
    
    def receive_quantity(self, quantity, lot_number=None, expiration_date=None):
        """Registra la recepción de una cantidad específica"""
        from .models import PurchaseReceipt
        
        if quantity > self.remaining_quantity:
            raise ValueError(_("Cannot receive more than ordered quantity"))
        
        # Crear registro de recepción
        receipt = PurchaseReceipt.objects.create(
            purchase_order_line=self,
            quantity=quantity,
            lot_number=lot_number,
            expiration_date=expiration_date,
            received_by=self.purchase_order.created_by
        )
        
        # Actualizar cantidad recibida
        self.received_quantity += quantity
        self.save()
        
        # Actualizar estado de la orden
        self.purchase_order.update_status()
        
        return receipt 