"""
Modelos para la integración con MercadoPago
Soporte completo para múltiples puntos de pago y dispositivos SmartPOS
"""

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.conf import settings
import json
import logging

logger = logging.getLogger(__name__)


class MercadoPagoConfig(models.Model):
    """
    Configuración de MercadoPago por empresa
    """
    empresa = models.ForeignKey('core.Empresa', on_delete=models.CASCADE, verbose_name=_("Company"))
    is_active = models.BooleanField(_("Active"), default=True)
    is_sandbox = models.BooleanField(_("Sandbox Mode"), default=True)
    
    # Credenciales básicas
    client_id = models.CharField(_("Client ID"), max_length=255)
    client_secret = models.CharField(_("Client Secret"), max_length=255)
    
    # Configuración de webhooks
    webhook_url = models.URLField(_("Webhook URL"), blank=True)
    webhook_secret = models.CharField(_("Webhook Secret"), max_length=255, blank=True)
    
    # Configuración de pagos
    supported_payment_methods = models.JSONField(_("Supported Payment Methods"), default=list)
    commission_percentage = models.DecimalField(_("Commission %"), max_digits=5, decimal_places=2, default=0)
    auto_capture = models.BooleanField(_("Auto Capture"), default=True)
    installments_enabled = models.BooleanField(_("Installments Enabled"), default=True)
    max_installments = models.IntegerField(_("Max Installments"), default=12)
    
    # Configuración de SmartPOS
    smartpos_enabled = models.BooleanField(_("SmartPOS Enabled"), default=True)
    smartpos_api_key = models.CharField(_("SmartPOS API Key"), max_length=255, blank=True)
    smartpos_webhook_url = models.URLField(_("SmartPOS Webhook URL"), blank=True)
    
    # Configuración de múltiples dispositivos
    allow_multiple_devices = models.BooleanField(_("Allow Multiple Devices"), default=True)
    max_devices_per_branch = models.IntegerField(_("Max Devices per Branch"), default=5)
    device_sync_interval = models.IntegerField(_("Device Sync Interval (seconds)"), default=300)
    
    # Configuración adicional
    config = models.JSONField(_("Additional Configuration"), default=dict, blank=True)
    
    # Auditoría
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey('core.UsuarioExtendido', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_mercadopago_configs')
    updated_by = models.ForeignKey('core.UsuarioExtendido', on_delete=models.SET_NULL, null=True, blank=True, related_name='updated_mercadopago_configs')
    
    class Meta:
        verbose_name = _('MercadoPago Configuration')
        verbose_name_plural = _('MercadoPago Configurations')
        ordering = ['empresa__name']
        unique_together = [['empresa']]
        indexes = [
            models.Index(fields=['empresa', 'is_active']),
            models.Index(fields=['is_sandbox']),
        ]
    
    def __str__(self):
        return f"MercadoPago Config - {self.empresa.name}"
    
    def clean(self):
        """Validaciones del modelo"""
        if self.commission_percentage < 0 or self.commission_percentage > 100:
            raise ValidationError(_("Commission percentage must be between 0 and 100"))
        
        if self.max_installments < 1 or self.max_installments > 60:
            raise ValidationError(_("Max installments must be between 1 and 60"))
        
        if self.max_devices_per_branch < 1 or self.max_devices_per_branch > 20:
            raise ValidationError(_("Max devices per branch must be between 1 and 20"))
    
    def get_api_base_url(self):
        """Obtener URL base de la API según el modo"""
        if self.is_sandbox:
            return "https://api.mercadopago.com/sandbox"
        return "https://api.mercadopago.com"
    
    def get_smartpos_api_url(self):
        """Obtener URL de la API SmartPOS"""
        if self.is_sandbox:
            return "https://api.mercadopago.com/sandbox/point"
        return "https://api.mercadopago.com/point"
    
    def get_webhook_url(self):
        """Obtener URL del webhook"""
        if self.webhook_url:
            return self.webhook_url
        return f"{settings.BASE_URL}/mercadopago/webhook/"
    
    def get_smartpos_webhook_url(self):
        """Obtener URL del webhook SmartPOS"""
        if self.smartpos_webhook_url:
            return self.smartpos_webhook_url
        return f"{settings.BASE_URL}/mercadopago/smartpos-webhook/"


class MercadoPagoDevice(models.Model):
    """
    Modelo para gestionar dispositivos SmartPOS y puntos de pago
    """
    DEVICE_TYPES = [
        ('smartpos', _('SmartPOS Terminal')),
        ('mobile_pos', _('Mobile POS')),
        ('web_checkout', _('Web Checkout')),
        ('api_integration', _('API Integration')),
    ]
    
    STATUS_CHOICES = [
        ('active', _('Active')),
        ('inactive', _('Inactive')),
        ('maintenance', _('Maintenance')),
        ('offline', _('Offline')),
        ('error', _('Error')),
    ]
    
    CONNECTION_STATUS_CHOICES = [
        ('connected', _('Connected')),
        ('disconnected', _('Disconnected')),
        ('connecting', _('Connecting')),
        ('error', _('Error')),
        ('unknown', _('Unknown')),
    ]
    
    # Identificación del dispositivo
    name = models.CharField(_("Device Name"), max_length=100)
    device_id = models.CharField(_("Device ID"), max_length=255, unique=True, blank=True)
    device_type = models.CharField(_("Device Type"), max_length=20, choices=DEVICE_TYPES)
    serial_number = models.CharField(_("Serial Number"), max_length=100, blank=True)
    
    # Relaciones
    empresa = models.ForeignKey('core.Empresa', on_delete=models.CASCADE, verbose_name=_("Company"))
    branch = models.ForeignKey('core.Branch', on_delete=models.CASCADE, verbose_name=_("Branch"))
    config = models.ForeignKey(MercadoPagoConfig, on_delete=models.CASCADE, verbose_name=_("Configuration"))
    
    # Estado y configuración
    status = models.CharField(_("Status"), max_length=20, choices=STATUS_CHOICES, default='inactive')
    is_default = models.BooleanField(_("Default Device"), default=False)
    is_active = models.BooleanField(_("Active"), default=True)
    
    # Configuración específica del dispositivo
    device_config = models.JSONField(_("Device Configuration"), default=dict, blank=True)
    supported_payment_methods = models.JSONField(_("Supported Payment Methods"), default=list, blank=True)
    
    # Información de conectividad
    last_sync = models.DateTimeField(_("Last Sync"), null=True, blank=True)
    last_transaction = models.DateTimeField(_("Last Transaction"), null=True, blank=True)
    connection_status = models.CharField(_("Connection Status"), max_length=20, choices=CONNECTION_STATUS_CHOICES, default='unknown')
    
    # Metadata
    firmware_version = models.CharField(_("Firmware Version"), max_length=50, blank=True)
    hardware_model = models.CharField(_("Hardware Model"), max_length=100, blank=True)
    location_description = models.TextField(_("Location Description"), blank=True)
    
    # Auditoría
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey('core.UsuarioExtendido', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_mercadopago_devices')
    
    class Meta:
        verbose_name = _('MercadoPago Device')
        verbose_name_plural = _('MercadoPago Devices')
        ordering = ['branch', 'name']
        unique_together = [['empresa', 'device_id']]
        indexes = [
            models.Index(fields=['empresa', 'branch']),
            models.Index(fields=['device_type', 'status']),
            models.Index(fields=['device_id']),
            models.Index(fields=['is_active', 'status']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.branch.name})"
    
    def clean(self):
        """Validaciones del modelo"""
        # Verificar que solo un dispositivo sea default por sucursal
        if self.is_default:
            MercadoPagoDevice.objects.filter(
                empresa=self.empresa,
                branch=self.branch,
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        
        # Verificar límites de dispositivos por sucursal
        if not self.pk:  # Solo para dispositivos nuevos
            device_count = MercadoPagoDevice.objects.filter(
                empresa=self.empresa,
                branch=self.branch
            ).count()
            
            if device_count >= self.config.max_devices_per_branch:
                raise ValidationError(
                    _("Maximum number of devices per branch reached")
                )
    
    def get_device_service(self):
        """Obtener servicio específico del dispositivo"""
        if self.device_type == 'smartpos':
            from mercadopago.services.smartpos_service import MercadoPagoSmartPOSService
            return MercadoPagoSmartPOSService(self)
        elif self.device_type == 'mobile_pos':
            from mercadopago.services.mobile_pos_service import MercadoPagoMobilePOSService
            return MercadoPagoMobilePOSService(self)
        else:
            from mercadopago.services.payment_service import MercadoPagoPaymentService
            return MercadoPagoPaymentService(self.config.empresa)
    
    def can_process_payment(self, amount, payment_method):
        """Verificar si el dispositivo puede procesar el pago"""
        if not self.is_active or self.status != 'active':
            return False
        
        if payment_method not in self.supported_payment_methods:
            return False
        
        # Verificar límites del dispositivo
        device_limits = self.device_config.get('limits', {})
        min_amount = device_limits.get('min_amount', 0)
        max_amount = device_limits.get('max_amount', float('inf'))
        
        if amount < min_amount or amount > max_amount:
            return False
        
        return True
    
    def update_status(self, status, connection_status=None):
        """Actualizar estado del dispositivo"""
        self.status = status
        if connection_status:
            self.connection_status = connection_status
        self.last_sync = timezone.now()
        self.save(update_fields=['status', 'connection_status', 'last_sync'])
    
    def get_transactions_today(self):
        """Obtener transacciones del día"""
        today = timezone.now().date()
        return MercadoPagoTransaction.objects.filter(
            device=self,
            created_at__date=today
        )
    
    def get_total_amount_today(self):
        """Obtener monto total de transacciones del día"""
        transactions = self.get_transactions_today()
        return transactions.aggregate(
            total=models.Sum('amount')
        )['total'] or 0


class MercadoPagoTransaction(models.Model):
    """
    Modelo para transacciones de MercadoPago
    """
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('approved', _('Approved')),
        ('authorized', _('Authorized')),
        ('in_process', _('In Process')),
        ('in_mediation', _('In Mediation')),
        ('rejected', _('Rejected')),
        ('cancelled', _('Cancelled')),
        ('refunded', _('Refunded')),
        ('charged_back', _('Chargeback')),
    ]
    
    # Identificadores
    external_reference = models.CharField(_("External Reference"), max_length=255, unique=True)
    mercadopago_id = models.CharField(_("MercadoPago ID"), max_length=255, unique=True)
    
    # Relaciones
    empresa = models.ForeignKey('core.Empresa', on_delete=models.CASCADE, verbose_name=_("Company"))
    branch = models.ForeignKey('core.Branch', on_delete=models.CASCADE, null=True, blank=True, verbose_name=_("Branch"))
    device = models.ForeignKey(MercadoPagoDevice, on_delete=models.CASCADE, null=True, blank=True, verbose_name=_("Device"))
    sale = models.ForeignKey('sales.POSSale', on_delete=models.CASCADE, null=True, blank=True, verbose_name=_("Sale"))
    invoice = models.ForeignKey('sales.Invoice', on_delete=models.CASCADE, null=True, blank=True, verbose_name=_("Invoice"))
    
    # Datos del pago
    amount = models.DecimalField(_("Amount"), max_digits=12, decimal_places=2)
    currency = models.CharField(_("Currency"), max_length=3, default='ARS')
    payment_method = models.CharField(_("Payment Method"), max_length=50)
    payment_type = models.CharField(_("Payment Type"), max_length=50)
    installments = models.IntegerField(_("Installments"), default=1)
    
    # Información del dispositivo
    device_transaction_id = models.CharField(_("Device Transaction ID"), max_length=255, blank=True)
    device_response = models.JSONField(_("Device Response"), default=dict, blank=True)
    
    # Estado y metadata
    status = models.CharField(_("Status"), max_length=20, choices=STATUS_CHOICES)
    status_detail = models.CharField(_("Status Detail"), max_length=100, blank=True)
    metadata = models.JSONField(_("Metadata"), default=dict, blank=True)
    
    # Auditoría
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_at = models.DateTimeField(_("Processed At"), null=True, blank=True)
    
    class Meta:
        verbose_name = _('MercadoPago Transaction')
        verbose_name_plural = _('MercadoPago Transactions')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['empresa', 'branch']),
            models.Index(fields=['device']),
            models.Index(fields=['status']),
            models.Index(fields=['mercadopago_id']),
            models.Index(fields=['external_reference']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Transaction {self.mercadopago_id} - {self.external_reference}"
    
    def clean(self):
        """Validaciones del modelo"""
        if self.amount <= 0:
            raise ValidationError(_("Amount must be greater than 0"))
        
        if self.installments < 1:
            raise ValidationError(_("Installments must be at least 1"))
    
    def save(self, *args, **kwargs):
        """Sobrescribir save para actualizar processed_at"""
        if self.status in ['approved', 'authorized'] and not self.processed_at:
            self.processed_at = timezone.now()
        super().save(*args, **kwargs)
    
    def get_commission_amount(self):
        """Calcular comisión de la transacción"""
        if self.device and self.device.config:
            commission_percentage = self.device.config.commission_percentage
            return (self.amount * commission_percentage) / 100
        return 0
    
    def can_be_refunded(self):
        """Verificar si la transacción puede ser reembolsada"""
        return self.status in ['approved', 'authorized']
    
    def get_status_display_color(self):
        """Obtener color para mostrar el estado"""
        status_colors = {
            'pending': 'yellow',
            'approved': 'green',
            'authorized': 'blue',
            'in_process': 'orange',
            'in_mediation': 'purple',
            'rejected': 'red',
            'cancelled': 'gray',
            'refunded': 'indigo',
            'charged_back': 'red',
        }
        return status_colors.get(self.status, 'gray') 