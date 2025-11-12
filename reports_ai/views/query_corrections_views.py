"""
Views para gestión de correcciones de queries
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib.auth.models import User

from reports_ai.models import QueryCorrection, ReportRequest


@login_required
def corrections_list(request):
    """
    Lista todas las correcciones de queries
    """
    corrections = QueryCorrection.objects.all()
    
    # Filtros
    search = request.GET.get('search', '')
    correction_type = request.GET.get('type', '')
    applied = request.GET.get('applied', '')
    
    if search:
        corrections = corrections.filter(
            Q(original_query__icontains=search) |
            Q(correction_notes__icontains=search)
        )
    
    if correction_type:
        corrections = corrections.filter(correction_type=correction_type)
    
    if applied == 'yes':
        corrections = corrections.filter(applied_to_catalog=True)
    elif applied == 'no':
        corrections = corrections.filter(applied_to_catalog=False)
    
    # Paginación
    paginator = Paginator(corrections, 20)
    page = request.GET.get('page', 1)
    corrections = paginator.get_page(page)
    
    context = {
        'corrections': corrections,
        'search': search,
        'correction_type': correction_type,
        'applied': applied,
        'correction_types': QueryCorrection._meta.get_field('correction_type').choices
    }
    
    return render(request, 'reports_ai/corrections/list.html', context)


@login_required
def correction_detail(request, correction_id):
    """
    Detalle de una corrección
    """
    correction = get_object_or_404(QueryCorrection, id=correction_id)
    
    context = {
        'correction': correction
    }
    
    return render(request, 'reports_ai/corrections/detail.html', context)


@login_required
def create_correction(request, report_request_id=None):
    """
    Crear nueva corrección
    """
    report_request = None
    if report_request_id:
        report_request = get_object_or_404(ReportRequest, id=report_request_id)
    
    if request.method == 'POST':
        original_query = request.POST.get('original_query', '')
        original_sql = request.POST.get('original_sql', '')
        correction_type = request.POST.get('correction_type', '')
        corrected_sql = request.POST.get('corrected_sql', '')
        correction_notes = request.POST.get('correction_notes', '')
        
        if not original_query or not correction_notes:
            messages.error(request, 'La query original y las notas son obligatorias')
        else:
            correction = QueryCorrection.objects.create(
                report_request=report_request,
                original_query=original_query,
                original_sql=original_sql,
                correction_type=correction_type or 'wrong_table',
                corrected_sql=corrected_sql,
                correction_notes=correction_notes,
                corrected_by=request.user
            )
            
            messages.success(request, 'Corrección creada exitosamente')
            return redirect('reports_ai:correction_detail', correction_id=correction.id)
    
    context = {
        'report_request': report_request,
        'correction_types': QueryCorrection._meta.get_field('correction_type').choices
    }
    
    return render(request, 'reports_ai/corrections/form.html', context)


@login_required
def edit_correction(request, correction_id):
    """
    Editar corrección existente
    """
    correction = get_object_or_404(QueryCorrection, id=correction_id)
    
    if request.method == 'POST':
        correction.original_query = request.POST.get('original_query', '')
        correction.original_sql = request.POST.get('original_sql', '')
        correction.correction_type = request.POST.get('correction_type', '')
        correction.corrected_sql = request.POST.get('corrected_sql', '')
        correction.correction_notes = request.POST.get('correction_notes', '')
        correction.applied_to_catalog = request.POST.get('applied_to_catalog') == 'on'
        
        correction.save()
        
        messages.success(request, 'Corrección actualizada exitosamente')
        return redirect('reports_ai:correction_detail', correction_id=correction.id)
    
    context = {
        'correction': correction,
        'correction_types': QueryCorrection._meta.get_field('correction_type').choices
    }
    
    return render(request, 'reports_ai/corrections/form.html', context)


@login_required
def mark_applied(request, correction_id):
    """
    Marca una corrección como aplicada al catálogo
    """
    correction = get_object_or_404(QueryCorrection, id=correction_id)
    
    correction.applied_to_catalog = True
    correction.save()
    
    messages.success(request, 'Corrección marcada como aplicada')
    return redirect('reports_ai:correction_detail', correction_id=correction.id)


@login_required
def delete_correction(request, correction_id):
    """
    Elimina una corrección
    """
    correction = get_object_or_404(QueryCorrection, id=correction_id)
    
    if request.method == 'POST':
        correction.delete()
        messages.success(request, 'Corrección eliminada')
        return redirect('reports_ai:corrections_list')
    
    context = {
        'correction': correction
    }
    
    return render(request, 'reports_ai/corrections/delete_confirm.html', context)

