from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json

# Eliminada la importación de core.constantes_permisos
from .models import Report, ReportTemplate, ReportComponent, ReportSchedule, ReportExport
from .forms import ReportForm, ReportTemplateForm, ReportScheduleForm


@login_required
@permission_required('reports.ver')
def dashboard(request):
    """
    Dashboard principal del módulo de reportes
    """
    # Obtener estadísticas
    total_reports = Report.objects.filter(empresa=request.user.empresa).count()
    active_reports = Report.objects.filter(empresa=request.user.empresa, is_active=True).count()
    scheduled_reports = ReportSchedule.objects.filter(
        report__empresa=request.user.empresa, 
        is_active=True
    ).count()
    recent_reports = Report.objects.filter(
        empresa=request.user.empresa
    ).order_by('-created_at')[:5]
    
    # Obtener plantillas populares
    popular_templates = ReportTemplate.objects.filter(
        empresa=request.user.empresa
    ).annotate(
        usage_count=Count('reports')
    ).order_by('-usage_count')[:5]
    
    context = {
        'total_reports': total_reports,
        'active_reports': active_reports,
        'scheduled_reports': scheduled_reports,
        'recent_reports': recent_reports,
        'popular_templates': popular_templates,
    }
    
    return render(request, 'reports/dashboard.html', context)


@login_required
@permission_required('reports.ver')
def report_list(request):
    """
    Lista de reportes con filtros y paginación
    """
    reports = Report.objects.filter(empresa=request.user.empresa)
    
    # Filtros
    search = request.GET.get('search')
    is_active = request.GET.get('is_active')
    template_id = request.GET.get('template')
    
    if search:
        reports = reports.filter(
            Q(name__icontains=search) | 
            Q(description__icontains=search)
        )
    
    if is_active:
        reports = reports.filter(is_active=is_active == 'true')
    
    if template_id:
        reports = reports.filter(template_id=template_id)
    
    # Ordenamiento
    reports = reports.order_by('-created_at')
    
    # Paginación
    paginator = Paginator(reports, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Obtener plantillas para el filtro
    templates = ReportTemplate.objects.filter(empresa=request.user.empresa)
    
    context = {
        'reports': page_obj,
        'templates': templates,
        'is_paginated': paginator.num_pages > 1,
        'page_obj': page_obj,
    }
    
    return render(request, 'reports/report_list.html', context)


@login_required
@permission_required('reports.crear')
def report_create(request):
    """
    Crear nuevo reporte
    """
    if request.method == 'POST':
        form = ReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.empresa = request.user.empresa
            report.created_by = request.user
            report.save()
            
            messages.success(request, 'Reporte creado exitosamente.')
            return redirect('reports:report_detail', pk=report.pk)
    else:
        form = ReportForm()
    
    # Obtener plantillas para la selección
    templates = ReportTemplate.objects.filter(empresa=request.user.empresa)
    
    context = {
        'form': form,
        'templates': templates,
        'object': None,
    }
    
    return render(request, 'reports/report_form.html', context)


@login_required
@permission_required('reports.editar')
def report_edit(request, pk):
    """
    Editar reporte existente
    """
    report = get_object_or_404(Report, pk=pk, empresa=request.user.empresa)
    
    if request.method == 'POST':
        form = ReportForm(request.POST, instance=report)
        if form.is_valid():
            report = form.save()
            messages.success(request, 'Reporte actualizado exitosamente.')
            return redirect('reports:report_detail', pk=report.pk)
    else:
        form = ReportForm(instance=report)
    
    # Obtener plantillas para la selección
    templates = ReportTemplate.objects.filter(empresa=request.user.empresa)
    
    context = {
        'form': form,
        'templates': templates,
        'object': report,
    }
    
    return render(request, 'reports/report_form.html', context)


@login_required
@permission_required('reports.ver')
def report_detail(request, pk):
    """
    Detalle de reporte con estadísticas y acciones
    """
    report = get_object_or_404(Report, pk=pk, empresa=request.user.empresa)
    
    # Obtener estadísticas
    exports_count = ReportExport.objects.filter(report=report).count()
    schedules_count = ReportSchedule.objects.filter(report=report).count()
    components_count = ReportComponent.objects.filter(report=report).count()
    
    # Obtener exportaciones recientes
    recent_exports = ReportExport.objects.filter(
        report=report
    ).order_by('-created_at')[:5]
    
    # Obtener programaciones
    scheduled_reports = ReportSchedule.objects.filter(
        report=report
    ).order_by('-created_at')[:5]
    
    context = {
        'report': report,
        'exports_count': exports_count,
        'schedules_count': schedules_count,
        'components_count': components_count,
        'recent_exports': recent_exports,
        'scheduled_reports': scheduled_reports,
    }
    
    return render(request, 'reports/report_detail.html', context)


@login_required
@permission_required('reports.eliminar')
def report_delete(request, pk):
    """
    Eliminar reporte
    """
    report = get_object_or_404(Report, pk=pk, empresa=request.user.empresa)
    
    if request.method == 'POST':
        report.delete()
        messages.success(request, 'Reporte eliminado exitosamente.')
        return redirect('reports:report_list')
    
    return redirect('reports:report_detail', pk=report.pk)


@login_required
@permission_required('reports.ver')
def component_library(request):
    """
    Biblioteca de componentes disponibles
    """
    # Por ahora, componentes estáticos
    # En el futuro, esto vendrá de la base de datos
    components = [
        {
            'name': 'Line Chart',
            'category': 'chart',
            'description': 'Display data trends over time with smooth line visualization',
            'icon': 'chart-line'
        },
        {
            'name': 'Bar Chart',
            'category': 'chart',
            'description': 'Compare values across categories with vertical bars',
            'icon': 'chart-bar'
        },
        {
            'name': 'Pie Chart',
            'category': 'chart',
            'description': 'Show proportions and percentages in a circular format',
            'icon': 'chart-pie'
        },
        {
            'name': 'Data Table',
            'category': 'table',
            'description': 'Display structured data with sorting and filtering',
            'icon': 'table'
        },
        {
            'name': 'Title',
            'category': 'text',
            'description': 'Add headings and titles to your report',
            'icon': 'text'
        },
        {
            'name': 'Image',
            'category': 'image',
            'description': 'Add images, logos, and visual elements',
            'icon': 'image'
        },
    ]
    
    context = {
        'components': components,
    }
    
    return render(request, 'reports/component_library.html', context)


@login_required
@permission_required('reports.ver')
def template_list(request):
    """
    Lista de plantillas disponibles
    """
    templates = ReportTemplate.objects.filter(empresa=request.user.empresa)
    
    # Filtros
    search = request.GET.get('search')
    category = request.GET.get('category')
    sort = request.GET.get('sort', 'name')
    
    if search:
        templates = templates.filter(
            Q(name__icontains=search) | 
            Q(description__icontains=search)
        )
    
    if category:
        templates = templates.filter(category=category)
    
    # Ordenamiento
    if sort == 'created':
        templates = templates.order_by('-created_at')
    elif sort == 'popular':
        templates = templates.annotate(
            usage_count=Count('reports')
        ).order_by('-usage_count')
    else:
        templates = templates.order_by('name')
    
    # Paginación
    paginator = Paginator(templates, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'templates': page_obj,
        'is_paginated': paginator.num_pages > 1,
        'page_obj': page_obj,
    }
    
    return render(request, 'reports/template_list.html', context)


@login_required
@permission_required('reports.ver')
def template_detail(request, pk):
    """
    Detalle de plantilla
    """
    template = get_object_or_404(ReportTemplate, pk=pk, empresa=request.user.empresa)
    
    # Obtener reportes que usan esta plantilla
    reports_using_template = Report.objects.filter(
        template=template,
        empresa=request.user.empresa
    ).order_by('-created_at')[:10]
    
    context = {
        'template': template,
        'reports_using_template': reports_using_template,
    }
    
    return render(request, 'reports/template_detail.html', context)


@login_required
@permission_required('reports.crear')
def template_create(request):
    """
    Crear nueva plantilla
    """
    if request.method == 'POST':
        form = ReportTemplateForm(request.POST)
        if form.is_valid():
            template = form.save(commit=False)
            template.empresa = request.user.empresa
            template.created_by = request.user
            template.save()
            
            messages.success(request, 'Plantilla creada exitosamente.')
            return redirect('reports:template_detail', pk=template.pk)
    else:
        form = ReportTemplateForm()
    
    context = {
        'form': form,
        'object': None,
    }
    
    return render(request, 'reports/template_form.html', context)


@login_required
@permission_required('reports.editar')
def template_edit(request, pk):
    """
    Editar plantilla existente
    """
    template = get_object_or_404(ReportTemplate, pk=pk, empresa=request.user.empresa)
    
    if request.method == 'POST':
        form = ReportTemplateForm(request.POST, instance=template)
        if form.is_valid():
            template = form.save()
            messages.success(request, 'Plantilla actualizada exitosamente.')
            return redirect('reports:template_detail', pk=template.pk)
    else:
        form = ReportTemplateForm(instance=template)
    
    context = {
        'form': form,
        'object': template,
    }
    
    return render(request, 'reports/template_form.html', context)


@login_required
@permission_required('reports.programar')
def schedule_list(request):
    """
    Lista de programaciones de reportes
    """
    schedules = ReportSchedule.objects.filter(
        report__empresa=request.user.empresa
    ).select_related('report', 'created_by')
    
    # Filtros
    search = request.GET.get('search')
    is_active = request.GET.get('is_active')
    frequency = request.GET.get('frequency')
    
    if search:
        schedules = schedules.filter(
            Q(name__icontains=search) | 
            Q(report__name__icontains=search)
        )
    
    if is_active:
        schedules = schedules.filter(is_active=is_active == 'true')
    
    if frequency:
        schedules = schedules.filter(frequency=frequency)
    
    # Ordenamiento
    schedules = schedules.order_by('-created_at')
    
    # Paginación
    paginator = Paginator(schedules, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'schedules': page_obj,
        'is_paginated': paginator.num_pages > 1,
        'page_obj': page_obj,
    }
    
    return render(request, 'reports/schedule_list.html', context)


@login_required
@permission_required('reports.programar')
def schedule_create(request):
    """
    Crear nueva programación
    """
    if request.method == 'POST':
        form = ReportScheduleForm(request.POST)
        if form.is_valid():
            schedule = form.save(commit=False)
            schedule.created_by = request.user
            schedule.save()
            form.save_m2m()  # Para campos many-to-many
            
            messages.success(request, 'Programación creada exitosamente.')
            return redirect('reports:schedule_detail', pk=schedule.pk)
    else:
        form = ReportScheduleForm()
        # Filtrar reportes por empresa
        form.fields['report'].queryset = Report.objects.filter(
            empresa=request.user.empresa
        )
    
    context = {
        'form': form,
        'object': None,
    }
    
    return render(request, 'reports/schedule_form.html', context)


@login_required
@permission_required('reports.programar')
def schedule_edit(request, pk):
    """
    Editar programación existente
    """
    schedule = get_object_or_404(
        ReportSchedule, 
        pk=pk, 
        report__empresa=request.user.empresa
    )
    
    if request.method == 'POST':
        form = ReportScheduleForm(request.POST, instance=schedule)
        if form.is_valid():
            schedule = form.save()
            messages.success(request, 'Programación actualizada exitosamente.')
            return redirect('reports:schedule_detail', pk=schedule.pk)
    else:
        form = ReportScheduleForm(instance=schedule)
        # Filtrar reportes por empresa
        form.fields['report'].queryset = Report.objects.filter(
            empresa=request.user.empresa
        )
    
    context = {
        'form': form,
        'object': schedule,
    }
    
    return render(request, 'reports/schedule_form.html', context)


@login_required
@permission_required('reports.programar')
def schedule_detail(request, pk):
    """
    Detalle de programación
    """
    schedule = get_object_or_404(
        ReportSchedule, 
        pk=pk, 
        report__empresa=request.user.empresa
    )
    
    # Obtener ejecuciones recientes
    recent_executions = ReportExport.objects.filter(
        schedule=schedule
    ).order_by('-created_at')[:10]
    
    context = {
        'schedule': schedule,
        'recent_executions': recent_executions,
    }
    
    return render(request, 'reports/schedule_detail.html', context)


@login_required
@permission_required('reports.exportar')
def report_export(request, pk):
    """
    Exportar reporte
    """
    report = get_object_or_404(Report, pk=pk, empresa=request.user.empresa)
    
    # Por ahora, solo simular exportación
    # En el futuro, esto generará PDF/PPTX reales
    export = ReportExport.objects.create(
        report=report,
        created_by=request.user,
        format='pdf',
        status='completed'
    )
    
    messages.success(request, 'Reporte exportado exitosamente.')
    return redirect('reports:report_detail', pk=report.pk)


@login_required
@permission_required('reports.ver')
def report_builder(request, pk):
    """
    Constructor visual de reportes con drag & drop
    """
    report = get_object_or_404(Report, pk=pk, empresa=request.user.empresa)
    
    # Obtener componentes del reporte
    components = ReportComponent.objects.filter(report=report).order_by('order')
    
    context = {
        'report': report,
        'components': components,
    }
    
    return render(request, 'reports/report_builder.html', context)


@login_required
@permission_required('reports.editar')
@require_http_methods(["POST"])
@csrf_exempt
def save_report_config(request, pk):
    """
    Guardar configuración del reporte via AJAX
    """
    try:
        report = get_object_or_404(Report, pk=pk, empresa=request.user.empresa)
        data = json.loads(request.body)
        components_data = data.get('components', [])
        
        # Eliminar componentes existentes
        ReportComponent.objects.filter(report=report).delete()
        
        # Crear nuevos componentes
        for i, comp_data in enumerate(components_data):
            ReportComponent.objects.create(
                report=report,
                name=comp_data.get('type', 'Component'),
                component_type=comp_data.get('type', 'text'),
                config=json.dumps(comp_data.get('config', {})),
                order=i
            )
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@permission_required('reports.ver')
def get_report_config(request, pk):
    """
    Obtener configuración del reporte via AJAX
    """
    try:
        report = get_object_or_404(Report, pk=pk, empresa=request.user.empresa)
        components = ReportComponent.objects.filter(report=report).order_by('order')
        
        components_data = []
        for comp in components:
            try:
                config = json.loads(comp.config) if comp.config else {}
            except:
                config = {}
            
            components_data.append({
                'id': comp.id,
                'type': comp.component_type,
                'name': comp.name,
                'config': config,
                'order': comp.order
            })
        
        return JsonResponse({
            'success': True,
            'components': components_data
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@permission_required('reports.ver')
def report_preview(request, pk):
    """
    Vista previa del reporte
    """
    report = get_object_or_404(Report, pk=pk, empresa=request.user.empresa)
    components = ReportComponent.objects.filter(report=report).order_by('order')
    
    context = {
        'report': report,
        'components': components,
        'is_preview': True,
    }
    
    return render(request, 'reports/report_preview.html', context)


# APIs para funcionalidad AJAX
@login_required
@permission_required('reports.programar')
@require_http_methods(["POST"])
@csrf_exempt
def schedule_toggle(request, pk):
    """
    Activar/desactivar programación via AJAX
    """
    try:
        schedule = get_object_or_404(
            ReportSchedule, 
            pk=pk, 
            report__empresa=request.user.empresa
        )
        
        data = json.loads(request.body)
        is_active = data.get('is_active', False)
        
        schedule.is_active = is_active
        schedule.save()
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# APIs para el constructor visual
@login_required
@permission_required('reports.editar')
@require_http_methods(["GET"])
def get_report_config(request, pk):
    """
    Obtener configuración del reporte para el constructor visual
    """
    try:
        report = get_object_or_404(Report, pk=pk, empresa=request.user.empresa)
        components = ReportComponent.objects.filter(report=report).order_by('order')
        
        components_data = []
        for component in components:
            components_data.append({
                'id': component.id,
                'type': component.component_type,
                'config': json.loads(component.config) if component.config else {},
                'order': component.order
            })
        
        return JsonResponse({
            'success': True,
            'components': components_data
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@permission_required('reports.editar')
@require_http_methods(["POST"])
@csrf_exempt
def save_report_config(request, pk):
    """
    Guardar configuración del reporte desde el constructor visual
    """
    try:
        report = get_object_or_404(Report, pk=pk, empresa=request.user.empresa)
        data = json.loads(request.body)
        components_data = data.get('components', [])
        
        # Eliminar componentes existentes
        ReportComponent.objects.filter(report=report).delete()
        
        # Crear nuevos componentes
        for i, component_data in enumerate(components_data):
            ReportComponent.objects.create(
                report=report,
                name=component_data.get('name', f'Component {i+1}'),
                component_type=component_data.get('type', 'text'),
                config=json.dumps(component_data.get('config', {})),
                order=i
            )
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@permission_required('reports.ver')
def report_preview(request, pk):
    """
    Vista previa del reporte generado
    """
    report = get_object_or_404(Report, pk=pk, empresa=request.user.empresa)
    components = ReportComponent.objects.filter(report=report).order_by('order')
    
    context = {
        'report': report,
        'components': components,
        'is_preview': True
    }
    
    return render(request, 'reports/report_preview.html', context) 