from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.core.cache import cache
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


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

