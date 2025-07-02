from django.db.models.signals import m2m_changed, post_save, pre_delete
from django.dispatch import receiver
from django.core.cache import cache
from django.utils import timezone
from .models import UsuarioExtendido, Rol, Permiso
from .utils import registrar_actividad_usuario, limpiar_cache_usuario
import logging

logger = logging.getLogger(__name__)


@receiver(m2m_changed, sender=UsuarioExtendido.roles.through)
def sincronizar_roles_con_superuser(sender, instance, action, **kwargs):
    """Sincroniza el flag is_superuser cuando cambian los roles del usuario"""
    if action in ["post_add", "post_remove", "post_clear"]:
        tiene_rol_admin = instance.roles.filter(nombre__iexact="administrador", activo=True).exists()
        
        if tiene_rol_admin and not instance.is_superuser:
            instance.is_superuser = True
            instance.save(update_fields=['is_superuser'])
            logger.info(f"Usuario {instance.email} promovido a superuser")
        elif not tiene_rol_admin and instance.is_superuser:
            instance.is_superuser = False
            instance.save(update_fields=['is_superuser'])
            logger.info(f"Usuario {instance.email} degradado de superuser")
        
        # Limpiar cache del usuario
        limpiar_cache_usuario(instance)


@receiver(m2m_changed, sender=UsuarioExtendido.permisos_extra.through)
def auditar_cambios_permisos_directos(sender, instance, action, **kwargs):
    """Audita cambios en permisos directos del usuario"""
    if action in ["post_add", "post_remove", "post_clear"]:
        # Registrar actividad
        detalles = {
            "accion": f"permisos_directos_{action}",
            "usuario_afectado": instance.email,
            "timestamp": timezone.now().isoformat()
        }
        
        if action == "post_add":
            pk_set = kwargs.get('pk_set', set())
            permisos_agregados = Permiso.objects.filter(id__in=pk_set)
            detalles["permisos_agregados"] = list(permisos_agregados.values_list('codigo', flat=True))
        elif action == "post_remove":
            pk_set = kwargs.get('pk_set', set())
            permisos_removidos = Permiso.objects.filter(id__in=pk_set)
            detalles["permisos_removidos"] = list(permisos_removidos.values_list('codigo', flat=True))
        
        registrar_actividad_usuario(instance, "cambio_permisos_directos", detalles)
        
        # Limpiar cache
        limpiar_cache_usuario(instance)


@receiver(m2m_changed, sender=Rol.permisos.through)
def auditar_cambios_permisos_rol(sender, instance, action, **kwargs):
    """Audita cambios en permisos de roles"""
    if action in ["post_add", "post_remove", "post_clear"]:
        # Obtener usuarios afectados por este cambio de rol
        usuarios_afectados = instance.usuarioextendido_set.all()
        
        detalles = {
            "accion": f"permisos_rol_{action}",
            "rol": instance.nombre,
            "usuarios_afectados": list(usuarios_afectados.values_list('email', flat=True)),
            "timestamp": timezone.now().isoformat()
        }
        
        if action == "post_add":
            pk_set = kwargs.get('pk_set', set())
            permisos_agregados = Permiso.objects.filter(id__in=pk_set)
            detalles["permisos_agregados"] = list(permisos_agregados.values_list('codigo', flat=True))
        elif action == "post_remove":
            pk_set = kwargs.get('pk_set', set())
            permisos_removidos = Permiso.objects.filter(id__in=pk_set)
            detalles["permisos_removidos"] = list(permisos_removidos.values_list('codigo', flat=True))
        
        # Registrar actividad para cada usuario afectado
        for usuario in usuarios_afectados:
            registrar_actividad_usuario(usuario, "cambio_permisos_rol", detalles)
            limpiar_cache_usuario(usuario)


@receiver(post_save, sender=UsuarioExtendido)
def auditar_cambios_usuario(sender, instance, created, **kwargs):
    """Audita cambios en usuarios"""
    if created:
        registrar_actividad_usuario(instance, "usuario_creado", {
            "email": instance.email,
            "nombre": instance.nombre,
            "idioma": instance.idioma
        })
    else:
        # Para cambios específicos, podríamos implementar un sistema de tracking
        # Por ahora solo registramos que hubo un cambio
        logger.info(f"Usuario {instance.email} actualizado")


@receiver(pre_delete, sender=UsuarioExtendido)
def auditar_eliminacion_usuario(sender, instance, **kwargs):
    """Audita eliminación de usuarios"""
    registrar_actividad_usuario(instance, "usuario_eliminado", {
        "email": instance.email,
        "nombre": instance.nombre,
        "roles": list(instance.roles.values_list('nombre', flat=True)),
        "permisos_directos": list(instance.permisos_extra.values_list('codigo', flat=True))
    })


@receiver(post_save, sender=Rol)
def auditar_cambios_rol(sender, instance, created, **kwargs):
    """Audita cambios en roles"""
    if created:
        logger.info(f"Rol creado: {instance.nombre}")
    else:
        logger.info(f"Rol {instance.nombre} actualizado")
        
        # Limpiar cache de usuarios con este rol
        usuarios_afectados = instance.usuarioextendido_set.all()
        for usuario in usuarios_afectados:
            limpiar_cache_usuario(usuario)


@receiver(post_save, sender=Permiso)
def auditar_cambios_permiso(sender, instance, created, **kwargs):
    """Audita cambios en permisos"""
    if created:
        logger.info(f"Permiso creado: {instance.codigo} - {instance.nombre}")
    else:
        logger.info(f"Permiso {instance.codigo} actualizado")
        
        # Limpiar cache de usuarios con este permiso (relación inversa correcta)
        usuarios_afectados = instance.usuarios_con_permiso_directo.all()
        for usuario in usuarios_afectados:
            limpiar_cache_usuario(usuario)


# Signal para sincronización con Firebase
@receiver(post_save, sender=UsuarioExtendido)
def sincronizar_usuario_firebase(sender, instance, created, **kwargs):
    """Sincroniza cambios de usuario con Firebase"""
    try:
        from firebase_admin import firestore
        
        firestore_db = firestore.client()
        doc_ref = firestore_db.collection("usuarios").document(instance.uid)
        
        # Evita el error al acceder a M2M en un objeto recién creado.
        # Si es nuevo, los roles están vacíos. Si no, los consultamos.
        roles_nombres = []
        if not created:
            roles_nombres = list(instance.roles.filter(activo=True).values_list("nombre", flat=True))

        datos_usuario = {
            "email": instance.email,
            "nombre": instance.nombre,
            "idioma": instance.idioma,
            "is_active": instance.is_active,
            "roles": roles_nombres,
            "ultimo_acceso": instance.ultimo_acceso.isoformat() if instance.ultimo_acceso else None,
            "fecha_modificacion": instance.fecha_modificacion.isoformat()
        }
        
        doc_ref.set(datos_usuario, merge=True)
        logger.debug(f"Usuario {instance.email} sincronizado con Firebase")
        
    except Exception as e:
        logger.error(f"Error sincronizando usuario {instance.email} con Firebase: {e}")


# Signal para limpiar cache cuando se modifica configuración del sistema
@receiver(post_save, sender='core.SystemConfiguration')
def limpiar_cache_configuracion(sender, instance, **kwargs):
    """Limpia cache cuando cambia la configuración del sistema"""
    # Limpiar cache de configuración
    cache.delete('system_config')
    cache.delete('currency_config')
    cache.delete('uom_config')
    logger.info("Cache de configuración del sistema limpiado")
