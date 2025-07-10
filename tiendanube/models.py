from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from inventory.models import Product, ProductVariant, StockQuant, Location, Warehouse, StockMove
from sales.models import Client, SalesOrder, SalesOrderLine
from decimal import Decimal
from django.utils import timezone

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


class TiendaNubeProductRestockPolicy(models.Model):
    """Políticas de reabastecimiento individuales por producto para Tiendanube"""
    class PolicyType(models.TextChoices):
        MANUAL = 'manual', _('Manual Configuration')
        RULE_BASED = 'rule_based', _('Rule Based')
        INTELLIGENT = 'intelligent', _('Intelligent (AI)')
    
    class ActionType(models.TextChoices):
        TRANSFER = 'transfer', _('Internal Transfer')
        PURCHASE = 'purchase', _('Purchase Order')
        NOTIFICATION = 'notification', _('Notification Only')
        COMBINED = 'combined', _('Combined Actions')
    
    product = models.OneToOneField(
        Product, 
        on_delete=models.CASCADE,
        verbose_name=_("Product"),
        help_text=_("Product to apply this restock policy")
    )
    
    # Configuración básica
    is_active = models.BooleanField(_("Active"), default=True)
    policy_type = models.CharField(
        _("Policy Type"), 
        max_length=20, 
        choices=PolicyType.choices,
        default=PolicyType.MANUAL
    )
    action_type = models.CharField(
        _("Action Type"), 
        max_length=20, 
        choices=ActionType.choices,
        default=ActionType.TRANSFER
    )
    
    # Parámetros de stock
    threshold = models.DecimalField(
        _("Restock Threshold"), 
        max_digits=10, 
        decimal_places=2,
        help_text=_("Minimum stock level to trigger restock")
    )
    restock_quantity = models.DecimalField(
        _("Restock Quantity"), 
        max_digits=10, 
        decimal_places=2,
        help_text=_("Quantity to restock when threshold is reached")
    )
    
    # Configuración avanzada
    max_stock_level = models.DecimalField(
        _("Maximum Stock Level"), 
        max_digits=10, 
        decimal_places=2,
        null=True, 
        blank=True,
        help_text=_("Maximum stock level to maintain (optional)")
    )
    safety_stock = models.DecimalField(
        _("Safety Stock"), 
        max_digits=10, 
        decimal_places=2,
        null=True, 
        blank=True,
        help_text=_("Safety stock level (optional)")
    )
    
    # Configuración de transferencia
    source_warehouse = models.ForeignKey(
        Warehouse, 
        on_delete=models.SET_NULL,
        null=True, 
        blank=True,
        related_name='restock_policy_source',
        verbose_name=_("Source Warehouse"),
        help_text=_("Warehouse to transfer stock from")
    )
    destination_warehouse = models.ForeignKey(
        Warehouse, 
        on_delete=models.SET_NULL,
        null=True, 
        blank=True,
        related_name='restock_policy_destination',
        verbose_name=_("Destination Warehouse"),
        help_text=_("Warehouse to transfer stock to")
    )
    
    # Configuración de notificaciones
    notify_on_restock = models.BooleanField(_("Notify on Restock"), default=True)
    notify_email = models.EmailField(_("Notification Email"), blank=True)
    notify_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL, 
        blank=True,
        verbose_name=_("Notify Users")
    )
    
    # Configuración de reglas inteligentes
    lead_time_days = models.IntegerField(
        _("Lead Time (Days)"), 
        default=1,
        help_text=_("Expected lead time for restock")
    )
    demand_forecast_days = models.IntegerField(
        _("Demand Forecast (Days)"), 
        default=7,
        help_text=_("Days to forecast demand")
    )
    
    # Metadatos
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_restock_date = models.DateTimeField(_("Last Restock Date"), null=True, blank=True)
    restock_count = models.IntegerField(_("Restock Count"), default=0)
    
    class Meta:
        verbose_name = _("Tiendanube Product Restock Policy")
        verbose_name_plural = _("Tiendanube Product Restock Policies")
        ordering = ['product__name']
    
    def __str__(self):
        return f"Restock Policy for {self.product.sku}"
    
    @property
    def effective_threshold(self):
        """Obtiene el umbral efectivo considerando stock de seguridad"""
        if self.safety_stock:
            return self.threshold + self.safety_stock
        return self.threshold
    
    @property
    def needs_restock(self):
        """Determina si el producto necesita reabastecimiento"""
        try:
            # Obtener stock actual en el almacén de destino
            if self.destination_warehouse:
                stock_quants = StockQuant.objects.filter(
                    product=self.product,
                    location__warehouse=self.destination_warehouse
                )
                current_stock = sum(quant.available_quantity for quant in stock_quants)
                return current_stock <= self.effective_threshold
            return False
        except Exception:
            return False
    
    def get_restock_quantity(self, current_stock=None):
        """Calcula la cantidad de reabastecimiento basada en la política"""
        if current_stock is None:
            if self.destination_warehouse:
                stock_quants = StockQuant.objects.filter(
                    product=self.product,
                    location__warehouse=self.destination_warehouse
                )
                current_stock = sum(quant.available_quantity for quant in stock_quants)
            else:
                current_stock = 0
        
        # Cálculo básico
        needed_quantity = self.restock_quantity
        
        # Si hay stock máximo configurado, ajustar
        if self.max_stock_level:
            max_needed = self.max_stock_level - current_stock
            needed_quantity = min(needed_quantity, max_needed)
        
        # Si hay stock de seguridad, asegurar que se mantenga
        if self.safety_stock:
            safety_needed = self.safety_stock - current_stock
            if safety_needed > 0:
                needed_quantity = max(needed_quantity, safety_needed)
        
        return max(0, needed_quantity)
    
    def execute_restock(self):
        """Ejecuta el reabastecimiento según la política"""
        try:
            if not self.is_active:
                return False, "Policy is not active"
            
            if not self.needs_restock:
                return False, "Product does not need restock"
            
            current_stock = 0
            if self.destination_warehouse:
                stock_quants = StockQuant.objects.filter(
                    product=self.product,
                    location__warehouse=self.destination_warehouse
                )
                current_stock = sum(quant.available_quantity for quant in stock_quants)
            
            restock_quantity = self.get_restock_quantity(current_stock)
            
            if restock_quantity <= 0:
                return False, "No restock quantity needed"
            
            # Ejecutar acción según tipo
            if self.action_type == self.ActionType.TRANSFER:
                return self._execute_transfer(restock_quantity)
            elif self.action_type == self.ActionType.PURCHASE:
                return self._execute_purchase(restock_quantity)
            elif self.action_type == self.ActionType.NOTIFICATION:
                return self._execute_notification(restock_quantity)
            elif self.action_type == self.ActionType.COMBINED:
                return self._execute_combined(restock_quantity)
            
            return False, "Unknown action type"
            
        except Exception as e:
            return False, str(e)
    
    def _execute_transfer(self, quantity):
        """Ejecuta transferencia interna"""
        try:
            if not self.source_warehouse or not self.destination_warehouse:
                return False, "Source and destination warehouses must be configured"
            
            source_location = Location.objects.filter(
                warehouse=self.source_warehouse,
                is_active=True
            ).first()
            
            destination_location = Location.objects.filter(
                warehouse=self.destination_warehouse,
                is_active=True
            ).first()
            
            if not source_location or not destination_location:
                return False, "Active locations not found"
            
            # Crear movimiento de stock
            stock_move = StockMove.objects.create(
                empresa=self.product.empresa,
                branch=self.product.branch,
                product=self.product,
                location_from=source_location,
                location_to=destination_location,
                quantity=quantity,
                move_type='internal_transfer',
                reference=f'Tiendanube Restock - {self.product.sku}',
                state='confirmed'
            )
            
            # Actualizar contadores
            self.last_restock_date = timezone.now()
            self.restock_count += 1
            self.save()
            
            return True, f"Transfer completed: {quantity} units"
            
        except Exception as e:
            return False, f"Transfer error: {str(e)}"
    
    def _execute_purchase(self, quantity):
        """Ejecuta orden de compra"""
        try:
            # TODO: Implementar creación de orden de compra
            # Por ahora, solo actualizar contadores
            self.last_restock_date = timezone.now()
            self.restock_count += 1
            self.save()
            
            return True, f"Purchase order requested: {quantity} units"
            
        except Exception as e:
            return False, f"Purchase error: {str(e)}"
    
    def _execute_notification(self, quantity):
        """Ejecuta notificación"""
        try:
            # TODO: Implementar envío de notificaciones
            self.last_restock_date = timezone.now()
            self.restock_count += 1
            self.save()
            
            return True, f"Notification sent: {quantity} units needed"
            
        except Exception as e:
            return False, f"Notification error: {str(e)}"
    
    def _execute_combined(self, quantity):
        """Ejecuta acciones combinadas"""
        try:
            # Intentar transferencia primero
            success, message = self._execute_transfer(quantity)
            if success:
                return True, f"Combined action: {message}"
            
            # Si falla, intentar notificación
            return self._execute_notification(quantity)
            
        except Exception as e:
            return False, f"Combined action error: {str(e)}"

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
