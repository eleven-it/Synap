from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from core.models import Empresa, Branch, Currency
from .supplier import Supplier
from .purchase_request import PurchaseRequest
from django.conf import settings

class PurchaseQuotation(models.Model):
    """
    Modelo para gestionar cotizaciones de compra
    Permite comparar múltiples ofertas de proveedores para una solicitud
    """
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='purchase_quotations', verbose_name=_('Company'))
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='purchase_quotations', verbose_name=_('Branch'))
    
    # Información básica
    quotation_number = models.CharField(_("Quotation Number"), max_length=50, unique=True, help_text=_("Auto-generated quotation number"))
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='quotations', verbose_name=_("Supplier"))
    
    # Relación con solicitud de compra
    purchase_request = models.ForeignKey(PurchaseRequest, on_delete=models.CASCADE, related_name='quotations', verbose_name=_("Purchase Request"))
    
    # Estado de la cotización
    status = models.CharField(_("Status"), max_length=20, choices=[
        ('draft', _('Draft')),
        ('sent', _('Sent to Supplier')),
        ('received', _('Received from Supplier')),
        ('evaluated', _('Evaluated')),
        ('selected', _('Selected')),
        ('rejected', _('Rejected')),
        ('expired', _('Expired')),
    ], default='draft')
    
    # Fechas
    quotation_date = models.DateField(_("Quotation Date"), auto_now_add=True)
    valid_until = models.DateField(_("Valid Until"), help_text=_("Date until which the quotation is valid"))
    received_date = models.DateField(_("Received Date"), null=True, blank=True)
    
    # Información comercial
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, verbose_name=_("Currency"))
    exchange_rate = models.DecimalField(_("Exchange Rate"), max_digits=10, decimal_places=6, default=1.0,
                                      help_text=_("Exchange rate to base currency"))
    
    # Condiciones comerciales
    payment_terms = models.CharField(_("Payment Terms"), max_length=100, blank=True)
    delivery_terms = models.CharField(_("Delivery Terms"), max_length=100, blank=True)
    delivery_time = models.PositiveIntegerField(_("Delivery Time (days)"), null=True, blank=True)
    
    # Totales
    subtotal = models.DecimalField(_("Subtotal"), max_digits=15, decimal_places=2, default=0)
    tax_amount = models.DecimalField(_("Tax Amount"), max_digits=15, decimal_places=2, default=0)
    discount_amount = models.DecimalField(_("Discount Amount"), max_digits=15, decimal_places=2, default=0)
    total_amount = models.DecimalField(_("Total Amount"), max_digits=15, decimal_places=2, default=0)
    
    # Información adicional
    notes = models.TextField(_("Notes"), blank=True)
    supplier_notes = models.TextField(_("Supplier Notes"), blank=True, help_text=_("Notes from the supplier"))
    
    # Evaluación
    evaluation_score = models.PositiveIntegerField(_("Evaluation Score"), null=True, blank=True, 
                                                 validators=[MinValueValidator(1), MaxValueValidator(10)],
                                                 help_text=_("Score from 1 to 10"))
    evaluation_notes = models.TextField(_("Evaluation Notes"), blank=True)
    
    # Auditoría
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_quotations', verbose_name=_("Created By"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Purchase Quotation")
        verbose_name_plural = _("Purchase Quotations")
        ordering = ['-quotation_date', '-created_at']
        indexes = [
            models.Index(fields=['empresa', 'status']),
            models.Index(fields=['supplier', 'status']),
            models.Index(fields=['purchase_request', 'status']),
            models.Index(fields=['valid_until']),
        ]
    
    def __str__(self):
        return f"{self.quotation_number} - {self.supplier.name} ({self.get_status_display()})"
    
    def save(self, *args, **kwargs):
        """Genera automáticamente el número de cotización si no existe"""
        if not self.quotation_number:
            self.quotation_number = self._generate_quotation_number()
        super().save(*args, **kwargs)
    
    def _generate_quotation_number(self):
        """Genera un número único de cotización"""
        from django.utils import timezone
        
        year = timezone.now().year
        month = timezone.now().month
        
        # Contar cotizaciones del mes actual
        count = PurchaseQuotation.objects.filter(
            quotation_date__year=year,
            quotation_date__month=month
        ).count() + 1
        
        return f"QC-{year}{month:02d}-{count:04d}"
    
    def calculate_totals(self):
        """Calcula los totales de la cotización"""
        lines = self.lines.all()
        
        self.subtotal = sum(line.subtotal for line in lines)
        self.tax_amount = sum(line.tax_amount for line in lines)
        self.discount_amount = sum(line.discount_amount for line in lines)
        self.total_amount = self.subtotal + self.tax_amount - self.discount_amount
        
        self.save(update_fields=['subtotal', 'tax_amount', 'discount_amount', 'total_amount'])
    
    def is_expired(self):
        """Verifica si la cotización ha expirado"""
        from django.utils import timezone
        
        return timezone.now().date() > self.valid_until
    
    def is_valid(self):
        """Verifica si la cotización es válida"""
        return self.status in ['received', 'evaluated'] and not self.is_expired()
    
    def mark_received(self):
        """Marca la cotización como recibida del proveedor"""
        from django.utils import timezone
        
        self.status = 'received'
        self.received_date = timezone.now().date()
        self.save()
    
    def evaluate(self, score, notes=""):
        """Evalúa la cotización"""
        self.status = 'evaluated'
        self.evaluation_score = score
        self.evaluation_notes = notes
        self.save()
    
    def select(self):
        """Selecciona esta cotización como la ganadora"""
        self.status = 'selected'
        self.save()
        
        # Rechazar otras cotizaciones de la misma solicitud
        other_quotations = PurchaseQuotation.objects.filter(
            purchase_request=self.purchase_request,
            status__in=['received', 'evaluated']
        ).exclude(id=self.id)
        
        for quotation in other_quotations:
            quotation.status = 'rejected'
            quotation.save()
    
    def reject(self, reason=""):
        """Rechaza la cotización"""
        self.status = 'rejected'
        self.evaluation_notes = reason
        self.save()
    
    def get_total_in_base_currency(self):
        """Retorna el total en moneda base"""
        return self.total_amount * self.exchange_rate
    
    def get_delivery_urgency(self):
        """Calcula la urgencia de entrega basada en la fecha requerida"""
        from django.utils import timezone
        
        required_date = self.purchase_request.required_date
        delivery_date = timezone.now().date()
        
        if self.delivery_time:
            delivery_date = delivery_date + timedelta(days=self.delivery_time)
        
        days_until_required = (required_date - delivery_date).days
        
        if days_until_required < 0:
            return 'late'
        elif days_until_required <= 3:
            return 'urgent'
        elif days_until_required <= 7:
            return 'normal'
        else:
            return 'comfortable'


class PurchaseQuotationLine(models.Model):
    """
    Modelo para las líneas individuales de una cotización de compra
    """
    quotation = models.ForeignKey(PurchaseQuotation, on_delete=models.CASCADE, related_name='lines', verbose_name=_("Quotation"))
    
    # Referencia a la línea de solicitud
    request_line = models.ForeignKey('PurchaseRequestLine', on_delete=models.CASCADE, related_name='quotation_lines', verbose_name=_("Request Line"))
    
    # Información del producto
    product_variant = models.ForeignKey('inventory.ProductVariant', on_delete=models.CASCADE, verbose_name=_("Product"))
    
    # Cantidades y precios
    quantity = models.DecimalField(_("Quantity"), max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    unit_price = models.DecimalField(_("Unit Price"), max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    unit_of_measure = models.ForeignKey('core.UnitOfMeasure', on_delete=models.CASCADE, verbose_name=_("Unit of Measure"))
    
    # Descuentos
    discount_percentage = models.DecimalField(_("Discount %"), max_digits=5, decimal_places=2, default=0)
    discount_amount = models.DecimalField(_("Discount Amount"), max_digits=10, decimal_places=2, default=0)
    
    # Impuestos
    tax_percentage = models.DecimalField(_("Tax %"), max_digits=5, decimal_places=2, default=0)
    tax_amount = models.DecimalField(_("Tax Amount"), max_digits=10, decimal_places=2, default=0)
    
    # Totales
    subtotal = models.DecimalField(_("Subtotal"), max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(_("Total"), max_digits=10, decimal_places=2, default=0)
    
    # Información adicional
    description = models.TextField(_("Description"), blank=True)
    specifications = models.JSONField(_("Specifications"), default=dict, blank=True)
    
    # Condiciones específicas
    delivery_time = models.PositiveIntegerField(_("Delivery Time (days)"), null=True, blank=True)
    minimum_order_quantity = models.DecimalField(_("Minimum Order Quantity"), max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Auditoría
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Purchase Quotation Line")
        verbose_name_plural = _("Purchase Quotation Lines")
        ordering = ['quotation', 'created_at']
        unique_together = [['quotation', 'request_line']]
    
    def __str__(self):
        return f"{self.quotation.quotation_number} - {self.product_variant} ({self.quantity})"
    
    def save(self, *args, **kwargs):
        """Calcula automáticamente los totales al guardar"""
        self._calculate_totals()
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
        self.total = taxable_base + self.tax_amount
    
    @property
    def unit_price_with_discount(self):
        """Retorna el precio unitario con descuento aplicado"""
        if self.discount_percentage > 0:
            return self.unit_price * (1 - self.discount_percentage / 100)
        return self.unit_price
    
    @property
    def effective_unit_price(self):
        """Retorna el precio unitario efectivo (con impuestos incluidos)"""
        return self.total / self.quantity if self.quantity > 0 else 0
    
    def get_delivery_date(self):
        """Calcula la fecha de entrega estimada"""
        if not self.delivery_time:
            return None
        
        from django.utils import timezone
        from datetime import timedelta
        
        return timezone.now().date() + timedelta(days=self.delivery_time)
    
    def meets_minimum_order(self):
        """Verifica si cumple con la cantidad mínima de pedido"""
        if not self.minimum_order_quantity:
            return True
        return self.quantity >= self.minimum_order_quantity 