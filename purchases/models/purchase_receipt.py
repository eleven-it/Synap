from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth import get_user_model
from core.models import Empresa, Branch
from .purchase_order import PurchaseOrderLine
from django.conf import settings

User = get_user_model()


class PurchaseReceipt(models.Model):
    """
    Modelo para gestionar las recepciones de productos de órdenes de compra
    Permite registrar múltiples recepciones por línea de orden
    """
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='purchase_receipts', verbose_name=_('Company'))
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='purchase_receipts', verbose_name=_('Branch'))
    
    # Información básica
    receipt_number = models.CharField(_("Receipt Number"), max_length=50, unique=True, help_text=_("Auto-generated receipt number"))
    purchase_order_line = models.ForeignKey(PurchaseOrderLine, on_delete=models.CASCADE, related_name='receipts', verbose_name=_("Purchase Order Line"))
    
    # Cantidades y fechas
    quantity = models.DecimalField(_("Received Quantity"), max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    receipt_date = models.DateField(_("Receipt Date"), auto_now_add=True)
    received_at = models.DateTimeField(_("Received At"), auto_now_add=True)
    
    # Información de calidad y trazabilidad
    lot_number = models.CharField(_("Lot Number"), max_length=100, blank=True)
    expiration_date = models.DateField(_("Expiration Date"), null=True, blank=True)
    manufacturing_date = models.DateField(_("Manufacturing Date"), null=True, blank=True)
    
    # Estado de la recepción
    status = models.CharField(_("Status"), max_length=20, choices=[
        ('pending', _('Pending Inspection')),
        ('approved', _('Approved')),
        ('rejected', _('Rejected')),
        ('returned', _('Returned to Supplier')),
    ], default='pending')
    
    # Información de calidad
    quality_score = models.PositiveIntegerField(_("Quality Score"), null=True, blank=True, 
                                              validators=[MaxValueValidator(10)],
                                              help_text=_("Quality score from 1 to 10"))
    quality_notes = models.TextField(_("Quality Notes"), blank=True)
    
    # Condiciones de recepción
    packaging_condition = models.CharField(_("Packaging Condition"), max_length=20, choices=[
        ('excellent', _('Excellent')),
        ('good', _('Good')),
        ('fair', _('Fair')),
        ('poor', _('Poor')),
        ('damaged', _('Damaged')),
    ], default='good')
    
    # Información adicional
    notes = models.TextField(_("Notes"), blank=True)
    supplier_notes = models.TextField(_("Supplier Notes"), blank=True)
    
    # Usuarios involucrados
    received_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='received_purchases', verbose_name=_("Received By"))
    inspected_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='inspected_purchases', verbose_name=_("Inspected By"))
    
    # Auditoría
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Purchase Receipt")
        verbose_name_plural = _("Purchase Receipts")
        ordering = ['-receipt_date', '-created_at']
        indexes = [
            models.Index(fields=['empresa', 'status']),
            models.Index(fields=['purchase_order_line']),
            models.Index(fields=['receipt_date']),
            models.Index(fields=['lot_number']),
            models.Index(fields=['expiration_date']),
        ]
    
    def __str__(self):
        return f"{self.receipt_number} - {self.purchase_order_line.product_variant} ({self.quantity})"
    
    def save(self, *args, **kwargs):
        """Genera automáticamente el número de recepción si no existe"""
        if not self.receipt_number:
            self.receipt_number = self._generate_receipt_number()
        super().save(*args, **kwargs)
    
    def _generate_receipt_number(self):
        """Genera un número único de recepción"""
        from django.utils import timezone
        
        year = timezone.now().year
        month = timezone.now().month
        
        # Contar recepciones del mes actual
        count = PurchaseReceipt.objects.filter(
            receipt_date__year=year,
            receipt_date__month=month
        ).count() + 1
        
        return f"PR-{year}{month:02d}-{count:04d}"
    
    def approve(self, user, quality_score=None, quality_notes=""):
        """Aprueba la recepción después de la inspección"""
        self.status = 'approved'
        self.inspected_by = user
        self.quality_score = quality_score
        self.quality_notes = quality_notes
        self.save()
        
        # Actualizar stock
        self._update_stock()
    
    def reject(self, user, reason=""):
        """Rechaza la recepción"""
        self.status = 'rejected'
        self.inspected_by = user
        self.quality_notes = f"Rejected: {reason}"
        self.save()
    
    def return_to_supplier(self, user, reason=""):
        """Marca la recepción como devuelta al proveedor"""
        self.status = 'returned'
        self.notes = f"Returned to supplier: {reason}"
        self.save()
    
    def _update_stock(self):
        """Actualiza el stock del producto"""
        from inventory.services import StockService
        
        stock_service = StockService()
        
        # Obtener información del producto
        product_variant = self.purchase_order_line.product_variant
        quantity = self.quantity
        lot_number = self.lot_number
        expiration_date = self.expiration_date
        
        # Actualizar stock
        stock_service.add_stock(
            product_variant=product_variant,
            quantity=quantity,
            lot_number=lot_number,
            expiration_date=expiration_date,
            reference=f"Purchase Receipt {self.receipt_number}",
            reference_type='purchase_receipt',
            reference_id=self.id
        )
    
    def get_quality_status(self):
        """Retorna el estado de calidad basado en el score"""
        if not self.quality_score:
            return 'not_evaluated'
        
        if self.quality_score >= 9:
            return 'excellent'
        elif self.quality_score >= 7:
            return 'good'
        elif self.quality_score >= 5:
            return 'fair'
        else:
            return 'poor'
    
    def is_expired(self):
        """Verifica si el producto ha expirado"""
        if not self.expiration_date:
            return False
        
        from django.utils import timezone
        return timezone.now().date() > self.expiration_date
    
    def get_days_until_expiration(self):
        """Calcula los días hasta la expiración"""
        if not self.expiration_date:
            return None
        
        from django.utils import timezone
        delta = self.expiration_date - timezone.now().date()
        return delta.days
    
    def get_expiration_status(self):
        """Retorna el estado de expiración"""
        days_until_expiration = self.get_days_until_expiration()
        
        if days_until_expiration is None:
            return 'no_expiration'
        elif days_until_expiration < 0:
            return 'expired'
        elif days_until_expiration <= 30:
            return 'expiring_soon'
        elif days_until_expiration <= 90:
            return 'expiring_soon'
        else:
            return 'good'
    
    @property
    def purchase_order(self):
        """Retorna la orden de compra asociada"""
        return self.purchase_order_line.purchase_order
    
    @property
    def supplier(self):
        """Retorna el proveedor asociado"""
        return self.purchase_order.supplier
    
    @property
    def product_variant(self):
        """Retorna la variante del producto"""
        return self.purchase_order_line.product_variant


class PurchaseReceiptDocument(models.Model):
    """
    Modelo para gestionar documentos asociados a las recepciones
    """
    receipt = models.ForeignKey(PurchaseReceipt, on_delete=models.CASCADE, related_name='documents', verbose_name=_("Receipt"))
    
    # Información del documento
    document_type = models.CharField(_("Document Type"), max_length=50, choices=[
        ('delivery_note', _('Delivery Note')),
        ('invoice', _('Invoice')),
        ('quality_certificate', _('Quality Certificate')),
        ('safety_data_sheet', _('Safety Data Sheet')),
        ('other', _('Other')),
    ])
    
    document_number = models.CharField(_("Document Number"), max_length=100, blank=True)
    document_date = models.DateField(_("Document Date"), null=True, blank=True)
    
    # Archivo
    file = models.FileField(_("File"), upload_to='purchases/receipts/documents/')
    file_name = models.CharField(_("File Name"), max_length=255)
    file_size = models.PositiveIntegerField(_("File Size (bytes)"), null=True, blank=True)
    
    # Información adicional
    description = models.TextField(_("Description"), blank=True)
    
    # Auditoría
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name=_("Uploaded By"))
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _("Purchase Receipt Document")
        verbose_name_plural = _("Purchase Receipt Documents")
        ordering = ['receipt', '-uploaded_at']
    
    def __str__(self):
        return f"{self.receipt.receipt_number} - {self.get_document_type_display()}"
    
    def save(self, *args, **kwargs):
        """Calcula automáticamente el tamaño del archivo"""
        if self.file and not self.file_size:
            try:
                self.file_size = self.file.size
            except:
                pass
        super().save(*args, **kwargs)
    
    @property
    def file_size_mb(self):
        """Retorna el tamaño del archivo en MB"""
        if self.file_size:
            return round(self.file_size / (1024 * 1024), 2)
        return 0 