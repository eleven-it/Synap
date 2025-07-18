from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from core.models import Currency, UnitOfMeasure, Empresa, Branch
from core.utils.currency import convert_to_base  # Conversion helper
from django.contrib.auth import get_user_model

# ─────────────────────────────────────────────
# MODEL: Main Warehouse
# ─────────────────────────────────────────────
class Warehouse(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='warehouses', verbose_name=_('Company'))
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='warehouses', verbose_name=_('Branch'))
    name = models.CharField(_("Name"), max_length=255)
    code = models.CharField(_("Code"), max_length=20, unique=True)
    address = models.CharField(_("Address"), max_length=255, blank=True)
    is_active = models.BooleanField(_("Is Active"), default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.code} - {self.name} ({self.empresa} / {self.branch})"

    class Meta:
        verbose_name = _("Warehouse")
        verbose_name_plural = _("Warehouses")

# ─────────────────────────────────────────────
# MODEL: Physical Location
# ─────────────────────────────────────────────
class Location(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='locations', verbose_name=_('Company'))
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='locations', verbose_name=_('Branch'))
    class LocationType(models.TextChoices):
        INTERNAL = 'internal', _('Internal')
        SUPPLIER = 'supplier', _('Supplier')
        CUSTOMER = 'customer', _('Customer')
        TRANSIT = 'transit', _('In Transit')
        SCRAP = 'scrap', _('Scrap')

    name = models.CharField(_("Name"), max_length=255)
    location_type = models.CharField(
        _("Location Type"),
        max_length=20,
        choices=LocationType.choices,
        default=LocationType.INTERNAL
    )
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, null=True, blank=True, verbose_name=_("Warehouse"))
    parent_location = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, verbose_name=_("Parent Location"))
    is_active = models.BooleanField(_("Is Active"), default=True)
    allow_operations = models.BooleanField(_("Allow Operations"), default=True)

    def __str__(self):
        return f"{self.name} ({self.empresa} / {self.branch})"

    def can_receive_stock(self):
        return self.is_active and self.allow_operations
    
    class Meta:
        verbose_name = _("Location")
        verbose_name_plural = _("Locations")

# ─────────────────────────────────────────────
# MODEL: Product Brand
# ─────────────────────────────────────────────
class Brand(models.Model):
    empresa = models.ForeignKey('core.Empresa', on_delete=models.CASCADE, related_name='brands', verbose_name=_('Company'), null=True, blank=True)
    name = models.CharField(_("Name"), max_length=100, unique=True)
    is_active = models.BooleanField(_("Active"), default=True)
    adminet_id = models.IntegerField(null=True, blank=True, unique=True, help_text='ID original de administraNET para sincronización')

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = _("Brand")
        verbose_name_plural = _("Brands")
        ordering = ['name']

# ─────────────────────────────────────────────
# MODEL: Product Category
# ─────────────────────────────────────────────
class Category(models.Model):
    empresa = models.ForeignKey('core.Empresa', on_delete=models.CASCADE, related_name='categories', verbose_name=_('Company'), null=True, blank=True)
    name = models.CharField(_("Name"), max_length=100, unique=True)
    is_active = models.BooleanField(_("Active"), default=True)
    adminet_id = models.IntegerField(null=True, blank=True, unique=True, help_text='ID original de administraNET para sincronización')

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")
        ordering = ['name']

# ─────────────────────────────────────────────
# MODEL: Product Subcategory
# ─────────────────────────────────────────────
class Subcategory(models.Model):
    empresa = models.ForeignKey('core.Empresa', on_delete=models.CASCADE, related_name='subcategories', verbose_name=_('Company'), null=True, blank=True)
    name = models.CharField(_("Name"), max_length=100)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='subcategories', verbose_name=_("Category"))
    is_active = models.BooleanField(_("Active"), default=True)
    adminet_id = models.IntegerField(null=True, blank=True, unique=True, help_text='ID original de administraNET para sincronización')

    class Meta:
        unique_together = ('name', 'category')
        verbose_name = _("Subcategory")
        verbose_name_plural = _("Subcategories")
        ordering = ['category', 'name']

    def __str__(self):
        return f"{self.category.name} > {self.name}"

# ─────────────────────────────────────────────
# MODEL: Product Image
# ─────────────────────────────────────────────
class ProductImage(models.Model):
    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='images', verbose_name=_('Product'))
    image = models.ImageField(_('Image'), upload_to='products/')
    order = models.PositiveIntegerField(_('Order'), default=0)

    class Meta:
        ordering = ['order', 'id']
        verbose_name = _('Product Image')
        verbose_name_plural = _('Product Images')

    def __str__(self):
        return f"{self.product.sku} - {self.image.name}"

# ─────────────────────────────────────────────
# MODEL: Product
# ─────────────────────────────────────────────
class Product(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='products', verbose_name=_('Company'))
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='products', verbose_name=_('Branch'))
    class TrackingMethod(models.TextChoices):
        NONE = 'none', _('None')
        LOT = 'lot', _('By Lot')
        SERIAL = 'serial', _('By Serial Number')
    TYPE_CHOICES = [
        ('consumable', _('Consumable')),
        ('stockable', _('Stockable')),
        ('service', _('Service')),
        ('combo', _('Combo')),
    ]
    type = models.CharField(_('Product Type'), max_length=20, choices=TYPE_CHOICES, default='stockable')
    name = models.CharField(_("Name"), max_length=255)
    sku = models.CharField(_('SKU'), max_length=100, unique=True, blank=True, null=True)
    description = models.TextField(_("Description"), blank=True)

    category = models.ForeignKey('Category', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('Category'))
    brand = models.ForeignKey('Brand', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('Brand'))
    subcategory = models.ForeignKey('Subcategory', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('Subcategory'))

    handle = models.SlugField(_('Handle (URL)'), max_length=255, unique=True, blank=True, null=True)

    price = models.DecimalField(_("Price"), max_digits=10, decimal_places=2)
    price_currency = models.ForeignKey(Currency, on_delete=models.SET_NULL, null=True, verbose_name=_("Price Currency"))
    uom = models.ForeignKey('core.UnitOfMeasure', on_delete=models.SET_NULL, null=True, blank=True)

    tracking = models.CharField(
        _("Tracking"),
        max_length=10,
        choices=TrackingMethod.choices,
        default=TrackingMethod.NONE
    )

    weight_kg = models.DecimalField(_("Weight (kg)"), max_digits=6, decimal_places=3, null=True, blank=True)
    volume_m3 = models.DecimalField(_("Volume (m³)"), max_digits=6, decimal_places=3, null=True, blank=True)
    is_dangerous = models.BooleanField(_("Is Dangerous Good"), default=False)
    barcode = models.CharField(_("Barcode"), max_length=64, blank=True)

    tiendanube_id = models.BigIntegerField(null=True, blank=True)
    tiendanube_url = models.URLField(blank=True)
    is_published = models.BooleanField(_("Is Published"), default=True)

    width_cm = models.DecimalField(_('Width (cm)'), max_digits=6, decimal_places=2, null=True, blank=True)
    height_cm = models.DecimalField(_('Height (cm)'), max_digits=6, decimal_places=2, null=True, blank=True)
    depth_cm = models.DecimalField(_('Depth (cm)'), max_digits=6, decimal_places=2, null=True, blank=True)
    video_url = models.URLField(_('Video URL (YouTube/Vimeo)'), blank=True)
    sale_price = models.DecimalField(_('Sale Price'), max_digits=10, decimal_places=2, null=True, blank=True)
    cost_price = models.DecimalField(_('Cost Price'), max_digits=10, decimal_places=2, null=True, blank=True)
    profit_margin = models.DecimalField(_('Profit Margin (%)'), max_digits=5, decimal_places=2, null=True, blank=True)
    PRODUCT_KIND_CHOICES = [
        ('physical', _('Physical')),
        ('digital', _('Digital/Service')),
    ]
    product_kind = models.CharField(_('Product Kind'), max_length=10, choices=PRODUCT_KIND_CHOICES, default='physical')
    
    # Configuración de impuestos
    taxes = models.ManyToManyField('accounting.Tax', blank=True, related_name='products', verbose_name=_('Taxes'))
    fiscal_position = models.ForeignKey('accounting.FiscalPosition', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('Fiscal Position'))
    tax_category = models.CharField(_('Tax Category'), max_length=50, blank=True, help_text=_('Category for tax calculation (e.g., standard, reduced, zero)'))

    # Tags para categorización y sincronización
    tags = models.CharField(_('Tags'), max_length=255, blank=True, help_text=_('Comma-separated tags for categorization and sync control'))

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Product")
        verbose_name_plural = _("Products")

    def __str__(self):
        return f"{self.sku} - {self.name} ({self.empresa} / {self.branch})"

    def requires_tracking(self):
        return self.tracking in [self.TrackingMethod.LOT, self.TrackingMethod.SERIAL]

    def price_in_base_currency(self, date=None):
        if self.price_currency:
            return convert_to_base(self.price, self.price_currency, date)
        return self.price

    def save(self, *args, **kwargs):
        # Asignar la moneda de la empresa automáticamente
        if self.empresa and hasattr(self.empresa, 'currency') and self.empresa.currency:
            self.price_currency = self.empresa.currency
        super().save(*args, **kwargs)
        # Si el producto tiene tiendanube_id pero no existe mapping, crearlo automáticamente
        from tiendanube.models import TiendaNubeProductMapping
        if self.tiendanube_id:
            mapping, created = TiendaNubeProductMapping.objects.get_or_create(
                product=self,
                defaults={
                    'tiendanube_id': self.tiendanube_id,
                    'tiendanube_handle': self.handle,
                    'sync_status': TiendaNubeProductMapping.SyncStatus.PENDING,
                    'sync_enabled': True
                }
            )
            # Si ya existe y estaba en SYNCED, marcar como pendiente
            if not created and mapping.sync_status == TiendaNubeProductMapping.SyncStatus.SYNCED:
                mapping.sync_status = TiendaNubeProductMapping.SyncStatus.PENDING
                mapping.save(update_fields=["sync_status"])

# ─────────────────────────────────────────────
# MODEL: Product Attribute
# ─────────────────────────────────────────────
class ProductAttribute(models.Model):
    """Atributo de producto (ej: color, talla)"""
    name = models.CharField(max_length=64)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

# ─────────────────────────────────────────────
# MODEL: Product Attribute Value
# ─────────────────────────────────────────────
class ProductAttributeValue(models.Model):
    """Valor posible para un atributo (ej: Rojo, XL)"""
    attribute = models.ForeignKey(ProductAttribute, on_delete=models.CASCADE, related_name='values')
    value = models.CharField(max_length=64)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.attribute.name}: {self.value}"

# ─────────────────────────────────────────────
# MODEL: Product Variant
# ─────────────────────────────────────────────
class ProductVariant(models.Model):
    """Variante de producto (SKU único, combinación de atributos)"""
    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='variants')
    sku = models.CharField(max_length=64, unique=True)
    barcode = models.CharField(max_length=64, blank=True, null=True)
    attributes = models.ManyToManyField(ProductAttributeValue, blank=True, related_name='variants')
    price = models.DecimalField(max_digits=12, decimal_places=2)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.product.name} - {self.sku}"

# ─────────────────────────────────────────────
# MODEL: Stock Lot or Serial Number
# ─────────────────────────────────────────────
class StockLot(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='stocklots', verbose_name=_('Company'))
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='stocklots', verbose_name=_('Branch'))
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name=_("Product"))
    lot_number = models.CharField(_("Lot/Serial Number"), max_length=100)
    expiration_date = models.DateField(_("Expiration Date"), null=True, blank=True)

    class Meta:
        verbose_name = _("Stock Lot")
        verbose_name_plural = _("Stock Lots")

    def __str__(self):
        return f"{self.product.sku} - Lote {self.lot_number} ({self.empresa} / {self.branch})"


# ─────────────────────────────────────────────
# MODEL: Stock Quantity per Location
# ─────────────────────────────────────────────
class StockQuant(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='stockquants', verbose_name=_('Company'))
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='stockquants', verbose_name=_('Branch'))
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name=_("Product"))
    location = models.ForeignKey(Location, on_delete=models.CASCADE, verbose_name=_("Location"))
    lot = models.ForeignKey(StockLot, null=True, blank=True, on_delete=models.SET_NULL, verbose_name=_("Lot"))
    quantity = models.DecimalField(_("Quantity"), max_digits=10, decimal_places=2)
    reserved_quantity = models.DecimalField(_("Reserved Quantity"), max_digits=10, decimal_places=2, default=0)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('product', 'location', 'lot')
        verbose_name = _("Stock Quant")
        verbose_name_plural = _("Stock Quants")

    def __str__(self):
        return f"{self.product.sku} @ {self.location.name} = {self.quantity} ({self.empresa} / {self.branch})"

    @property
    def available_quantity(self):
        return max(self.quantity - self.reserved_quantity, 0)

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.reserved_quantity > self.quantity:
            raise ValidationError(_("The reserved quantity cannot be greater than the available stock."))

    def value_in_base_currency(self, date=None):
        unit_price = self.product.price_in_base_currency(date)
        return unit_price * self.quantity


# ─────────────────────────────────────────────
# MODEL: Stock Move
# ─────────────────────────────────────────────
class StockMove(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='stockmoves', verbose_name=_('Company'))
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='stockmoves', verbose_name=_('Branch'))
    class MoveType(models.TextChoices):
        INCOMING = 'incoming', _('Incoming')
        OUTGOING = 'outgoing', _('Outgoing')
        INTERNAL = 'internal', _('Internal Transfer')
        ADJUSTMENT = 'adjustment', _('Adjustment')

    class State(models.TextChoices):
        DRAFT = 'draft', _('Draft')
        CONFIRMED = 'confirmed', _('Confirmed')
        DONE = 'done', _('Done')
        CANCELLED = 'cancelled', _('Cancelled')

    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name=_("Product"))
    quantity = models.DecimalField(_("Quantity"), max_digits=10, decimal_places=2)
    from_location = models.ForeignKey(Location, related_name='moves_out', on_delete=models.CASCADE, verbose_name=_("From Location"))
    to_location = models.ForeignKey(Location, related_name='moves_in', on_delete=models.CASCADE, verbose_name=_("To Location"))
    lot = models.ForeignKey(StockLot, null=True, blank=True, on_delete=models.SET_NULL, verbose_name=_("Lot"))

    move_type = models.CharField(_("Move Type"), max_length=20, choices=MoveType.choices)
    reference = models.CharField(_("Reference"), max_length=255, blank=True)
    origin = models.CharField(_("Origin"), max_length=255, blank=True)

    state = models.CharField(_("State"), max_length=20, choices=State.choices, default=State.DRAFT)

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='stock_moves_created', on_delete=models.SET_NULL, null=True, verbose_name=_("Created By"))
    validated_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='stock_moves_validated', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Validated By"))
    validated_at = models.DateTimeField(_("Validated At"), null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _("Stock Move")
        verbose_name_plural = _("Stock Moves")

    def __str__(self):
        return f"{self.product.sku} - {self.quantity} ({self.get_state_display()}) ({self.empresa} / {self.branch})"

    def affects_stock(self):
        return self.state == self.State.DONE

    def value_in_base_currency(self, date=None):
        unit_price = self.product.price_in_base_currency(date)
        return unit_price * self.quantity

# ─────────────────────────────────────────────
# MODEL: Inventory Adjustment
# ─────────────────────────────────────────────
class InventoryAdjustment(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='inventoryadjustments', verbose_name=_('Company'))
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='inventoryadjustments', verbose_name=_('Branch'))
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name=_("Product"))
    location = models.ForeignKey(Location, on_delete=models.CASCADE, verbose_name=_("Location"))
    expected_quantity = models.DecimalField(_("Expected Quantity"), max_digits=10, decimal_places=2)
    real_quantity = models.DecimalField(_("Real Quantity"), max_digits=10, decimal_places=2)
    reason = models.TextField(_("Reason"))
    counted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name=_("Counted By"))
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = _("Inventory Adjustment")
        verbose_name_plural = _("Inventory Adjustments")

    @property
    def difference(self):
        return self.real_quantity - self.expected_quantity

    def value_difference_in_base_currency(self, date=None):
        unit_price = self.product.price_in_base_currency(date)
        return unit_price * self.difference

    def __str__(self):
        return f"{self.product.sku} - {self.location} ({self.empresa} / {self.branch})"

# ─────────────────────────────────────────────
# MODEL: Stock Reservation
# ─────────────────────────────────────────────
class StockReservation(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='stockreservations', verbose_name=_('Company'))
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='stockreservations', verbose_name=_('Branch'))
    class Status(models.TextChoices):
        ACTIVE = 'active', _('Active')
        USED = 'used', _('Used')
        CANCELLED = 'cancelled', _('Cancelled')

    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name=_("Product"))
    location = models.ForeignKey(Location, on_delete=models.CASCADE, verbose_name=_("Location"))
    quantity = models.DecimalField(_("Quantity"), max_digits=10, decimal_places=2)
    reserved_for = models.CharField(_("Reserved For"), max_length=255)  # order number, production, etc.
    status = models.CharField(_("Status"), max_length=20, choices=Status.choices, default=Status.ACTIVE)
    reserved_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _("Stock Reservation")
        verbose_name_plural = _("Stock Reservations")

    def is_active(self):
        return self.status == self.Status.ACTIVE

    def __str__(self):
        return f"{self.product.sku} - {self.location} ({self.empresa} / {self.branch})"

# ─────────────────────────────────────────────
# MODEL: Replenishment Rule
# ─────────────────────────────────────────────
class ReplenishmentRule(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='replenishmentrules', verbose_name=_('Company'))
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='replenishmentrules', verbose_name=_('Branch'))
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name=_("Product"))
    location = models.ForeignKey(Location, on_delete=models.CASCADE, verbose_name=_("Location"))
    min_quantity = models.DecimalField(_("Min Quantity"), max_digits=10, decimal_places=2)
    max_quantity = models.DecimalField(_("Max Quantity"), max_digits=10, decimal_places=2)
    method = models.CharField(_("Method"), max_length=20, default='manual')

    class Meta:
        verbose_name = _("Replenishment Rule")
        verbose_name_plural = _("Replenishment Rules")

    def needs_replenishment(self, current_quantity):
        return current_quantity < self.min_quantity

    def __str__(self):
        return f"Rule for {self.product.sku} @ {self.location.name} ({self.empresa} / {self.branch})"

class InitialStockDraft(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='initialstockdrafts', verbose_name=_('Company'))
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='initialstockdrafts', verbose_name=_('Branch'))
    ESTADO_CHOICES = [
        ('borrador', 'Borrador'),
        ('finalizado', 'Finalizado'),
        ('cancelado', 'Cancelado'),
    ]
    creado_por = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name='stockdrafts_creados')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_ultima_modificacion = models.DateTimeField(auto_now=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='borrador')
    comentario = models.TextField(blank=True)
    almacen = models.ForeignKey('Warehouse', on_delete=models.CASCADE, verbose_name='Warehouse')
    ubicacion = models.ForeignKey('Location', on_delete=models.CASCADE, verbose_name='Location')
    es_carga_masiva = models.BooleanField(default=False)
    archivo_excel = models.FileField(upload_to='stock_initial_excels/', null=True, blank=True)
    tags = models.CharField(max_length=255, blank=True)
    referencia_externa = models.CharField(max_length=255, blank=True)
    # Eliminar 'motivo' y 'adjuntos', agregar relación a documentos de respaldo
    # Para múltiples archivos, usar un modelo relacionado:
    # documentos_respaldo = models.ManyToManyField('InitialStockDraftDocument', blank=True)

    class Meta:
        verbose_name = 'Borrador de Stock Inicial'
        verbose_name_plural = 'Borradores de Stock Inicial'

    def __str__(self):
        return f"Draft {self.id} ({self.empresa} / {self.branch})"

class InitialStockDraftItem(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='initialstockdraftitems', verbose_name=_('Company'))
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='initialstockdraftitems', verbose_name=_('Branch'))
    borrador = models.ForeignKey(InitialStockDraft, on_delete=models.CASCADE, related_name='items')
    producto = models.ForeignKey('Product', on_delete=models.CASCADE)
    sku = models.CharField(max_length=100)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    lote = models.CharField(max_length=100, blank=True)
    fecha_vencimiento = models.DateField(null=True, blank=True)
    observaciones = models.TextField(blank=True)
    uom = models.ForeignKey('core.UnitOfMeasure', on_delete=models.SET_NULL, null=True, blank=True)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    ubicacion_detalle = models.ForeignKey('Location', on_delete=models.SET_NULL, null=True, blank=True, related_name='stockdraft_items')

    class Meta:
        verbose_name = 'Detalle de Borrador de Stock Inicial'
        verbose_name_plural = 'Detalles de Borrador de Stock Inicial'

    def __str__(self):
        return f"DraftItem {self.id} ({self.empresa} / {self.branch})"

class InitialStockDraftDocument(models.Model):
    borrador = models.ForeignKey(InitialStockDraft, on_delete=models.CASCADE, related_name='documentos_respaldo')
    archivo = models.FileField(upload_to='stock_initial_attachments/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return self.archivo.name

# ─────────────────────────────────────────────
# MODEL: Product Combo Item
# ─────────────────────────────────────────────
class ProductComboItem(models.Model):
    combo = models.ForeignKey(Product, related_name='combo_items', limit_choices_to={'type': 'combo'}, on_delete=models.CASCADE)
    component = models.ForeignKey(Product, related_name='as_component', limit_choices_to={'type__in': ['consumable', 'stockable']}, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    class Meta:
        verbose_name = _('Combo Component')
        verbose_name_plural = _('Combo Components')
        unique_together = ('combo', 'component')
    def __str__(self):
        return f"{self.combo} - {self.component} x {self.quantity}"



