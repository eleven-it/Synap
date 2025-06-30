from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.core.cache import cache
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


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

