"""
Vistas para gestión del Catálogo Funcional
"""
import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.http import JsonResponse
from reports_ai.models import FunctionalCatalog
from reports_ai.forms import FunctionalCatalogForm

logger = logging.getLogger(__name__)


@login_required
@permission_required('reports_ai.manage_business_rules', raise_exception=True)
def catalog_list(request):
    """
    Lista de entradas del catálogo funcional
    
    GET /reports-ai/catalog/
    """
    # Filtros
    module_filter = request.GET.get('module', '')
    search_query = request.GET.get('q', '')
    
    # Query base
    entries = FunctionalCatalog.objects.filter(is_active=True)
    
    # Aplicar filtros
    if module_filter:
        entries = entries.filter(module__icontains=module_filter)
    
    if search_query:
        entries = entries.filter(
            procedure__icontains=search_query
        )
    
    entries = entries.order_by('-priority', 'module', 'procedure')
    
    # Agrupar por módulo
    modules = {}
    for entry in entries:
        if entry.module not in modules:
            modules[entry.module] = []
        modules[entry.module].append(entry)
    
    context = {
        'page_title': 'Catálogo Funcional',
        'active_tab': 'catalog',
        'entries': entries,
        'modules': modules,
        'module_filter': module_filter,
        'search_query': search_query,
        'total_entries': entries.count()
    }
    
    return render(request, 'reports_ai/catalog/list.html', context)


@login_required
@permission_required('reports_ai.manage_business_rules', raise_exception=True)
def catalog_detail(request, catalog_id):
    """
    Detalle de una entrada del catálogo
    
    GET /reports-ai/catalog/<id>/
    """
    entry = get_object_or_404(FunctionalCatalog, id=catalog_id)
    
    context = {
        'page_title': f'{entry.module} - {entry.procedure}',
        'active_tab': 'catalog',
        'entry': entry
    }
    
    return render(request, 'reports_ai/catalog/detail.html', context)


@login_required
@permission_required('reports_ai.manage_business_rules', raise_exception=True)
def catalog_create(request):
    """
    Crear nueva entrada en el catálogo
    
    GET/POST /reports-ai/catalog/create/
    """
    if request.method == 'POST':
        form = FunctionalCatalogForm(request.POST)
        
        if form.is_valid():
            entry = form.save(commit=False)
            entry.created_by = request.user
            entry.save()
            
            messages.success(
                request,
                f'✅ Entrada creada: {entry.module} - {entry.procedure}'
            )
            
            return redirect('reports_ai:catalog_detail', catalog_id=entry.id)
        else:
            messages.error(request, '❌ Error al crear entrada. Revisa los campos.')
    else:
        form = FunctionalCatalogForm()
    
    context = {
        'page_title': 'Nueva Entrada - Catálogo Funcional',
        'active_tab': 'catalog',
        'form': form,
        'is_edit': False
    }
    
    return render(request, 'reports_ai/catalog/form.html', context)


@login_required
@permission_required('reports_ai.manage_business_rules', raise_exception=True)
def catalog_edit(request, catalog_id):
    """
    Editar entrada del catálogo
    
    GET/POST /reports-ai/catalog/<id>/edit/
    """
    entry = get_object_or_404(FunctionalCatalog, id=catalog_id)
    
    if request.method == 'POST':
        form = FunctionalCatalogForm(request.POST, instance=entry)
        
        if form.is_valid():
            form.save()
            
            messages.success(
                request,
                f'✅ Entrada actualizada: {entry.module} - {entry.procedure}'
            )
            
            return redirect('reports_ai:catalog_detail', catalog_id=entry.id)
        else:
            messages.error(request, '❌ Error al actualizar entrada. Revisa los campos.')
    else:
        form = FunctionalCatalogForm(instance=entry)
    
    context = {
        'page_title': f'Editar: {entry.module} - {entry.procedure}',
        'active_tab': 'catalog',
        'form': form,
        'entry': entry,
        'is_edit': True
    }
    
    return render(request, 'reports_ai/catalog/form.html', context)


@login_required
@permission_required('reports_ai.manage_business_rules', raise_exception=True)
def catalog_delete(request, catalog_id):
    """
    Eliminar entrada del catálogo
    
    POST /reports-ai/catalog/<id>/delete/
    """
    entry = get_object_or_404(FunctionalCatalog, id=catalog_id)
    
    if request.method == 'POST':
        module = entry.module
        procedure = entry.procedure
        entry.delete()
        
        messages.success(
            request,
            f'✅ Entrada eliminada: {module} - {procedure}'
        )
        
        return redirect('reports_ai:catalog_list')
    
    return JsonResponse({
        'success': False,
        'error': 'Método no permitido'
    }, status=405)


@login_required
@permission_required('reports_ai.manage_business_rules', raise_exception=True)
def catalog_toggle_active(request, catalog_id):
    """
    Activar/desactivar entrada del catálogo
    
    POST /reports-ai/catalog/<id>/toggle/
    """
    entry = get_object_or_404(FunctionalCatalog, id=catalog_id)
    
    if request.method == 'POST':
        entry.is_active = not entry.is_active
        entry.save()
        
        status_text = 'activada' if entry.is_active else 'desactivada'
        
        messages.success(
            request,
            f'✅ Entrada {status_text}: {entry.module} - {entry.procedure}'
        )
        
        return redirect('reports_ai:catalog_detail', catalog_id=entry.id)
    
    return JsonResponse({
        'success': False,
        'error': 'Método no permitido'
    }, status=405)

