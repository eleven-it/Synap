from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import (
    TiendanubeConfig, 
    AdministraNETConfig, 
    CustomerMapping, 
    SyncLog, 
    ProductMapping, 
    ProductVariantMapping,
    ProductCategoryMapping,
    OrderMapping,
    WebhookConfig,
    WebhookEvent,
    WebhookDeliveryLog
)


@admin.register(TiendanubeConfig)
class TiendanubeConfigAdmin(admin.ModelAdmin):
    list_display = ['name', 'store_id', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'store_id']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('name', 'store_id', 'is_active')
        }),
        (_('API Configuration'), {
            'fields': ('access_token', 'api_url')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(AdministraNETConfig)
class AdministraNETConfigAdmin(admin.ModelAdmin):
    list_display = ['name', 'host', 'port', 'database', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'host', 'database']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('name', 'is_active')
        }),
        (_('Database Configuration'), {
            'fields': ('host', 'port', 'database', 'user', 'password')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(CustomerMapping)
class CustomerMappingAdmin(admin.ModelAdmin):
    list_display = [
        'tiendanube_email', 'tiendanube_id', 'adminet_codigo', 
        'sync_status', 'sync_direction', 'sync_enabled', 'last_synced'
    ]
    list_filter = [
        'sync_status', 'sync_direction', 'sync_enabled', 
        'created_at', 'last_synced'
    ]
    search_fields = [
        'tiendanube_email', 'tiendanube_name', 'adminet_nombre',
        'tiendanube_id', 'adminet_codigo'
    ]
    readonly_fields = ['created_at', 'updated_at', 'last_synced']
    
    fieldsets = (
        (_('Tiendanube Information'), {
            'fields': (
                'tiendanube_id', 'tiendanube_email', 'tiendanube_name',
                'tiendanube_document', 'tiendanube_phone', 'tiendanube_address'
            )
        }),
        (_('AdministraNET Information'), {
            'fields': (
                'adminet_codigo', 'adminet_nombre', 'adminet_documento',
                'adminet_telefono', 'adminet_direccion'
            )
        }),
        (_('Sync Configuration'), {
            'fields': ('sync_direction', 'sync_status', 'sync_enabled')
        }),
        (_('Error Information'), {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at', 'last_synced'),
            'classes': ('collapse',)
        }),
    )


@admin.register(SyncLog)
class SyncLogAdmin(admin.ModelAdmin):
    list_display = [
        'sync_type', 'direction', 'status', 'total_items', 
        'successful_items', 'failed_items', 'started_at'
    ]
    list_filter = [
        'sync_type', 'direction', 'status', 'started_at'
    ]
    search_fields = ['error_message']
    readonly_fields = [
        'started_at', 'completed_at', 'duration_seconds', 
        'total_items', 'successful_items', 'failed_items'
    ]
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('sync_type', 'direction', 'status')
        }),
        (_('Configuration'), {
            'fields': ('tiendanube_config', 'adminet_config')
        }),
        (_('Metrics'), {
            'fields': ('total_items', 'processed_items', 'successful_items', 'failed_items')
        }),
        (_('Details'), {
            'fields': ('error_message', 'details')
        }),
        (_('Timestamps'), {
            'fields': ('started_at', 'completed_at', 'duration_seconds')
        }),
    )


@admin.register(ProductMapping)
class ProductMappingAdmin(admin.ModelAdmin):
    list_display = [
        'tiendanube_name', 'tiendanube_sku', 'adminet_codigo_articulo',
        'sync_status', 'sync_enabled', 'last_synced'
    ]
    list_filter = ['sync_status', 'sync_enabled', 'created_at', 'last_synced']
    search_fields = [
        'tiendanube_name', 'tiendanube_sku', 'adminet_nombre', 'adminet_codigo_articulo'
    ]
    readonly_fields = ['created_at', 'updated_at', 'last_synced']
    
    fieldsets = (
        (_('Tiendanube Information'), {
            'fields': (
                'tiendanube_id', 'tiendanube_name', 'tiendanube_handle', 'tiendanube_sku',
                'tiendanube_price', 'tiendanube_compare_at_price', 'tiendanube_cost', 'tiendanube_stock',
                'tiendanube_weight', 'tiendanube_width', 'tiendanube_height', 'tiendanube_depth',
                'tiendanube_free_shipping', 'tiendanube_published', 'tiendanube_featured',
                'tiendanube_product_type', 'tiendanube_seo_title', 'tiendanube_seo_description'
            )
        }),
        (_('AdministraNET Basic Information'), {
            'fields': (
                'adminet_id', 'adminet_id_manual', 'adminet_codigo_articulo', 'adminet_nombre',
                'adminet_detalle', 'adminet_stock', 'adminet_stock_max', 'adminet_stock_min'
            )
        }),
        (_('AdministraNET Pricing'), {
            'fields': (
                'adminet_precio_costo', 'adminet_precio_1v', 'adminet_precio_2v', 'adminet_precio_3v',
                'adminet_precio_4v', 'adminet_precio_5v'
            )
        }),
        (_('AdministraNET Classification'), {
            'fields': (
                'adminet_codigo_proveedor', 'adminet_codigo_marca', 'adminet_codigo_modelo',
                'adminet_codigo_rubro', 'adminet_codigo_subrubro'
            )
        }),
        (_('AdministraNET Barcodes'), {
            'fields': (
                'adminet_codigo_barra', 'adminet_codigo_barra_f'
            )
        }),
        (_('AdministraNET Tax & Currency'), {
            'fields': (
                'adminet_alicuota', 'adminet_alicuota_ib', 'adminet_moneda',
                'adminet_tipo_iva', 'adminet_tipo_ib'
            )
        }),
        (_('AdministraNET Status'), {
            'fields': (
                'adminet_discontinuo', 'adminet_ecommerce', 'adminet_detalle_web',
                'adminet_disponible_venta', 'adminet_disponible_compra'
            )
        }),
        (_('AdministraNET Timestamps'), {
            'fields': (
                'adminet_fecha_alta', 'adminet_fecha_mod'
            ),
            'classes': ('collapse',)
        }),
        (_('Sync Configuration'), {
            'fields': ('sync_status', 'sync_enabled', 'sync_price', 'sync_stock', 'sync_description', 'sync_images')
        }),
        (_('Error Information'), {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at', 'last_synced'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ProductVariantMapping)
class ProductVariantMappingAdmin(admin.ModelAdmin):
    list_display = [
        'product_mapping', 'tiendanube_name', 'tiendanube_sku', 'adminet_codigo_articulo',
        'sync_status', 'sync_enabled', 'last_synced'
    ]
    list_filter = ['sync_status', 'sync_enabled', 'created_at', 'last_synced']
    search_fields = [
        'tiendanube_name', 'tiendanube_sku', 'adminet_nombre', 'adminet_codigo_articulo',
        'product_mapping__tiendanube_name'
    ]
    readonly_fields = ['created_at', 'updated_at', 'last_synced']
    
    fieldsets = (
        (_('Product Relationship'), {
            'fields': ('product_mapping',)
        }),
        (_('Tiendanube Information'), {
            'fields': (
                'tiendanube_variant_id', 'tiendanube_name', 'tiendanube_sku',
                'tiendanube_price', 'tiendanube_compare_at_price', 'tiendanube_cost', 'tiendanube_stock',
                'tiendanube_weight', 'tiendanube_width', 'tiendanube_height', 'tiendanube_depth',
                'tiendanube_free_shipping', 'tiendanube_published', 'tiendanube_values'
            )
        }),
        (_('AdministraNET Basic Information'), {
            'fields': (
                'adminet_id', 'adminet_id_manual', 'adminet_codigo_articulo', 'adminet_nombre',
                'adminet_detalle', 'adminet_stock'
            )
        }),
        (_('AdministraNET Pricing'), {
            'fields': (
                'adminet_precio_costo', 'adminet_precio_1v'
            )
        }),
        (_('AdministraNET Classification'), {
            'fields': (
                'adminet_codigo_proveedor', 'adminet_codigo_marca', 'adminet_codigo_modelo'
            )
        }),
        (_('AdministraNET Barcodes'), {
            'fields': (
                'adminet_codigo_barra',
            )
        }),
        (_('AdministraNET Tax & Currency'), {
            'fields': (
                'adminet_alicuota', 'adminet_alicuota_ib', 'adminet_moneda',
                'adminet_tipo_iva', 'adminet_tipo_ib'
            )
        }),
        (_('AdministraNET Status'), {
            'fields': (
                'adminet_discontinuo', 'adminet_ecommerce', 'adminet_detalle_web',
                'adminet_disponible_venta', 'adminet_disponible_compra'
            )
        }),
        (_('AdministraNET Timestamps'), {
            'fields': (
                'adminet_fecha_alta', 'adminet_fecha_mod'
            ),
            'classes': ('collapse',)
        }),
        (_('Sync Configuration'), {
            'fields': ('sync_status', 'sync_enabled', 'sync_price', 'sync_stock')
        }),
        (_('Error Information'), {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at', 'last_synced'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ProductCategoryMapping)
class ProductCategoryMappingAdmin(admin.ModelAdmin):
    list_display = [
        'tiendanube_name', 'tiendanube_handle', 'adminet_codigo',
        'sync_status', 'sync_enabled', 'last_synced'
    ]
    list_filter = ['sync_status', 'sync_enabled', 'created_at', 'last_synced']
    search_fields = [
        'tiendanube_name', 'tiendanube_handle', 'adminet_nombre', 'adminet_codigo'
    ]
    readonly_fields = ['created_at', 'updated_at', 'last_synced']
    
    fieldsets = (
        (_('Tiendanube Information'), {
            'fields': (
                'tiendanube_id', 'tiendanube_name', 'tiendanube_handle', 'tiendanube_description',
                'tiendanube_parent_id', 'tiendanube_image'
            )
        }),
        (_('AdministraNET Information'), {
            'fields': (
                'adminet_codigo', 'adminet_nombre', 'adminet_descripcion', 'adminet_categoria_padre'
            )
        }),
        (_('Sync Configuration'), {
            'fields': ('sync_status', 'sync_enabled')
        }),
        (_('Error Information'), {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at', 'last_synced'),
            'classes': ('collapse',)
        }),
    )


@admin.register(OrderMapping)
class OrderMappingAdmin(admin.ModelAdmin):
    list_display = [
        'tiendanube_number', 'tiendanube_customer_email', 'adminet_codigo',
        'sync_status', 'sync_enabled', 'created_at'
    ]
    list_filter = ['sync_status', 'sync_enabled', 'created_at', 'last_synced']
    search_fields = [
        'tiendanube_number', 'tiendanube_customer_email', 'adminet_numero'
    ]
    readonly_fields = ['created_at', 'updated_at', 'last_synced']
    
    fieldsets = (
        (_('Tiendanube Information'), {
            'fields': (
                'tiendanube_id', 'tiendanube_number', 'tiendanube_status',
                'tiendanube_total', 'tiendanube_customer_email'
            )
        }),
        (_('AdministraNET Information'), {
            'fields': (
                'adminet_codigo', 'adminet_numero', 'adminet_estado', 'adminet_total'
            )
        }),
        (_('Sync Configuration'), {
            'fields': ('sync_status', 'sync_enabled')
        }),
        (_('Error Information'), {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at', 'last_synced'),
            'classes': ('collapse',)
        }),
    )


@admin.register(WebhookConfig)
class WebhookConfigAdmin(admin.ModelAdmin):
    list_display = ['webhook_url', 'tiendanube_config', 'status', 'is_active', 'created_at', 'last_triggered']
    list_filter = ['status', 'is_active', 'created_at']
    search_fields = ['webhook_url', 'description', 'tiendanube_config__name']
    readonly_fields = ['webhook_id', 'created_at', 'updated_at', 'last_triggered']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('tiendanube_config', 'webhook_url', 'webhook_secret', 'description')
        }),
        ('Events', {
            'fields': ('events',)
        }),
        ('Configuration', {
            'fields': ('status', 'is_active', 'max_retries', 'retry_delay')
        }),
        ('System Information', {
            'fields': ('webhook_id', 'created_at', 'updated_at', 'last_triggered'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('tiendanube_config')


@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    list_display = ['event_type', 'event_id', 'resource_type', 'resource_id', 'status', 'received_at', 'webhook_config']
    list_filter = ['status', 'event_type', 'resource_type', 'received_at']
    search_fields = ['event_id', 'resource_id', 'webhook_config__webhook_url']
    readonly_fields = ['received_at', 'processed_at', 'next_retry_at']
    
    fieldsets = (
        ('Event Information', {
            'fields': ('webhook_config', 'event_type', 'event_id', 'resource_type', 'resource_id')
        }),
        ('Data', {
            'fields': ('payload', 'headers')
        }),
        ('Status', {
            'fields': ('status', 'retry_count', 'processing_result', 'error_message')
        }),
        ('Timestamps', {
            'fields': ('received_at', 'processed_at', 'next_retry_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('webhook_config', 'webhook_config__tiendanube_config')


@admin.register(WebhookDeliveryLog)
class WebhookDeliveryLogAdmin(admin.ModelAdmin):
    list_display = ['webhook_config', 'webhook_event', 'status', 'response_code', 'sent_at', 'request_duration']
    list_filter = ['status', 'response_code', 'sent_at']
    search_fields = ['webhook_config__webhook_url', 'webhook_event__event_id']
    readonly_fields = ['sent_at', 'received_at']
    
    fieldsets = (
        ('Delivery Information', {
            'fields': ('webhook_config', 'webhook_event', 'status', 'response_code')
        }),
        ('Response Data', {
            'fields': ('response_body', 'response_headers', 'error_message')
        }),
        ('Performance', {
            'fields': ('request_duration', 'payload_size')
        }),
        ('Timestamps', {
            'fields': ('sent_at', 'received_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('webhook_config', 'webhook_event')
