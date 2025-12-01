# core/views/views_permisos.py

import json
from django.shortcuts import render, redirect
from django.contrib import messages
from django.views.decorators.csrf import csrf_protect
from django.core.paginator import Paginator
from django.http import JsonResponse
from core.decorators import tiene_permiso
from core.services.administranet_permiso_sistema import AdministraNETPermisoSistemaService
from django.core.exceptions import PermissionDenied
import logging

logger = logging.getLogger(__name__)


@tiene_permiso("administrar.usuarios")
def listar_permisos_view(request):
    """
    Muestra una lista filtrable de todos los permisos del sistema de administraNET.
    Ordenados por grupo y nombre.
    """
    # Obtener datos de la sesión del usuario actual
    session_user = request.session.get("user", {})
    base_empresa = session_user.get("base_empresa")
    id_puesto = session_user.get("id_puesto")
    
    if not base_empresa:
        messages.error(request, "No se pudo determinar la empresa activa.")
        return redirect("core:dashboard")
    
    # Inicializar servicio
    permisos_service = AdministraNETPermisoSistemaService()
    
    # Búsqueda y filtros
    consulta = request.GET.get("q", "").strip()
    grupo = request.GET.get("grupo", "").strip() or None
    
    # Obtener permisos desde MySQL de administraNET, filtrando por el puesto del usuario actual
    permisos = permisos_service.listar_permisos(
        base_empresa=base_empresa,
        busqueda=consulta if consulta else None,
        grupo=grupo,
        id_puesto=id_puesto
    )
    
    # Obtener grupos disponibles
    grupos = permisos_service.obtener_grupos(base_empresa)
    
    # Agrupar permisos por módulo
    permisos_por_modulo = {}
    for permiso in permisos:
        modulo = permiso.get('grupo_permiso', 'Sin módulo')
        if modulo not in permisos_por_modulo:
            permisos_por_modulo[modulo] = []
        permisos_por_modulo[modulo].append(permiso)
    
    # Convertir a lista de tuplas (modulo, permisos) para el template
    permisos_agrupados = sorted(permisos_por_modulo.items(), key=lambda x: x[0])
    
    # Paginación manual (paginamos los módulos, no los permisos individuales)
    # Para simplificar, mostramos todos los módulos pero podríamos paginar si hay muchos
    paginator = Paginator(permisos_agrupados, 10)  # 10 módulos por página
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "permisos_agrupados": page_obj,
        "q": consulta,
        "grupo_seleccionado": grupo,
        "grupos": grupos,
        "base_empresa": base_empresa,
        "total_permisos": len(permisos),
    }
    return render(request, "core/permisos_list.html", context)


@csrf_protect
@tiene_permiso("administrar.usuarios")
def crear_editar_permiso_view(request, permiso_id=None):
    """
    Crea o edita un permiso del sistema de administraNET
    """
    # Obtener datos de la sesión del usuario actual
    session_user = request.session.get("user", {})
    base_empresa = session_user.get("base_empresa")
    
    if not base_empresa:
        messages.error(request, "No se pudo determinar la empresa activa.")
        return redirect("core:listar_permisos")
    
    # Inicializar servicio
    permisos_service = AdministraNETPermisoSistemaService()
    
    editar = permiso_id is not None
    
    if editar:
        permiso = permisos_service.obtener_permiso(base_empresa, permiso_id)
        if not permiso:
            messages.error(request, "Permiso no encontrado.")
            return redirect("core:listar_permisos")
    else:
        permiso = None
    
    if request.method == "POST":
        key_permiso = request.POST.get("key_permiso", "").strip()
        nombre_permiso = request.POST.get("nombre_permiso", "").strip()
        detalle_permiso = request.POST.get("detalle_permiso", "").strip()
        grupo_permiso = request.POST.get("grupo_permiso", "Generales").strip()
        tipo_permiso = request.POST.get("tipo_permiso", "Si-No").strip()
        default_permiso = request.POST.get("default_permiso", "No").strip()
        detalle_valor_permiso = request.POST.get("detalle_valor_permiso", "Si-No").strip()
        
        if not key_permiso or not nombre_permiso:
            messages.error(request, "El código y nombre del permiso son requeridos.")
        else:
            datos_permiso = {
                'key_permiso': key_permiso,
                'nombre_permiso': nombre_permiso,
                'detalle_permiso': detalle_permiso,
                'grupo_permiso': grupo_permiso,
                'tipo_permiso': tipo_permiso,
                'default_permiso': default_permiso,
                'detalle_valor_permiso': detalle_valor_permiso,
            }
            
            if editar:
                if permisos_service.actualizar_permiso(base_empresa, permiso_id, datos_permiso):
                    messages.success(request, f"✅ Permiso '{nombre_permiso}' actualizado correctamente.")
                    return redirect("core:listar_permisos")
                else:
                    messages.error(request, "Error al actualizar el permiso. Verifique que el código no esté duplicado.")
            else:
                nuevo_id = permisos_service.crear_permiso(base_empresa, datos_permiso)
                if nuevo_id:
                    messages.success(request, f"✅ Permiso '{nombre_permiso}' creado correctamente.")
                    return redirect("core:listar_permisos")
                else:
                    messages.error(request, "Error al crear el permiso. Verifique que el código no esté duplicado.")
    
    # Obtener grupos disponibles
    grupos = permisos_service.obtener_grupos(base_empresa)
    
    return render(request, "core/permisos_form.html", {
        "permiso": permiso, 
        "editar": editar,
        "grupos": grupos,
        "base_empresa": base_empresa,
    })


@csrf_protect
@tiene_permiso("administrar.usuarios")
def eliminar_permiso_view(request, permiso_id):
    """
    Elimina un permiso del sistema de administraNET
    """
    # Obtener datos de la sesión del usuario actual
    session_user = request.session.get("user", {})
    base_empresa = session_user.get("base_empresa")
    
    if not base_empresa:
        messages.error(request, "No se pudo determinar la empresa activa.")
        return redirect("core:listar_permisos")
    
    # Inicializar servicio
    permisos_service = AdministraNETPermisoSistemaService()
    
    # Obtener permiso para mostrar su nombre en el mensaje
    permiso = permisos_service.obtener_permiso(base_empresa, permiso_id)
    
    if not permiso:
        messages.error(request, "Permiso no encontrado.")
        return redirect("core:listar_permisos")
    
    if permisos_service.eliminar_permiso(base_empresa, permiso_id):
        messages.success(request, f"✅ Permiso '{permiso.get('nombre_permiso', '')}' eliminado correctamente.")
    else:
        messages.error(request, "Error al eliminar el permiso.")
    
    return redirect("core:listar_permisos")


@csrf_protect
@tiene_permiso("administrar.usuarios")
def toggle_valor_permiso_view(request, permiso_id):
    """
    Vista API para cambiar el valor de un permiso (Si/No) mediante AJAX
    Solo actualiza el valor para el puesto del usuario actual
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)
    
    # Obtener datos de la sesión del usuario actual
    session_user = request.session.get("user", {})
    base_empresa = session_user.get("base_empresa")
    id_puesto = session_user.get("id_puesto")
    
    if not base_empresa:
        return JsonResponse({'success': False, 'error': 'No se pudo determinar la empresa activa'}, status=400)
    
    if not id_puesto:
        return JsonResponse({'success': False, 'error': 'No se pudo determinar el puesto del usuario'}, status=400)
    
    try:
        data = json.loads(request.body)
        nuevo_valor = data.get('valor', '').strip()
        
        if nuevo_valor not in ['Si', 'No']:
            return JsonResponse({'success': False, 'error': 'Valor inválido. Debe ser "Si" o "No"'}, status=400)
        
        # Inicializar servicio
        permisos_service = AdministraNETPermisoSistemaService()
        
        # Actualizar el valor solo para el puesto del usuario actual
        if permisos_service.actualizar_valor_permiso(base_empresa, permiso_id, nuevo_valor, id_puesto):
            return JsonResponse({
                'success': True,
                'valor': nuevo_valor,
                'mensaje': f'Permiso actualizado a {nuevo_valor} para tu puesto'
            })
        else:
            return JsonResponse({'success': False, 'error': 'Error al actualizar el permiso'}, status=500)
            
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'JSON inválido'}, status=400)
    except Exception as e:
        logger.error(f"Error inesperado al cambiar valor del permiso: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
