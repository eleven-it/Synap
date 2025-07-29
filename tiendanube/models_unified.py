from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

class TiendaNubeUnifiedCustomerMapping(models.Model):
    """
    Modelo unificado para mapeo de clientes entre Synap, Tiendanube y AdministraNET.
    Reemplaza TiendaNubeCustomerMapping y TiendaNubeClienteMap con lógica unificada.
    """
    
    class SyncStatus(models.TextChoices):
        SYNCED = 'synced', _('Synced')
        PENDING = 'pending', _('Pending')
        ERROR = 'error', _('Error')
        CONFLICT = 'conflict', _('Conflict')
    
    class SyncDirection(models.TextChoices):
        BIDIRECTIONAL = 'bidirectional', _('Bidirectional')
        TIENDANUBE_TO_SYNAP = 'tiendanube_to_synap', _('Tiendanube → Synap')
        SYNAP_TO_TIENDANUBE = 'synap_to_tiendanube', _('Synap → Tiendanube')
        ADMINET_ONLY = 'adminet_only', _('AdministraNET Only')
    
    # Campos de Tiendanube
    tiendanube_id = models.BigIntegerField(unique=True, null=True, blank=True, verbose_name=_("Tiendanube ID"))
    tiendanube_email = models.EmailField(unique=True, verbose_name=_("Tiendanube Email"))
    tiendanube_document = models.CharField(max_length=50, blank=True, verbose_name=_("Tiendanube Document"))
    
    # Campos de Synap
    synap_client = models.OneToOneField('sales.Client', on_delete=models.CASCADE, null=True, blank=True, verbose_name=_("Synap Client"))
    synap_contact = models.OneToOneField('core.Contact', on_delete=models.CASCADE, null=True, blank=True, verbose_name=_("Synap Contact"))
    
    # Campos de AdministraNET
    adminet_codigo = models.IntegerField(null=True, blank=True, verbose_name=_("AdministraNET Code"))
    adminet_nombre = models.CharField(max_length=255, blank=True, verbose_name=_("AdministraNET Name"))
    adminet_documento = models.CharField(max_length=50, blank=True, verbose_name=_("AdministraNET Document"))
    
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
        verbose_name = _("Unified Customer Mapping")
        verbose_name_plural = _("Unified Customer Mappings")
        ordering = ['tiendanube_email']
        indexes = [
            models.Index(fields=['tiendanube_email']),
            models.Index(fields=['adminet_codigo']),
            models.Index(fields=['sync_status']),
            models.Index(fields=['sync_enabled']),
        ]
    
    def __str__(self):
        if self.tiendanube_email:
            return f"{self.tiendanube_email} → {self.adminet_codigo or 'N/A'}"
        return f"Mapping {self.id}"
    
    @property
    def needs_sync(self):
        """Verifica si el mapeo necesita sincronización."""
        return self.sync_enabled and self.sync_status != self.SyncStatus.SYNCED
    
    @property
    def is_fully_mapped(self):
        """Verifica si el mapeo está completo en todas las plataformas."""
        has_tiendanube = bool(self.tiendanube_id and self.tiendanube_email)
        has_synap = bool(self.synap_client or self.synap_contact)
        has_adminet = bool(self.adminet_codigo)
        
        return has_tiendanube and has_synap and has_adminet
    
    def get_primary_email(self):
        """Obtiene el email principal para identificación."""
        if self.tiendanube_email:
            return self.tiendanube_email
        if self.synap_contact and self.synap_contact.email:
            return self.synap_contact.email
        if self.synap_client and self.synap_client.email:
            return self.synap_client.email
        return None
    
    def get_primary_name(self):
        """Obtiene el nombre principal."""
        if self.adminet_nombre:
            return self.adminet_nombre
        if self.synap_contact:
            return self.synap_contact.display_name
        if self.synap_client:
            return self.synap_client.name
        return "Cliente sin nombre"
    
    def get_primary_document(self):
        """Obtiene el documento principal."""
        if self.tiendanube_document:
            return self.tiendanube_document
        if self.adminet_documento:
            return self.adminet_documento
        if self.synap_contact and self.synap_contact.notes:
            return self.synap_contact.notes
        if self.synap_client and self.synap_client.document_number:
            return self.synap_client.document_number
        return None
    
    def update_sync_status(self, status, error_message=""):
        """Actualiza el estado de sincronización."""
        self.sync_status = status
        if error_message:
            self.error_message = error_message
        self.save(update_fields=['sync_status', 'error_message', 'last_synced'])
    
    def can_sync_to_tiendanube(self):
        """Verifica si puede sincronizar hacia Tiendanube."""
        return (
            self.sync_enabled and
            self.sync_direction in [self.SyncDirection.BIDIRECTIONAL, self.SyncDirection.SYNAP_TO_TIENDANUBE] and
            (self.synap_client or self.synap_contact)
        )
    
    def can_sync_from_tiendanube(self):
        """Verifica si puede sincronizar desde Tiendanube."""
        return (
            self.sync_enabled and
            self.sync_direction in [self.SyncDirection.BIDIRECTIONAL, self.SyncDirection.TIENDANUBE_TO_SYNAP] and
            self.tiendanube_id
        )
    
    def can_sync_with_adminet(self):
        """Verifica si puede sincronizar con AdministraNET."""
        return (
            self.sync_enabled and
            self.adminet_codigo is not None
        )


class TiendaNubeUnifiedSyncLog(models.Model):
    """
    Log unificado para todas las operaciones de sincronización de clientes.
    """
    
    class SyncType(models.TextChoices):
        CUSTOMER_SYNC = 'customer_sync', _('Customer Sync')
        MAPPING_CREATE = 'mapping_create', _('Mapping Create')
        MAPPING_UPDATE = 'mapping_update', _('Mapping Update')
        MAPPING_DELETE = 'mapping_delete', _('Mapping Delete')
        ADMINET_SYNC = 'adminet_sync', _('AdministraNET Sync')
    
    class Status(models.TextChoices):
        SUCCESS = 'success', _('Success')
        ERROR = 'error', _('Error')
        PARTIAL = 'partial', _('Partial')
        WARNING = 'warning', _('Warning')
    
    class Platform(models.TextChoices):
        TIENDANUBE = 'tiendanube', _('Tiendanube')
        SYNAP = 'synap', _('Synap')
        ADMINET = 'adminet', _('AdministraNET')
    
    # Campos básicos
    sync_type = models.CharField(max_length=20, choices=SyncType.choices, verbose_name=_("Sync Type"))
    status = models.CharField(max_length=20, choices=Status.choices, verbose_name=_("Status"))
    platform = models.CharField(max_length=20, choices=Platform.choices, verbose_name=_("Platform"))
    
    # Referencias
    mapping = models.ForeignKey(
        TiendaNubeUnifiedCustomerMapping, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        verbose_name=_("Customer Mapping")
    )
    
    # Detalles
    message = models.TextField(verbose_name=_("Message"))
    details = models.JSONField(default=dict, blank=True, verbose_name=_("Details"))
    
    # Métricas
    items_processed = models.IntegerField(default=0, verbose_name=_("Items Processed"))
    items_success = models.IntegerField(default=0, verbose_name=_("Items Success"))
    items_failed = models.IntegerField(default=0, verbose_name=_("Items Failed"))
    
    # Timestamps
    started_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Started At"))
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Completed At"))
    
    class Meta:
        verbose_name = _("Unified Sync Log")
        verbose_name_plural = _("Unified Sync Logs")
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['sync_type']),
            models.Index(fields=['status']),
            models.Index(fields=['platform']),
            models.Index(fields=['started_at']),
        ]
    
    def __str__(self):
        return f"{self.get_sync_type_display()} - {self.get_status_display()} ({self.platform})"
    
    @property
    def duration(self):
        """Calcula la duración de la sincronización."""
        if self.completed_at:
            return self.completed_at - self.started_at
        return None
    
    def mark_completed(self):
        """Marca la sincronización como completada."""
        from django.utils import timezone
        self.completed_at = timezone.now()
        self.save(update_fields=['completed_at'])


class TiendaNubeUnifiedConfig(models.Model):
    """
    Configuración unificada para sincronización de clientes.
    """
    
    class SyncMode(models.TextChoices):
        MANUAL = 'manual', _('Manual')
        AUTOMATIC = 'automatic', _('Automatic')
        SCHEDULED = 'scheduled', _('Scheduled')
    
    # Configuración general
    name = models.CharField(max_length=100, verbose_name=_("Configuration Name"))
    is_active = models.BooleanField(default=True, verbose_name=_("Active"))
    sync_mode = models.CharField(
        max_length=20, 
        choices=SyncMode.choices, 
        default=SyncMode.MANUAL,
        verbose_name=_("Sync Mode")
    )
    
    # Configuración de Tiendanube
    tiendanube_store_id = models.CharField(max_length=50, blank=True, verbose_name=_("Tiendanube Store ID"))
    tiendanube_access_token = models.CharField(max_length=255, blank=True, verbose_name=_("Tiendanube Access Token"))
    tiendanube_api_url = models.URLField(default="https://api.tiendanube.com/v1", verbose_name=_("Tiendanube API URL"))
    
    # Configuración de AdministraNET
    adminet_host = models.CharField(max_length=255, blank=True, verbose_name=_("AdministraNET Host"))
    adminet_port = models.IntegerField(default=3306, verbose_name=_("AdministraNET Port"))
    adminet_database = models.CharField(max_length=100, blank=True, verbose_name=_("AdministraNET Database"))
    adminet_user = models.CharField(max_length=100, blank=True, verbose_name=_("AdministraNET User"))
    adminet_password = models.CharField(max_length=255, blank=True, verbose_name=_("AdministraNET Password"))
    
    # Configuración de sincronización
    sync_interval = models.IntegerField(default=30, verbose_name=_("Sync Interval (minutes)"))
    batch_size = models.IntegerField(default=100, verbose_name=_("Batch Size"))
    max_retries = models.IntegerField(default=3, verbose_name=_("Max Retries"))
    
    # Configuración de notificaciones
    notify_on_error = models.BooleanField(default=True, verbose_name=_("Notify on Error"))
    notify_email = models.EmailField(blank=True, verbose_name=_("Notification Email"))
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))
    last_sync = models.DateTimeField(null=True, blank=True, verbose_name=_("Last Sync"))
    
    class Meta:
        verbose_name = _("Unified Configuration")
        verbose_name_plural = _("Unified Configurations")
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.get_sync_mode_display()})"
    
    @property
    def is_configured(self):
        """Verifica si la configuración está completa."""
        has_tiendanube = bool(self.tiendanube_store_id and self.tiendanube_access_token)
        has_adminet = bool(
            self.adminet_host and 
            self.adminet_database and 
            self.adminet_user and 
            self.adminet_password
        )
        return has_tiendanube or has_adminet
    
    def get_tiendanube_config(self):
        """Obtiene la configuración de Tiendanube."""
        return {
            'store_id': self.tiendanube_store_id,
            'access_token': self.tiendanube_access_token,
            'api_url': self.tiendanube_api_url,
        }
    
    def get_adminet_config(self):
        """Obtiene la configuración de AdministraNET."""
        return {
            'host': self.adminet_host,
            'port': self.adminet_port,
            'database': self.adminet_database,
            'user': self.adminet_user,
            'password': self.adminet_password,
        } 