from rest_framework import serializers
from tiendanube.models import (
    Product, ProductVariant, StockQuant, StockMove,
    TiendaNubeConfig, TiendaNubeSyncLog, TiendaNubeProductMapping
)


class ProductSerializer(serializers.ModelSerializer):
    """Serializer para productos"""
    tiendanube_id = serializers.IntegerField(read_only=True)
    tiendanube_url = serializers.URLField(read_only=True)
    total_stock = serializers.SerializerMethodField()
    available_stock = serializers.SerializerMethodField()
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'sku', 'description', 'brand', 'handle',
            'price', 'price_currency', 'uom', 'tracking',
            'weight_kg', 'volume_m3', 'is_dangerous', 'barcode',
            'tiendanube_id', 'tiendanube_url', 'is_published',
            'total_stock', 'available_stock', 'created_at', 'updated_at'
        ]
    
    def get_total_stock(self, obj):
        """Calcula el stock total del producto"""
        return sum(quant.quantity for quant in obj.stockquant_set.all())
    
    def get_available_stock(self, obj):
        """Calcula el stock disponible del producto"""
        return sum(quant.available_quantity for quant in obj.stockquant_set.all())


class ProductVariantSerializer(serializers.ModelSerializer):
    """Serializer para variantes de productos"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    
    class Meta:
        model = ProductVariant
        fields = [
            'id', 'product', 'product_name', 'name', 'sku',
            'price', 'quantity', 'tiendanube_id'
        ]


class StockQuantSerializer(serializers.ModelSerializer):
    """Serializer para cantidades de stock"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    location_name = serializers.CharField(source='location.name', read_only=True)
    
    class Meta:
        model = StockQuant
        fields = [
            'id', 'product', 'product_name', 'product_sku',
            'location', 'location_name', 'lot', 'quantity',
            'reserved_quantity', 'available_quantity', 'last_updated'
        ]


class StockMoveSerializer(serializers.ModelSerializer):
    """Serializer para movimientos de stock"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    from_location_name = serializers.CharField(source='from_location.name', read_only=True)
    to_location_name = serializers.CharField(source='to_location.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = StockMove
        fields = [
            'id', 'product', 'product_name', 'product_sku',
            'quantity', 'from_location', 'from_location_name',
            'to_location', 'to_location_name', 'lot', 'move_type',
            'reference', 'origin', 'state', 'created_by', 'created_by_name',
            'validated_by', 'validated_at', 'timestamp'
        ]


class TiendaNubeConfigSerializer(serializers.ModelSerializer):
    """Serializer para configuración de TiendaNube"""
    is_configured = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = TiendaNubeConfig
        fields = [
            'id', 'store_id', 'access_token', 'webhook_secret',
            'api_url', 'auto_sync', 'sync_interval', 'last_sync',
            'sync_products', 'sync_stock', 'sync_variants',
            'webhook_url', 'webhook_active', 'is_configured',
            'created_at', 'updated_at'
        ]
        extra_kwargs = {
            'access_token': {'write_only': True},
            'webhook_secret': {'write_only': True}
        }
    
    def to_representation(self, instance):
        """Oculta información sensible en la respuesta"""
        data = super().to_representation(instance)
        if data.get('access_token'):
            data['access_token'] = '*' * 20
        if data.get('webhook_secret'):
            data['webhook_secret'] = '*' * 20
        return data


class TiendaNubeSyncLogSerializer(serializers.ModelSerializer):
    """Serializer para logs de sincronización"""
    config_store_id = serializers.CharField(source='config.store_id', read_only=True)
    duration_seconds = serializers.SerializerMethodField()
    
    class Meta:
        model = TiendaNubeSyncLog
        fields = [
            'id', 'config', 'config_store_id', 'sync_type', 'status',
            'message', 'details', 'items_processed', 'items_success',
            'items_failed', 'started_at', 'completed_at', 'duration_seconds'
        ]
    
    def get_duration_seconds(self, obj):
        """Calcula la duración en segundos"""
        if obj.duration:
            return obj.duration.total_seconds()
        return None


class TiendaNubeProductMappingSerializer(serializers.ModelSerializer):
    """Serializer para mapeo de productos"""
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    
    class Meta:
        model = TiendaNubeProductMapping
        fields = [
            'id', 'product', 'product_name', 'product_sku',
            'tiendanube_id', 'tiendanube_variant_id', 'tiendanube_handle',
            'last_synced', 'sync_status', 'sync_enabled', 'sync_price',
            'sync_stock', 'sync_description', 'error_message', 'needs_sync'
        ]


class SyncStatusSerializer(serializers.Serializer):
    """Serializer para estado de sincronización"""
    configured = serializers.BooleanField()
    auto_sync = serializers.BooleanField(required=False)
    last_sync = serializers.DateTimeField(required=False)
    total_products = serializers.IntegerField(required=False)
    synced_products = serializers.IntegerField(required=False)
    pending_products = serializers.IntegerField(required=False)
    error_products = serializers.IntegerField(required=False)
    sync_percentage = serializers.FloatField(required=False)


class SyncRequestSerializer(serializers.Serializer):
    """Serializer para solicitudes de sincronización"""
    limit = serializers.IntegerField(default=100, min_value=1, max_value=1000)
    offset = serializers.IntegerField(default=0, min_value=0)
    product_id = serializers.IntegerField(required=False)
    sync_type = serializers.ChoiceField(
        choices=['products', 'stock', 'full'],
        default='products'
    )


class WebhookRequestSerializer(serializers.Serializer):
    """Serializer para solicitudes de webhook"""
    webhook_url = serializers.URLField()
    events = serializers.ListField(
        child=serializers.CharField(),
        default=['product/created', 'product/updated', 'product/deleted', 'stock/updated']
    )


class ConnectionTestSerializer(serializers.Serializer):
    """Serializer para pruebas de conexión"""
    success = serializers.BooleanField()
    message = serializers.CharField()
    timestamp = serializers.DateTimeField()


class DashboardDataSerializer(serializers.Serializer):
    """Serializer para datos del dashboard"""
    sync_status = SyncStatusSerializer()
    statistics = serializers.DictField()
    recent_moves = serializers.ListField()
    low_stock_products = serializers.ListField() 