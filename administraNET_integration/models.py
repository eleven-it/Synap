from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from core.models.models import Empresa
from django.conf import settings


class AdministraNETConfig(models.Model):
    """
    Configuración principal de la integración con administraNET
    """
    # Configuración de conexión
    host = models.CharField(
        max_length=255,
        verbose_name=_('Host'),
        help_text=_('Host o IP del servidor MySQL de administraNET')
    )
    port = models.IntegerField(
        default=3306,
        validators=[MinValueValidator(1), MaxValueValidator(65535)],
        verbose_name=_('Puerto'),
        help_text=_('Puerto de conexión MySQL')
    )
    database_name = models.CharField(
        max_length=255,
        verbose_name=_('Nombre de Base de Datos'),
        help_text=_('Nombre de la base de datos de administraNET')
    )
    username = models.CharField(
        max_length=255,
        verbose_name=_('Usuario'),
        help_text=_('Usuario de MySQL')
    )
    password = models.CharField(
        max_length=255,
        verbose_name=_('Contraseña'),
        help_text=_('Contraseña de MySQL')
    )
    
    # Configuración de la integración
    is_active = models.BooleanField(
        default=False,
        verbose_name=_('Activa'),
        help_text=_('Activar o desactivar la integración')
    )
    sync_interval = models.IntegerField(
        default=30,
        validators=[MinValueValidator(1), MaxValueValidator(1440)],
        verbose_name=_('Intervalo de Sincronización (minutos)'),
        help_text=_('Intervalo en minutos para sincronización automática')
    )
    
    # Configuración de logs
    enable_logging = models.BooleanField(
        default=True,
        verbose_name=_('Habilitar Logs'),
        help_text=_('Registrar todas las operaciones de sincronización')
    )
    log_level = models.CharField(
        max_length=20,
        choices=[
            ('DEBUG', 'Debug'),
            ('INFO', 'Info'),
            ('WARNING', 'Warning'),
            ('ERROR', 'Error'),
        ],
        default='INFO',
        verbose_name=_('Nivel de Log'),
        help_text=_('Nivel de detalle para los logs')
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_sync = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Última Sincronización'),
        help_text=_('Fecha y hora de la última sincronización exitosa')
    )
    
    class Meta:
        verbose_name = _('Configuración administraNET')
        verbose_name_plural = _('Configuraciones administraNET')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Configuración administraNET - {self.database_name} ({'Activa' if self.is_active else 'Inactiva'})"
    
    def get_connection_string(self):
        """Obtener string de conexión para debugging"""
        return f"mysql://{self.username}@{self.host}:{self.port}/{self.database_name}"
    
    def get_connection_params(self):
        """Obtener parámetros de conexión como diccionario"""
        return {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': self.database_name,
            'USER': self.username,
            'PASSWORD': self.password,
            'HOST': self.host,
            'PORT': self.port,
            'OPTIONS': {
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            },
        }


class SyncLog(models.Model):
    """
    Log de sincronización para auditoría y debugging
    """
    SYNC_TYPES = [
        ('PRODUCTS', _('Productos')),
        ('STOCK', _('Stock')),
        ('CUSTOMERS', _('Clientes')),
        ('ORDERS', _('Pedidos')),
        ('SUPPLIERS', _('Proveedores')),
        ('CATEGORIES', _('Categorías')),
        ('BRANDS', _('Marcas')),
        ('FULL', _('Sincronización Completa')),
    ]
    
    SYNC_STATUS = [
        ('PENDING', _('Pendiente')),
        ('IN_PROGRESS', _('En Progreso')),
        ('COMPLETED', _('Completado')),
        ('FAILED', _('Falló')),
        ('CANCELLED', _('Cancelado')),
    ]
    
    sync_type = models.CharField(
        max_length=20,
        choices=SYNC_TYPES,
        verbose_name=_('Tipo de Sincronización')
    )
    status = models.CharField(
        max_length=20,
        choices=SYNC_STATUS,
        default='PENDING',
        verbose_name=_('Estado')
    )
    started_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Iniciado')
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Completado')
    )
    
    # Estadísticas
    records_processed = models.IntegerField(
        default=0,
        verbose_name=_('Registros Procesados')
    )
    records_created = models.IntegerField(
        default=0,
        verbose_name=_('Registros Creados')
    )
    records_updated = models.IntegerField(
        default=0,
        verbose_name=_('Registros Actualizados')
    )
    records_failed = models.IntegerField(
        default=0,
        verbose_name=_('Registros Fallidos')
    )
    
    # Información de error
    error_message = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Mensaje de Error')
    )
    error_details = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Detalles del Error')
    )
    
    # Usuario que inició la sincronización
    initiated_by = models.ForeignKey(
        'core.UsuarioExtendido',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('Iniciado por')
    )
    
    class Meta:
        verbose_name = _('Log de Sincronización')
        verbose_name_plural = _('Logs de Sincronización')
        ordering = ['-started_at']
    
    def __str__(self):
        return f"{self.get_sync_type_display()} - {self.get_status_display()} ({self.started_at.strftime('%Y-%m-%d %H:%M')})"
    
    @property
    def duration(self):
        """Duración de la sincronización"""
        if self.completed_at and self.started_at:
            return self.completed_at - self.started_at
        return None
    
    @property
    def success_rate(self):
        """Tasa de éxito de la sincronización"""
        if self.records_processed > 0:
            successful = self.records_created + self.records_updated
            return (successful / self.records_processed) * 100
        return 0
    
    def mark_completed(self, success=True, error_message=None):
        """Marcar sincronización como completada"""
        from django.utils import timezone
        
        self.status = 'COMPLETED' if success else 'FAILED'
        self.completed_at = timezone.now()
        
        if error_message:
            self.error_message = error_message
        
        self.save()


class TableMapping(models.Model):
    """
    Mapeo entre tablas de administraNET y modelos de Synap
    """
    MAPPING_TYPES = [
        ('PRODUCTS', _('Productos')),
        ('STOCK', _('Stock')),
        ('CUSTOMERS', _('Clientes')),
        ('ORDERS', _('Pedidos')),
        ('SUPPLIERS', _('Proveedores')),
        ('CATEGORIES', _('Categorías')),
        ('BRANDS', _('Marcas')),
        ('SUBCATEGORIES', _('Subcategorías')),
    ]
    
    mapping_type = models.CharField(
        max_length=20,
        choices=MAPPING_TYPES,
        verbose_name=_('Tipo de Mapeo')
    )
    administraNET_table = models.CharField(
        max_length=255,
        verbose_name=_('Tabla administraNET'),
        help_text=_('Nombre de la tabla en administraNET')
    )
    synap_model = models.CharField(
        max_length=255,
        verbose_name=_('Modelo Synap'),
        help_text=_('Nombre del modelo en Synap (app.model)')
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Activo'),
        help_text=_('Activar o desactivar este mapeo')
    )
    
    # Configuración de sincronización
    sync_direction = models.CharField(
        max_length=15,
        choices=[
            ('TO_SYNAP', _('Hacia Synap')),
            ('FROM_SYNAP', _('Desde Synap')),
            ('BIDIRECTIONAL', _('Bidireccional')),
        ],
        default='TO_SYNAP',
        verbose_name=_('Dirección de Sincronización')
    )
    
    # Campos mapeados
    field_mappings = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Mapeo de Campos'),
        help_text=_('Diccionario de mapeo de campos: {"campo_admin": "campo_synap"}')
    )
    
    # Configuración adicional
    sync_frequency = models.IntegerField(
        default=30,
        validators=[MinValueValidator(1), MaxValueValidator(1440)],
        verbose_name=_('Frecuencia de Sincronización (minutos)'),
        help_text=_('Frecuencia específica para este mapeo (0 = usar configuración global)')
    )
    
    # Configuración de mapeo predefinido
    use_preset_mapping = models.BooleanField(
        default=True,
        verbose_name=_('Usar Mapeo Predefinido'),
        help_text=_('Usar mapeo predefinido para este tipo')
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Mapeo de Tabla')
        verbose_name_plural = _('Mapeos de Tablas')
        unique_together = ['mapping_type', 'administraNET_table']
        ordering = ['mapping_type', 'administraNET_table']
    
    def __str__(self):
        return f"{self.get_mapping_type_display()} - {self.administraNET_table} → {self.synap_model}"
    
    def get_field_mapping(self, admin_field):
        """Obtener el campo de Synap correspondiente a un campo de administraNET"""
        return self.field_mappings.get(admin_field, admin_field)
    
    def get_admin_field(self, synap_field):
        """Obtener el campo de administraNET correspondiente a un campo de Synap"""
        for admin_field, synap_mapped in self.field_mappings.items():
            if synap_mapped == synap_field:
                return admin_field
        return synap_field
    
    @classmethod
    def get_preset_mappings(cls):
        """Obtener mapeos predefinidos para cada tipo"""
        return {
            'PRODUCTS': {
                'table': 'articulo',
                'model': 'inventory.Product',
                'fields': {
                    'codigo': 'sku',
                    'nombre': 'name',
                    'descripcion': 'description',
                    'precio': 'price',
                    'precio_costo': 'cost_price',
                    'codigo_marca': 'brand',
                    'codigo_rubro': 'category',
                    'codigo_subrubro': 'subcategory',
                    'anulado': 'is_active',
                    'codigo_barras': 'barcode',
                    'peso': 'weight_kg',
                    'volumen': 'volume_m3',
                    'ancho': 'width_cm',
                    'alto': 'height_cm',
                    'profundidad': 'depth_cm',
                }
            },
            'CUSTOMERS': {
                'table': 'cliente',
                'model': 'sales.Client',
                'fields': {
                    'codigo': 'code',
                    'nombre_cliente': 'name',
                    'nombre_fantasia': 'trade_name',
                    'cuit': 'tax_id',
                    'email': 'email',
                    'telefono': 'phone',
                    'celular': 'mobile',
                    'direccion': 'address',
                    'localidad': 'city',
                    'codigo_postal': 'postal_code',
                    'provincia': 'state',
                    'pais': 'country',
                    'limite_credito': 'credit_limit',
                    'condicion_pago': 'payment_terms',
                    'categoria': 'customer_category',
                    'estado': 'is_active',
                    'observaciones': 'notes',
                }
            },
            'CATEGORIES': {
                'table': 'rubro',
                'model': 'inventory.Category',
                'fields': {
                    'codigo_rubro': 'adminet_id',
                    'nombre_rubro': 'name',
                    'anulado': 'is_active',
                }
            },
            'BRANDS': {
                'table': 'marca',
                'model': 'inventory.Brand',
                'fields': {
                    'codigo_marca': 'adminet_id',
                    'nombre_marca': 'name',
                    'anulado': 'is_active',
                }
            },
            'SUBCATEGORIES': {
                'table': 'subrubro',
                'model': 'inventory.Subcategory',
                'fields': {
                    'id_subrubro': 'adminet_id',
                    'nombre_subrubro': 'name',
                    'codigo_rubro': 'category',
                    'anulado': 'is_active',
                }
            },
            'SUPPLIERS': {
                'table': 'proveedor',
                'model': 'purchases.Supplier',
                'fields': {
                    'codigo': 'code',
                    'nombre_proveedor': 'name',
                    'nombre_fantasia': 'trade_name',
                    'cuit': 'tax_id',
                    'email': 'email',
                    'telefono': 'phone',
                    'celular': 'mobile',
                    'direccion': 'address',
                    'localidad': 'city',
                    'codigo_postal': 'postal_code',
                    'provincia': 'state',
                    'pais': 'country',
                    'limite_credito': 'credit_limit',
                    'condicion_pago': 'payment_terms',
                    'estado': 'is_active',
                    'observaciones': 'notes',
                }
            },
            'STOCK': {
                'table': 'inventario',
                'model': 'inventory.StockMovement',
                'fields': {
                    'codigo_articulo': 'product',
                    'cantidad': 'quantity',
                    'tipo_movimiento': 'movement_type',
                    'fecha': 'date',
                    'motivo': 'reason',
                    'almacen': 'warehouse',
                }
            }
        }
    
    @classmethod
    def create_preset_mapping(cls, mapping_type, empresa=None):
        """Crear mapeo usando configuración predefinida"""
        presets = cls.get_preset_mappings()
        if mapping_type not in presets:
            raise ValueError(f"Tipo de mapeo no válido: {mapping_type}")
        
        preset = presets[mapping_type]
        
        # Verificar si ya existe un mapeo para este tipo
        existing = cls.objects.filter(mapping_type=mapping_type).first()
        if existing:
            return existing
        
        # Crear nuevo mapeo
        mapping = cls.objects.create(
            mapping_type=mapping_type,
            administraNET_table=preset['table'],
            synap_model=preset['model'],
            field_mappings=preset['fields'],
            use_preset_mapping=True,
            is_active=True,
            sync_direction='TO_SYNAP',
            sync_frequency=30
        )
        
        return mapping
    
    def update_from_preset(self):
        """Actualizar mapeo desde configuración predefinida"""
        if not self.use_preset_mapping:
            return
        
        presets = self.get_preset_mappings()
        if self.mapping_type not in presets:
            return
        
        preset = presets[self.mapping_type]
        self.administraNET_table = preset['table']
        self.synap_model = preset['model']
        self.field_mappings = preset['fields']
        self.save()


class ValidationRuleConfig(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='validation_configs', verbose_name=_('Company'))
    rule_code = models.CharField(max_length=100, verbose_name=_('Validation Rule'))
    is_active = models.BooleanField(default=True, verbose_name=_('Active'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, verbose_name=_('Modified by'))

    class Meta:
        unique_together = ('empresa', 'rule_code')
        verbose_name = _('Validation Rule Config')
        verbose_name_plural = _('Validation Rule Configs')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.empresa} - {self.rule_code} ({'Active' if self.is_active else 'Inactive'})"


class SyncTimestampLog(models.Model):
    """Log de conflictos de timestamp resueltos durante sincronización"""
    sync_log = models.ForeignKey(SyncLog, on_delete=models.CASCADE, related_name='timestamp_conflicts')
    record_type = models.CharField(_('Record Type'), max_length=50)  # PRODUCT, CUSTOMER, etc.
    record_id = models.CharField(_('Record ID'), max_length=100)
    synap_timestamp = models.DateTimeField(_('Synap Timestamp'))
    adminet_timestamp = models.DateTimeField(_('administraNET Timestamp'))
    winner = models.CharField(_('Winner'), max_length=20, choices=[
        ('SYNAP_WINS', _('Synap Wins')),
        ('ADMINET_WINS', _('administraNET Wins')),
        ('NO_CHANGE', _('No Change'))
    ])
    fields_updated = models.JSONField(_('Fields Updated'), default=list)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('Sync Timestamp Log')
        verbose_name_plural = _('Sync Timestamp Logs')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['sync_log', 'record_type']),
            models.Index(fields=['winner']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.record_type} {self.record_id} - {self.winner} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"


class SyncTimestampConfig(models.Model):
    """Configuración de sincronización basada en timestamps"""
    sync_type = models.CharField(_('Sync Type'), max_length=50, choices=[
        ('PRODUCTS', _('Products')),
        ('CUSTOMERS', _('Customers')),
        ('STOCK', _('Stock')),
        ('ORDERS', _('Orders')),
    ])
    enable_timestamp_resolution = models.BooleanField(_('Enable Timestamp Resolution'), default=True)
    sync_all_fields = models.BooleanField(_('Sync All Fields'), default=True, help_text=_('Always synchronize all editable fields'))
    log_conflicts = models.BooleanField(_('Log Conflicts'), default=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Sync Timestamp Config')
        verbose_name_plural = _('Sync Timestamp Configs')
        unique_together = ['sync_type']
        ordering = ['sync_type']
    
    def __str__(self):
        return f"{self.get_sync_type_display()} - {'Enabled' if self.enable_timestamp_resolution else 'Disabled'}"
