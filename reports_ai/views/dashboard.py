"""
Vista del Dashboard de Reports AI
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.utils.translation import gettext as _
from reports_ai.models import ReportRequest, AgentMetrics, BusinessRule, GlossaryTerm
from reports_ai.services.crew_service import CrewService
from datetime import date
import json


@login_required
@permission_required('reports_ai.view_reports', raise_exception=True)
def dashboard(request):
    """Dashboard principal de Reports AI"""
    
    # Obtener estadísticas básicas
    total_requests = ReportRequest.objects.count()
    completed_requests = ReportRequest.objects.filter(status='completed').count()
    pending_requests = ReportRequest.objects.filter(status='processing').count()
    error_requests = ReportRequest.objects.filter(status='error').count()
    
    # Métricas de agentes de hoy
    today_metrics = AgentMetrics.objects.filter(date=date.today())
    
    # Últimas 10 solicitudes
    recent_requests = ReportRequest.objects.all().order_by('-created_at')[:10]
    
    # Estadísticas adicionales
    avg_processing_time = 0
    total_tokens = 0
    success_rate = 0
    
    if total_requests > 0:
        from django.db.models import Avg, Sum
        
        # Calcular métricas de reportes completados
        completed_stats = ReportRequest.objects.filter(status='completed').aggregate(
            avg_time=Avg('processing_time'),
            total_tokens=Sum('tokens_used')
        )
        avg_processing_time = completed_stats['avg_time'] or 0
        total_tokens = completed_stats['total_tokens'] or 0
        
        # Calcular tasa de éxito
        success_rate = (completed_requests / total_requests) * 100 if total_requests > 0 else 0
    
    # Contar reglas y términos del glosario
    total_rules = BusinessRule.objects.filter(is_active=True).count()
    total_glossary_terms = GlossaryTerm.objects.filter(is_active=True).count()
    
    context = {
        # Estadísticas principales
        'total_requests': total_requests,
        'completed_requests': completed_requests,
        'pending_requests': pending_requests,
        'error_requests': error_requests,
        
        # Métricas
        'avg_processing_time': avg_processing_time,
        'total_tokens': total_tokens,
        'success_rate': success_rate,
        
        # Datos
        'today_metrics': today_metrics,
        'recent_requests': recent_requests,
        
        # Configuración
        'business_rules_count': total_rules,
        'glossary_count': total_glossary_terms,
    }
    
    return render(request, 'reports_ai/dashboard.html', context)


@login_required
@permission_required('reports_ai.generate_reports', raise_exception=True)
def generate_report(request):
    """Vista para generar un nuevo reporte"""
    
    if request.method == 'POST':
        # El formulario envía 'intent', no 'query'
        query = request.POST.get('intent', '').strip()
        
        if not query:
            messages.error(request, _('Por favor ingresa una consulta'))
            return redirect('reports_ai:generate_report')  # Regresar al form, no al dashboard
        
        try:
            # Inicializar servicio
            crew_service = CrewService()
            
            # Generar reporte
            result = crew_service.generate_report(
                query=query,
                user=request.user,
                empresa=getattr(request.user, 'empresa_activa', None),
                source='web'
            )
            
            if result['success']:
                messages.success(
                    request,
                    _('Reporte generado exitosamente: {}').format(result['request_id'])
                )
                return redirect('reports_ai:report_detail', request_id=result['request_id'])
            else:
                messages.error(
                    request,
                    _('Error generando reporte: {}').format(result.get('error', 'Error desconocido'))
                )
                
        except Exception as e:
            messages.error(request, _('Error: {}').format(str(e)))
        
        return redirect('reports_ai:dashboard')
    
    # GET: mostrar formulario
    context = {
        'example_queries': [
            _('Ventas netas de septiembre por sucursal'),
            _('Top 10 productos más vendidos'),
            _('Clientes activos del último trimestre'),
            _('Stock disponible por categoría'),
            _('Pedidos pendientes por antigüedad'),
        ]
    }
    
    return render(request, 'reports_ai/generate_form.html', context)


@login_required
@permission_required('reports_ai.configure_reports_ai', raise_exception=True)
def config(request):
    """Vista de configuración del módulo"""
    
    # Estadísticas del sistema
    business_rules_count = BusinessRule.objects.count()
    glossary_count = GlossaryTerm.objects.count()
    active_agents = 7  # Total de agentes implementados
    
    # Verificar conexiones
    openai_status = 'ok'
    mysql_status = 'ok'
    
    try:
        import os
        if not os.getenv('OPENAI_API_KEY'):
            openai_status = 'warning'
    except:
        openai_status = 'error'
    
    try:
        from administraNET_integration.services.connection_service import AdministraNETConnectionService
        connection = AdministraNETConnectionService()
        # Intenta obtener conexión
        connection.get_connection()
        mysql_status = 'ok'
    except:
        mysql_status = 'error'
    
    context = {
        'business_rules_count': business_rules_count,
        'glossary_count': glossary_count,
        'active_agents': active_agents,
        'openai_status': openai_status,
        'mysql_status': mysql_status,
    }
    
    return render(request, 'reports_ai/config.html', context)


@login_required
@permission_required('reports_ai.view_reports', raise_exception=True)
def report_detail(request, request_id):
    """Vista de detalle de un reporte específico"""
    
    report_request = get_object_or_404(ReportRequest, request_id=request_id)
    
    # Formatear el reporte para mejor visualización
    report_formatted = None
    if report_request.response_data:
        try:
            if isinstance(report_request.response_data, dict):
                report_formatted = json.dumps(report_request.response_data, indent=2, ensure_ascii=False)
            else:
                report_formatted = str(report_request.response_data)
        except:
            report_formatted = str(report_request.response_data)
    
    context = {
        'report_request': report_request,
        'report_formatted': report_formatted,
    }
    
    return render(request, 'reports_ai/report_detail.html', context)


@login_required
@permission_required('reports_ai.view_reports', raise_exception=True)
def report_history(request):
    """Vista de historial de reportes"""
    
    # Filtros
    status_filter = request.GET.get('status', '')
    
    # Query base
    queryset = ReportRequest.objects.all()
    
    # Aplicar filtros
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    
    # Filtrar por usuario si no es superuser
    if not request.user.is_superuser:
        queryset = queryset.filter(user=request.user)
    
    # Ordenar y paginar
    reports = queryset.order_by('-created_at')[:50]
    
    # Estadísticas
    stats = {
        'total': queryset.count(),
        'completed': queryset.filter(status='completed').count(),
        'processing': queryset.filter(status='processing').count(),
        'error': queryset.filter(status='error').count(),
    }
    
    context = {
        'reports': reports,
        'stats': stats,
        'status_filter': status_filter,
    }
    
    return render(request, 'reports_ai/report_history.html', context)


@login_required
@permission_required('reports_ai.view_agent_metrics', raise_exception=True)
def agent_metrics(request):
    """Vista de métricas de agentes"""
    
    # Métricas de hoy
    today_metrics = AgentMetrics.objects.filter(date=date.today()).order_by('agent_name')
    
    # Métricas de la última semana
    from datetime import timedelta
    week_ago = date.today() - timedelta(days=7)
    week_metrics = AgentMetrics.objects.filter(date__gte=week_ago)
    
    # Calcular totales
    total_invocations = sum(m.total_invocations for m in week_metrics)
    total_tokens = sum(m.total_tokens_used for m in week_metrics)
    total_hallucinations = sum(m.hallucination_count for m in week_metrics)
    
    # Métricas por agente con más detalles
    metrics_list = []
    for metric in today_metrics:
        metrics_list.append({
            'agent_name': metric.get_agent_name_display(),
            'total_invocations': metric.total_invocations,
            'successful_invocations': metric.successful_invocations,
            'failed_invocations': metric.failed_invocations,
            'success_rate': metric.success_rate,
            'avg_processing_time': metric.avg_processing_time,
            'total_tokens_used': metric.total_tokens_used,
            'hallucination_count': metric.hallucination_count,
        })
    
    context = {
        'metrics': metrics_list,
        'today_metrics': today_metrics,
        'total_invocations': total_invocations,
        'total_tokens': total_tokens,
        'total_hallucinations': total_hallucinations,
    }
    
    return render(request, 'reports_ai/agent_metrics.html', context)

