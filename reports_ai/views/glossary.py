"""
Vistas para gestión del Glosario
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.http import JsonResponse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_http_methods
import json

from ..models import GlossaryTerm
from ..forms import GlossaryTermForm


@login_required
def glossary_list(request):
    """Lista de términos del glosario"""
    
    # Búsqueda
    search = request.GET.get('search', '')
    category = request.GET.get('category', '')
    
    terms = GlossaryTerm.objects.all().order_by('term')
    
    if search:
        terms = terms.filter(
            Q(term__icontains=search) |
            Q(definition__icontains=search) |
            Q(context__icontains=search)
        )
    
    if category:
        terms = terms.filter(category=category)
    
    # Paginación
    paginator = Paginator(terms, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Estadísticas
    stats = {
        'total': GlossaryTerm.objects.count(),
        'active': GlossaryTerm.objects.filter(is_active=True).count(),
        'by_category': GlossaryTerm.objects.values('category').annotate(
            count=Count('id')
        ).order_by('-count')
    }
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'category': category,
        'stats': stats,
        'title': _('Glossary'),
        'breadcrumb': [
            {'name': _('Reports AI'), 'url': 'reports_ai:dashboard'},
            {'name': _('Glossary'), 'url': None}
        ]
    }
    
    return render(request, 'reports_ai/glossary/list.html', context)


@login_required
def glossary_term_detail(request, term_id):
    """Detalle de un término del glosario"""
    
    term = get_object_or_404(GlossaryTerm, id=term_id)
    
    # Términos relacionados (misma categoría)
    related_terms = GlossaryTerm.objects.filter(
        category=term.category
    ).exclude(id=term.id)[:5]
    
    context = {
        'term': term,
        'related_terms': related_terms,
        'title': f"{_('Glossary Term')}: {term.term}",
        'breadcrumb': [
            {'name': _('Reports AI'), 'url': 'reports_ai:dashboard'},
            {'name': _('Glossary'), 'url': 'reports_ai:glossary_list'},
            {'name': term.term, 'url': None}
        ]
    }
    
    return render(request, 'reports_ai/glossary/detail.html', context)


@login_required
def glossary_term_create(request):
    """Crear nuevo término del glosario"""
    
    if request.method == 'POST':
        form = GlossaryTermForm(request.POST)
        if form.is_valid():
            term = form.save()
            
            messages.success(
                request, 
                _('Glossary term created successfully.')
            )
            return redirect('reports_ai:glossary_term_detail', term_id=term.id)
    else:
        form = GlossaryTermForm()
    
    context = {
        'form': form,
        'title': _('Create Glossary Term'),
        'breadcrumb': [
            {'name': _('Reports AI'), 'url': 'reports_ai:dashboard'},
            {'name': _('Glossary'), 'url': 'reports_ai:glossary_list'},
            {'name': _('Create'), 'url': None}
        ]
    }
    
    return render(request, 'reports_ai/glossary/form.html', context)


@login_required
def glossary_term_edit(request, term_id):
    """Editar término del glosario existente"""
    
    term = get_object_or_404(GlossaryTerm, id=term_id)
    
    if request.method == 'POST':
        form = GlossaryTermForm(request.POST, instance=term)
        if form.is_valid():
            form.save()
            
            messages.success(
                request, 
                _('Glossary term updated successfully.')
            )
            return redirect('reports_ai:glossary_term_detail', term_id=term.id)
    else:
        form = GlossaryTermForm(instance=term)
    
    context = {
        'form': form,
        'term': term,
        'title': f"{_('Edit Glossary Term')}: {term.term}",
        'breadcrumb': [
            {'name': _('Reports AI'), 'url': 'reports_ai:dashboard'},
            {'name': _('Glossary'), 'url': 'reports_ai:glossary_list'},
            {'name': term.term, 'url': 'reports_ai:glossary_term_detail', 'args': [term.id]},
            {'name': _('Edit'), 'url': None}
        ]
    }
    
    return render(request, 'reports_ai/glossary/form.html', context)


@login_required
def glossary_term_delete(request, term_id):
    """Eliminar término del glosario"""
    
    term = get_object_or_404(GlossaryTerm, id=term_id)
    
    if request.method == 'POST':
        term_name = term.term
        term.delete()
        
        messages.success(
            request, 
            _('Glossary term "%(term)s" deleted successfully.') % {'term': term_name}
        )
        return redirect('reports_ai:glossary_list')
    
    context = {
        'term': term,
        'title': f"{_('Delete Glossary Term')}: {term.term}",
        'breadcrumb': [
            {'name': _('Reports AI'), 'url': 'reports_ai:dashboard'},
            {'name': _('Glossary'), 'url': 'reports_ai:glossary_list'},
            {'name': term.term, 'url': 'reports_ai:glossary_term_detail', 'args': [term.id]},
            {'name': _('Delete'), 'url': None}
        ]
    }
    
    return render(request, 'reports_ai/glossary/delete.html', context)


@login_required
def glossary_term_toggle_active(request, term_id):
    """Activar/desactivar término del glosario"""
    
    term = get_object_or_404(GlossaryTerm, id=term_id)
    term.is_active = not term.is_active
    term.save()
    
    status = _('activated') if term.is_active else _('deactivated')
    messages.success(
        request,
        _('Glossary term "%(term)s" %(status)s.') % {
            'term': term.term, 'status': status
        }
    )
    
    return redirect('reports_ai:glossary_term_detail', term_id=term.id)


@login_required
def glossary_search_api(request):
    """API para búsqueda de términos del glosario (AJAX)"""
    
    query = request.GET.get('q', '')
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    terms = GlossaryTerm.objects.filter(
        Q(term__icontains=query) |
        Q(definition__icontains=query)
    ).filter(is_active=True)[:10]
    
    results = []
    for term in terms:
        results.append({
            'id': term.id,
            'term': term.term,
            'definition': term.definition[:100] + '...' if len(term.definition) > 100 else term.definition,
            'category': term.get_category_display()
        })
    
    return JsonResponse({'results': results})


@login_required
def glossary_export(request):
    """Exportar glosario"""
    
    terms = GlossaryTerm.objects.all().order_by('term')
    
    # Crear respuesta JSON
    data = {
        'glossary': [],
        'export_date': str(terms.first().created_at) if terms.exists() else None,
        'total_terms': terms.count()
    }
    
    for term in terms:
        data['glossary'].append({
            'term': term.term,
            'definition': term.definition,
            'category': term.category,
            'context': term.context,
            'examples': term.examples,
            'is_active': term.is_active,
            'created_at': str(term.created_at),
            'updated_at': str(term.updated_at)
        })
    
    response = JsonResponse(data, json_dumps_params={'indent': 2})
    response['Content-Disposition'] = 'attachment; filename="glossary.json"'
    
    return response


@login_required
def glossary_import(request):
    """Importar glosario desde archivo JSON"""
    
    if request.method == 'POST':
        try:
            uploaded_file = request.FILES['glossary_file']
            
            if not uploaded_file.name.endswith('.json'):
                messages.error(request, _('Please upload a JSON file.'))
                return redirect('reports_ai:glossary_list')
            
            # Leer y procesar archivo
            data = json.loads(uploaded_file.read().decode('utf-8'))
            
            imported_count = 0
            for term_data in data.get('glossary', []):
                term, created = GlossaryTerm.objects.get_or_create(
                    term=term_data['term'],
                    defaults={
                        'definition': term_data.get('definition', ''),
                        'category': term_data.get('category', 'general'),
                        'context': term_data.get('context', ''),
                        'examples': term_data.get('examples', ''),
                        'is_active': term_data.get('is_active', True)
                    }
                )
                if created:
                    imported_count += 1
            
            messages.success(
                request,
                _('Successfully imported %(count)d glossary terms.') % {'count': imported_count}
            )
            
        except Exception as e:
            messages.error(
                request,
                _('Error importing glossary: %(error)s') % {'error': str(e)}
            )
    
    return redirect('reports_ai:glossary_list')
