# core/views/views_permisos.py

import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from django.views.decorators.csrf import csrf_protect
from core.models import Permiso
from core.decorators import tiene_permiso
from core.constantes_permisos import PERMISOS_POR_MODULO
from django.core.exceptions import PermissionDenied
from django.core.management import call_command
from django.http import JsonResponse
from io import StringIO
import logging
import re

logger = logging.getLogger(__name__)


@tiene_permiso("usuarios.ver")
def listar_permisos_view(request):
    """
    Muestra una lista plana y filtrable de todos los permisos del sistema.
    """
    consulta = request.GET.get("q", "").strip()
    
    permisos_qs = Permiso.objects.all().order_by("nombre")

    if consulta:
        permisos_qs = permisos_qs.filter(
            Q(nombre__icontains=consulta) | Q(codigo__icontains=consulta)
        )

    context = {
        "permisos": permisos_qs,
        "q": consulta,
    }
    return render(request, "core/permisos_list.html", context)


@csrf_protect
@tiene_permiso("usuarios.permisos.crear")
def crear_editar_permiso_view(request, permiso_id=None):
    if permiso_id:
        permiso = get_object_or_404(Permiso, id=permiso_id)
        if not request.user.tiene_permiso("usuarios.permisos.editar"):
            raise PermissionDenied
        editar = True
    else:
        permiso = None
        editar = False

    if request.method == "POST":
        codigo = request.POST.get("codigo", "").strip()
        nombre = request.POST.get("nombre", "").strip()
        
        if not codigo or not nombre:
            messages.error(request, "El código y el nombre son obligatorios.")
        else:
            # Para edición, excluimos el propio objeto de la validación de unicidad
            query = Permiso.objects.filter(codigo=codigo)
            if editar:
                query = query.exclude(pk=permiso_id)

            if query.exists():
                messages.error(request, f"El permiso con el código '{codigo}' ya existe.")
            else:
                if editar:
                    permiso.nombre = nombre # Solo se puede editar el nombre
                    permiso.save()
                    messages.success(request, "Permiso actualizado exitosamente.")
                else:
                    Permiso.objects.create(codigo=codigo, nombre=nombre)
                    messages.success(request, "Permiso creado exitosamente.")
                return redirect("core:listar_permisos")

    return render(request, "core/permisos_form.html", {"permiso": permiso, "editar": editar})


@csrf_protect
@tiene_permiso("usuarios.permisos.eliminar")
def eliminar_permiso_view(request, permiso_id):
    permiso = get_object_or_404(Permiso, id=permiso_id)
    permiso.delete()
    messages.success(request, f"Permiso '{permiso.codigo}' eliminado correctamente.")
    return redirect("core:listar_permisos")


@csrf_protect
@tiene_permiso("administrar.sync")
def sincronizar_sistema_view(request):
    """
    Ejecuta los comandos de sincronización y devuelve un JSON estructurado
    con el resultado de cada paso.
    """
    if request.method != "POST":
        return JsonResponse({'status': 'error', 'message': 'Método no permitido'}, status=405)

    results = []
    
    try:
        # --- Paso 1: Sincronizar Permisos ---
        perm_out = StringIO()
        call_command('sincronizar_permisos', stdout=perm_out)
        perm_log = perm_out.getvalue()
        
        perm_added = len(re.findall(r'\[\+\] Agregando permiso', perm_log))
        perm_updated = len(re.findall(r'\[\*\] Actualizando nombre', perm_log))
        perm_summary = f"{perm_added} permisos creados, {perm_updated} actualizados."
        
        results.append({
            'step': 'Sincronización de Permisos',
            'status': 'success',
            'summary': perm_summary,
            'log': perm_log,
        })
        
        # --- Paso 2: Asignar Roles ---
        role_out = StringIO()
        call_command('asignar_roles_predeterminados', stdout=role_out)
        role_log = role_out.getvalue()

        roles_created = len(re.findall(r'\[\+\] Rol', role_log))
        roles_updated = len(re.findall(r'\[\*\] Rol', role_log))
        perms_assigned = sum(map(int, re.findall(r'Se añadieron (\d+)', role_log)))
        role_summary = f"{roles_created} roles creados, {roles_updated} actualizados. {perms_assigned} permisos asignados."

        results.append({
            'step': 'Asignación de Roles',
            'status': 'success',
            'summary': role_summary,
            'log': role_log,
        })

        logger.info(f"Sincronización manual exitosa por {request.user.email}")
        return JsonResponse({'status': 'success', 'results': results})

    except Exception as e:
        logger.error(f"Error en sincronización por {request.user.email}: {e}")
        # Añade el error al último paso que falló, si lo hay
        if results:
            results[-1]['status'] = 'error'
            results[-1]['summary'] = f"Falló: {str(e)}"
            results[-1]['log'] += f"\\nERROR: {str(e)}"
        
        return JsonResponse({
            'status': 'error',
            'message': str(e),
            'results': results
        }, status=500)
