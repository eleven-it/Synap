from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.paginator import Paginator
from core.decorators import tiene_permiso
from core.services.administranet_puestos import AdministraNETPuestosService
from core.services.administranet_permisos_menu import AdministraNETPermisosMenuService
import logging

logger = logging.getLogger(__name__)

@tiene_permiso("administrar.usuarios")
def listar_roles_view(request):
    """
    Lista puestos (roles) de administraNET Gestión
    """
    # Obtener datos de la sesión del usuario actual
    session_user = request.session.get("user", {})
    base_empresa = session_user.get("base_empresa")
    
    if not base_empresa:
        messages.error(request, "No se pudo determinar la empresa activa.")
        return redirect("core:dashboard")
    
    # Inicializar servicio
    puestos_service = AdministraNETPuestosService()
    
    # Búsqueda
    q = request.GET.get("q", "").strip()
    
    # Obtener puestos desde MySQL de administraNET
    puestos = puestos_service.listar_puestos(
        base_empresa=base_empresa,
        busqueda=q if q else None
    )
    
    # Paginación manual
    paginator = Paginator(puestos, 15)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    
    context = {
        "puestos": page_obj,
        "q": q,
        "base_empresa": base_empresa,
    }
    return render(request, "core/roles_listar.html", context)

@tiene_permiso("administrar.usuarios")
def crear_editar_rol_view(request, puesto_id=None):
    """
    Crea o edita un puesto (rol) y gestiona sus permisos del menú
    """
    # Obtener datos de la sesión del usuario actual
    session_user = request.session.get("user", {})
    base_empresa = session_user.get("base_empresa")
    
    if not base_empresa:
        messages.error(request, "No se pudo determinar la empresa activa.")
        return redirect("core:listar_roles")
    
    # Inicializar servicios
    puestos_service = AdministraNETPuestosService()
    permisos_menu_service = AdministraNETPermisosMenuService()
    
    editar = puesto_id is not None
    
    if editar:
        puesto = puestos_service.obtener_puesto(base_empresa, puesto_id)
        if not puesto:
            messages.error(request, "Puesto no encontrado.")
            return redirect("core:listar_roles")
        
        # Obtener permisos actuales del puesto
        permisos_actuales = permisos_menu_service.obtener_permisos_puesto(base_empresa, puesto_id)
    else:
        puesto = None
        permisos_actuales = set()
    
    # Obtener lista de puestos para el selector de puesto base (solo al crear)
    puestos_disponibles = puestos_service.listar_puestos(base_empresa) if not editar else []
    
    if request.method == "POST":
        nombre = request.POST.get("nombre", "").strip()
        permisos_seleccionados = set(request.POST.getlist("permisos"))
        heredar_desde_puesto = request.POST.get("heredar_desde_puesto", "").strip() == "on"
        puesto_base_id = request.POST.get("puesto_base_id", "").strip()
        
        if not nombre:
            messages.error(request, "El nombre del puesto es requerido.")
        else:
            if editar:
                if puestos_service.actualizar_puesto(base_empresa, puesto_id, nombre):
                    # Guardar permisos del menú
                    if permisos_menu_service.guardar_permisos_puesto(base_empresa, puesto_id, permisos_seleccionados):
                        messages.success(request, f"✅ Puesto '{nombre}' actualizado correctamente.")
                        return redirect("core:listar_roles")
                    else:
                        messages.error(request, "Error al guardar los permisos del menú.")
                else:
                    messages.error(request, "Error al actualizar el puesto. Verifique que el nombre no esté duplicado.")
            else:
                nuevo_id = puestos_service.crear_puesto(base_empresa, nombre)
                if nuevo_id:
                    # Si se marcó heredar desde puesto base, heredar permisos
                    if heredar_desde_puesto and puesto_base_id:
                        try:
                            puesto_base_id_int = int(puesto_base_id)
                            # Heredar permisos del menú
                            permisos_menu_service.heredar_permisos_desde_puesto(base_empresa, nuevo_id, puesto_base_id_int)
                            # Heredar permisos del sistema
                            from core.services.administranet_permisos_sistema import AdministraNETPermisosSistemaService
                            permisos_sistema_service = AdministraNETPermisosSistemaService()
                            permisos_sistema_service.heredar_permisos_desde_puesto(base_empresa, nuevo_id, puesto_base_id_int)
                            messages.success(request, f"✅ Puesto '{nombre}' creado correctamente heredando permisos desde el puesto base.")
                        except (ValueError, Exception) as e:
                            logger.error(f"Error al heredar permisos: {e}", exc_info=True)
                            messages.warning(request, f"Puesto creado pero hubo un error al heredar permisos: {str(e)}")
                    else:
                        # Guardar permisos del menú seleccionados manualmente
                        if permisos_seleccionados:
                            if permisos_menu_service.guardar_permisos_puesto(base_empresa, nuevo_id, permisos_seleccionados):
                                messages.success(request, f"✅ Puesto '{nombre}' creado correctamente.")
                            else:
                                messages.error(request, "Error al guardar los permisos del menú.")
                        else:
                            messages.success(request, f"✅ Puesto '{nombre}' creado correctamente (sin permisos asignados).")
                    
                    return redirect("core:listar_roles")
                else:
                    messages.error(request, "Error al crear el puesto. Verifique que el nombre no esté duplicado.")
    
    # Obtener estructura del menú
    estructura_menu = permisos_menu_service.obtener_estructura_menu()
    
    return render(
        request,
        "core/roles_form.html",
        {
            "puesto": puesto,
            "editar": editar,
            "estructura_menu": estructura_menu,
            "permisos_actuales": permisos_actuales,
            "puestos_disponibles": puestos_disponibles,
            "base_empresa": base_empresa,
        },
    )

@tiene_permiso("administrar.usuarios")
def eliminar_rol_view(request, puesto_id):
    """
    Elimina un puesto (rol) de administraNET Gestión
    """
    # Obtener datos de la sesión del usuario actual
    session_user = request.session.get("user", {})
    base_empresa = session_user.get("base_empresa")
    
    if not base_empresa:
        messages.error(request, "No se pudo determinar la empresa activa.")
        return redirect("core:listar_roles")
    
    # Inicializar servicio
    puestos_service = AdministraNETPuestosService()
    
    # Obtener puesto para mostrar su nombre en el mensaje
    puesto = puestos_service.obtener_puesto(base_empresa, puesto_id)
    
    if not puesto:
        messages.error(request, "Puesto no encontrado.")
        return redirect("core:listar_roles")
    
    if puestos_service.eliminar_puesto(base_empresa, puesto_id):
        messages.success(request, f"✅ Puesto '{puesto.get('nombre', '')}' eliminado correctamente.")
    else:
        messages.error(request, "No se puede eliminar el puesto. Tiene usuarios asociados.")
    
    return redirect("core:listar_roles")
