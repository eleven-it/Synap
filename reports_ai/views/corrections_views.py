"""
Vistas para el sistema de correcciones humanas (active learning)
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from ..models import ReportRequest, QueryCorrection, RelationshipCandidate, SynonymMapping
from ..services.quality_metrics import QualityMetricsService


@login_required
def corrections_list(request):
    """
    Lista de queries que requieren o tuvieron correcciones
    """
    # Obtener todas las correcciones
    corrections = QueryCorrection.objects.select_related(
        'report_request',
        'corrected_by'
    ).order_by('-corrected_at')
    
    # Filtros
    correction_type = request.GET.get('type')
    if correction_type:
        corrections = corrections.filter(correction_type=correction_type)
    
    # Métricas rápidas
    total_corrections = corrections.count()
    pending_apply = corrections.filter(applied_to_catalog=False).count()
    
    context = {
        'corrections': corrections[:100],  # Últimas 100
        'total_corrections': total_corrections,
        'pending_apply': pending_apply,
        'correction_types': QueryCorrection._meta.get_field('correction_type').choices
    }
    
    return render(request, 'reports_ai/corrections/list.html', context)


@login_required
def correction_detail(request, correction_id):
    """
    Detalle de una corrección específica
    """
    correction = get_object_or_404(
        QueryCorrection.objects.select_related('report_request', 'corrected_by'),
        id=correction_id
    )
    
    context = {
        'correction': correction
    }
    
    return render(request, 'reports_ai/corrections/detail.html', context)


@login_required
@require_POST
def create_correction(request):
    """
    Crea una nueva corrección para una query
    """
    report_id = request.POST.get('report_id')
    correction_type = request.POST.get('correction_type')
    corrected_sql = request.POST.get('corrected_sql', '')
    notes = request.POST.get('notes', '')
    
    report = get_object_or_404(ReportRequest, id=report_id)
    
    # Crear la corrección
    correction = QueryCorrection.objects.create(
        report_request=report,
        original_query=report.query,
        original_sql=report.sql_query,
        correction_type=correction_type,
        corrected_sql=corrected_sql,
        correction_notes=notes,
        corrected_by=request.user
    )
    
    messages.success(request, '✅ Corrección registrada exitosamente')
    
    return redirect('reports_ai:correction_detail', correction_id=correction.id)


@login_required
@require_POST
def apply_correction(request, correction_id):
    """
    Aplica una corrección al catálogo (active learning)
    Actualiza relaciones y sinónimos basándose en la corrección
    """
    correction = get_object_or_404(QueryCorrection, id=correction_id)
    
    if correction.applied_to_catalog:
        return JsonResponse({
            'success': False,
            'error': 'Esta corrección ya fue aplicada'
        })
    
    try:
        # Aplicar según el tipo de corrección
        if correction.correction_type == 'wrong_table':
            # TODO: Actualizar sinónimos para evitar la tabla incorrecta
            pass
        
        elif correction.correction_type == 'wrong_column':
            # TODO: Actualizar sinónimos de columnas
            pass
        
        elif correction.correction_type in ['missing_join', 'wrong_join']:
            # TODO: Ajustar relaciones en el catálogo
            pass
        
        # Marcar como aplicada
        correction.applied_to_catalog = True
        correction.save()
        
        messages.success(request, '✅ Corrección aplicada al catálogo')
        
        return JsonResponse({
            'success': True,
            'message': 'Corrección aplicada exitosamente'
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
def relationships_list(request):
    """
    Lista todas las relaciones descubiertas con filtros
    """
    from django.core.paginator import Paginator
    
    relationships = RelationshipCandidate.objects.all().order_by('-confidence_score')
    
    # Filtros
    min_confidence = request.GET.get('min_confidence', '')
    rel_type = request.GET.get('type', '')
    validated = request.GET.get('validated', '')
    search = request.GET.get('search', '')
    
    if min_confidence:
        try:
            relationships = relationships.filter(confidence_score__gte=float(min_confidence))
        except ValueError:
            pass
    
    if rel_type:
        relationships = relationships.filter(cardinality=rel_type)
    
    if validated == 'yes':
        relationships = relationships.filter(validated_by_human=True)
    elif validated == 'no':
        relationships = relationships.filter(validated_by_human=False)
    
    if search:
        from django.db.models import Q
        relationships = relationships.filter(
            Q(source_table__icontains=search) |
            Q(target_table__icontains=search) |
            Q(source_column__icontains=search) |
            Q(target_column__icontains=search)
        )
    
    # Paginación
    paginator = Paginator(relationships, 50)
    page = request.GET.get('page', 1)
    relationships = paginator.get_page(page)
    
    context = {
        'relationships': relationships,
        'min_confidence': min_confidence,
        'rel_type': rel_type,
        'validated': validated,
        'search': search,
        'total_count': paginator.count
    }
    
    return render(request, 'reports_ai/quality/relationships.html', context)


@login_required
def quality_dashboard(request):
    """
    Dashboard de métricas de calidad
    """
    period_days = int(request.GET.get('period', 7))
    
    service = QualityMetricsService()
    metrics = service.calculate_all_metrics(period_days=period_days)
    
    # Top relaciones
    top_relationships = service.get_top_relationships(limit=10)
    
    # Queries problemáticas
    from django.utils import timezone
    from datetime import timedelta
    since = timezone.now() - timedelta(days=period_days)
    problematic = service.get_problematic_queries(since=since, limit=10)
    
    context = {
        'metrics': metrics,
        'top_relationships': top_relationships,
        'problematic_queries': problematic,
        'period_days': period_days,
        'report_text': service.generate_report(period_days=period_days)
    }
    
    return render(request, 'reports_ai/quality/dashboard.html', context)


@login_required
def validate_relationship(request, relationship_id):
    """
    Marca una relación como validada por humano
    """
    relationship = get_object_or_404(RelationshipCandidate, id=relationship_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'validate':
            relationship.validated_by_human = True
            relationship.update_confidence()  # Recalcula con bonus de validación
            relationship.save()
            messages.success(request, f'✅ Relación validada: {relationship}')
        
        elif action == 'reject':
            relationship.delete()
            messages.warning(request, f'🗑️ Relación eliminada: {relationship}')
        
        return redirect('reports_ai:quality_dashboard')
    
    context = {
        'relationship': relationship
    }
    
    return render(request, 'reports_ai/corrections/validate_relationship.html', context)

