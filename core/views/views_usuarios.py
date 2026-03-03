# core/views_usuarios.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.csrf import csrf_protect
from core.models import Permiso, Rol
from core.decorators import tiene_permiso
from core.constantes_permisos import PERMISOS_POR_MODULO
from core.utils import permisos_contextuales
from core.services.administranet_users import AdministraNETUserService
from core.services.administranet_sucursales import AdministraNETSucursalesService
from core.services.administranet_empresas import AdministraNETEmpresaService
from core.services.administranet_validacion_puestos import AdministraNETValidacionPuestosService
import logging


def _int_or_none(val):
    if val is None or (isinstance(val, str) and val.strip() == ''):
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def _float_or_none(val):
    if val is None or (isinstance(val, str) and val.strip() == ''):
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _datos_usuario_desde_post(request, es_supervisor=False):
    """Construye el diccionario datos_usuario desde POST (paridad CargaUsuario.frm)."""
    data = {}
    if not es_supervisor:
        data['cod_usuario'] = request.POST.get('cod_usuario', '').strip().lower()
        data['nombre_usuario'] = request.POST.get('nombre_usuario', '').strip()
        data['apellido_usuario'] = request.POST.get('apellido_usuario', '').strip()
        data['id_puesto'] = _int_or_none(request.POST.get('id_puesto'))
        data['id_sucursal'] = _int_or_none(request.POST.get('id_sucursal'))
        data['id_punto_venta'] = _int_or_none(request.POST.get('id_punto_venta'))
        data['id_deposito'] = _int_or_none(request.POST.get('id_deposito'))
        data['id_caja'] = _int_or_none(request.POST.get('id_caja'))
        data['pv'] = _int_or_none(request.POST.get('pv'))
        data['pvc'] = _int_or_none(request.POST.get('pvc'))
        data['tipo_busq'] = request.POST.get('tipo_busq', '').strip()
        data['id_caja_cheque'] = _int_or_none(request.POST.get('id_caja_cheque'))
        data['id_caja_tarjeta'] = _int_or_none(request.POST.get('id_caja_tarjeta'))
        data['id_punto_ventac'] = _int_or_none(request.POST.get('id_punto_ventac'))
        data['id_caja_cheque_deposito'] = _int_or_none(request.POST.get('id_caja_cheque_deposito'))
        data['id_caja_deposito'] = _int_or_none(request.POST.get('id_caja_deposito'))
        data['id_caja_tarjeta_deposito'] = _int_or_none(request.POST.get('id_caja_tarjeta_deposito'))
        data['baja_usuario'] = 'Si' if request.POST.get('baja_usuario') == 'Si' else 'No'
        data['tipo_busqueda_defecto'] = _int_or_none(request.POST.get('tipo_busqueda_defecto')) or 0
        data['permiso_supervisor_venta'] = 'Si' if request.POST.get('permiso_supervisor_venta') == 'Si' else 'No'
        data['vendedor_web'] = 'Si' if request.POST.get('vendedor_web') == 'Si' else 'No'
        data['CodViajante'] = _int_or_none(request.POST.get('CodViajante'))
        data['resol_principal'] = request.POST.get('resol_principal', '').strip()
        data['entrega_defecto'] = request.POST.get('entrega_defecto', '').strip()
        data['utiliza_reporte_local'] = 'Si' if request.POST.get('utiliza_reporte_local') == 'Si' else 'No'
        data['utiliza_certificado_local'] = 'Si' if request.POST.get('utiliza_certificado_local') == 'Si' else 'No'
        data['ruta_reporte_local'] = request.POST.get('ruta_reporte_local', '').strip()
        data['ruta_certificado_local'] = request.POST.get('ruta_certificado_local', '').strip()
        data['carpeta_documentos'] = request.POST.get('carpeta_documentos', '').strip()
        data['fuente_nombre'] = request.POST.get('fuente_nombre', '').strip()
        data['fuente_tamano'] = _float_or_none(request.POST.get('fuente_tamano')) or 8.25
        data['color_formulario'] = request.POST.get('color_formulario', '').strip()
        data['tipo_boton'] = request.POST.get('tipo_boton', '').strip()
        data['zoom_reportes'] = _int_or_none(request.POST.get('zoom_reportes')) or 100
        if data.get('pv') is None and data.get('id_punto_venta') is not None:
            data['pv'] = data['id_punto_venta']
    password = request.POST.get('password', '')
    if password:
        data['password'] = password
    return data


def _contexto_listas_usuarios(user_service, sucursales_service, base_empresa, id_sucursal=None):
    """Contexto con puestos, sucursales, depósitos, cajas por tipo (alineado CargaUsuario.frm), puntos de venta y viajantes."""
    cajas_form = user_service.obtener_cajas_usuario_formulario(base_empresa, id_sucursal)
    return {
        'puestos': user_service.obtener_puestos(base_empresa),
        'sucursales': user_service.obtener_sucursales(base_empresa),
        'depositos': user_service.obtener_depositos(base_empresa),
        **cajas_form,
        'puntos_venta': user_service.obtener_puntos_venta(base_empresa, id_sucursal),
        'viajantes': sucursales_service.obtener_viajantes(base_empresa),
    }

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
    
    # Cargar usuarios una sola vez (solo filtro activos); la búsqueda por texto se hace en el cliente
    solo_activos = request.GET.get("activos", "true").lower() == "true"
    
    usuarios = user_service.listar_usuarios(
        base_empresa=base_empresa,
        id_empresa=id_empresa,
        busqueda=None,
        solo_activos=solo_activos
    )
    
    # Normalizar sucursal para agrupación
    for u in usuarios:
        u["nombre_sucursal_display"] = (u.get("nombre_sucursal") or "").strip() or "Sin sucursal"
    
    usuarios_sorted = sorted(
        usuarios,
        key=lambda x: (
            (x.get("nombre_sucursal_display") or "").lower(),
            (x.get("nombre_usuario") or "").lower(),
        ),
    )
    
    total_sucursales = len(set(u.get("nombre_sucursal_display") for u in usuarios_sorted))
    
    # Obtener puestos y sucursales para formularios
    puestos = user_service.obtener_puestos(base_empresa)
    sucursales = user_service.obtener_sucursales(base_empresa)

    context.update({
        "usuarios_list": usuarios_sorted,
        "total_sucursales": total_sucursales,
        "puestos": puestos,
        "sucursales": sucursales,
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
    
    user_service = AdministraNETUserService()
    sucursales_service = AdministraNETSucursalesService()

    def _ctx_crear():
        empresa_service = AdministraNETEmpresaService()
        empresa = empresa_service.obtener_empresa(base_empresa)
        nombre_empresa = (empresa.get('Nombre') or '').strip() if empresa else base_empresa
        return {
            **_contexto_listas_usuarios(user_service, sucursales_service, base_empresa),
            'base_empresa': base_empresa,
            'nombre_empresa': nombre_empresa,
        }

    if request.method == "POST":
        cod_usuario = request.POST.get("cod_usuario", "").strip().lower()
        nombre_usuario = request.POST.get("nombre_usuario", "").strip()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirmar_password", "")

        if not cod_usuario or not password or not confirm_password or not nombre_usuario:
            messages.error(request, "Completa todos los campos obligatorios (código, nombre, contraseña y confirmación).")
            return render(request, "core/usuarios_crear.html", _ctx_crear())

        if password != confirm_password:
            messages.error(request, "Las contraseñas no coinciden.")
            return render(request, "core/usuarios_crear.html", _ctx_crear())

        usuarios_existentes = user_service.listar_usuarios(base_empresa, id_empresa, busqueda=cod_usuario, solo_activos=False)
        if any(u.get('cod_usuario', '').lower() == cod_usuario.lower() for u in usuarios_existentes):
            messages.error(request, f"El usuario '{cod_usuario}' ya existe.")
            return render(request, "core/usuarios_crear.html", _ctx_crear())

        datos_usuario = _datos_usuario_desde_post(request, es_supervisor=False)
        datos_usuario.setdefault('baja_usuario', 'No')
        datos_usuario.setdefault('tipo_busqueda_defecto', 0)
        datos_usuario.setdefault('permiso_supervisor_venta', 'No')
        datos_usuario.setdefault('vendedor_web', 'No')
        datos_usuario.setdefault('zoom_reportes', 100)

        id_puesto = datos_usuario.get('id_puesto')
        if id_puesto:
            validacion_service = AdministraNETValidacionPuestosService()
            validacion = validacion_service.validar_integridad_puesto(base_empresa, id_puesto)
            if not validacion['valido']:
                messages.error(request, f"⚠️ El puesto tiene problemas de integridad: {', '.join(validacion['errores'])}")
                return render(request, "core/usuarios_crear.html", _ctx_crear())
            for advertencia in validacion.get('advertencias', []):
                messages.warning(request, f"⚠️ {advertencia}")

        nuevo_id = user_service.crear_usuario(base_empresa, id_empresa, datos_usuario)
        if nuevo_id:
            messages.success(request, f"✅ Usuario '{cod_usuario}' creado correctamente.")
            return redirect("core:usuarios")
        messages.error(request, "Error al crear el usuario. Por favor intente nuevamente.")
        return render(request, "core/usuarios_crear.html", _ctx_crear())

    return render(request, "core/usuarios_crear.html", _ctx_crear())


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
    
    usuario = user_service.obtener_usuario(base_empresa, id_usuario)
    if not usuario:
        messages.error(request, "Usuario no encontrado.")
        return redirect("core:usuarios")

    es_supervisor = id_usuario == 1
    sucursales_service = AdministraNETSucursalesService()
    id_sucursal = usuario.get('id_sucursal')

    def _ctx_editar():
        return {
            'usuario': usuario,
            'base_empresa': base_empresa,
            'es_supervisor': es_supervisor,
            **_contexto_listas_usuarios(user_service, sucursales_service, base_empresa, id_sucursal),
        }

    if request.method == "POST":
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirmar_password", "")
        if password or confirm_password:
            if password != confirm_password:
                messages.error(request, "Las contraseñas no coinciden.")
                return render(request, "core/usuarios_editar.html", _ctx_editar())

        datos_usuario = _datos_usuario_desde_post(request, es_supervisor=es_supervisor)
        if not es_supervisor and 'id_sucursal' not in datos_usuario:
            datos_usuario['id_sucursal'] = id_sucursal

        if not es_supervisor and datos_usuario.get('id_puesto'):
            validacion_service = AdministraNETValidacionPuestosService()
            validacion = validacion_service.validar_integridad_puesto(base_empresa, datos_usuario['id_puesto'])
            if not validacion['valido']:
                messages.error(request, f"⚠️ El puesto tiene problemas de integridad: {', '.join(validacion['errores'])}")
                return render(request, "core/usuarios_editar.html", _ctx_editar())
            for advertencia in validacion.get('advertencias', []):
                messages.warning(request, f"⚠️ {advertencia}")

        if user_service.actualizar_usuario(base_empresa, id_usuario, datos_usuario):
            messages.success(request, "✅ Usuario actualizado correctamente.")
            return redirect("core:usuarios")
        messages.error(request, "Error al actualizar el usuario.")
        return render(request, "core/usuarios_editar.html", _ctx_editar())

    return render(request, "core/usuarios_editar.html", _ctx_editar())


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
