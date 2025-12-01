"""
Vistas para gestión de Business Rules
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.http import JsonResponse, HttpResponse
# Función dummy para mantener compatibilidad - no se usa internacionalización
def _(s): return s
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json
import csv
import os

from ..models import BusinessRule, GlossaryTerm
from ..forms import (
    BusinessRuleForm,
    BusinessRuleSearchForm,
    BusinessRuleImportForm,
    BusinessRuleBulkActionForm
)
from ..services.code_analysis_service import CodeAnalysisService


@login_required
def business_rules_list(request):
    """Lista de reglas de negocio con filtros y búsqueda"""
    
    # Construir queryset base
    rules = BusinessRule.objects.all().order_by('-created_at')
    
    # Crear formulario de búsqueda
    search_form = BusinessRuleSearchForm(request.GET)
    
    # Obtener parámetros de búsqueda
    search = request.GET.get('search', '')
    category = request.GET.get('category', '')
    module = request.GET.get('module', '')
    is_active = request.GET.get('is_active', '')
    
    # Aplicar filtros
    if search:
        rules = rules.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search) |
            Q(tags__icontains=search)
        )
    
    if category:
        rules = rules.filter(category=category)
    
    if module:
        rules = rules.filter(module__icontains=module)
    
    if is_active:
        rules = rules.filter(is_active=(is_active == 'true'))
    
    # Paginación
    paginator = Paginator(rules, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Estadísticas
    stats = {
        'total': BusinessRule.objects.count(),
        'active': BusinessRule.objects.filter(is_active=True).count(),
        'by_category': BusinessRule.objects.values('category').annotate(
            count=Count('id')
        ).order_by('-count'),
        'by_module': BusinessRule.objects.values('module').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
    }
    
    context = {
        'page_obj': page_obj,
        'search_form': search_form,
        'stats': stats,
        'title': _('Business Rules'),
        'breadcrumb': [
            {'name': _('Reports AI'), 'url': 'reports_ai:dashboard'},
            {'name': _('Business Rules'), 'url': None}
        ]
    }
    
    return render(request, 'reports_ai/business_rules/list.html', context)


@login_required
def business_rule_detail(request, rule_id):
    """Detalle de una regla de negocio"""
    
    rule = get_object_or_404(BusinessRule, id=rule_id)
    
    # Reglas relacionadas (mismo módulo o categoría)
    related_rules = BusinessRule.objects.filter(
        Q(module=rule.module) | Q(category=rule.category)
    ).exclude(id=rule.id)[:5]
    
    context = {
        'rule': rule,
        'related_rules': related_rules,
        'title': f"{_('Business Rule')}: {rule.name}",
        'breadcrumb': [
            {'name': _('Reports AI'), 'url': 'reports_ai:dashboard'},
            {'name': _('Business Rules'), 'url': 'reports_ai:business_rules_list'},
            {'name': rule.name, 'url': None}
        ]
    }
    
    return render(request, 'reports_ai/business_rules/detail.html', context)


@login_required
def business_rule_create(request):
    """Crear nueva regla de negocio"""
    
    if request.method == 'POST':
        form = BusinessRuleForm(request.POST)
        if form.is_valid():
            rule = form.save(commit=False)
            rule.created_by = request.user
            rule.save()
            
            messages.success(
                request, 
                _('Business rule created successfully.')
            )
            return redirect('reports_ai:business_rule_detail', rule_id=rule.id)
    else:
        form = BusinessRuleForm()
    
    context = {
        'form': form,
        'title': _('Create Business Rule'),
        'breadcrumb': [
            {'name': _('Reports AI'), 'url': 'reports_ai:dashboard'},
            {'name': _('Business Rules'), 'url': 'reports_ai:business_rules_list'},
            {'name': _('Create'), 'url': None}
        ]
    }
    
    return render(request, 'reports_ai/business_rules/form.html', context)


@login_required
def business_rule_edit(request, rule_id):
    """Editar regla de negocio existente"""
    
    rule = get_object_or_404(BusinessRule, id=rule_id)
    
    if request.method == 'POST':
        form = BusinessRuleForm(request.POST, instance=rule)
        if form.is_valid():
            form.save()
            
            messages.success(
                request, 
                _('Business rule updated successfully.')
            )
            return redirect('reports_ai:business_rule_detail', rule_id=rule.id)
    else:
        form = BusinessRuleForm(instance=rule)
    
    context = {
        'form': form,
        'rule': rule,
        'title': f"{_('Edit Business Rule')}: {rule.name}",
        'breadcrumb': [
            {'name': _('Reports AI'), 'url': 'reports_ai:dashboard'},
            {'name': _('Business Rules'), 'url': 'reports_ai:business_rules_list'},
            {'name': rule.name, 'url': 'reports_ai:business_rule_detail', 'args': [rule.id]},
            {'name': _('Edit'), 'url': None}
        ]
    }
    
    return render(request, 'reports_ai/business_rules/form.html', context)


@login_required
def business_rule_delete(request, rule_id):
    """Eliminar regla de negocio"""
    
    rule = get_object_or_404(BusinessRule, id=rule_id)
    
    if request.method == 'POST':
        rule_name = rule.name
        rule.delete()
        
        messages.success(
            request, 
            _('Business rule "%(name)s" deleted successfully.') % {'name': rule_name}
        )
        return redirect('reports_ai:business_rules_list')
    
    context = {
        'rule': rule,
        'title': f"{_('Delete Business Rule')}: {rule.name}",
        'breadcrumb': [
            {'name': _('Reports AI'), 'url': 'reports_ai:dashboard'},
            {'name': _('Business Rules'), 'url': 'reports_ai:business_rules_list'},
            {'name': rule.name, 'url': 'reports_ai:business_rule_detail', 'args': [rule.id]},
            {'name': _('Delete'), 'url': None}
        ]
    }
    
    return render(request, 'reports_ai/business_rules/delete.html', context)


@login_required
def business_rule_import(request):
    """Importar reglas desde código VB6/PHP"""
    
    if request.method == 'POST':
        form = BusinessRuleImportForm(request.POST)
        if form.is_valid():
            source_dir = form.cleaned_data['source_directory']
            module_filter = form.cleaned_data['module_filter']
            file_patterns = form.cleaned_data['file_patterns']
            auto_activate = form.cleaned_data['auto_activate']
            
            try:
                # Usar el servicio de análisis de código
                analyzer = CodeAnalysisService()
                results = analyzer.analyze_directory(
                    source_dir=source_dir,
                    module_filter=module_filter,
                    file_patterns=file_patterns.split(',')
                )
                
                # Crear reglas desde los resultados
                created_count = 0
                for result in results:
                    rule, created = BusinessRule.objects.get_or_create(
                        name=result['name'],
                        defaults={
                            'description': result['description'],
                            'category': result['category'],
                            'module': result['module'],
                            'conditions': result['conditions'],
                            'actions': result['actions'],
                            'source_file': result['source_file'],
                            'source_line': result['source_line'],
                            'is_active': auto_activate,
                            'created_by': request.user
                        }
                    )
                    if created:
                        created_count += 1
                
                messages.success(
                    request,
                    _('Successfully imported %(count)d business rules.') % {'count': created_count}
                )
                return redirect('reports_ai:business_rules_list')
                
            except Exception as e:
                messages.error(
                    request,
                    _('Error importing business rules: %(error)s') % {'error': str(e)}
                )
    else:
        form = BusinessRuleImportForm()
    
    context = {
        'form': form,
        'title': _('Import Business Rules'),
        'breadcrumb': [
            {'name': _('Reports AI'), 'url': 'reports_ai:dashboard'},
            {'name': _('Business Rules'), 'url': 'reports_ai:business_rules_list'},
            {'name': _('Import'), 'url': None}
        ]
    }
    
    return render(request, 'reports_ai/business_rules/import.html', context)


@login_required
@require_http_methods(["POST"])
def business_rule_bulk_action(request):
    """Acciones masivas en reglas de negocio"""
    
    form = BusinessRuleBulkActionForm(request.POST)
    if not form.is_valid():
        return JsonResponse({'success': False, 'error': 'Invalid form'})
    
    action = form.cleaned_data['action']
    selected_rules = form.cleaned_data['selected_rules']
    tag_name = form.cleaned_data.get('tag_name', '')
    
    try:
        rule_ids = json.loads(selected_rules)
        rules = BusinessRule.objects.filter(id__in=rule_ids)
        
        if action == 'activate':
            rules.update(is_active=True)
            message = _('%(count)d rules activated.') % {'count': rules.count()}
            
        elif action == 'deactivate':
            rules.update(is_active=False)
            message = _('%(count)d rules deactivated.') % {'count': rules.count()}
            
        elif action == 'delete':
            count = rules.count()
            rules.delete()
            message = _('%(count)d rules deleted.') % {'count': count}
            
        elif action == 'tag' and tag_name:
            for rule in rules:
                current_tags = rule.tags.split(',') if rule.tags else []
                if tag_name not in current_tags:
                    current_tags.append(tag_name)
                rule.tags = ','.join(current_tags)
                rule.save()
            message = _('Tag "%(tag)s" applied to %(count)d rules.') % {
                'tag': tag_name, 'count': rules.count()
            }
            
        elif action == 'export':
            # Implementar exportación
            return JsonResponse({'success': True, 'redirect': 'export'})
        
        return JsonResponse({'success': True, 'message': message})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
def business_rule_export(request):
    """Exportar reglas de negocio"""
    
    # Obtener filtros si existen
    search_form = BusinessRuleSearchForm(request.GET)
    rules = BusinessRule.objects.all()
    
    # Obtener parámetros de búsqueda
    search = request.GET.get('search', '')
    category = request.GET.get('category', '')
    module = request.GET.get('module', '')
    is_active = request.GET.get('is_active', '')
    
    # Aplicar filtros
    if search:
        rules = rules.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search) |
            Q(tags__icontains=search)
        )
    if category:
        rules = rules.filter(category=category)
    if module:
        rules = rules.filter(module__icontains=module)
    if is_active:
        rules = rules.filter(is_active=(is_active == 'true'))
    
    # Crear respuesta CSV
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="business_rules.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Name', 'Description', 'Category', 'Module', 'Priority',
        'Conditions', 'Actions', 'Source File', 'Source Line',
        'Tags', 'Active', 'Created At', 'Updated At'
    ])
    
    for rule in rules:
        writer.writerow([
            rule.name,
            rule.description,
            rule.get_category_display(),
            rule.module,
            rule.get_priority_display(),
            rule.conditions,
            rule.actions,
            rule.source_file,
            rule.source_line,
            rule.tags,
            'Yes' if rule.is_active else 'No',
            rule.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            rule.updated_at.strftime('%Y-%m-%d %H:%M:%S')
        ])
    
    return response


@login_required
def business_rule_toggle_active(request, rule_id):
    """Activar/desactivar regla de negocio"""
    
    rule = get_object_or_404(BusinessRule, id=rule_id)
    rule.is_active = not rule.is_active
    rule.save()
    
    status = _('activated') if rule.is_active else _('deactivated')
    messages.success(
        request,
        _('Business rule "%(name)s" %(status)s.') % {
            'name': rule.name, 'status': status
        }
    )
    
    return redirect('reports_ai:business_rule_detail', rule_id=rule.id)


@login_required
def business_rule_duplicate(request, rule_id):
    """Duplicar regla de negocio"""
    
    original_rule = get_object_or_404(BusinessRule, id=rule_id)
    
    # Crear copia
    new_rule = BusinessRule.objects.create(
        name=f"{original_rule.name} (Copy)",
        description=original_rule.description,
        category=original_rule.category,
        module=original_rule.module,
        priority=original_rule.priority,
        conditions=original_rule.conditions,
        actions=original_rule.actions,
        source_file=original_rule.source_file,
        source_line=original_rule.source_line,
        tags=original_rule.tags,
        is_active=False,  # Duplicado inactivo por defecto
        created_by=request.user
    )
    
    messages.success(
        request,
        _('Business rule duplicated successfully.')
    )
    
    return redirect('reports_ai:business_rule_edit', rule_id=new_rule.id)
