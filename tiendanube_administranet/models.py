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
    
    # Configuración de sincronización automática
    auto_sync = models.BooleanField(
        default=True, 
        verbose_name=_("Auto Sync"),
        help_text=_("Habilitar sincronización automática")
    )
    sync_interval = models.IntegerField(
        default=30,
        verbose_name=_("Sync Interval (minutes)"),
        help_text=_("Intervalo en minutos para sincronización automática")
    )
    last_sync = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name=_("Last Sync"),
        help_text=_("Última sincronización realizada")
    )
    
    # Configuración de qué sincronizar
    sync_products = models.BooleanField(
        default=True,
        verbose_name=_("Sync Products"),
        help_text=_("Sincronizar productos")
    )
    sync_customers = models.BooleanField(
        default=True,
        verbose_name=_("Sync Customers"),
        help_text=_("Sincronizar clientes")
    )
    sync_orders = models.BooleanField(
        default=True,
        verbose_name=_("Sync Orders"),
        help_text=_("Sincronizar pedidos")
    )
    sync_stock = models.BooleanField(
        default=True,
        verbose_name=_("Sync Stock"),
        help_text=_("Sincronizar stock")
    )
    
    # Configuración de webhooks
    webhook_secret = models.CharField(
        max_length=255, 
        blank=True, 
        verbose_name=_("Webhook Secret"),
        help_text=_("Secret para verificación de webhooks de TiendaNube")
    )
    
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
    Parámetros de integración con AdministraNET.

    La conexión TCP a MySQL usa el pool compartido de Synap (``settings.DATABASES['mysql']``,
    habitualmente definido en ``.env``). Este modelo guarda el **nombre de esquema** (base)
    que debe alinearse con ``base_empresa`` de la sesión, más IDs operativos (depósito, etc.).
    """

    name = models.CharField(max_length=100, verbose_name=_("Configuration Name"))
    database = models.CharField(
        max_length=255,
        verbose_name=_("Base de datos (esquema MySQL)"),
        help_text=_(
            "Nombre del esquema de AdministraNET; en la app web se alinea automáticamente con "
            "la empresa en sesión (base_empresa). Host y credenciales: pool Synap (.env)."
        ),
    )
    deposito_tiendanube_id = models.IntegerField(
        null=True, 
        blank=True, 
        verbose_name=_("Depósito TiendaNube"),
        help_text=_("ID del depósito en AdministraNET que se sincronizará con TiendaNube")
    )
    sucursal_tiendanube_id = models.IntegerField(
        default=1,
        verbose_name=_("Sucursal Tiendanube ID"),
        help_text=_("ID de la sucursal para órdenes de Tiendanube")
    )
    punto_venta_tiendanube_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_("Punto de Venta Tiendanube ID"),
        help_text=_("ID del punto de venta para numeración de comprobantes (ej: 0001-00000001)")
    )
    viajante_tiendanube_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name=_("Vendedor Tiendanube ID"),
        help_text=_("ID del vendedor para órdenes de Tiendanube")
    )
    is_active = models.BooleanField(default=True, verbose_name=_("Active"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        verbose_name = _("AdministraNET Configuration")
        verbose_name_plural = _("AdministraNET Configurations")
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.database})"


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
    adminet_email = models.EmailField(blank=True, verbose_name=_("Email AdministraNET"))
    adminet_documento = models.CharField(max_length=50, blank=True, verbose_name=_("AdministraNET Document"))
    adminet_telefono = models.CharField(max_length=50, blank=True, verbose_name=_("AdministraNET Phone"))
    
    # Campos de dirección de AdministraNET (datos de la cuenta del cliente)
    adminet_calle = models.CharField(max_length=255, blank=True, verbose_name=_("Calle AdministraNET"))
    adminet_nro_calle = models.CharField(max_length=20, blank=True, verbose_name=_("Número Calle AdministraNET"))
    adminet_dpto = models.CharField(max_length=50, blank=True, verbose_name=_("Departamento AdministraNET"))
    
    # Campo de dirección combinada (para compatibilidad)
    adminet_direccion = models.TextField(blank=True, verbose_name=_("AdministraNET Address"))
    
    # Campos de ubicación (relaciones con tablas de referencia - datos de la cuenta)
    adminet_id_distrito = models.IntegerField(blank=True, null=True, verbose_name=_("ID Distrito AdministraNET"))
    adminet_cod_provincia = models.IntegerField(blank=True, null=True, verbose_name=_("Código Provincia AdministraNET"))
    adminet_id_departamento = models.IntegerField(blank=True, null=True, verbose_name=_("ID Departamento AdministraNET"))
    
    # Campos de configuración y estado
    adminet_tipo_cliente = models.IntegerField(blank=True, null=True, verbose_name=_("Tipo Cliente AdministraNET"))
    adminet_cod_viajante = models.IntegerField(blank=True, null=True, verbose_name=_("Código Viajante AdministraNET"))
    adminet_id_pais = models.IntegerField(blank=True, null=True, verbose_name=_("ID País AdministraNET"))
    adminet_estado = models.CharField(max_length=30, blank=True, verbose_name=_("Estado AdministraNET"))
    adminet_tipo_doc = models.CharField(max_length=10, blank=True, verbose_name=_("Tipo Documento AdministraNET"))
    adminet_lista_precio = models.CharField(max_length=60, blank=True, verbose_name=_("Lista Precio AdministraNET"))
    adminet_fecha_alta = models.DateTimeField(blank=True, null=True, verbose_name=_("Fecha Alta AdministraNET"))
    adminet_fecha_ultima_compra = models.DateField(blank=True, null=True, verbose_name=_("Fecha Última Compra AdministraNET"))
    
    # Campos adicionales importantes
    adminet_cuit = models.CharField(max_length=20, blank=True, verbose_name=_("CUIT AdministraNET"))
    adminet_credito = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, verbose_name=_("Crédito AdministraNET"))
    adminet_descuento = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, verbose_name=_("Descuento AdministraNET"))
    adminet_observaciones = models.TextField(blank=True, verbose_name=_("Observaciones AdministraNET"))
    adminet_saldo = models.DecimalField(max_digits=25, decimal_places=2, blank=True, null=True, verbose_name=_("Saldo AdministraNET"))
    adminet_id_manual_cli = models.CharField(max_length=200, blank=True, verbose_name=_("ID Manual Cliente AdministraNET"))
    adminet_nombre_fantasia = models.CharField(max_length=300, blank=True, verbose_name=_("Nombre Fantasía AdministraNET"))
    adminet_cliente_ecommerce = models.CharField(max_length=5, blank=True, verbose_name=_("Cliente Ecommerce AdministraNET"))
    
    # Campos para manejo de datos incompletos
    datos_completos = models.BooleanField(default=False, verbose_name=_("Datos Completos"))
    fecha_registro_incompleto = models.DateTimeField(null=True, blank=True, verbose_name=_("Fecha Registro Incompleto"))
    intentos_completar_datos = models.IntegerField(default=0, verbose_name=_("Intentos Completar Datos"))
    ultimo_intento_completar = models.DateTimeField(null=True, blank=True, verbose_name=_("Último Intento Completar"))
    
    # Estado del workflow de completado
    workflow_estado = models.CharField(
        max_length=20,
        choices=[
            ('incompleto', 'Datos Incompletos'),
            ('pendiente', 'Pendiente de Completar'),
            ('completo', 'Datos Completos'),
            ('abandonado', 'Abandonado'),
        ],
        default='incompleto',
        verbose_name=_("Estado del Workflow")
    )

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

    def combine_adminet_address(self):
        """
        Combina los campos de dirección de AdministraNET en un solo string.
        Formato: "Calle NroCalle Dpto"
        """
        parts = []
        if self.adminet_calle:
            parts.append(self.adminet_calle.strip())
        if self.adminet_nro_calle:
            parts.append(self.adminet_nro_calle.strip())
        if self.adminet_dpto:
            parts.append(self.adminet_dpto.strip())
        
        combined = ' '.join(parts)
        self.adminet_direccion = combined
        return combined

    def parse_tiendanube_address(self, address_string):
        """
        Parsea la dirección de Tiendanube y la separa en campos de AdministraNET.
        Tiendanube: "Calle 1234 Depto 5B"
        AdministraNET: Calle="Calle", NroCalle="1234", Dpto="Depto 5B"
        """
        if not address_string:
            return
        
        # Algoritmo de parsing inteligente
        address_parts = address_string.strip().split()
        
        if len(address_parts) >= 2:
            # Buscar el número (primer grupo de dígitos)
            number_index = -1
            for i, part in enumerate(address_parts):
                if part.replace('.', '').isdigit():
                    number_index = i
                    break
            
            if number_index > 0:
                # Calle: todo antes del número
                self.adminet_calle = ' '.join(address_parts[:number_index])
                # Número: el número encontrado
                self.adminet_nro_calle = address_parts[number_index]
                # Departamento: todo después del número
                if number_index + 1 < len(address_parts):
                    self.adminet_dpto = ' '.join(address_parts[number_index + 1:])
                else:
                    self.adminet_dpto = ''
            else:
                # No se encontró número, todo va en calle
                self.adminet_calle = address_string
                self.adminet_nro_calle = ''
                self.adminet_dpto = ''
        else:
            # Solo una palabra, va en calle
            self.adminet_calle = address_string
            self.adminet_nro_calle = ''
            self.adminet_dpto = ''
        
        # Actualizar el campo combinado
        self.combine_adminet_address()

    def get_tiendanube_address(self):
        """
        Obtiene la dirección formateada para Tiendanube desde los campos de AdministraNET.
        """
        return self.combine_adminet_address()

    def sync_address_to_tiendanube(self):
        """
        Sincroniza la dirección desde AdministraNET hacia Tiendanube.
        """
        if self.adminet_calle or self.adminet_nro_calle or self.adminet_dpto:
            self.tiendanube_address = self.get_tiendanube_address()

    def sync_address_from_tiendanube(self):
        """
        Sincroniza la dirección desde Tiendanube hacia AdministraNET.
        """
        if self.tiendanube_address:
            self.parse_tiendanube_address(self.tiendanube_address)


class AdministraNETTipoCliente(models.Model):
    """
    Modelo para la tabla tipo_cliente de AdministraNET.
    """
    id_tipo_cliente = models.IntegerField(primary_key=True, verbose_name=_("ID Tipo Cliente"))
    nombre_tipo_cliente = models.CharField(max_length=50, blank=True, verbose_name=_("Nombre Tipo Cliente"))
    anulado = models.CharField(max_length=5, blank=True, verbose_name=_("Anulado"))

    class Meta:
        verbose_name = _("AdministraNET Tipo Cliente")
        verbose_name_plural = _("AdministraNET Tipos Cliente")
        db_table = 'tipo_cliente'

    def __str__(self):
        return f"{self.nombre_tipo_cliente}"


class AdministraNETDepartamento(models.Model):
    """
    Modelo para la tabla departamento de AdministraNET.
    """
    id_departamento = models.IntegerField(primary_key=True, verbose_name=_("ID Departamento"))
    nombre_departamento = models.CharField(max_length=50, blank=True, verbose_name=_("Nombre Departamento"))
    cod_provincia = models.IntegerField(verbose_name=_("Código Provincia"))
    anulado = models.CharField(max_length=5, blank=True, verbose_name=_("Anulado"))
    cod_postal = models.CharField(max_length=50, blank=True, verbose_name=_("Código Postal"))

    class Meta:
        verbose_name = _("AdministraNET Departamento")
        verbose_name_plural = _("AdministraNET Departamentos")
        db_table = 'departamento'

    def __str__(self):
        return f"{self.nombre_departamento}"


class AdministraNETProvincia(models.Model):
    """
    Modelo para la tabla provincia de AdministraNET.
    """
    cod_provincia = models.IntegerField(primary_key=True, verbose_name=_("Código Provincia"))
    provincia = models.CharField(max_length=100, blank=True, verbose_name=_("Provincia"))
    anulado = models.CharField(max_length=5, blank=True, verbose_name=_("Anulado"))
    id_pais = models.IntegerField(blank=True, null=True, verbose_name=_("ID País"))
    cod_afip = models.IntegerField(blank=True, null=True, verbose_name=_("Código AFIP"))
    id_juridic_convenio = models.IntegerField(blank=True, null=True, verbose_name=_("ID Jurídico Convenio"))
    id_pc = models.IntegerField(blank=True, null=True, verbose_name=_("ID PC"))

    class Meta:
        verbose_name = _("AdministraNET Provincia")
        verbose_name_plural = _("AdministraNET Provincias")
        db_table = 'provincia'

    def __str__(self):
        return f"{self.provincia}"


class AdministraNETDistrito(models.Model):
    """
    Modelo para la tabla distrito de AdministraNET.
    """
    id_distrito = models.IntegerField(primary_key=True, verbose_name=_("ID Distrito"))
    id_departamento = models.IntegerField(blank=True, null=True, verbose_name=_("ID Departamento"))
    nombre_distrito = models.CharField(max_length=50, blank=True, verbose_name=_("Nombre Distrito"))
    anulado = models.CharField(max_length=5, blank=True, verbose_name=_("Anulado"))
    cod_postal = models.CharField(max_length=50, blank=True, verbose_name=_("Código Postal"))

    class Meta:
        verbose_name = _("AdministraNET Distrito")
        verbose_name_plural = _("AdministraNET Distritos")
        db_table = 'distrito'

    def __str__(self):
        return f"{self.nombre_distrito}"


class AdministraNETViajante(models.Model):
    """
    Modelo para la tabla viajantes de AdministraNET.
    """
    cod_viajante = models.IntegerField(primary_key=True, verbose_name=_("Código Viajante"))
    nombre = models.CharField(max_length=50, blank=True, verbose_name=_("Nombre"))
    comision_vta = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True, verbose_name=_("Comisión Venta"))
    comision_cob = models.DecimalField(max_digits=15, decimal_places=2, verbose_name=_("Comisión Cobro"))
    zona = models.CharField(max_length=50, blank=True, verbose_name=_("Zona"))
    observaciones = models.CharField(max_length=255, blank=True, verbose_name=_("Observaciones"))
    anulado = models.CharField(max_length=5, blank=True, verbose_name=_("Anulado"))
    web_desc_renglon = models.CharField(max_length=2, blank=True, verbose_name=_("Web Desc Renglón"))
    web_desc_pie = models.CharField(max_length=2, blank=True, verbose_name=_("Web Desc Pie"))
    web_cliente_todos = models.CharField(max_length=2, blank=True, verbose_name=_("Web Cliente Todos"))
    cobrador = models.CharField(max_length=2, blank=True, verbose_name=_("Cobrador"))
    clave_caja = models.CharField(max_length=50, blank=True, verbose_name=_("Clave Caja"))
    logueado = models.CharField(max_length=2, blank=True, verbose_name=_("Logueado"))
    detalle_logueo = models.CharField(max_length=500, blank=True, verbose_name=_("Detalle Logueo"))
    ip_logueo = models.CharField(max_length=30, blank=True, verbose_name=_("IP Logueo"))
    comisiones_avanzadas = models.CharField(max_length=2, blank=True, verbose_name=_("Comisiones Avanzadas"))

    class Meta:
        verbose_name = _("AdministraNET Viajante")
        verbose_name_plural = _("AdministraNET Viajantes")
        db_table = 'viajantes'

    def __str__(self):
        return f"{self.nombre}"


class AdministraNETPais(models.Model):
    """
    Modelo para la tabla pais de AdministraNET.
    """
    id_pais = models.IntegerField(primary_key=True, verbose_name=_("ID País"))
    nombre = models.CharField(max_length=100, blank=True, verbose_name=_("Nombre"))
    anulado = models.CharField(max_length=2, blank=True, verbose_name=_("Anulado"))

    class Meta:
        verbose_name = _("AdministraNET País")
        verbose_name_plural = _("AdministraNET Países")
        db_table = 'pais'

    def __str__(self):
        return f"{self.nombre}"


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
    tiendanube_brand = models.CharField(max_length=255, blank=True, verbose_name=_("Tiendanube Brand"))
    tiendanube_categories = models.JSONField(default=list, blank=True, verbose_name=_("Tiendanube Categories"))
    tiendanube_tags = models.JSONField(default=list, blank=True, verbose_name=_("Tiendanube Tags"))
    tiendanube_images = models.JSONField(default=list, blank=True, verbose_name=_("Tiendanube Images"))
    tiendanube_videos = models.JSONField(default=list, blank=True, verbose_name=_("Tiendanube Videos"))
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
    adminet_promo_destacado = models.CharField(max_length=2, blank=True, null=True, verbose_name=_("Promo Destacado AdministraNET"))
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
    tiendanube_product_id = models.BigIntegerField(null=True, blank=True, verbose_name=_("Tiendanube Product ID"))
    tiendanube_options = models.JSONField(default=list, blank=True, verbose_name=_("Tiendanube Variant Options"))
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
    tiendanube_total = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name=_("Tiendanube Total"))
    tiendanube_currency = models.CharField(max_length=10, blank=True, verbose_name=_("Tiendanube Currency"))
    tiendanube_status = models.CharField(max_length=50, blank=True, verbose_name=_("Tiendanube Status"))
    tiendanube_payment_status = models.CharField(max_length=50, blank=True, verbose_name=_("Tiendanube Payment Status"))
    tiendanube_notes = models.TextField(blank=True, verbose_name=_("Tiendanube Notes"))
    tiendanube_customer_id = models.BigIntegerField(null=True, blank=True, verbose_name=_("Tiendanube Customer ID"))
    tiendanube_customer_email = models.EmailField(blank=True, verbose_name=_("Tiendanube Customer Email"))
    tiendanube_customer_name = models.CharField(max_length=255, blank=True, verbose_name=_("Tiendanube Customer Name"))
    tiendanube_shipping_address = models.JSONField(default=dict, blank=True, verbose_name=_("Tiendanube Shipping Address"))
    tiendanube_billing_address = models.JSONField(default=dict, blank=True, verbose_name=_("Tiendanube Billing Address"))
    tiendanube_payment_method = models.CharField(max_length=100, blank=True, verbose_name=_("Tiendanube Payment Method"))
    tiendanube_shipping_method = models.CharField(max_length=100, blank=True, verbose_name=_("Tiendanube Shipping Method"))
    tiendanube_created_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Tiendanube Created At"))
    tiendanube_updated_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Tiendanube Updated At"))

    # Campos de AdministraNET
    adminet_codigo = models.CharField(max_length=50, null=True, blank=True, verbose_name=_("AdministraNET Code"))
    adminet_numero = models.CharField(max_length=50, blank=True, verbose_name=_("AdministraNET Number"))
    adminet_estado = models.CharField(max_length=50, blank=True, verbose_name=_("AdministraNET Status"))
    adminet_total = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name=_("AdministraNET Total"))
    
    # Campos de dirección de entrega (AdministraNET)
    adminet_direccion_entrega = models.TextField(blank=True, verbose_name=_("Dirección de Entrega AdministraNET"))
    adminet_calle_entrega = models.CharField(max_length=255, blank=True, verbose_name=_("Calle Entrega AdministraNET"))
    adminet_nro_calle_entrega = models.CharField(max_length=20, blank=True, verbose_name=_("Número Calle Entrega AdministraNET"))
    adminet_dpto_entrega = models.CharField(max_length=50, blank=True, verbose_name=_("Departamento Entrega AdministraNET"))
    adminet_ciudad_entrega = models.CharField(max_length=100, blank=True, verbose_name=_("Ciudad Entrega AdministraNET"))
    adminet_provincia_entrega = models.CharField(max_length=100, blank=True, verbose_name=_("Provincia Entrega AdministraNET"))
    adminet_codigo_postal_entrega = models.CharField(max_length=20, blank=True, verbose_name=_("Código Postal Entrega AdministraNET"))
    
    # Campos de dirección de facturación (AdministraNET)
    adminet_direccion_facturacion = models.TextField(blank=True, verbose_name=_("Dirección de Facturación AdministraNET"))
    adminet_calle_facturacion = models.CharField(max_length=255, blank=True, verbose_name=_("Calle Facturación AdministraNET"))
    adminet_nro_calle_facturacion = models.CharField(max_length=20, blank=True, verbose_name=_("Número Calle Facturación AdministraNET"))
    adminet_dpto_facturacion = models.CharField(max_length=50, blank=True, verbose_name=_("Departamento Facturación AdministraNET"))
    adminet_ciudad_facturacion = models.CharField(max_length=100, blank=True, verbose_name=_("Ciudad Facturación AdministraNET"))
    adminet_provincia_facturacion = models.CharField(max_length=100, blank=True, verbose_name=_("Provincia Facturación AdministraNET"))
    adminet_codigo_postal_facturacion = models.CharField(max_length=20, blank=True, verbose_name=_("Código Postal Facturación AdministraNET"))

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
        # Calcular duración: mínimo 1 segundo para que se muestre en la UI
        duration = (self.completed_at - self.started_at).total_seconds()
        self.duration_seconds = max(1, round(duration))
        
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


class FieldMappingConfig(models.Model):
    """
    Configuración dinámica de mapeos de campos entre Tiendanube y AdministraNET.
    Permite configurar los mapeos sin modificar código.
    """
    class MappingType(models.TextChoices):
        CUSTOMER = 'customer', _('Customer')
        PRODUCT = 'product', _('Product')
        ORDER = 'order', _('Order')
        VARIANT = 'variant', _('Product Variant')
        CATEGORY = 'category', _('Category')

    class FieldType(models.TextChoices):
        ADMINET = 'adminet', _('AdministraNET')
        TIENDANUBE = 'tiendanube', _('Tiendanube')

    # Configuración básica
    mapping_type = models.CharField(
        max_length=20,
        choices=MappingType.choices,
        verbose_name=_("Mapping Type")
    )
    field_type = models.CharField(
        max_length=20,
        choices=FieldType.choices,
        verbose_name=_("Field Type")
    )
    
    # Información del campo
    field_name = models.CharField(max_length=100, verbose_name=_("Field Name"))
    field_display_name = models.CharField(max_length=200, verbose_name=_("Display Name"))
    field_description = models.TextField(blank=True, verbose_name=_("Field Description"))
    
    # Configuración de mapeo
    is_mappable = models.BooleanField(default=True, verbose_name=_("Is Mappable"))
    is_required = models.BooleanField(default=False, verbose_name=_("Is Required"))
    is_primary_key = models.BooleanField(default=False, verbose_name=_("Is Primary Key"))
    
    # Mapeo con campo correspondiente
    mapped_to_field = models.CharField(
        max_length=100, 
        blank=True, 
        verbose_name=_("Mapped To Field"),
        help_text=_("Field name in the other system")
    )
    mapping_notes = models.TextField(blank=True, verbose_name=_("Mapping Notes"))
    
    # Configuración de transformación
    transformation_type = models.CharField(
        max_length=50,
        choices=[
            ('direct', 'Direct Mapping'),
            ('address_parse', 'Address Parsing'),
            ('name_mapping', 'Name Mapping'),
            ('custom', 'Custom Transformation'),
        ],
        default='direct',
        verbose_name=_("Transformation Type")
    )
    transformation_config = models.JSONField(
        default=dict, 
        blank=True, 
        verbose_name=_("Transformation Configuration")
    )
    
    # Estado y orden
    is_active = models.BooleanField(default=True, verbose_name=_("Active"))
    display_order = models.IntegerField(default=0, verbose_name=_("Display Order"))
    
    # Metadatos
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        verbose_name = _("Field Mapping Configuration")
        verbose_name_plural = _("Field Mapping Configurations")
        ordering = ['mapping_type', 'field_type', 'display_order']
        unique_together = ['mapping_type', 'field_type', 'field_name']

    def __str__(self):
        return f"{self.get_mapping_type_display()} - {self.get_field_type_display()} - {self.field_name}"

    @classmethod
    def get_mappings_for_type(cls, mapping_type: str, field_type: str = None):
        """Obtener todos los mapeos para un tipo específico."""
        queryset = cls.objects.filter(
            mapping_type=mapping_type,
            is_active=True
        )
        if field_type:
            queryset = queryset.filter(field_type=field_type)
        return queryset.order_by('display_order')

    @classmethod
    def get_mappable_fields(cls, mapping_type: str, field_type: str = None):
        """Obtener solo campos mapeables."""
        return cls.get_mappings_for_type(mapping_type, field_type).filter(is_mappable=True)

    def get_mapped_field_info(self):
        """Obtener información del campo mapeado."""
        if not self.mapped_to_field:
            return None
        
        return FieldMappingConfig.objects.filter(
            mapping_type=self.mapping_type,
            field_name=self.mapped_to_field,
            is_active=True
        ).first()
