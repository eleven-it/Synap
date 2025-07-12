from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.core.exceptions import ValidationError
import json
import uuid


class CloverDevice(models.Model):
    """
    Dispositivo Clover - Terminal físico o virtual
    """
    DEVICE_TYPES = [
        ('station', _('Clover Station')),
        ('mini', _('Clover Mini')),
        ('flex', _('Clover Flex')),
        ('go', _('Clover Go')),
        ('mobile', _('Clover Mobile')),
        ('virtual', _('Virtual Terminal')),
    ]
    
    DEVICE_STATUS = [
        ('active', _('Active')),
        ('inactive', _('Inactive')),
        ('maintenance', _('Maintenance')),
        ('offline', _('Offline')),
    ]
    
    # Identificación única
    device_id = models.CharField(_("Device ID"), max_length=255, unique=True)
    serial_number = models.CharField(_("Serial Number"), max_length=255, blank=True)
    device_type = models.CharField(_("Device Type"), max_length=20, choices=DEVICE_TYPES)
    
    # Configuración de empresa y sucursal (multiempresa/multisucursal)
    empresa = models.ForeignKey('core.Empresa', on_delete=models.PROTECT, verbose_name=_("Company"))
    branch = models.ForeignKey('core.Branch', on_delete=models.PROTECT, verbose_name=_("Branch"))
    
    # Configuración de Clover
    merchant_id = models.CharField(_("Merchant ID"), max_length=255)
    api_token = models.CharField(_("API Token"), max_length=500)
    app_id = models.CharField(_("App ID"), max_length=255, blank=True)
    
    # Estado y configuración
    status = models.CharField(_("Status"), max_length=20, choices=DEVICE_STATUS, default='active')
    is_active = models.BooleanField(_("Active"), default=True)
    is_default = models.BooleanField(_("Default Device"), default=False)
    
    # Configuración de pagos
    supports_contactless = models.BooleanField(_("Supports Contactless"), default=True)
    supports_chip = models.BooleanField(_("Supports Chip"), default=True)
    supports_magnetic_stripe = models.BooleanField(_("Supports Magnetic Stripe"), default=True)
    supports_manual_entry = models.BooleanField(_("Supports Manual Entry"), default=True)
    
    # Configuración de impresión
    supports_receipt_printing = models.BooleanField(_("Supports Receipt Printing"), default=True)
    supports_signature_capture = models.BooleanField(_("Supports Signature Capture"), default=True)
    
    # Configuración adicional
    config = models.JSONField(_("Configuration"), default=dict, blank=True)
    notes = models.TextField(_("Notes"), blank=True)
    
    # Auditoría
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='clover_devices_created')
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='clover_devices_updated')
    
    class Meta:
        verbose_name = _('Clover Device')
        verbose_name_plural = _('Clover Devices')
        ordering = ['-created_at']
        unique_together = ['empresa', 'device_id']
    
    def __str__(self):
        return f"{self.get_device_type_display()} - {self.device_id} ({self.branch.name})"
    
    def clean(self):
        """Validaciones personalizadas"""
        if self.is_default:
            # Solo un dispositivo por defecto por sucursal
            existing_default = CloverDevice.objects.filter(
                empresa=self.empresa,
                branch=self.branch,
                is_default=True
            ).exclude(pk=self.pk)
            
            if existing_default.exists():
                raise ValidationError(_('Only one default device per branch is allowed.'))
    
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class CloverTransaction(models.Model):
    """
    Transacción procesada por Clover
    """
    TRANSACTION_TYPES = [
        ('sale', _('Sale')),
        ('refund', _('Refund')),
        ('void', _('Void')),
        ('preauth', _('Pre-authorization')),
        ('capture', _('Capture')),
    ]
    
    TRANSACTION_STATUS = [
        ('pending', _('Pending')),
        ('approved', _('Approved')),
        ('declined', _('Declined')),
        ('error', _('Error')),
        ('cancelled', _('Cancelled')),
        ('voided', _('Voided')),
    ]
    
    # Identificación única
    transaction_id = models.CharField(_("Transaction ID"), max_length=255, unique=True)
    clover_transaction_id = models.CharField(_("Clover Transaction ID"), max_length=255, blank=True)
    
    # Relaciones con empresa y sucursal
    empresa = models.ForeignKey('core.Empresa', on_delete=models.PROTECT, verbose_name=_("Company"))
    branch = models.ForeignKey('core.Branch', on_delete=models.PROTECT, verbose_name=_("Branch"))
    
    # Dispositivo y operador
    device = models.ForeignKey(CloverDevice, on_delete=models.PROTECT, verbose_name=_("Device"))
    operator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, verbose_name=_("Operator"))
    
    # Información de la transacción
    transaction_type = models.CharField(_("Transaction Type"), max_length=20, choices=TRANSACTION_TYPES)
    status = models.CharField(_("Status"), max_length=20, choices=TRANSACTION_STATUS, default='pending')
    
    # Montos
    amount = models.DecimalField(_("Amount"), max_digits=12, decimal_places=2)
    tip_amount = models.DecimalField(_("Tip Amount"), max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField(_("Tax Amount"), max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(_("Total Amount"), max_digits=12, decimal_places=2)
    
    # Información de pago
    payment_method = models.CharField(_("Payment Method"), max_length=50, blank=True)
    card_type = models.CharField(_("Card Type"), max_length=50, blank=True)
    last_four_digits = models.CharField(_("Last Four Digits"), max_length=4, blank=True)
    
    # Información del cliente
    customer_name = models.CharField(_("Customer Name"), max_length=255, blank=True)
    customer_email = models.EmailField(_("Customer Email"), blank=True)
    
    # Respuesta de Clover
    clover_response = models.JSONField(_("Clover Response"), default=dict, blank=True)
    error_message = models.TextField(_("Error Message"), blank=True)
    
    # Información adicional
    external_reference = models.CharField(_("External Reference"), max_length=255, blank=True)
    notes = models.TextField(_("Notes"), blank=True)
    
    # Auditoría
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Clover Transaction')
        verbose_name_plural = _('Clover Transactions')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.transaction_id} - {self.get_transaction_type_display()} - {self.total_amount}"
    
    @property
    def is_successful(self):
        """Verificar si la transacción fue exitosa"""
        return self.status == 'approved'
    
    @property
    def can_be_refunded(self):
        """Verificar si la transacción puede ser reembolsada"""
        return (self.is_successful and 
                self.transaction_type == 'sale' and
                self.status not in ['voided', 'cancelled'])


class CloverConfiguration(models.Model):
    """
    Configuración global de Clover para la empresa
    """
    empresa = models.OneToOneField('core.Empresa', on_delete=models.CASCADE, verbose_name=_("Company"))
    
    # Configuración de API
    api_base_url = models.URLField(_("API Base URL"), default="https://api.clover.com")
    api_version = models.CharField(_("API Version"), max_length=10, default="v3")
    
    # Configuración de pagos
    default_currency = models.CharField(_("Default Currency"), max_length=3, default="ARS")
    supported_currencies = models.JSONField(_("Supported Currencies"), default=list)
    
    # Configuración de seguridad
    webhook_secret = models.CharField(_("Webhook Secret"), max_length=255, blank=True)
    webhook_url = models.URLField(_("Webhook URL"), blank=True)
    
    # Configuración de notificaciones
    send_email_notifications = models.BooleanField(_("Send Email Notifications"), default=True)
    notification_email = models.EmailField(_("Notification Email"), blank=True)
    
    # Configuración adicional
    config = models.JSONField(_("Additional Configuration"), default=dict, blank=True)
    
    # Auditoría
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Clover Configuration')
        verbose_name_plural = _('Clover Configurations')
    
    def __str__(self):
        return f"Clover Configuration - {self.empresa.name}"
    
    def get_api_url(self, endpoint=""):
        """Obtener URL completa de la API"""
        return f"{self.api_base_url}/{self.api_version}/{endpoint.lstrip('/')}"


class CloverWebhook(models.Model):
    """
    Webhooks recibidos de Clover
    """
    webhook_id = models.CharField(_("Webhook ID"), max_length=255, unique=True)
    
    # Información del webhook
    event_type = models.CharField(_("Event Type"), max_length=100)
    event_data = models.JSONField(_("Event Data"), default=dict)
    
    # Estado de procesamiento
    processed = models.BooleanField(_("Processed"), default=False)
    processing_error = models.TextField(_("Processing Error"), blank=True)
    
    # Auditoría
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = _('Clover Webhook')
        verbose_name_plural = _('Clover Webhooks')
        ordering = ['-received_at']
    
    def __str__(self):
        return f"{self.event_type} - {self.webhook_id}" 