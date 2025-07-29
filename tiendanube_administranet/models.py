from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class TiendanubeConfig(models.Model):
    """
    Configuración de conexión con Tiendanube.
    """
    name = models.CharField(max_length=100, verbose_name=_("Configuration Name"))
    store_id = models.CharField(max_length=50, unique=True, verbose_name=_("Store ID"))
    access_token = models.CharField(max_length=255, verbose_name=_("Access Token"))
    api_url = models.URLField(default="https://api.tiendanube.com/v1", verbose_name=_("API URL"))
    is_active = models.BooleanField(default=True, verbose_name=_("Active"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        verbose_name = _("Tiendanube Configuration")
        verbose_name_plural = _("Tiendanube Configurations")
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.store_id})"


class AdministraNETConfig(models.Model):
    """
    Configuración de conexión con AdministraNET.
    """
    name = models.CharField(max_length=100, verbose_name=_("Configuration Name"))
    host = models.CharField(max_length=255, verbose_name=_("Host"))
    port = models.IntegerField(default=3306, verbose_name=_("Port"))
    database = models.CharField(max_length=255, verbose_name=_("Database"))
    user = models.CharField(max_length=255, verbose_name=_("User"))
    password = models.CharField(max_length=255, verbose_name=_("Password"))
    is_active = models.BooleanField(default=True, verbose_name=_("Active"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        verbose_name = _("AdministraNET Configuration")
        verbose_name_plural = _("AdministraNET Configurations")
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.host}:{self.port}/{self.database})"


class CustomerMapping(models.Model):
    """
    Mapeo entre clientes de Tiendanube y AdministraNET.
    """
    class SyncStatus(models.TextChoices):
        SYNCED = 'synced', _('Synced')
        PENDING = 'pending', _('Pending')
        ERROR = 'error', _('Error')
        CONFLICT = 'conflict', _('Conflict')

    class SyncDirection(models.TextChoices):
        BIDIRECTIONAL = 'bidirectional', _('Bidirectional')
        TIENDANUBE_TO_ADMINET = 'tiendanube_to_adminet', _('Tiendanube → AdministraNET')
        ADMINET_TO_TIENDANUBE = 'adminet_to_tiendanube', _('AdministraNET → Tiendanube')

    # Campos de Tiendanube (según documentación oficial)
    tiendanube_id = models.BigIntegerField(unique=True, null=True, blank=True, verbose_name=_("Tiendanube ID"))
    tiendanube_email = models.EmailField(unique=True, verbose_name=_("Tiendanube Email"))
    tiendanube_name = models.CharField(max_length=255, blank=True, verbose_name=_("Tiendanube Name"))
    tiendanube_first_name = models.CharField(max_length=100, blank=True, verbose_name=_("Tiendanube First Name"))
    tiendanube_last_name = models.CharField(max_length=100, blank=True, verbose_name=_("Tiendanube Last Name"))
    tiendanube_document = models.CharField(max_length=50, blank=True, verbose_name=_("Tiendanube Document"))
    tiendanube_phone = models.CharField(max_length=50, blank=True, verbose_name=_("Tiendanube Phone"))
    tiendanube_address = models.TextField(blank=True, verbose_name=_("Tiendanube Address"))
    tiendanube_city = models.CharField(max_length=100, blank=True, verbose_name=_("Tiendanube City"))
    tiendanube_state = models.CharField(max_length=100, blank=True, verbose_name=_("Tiendanube State"))
    tiendanube_country = models.CharField(max_length=100, blank=True, verbose_name=_("Tiendanube Country"))
    tiendanube_postal_code = models.CharField(max_length=20, blank=True, verbose_name=_("Tiendanube Postal Code"))
    tiendanube_notes = models.TextField(blank=True, verbose_name=_("Tiendanube Notes"))
    tiendanube_tags = models.JSONField(default=list, blank=True, verbose_name=_("Tiendanube Tags"))
    tiendanube_accepts_marketing = models.BooleanField(default=False, verbose_name=_("Tiendanube Accepts Marketing"))
    tiendanube_total_spent = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name=_("Tiendanube Total Spent"))
    tiendanube_orders_count = models.IntegerField(default=0, verbose_name=_("Tiendanube Orders Count"))
    tiendanube_last_order_id = models.BigIntegerField(null=True, blank=True, verbose_name=_("Tiendanube Last Order ID"))
    tiendanube_verified_email = models.BooleanField(default=False, verbose_name=_("Tiendanube Verified Email"))
    tiendanube_multipass_identifier = models.CharField(max_length=255, blank=True, verbose_name=_("Tiendanube Multipass Identifier"))
    tiendanube_tax_exempt = models.BooleanField(default=False, verbose_name=_("Tiendanube Tax Exempt"))
    tiendanube_tax_exemptions = models.JSONField(default=list, blank=True, verbose_name=_("Tiendanube Tax Exemptions"))
    tiendanube_created_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Tiendanube Created At"))
    tiendanube_updated_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Tiendanube Updated At"))

    # Campos de AdministraNET
    adminet_codigo = models.IntegerField(null=True, blank=True, verbose_name=_("AdministraNET Code"))
    adminet_nombre = models.CharField(max_length=255, blank=True, verbose_name=_("AdministraNET Name"))
    adminet_documento = models.CharField(max_length=50, blank=True, verbose_name=_("AdministraNET Document"))
    adminet_telefono = models.CharField(max_length=50, blank=True, verbose_name=_("AdministraNET Phone"))
    adminet_direccion = models.TextField(blank=True, verbose_name=_("AdministraNET Address"))

    # Configuración de sincronización
    sync_direction = models.CharField(
        max_length=30,
        choices=SyncDirection.choices,
        default=SyncDirection.BIDIRECTIONAL,
        verbose_name=_("Sync Direction")
    )
    sync_status = models.CharField(
        max_length=20,
        choices=SyncStatus.choices,
        default=SyncStatus.PENDING,
        verbose_name=_("Sync Status")
    )
    sync_enabled = models.BooleanField(default=True, verbose_name=_("Sync Enabled"))

    # Campos de control
    last_synced = models.DateTimeField(auto_now=True, verbose_name=_("Last Synced"))
    error_message = models.TextField(blank=True, verbose_name=_("Error Message"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        verbose_name = _("Customer Mapping")
        verbose_name_plural = _("Customer Mappings")
        ordering = ['-created_at']

    def __str__(self):
        return f"Customer {self.tiendanube_name or self.adminet_nombre}"

    @property
    def needs_sync(self):
        """Verificar si necesita sincronización."""
        return self.sync_enabled and self.sync_status != self.SyncStatus.SYNCED


class ProductMapping(models.Model):
    """
    Mapeo entre productos de Tiendanube y AdministraNET.
    Basado en la documentación oficial de Tiendanube API.
    """
    class SyncStatus(models.TextChoices):
        SYNCED = 'synced', _('Synced')
        PENDING = 'pending', _('Pending')
        ERROR = 'error', _('Error')
        CONFLICT = 'conflict', _('Conflict')

    class ProductType(models.TextChoices):
        PHYSICAL = 'physical', _('Physical Product')
        DIGITAL = 'digital', _('Digital Product')
        SERVICE = 'service', _('Service')

    # Campos de Tiendanube (según documentación oficial)
    tiendanube_id = models.BigIntegerField(unique=True, null=True, blank=True, verbose_name=_("Tiendanube ID"))
    tiendanube_name = models.CharField(max_length=255, blank=True, verbose_name=_("Tiendanube Name"))
    tiendanube_handle = models.CharField(max_length=255, blank=True, verbose_name=_("Tiendanube Handle"))
    tiendanube_description = models.TextField(blank=True, verbose_name=_("Tiendanube Description"))
    tiendanube_sku = models.CharField(max_length=100, blank=True, verbose_name=_("Tiendanube SKU"))
    tiendanube_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name=_("Tiendanube Price"))
    tiendanube_compare_at_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name=_("Tiendanube Compare At Price"))
    tiendanube_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name=_("Tiendanube Cost"))
    tiendanube_stock = models.IntegerField(default=0, verbose_name=_("Tiendanube Stock"))
    tiendanube_weight = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True, verbose_name=_("Tiendanube Weight (kg)"))
    tiendanube_width = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name=_("Tiendanube Width (cm)"))
    tiendanube_height = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name=_("Tiendanube Height (cm)"))
    tiendanube_depth = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name=_("Tiendanube Depth (cm)"))
    tiendanube_free_shipping = models.BooleanField(default=False, verbose_name=_("Tiendanube Free Shipping"))
    tiendanube_published = models.BooleanField(default=True, verbose_name=_("Tiendanube Published"))
    tiendanube_featured = models.BooleanField(default=False, verbose_name=_("Tiendanube Featured"))
    tiendanube_product_type = models.CharField(max_length=20, choices=ProductType.choices, default=ProductType.PHYSICAL, verbose_name=_("Tiendanube Product Type"))
    tiendanube_categories = models.JSONField(default=list, blank=True, verbose_name=_("Tiendanube Categories"))
    tiendanube_images = models.JSONField(default=list, blank=True, verbose_name=_("Tiendanube Images"))
    tiendanube_videos = models.JSONField(default=list, blank=True, verbose_name=_("Tiendanube Videos"))
    tiendanube_seo_title = models.CharField(max_length=255, blank=True, verbose_name=_("Tiendanube SEO Title"))
    tiendanube_seo_description = models.TextField(blank=True, verbose_name=_("Tiendanube SEO Description"))
    tiendanube_created_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Tiendanube Created At"))
    tiendanube_updated_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Tiendanube Updated At"))

    # Campos de AdministraNET (mapeo real con tabla articulo)
    adminet_id = models.BigIntegerField(blank=True, null=True, verbose_name=_("ID Artículo AdministraNET"))
    adminet_id_manual = models.CharField(max_length=200, blank=True, null=True, verbose_name=_("ID Manual AdministraNET"))
    adminet_codigo_articulo = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("Código Artículo AdministraNET"))
    adminet_nombre = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("Nombre Artículo AdministraNET"))
    adminet_detalle = models.TextField(blank=True, null=True, verbose_name=_("Detalle AdministraNET"))
    adminet_precio_costo = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True, verbose_name=_("Precio Costo AdministraNET"))
    adminet_precio_1v = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True, verbose_name=_("Precio 1V AdministraNET"))
    adminet_precio_2v = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True, verbose_name=_("Precio 2V AdministraNET"))
    adminet_precio_3v = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True, verbose_name=_("Precio 3V AdministraNET"))
    adminet_precio_4v = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True, verbose_name=_("Precio 4V AdministraNET"))
    adminet_precio_5v = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True, verbose_name=_("Precio 5V AdministraNET"))
    adminet_stock = models.IntegerField(blank=True, null=True, verbose_name=_("Stock AdministraNET"))
    adminet_stock_max = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, verbose_name=_("Stock Máximo AdministraNET"))
    adminet_stock_min = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, verbose_name=_("Stock Mínimo AdministraNET"))
    adminet_codigo_barra = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("Código de Barra AdministraNET"))
    adminet_codigo_barra_f = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("Código de Barra F AdministraNET"))
    adminet_codigo_proveedor = models.IntegerField(blank=True, null=True, verbose_name=_("Código Proveedor AdministraNET"))
    adminet_codigo_marca = models.IntegerField(blank=True, null=True, verbose_name=_("Código Marca AdministraNET"))
    adminet_codigo_modelo = models.IntegerField(blank=True, null=True, verbose_name=_("Código Modelo AdministraNET"))
    adminet_codigo_rubro = models.IntegerField(blank=True, null=True, verbose_name=_("Código Rubro AdministraNET"))
    adminet_codigo_subrubro = models.IntegerField(blank=True, null=True, verbose_name=_("Código SubRubro AdministraNET"))
    adminet_alicuota = models.IntegerField(blank=True, null=True, verbose_name=_("Alicuota IVA AdministraNET"))
    adminet_alicuota_ib = models.IntegerField(blank=True, null=True, verbose_name=_("Alicuota IB AdministraNET"))
    adminet_moneda = models.CharField(max_length=5, blank=True, null=True, verbose_name=_("Moneda AdministraNET"))
    adminet_tipo_iva = models.CharField(max_length=100, blank=True, null=True, verbose_name=_("Tipo IVA AdministraNET"))
    adminet_tipo_ib = models.CharField(max_length=100, blank=True, null=True, verbose_name=_("Tipo IB AdministraNET"))
    adminet_discontinuo = models.CharField(max_length=5, blank=True, null=True, verbose_name=_("Discontinuo AdministraNET"))
    adminet_ecommerce = models.CharField(max_length=2, blank=True, null=True, verbose_name=_("Ecommerce AdministraNET"))
    adminet_detalle_web = models.TextField(blank=True, null=True, verbose_name=_("Detalle Web AdministraNET"))
    adminet_disponible_venta = models.CharField(max_length=2, blank=True, null=True, verbose_name=_("Disponible Venta AdministraNET"))
    adminet_disponible_compra = models.CharField(max_length=2, blank=True, null=True, verbose_name=_("Disponible Compra AdministraNET"))
    adminet_fecha_alta = models.DateTimeField(blank=True, null=True, verbose_name=_("Fecha Alta AdministraNET"))
    adminet_fecha_mod = models.DateTimeField(blank=True, null=True, verbose_name=_("Fecha Modificación AdministraNET"))

    # Configuración de sincronización
    sync_status = models.CharField(
        max_length=20,
        choices=SyncStatus.choices,
        default=SyncStatus.PENDING,
        verbose_name=_("Sync Status")
    )
    sync_enabled = models.BooleanField(default=True, verbose_name=_("Sync Enabled"))
    sync_price = models.BooleanField(default=True, verbose_name=_("Sync Price"))
    sync_stock = models.BooleanField(default=True, verbose_name=_("Sync Stock"))
    sync_description = models.BooleanField(default=True, verbose_name=_("Sync Description"))
    sync_images = models.BooleanField(default=True, verbose_name=_("Sync Images"))

    # Campos de control
    last_synced = models.DateTimeField(auto_now=True, verbose_name=_("Last Synced"))
    error_message = models.TextField(blank=True, verbose_name=_("Error Message"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        verbose_name = _("Product Mapping")
        verbose_name_plural = _("Product Mappings")
        ordering = ['-created_at']

    def __str__(self):
        return f"Product {self.tiendanube_name or self.adminet_nombre}"

    @property
    def needs_sync(self):
        """Verificar si necesita sincronización."""
        return self.sync_enabled and self.sync_status != self.SyncStatus.SYNCED


class ProductVariantMapping(models.Model):
    """
    Mapeo entre variantes de productos de Tiendanube y AdministraNET.
    """
    class SyncStatus(models.TextChoices):
        SYNCED = 'synced', _('Synced')
        PENDING = 'pending', _('Pending')
        ERROR = 'error', _('Error')
        CONFLICT = 'conflict', _('Conflict')

    # Relación con el producto padre
    product_mapping = models.ForeignKey(
        ProductMapping, 
        on_delete=models.CASCADE, 
        related_name='variants',
        verbose_name=_("Product Mapping")
    )

    # Campos de Tiendanube
    tiendanube_variant_id = models.BigIntegerField(unique=True, null=True, blank=True, verbose_name=_("Tiendanube Variant ID"))
    tiendanube_name = models.CharField(max_length=255, blank=True, verbose_name=_("Tiendanube Variant Name"))
    tiendanube_sku = models.CharField(max_length=100, blank=True, verbose_name=_("Tiendanube Variant SKU"))
    tiendanube_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name=_("Tiendanube Variant Price"))
    tiendanube_compare_at_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name=_("Tiendanube Variant Compare At Price"))
    tiendanube_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name=_("Tiendanube Variant Cost"))
    tiendanube_stock = models.IntegerField(default=0, verbose_name=_("Tiendanube Variant Stock"))
    tiendanube_weight = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True, verbose_name=_("Tiendanube Variant Weight"))
    tiendanube_width = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name=_("Tiendanube Variant Width"))
    tiendanube_height = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name=_("Tiendanube Variant Height"))
    tiendanube_depth = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name=_("Tiendanube Variant Depth"))
    tiendanube_free_shipping = models.BooleanField(default=False, verbose_name=_("Tiendanube Variant Free Shipping"))
    tiendanube_published = models.BooleanField(default=True, verbose_name=_("Tiendanube Variant Published"))
    tiendanube_values = models.JSONField(default=dict, blank=True, verbose_name=_("Tiendanube Variant Values"))
    tiendanube_images = models.JSONField(default=list, blank=True, verbose_name=_("Tiendanube Variant Images"))
    tiendanube_created_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Tiendanube Variant Created At"))
    tiendanube_updated_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Tiendanube Variant Updated At"))

    # Campos de AdministraNET (mapeo real con tabla articulo para variantes)
    adminet_id = models.BigIntegerField(blank=True, null=True, verbose_name=_("ID Variante AdministraNET"))
    adminet_id_manual = models.CharField(max_length=200, blank=True, null=True, verbose_name=_("ID Manual Variante AdministraNET"))
    adminet_codigo_articulo = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("Código Variante AdministraNET"))
    adminet_nombre = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("Nombre Variante AdministraNET"))
    adminet_detalle = models.TextField(blank=True, null=True, verbose_name=_("Detalle Variante AdministraNET"))
    adminet_precio_costo = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True, verbose_name=_("Precio Costo Variante AdministraNET"))
    adminet_precio_1v = models.DecimalField(max_digits=15, decimal_places=4, blank=True, null=True, verbose_name=_("Precio 1V Variante AdministraNET"))
    adminet_stock = models.IntegerField(blank=True, null=True, verbose_name=_("Stock Variante AdministraNET"))
    adminet_codigo_barra = models.CharField(max_length=255, blank=True, null=True, verbose_name=_("Código de Barra Variante AdministraNET"))
    adminet_codigo_proveedor = models.IntegerField(blank=True, null=True, verbose_name=_("Código Proveedor Variante AdministraNET"))
    adminet_codigo_marca = models.IntegerField(blank=True, null=True, verbose_name=_("Código Marca Variante AdministraNET"))
    adminet_codigo_modelo = models.IntegerField(blank=True, null=True, verbose_name=_("Código Modelo Variante AdministraNET"))
    adminet_alicuota = models.IntegerField(blank=True, null=True, verbose_name=_("Alicuota IVA Variante AdministraNET"))
    adminet_alicuota_ib = models.IntegerField(blank=True, null=True, verbose_name=_("Alicuota IB Variante AdministraNET"))
    adminet_moneda = models.CharField(max_length=5, blank=True, null=True, verbose_name=_("Moneda Variante AdministraNET"))
    adminet_tipo_iva = models.CharField(max_length=100, blank=True, null=True, verbose_name=_("Tipo IVA Variante AdministraNET"))
    adminet_tipo_ib = models.CharField(max_length=100, blank=True, null=True, verbose_name=_("Tipo IB Variante AdministraNET"))
    adminet_discontinuo = models.CharField(max_length=5, blank=True, null=True, verbose_name=_("Discontinuo Variante AdministraNET"))
    adminet_ecommerce = models.CharField(max_length=2, blank=True, null=True, verbose_name=_("Ecommerce Variante AdministraNET"))
    adminet_detalle_web = models.TextField(blank=True, null=True, verbose_name=_("Detalle Web Variante AdministraNET"))
    adminet_disponible_venta = models.CharField(max_length=2, blank=True, null=True, verbose_name=_("Disponible Venta Variante AdministraNET"))
    adminet_disponible_compra = models.CharField(max_length=2, blank=True, null=True, verbose_name=_("Disponible Compra Variante AdministraNET"))
    adminet_fecha_alta = models.DateTimeField(blank=True, null=True, verbose_name=_("Fecha Alta Variante AdministraNET"))
    adminet_fecha_mod = models.DateTimeField(blank=True, null=True, verbose_name=_("Fecha Modificación Variante AdministraNET"))

    # Configuración de sincronización
    sync_status = models.CharField(
        max_length=20,
        choices=SyncStatus.choices,
        default=SyncStatus.PENDING,
        verbose_name=_("Sync Status")
    )
    sync_enabled = models.BooleanField(default=True, verbose_name=_("Sync Enabled"))
    sync_price = models.BooleanField(default=True, verbose_name=_("Sync Price"))
    sync_stock = models.BooleanField(default=True, verbose_name=_("Sync Stock"))

    # Campos de control
    last_synced = models.DateTimeField(auto_now=True, verbose_name=_("Last Synced"))
    error_message = models.TextField(blank=True, verbose_name=_("Error Message"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        verbose_name = _("Product Variant Mapping")
        verbose_name_plural = _("Product Variant Mappings")
        ordering = ['-created_at']

    def __str__(self):
        return f"Variant {self.tiendanube_name or self.adminet_nombre} of {self.product_mapping}"

    @property
    def needs_sync(self):
        """Verificar si necesita sincronización."""
        return self.sync_enabled and self.sync_status != self.SyncStatus.SYNCED


class ProductCategoryMapping(models.Model):
    """
    Mapeo entre categorías de productos de Tiendanube y AdministraNET.
    """
    class SyncStatus(models.TextChoices):
        SYNCED = 'synced', _('Synced')
        PENDING = 'pending', _('Pending')
        ERROR = 'error', _('Error')
        CONFLICT = 'conflict', _('Conflict')

    # Campos de Tiendanube
    tiendanube_id = models.BigIntegerField(unique=True, null=True, blank=True, verbose_name=_("Tiendanube Category ID"))
    tiendanube_name = models.CharField(max_length=255, blank=True, verbose_name=_("Tiendanube Category Name"))
    tiendanube_handle = models.CharField(max_length=255, blank=True, verbose_name=_("Tiendanube Category Handle"))
    tiendanube_description = models.TextField(blank=True, verbose_name=_("Tiendanube Category Description"))
    tiendanube_parent_id = models.BigIntegerField(null=True, blank=True, verbose_name=_("Tiendanube Parent Category ID"))
    tiendanube_image = models.URLField(blank=True, verbose_name=_("Tiendanube Category Image"))
    tiendanube_created_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Tiendanube Category Created At"))
    tiendanube_updated_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Tiendanube Category Updated At"))

    # Campos de AdministraNET
    adminet_codigo = models.CharField(max_length=50, null=True, blank=True, verbose_name=_("AdministraNET Category Code"))
    adminet_nombre = models.CharField(max_length=255, blank=True, verbose_name=_("AdministraNET Category Name"))
    adminet_descripcion = models.TextField(blank=True, verbose_name=_("AdministraNET Category Description"))
    adminet_categoria_padre = models.CharField(max_length=50, null=True, blank=True, verbose_name=_("AdministraNET Parent Category"))

    # Configuración de sincronización
    sync_status = models.CharField(
        max_length=20,
        choices=SyncStatus.choices,
        default=SyncStatus.PENDING,
        verbose_name=_("Sync Status")
    )
    sync_enabled = models.BooleanField(default=True, verbose_name=_("Sync Enabled"))

    # Campos de control
    last_synced = models.DateTimeField(auto_now=True, verbose_name=_("Last Synced"))
    error_message = models.TextField(blank=True, verbose_name=_("Error Message"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        verbose_name = _("Product Category Mapping")
        verbose_name_plural = _("Product Category Mappings")
        ordering = ['-created_at']

    def __str__(self):
        return f"Category {self.tiendanube_name or self.adminet_nombre}"

    @property
    def needs_sync(self):
        """Verificar si necesita sincronización."""
        return self.sync_enabled and self.sync_status != self.SyncStatus.SYNCED


class OrderMapping(models.Model):
    """
    Mapeo entre órdenes de Tiendanube y AdministraNET.
    """
    class SyncStatus(models.TextChoices):
        SYNCED = 'synced', _('Synced')
        PENDING = 'pending', _('Pending')
        ERROR = 'error', _('Error')
        CONFLICT = 'conflict', _('Conflict')

    class OrderStatus(models.TextChoices):
        PENDING = 'pending', _('Pending')
        PAID = 'paid', _('Paid')
        SHIPPED = 'shipped', _('Shipped')
        DELIVERED = 'delivered', _('Delivered')
        CANCELLED = 'cancelled', _('Cancelled')

    # Campos de Tiendanube
    tiendanube_id = models.BigIntegerField(unique=True, null=True, blank=True, verbose_name=_("Tiendanube ID"))
    tiendanube_number = models.CharField(max_length=50, blank=True, verbose_name=_("Tiendanube Number"))
    tiendanube_status = models.CharField(max_length=50, blank=True, verbose_name=_("Tiendanube Status"))
    tiendanube_total = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name=_("Tiendanube Total"))
    tiendanube_customer_email = models.EmailField(blank=True, verbose_name=_("Tiendanube Customer Email"))

    # Campos de AdministraNET
    adminet_codigo = models.CharField(max_length=50, null=True, blank=True, verbose_name=_("AdministraNET Code"))
    adminet_numero = models.CharField(max_length=50, blank=True, verbose_name=_("AdministraNET Number"))
    adminet_estado = models.CharField(max_length=50, blank=True, verbose_name=_("AdministraNET Status"))
    adminet_total = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name=_("AdministraNET Total"))

    # Configuración de sincronización
    sync_status = models.CharField(
        max_length=20,
        choices=SyncStatus.choices,
        default=SyncStatus.PENDING,
        verbose_name=_("Sync Status")
    )
    sync_enabled = models.BooleanField(default=True, verbose_name=_("Sync Enabled"))

    # Campos de control
    last_synced = models.DateTimeField(auto_now=True, verbose_name=_("Last Synced"))
    error_message = models.TextField(blank=True, verbose_name=_("Error Message"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        verbose_name = _("Order Mapping")
        verbose_name_plural = _("Order Mappings")
        ordering = ['-created_at']

    def __str__(self):
        return f"Order {self.tiendanube_number or self.adminet_numero}"

    @property
    def needs_sync(self):
        """Verificar si necesita sincronización."""
        return self.sync_enabled and self.sync_status != self.SyncStatus.SYNCED


class SyncLog(models.Model):
    """
    Log de sincronización entre Tiendanube y AdministraNET.
    """
    class SyncType(models.TextChoices):
        CUSTOMER = 'customer', _('Customer')
        PRODUCT = 'product', _('Product')
        ORDER = 'order', _('Order')
        FULL = 'full', _('Full Sync')

    class SyncDirection(models.TextChoices):
        TO_ADMINET = 'to_adminet', _('To AdministraNET')
        FROM_ADMINET = 'from_adminet', _('From AdministraNET')
        BIDIRECTIONAL = 'bidirectional', _('Bidirectional')

    class Status(models.TextChoices):
        PENDING = 'pending', _('Pending')
        IN_PROGRESS = 'in_progress', _('In Progress')
        COMPLETED = 'completed', _('Completed')
        FAILED = 'failed', _('Failed')
        CANCELLED = 'cancelled', _('Cancelled')

    sync_type = models.CharField(max_length=20, choices=SyncType.choices, verbose_name=_("Sync Type"))
    direction = models.CharField(max_length=20, choices=SyncDirection.choices, default=SyncDirection.TO_ADMINET, verbose_name=_("Direction"))
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, verbose_name=_("Status"))
    
    # Contadores
    total_items = models.IntegerField(default=0, verbose_name=_("Total Items"))
    processed_items = models.IntegerField(default=0, verbose_name=_("Processed Items"))
    successful_items = models.IntegerField(default=0, verbose_name=_("Successful Items"))
    failed_items = models.IntegerField(default=0, verbose_name=_("Failed Items"))
    
    # Información de ejecución
    started_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Started At"))
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Completed At"))
    duration_seconds = models.IntegerField(null=True, blank=True, verbose_name=_("Duration (seconds)"))
    
    # Detalles
    error_message = models.TextField(blank=True, verbose_name=_("Error Message"))
    details = models.JSONField(default=dict, blank=True, verbose_name=_("Details"))
    
    # Configuración utilizada
    tiendanube_config = models.ForeignKey(TiendanubeConfig, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Tiendanube Config"))
    adminet_config = models.ForeignKey(AdministraNETConfig, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("AdministraNET Config"))

    class Meta:
        verbose_name = _("Sync Log")
        verbose_name_plural = _("Sync Logs")
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.get_sync_type_display()} - {self.get_status_display()} ({self.started_at})"

    def complete_sync(self, success=True, error_message=""):
        """Marcar sincronización como completada."""
        self.completed_at = timezone.now()
        self.duration_seconds = int((self.completed_at - self.started_at).total_seconds())
        
        if success:
            self.status = self.Status.COMPLETED
        else:
            self.status = self.Status.FAILED
            self.error_message = error_message
        
        self.save()


class ValidationRule(models.Model):
    """
    Reglas de validación para la sincronización.
    """
    class RuleType(models.TextChoices):
        CUSTOMER = 'customer', _('Customer')
        PRODUCT = 'product', _('Product')
        ORDER = 'order', _('Order')

    class ValidationType(models.TextChoices):
        REQUIRED_FIELD = 'required_field', _('Required Field')
        FIELD_FORMAT = 'field_format', _('Field Format')
        BUSINESS_RULE = 'business_rule', _('Business Rule')
        CUSTOM = 'custom', _('Custom')

    name = models.CharField(max_length=100, verbose_name=_("Rule Name"))
    rule_type = models.CharField(max_length=20, choices=RuleType.choices, verbose_name=_("Rule Type"))
    validation_type = models.CharField(max_length=20, choices=ValidationType.choices, verbose_name=_("Validation Type"))
    
    # Configuración de la regla
    field_name = models.CharField(max_length=100, blank=True, verbose_name=_("Field Name"))
    rule_config = models.JSONField(default=dict, verbose_name=_("Rule Configuration"))
    
    # Estado
    is_active = models.BooleanField(default=True, verbose_name=_("Active"))
    is_critical = models.BooleanField(default=False, verbose_name=_("Critical"))
    
    # Metadatos
    description = models.TextField(blank=True, verbose_name=_("Description"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        verbose_name = _("Validation Rule")
        verbose_name_plural = _("Validation Rules")
        ordering = ['rule_type', 'name']

    def __str__(self):
        return f"{self.name} ({self.get_rule_type_display()})"


class ValidationLog(models.Model):
    """
    Log de validaciones ejecutadas.
    """
    class Status(models.TextChoices):
        PASSED = 'passed', _('Passed')
        FAILED = 'failed', _('Failed')
        WARNING = 'warning', _('Warning')

    validation_rule = models.ForeignKey(ValidationRule, on_delete=models.CASCADE, verbose_name=_("Validation Rule"))
    sync_log = models.ForeignKey(SyncLog, on_delete=models.CASCADE, verbose_name=_("Sync Log"))
    
    # Resultado
    status = models.CharField(max_length=20, choices=Status.choices, verbose_name=_("Status"))
    message = models.TextField(blank=True, verbose_name=_("Message"))
    
    # Datos validados
    validated_data = models.JSONField(default=dict, blank=True, verbose_name=_("Validated Data"))
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))

    class Meta:
        verbose_name = _("Validation Log")
        verbose_name_plural = _("Validation Logs")
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.validation_rule.name} - {self.get_status_display()} ({self.created_at})"


class WebhookConfig(models.Model):
    """
    Configuración de webhooks de Tiendanube.
    """
    class WebhookStatus(models.TextChoices):
        ACTIVE = 'active', _('Active')
        INACTIVE = 'inactive', _('Inactive')
        ERROR = 'error', _('Error')

    class WebhookEvent(models.TextChoices):
        # Product events
        PRODUCT_CREATED = 'product/created', _('Product Created')
        PRODUCT_UPDATED = 'product/updated', _('Product Updated')
        PRODUCT_DELETED = 'product/deleted', _('Product Deleted')
        
        # Order events
        ORDER_CREATED = 'order/created', _('Order Created')
        ORDER_UPDATED = 'order/updated', _('Order Updated')
        ORDER_CANCELLED = 'order/cancelled', _('Order Cancelled')
        ORDER_PAID = 'order/paid', _('Order Paid')
        ORDER_FULFILLED = 'order/fulfilled', _('Order Fulfilled')
        
        # Customer events
        CUSTOMER_CREATED = 'customer/created', _('Customer Created')
        CUSTOMER_UPDATED = 'customer/updated', _('Customer Updated')
        CUSTOMER_DELETED = 'customer/deleted', _('Customer Deleted')
        
        # Inventory events
        INVENTORY_UPDATED = 'inventory/updated', _('Inventory Updated')
        
        # Category events
        CATEGORY_CREATED = 'category/created', _('Category Created')
        CATEGORY_UPDATED = 'category/updated', _('Category Updated')
        CATEGORY_DELETED = 'category/deleted', _('Category Deleted')

    # Configuración de Tiendanube asociada
    tiendanube_config = models.ForeignKey(
        TiendanubeConfig, 
        on_delete=models.CASCADE, 
        related_name='webhooks',
        verbose_name=_("Tiendanube Configuration")
    )
    
    # Información del webhook en Tiendanube
    webhook_id = models.BigIntegerField(null=True, blank=True, verbose_name=_("Tiendanube Webhook ID"))
    webhook_url = models.URLField(verbose_name=_("Webhook URL"))
    webhook_secret = models.CharField(max_length=255, blank=True, verbose_name=_("Webhook Secret"))
    
    # Eventos suscritos
    events = models.JSONField(
        default=list,
        verbose_name=_("Subscribed Events"),
        help_text=_("List of events this webhook is subscribed to")
    )
    
    # Estado y configuración
    status = models.CharField(
        max_length=20,
        choices=WebhookStatus.choices,
        default=WebhookStatus.ACTIVE,
        verbose_name=_("Status")
    )
    is_active = models.BooleanField(default=True, verbose_name=_("Active"))
    
    # Configuración de reintentos
    max_retries = models.IntegerField(default=3, verbose_name=_("Max Retries"))
    retry_delay = models.IntegerField(default=300, verbose_name=_("Retry Delay (seconds)"))
    
    # Metadatos
    description = models.TextField(blank=True, verbose_name=_("Description"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))
    last_triggered = models.DateTimeField(null=True, blank=True, verbose_name=_("Last Triggered"))
    
    class Meta:
        verbose_name = _("Webhook Configuration")
        verbose_name_plural = _("Webhook Configurations")
        ordering = ['-created_at']
        unique_together = ['tiendanube_config', 'webhook_url']

    def __str__(self):
        return f"Webhook {self.webhook_id} - {self.webhook_url}"

    def get_events_display(self):
        """Obtener lista legible de eventos."""
        event_names = []
        for event in self.events:
            try:
                event_names.append(dict(self.WebhookEvent.choices)[event])
            except KeyError:
                event_names.append(event)
        return ', '.join(event_names)

    def is_subscribed_to(self, event_type):
        """Verificar si el webhook está suscrito a un evento específico."""
        return event_type in self.events


class WebhookEvent(models.Model):
    """
    Registro de eventos de webhook recibidos.
    """
    class EventStatus(models.TextChoices):
        PENDING = 'pending', _('Pending')
        PROCESSING = 'processing', _('Processing')
        COMPLETED = 'completed', _('Completed')
        FAILED = 'failed', _('Failed')
        RETRY = 'retry', _('Retry')

    # Configuración del webhook
    webhook_config = models.ForeignKey(
        WebhookConfig,
        on_delete=models.CASCADE,
        related_name='webhook_events',
        verbose_name=_("Webhook Configuration")
    )
    
    # Información del evento
    event_type = models.CharField(max_length=50, verbose_name=_("Event Type"))
    event_id = models.CharField(max_length=100, verbose_name=_("Event ID"))
    resource_id = models.BigIntegerField(null=True, blank=True, verbose_name=_("Resource ID"))
    resource_type = models.CharField(max_length=50, blank=True, verbose_name=_("Resource Type"))
    
    # Datos del evento
    payload = models.JSONField(verbose_name=_("Event Payload"))
    headers = models.JSONField(default=dict, verbose_name=_("Request Headers"))
    
    # Estado y procesamiento
    status = models.CharField(
        max_length=20,
        choices=EventStatus.choices,
        default=EventStatus.PENDING,
        verbose_name=_("Status")
    )
    retry_count = models.IntegerField(default=0, verbose_name=_("Retry Count"))
    
    # Resultado del procesamiento
    processing_result = models.JSONField(default=dict, blank=True, verbose_name=_("Processing Result"))
    error_message = models.TextField(blank=True, verbose_name=_("Error Message"))
    
    # Timestamps
    received_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Received At"))
    processed_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Processed At"))
    next_retry_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Next Retry At"))

    class Meta:
        verbose_name = _("Webhook Event")
        verbose_name_plural = _("Webhook Events")
        ordering = ['-received_at']
        indexes = [
            models.Index(fields=['event_type', 'status']),
            models.Index(fields=['resource_type', 'resource_id']),
            models.Index(fields=['received_at']),
        ]

    def __str__(self):
        return f"{self.event_type} - {self.event_id} ({self.status})"

    def mark_processing(self):
        """Marcar evento como en procesamiento."""
        self.status = self.EventStatus.PROCESSING
        self.save(update_fields=['status'])

    def mark_completed(self, result=None):
        """Marcar evento como completado."""
        self.status = self.EventStatus.COMPLETED
        self.processed_at = timezone.now()
        if result:
            self.processing_result = result
        self.save(update_fields=['status', 'processed_at', 'processing_result'])

    def mark_failed(self, error_message, retry=True):
        """Marcar evento como fallido."""
        self.error_message = error_message
        self.retry_count += 1
        
        if retry and self.retry_count < self.webhook_config.max_retries:
            self.status = self.EventStatus.RETRY
            self.next_retry_at = timezone.now() + timezone.timedelta(seconds=self.webhook_config.retry_delay)
        else:
            self.status = self.EventStatus.FAILED
        
        self.save(update_fields=['status', 'error_message', 'retry_count', 'next_retry_at'])


class WebhookDeliveryLog(models.Model):
    """
    Log de entrega de webhooks para debugging y monitoreo.
    """
    class DeliveryStatus(models.TextChoices):
        SUCCESS = 'success', _('Success')
        FAILED = 'failed', _('Failed')
        TIMEOUT = 'timeout', _('Timeout')
        INVALID_RESPONSE = 'invalid_response', _('Invalid Response')

    webhook_config = models.ForeignKey(
        WebhookConfig,
        on_delete=models.CASCADE,
        related_name='webhook_delivery_logs',
        verbose_name=_("Webhook Configuration")
    )
    
    webhook_event = models.ForeignKey(
        WebhookEvent,
        on_delete=models.CASCADE,
        related_name='delivery_logs',
        verbose_name=_("Webhook Event")
    )
    
    # Información de la entrega
    status = models.CharField(max_length=20, choices=DeliveryStatus.choices, verbose_name=_("Status"))
    response_code = models.IntegerField(null=True, blank=True, verbose_name=_("Response Code"))
    response_body = models.TextField(blank=True, verbose_name=_("Response Body"))
    response_headers = models.JSONField(default=dict, blank=True, verbose_name=_("Response Headers"))
    
    # Métricas de rendimiento
    request_duration = models.FloatField(null=True, blank=True, verbose_name=_("Request Duration (seconds)"))
    payload_size = models.IntegerField(null=True, blank=True, verbose_name=_("Payload Size (bytes)"))
    
    # Información de error
    error_message = models.TextField(blank=True, verbose_name=_("Error Message"))
    
    # Timestamps
    sent_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Sent At"))
    received_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Received At"))

    class Meta:
        verbose_name = _("Webhook Delivery Log")
        verbose_name_plural = _("Webhook Delivery Logs")
        ordering = ['-sent_at']

    def __str__(self):
        return f"Delivery {self.id} - {self.status} ({self.sent_at})"
