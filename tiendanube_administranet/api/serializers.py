"""
Serializers para la API de integración Tiendanube-AdministraNET.
"""

from rest_framework import serializers
from django.utils import timezone

from ..models import (
    TiendanubeConfig, AdministraNETConfig, CustomerMapping,
    SyncLog, ProductMapping, OrderMapping
)


class TiendanubeConfigSerializer(serializers.ModelSerializer):
    """
    Serializer para configuraciones de Tiendanube.
    """
    
    class Meta:
        model = TiendanubeConfig
        fields = [
            'id', 'name', 'store_id', 'access_token', 'api_url', 
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'access_token': {'write_only': True}
        }
    
    def to_representation(self, instance):
        """Ocultar el token de acceso en las respuestas."""
        data = super().to_representation(instance)
        data['access_token'] = '***' if instance.access_token else None
        return data


class AdministraNETConfigSerializer(serializers.ModelSerializer):
    """
    Serializer para configuraciones de AdministraNET.

    La conexión MySQL usa el pool de Synap; solo se expone el esquema y parámetros de integración.
    """

    class Meta:
        model = AdministraNETConfig
        fields = [
            'id',
            'name',
            'database',
            'deposito_tiendanube_id',
            'sucursal_tiendanube_id',
            'punto_venta_tiendanube_id',
            'viajante_tiendanube_id',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'database', 'created_at', 'updated_at']


class CustomerMappingSerializer(serializers.ModelSerializer):
    """
    Serializer para mapeos de clientes.
    """
    
    # Campos calculados
    needs_sync = serializers.ReadOnlyField()
    is_fully_mapped = serializers.ReadOnlyField()
    
    # Información adicional
    sync_status_display = serializers.CharField(source='get_sync_status_display', read_only=True)
    sync_direction_display = serializers.CharField(source='get_sync_direction_display', read_only=True)
    
    class Meta:
        model = CustomerMapping
        fields = [
            'id', 'tiendanube_id', 'tiendanube_email', 'tiendanube_name',
            'tiendanube_document', 'tiendanube_phone', 'tiendanube_address',
            'adminet_codigo', 'adminet_nombre', 'adminet_documento',
            'adminet_telefono', 'adminet_direccion', 'sync_direction',
            'sync_status', 'sync_enabled', 'last_synced', 'error_message',
            'created_at', 'updated_at', 'needs_sync', 'is_fully_mapped',
            'sync_status_display', 'sync_direction_display'
        ]
        read_only_fields = [
            'id', 'last_synced', 'created_at', 'updated_at',
            'needs_sync', 'is_fully_mapped', 'sync_status_display', 'sync_direction_display'
        ]
    
    def validate_tiendanube_email(self, value):
        """Validar que el email sea único."""
        if not value:
            return value
        
        # Verificar si ya existe un mapeo con este email
        existing = CustomerMapping.objects.filter(tiendanube_email=value)
        if self.instance:
            existing = existing.exclude(id=self.instance.id)
        
        if existing.exists():
            raise serializers.ValidationError("Ya existe un mapeo con este email.")
        
        return value
    
    def validate(self, data):
        """Validar que al menos una plataforma tenga datos."""
        tiendanube_email = data.get('tiendanube_email')
        adminet_codigo = data.get('adminet_codigo')
        
        if not tiendanube_email and not adminet_codigo:
            raise serializers.ValidationError(
                "Debe proporcionar al menos un email de Tiendanube o un código de AdministraNET."
            )
        
        return data


class SyncLogSerializer(serializers.ModelSerializer):
    """
    Serializer para logs de sincronización.
    """
    
    # Campos calculados
    duration = serializers.ReadOnlyField()
    
    # Información adicional
    sync_type_display = serializers.CharField(source='get_sync_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    platform_display = serializers.CharField(source='get_platform_display', read_only=True)
    
    # Información del mapeo relacionado
    mapping_email = serializers.CharField(source='mapping.tiendanube_email', read_only=True)
    
    class Meta:
        model = SyncLog
        fields = [
            'id', 'sync_type', 'status', 'platform', 'mapping', 'message',
            'details', 'items_processed', 'items_success', 'items_failed',
            'started_at', 'completed_at', 'duration', 'sync_type_display',
            'status_display', 'platform_display', 'mapping_email'
        ]
        read_only_fields = [
            'id', 'items_processed', 'items_success', 'items_failed',
            'started_at', 'completed_at', 'duration', 'sync_type_display',
            'status_display', 'platform_display', 'mapping_email'
        ]


class ProductMappingSerializer(serializers.ModelSerializer):
    """
    Serializer para mapeos de productos.
    """
    
    # Información adicional
    sync_status_display = serializers.CharField(source='get_sync_status_display', read_only=True)
    
    class Meta:
        model = ProductMapping
        fields = [
            'id', 'tiendanube_id', 'tiendanube_name', 'tiendanube_sku',
            'tiendanube_price', 'tiendanube_stock', 'adminet_codigo',
            'adminet_nombre', 'adminet_precio', 'adminet_stock',
            'sync_status', 'sync_enabled', 'last_synced', 'error_message',
            'created_at', 'updated_at', 'sync_status_display'
        ]
        read_only_fields = [
            'id', 'last_synced', 'created_at', 'updated_at', 'sync_status_display'
        ]


class OrderMappingSerializer(serializers.ModelSerializer):
    """
    Serializer para mapeos de órdenes.
    """
    
    # Información adicional
    sync_status_display = serializers.CharField(source='get_sync_status_display', read_only=True)
    order_status_display = serializers.CharField(source='get_tiendanube_status_display', read_only=True)
    
    class Meta:
        model = OrderMapping
        fields = [
            'id', 'tiendanube_id', 'tiendanube_number', 'tiendanube_status',
            'tiendanube_total', 'tiendanube_customer_email', 'adminet_codigo',
            'adminet_numero', 'adminet_estado', 'adminet_total',
            'sync_status', 'sync_enabled', 'last_synced', 'error_message',
            'created_at', 'updated_at', 'sync_status_display', 'order_status_display'
        ]
        read_only_fields = [
            'id', 'last_synced', 'created_at', 'updated_at', 
            'sync_status_display', 'order_status_display'
        ]


class SyncStatisticsSerializer(serializers.Serializer):
    """
    Serializer para estadísticas de sincronización.
    """
    
    total_mappings = serializers.IntegerField()
    synced_mappings = serializers.IntegerField()
    pending_mappings = serializers.IntegerField()
    error_mappings = serializers.IntegerField()
    tiendanube_mappings = serializers.IntegerField()
    adminet_mappings = serializers.IntegerField()
    sync_percentage = serializers.FloatField()


class SyncResultSerializer(serializers.Serializer):
    """
    Serializer para resultados de sincronización.
    """
    
    success = serializers.BooleanField()
    message = serializers.CharField()
    success_count = serializers.IntegerField()
    failed_count = serializers.IntegerField()
    total_processed = serializers.IntegerField()
    timestamp = serializers.DateTimeField()


class ConnectionTestSerializer(serializers.Serializer):
    """
    Serializer para pruebas de conexión.
    """
    
    success = serializers.BooleanField()
    message = serializers.CharField()
    error = serializers.CharField(required=False)
    details = serializers.DictField(required=False)


class BulkSyncRequestSerializer(serializers.Serializer):
    """
    Serializer para solicitudes de sincronización masiva.
    """
    
    mapping_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        max_length=100
    )
    direction = serializers.ChoiceField(
        choices=[
            ('auto', 'Automático'),
            ('to_tiendanube', 'Hacia Tiendanube'),
            ('to_adminet', 'Hacia AdministraNET')
        ],
        default='auto'
    )


class BulkSyncResultSerializer(serializers.Serializer):
    """
    Serializer para resultados de sincronización masiva.
    """
    
    success = serializers.BooleanField()
    results = serializers.ListField(
        child=serializers.DictField()
    )
    summary = serializers.DictField() 