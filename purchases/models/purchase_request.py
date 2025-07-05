from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from core.models import Empresa, Branch, Currency
from inventory.models import ProductVariant, Location

User = get_user_model()


class PurchaseRequest(models.Model):
    """
    Modelo para gestionar solicitudes de compra
    Pueden generarse automáticamente desde órdenes de venta o manualmente
    """
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='purchase_requests', verbose_name=_('Company'))
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='purchase_requests', verbose_name=_('Branch'))
    
    # Información básica
    request_number = models.CharField(_("Request Number"), max_length=50, unique=True, help_text=_("Auto-generated request number"))
    title = models.CharField(_("Title"), max_length=255, help_text=_("Brief description of the request"))
    description = models.TextField(_("Description"), blank=True, help_text=_("Detailed description of the request"))
    
    # Estado y prioridad
    status = models.CharField(_("Status"), max_length=20, choices=[
        ('draft', _('Draft')),
        ('submitted', _('Submitted')),
        ('approved', _('Approved')),
        ('rejected', _('Rejected')),
        ('converted', _('Converted to Order')),
        ('cancelled', _('Cancelled')),
    ], default='draft')
    
    priority = models.CharField(_("Priority"), max_length=20, choices=[
        ('low', _('Low')),
        ('medium', _('Medium')),
        ('high', _('High')),
        ('urgent', _('Urgent')),
    ], default='medium')
    
    # Fechas
    request_date = models.DateField(_("Request Date"), auto_now_add=True)
    required_date = models.DateField(_("Required Date"), help_text=_("Date when items are needed"))
    approved_date = models.DateField(_("Approved Date"), null=True, blank=True)
    
    # Ubicación de entrega
    delivery_location = models.ForeignKey(Location, on_delete=models.CASCADE, verbose_name=_("Delivery Location"))
    
    # Información de presupuesto
    budget_amount = models.DecimalField(_("Budget Amount"), max_digits=15, decimal_places=2, null=True, blank=True)
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, verbose_name=_("Currency"))
    
    # Origen de la solicitud
    origin_type = models.CharField(_("Origin Type"), max_length=20, choices=[
        ('manual', _('Manual')),
        ('sales_order', _('Sales Order')),
        ('inventory', _('Inventory Replenishment')),
        ('production', _('Production Requirement')),
        ('other', _('Other')),
    ], default='manual')
    
    origin_reference = models.CharField(_("Origin Reference"), max_length=100, blank=True, 
                                      help_text=_("Reference to the original document (e.g., SO-001)"))
    
    # Usuarios involucrados
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='requested_purchases', verbose_name=_("Requested By"))
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_purchases', verbose_name=_("Approved By"))
    
    # Comentarios y notas
    notes = models.TextField(_("Notes"), blank=True)
    rejection_reason = models.TextField(_("Rejection Reason"), blank=True)
    
    # Auditoría
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Purchase Request")
        verbose_name_plural = _("Purchase Requests")
        ordering = ['-request_date', '-created_at']
        indexes = [
            models.Index(fields=['empresa', 'status']),
            models.Index(fields=['requested_by', 'status']),
            models.Index(fields=['required_date']),
            models.Index(fields=['origin_type', 'origin_reference']),
        ]
    
    def __str__(self):
        return f"{self.request_number} - {self.title} ({self.get_status_display()})"
    
    def save(self, *args, **kwargs):
        """Genera automáticamente el número de solicitud si no existe"""
        if not self.request_number:
            self.request_number = self._generate_request_number()
        super().save(*args, **kwargs)
    
    def _generate_request_number(self):
        """Genera un número único de solicitud"""
        from django.utils import timezone
        
        year = timezone.now().year
        month = timezone.now().month
        
        # Contar solicitudes del mes actual
        count = PurchaseRequest.objects.filter(
            request_date__year=year,
            request_date__month=month
        ).count() + 1
        
        return f"PR-{year}{month:02d}-{count:04d}"
    
    def get_total_amount(self):
        """Calcula el monto total de la solicitud"""
        return self.lines.aggregate(total=models.Sum('total_amount'))['total'] or 0
    
    def get_line_count(self):
        """Retorna el número de líneas en la solicitud"""
        return self.lines.count()
    
    def approve(self, user, notes=""):
        """Aprueba la solicitud de compra"""
        from django.utils import timezone
        
        self.status = 'approved'
        self.approved_by = user
        self.approved_date = timezone.now().date()
        self.notes = notes
        self.save()
    
    def reject(self, user, reason=""):
        """Rechaza la solicitud de compra"""
        self.status = 'rejected'
        self.approved_by = user
        self.rejection_reason = reason
        self.save()
    
    def convert_to_order(self):
        """Marca la solicitud como convertida a orden"""
        self.status = 'converted'
        self.save()
    
    def cancel(self, user):
        """Cancela la solicitud de compra"""
        self.status = 'cancelled'
        self.approved_by = user
        self.save()
    
    def is_urgent(self):
        """Verifica si la solicitud es urgente basada en la fecha requerida"""
        from django.utils import timezone
        from datetime import timedelta
        
        today = timezone.now().date()
        days_until_required = (self.required_date - today).days
        
        return days_until_required <= 7 or self.priority == 'urgent'
    
    def get_related_orders(self):
        """Retorna las órdenes de compra relacionadas con esta solicitud"""
        from .purchase_order import PurchaseOrder
        return PurchaseOrder.objects.filter(purchase_request=self)


class PurchaseRequestLine(models.Model):
    """
    Modelo para las líneas individuales de una solicitud de compra
    """
    purchase_request = models.ForeignKey(PurchaseRequest, on_delete=models.CASCADE, related_name='lines', verbose_name=_("Purchase Request"))
    
    # Producto
    product_variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, verbose_name=_("Product"))
    
    # Cantidades
    quantity = models.DecimalField(_("Quantity"), max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    unit_of_measure = models.ForeignKey('core.UnitOfMeasure', on_delete=models.CASCADE, verbose_name=_("Unit of Measure"))
    
    # Información de precio
    estimated_unit_price = models.DecimalField(_("Estimated Unit Price"), max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, verbose_name=_("Currency"))
    
    # Información adicional
    description = models.TextField(_("Description"), blank=True, help_text=_("Additional specifications or requirements"))
    specifications = models.JSONField(_("Specifications"), default=dict, blank=True, help_text=_("Technical specifications as JSON"))
    
    # Estado de la línea
    status = models.CharField(_("Status"), max_length=20, choices=[
        ('pending', _('Pending')),
        ('approved', _('Approved')),
        ('rejected', _('Rejected')),
        ('ordered', _('Ordered')),
        ('received', _('Received')),
    ], default='pending')
    
    # Información de stock
    current_stock = models.DecimalField(_("Current Stock"), max_digits=10, decimal_places=2, default=0)
    minimum_stock = models.DecimalField(_("Minimum Stock"), max_digits=10, decimal_places=2, default=0)
    
    # Auditoría
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Purchase Request Line")
        verbose_name_plural = _("Purchase Request Lines")
        ordering = ['purchase_request', 'created_at']
    
    def __str__(self):
        return f"{self.purchase_request.request_number} - {self.product_variant} ({self.quantity})"
    
    @property
    def total_amount(self):
        """Calcula el monto total de la línea"""
        if self.estimated_unit_price:
            return self.quantity * self.estimated_unit_price
        return 0
    
    def get_stock_deficit(self):
        """Calcula el déficit de stock"""
        return max(0, self.minimum_stock - self.current_stock)
    
    def is_stock_critical(self):
        """Verifica si el stock está en nivel crítico"""
        return self.current_stock <= self.minimum_stock
    
    def update_stock_info(self):
        """Actualiza la información de stock desde el inventario"""
        from inventory.services.stock import StockService
        
        stock_service = StockService()
        current_stock = stock_service.get_product_stock(
            product_variant=self.product_variant,
            empresa=self.purchase_request.empresa,
            branch=self.purchase_request.branch
        )
        
        self.current_stock = current_stock.get('available_quantity', 0)
        self.save(update_fields=['current_stock'])
    
    def approve(self):
        """Aprueba la línea de solicitud"""
        self.status = 'approved'
        self.save()
    
    def reject(self):
        """Rechaza la línea de solicitud"""
        self.status = 'rejected'
        self.save()
    
    def mark_ordered(self):
        """Marca la línea como ordenada"""
        self.status = 'ordered'
        self.save()
    
    def mark_received(self):
        """Marca la línea como recibida"""
        self.status = 'received'
        self.save() 