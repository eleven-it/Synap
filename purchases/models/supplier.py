from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator
from django.contrib.auth import get_user_model
from core.models import Empresa, Branch, Currency
from django.utils import timezone

User = get_user_model()


class Supplier(models.Model):
    """
    Modelo para gestionar proveedores del sistema
    Contiene información completa del proveedor para compras
    """
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='suppliers', verbose_name=_('Company'))
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='suppliers', verbose_name=_('Branch'))
    
    # Información básica
    name = models.CharField(_("Name"), max_length=255)
    code = models.CharField(_("Code"), max_length=20, unique=True, help_text=_("Internal supplier code"))
    tax_id = models.CharField(_("Tax ID"), max_length=50, blank=True, help_text=_("VAT number or tax identification"))
    
    # Información de contacto
    contact_person = models.CharField(_("Contact Person"), max_length=100, blank=True)
    email = models.EmailField(_("Email"), blank=True)
    phone = models.CharField(_("Phone"), max_length=20, blank=True)
    mobile = models.CharField(_("Mobile"), max_length=20, blank=True)
    
    # Dirección
    address = models.TextField(_("Address"), blank=True)
    city = models.CharField(_("City"), max_length=100, blank=True)
    state = models.CharField(_("State/Province"), max_length=100, blank=True)
    postal_code = models.CharField(_("Postal Code"), max_length=20, blank=True)
    country = models.CharField(_("Country"), max_length=100, default="Argentina")
    
    # Información comercial
    payment_terms = models.CharField(_("Payment Terms"), max_length=100, blank=True, help_text=_("e.g., Net 30, Net 60"))
    credit_limit = models.DecimalField(_("Credit Limit"), max_digits=15, decimal_places=2, null=True, blank=True)
    currency = models.ForeignKey(Currency, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Default Currency"))
    
    # Categorización
    supplier_category = models.CharField(_("Category"), max_length=50, blank=True, help_text=_("e.g., Raw Materials, Services, Equipment"))
    supplier_type = models.CharField(_("Type"), max_length=50, choices=[
        ('manufacturer', _('Manufacturer')),
        ('distributor', _('Distributor')),
        ('wholesaler', _('Wholesaler')),
        ('service_provider', _('Service Provider')),
        ('other', _('Other')),
    ], default='other')
    
    # Configuración de impuestos
    tax_category = models.CharField(_("Tax Category"), max_length=50, blank=True, help_text=_("Category for tax calculation"))
    is_tax_exempt = models.BooleanField(_("Tax Exempt"), default=False)
    
    # Estado y configuración
    is_active = models.BooleanField(_("Active"), default=True)
    is_approved = models.BooleanField(_("Approved"), default=False)
    approval_date = models.DateTimeField(_("Approval Date"), null=True, blank=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_suppliers', verbose_name=_("Approved By"))
    
    # Información adicional
    notes = models.TextField(_("Notes"), blank=True)
    website = models.URLField(_("Website"), blank=True)
    
    # Auditoría
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_suppliers', verbose_name=_("Created By"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Supplier")
        verbose_name_plural = _("Suppliers")
        ordering = ['name']
        unique_together = [['empresa', 'code']]
        indexes = [
            models.Index(fields=['empresa', 'is_active']),
            models.Index(fields=['supplier_category', 'is_active']),
            models.Index(fields=['name']),
        ]
    
    def __str__(self):
        return f"{self.code} - {self.name} ({self.empresa})"
    
    def get_full_address(self):
        """Retorna la dirección completa del proveedor"""
        parts = [self.address, self.city, self.state, self.postal_code, self.country]
        return ", ".join(filter(None, parts))
    
    def get_contact_info(self):
        """Retorna la información de contacto principal"""
        if self.email:
            return self.email
        elif self.phone:
            return self.phone
        elif self.mobile:
            return self.mobile
        return _("No contact information")
    
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