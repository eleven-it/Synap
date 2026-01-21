# core/views_usuarios.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.views.decorators.csrf import csrf_protect
from core.models import Permiso, Rol
from core.decorators import tiene_permiso
from core.constantes_permisos import PERMISOS_POR_MODULO
from core.utils import permisos_contextuales
from core.services.administranet_users import AdministraNETUserService
from core.services.administranet_validacion_puestos import AdministraNETValidacionPuestosService
import logging

logger = logging.getLogger(__name__)


@tiene_permiso("administrar.usuarios")
def usuarios_admin_view(request):
    """
    Vista principal de administración de usuarios
    Usa AdministraNETUserService para gestionar usuarios directamente en MySQL de administraNET
    """
    context = permisos_contextuales(request, "usuarios.ver", roles_permitidos=["Administrador"], debug=True)
    if not context.get("puede_usuarios_ver") and not context.get("rol_permitido"):
        return render(request, "core/403.html", context, status=403)

    # Obtener datos de la sesión del usuario actual
    session_user = request.session.get("user", {})
    base_empresa = session_user.get("base_empresa")
    id_empresa = session_user.get("id_empresa")
    
    if not base_empresa:
        messages.error(request, "No se pudo determinar la empresa activa.")
        return redirect("core:dashboard")
    
    # Inicializar servicio
    user_service = AdministraNETUserService()
    
    # Búsqueda
    q = request.GET.get("q", "").strip()
    solo_activos = request.GET.get("activos", "true").lower() == "true"
    
    # Obtener usuarios desde MySQL de administraNET
    usuarios = user_service.listar_usuarios(
        base_empresa=base_empresa,
        id_empresa=id_empresa,
        busqueda=q if q else None,
        solo_activos=solo_activos
    )
    
    # Paginación manual
    paginator = Paginator(usuarios, 15)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    
    # Obtener puestos y sucursales para formularios
    puestos = user_service.obtener_puestos(base_empresa)
    sucursales = user_service.obtener_sucursales(base_empresa)

    context.update({
        "usuarios": page_obj,
        "puestos": puestos,
        "sucursales": sucursales,
        "q": q,
        "solo_activos": solo_activos,
        "base_empresa": base_empresa,
        "id_empresa": id_empresa,
    })
    return render(request, "core/usuarios_admin.html", context)


@tiene_permiso("administrar.usuarios")
@csrf_protect
def crear_usuario_view(request):
    """
    Vista para crear un nuevo usuario en administraNET
    Similar a ABMUsuarios.frm - Agregar
    """
    # Obtener datos de la sesión del usuario actual
    session_user = request.session.get("user", {})
    base_empresa = session_user.get("base_empresa")
    id_empresa = session_user.get("id_empresa")
    
    if not base_empresa or not id_empresa:
        messages.error(request, "No se pudo determinar la empresa activa.")
        return redirect("core:usuarios")
    
    # Inicializar servicio
    user_service = AdministraNETUserService()
    
    if request.method == "POST":
        cod_usuario = request.POST.get("cod_usuario", "").strip().lower()
        nombre_usuario = request.POST.get("nombre_usuario", "").strip()
        apellido_usuario = request.POST.get("apellido_usuario", "").strip()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirmar_password", "")
        id_puesto = request.POST.get("id_puesto")
        id_sucursal = request.POST.get("id_sucursal")
        
        # Validaciones
        if not cod_usuario or not password or not confirm_password or not nombre_usuario:
            messages.error(request, "Completa todos los campos obligatorios.")
            puestos = user_service.obtener_puestos(base_empresa)
            sucursales = user_service.obtener_sucursales(base_empresa)
            return render(request, "core/usuarios_crear.html", {
                'puestos': puestos,
                'sucursales': sucursales,
                'base_empresa': base_empresa,
            })
        
        if password != confirm_password:
            messages.error(request, "Las contraseñas no coinciden.")
            puestos = user_service.obtener_puestos(base_empresa)
            sucursales = user_service.obtener_sucursales(base_empresa)
            return render(request, "core/usuarios_crear.html", {
                'puestos': puestos,
                'sucursales': sucursales,
                'base_empresa': base_empresa,
            })
        
        # Verificar si el usuario ya existe
        usuarios_existentes = user_service.listar_usuarios(base_empresa, id_empresa, busqueda=cod_usuario, solo_activos=False)
        if any(u['cod_usuario'].lower() == cod_usuario.lower() for u in usuarios_existentes):
            messages.error(request, f"El usuario '{cod_usuario}' ya existe.")
            puestos = user_service.obtener_puestos(base_empresa)
            sucursales = user_service.obtener_sucursales(base_empresa)
            return render(request, "core/usuarios_crear.html", {
                'puestos': puestos,
                'sucursales': sucursales,
                'base_empresa': base_empresa,
            })
        
        # Preparar datos del usuario
        datos_usuario = {
            'cod_usuario': cod_usuario,
            'nombre_usuario': nombre_usuario,
            'apellido_usuario': apellido_usuario,
            'password': password,
            'id_puesto': int(id_puesto) if id_puesto else None,
            'id_sucursal': int(id_sucursal) if id_sucursal else None,
            'baja_usuario': 'No',
            'tipo_busqueda_defecto': 0,
            'permiso_supervisor_venta': 'No',
            'vendedor_web': 'No',
            'zoom_reportes': 100,
        }
        
        # Validar integridad del puesto antes de crear el usuario
        if id_puesto:
            validacion_service = AdministraNETValidacionPuestosService()
            validacion = validacion_service.validar_integridad_puesto(base_empresa, int(id_puesto))
            
            if not validacion['valido']:
                messages.error(request, f"⚠️ El puesto seleccionado tiene problemas de integridad: {', '.join(validacion['errores'])}")
                puestos = user_service.obtener_puestos(base_empresa)
                sucursales = user_service.obtener_sucursales(base_empresa)
                return render(request, "core/usuarios_crear.html", {
                    'puestos': puestos,
                    'sucursales': sucursales,
                    'base_empresa': base_empresa,
                })
            
            if validacion['advertencias']:
                for advertencia in validacion['advertencias']:
                    messages.warning(request, f"⚠️ {advertencia}")
        
        # Crear usuario
        nuevo_id = user_service.crear_usuario(base_empresa, id_empresa, datos_usuario)
        
        if nuevo_id:
            messages.success(request, f"✅ Usuario '{cod_usuario}' creado correctamente.")
            return redirect("core:usuarios")
        else:
            messages.error(request, "Error al crear el usuario. Por favor intente nuevamente.")
            puestos = user_service.obtener_puestos(base_empresa)
            sucursales = user_service.obtener_sucursales(base_empresa)
            return render(request, "core/usuarios_crear.html", {
                'puestos': puestos,
                'sucursales': sucursales,
                'base_empresa': base_empresa,
            })
    
    # GET - mostrar formulario
    puestos = user_service.obtener_puestos(base_empresa)
    sucursales = user_service.obtener_sucursales(base_empresa)
    
    context = {
        'puestos': puestos,
        'sucursales': sucursales,
        'base_empresa': base_empresa,
    }
    return render(request, "core/usuarios_crear.html", context)


@tiene_permiso("administrar.usuarios")
@csrf_protect
def editar_usuario_view(request, id_usuario):
    """
    Vista para editar un usuario existente en administraNET
    Similar a ABMUsuarios.frm - Modificar
    """
    # Obtener datos de la sesión del usuario actual
    session_user = request.session.get("user", {})
    base_empresa = session_user.get("base_empresa")
    id_empresa = session_user.get("id_empresa")
    
    if not base_empresa or not id_empresa:
        messages.error(request, "No se pudo determinar la empresa activa.")
        return redirect("core:usuarios")
    
    # Inicializar servicio
    user_service = AdministraNETUserService()
    
    # Obtener usuario existente
    usuario = user_service.obtener_usuario(base_empresa, id_usuario)
    if not usuario:
        messages.error(request, "Usuario no encontrado.")
        return redirect("core:usuarios")
    
    # No permitir editar el usuario Supervisor (id_usuario = 1) excepto contraseña
    es_supervisor = id_usuario == 1
    
    if request.method == "POST":
        # Preparar datos a actualizar
        datos_usuario = {}
        
        # Campos editables (excepto supervisor)
        if not es_supervisor:
            datos_usuario['cod_usuario'] = request.POST.get("cod_usuario", "").strip().lower()
            datos_usuario['nombre_usuario'] = request.POST.get("nombre_usuario", "").strip()
            datos_usuario['apellido_usuario'] = request.POST.get("apellido_usuario", "").strip()
            datos_usuario['id_puesto'] = int(request.POST.get("id_puesto")) if request.POST.get("id_puesto") else None
            datos_usuario['id_sucursal'] = int(request.POST.get("id_sucursal")) if request.POST.get("id_sucursal") else None
        
        # Contraseña (siempre editable)
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirmar_password", "")
        if password and confirm_password:
            if password != confirm_password:
                messages.error(request, "Las contraseñas no coinciden.")
                puestos = user_service.obtener_puestos(base_empresa)
                sucursales = user_service.obtener_sucursales(base_empresa)
                return render(request, "core/usuarios_editar.html", {
                    'usuario': usuario,
                    'puestos': puestos,
                    'sucursales': sucursales,
                    'base_empresa': base_empresa,
                    'es_supervisor': es_supervisor,
                })
            datos_usuario['password'] = password
        
        # Validar integridad del puesto si se está cambiando
        if 'id_puesto' in datos_usuario and datos_usuario['id_puesto']:
            nuevo_id_puesto = datos_usuario['id_puesto']
            puesto_actual = usuario.get('id_puesto')
            
            # Solo validar si el puesto cambió
            if nuevo_id_puesto != puesto_actual:
                validacion_service = AdministraNETValidacionPuestosService()
                validacion = validacion_service.validar_integridad_puesto(base_empresa, nuevo_id_puesto)
                
                if not validacion['valido']:
                    messages.error(request, f"⚠️ El puesto seleccionado tiene problemas de integridad: {', '.join(validacion['errores'])}")
                    puestos = user_service.obtener_puestos(base_empresa)
                    sucursales = user_service.obtener_sucursales(base_empresa)
                    return render(request, "core/usuarios_editar.html", {
                        'usuario': usuario,
                        'puestos': puestos,
                        'sucursales': sucursales,
                        'base_empresa': base_empresa,
                        'es_supervisor': es_supervisor,
                    })
                
                if validacion['advertencias']:
                    for advertencia in validacion['advertencias']:
                        messages.warning(request, f"⚠️ {advertencia}")
        
        # Actualizar usuario
        if user_service.actualizar_usuario(base_empresa, id_usuario, datos_usuario):
            messages.success(request, f"✅ Usuario actualizado correctamente.")
            return redirect("core:usuarios")
        else:
            messages.error(request, "Error al actualizar el usuario.")
    
    # GET - mostrar formulario
    puestos = user_service.obtener_puestos(base_empresa)
    sucursales = user_service.obtener_sucursales(base_empresa)
    
    context = {
        'usuario': usuario,
        'puestos': puestos,
        'sucursales': sucursales,
        'base_empresa': base_empresa,
        'es_supervisor': es_supervisor,
    }
    return render(request, "core/usuarios_editar.html", context)


@tiene_permiso("administrar.usuarios")
@csrf_protect
def eliminar_usuario_view(request, id_usuario):
    """
    Vista para eliminar (dar de baja) un usuario
    Similar a ABMUsuarios.frm - no elimina físicamente, marca como dado de baja
    """
    # Obtener datos de la sesión del usuario actual
    session_user = request.session.get("user", {})
    base_empresa = session_user.get("base_empresa")
    
    if not base_empresa:
        messages.error(request, "No se pudo determinar la empresa activa.")
        return redirect("core:usuarios")
    
    # No permitir eliminar el usuario Supervisor
    if id_usuario == 1:
        messages.error(request, "No se puede eliminar el usuario Supervisor.")
        return redirect("core:usuarios")
    
    # Inicializar servicio
    user_service = AdministraNETUserService()
    
    if request.method == "POST":
        if user_service.eliminar_usuario(base_empresa, id_usuario):
            messages.success(request, "✅ Usuario dado de baja correctamente.")
        else:
            messages.error(request, "Error al eliminar el usuario.")
    
    return redirect("core:usuarios")


@tiene_permiso("administrar.usuarios")
def validar_integridad_usuarios_view(request):
    """
    Vista para validar la integridad de todos los usuarios y sus puestos
    """
    # Obtener datos de la sesión del usuario actual
    session_user = request.session.get("user", {})
    base_empresa = session_user.get("base_empresa")
    id_empresa = session_user.get("id_empresa")
    
    if not base_empresa:
        messages.error(request, "No se pudo determinar la empresa activa.")
        return redirect("core:dashboard")
    
    # Inicializar servicio de validación
    validacion_service = AdministraNETValidacionPuestosService()
    
    # Validar todos los usuarios
    resultado = validacion_service.validar_todos_los_usuarios(base_empresa, id_empresa)
    
    context = {
        'resultado': resultado,
        'base_empresa': base_empresa,
    }
    return render(request, "core/usuarios_validacion.html", context)
