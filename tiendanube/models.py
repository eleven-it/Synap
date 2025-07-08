from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from inventory.models import Product, ProductVariant, StockQuant, Location, Warehouse, StockMove
from sales.models import Client, SalesOrder, SalesOrderLine
from decimal import Decimal

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
    sync_orders = models.BooleanField(_("Sync Orders"), default=True)
    sync_customers = models.BooleanField(_("Sync Customers"), default=True)
    webhook_url = models.URLField(blank=True)
    webhook_active = models.BooleanField(_("Webhook Active"), default=True)
    
    # Almacén dedicado para Tiendanube
    tiendanube_warehouse = models.ForeignKey(
        Warehouse, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name=_("Tiendanube Warehouse"),
        help_text=_("Warehouse dedicated to Tiendanube stock management")
    )
    
    # Configuración de reabastecimiento
    auto_restock = models.BooleanField(_("Auto Restock"), default=True)
    restock_threshold = models.DecimalField(
        _("Restock Threshold"), 
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('5.00'),
        help_text=_("Minimum stock level to trigger auto restock")
    )
    restock_quantity = models.DecimalField(
        _("Restock Quantity"), 
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('20.00'),
        help_text=_("Quantity to restock when threshold is reached")
    )
    
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
            "User-Agent": "administranet_tiendanube - tiendanube@administranet.com.ar"
        }

class TiendaNubeSyncLog(models.Model):
    class SyncType(models.TextChoices):
        PRODUCT = 'product', _('Product')
        STOCK = 'stock', _('Stock')
        VARIANT = 'variant', _('Variant')
        ORDER = 'order', _('Order')
        CUSTOMER = 'customer', _('Customer')
        WEBHOOK = 'webhook', _('Webhook')
        RESTOCK = 'restock', _('Restock')
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
    
    # Campos para reabastecimiento
    restock_enabled = models.BooleanField(_("Auto Restock Enabled"), default=True)
    restock_threshold = models.DecimalField(
        _("Restock Threshold"), 
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text=_("Override global threshold for this product")
    )
    restock_quantity = models.DecimalField(
        _("Restock Quantity"), 
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text=_("Override global quantity for this product")
    )
    
    class Meta:
        verbose_name = _("TiendaNube Product Mapping")
        verbose_name_plural = _("TiendaNube Product Mappings")
    
    def __str__(self):
        return f"Mapping for {self.product.sku} <-> TN ID {self.tiendanube_id}"
    
    @property
    def needs_sync(self):
        return self.sync_enabled and self.sync_status != self.SyncStatus.SYNCED

class TiendaNubeCustomerMapping(models.Model):
    """Mapping entre clientes de Synap y Tiendanube"""
    class SyncStatus(models.TextChoices):
        SYNCED = 'synced', _('Synced')
        PENDING = 'pending', _('Pending')
        ERROR = 'error', _('Error')
        CONFLICT = 'conflict', _('Conflict')
    
    client = models.OneToOneField(Client, on_delete=models.CASCADE)
    tiendanube_id = models.BigIntegerField(unique=True)
    tiendanube_email = models.EmailField(blank=True)
    tiendanube_document = models.CharField(max_length=50, blank=True)
    last_synced = models.DateTimeField(auto_now=True)
    sync_status = models.CharField(_("Sync Status"), max_length=20, choices=SyncStatus.choices, default=SyncStatus.PENDING)
    sync_enabled = models.BooleanField(_("Sync Enabled"), default=True)
    error_message = models.TextField(blank=True)
    
    class Meta:
        verbose_name = _("TiendaNube Customer Mapping")
        verbose_name_plural = _("TiendaNube Customer Mappings")
    
    def __str__(self):
        return f"Customer {self.client.name} <-> TN ID {self.tiendanube_id}"

class TiendaNubeOrderMapping(models.Model):
    """Mapping entre órdenes de venta de Synap y pedidos de Tiendanube"""
    class SyncStatus(models.TextChoices):
        SYNCED = 'synced', _('Synced')
        PENDING = 'pending', _('Pending')
        ERROR = 'error', _('Error')
        CONFLICT = 'conflict', _('Conflict')
    
    sales_order = models.OneToOneField(SalesOrder, on_delete=models.CASCADE)
    tiendanube_order_id = models.BigIntegerField(unique=True)
    tiendanube_order_number = models.CharField(max_length=50, blank=True)
    order_source = models.CharField(max_length=50, default="Tiendanube")
    payment_method = models.CharField(max_length=100, blank=True)
    payment_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    last_synced = models.DateTimeField(auto_now=True)
    sync_status = models.CharField(_("Sync Status"), max_length=20, choices=SyncStatus.choices, default=SyncStatus.PENDING)
    error_message = models.TextField(blank=True)
    
    class Meta:
        verbose_name = _("TiendaNube Order Mapping")
        verbose_name_plural = _("TiendaNube Order Mappings")
    
    def __str__(self):
        return f"Order {self.sales_order.number} <-> TN Order {self.tiendanube_order_id}"

class TiendaNubeRestockRule(models.Model):
    """Reglas de reabastecimiento por producto o categoría"""
    class RuleType(models.TextChoices):
        PRODUCT = 'product', _('Product')
        CATEGORY = 'category', _('Category')
        GLOBAL = 'global', _('Global')
    
    class ActionType(models.TextChoices):
        TRANSFER = 'transfer', _('Internal Transfer')
        PURCHASE = 'purchase', _('Purchase Order')
        NOTIFICATION = 'notification', _('Notification Only')
    
    name = models.CharField(_("Rule Name"), max_length=100)
    rule_type = models.CharField(_("Rule Type"), max_length=20, choices=RuleType.choices)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)
    category = models.ForeignKey('inventory.Category', on_delete=models.CASCADE, null=True, blank=True)
    action_type = models.CharField(_("Action Type"), max_length=20, choices=ActionType.choices)
    
    # Configuración de stock
    threshold = models.DecimalField(_("Threshold"), max_digits=10, decimal_places=2)
    restock_quantity = models.DecimalField(_("Restock Quantity"), max_digits=10, decimal_places=2)
    
    # Configuración de transferencia
    source_warehouse = models.ForeignKey(
        Warehouse, 
        on_delete=models.CASCADE, 
        related_name='restock_source_rules',
        null=True, 
        blank=True
    )
    destination_warehouse = models.ForeignKey(
        Warehouse, 
        on_delete=models.CASCADE, 
        related_name='restock_destination_rules',
        null=True, 
        blank=True
    )
    
    # Configuración de notificaciones
    notify_email = models.EmailField(blank=True)
    notify_users = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True)
    
    is_active = models.BooleanField(_("Active"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("TiendaNube Restock Rule")
        verbose_name_plural = _("TiendaNube Restock Rules")
    
    def __str__(self):
        return f"{self.name} ({self.get_rule_type_display()})"

class TiendaNubeRestockLog(models.Model):
    """Log de acciones de reabastecimiento"""
    class ActionType(models.TextChoices):
        TRANSFER = 'transfer', _('Internal Transfer')
        PURCHASE = 'purchase', _('Purchase Order')
        NOTIFICATION = 'notification', _('Notification')
    
    class Status(models.TextChoices):
        PENDING = 'pending', _('Pending')
        COMPLETED = 'completed', _('Completed')
        FAILED = 'failed', _('Failed')
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    rule = models.ForeignKey(TiendaNubeRestockRule, on_delete=models.CASCADE, null=True, blank=True)
    action_type = models.CharField(_("Action Type"), max_length=20, choices=ActionType.choices)
    status = models.CharField(_("Status"), max_length=20, choices=Status.choices, default=Status.PENDING)
    
    # Detalles de la acción
    quantity_requested = models.DecimalField(_("Quantity Requested"), max_digits=10, decimal_places=2)
    quantity_processed = models.DecimalField(_("Quantity Processed"), max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Referencias a documentos creados
    stock_move = models.ForeignKey(StockMove, on_delete=models.SET_NULL, null=True, blank=True)
    purchase_order = models.ForeignKey('purchases.PurchaseOrder', on_delete=models.SET_NULL, null=True, blank=True)
    
    message = models.TextField(blank=True)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = _("TiendaNube Restock Log")
        verbose_name_plural = _("TiendaNube Restock Logs")
    
    def __str__(self):
        return f"Restock {self.product.sku} - {self.get_action_type_display()} ({self.get_status_display()})"
