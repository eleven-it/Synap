from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from inventory.models import Product, ProductVariant, StockQuant, Location, Warehouse, StockMove

# ─────────────────────────────────────────────
# TiendaNube Integration Models
# ─────────────────────────────────────────────

class TiendaNubeConfig(models.Model):
    """Main TiendaNube Configuration"""
    store_id = models.CharField(max_length=50, unique=True)
    access_token = models.CharField(max_length=255)
    webhook_secret = models.CharField(max_length=255, blank=True)
    api_url = models.URLField(default="https://api.tiendanube.com/v1")
    auto_sync = models.BooleanField(_("Auto Sync"), default=True)
    sync_interval = models.IntegerField(_("Sync Interval"), default=30, help_text=_("Interval in minutes for auto-sync."))
    last_sync = models.DateTimeField(_("Last Sync"), null=True, blank=True)
    sync_products = models.BooleanField(_("Sync Products"), default=True)
    sync_stock = models.BooleanField(_("Sync Stock"), default=True)
    sync_variants = models.BooleanField(_("Sync Variants"), default=True)
    webhook_url = models.URLField(blank=True)
    webhook_active = models.BooleanField(_("Webhook Active"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        verbose_name = _("TiendaNube Configuration")
        verbose_name_plural = _("TiendaNube Configurations")
    def __str__(self):
        return f"TiendaNube Config for Store ID: {self.store_id}"
    @property
    def is_configured(self):
        return self.store_id and self.access_token
    def get_api_headers(self):
        return {
            "Content-Type": "application/json",
            "Authentication": f"bearer {self.access_token}",
            "User-Agent": f"Synap (https://synap.com.ar)"
        }

class TiendaNubeSyncLog(models.Model):
    class SyncType(models.TextChoices):
        PRODUCT = 'product', _('Product')
        STOCK = 'stock', _('Stock')
        VARIANT = 'variant', _('Variant')
        WEBHOOK = 'webhook', _('Webhook')
        FULL = 'full', _('Full Sync')
    class Status(models.TextChoices):
        SUCCESS = 'success', _('Success')
        ERROR = 'error', _('Error')
        PARTIAL = 'partial', _('Partial')
    config = models.ForeignKey(TiendaNubeConfig, on_delete=models.CASCADE)
    sync_type = models.CharField(_("Sync Type"), max_length=20, choices=SyncType.choices)
    status = models.CharField(_("Status"), max_length=20, choices=Status.choices)
    message = models.TextField(_("Message"))
    details = models.JSONField(default=dict, blank=True)
    items_processed = models.IntegerField(default=0)
    items_success = models.IntegerField(default=0)
    items_failed = models.IntegerField(default=0)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        ordering = ['-started_at']
        verbose_name = _("TiendaNube Sync Log")
        verbose_name_plural = _("TiendaNube Sync Logs")
    def __str__(self):
        return f"{self.get_sync_type_display()} on {self.started_at.strftime('%Y-%m-%d')} - {self.get_status_display()}"
    @property
    def duration(self):
        if self.completed_at:
            return self.completed_at - self.started_at
        return None

class TiendaNubeProductMapping(models.Model):
    class SyncStatus(models.TextChoices):
        SYNCED = 'synced', _('Synced')
        PENDING = 'pending', _('Pending')
        ERROR = 'error', _('Error')
        CONFLICT = 'conflict', _('Conflict')
    product = models.OneToOneField(Product, on_delete=models.CASCADE)
    tiendanube_id = models.BigIntegerField(unique=True)
    tiendanube_variant_id = models.BigIntegerField(null=True, blank=True)
    tiendanube_handle = models.CharField(max_length=255, blank=True)
    last_synced = models.DateTimeField(auto_now=True)
    sync_status = models.CharField(_("Sync Status"), max_length=20, choices=SyncStatus.choices, default=SyncStatus.PENDING)
    sync_enabled = models.BooleanField(_("Sync Enabled"), default=True)
    sync_price = models.BooleanField(_("Sync Price"), default=True)
    sync_stock = models.BooleanField(_("Sync Stock"), default=True)
    sync_description = models.BooleanField(_("Sync Description"), default=True)
    error_message = models.TextField(blank=True)
    class Meta:
        verbose_name = _("TiendaNube Product Mapping")
        verbose_name_plural = _("TiendaNube Product Mappings")
    def __str__(self):
        return f"Mapping for {self.product.sku} <-> TN ID {self.tiendanube_id}"
    @property
    def needs_sync(self):
        return self.sync_enabled and self.sync_status != self.SyncStatus.SYNCED
