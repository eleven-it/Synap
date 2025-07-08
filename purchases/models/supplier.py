from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator
from django.contrib.auth import get_user_model
from core.models import Empresa, Branch, Currency, BusinessEntity
from django.utils import timezone

User = get_user_model()


class Supplier(BusinessEntity):
    """
    Proveedor específico con funcionalidad de compras
    Hereda de BusinessEntity para funcionalidad común
    """
    
    # Relaciones con empresa y sucursal
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='suppliers', verbose_name=_('Company'))
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='suppliers', verbose_name=_('Branch'))
    
    # Información específica de proveedor
    payment_terms = models.CharField(_("Payment Terms"), max_length=100, blank=True, help_text=_("e.g., Net 30, Net 60"))
    credit_limit = models.DecimalField(_("Credit Limit"), max_digits=15, decimal_places=2, null=True, blank=True)
    currency = models.ForeignKey(Currency, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Default Currency"))
    
    # Categorización específica
    supplier_category = models.CharField(_("Category"), max_length=50, blank=True, help_text=_("e.g., Raw Materials, Services, Equipment"))
    supplier_type = models.CharField(_("Type"), max_length=50, choices=[
        ('manufacturer', _('Manufacturer')),
        ('distributor', _('Distributor')),
        ('wholesaler', _('Wholesaler')),
        ('service_provider', _('Service Provider')),
        ('other', _('Other')),
    ], default='other')
    
    # Configuración de impuestos específica
    tax_category = models.CharField(_("Tax Category"), max_length=50, blank=True, help_text=_("Category for tax calculation"))
    is_tax_exempt = models.BooleanField(_("Tax Exempt"), default=False)
    
    # Estado específico de proveedor
    is_approved = models.BooleanField(_("Approved"), default=False)
    approval_date = models.DateTimeField(_("Approval Date"), null=True, blank=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_suppliers', verbose_name=_("Approved By"))
    
    # Auditoría específica
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_suppliers', verbose_name=_("Created By"))
    
    class Meta:
        verbose_name = _("Supplier")
        verbose_name_plural = _("Suppliers")
        ordering = ['name']
        unique_together = [['empresa', 'code']]
        indexes = [
            models.Index(fields=['empresa', 'is_active']),
            models.Index(fields=['supplier_category', 'is_active']),
            models.Index(fields=['supplier_type']),
            models.Index(fields=['is_approved']),
        ]
    
    def __str__(self):
        return f"{self.code} - {self.name} ({self.empresa})"
    
    def clean(self):
        """Validaciones específicas del proveedor"""
        from django.core.exceptions import ValidationError
        
        # Validar límite de crédito
        if self.credit_limit and self.credit_limit < 0:
            raise ValidationError(_('Credit limit cannot be negative.'))
        
        # Validar que tenga empresa y sucursal
        if not self.empresa:
            raise ValidationError(_('Supplier must be associated with a company.'))
        
        if not self.branch:
            raise ValidationError(_('Supplier must be associated with a branch.'))
        
        # Validar que la sucursal pertenezca a la empresa
        if self.empresa and self.branch and self.branch.empresa != self.empresa:
            raise ValidationError(_('Branch must belong to the selected company.'))
    
    def get_rating_average(self):
        """Retorna el promedio de calificaciones del proveedor"""
        ratings = self.ratings.filter(status='approved')
        if ratings.exists():
            return ratings.aggregate(avg=models.Avg('overall_score'))['avg']
        return None
    
    def get_total_purchases(self, start_date=None, end_date=None):
        """Retorna el total de compras en el período especificado"""
        from .purchase_order import PurchaseOrder
        
        queryset = PurchaseOrder.objects.filter(supplier=self, status='received')
        if start_date:
            queryset = queryset.filter(order_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(order_date__lte=end_date)
        
        return queryset.aggregate(total=models.Sum('total_amount'))['total'] or 0
    
    def get_purchase_history(self, days=30):
        """Retorna el historial de compras de los últimos días"""
        from django.utils import timezone
        from datetime import timedelta
        from .purchase_order import PurchaseOrder
        
        start_date = timezone.now() - timedelta(days=days)
        return PurchaseOrder.objects.filter(
            supplier=self,
            order_date__gte=start_date
        ).order_by('-order_date')
    
    def approve(self, user):
        """Aprueba el proveedor"""
        self.is_approved = True
        self.approval_date = timezone.now()
        self.approved_by = user
        self.save()
    
    def deactivate(self):
        """Desactiva el proveedor"""
        self.is_active = False
        self.save()
    
    def activate(self):
        """Activa el proveedor"""
        self.is_active = True
        self.save()
    
    @property
    def total_orders(self):
        """Retorna el total de órdenes del proveedor"""
        return self.purchase_orders.count()
    
    @property
    def total_spent(self):
        """Retorna el total gastado con el proveedor"""
        return self.purchase_orders.filter(status='received').aggregate(
            total=models.Sum('total_amount')
        )['total'] or 0
    
    @property
    def outstanding_balance(self):
        """Retorna el saldo pendiente con el proveedor"""
        return self.purchase_orders.filter(status='received', payment_status='pending').aggregate(
            total=models.Sum('total_amount')
        )['total'] or 0
    
    def can_place_order(self, amount):
        """Verifica si se puede realizar una orden por el monto especificado"""
        if not self.credit_limit:
            return True
        return self.credit_limit >= amount
    
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