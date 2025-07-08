from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.core.cache import cache
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from core.mixins import ContactableMixin


class Empresa(models.Model):
    nombre = models.CharField(max_length=255, unique=True, verbose_name=_('Nombre de la empresa'))
    identificador_fiscal = models.CharField(max_length=32, unique=True, verbose_name=_('CUIT/RFC/NIF'))
    email = models.EmailField(blank=True, null=True, verbose_name=_('Email de contacto'))
    telefono = models.CharField(max_length=32, blank=True, null=True, verbose_name=_('Teléfono'))
    direccion = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Dirección'))
    pais = models.CharField(max_length=64, blank=True, null=True, verbose_name=_('País'))
    ciudad = models.CharField(max_length=64, blank=True, null=True, verbose_name=_('Ciudad'))
    logo = models.ImageField(upload_to='empresas/logos/', blank=True, null=True, verbose_name=_('Logo'))
    activa = models.BooleanField(default=True, verbose_name=_('Empresa activa'))
    fecha_creacion = models.DateTimeField(default=timezone.now, verbose_name=_('Fecha de creación'))
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name=_('Fecha de modificación'))

    class Meta:
        verbose_name = _('Empresa')
        verbose_name_plural = _('Empresas')
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Permiso(models.Model):
    codigo = models.CharField(max_length=50, unique=True, db_index=True)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, help_text=_("Detailed description of the permission"))
    modulo = models.CharField(max_length=50, blank=True, help_text=_("Module to which it belongs"))
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("Permission")
        verbose_name_plural = _("Permissions")
        ordering = ['modulo', 'codigo']

    def __str__(self):
        return f"{self.codigo} — {self.nombre}"


class Rol(models.Model):
    nombre = models.CharField(max_length=50, unique=True, db_index=True)
    descripcion = models.TextField(blank=True)
    permisos = models.ManyToManyField(Permiso, blank=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(default=timezone.now)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Role")
        verbose_name_plural = _("Roles")
        ordering = ['nombre']

    def __str__(self):
        return self.nombre

    @classmethod
    def get_administrador(cls):
        """Obtiene el rol administrador, creándolo si no existe"""
        rol, created = cls.objects.get_or_create(
            nombre__iexact="administrador",
            defaults={
                "nombre": "Administrador",
                "descripcion": "Rol con acceso total al sistema"
            }
        )
        return rol


class UsuarioManager(BaseUserManager):
    def create_user(self, email, nombre="", password=None):
        if not email:
            raise ValueError("El email es obligatorio.")
        user = self.model(email=self.normalize_email(email), nombre=nombre)
        user.set_password(password or self.model.objects.make_random_password())
        user.save(using=self._db)
        return user

    def create_superuser(self, email, nombre="", password=None):
        user = self.create_user(email, nombre, password)
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user

    def get_by_uid(self, uid):
        """Obtiene usuario por UID con cache"""
        cache_key = f"user_uid_{uid}"
        user = cache.get(cache_key)
        if user is None:
            try:
                user = self.get(uid=uid)
                cache.set(cache_key, user, 300)  # Cache por 5 minutos
            except self.model.DoesNotExist:
                user = None
        return user


class UsuarioExtendido(AbstractBaseUser, PermissionsMixin):
    uid = models.CharField(max_length=128, unique=True, db_index=True)
    email = models.EmailField(unique=True, db_index=True)
    nombre = models.CharField(max_length=100, blank=True)
    idioma = models.CharField(
        max_length=10,
        choices=[("es", _( "Spanish")), ("en", _( "English")), ("pt", _( "Portuguese"))],
        default="es"
    )
    roles = models.ManyToManyField(Rol, blank=True)
    permisos_extra = models.ManyToManyField(Permiso, blank=True, related_name="usuarios_con_permiso_directo")

    # 🔐 Requerido por Django Admin y middleware
    is_active = models.BooleanField(default=True, db_index=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    # 🔑 Firebase-based: no se usa directamente, pero se requiere por AbstractBaseUser
    password = models.CharField(max_length=128, blank=True)

    # 📊 Campos adicionales
    ultimo_acceso = models.DateTimeField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(default=timezone.now)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nombre']

    objects = UsuarioManager()

    class Meta:
        verbose_name = _("Extended User")
        verbose_name_plural = _("Extended Users")
        ordering = ['email']

    def is_admin(self):
        """Verifica si el usuario tiene rol administrador"""
        # Si el objeto no está guardado aún (no tiene pk), no puede tener roles.
        if self.pk is None:
            return False
        return self.roles.filter(nombre__iexact="administrador", activo=True).exists()

    def get_permisos_cache_key(self):
        """Genera clave de cache para permisos del usuario"""
        return f"user_permisos_{self.uid}_{self.fecha_modificacion.timestamp()}"

    def get_permisos_totales(self):
        """Obtiene todos los permisos del usuario con cache"""
        cache_key = self.get_permisos_cache_key()
        permisos = cache.get(cache_key)
        
        if permisos is None:
            permisos = set()
            if self.is_admin():
                permisos = {"*"}
            else:
                # Permisos de roles activos
                for rol in self.roles.filter(activo=True).prefetch_related('permisos'):
                    permisos.update(rol.permisos.filter(activo=True).values_list("codigo", flat=True))
                # Permisos directos activos
                permisos.update(self.permisos_extra.filter(activo=True).values_list("codigo", flat=True))
            
            cache.set(cache_key, permisos, 300)  # Cache por 5 minutos
        
        return permisos

    def tiene_permiso(self, codigo):
        """Verifica si el usuario tiene un permiso específico"""
        permisos = self.get_permisos_totales()
        return "*" in permisos or codigo in permisos

    def tiene_permiso_modulo(self, modulo):
        """Verifica si el usuario tiene algún permiso de un módulo específico"""
        permisos = self.get_permisos_totales()
        if "*" in permisos:
            return True
        return any(perm.startswith(f"{modulo}.") for perm in permisos)

    def actualizar_ultimo_acceso(self):
        """Actualiza el timestamp del último acceso"""
        self.ultimo_acceso = timezone.now()
        self.save(update_fields=['ultimo_acceso'])
        # Invalidar cache de permisos
        cache.delete(self.get_permisos_cache_key())

    def has_perm(self, perm, obj=None):
        return self.is_admin() or super().has_perm(perm, obj)

    def has_module_perms(self, app_label):
        return self.is_admin() or super().has_module_perms(app_label)

    def save(self, *args, **kwargs):
        # Sync flag de superuser si tiene el rol administrador
        self.is_superuser = self.is_admin()
        super().save(*args, **kwargs)
        # Invalidar cache
        cache.delete(self.get_permisos_cache_key())

    def __str__(self):
        return self.email

    @property
    def nombre_completo(self):
        return self.nombre or self.email.split('@')[0]

    @property
    def empresa_activa(self):
        from core.models import Empresa
        request = getattr(self, '_request', None)
        if request and 'empresa_id' in request.session:
            try:
                return Empresa.objects.get(id=request.session['empresa_id'])
            except Empresa.DoesNotExist:
                return None
        # Fallback: primera empresa a la que tiene acceso (ajustar según lógica de permisos)
        return Empresa.objects.first()

    @property
    def branch_activa(self):
        from core.models import Branch
        request = getattr(self, '_request', None)
        if request and 'branch_id' in request.session:
            try:
                return Branch.objects.get(id=request.session['branch_id'])
            except Branch.DoesNotExist:
                return None
        # Fallback: primera sucursal de la empresa activa
        empresa = self.empresa_activa
        return empresa.branches.first() if empresa else None


class Branch(models.Model):
    empresa = models.ForeignKey('Empresa', on_delete=models.CASCADE, related_name='branches', verbose_name=_('Company'))
    name = models.CharField(max_length=128, verbose_name=_('Branch Name'))
    code = models.CharField(max_length=32, blank=True, null=True, verbose_name=_('Internal Code'))
    address = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Address'))
    city = models.CharField(max_length=64, blank=True, null=True, verbose_name=_('City'))
    state = models.CharField(max_length=64, blank=True, null=True, verbose_name=_('State/Province'))
    country = models.CharField(max_length=64, blank=True, null=True, verbose_name=_('Country'))
    phone = models.CharField(max_length=32, blank=True, null=True, verbose_name=_('Phone'))
    email = models.EmailField(blank=True, null=True, verbose_name=_('Email'))
    active = models.BooleanField(default=True, verbose_name=_('Active'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created at'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Updated at'))

    class Meta:
        verbose_name = _('Branch')
        verbose_name_plural = _('Branches')
        ordering = ['empresa', 'name']

    def __str__(self):
        return f"{self.name} ({self.empresa.nombre})"


class DeliveryLocation(models.Model):
    """
    Modelo para gestionar ubicaciones de entrega en el sistema
    Diferente del modelo Location de inventory que maneja ubicaciones de materiales
    """
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='delivery_locations', verbose_name=_('Company'))
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='delivery_locations', verbose_name=_('Branch'))
    
    # Información básica
    name = models.CharField(_("Location Name"), max_length=255)
    address = models.TextField(_("Full Address"), blank=True)
    city = models.CharField(_("City"), max_length=100, blank=True)
    state = models.CharField(_("State/Province"), max_length=100, blank=True)
    country = models.CharField(_("Country"), max_length=100, blank=True)
    postal_code = models.CharField(_("Postal Code"), max_length=20, blank=True)
    
    # Información de contacto
    contact_name = models.CharField(_("Contact Person"), max_length=255, blank=True)
    contact_phone = models.CharField(_("Contact Phone"), max_length=32, blank=True)
    contact_email = models.EmailField(_("Contact Email"), blank=True)
    
    # Configuración
    is_active = models.BooleanField(_("Active"), default=True)
    is_default = models.BooleanField(_("Default Location"), default=False)
    notes = models.TextField(_("Additional Notes"), blank=True)
    
    # Auditoría
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated at"))

    class Meta:
        verbose_name = _("Delivery Location")
        verbose_name_plural = _("Delivery Locations")
        ordering = ['empresa', 'branch', 'name']
        indexes = [
            models.Index(fields=['empresa', 'branch']),
            models.Index(fields=['is_active']),
            models.Index(fields=['is_default']),
        ]

    def __str__(self):
        return f"{self.name} ({self.empresa.nombre} / {self.branch.name})"

    def save(self, *args, **kwargs):
        """Si se marca como default, desmarca otros de la misma empresa/sucursal"""
        if self.is_default:
            DeliveryLocation.objects.filter(
                empresa=self.empresa,
                branch=self.branch,
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)

    @property
    def full_address(self):
        """Retorna la dirección completa formateada"""
        parts = [self.address, self.city, self.state, self.postal_code, self.country]
        return ", ".join(filter(None, parts))

    @classmethod
    def get_default_for_branch(cls, empresa, branch):
        """Obtiene la ubicación por defecto para una empresa/sucursal"""
        try:
            return cls.objects.get(empresa=empresa, branch=branch, is_default=True, is_active=True)
        except cls.DoesNotExist:
            # Si no hay default, retorna la primera activa
            return cls.objects.filter(empresa=empresa, branch=branch, is_active=True).first()


# --- MODELO DE CONTACTO UNIVERSAL ---

class Contact(models.Model):
    """
    Modelo universal de contacto que puede estar vinculado a múltiples entidades:
    - Clientes (sales.Client)
    - Proveedores (purchases.Supplier) 
    - Empleados (core.UsuarioExtendido)
    - Otros contactos
    """
    
    # Información básica del contacto
    name = models.CharField(_('Name'), max_length=255)
    type = models.CharField(
        max_length=16,
        choices=[
            ('person', _('Person')),
            ('company', _('Company')),
            ('employee', _('Employee')),
        ],
        default='person',
        verbose_name=_('Contact Type')
    )
    
    # Información personal/profesional
    first_name = models.CharField(_('First Name'), max_length=100, blank=True)
    last_name = models.CharField(_('Last Name'), max_length=100, blank=True)
    company_name = models.CharField(_('Company Name'), max_length=255, blank=True)
    position = models.CharField(_('Position/Job Title'), max_length=100, blank=True)
    department = models.CharField(_('Department'), max_length=100, blank=True)
    
    # Datos de contacto
    email = models.EmailField(_('Email'), blank=True)
    phone = models.CharField(_('Phone'), max_length=32, blank=True)
    mobile = models.CharField(_('Mobile'), max_length=32, blank=True)
    fax = models.CharField(_('Fax'), max_length=32, blank=True)
    website = models.URLField(_('Website'), blank=True, null=True)
    
    # Dirección
    address = models.TextField(_('Address'), blank=True, null=True)
    postal_code = models.CharField(_('Postal Code'), max_length=20, blank=True, null=True)
    city = models.CharField(_('City'), max_length=100, blank=True, null=True)
    state = models.CharField(_('State/Province'), max_length=100, blank=True, null=True)
    country = models.CharField(_('Country'), max_length=100, default="Argentina", blank=True, null=True)
    
    # Ubicación geográfica
    latitude = models.DecimalField(_('Latitude'), max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(_('Longitude'), max_digits=9, decimal_places=6, blank=True, null=True)
    
    # Información adicional
    notes = models.TextField(_('Notes'), blank=True, null=True)
    tags = models.CharField(_('Tags'), max_length=255, blank=True, help_text=_('Comma-separated tags'))
    
    # Imagen
    photo = models.ImageField(_('Photo'), upload_to='contacts/photos/', blank=True, null=True)
    
    # Estado
    is_active = models.BooleanField(_('Active'), default=True)
    is_primary = models.BooleanField(_('Primary Contact'), default=False)
    
    # Auditoría
    created_at = models.DateTimeField(_('Created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated at'), auto_now=True)
    
    class Meta:
        verbose_name = _('Contact')
        verbose_name_plural = _('Contacts')
        ordering = ['name']
        indexes = [
            models.Index(fields=['type']),
            models.Index(fields=['is_active']),
            models.Index(fields=['email']),
            models.Index(fields=['company_name']),
        ]
    
    def __str__(self):
        if self.type == 'person':
            return f"{self.first_name} {self.last_name}".strip() or self.name
        elif self.type == 'company':
            return self.company_name or self.name
        return self.name
    
    def clean(self):
        """Validaciones del modelo"""
        from django.core.exceptions import ValidationError
        
        # Validar que al menos tenga nombre o nombre completo
        if not self.name and not (self.first_name or self.last_name):
            raise ValidationError(_('Contact must have a name or first/last name.'))
        
        # Validar que tenga al menos un método de contacto
        if not any([self.email, self.phone, self.mobile]):
            raise ValidationError(_('Contact must have at least one contact method (email, phone, or mobile).'))
    
    @property
    def full_name(self):
        """Nombre completo del contacto"""
        if self.type == 'person':
            return f"{self.first_name} {self.last_name}".strip()
        return self.name
    
    @property
    def display_name(self):
        """Nombre para mostrar"""
        if self.type == 'person':
            name = self.full_name
            if self.company_name:
                return f"{name} ({self.company_name})"
            return name
        elif self.type == 'company':
            return self.company_name or self.name
        return self.name
    
    @property
    def full_address(self):
        """Dirección completa formateada"""
        parts = []
        if self.address:
            parts.append(self.address)
        if self.city:
            parts.append(self.city)
        if self.state:
            parts.append(self.state)
        if self.postal_code:
            parts.append(self.postal_code)
        if self.country:
            parts.append(self.country)
        return ', '.join(parts) if parts else ''
    
    @property
    def google_maps_url(self):
        """URL de Google Maps para la ubicación"""
        if self.latitude and self.longitude:
            return f"https://maps.google.com/?q={self.latitude},{self.longitude}"
        elif self.full_address:
            return f"https://maps.google.com/?q={self.full_address}"
        return None


class ContactRelationship(models.Model):
    """
    Modelo para gestionar las relaciones entre contactos y entidades del sistema
    Permite que un contacto esté vinculado a múltiples entidades
    """
    
    # El contacto
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='relationships', verbose_name=_('Contact'))
    
    # Entidad relacionada (usando ContentType para flexibilidad)
    content_type = models.ForeignKey('contenttypes.ContentType', on_delete=models.CASCADE, verbose_name=_('Content Type'))
    object_id = models.PositiveIntegerField(_('Object ID'))
    related_object = GenericForeignKey('content_type', 'object_id')
    
    # Tipo de relación
    RELATIONSHIP_TYPES = [
        ('primary', _('Primary Contact')),
        ('secondary', _('Secondary Contact')),
        ('billing', _('Billing Contact')),
        ('technical', _('Technical Contact')),
        ('decision_maker', _('Decision Maker')),
        ('employee', _('Employee')),
        ('representative', _('Representative')),
        ('other', _('Other')),
    ]
    
    relationship_type = models.CharField(
        max_length=20,
        choices=RELATIONSHIP_TYPES,
        default='secondary',
        verbose_name=_('Relationship Type')
    )
    
    # Información adicional de la relación
    is_active = models.BooleanField(_('Active'), default=True)
    notes = models.TextField(_('Notes'), blank=True)
    
    # Fechas de la relación
    start_date = models.DateField(_('Start Date'), blank=True, null=True)
    end_date = models.DateField(_('End Date'), blank=True, null=True)
    
    # Auditoría
    created_at = models.DateTimeField(_('Created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated at'), auto_now=True)
    
    class Meta:
        verbose_name = _('Contact Relationship')
        verbose_name_plural = _('Contact Relationships')
        ordering = ['contact', 'relationship_type']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['relationship_type']),
            models.Index(fields=['is_active']),
        ]
        unique_together = ['contact', 'content_type', 'object_id', 'relationship_type']
    
    def __str__(self):
        return f"{self.contact.display_name} - {self.get_relationship_type_display()} ({self.related_object})"
    
    def clean(self):
        """Validaciones del modelo"""
        from django.core.exceptions import ValidationError
        
        # Validar que no haya relaciones duplicadas
        if ContactRelationship.objects.filter(
            contact=self.contact,
            content_type=self.content_type,
            object_id=self.object_id,
            relationship_type=self.relationship_type,
            is_active=True
        ).exclude(pk=self.pk).exists():
            raise ValidationError(_('This contact already has this type of relationship with this entity.'))
        
        # Validar fechas
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError(_('Start date cannot be after end date.'))
    
    @property
    def is_current(self):
        """Verifica si la relación está activa actualmente"""
        from django.utils import timezone
        today = timezone.now().date()
        
        if not self.is_active:
            return False
        
        if self.start_date and self.start_date > today:
            return False
        
        if self.end_date and self.end_date < today:
            return False
        
        return True


class Country(models.Model):
    """
    Modelo para gestionar países del mundo
    """
    name = models.CharField(_('Name'), max_length=100, unique=True)
    name_es = models.CharField(_('Name (Spanish)'), max_length=100, blank=True)
    name_en = models.CharField(_('Name (English)'), max_length=100, blank=True)
    name_pt = models.CharField(_('Name (Portuguese)'), max_length=100, blank=True)
    
    # Códigos estándar
    code = models.CharField(_('ISO Code'), max_length=3, unique=True, help_text=_('ISO 3166-1 alpha-3 code'))
    code_2 = models.CharField(_('ISO Code (2 letters)'), max_length=2, blank=True, help_text=_('ISO 3166-1 alpha-2 code'))
    
    # Información adicional
    phone_code = models.CharField(_('Phone Code'), max_length=10, blank=True, help_text=_('International calling code'))
    currency_code = models.CharField(_('Currency Code'), max_length=3, blank=True, help_text=_('ISO 4217 currency code'))
    timezone = models.CharField(_('Timezone'), max_length=50, blank=True, help_text=_('Primary timezone'))
    
    # Estado
    is_active = models.BooleanField(_('Active'), default=True)
    
    # Auditoría
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Country')
        verbose_name_plural = _('Countries')
        ordering = ['name']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return self.name

    def get_localized_name(self, language=None):
        """Obtiene el nombre en el idioma especificado"""
        if language == 'es' and self.name_es:
            return self.name_es
        elif language == 'en' and self.name_en:
            return self.name_en
        elif language == 'pt' and self.name_pt:
            return self.name_pt
        return self.name

    @classmethod
    def get_active_countries(cls):
        """Obtiene todos los países activos"""
        return cls.objects.filter(is_active=True).order_by('name')


class State(models.Model):
    """
    Modelo para gestionar estados/provincias de países
    """
    name = models.CharField(_('Name'), max_length=100)
    name_es = models.CharField(_('Name (Spanish)'), max_length=100, blank=True)
    name_en = models.CharField(_('Name (English)'), max_length=100, blank=True)
    name_pt = models.CharField(_('Name (Portuguese)'), max_length=100, blank=True)
    
    # Códigos
    code = models.CharField(_('Code'), max_length=10, blank=True, help_text=_('State/province code'))
    
    # Relación con país
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='states', verbose_name=_('Country'))
    
    # Estado
    is_active = models.BooleanField(_('Active'), default=True)
    
    # Auditoría
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('State/Province')
        verbose_name_plural = _('States/Provinces')
        ordering = ['country', 'name']
        indexes = [
            models.Index(fields=['country']),
            models.Index(fields=['is_active']),
        ]
        unique_together = ['country', 'name']

    def __str__(self):
        return f"{self.name}, {self.country.name}"

    def get_localized_name(self, language=None):
        """Obtiene el nombre en el idioma especificado"""
        if language == 'es' and self.name_es:
            return self.name_es
        elif language == 'en' and self.name_en:
            return self.name_en
        elif language == 'pt' and self.name_pt:
            return self.name_pt
        return self.name

    @classmethod
    def get_states_by_country(cls, country_id):
        """Obtiene estados por país"""
        return cls.objects.filter(country_id=country_id, is_active=True).order_by('name')


# --- MODELO BASE PARA ENTIDADES COMERCIALES ---

class BusinessEntity(ContactableMixin, models.Model):
    """
    Modelo base abstracto para entidades comerciales (clientes y proveedores)
    Contiene toda la funcionalidad común entre clientes y proveedores
    """
    
    # Información básica
    name = models.CharField(_("Name"), max_length=255)
    code = models.CharField(_("Code"), max_length=20, unique=True, null=True, blank=True, help_text=_("Internal business entity code"))
    tax_id = models.CharField(_("Tax ID"), max_length=50, blank=True, help_text=_("VAT number or tax identification"))
    
    # Dirección común
    address = models.TextField(_("Address"), blank=True, null=True)
    city = models.CharField(_("City"), max_length=100, blank=True, null=True)
    state = models.CharField(_("State/Province"), max_length=100, blank=True, null=True)
    postal_code = models.CharField(_("Postal Code"), max_length=20, blank=True, null=True)
    country = models.CharField(_("Country"), max_length=100, default="Argentina", blank=True, null=True)
    
    # Información de contacto principal (legacy - para compatibilidad)
    contact_person = models.CharField(_("Contact Person"), max_length=100, blank=True, null=True)
    email = models.EmailField(_("Email"), blank=True, null=True)
    phone = models.CharField(_("Phone"), max_length=20, blank=True, null=True)
    mobile = models.CharField(_("Mobile"), max_length=20, blank=True, null=True)
    
    # Información adicional
    website = models.URLField(_("Website"), blank=True, null=True)
    notes = models.TextField(_("Notes"), blank=True, null=True)
    
    # Estado
    is_active = models.BooleanField(_("Active"), default=True)
    
    # Auditoría
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['code']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    def clean(self):
        """Validaciones del modelo base"""
        from django.core.exceptions import ValidationError
        
        # Validar que tenga al menos un método de contacto (legacy o contactos universales)
        if not any([self.email, self.phone, self.mobile]) and not self.has_contacts:
            raise ValidationError(_('Business entity must have at least one contact method.'))
    
    def get_full_address(self):
        """Retorna la dirección completa formateada"""
        parts = [self.address, self.city, self.state, self.postal_code, self.country]
        return ", ".join(filter(None, parts))
    
    def get_contact_info(self):
        """Retorna la información de contacto principal (legacy)"""
        if self.email:
            return self.email
        elif self.phone:
            return self.phone
        elif self.mobile:
            return self.mobile
        return _("No contact information")
    
    @property
    def primary_contact(self):
        """
        Obtiene el contacto principal del sistema universal (compatibilidad)
        """
        return self.get_primary_contact_object()
    
    def get_contacts_by_type(self, relationship_type=None):
        """
        Obtiene contactos por tipo de relación (compatibilidad)
        """
        return self.get_contacts(relationship_type=relationship_type)
    
    def add_contact_relationship(self, contact, relationship_type='secondary', **kwargs):
        """
        Agrega un contacto con un tipo de relación específico (compatibilidad)
        """
        return self.add_contact(contact, relationship_type, **kwargs)

